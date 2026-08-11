"""
Integração com o Outlook Desktop Classic via COM (pywin32).

Requer Outlook instalado, com perfil configurado, em sessão Windows
interativa (COM não funciona em serviço headless).
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import pythoncom
import win32com.client

from src.config.logger_config import logger
from src.config.outlook_config import Attachment, EmailMessage

_PR_ATTACH_FLAGS = "http://schemas.microsoft.com/mapi/proptag/0x37140003"
_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def _sanitize_filename(name: str) -> str:
    return _INVALID_FILENAME_CHARS.sub("_", name)


def _to_datetime(com_dt) -> Optional[datetime]:
    if com_dt is None:
        return None
    try:
        return datetime(
            com_dt.year, com_dt.month, com_dt.day,
            com_dt.hour, com_dt.minute, com_dt.second,
        )
    except Exception:
        return None


class OutlookError(RuntimeError):
    """Exceção base para erros do OutlookService."""


class OutlookService:
    """Interface com o Outlook Desktop via COM (win32com)."""

    def __init__(self, account: str) -> None:
        self._account = account
        logger.info(f"Conectando ao Outlook (conta configurada: '{account}')...")
        pythoncom.CoInitialize()
        try:
            self._app = win32com.client.Dispatch("Outlook.Application")
            self._ns = self._app.GetNamespace("MAPI")
        except Exception as exc:
            logger.error(
                f"Falha ao conectar ao Outlook via COM: {exc}. "
                "Verifique se: (1) o Outlook Desktop Classic está instalado e aberto "
                "(não o 'Novo Outlook' do Windows 11); (2) não está em 'modo de "
                "funcionalidade reduzida' (feche e reabra o Outlook); (3) há um "
                "perfil/arquivo de dados padrão configurado."
            )
            raise OutlookError(
                "Não foi possível conectar ao Outlook. "
                "Verifique se ele está instalado e aberto com perfil configurado."
            ) from exc
        logger.info("Conectado ao Outlook com sucesso.")

    # ------------------------------------------------------------------
    # Leitura de e-mails
    # ------------------------------------------------------------------

    def fetch_emails_from_folder(self, folder_name: str) -> list[EmailMessage]:
        """Retorna e-mails de uma pasta de topo da conta (irmã do Inbox)."""
        logger.debug(f"Lendo e-mails da pasta '{folder_name}' (conta '{self._account}')...")
        folder = self._get_or_create_top_level_folder(folder_name)
        items = folder.Items
        items.Sort("[ReceivedTime]", True)

        emails: list[EmailMessage] = []
        ignorados = 0
        for item in items:
            try:
                if item.Class != 43:  # olMailItem = 43
                    ignorados += 1
                    continue
                emails.append(self._build_email(item))
            except Exception as exc:
                ignorados += 1
                logger.warning(f"Item ignorado ao ler '{folder_name}' (não é um e-mail válido?): {exc}")
        logger.debug(
            f"Pasta '{folder_name}': {len(emails)} e-mail(s) lido(s), {ignorados} item(ns) ignorado(s)."
        )
        return emails

    def get_email_by_entry_id(self, entry_id: str) -> EmailMessage:
        """Busca um email pelo seu EntryID."""
        try:
            item = self._ns.GetItemFromID(entry_id)
            return self._build_email(item)
        except Exception as exc:
            raise OutlookError(f"Email com entry_id '{entry_id}' não encontrado.") from exc

    # ------------------------------------------------------------------
    # Movimentação
    # ------------------------------------------------------------------

    def move_to_subfolder(self, entry_id: str, folder_name: str, subfolder_name: str) -> None:
        """Move e-mail para `subfolder_name`, dentro da pasta de topo `folder_name`."""
        try:
            item = self._ns.GetItemFromID(entry_id)
        except Exception as exc:
            raise OutlookError(f"Email '{entry_id}' não encontrado para mover.") from exc

        folder = self._get_or_create_top_level_folder(folder_name)
        target = self._get_or_create_subfolder(folder, subfolder_name)
        try:
            item.Move(target)
            logger.debug(f"E-mail '{entry_id}' movido para '{folder_name}/{subfolder_name}'.")
        except Exception as exc:
            raise OutlookError(
                f"Falha ao mover email '{entry_id}' para '{folder_name}/{subfolder_name}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Download de anexos
    # ------------------------------------------------------------------

    def download_attachments(self, entry_id: str, dest_folder: Path) -> list[Path]:
        """Baixa todos os anexos não-inline de um e-mail para `dest_folder`."""
        dest_folder.mkdir(parents=True, exist_ok=True)

        try:
            item = self._ns.GetItemFromID(entry_id)
        except Exception as exc:
            raise OutlookError(f"Email '{entry_id}' não encontrado.") from exc

        attachments = item.Attachments
        total = attachments.Count
        logger.debug(f"E-mail '{entry_id}' tem {total} anexo(s) (inclui inline).")
        if total == 0:
            return []

        saved: list[Path] = []
        for idx in range(1, total + 1):
            attach = attachments.Item(idx)
            if self._is_inline(attach):
                continue
            safe_name = _sanitize_filename(attach.FileName)
            dest_path = self._unique_path(dest_folder / safe_name)

            last_exc: Optional[Exception] = None
            for attempt in range(1, 4):
                try:
                    attach.SaveAsFile(str(dest_path))
                    saved.append(dest_path)
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc = exc
                    logger.warning(
                        f"download_attachment: tentativa {attempt}/3 falhou para "
                        f"'{safe_name}' — {exc}"
                    )
                    if attempt < 3:
                        time.sleep(1)

            if last_exc is not None:
                raise OutlookError(
                    f"Falha ao salvar '{safe_name}' após 3 tentativas: {last_exc}"
                ) from last_exc

            logger.debug(f"Anexo salvo: '{dest_path}'.")

        logger.info(f"E-mail '{entry_id}': {len(saved)} anexo(s) baixado(s) para '{dest_folder}'.")
        return saved

    # ------------------------------------------------------------------
    # Resposta
    # ------------------------------------------------------------------

    def create_reply_draft(self, entry_id: str, body: str) -> None:
        """Cria rascunho de resposta ao e-mail original (salvo em Rascunhos)."""
        try:
            item = self._ns.GetItemFromID(entry_id)
        except Exception as exc:
            raise OutlookError(f"Email '{entry_id}' não encontrado para rascunho.") from exc
        try:
            reply = item.Reply()
            reply.Subject = f"RES: {item.Subject}"
            reply.Body = body
            reply.Save()
            logger.info(f"Rascunho de resposta criado para o e-mail '{entry_id}'.")
        except Exception as exc:
            raise OutlookError(f"Falha ao criar rascunho para '{entry_id}': {exc}") from exc

    # ------------------------------------------------------------------
    # Privado — pastas
    # ------------------------------------------------------------------

    def _get_or_create_top_level_folder(self, name: str):
        """Retorna (criando se necessário) uma pasta de topo, irmã do Inbox na conta."""
        try:
            parent = self._ns.Folders(self._account)
        except Exception as exc:
            disponiveis = self._listar_contas_disponiveis()
            logger.error(
                f"Não foi possível acessar a conta/arquivo de dados '{self._account}' "
                f"(configurado em OUTLOOK_ACCOUNT) para localizar '{name}'. "
                f"Contas/arquivos de dados disponíveis neste perfil do Outlook: {disponiveis}. "
                "Verifique se OUTLOOK_ACCOUNT no .env bate exatamente com um desses nomes."
            )
            raise OutlookError(
                f"Não foi possível acessar a conta '{self._account}' para localizar '{name}'."
            ) from exc
        return self._get_or_create_subfolder(parent, name)

    def _listar_contas_disponiveis(self) -> list[str]:
        """Lista os nomes das contas/arquivos de dados de topo no perfil atual (para diagnóstico)."""
        try:
            return [self._ns.Folders.Item(i).Name for i in range(1, self._ns.Folders.Count + 1)]
        except Exception:
            return []

    def _get_or_create_subfolder(self, parent_folder, name: str):
        """Retorna subpasta pelo nome (case-insensitive), criando se não existir."""
        try:
            for i in range(1, parent_folder.Folders.Count + 1):
                folder = parent_folder.Folders.Item(i)
                if folder.Name.lower() == name.lower():
                    logger.debug(f"Pasta '{name}' encontrada em '{parent_folder.Name}'.")
                    return folder
        except Exception:
            pass
        try:
            logger.info(f"Pasta '{name}' não encontrada em '{parent_folder.Name}' — criando.")
            return parent_folder.Folders.Add(name)
        except Exception as exc:
            raise OutlookError(
                f"Não foi possível acessar/criar a pasta '{name}'. Detalhe: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Privado — build email
    # ------------------------------------------------------------------

    def _build_email(self, item) -> EmailMessage:
        attachments = self._build_attachments(item)

        body = ""
        try:
            body = item.Body or ""
        except Exception:
            pass

        return EmailMessage(
            entry_id=item.EntryID,
            subject=item.Subject or "",
            sender_name=item.SenderName or "",
            sender_email=item.SenderEmailAddress or "",
            body=body,
            received_at=_to_datetime(item.ReceivedTime),
            attachments=attachments,
            attachment_count=len([a for a in attachments if not a.is_inline]),
        )

    def _build_attachments(self, item) -> list[Attachment]:
        result: list[Attachment] = []
        try:
            attachments = item.Attachments
            for i in range(1, attachments.Count + 1):
                attach = attachments.Item(i)
                inline = self._is_inline(attach)
                name = attach.FileName or attach.DisplayName or f"attachment_{i}"
                ext = Path(name).suffix.lstrip(".").lower()
                size = 0
                try:
                    size = int(attach.Size)
                except Exception:
                    pass
                result.append(Attachment(
                    index=i,
                    file_name=name,
                    display_name=attach.DisplayName or name,
                    file_size=size,
                    file_type=ext,
                    is_inline=inline,
                ))
        except Exception:
            pass
        return result

    @staticmethod
    def _is_inline(attach) -> bool:
        try:
            flags = attach.PropertyAccessor.GetProperty(_PR_ATTACH_FLAGS)
            return int(flags) == 4  # ATT_MHTML_REF
        except Exception:
            return False

    @staticmethod
    def _unique_path(path: Path) -> Path:
        if not path.exists():
            return path
        stem, suffix, parent = path.stem, path.suffix, path.parent
        counter = 1
        while True:
            candidate = parent / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1
