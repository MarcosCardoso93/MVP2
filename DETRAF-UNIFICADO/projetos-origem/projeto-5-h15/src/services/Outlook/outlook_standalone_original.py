"""
outlook_standalone.py — Módulo autossuficiente de integração Outlook via COM.

Contém toda a lógica de:
  - Conexão e verificação do Outlook
  - Leitura e filtro de e-mails
  - Criação/verificação de pastas no Outlook
  - Download de anexos
  - Organização de arquivos locais
  - Fila de processamento com retry

Uso em outro robô:
    from outlook_standalone import OutlookConfig, run_outlook_pipeline

    config = OutlookConfig(
        account="meu@email.com",
        root_folder="MEU-RPA",
        keyword_pattern=r"minha.*keyword",
    )

    def meu_processador(email, pasta_local, anexos):
        # sua lógica de negócio aqui
        print(f"Processando: {email.subject}")
        for anexo in anexos:
            print(f"  Anexo: {anexo}")

    run_outlook_pipeline(config, meu_processador)

Dependências:
    pip install pywin32
    python Scripts/pywin32_postinstall.py -install  (apenas em venv)

    O Outlook deve estar instalado e com perfil configurado na máquina.
"""

# ---------------------------------------------------------------------------
# Imports — apenas stdlib + pywin32
# ---------------------------------------------------------------------------

import json
import logging
import os
import re
import shutil
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

import pythoncom
import win32com.client

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

logger = logging.getLogger("outlook_standalone")

if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass
class Attachment:
    """Representa um anexo de e-mail."""
    index: int          # posição ordinal no COM (base 1)
    file_name: str
    display_name: str
    file_size: int      # bytes
    file_type: str      # extensão sem ponto, ex: "pdf"
    is_inline: bool     # True = imagem embutida no corpo HTML


@dataclass
class EmailMessage:
    """Representa um e-mail lido do Outlook com seus metadados."""
    entry_id: str
    subject: str
    sender_name: str
    sender_email: str
    recipients: list[str]
    body: str
    body_html: str
    received_at: datetime | None
    sent_at: datetime | None
    attachments: list[Attachment]
    attachment_count: int
    importance: str         # "Low" | "Normal" | "High"
    is_read: bool
    categories: list[str]
    conversation_id: str
    message_size: int       # bytes; 0 se indisponível


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

def _load_env_file(path: Path) -> dict[str, str]:
    """Lê arquivo .env e retorna dict de variáveis."""
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        result[key] = value
    return result


def _env_get(env: dict[str, str], key: str, default: str = "") -> str:
    return os.environ.get(key) or env.get(key) or default


def _env_int(env: dict[str, str], key: str, default: int | None) -> int | None:
    raw = _env_get(env, key, "")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class OutlookConfig:
    """
    Configuração do pipeline Outlook.

    Pode ser criada diretamente ou carregada de variáveis de ambiente / .env.

    Parâmetros:
        account:          Nome da conta Outlook (email). Vazio = perfil padrão.
        inbox_folder:     Nome da pasta Inbox. Vazio = inbox padrão.
        root_folder:      Pasta-raiz criada no Outlook para este robô.
                          Irmã do Inbox na conta (Exchange) ou dentro do Inbox.
        em_processamento: Subpasta de fila de trabalho (dentro de root_folder).
        processados:      Subpasta de concluídos (dentro de root_folder).
        erro:             Subpasta de erros (dentro de root_folder).
        max_emails:       Limite de emails lidos do inbox. None = sem limite.
        keyword_pattern:  Regex para filtrar emails relevantes (assunto + corpo).
        dest_root:        Pasta local onde baixar os anexos de cada email.
        max_retry:        Tentativas de processamento por email antes de mover p/ erro.
    """
    account: str = ""
    inbox_folder: str = ""
    root_folder: str = "MEU-RPA"
    em_processamento: str = "1 - EM PROCESSAMENTO"
    processados: str = "2 - PROCESSAMENTO FINALIZADO"
    erro: str = "3 - ERRO NO PROCESSAMENTO"
    max_emails: int | None = None
    keyword_pattern: str = r".*"        # default: todos os emails
    dest_root: Path = field(default_factory=lambda: Path(tempfile.gettempdir()) / "rpa_emails")
    max_retry: int = 3

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "OutlookConfig":
        """Carrega configuração de variáveis de ambiente ou .env."""
        env_path = env_file or Path(".env")
        env = _load_env_file(env_path)
        return cls(
            account=_env_get(env, "OUTLOOK_ACCOUNT", ""),
            inbox_folder=_env_get(env, "OUTLOOK_INBOX_FOLDER", ""),
            root_folder=_env_get(env, "OUTLOOK_ROOT_FOLDER", "MEU-RPA"),
            em_processamento=_env_get(env, "OUTLOOK_EM_PROCESSAMENTO", "1 - EM PROCESSAMENTO"),
            processados=_env_get(env, "OUTLOOK_PROCESSADOS", "2 - PROCESSAMENTO FINALIZADO"),
            erro=_env_get(env, "OUTLOOK_ERRO", "3 - ERRO NO PROCESSAMENTO"),
            max_emails=_env_int(env, "OUTLOOK_MAX_EMAILS", None),
            keyword_pattern=_env_get(env, "OUTLOOK_KEYWORD_PATTERN", r".*"),
            dest_root=Path(_env_get(env, "OUTLOOK_DEST_ROOT", str(Path(tempfile.gettempdir()) / "rpa_emails"))),
            max_retry=int(_env_get(env, "OUTLOOK_MAX_RETRY", "3")),
        )


# ---------------------------------------------------------------------------
# Constantes Outlook COM
# ---------------------------------------------------------------------------

_OL_DEFAULT_INBOX = 6
_IMPORTANCE_MAP = {0: "Low", 1: "Normal", 2: "High"}
_PR_ATTACH_FLAGS = "http://schemas.microsoft.com/mapi/proptag/0x37140003"
_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')
_INVALID_DIR_CHARS = re.compile(r'[\\/:*?"<>|]')


def _sanitize_filename(name: str) -> str:
    return _INVALID_FILENAME_CHARS.sub("_", name)


def _safe_dir_name(entry_id: str) -> str:
    """Converte entry_id em nome de diretório seguro (últimos 80 chars)."""
    safe = _INVALID_DIR_CHARS.sub("_", entry_id)
    return safe[-80:] if len(safe) > 80 else safe


def _to_datetime(com_dt) -> datetime | None:
    """Converte pywintypes.datetime para datetime stdlib."""
    if com_dt is None:
        return None
    try:
        return datetime(
            com_dt.year, com_dt.month, com_dt.day,
            com_dt.hour, com_dt.minute, com_dt.second,
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# OutlookError
# ---------------------------------------------------------------------------

class OutlookError(RuntimeError):
    """Exceção base para erros do OutlookService."""


# ---------------------------------------------------------------------------
# OutlookService
# ---------------------------------------------------------------------------

class OutlookService:
    """
    Interface com o Outlook Desktop via COM (win32com).

    Gerencia conexão, leitura, movimentação de e-mails e download de anexos.
    Requer Outlook instalado com perfil configurado na máquina.
    """

    def __init__(self, config: OutlookConfig) -> None:
        self._cfg = config
        pythoncom.CoInitialize()
        try:
            self._app = win32com.client.Dispatch("Outlook.Application")
            self._ns = self._app.GetNamespace("MAPI")
        except Exception as exc:
            raise OutlookError(
                "Não foi possível conectar ao Outlook. "
                "Verifique se ele está instalado e aberto com perfil configurado."
            ) from exc

    # ------------------------------------------------------------------
    # Leitura de emails
    # ------------------------------------------------------------------

    def fetch_emails(self, max_items: int | None = None) -> list[EmailMessage]:
        """Retorna emails da caixa de entrada (mais recentes primeiro)."""
        inbox = self._get_inbox_folder()
        items = inbox.Items
        items.Sort("[ReceivedTime]", True)

        emails: list[EmailMessage] = []
        count = 0
        for item in items:
            if max_items is not None and count >= max_items:
                break
            try:
                if item.Class != 43:  # olMailItem = 43
                    continue
                emails.append(self._build_email(item))
                count += 1
            except Exception:
                continue
        return emails

    def fetch_emails_from_subfolder(
        self,
        subfolder_name: str,
        max_items: int | None = None,
    ) -> list[EmailMessage]:
        """Retorna e-mails de uma subpasta dentro da pasta-raiz do robô."""
        root = self._get_root_folder()
        folder = self._get_or_create_subfolder(root, subfolder_name)
        items = folder.Items
        items.Sort("[ReceivedTime]", True)

        emails: list[EmailMessage] = []
        count = 0
        for item in items:
            if max_items is not None and count >= max_items:
                break
            try:
                if item.Class != 43:
                    continue
                emails.append(self._build_email(item))
                count += 1
            except Exception:
                continue
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

    def move_to_folder(self, entry_id: str, folder_name: str) -> None:
        """
        Move e-mail para subpasta dentro da pasta-raiz do robô.
        Cria a pasta se não existir.
        """
        try:
            item = self._ns.GetItemFromID(entry_id)
        except Exception as exc:
            raise OutlookError(f"Email '{entry_id}' não encontrado para mover.") from exc

        root = self._get_root_folder()
        target = self._get_or_create_subfolder(root, folder_name)
        try:
            item.Move(target)
        except Exception as exc:
            raise OutlookError(
                f"Falha ao mover email '{entry_id}' para '{folder_name}': {exc}"
            ) from exc

    def move_back_to_inbox(self, entry_id: str) -> None:
        """Move e-mail de volta para o Inbox (usado para reset/reprocessamento)."""
        try:
            item = self._ns.GetItemFromID(entry_id)
        except Exception as exc:
            raise OutlookError(f"Email '{entry_id}' não encontrado para reset.") from exc

        inbox = self._get_inbox_folder()
        try:
            item.Move(inbox)
        except Exception as exc:
            raise OutlookError(
                f"Falha ao mover email '{entry_id}' de volta para Inbox: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Download de anexos
    # ------------------------------------------------------------------

    def download_attachments(
        self,
        entry_id: str,
        attachment_index: int | None = None,
        dest_folder: Path | None = None,
    ) -> list[Path]:
        """
        Baixa anexos de um email.

        Args:
            entry_id:          EntryID do email.
            attachment_index:  Índice do anexo (base 1). None = todos.
            dest_folder:       Pasta de destino. None = tempdir/rpa.

        Returns:
            Lista com os caminhos dos arquivos salvos.
        """
        dest = dest_folder or Path(tempfile.gettempdir()) / "rpa_attachments"
        dest.mkdir(parents=True, exist_ok=True)

        try:
            item = self._ns.GetItemFromID(entry_id)
        except Exception as exc:
            raise OutlookError(f"Email '{entry_id}' não encontrado.") from exc

        attachments = item.Attachments
        total = attachments.Count
        if total == 0:
            return []

        if attachment_index is not None:
            if attachment_index < 1 or attachment_index > total:
                raise OutlookError(
                    f"Índice de anexo inválido: {attachment_index}. Email tem {total} anexo(s)."
                )
            indices = [attachment_index]
        else:
            indices = list(range(1, total + 1))

        saved: list[Path] = []
        for idx in indices:
            attach = attachments.Item(idx)
            if self._is_inline(attach):
                continue
            safe_name = _sanitize_filename(attach.FileName)
            dest_path = self._unique_path(dest / safe_name)

            last_exc: Exception | None = None
            for attempt in range(1, 4):
                try:
                    attach.SaveAsFile(str(dest_path))
                    saved.append(dest_path)
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc = exc
                    logger.warning(
                        "download_attachment: tentativa %d/3 falhou para '%s' — %s",
                        attempt, safe_name, exc,
                    )
                    if attempt < 3:
                        time.sleep(1)

            if last_exc is not None:
                raise OutlookError(
                    f"Falha ao salvar '{safe_name}' após 3 tentativas: {last_exc}"
                ) from last_exc

        return saved

    # ------------------------------------------------------------------
    # Envio / rascunho
    # ------------------------------------------------------------------

    def send_email(
        self,
        to: list[str] | str,
        subject: str,
        body: str,
        cc: list[str] | None = None,
    ) -> None:
        """Envia e-mail via Outlook COM."""
        try:
            mail = self._app.CreateItem(0)  # olMailItem = 0
            mail.Subject = subject
            mail.Body = body
            mail.To = "; ".join(to) if isinstance(to, list) else to
            if cc:
                mail.CC = "; ".join(cc) if isinstance(cc, list) else cc
            mail.Send()
        except Exception as exc:
            raise OutlookError(f"Falha ao enviar e-mail para '{to}': {exc}") from exc

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
        except Exception as exc:
            raise OutlookError(f"Falha ao criar rascunho para '{entry_id}': {exc}") from exc

    # ------------------------------------------------------------------
    # Privado — pastas
    # ------------------------------------------------------------------

    def _get_inbox_folder(self):
        account = self._cfg.account.strip()
        folder = (self._cfg.inbox_folder or "Inbox").strip()
        try:
            if account:
                return self._ns.Folders(account).Folders(folder)
            return self._ns.GetDefaultFolder(_OL_DEFAULT_INBOX)
        except Exception as exc:
            label = f"{account}/{folder}" if account else "caixa padrão"
            raise OutlookError(f"Não foi possível acessar Inbox ({label}).") from exc

    def _get_root_folder(self):
        """
        Retorna (criando se necessário) a pasta-raiz do robô.

        Com conta: cria como irmã do Inbox na conta (Exchange não permite
        subpastas dentro do Inbox via COM).
        Sem conta: cria dentro do Inbox padrão.

        Estrutura com conta:
            [conta]/
            ├── Inbox
            └── [root_folder]/          ← aqui
                ├── 1 - EM PROCESSAMENTO
                ├── 2 - PROCESSAMENTO FINALIZADO
                └── 3 - ERRO NO PROCESSAMENTO
        """
        root_name = self._cfg.root_folder or "MEU-RPA"
        account = self._cfg.account.strip()
        try:
            parent = self._ns.Folders(account) if account else self._get_inbox_folder()
        except Exception as exc:
            raise OutlookError(
                f"Não foi possível acessar raiz para criar '{root_name}'."
            ) from exc
        return self._get_or_create_subfolder(parent, root_name)

    def _get_or_create_subfolder(self, parent_folder, name: str):
        """Retorna subpasta pelo nome (case-insensitive), criando se não existir."""
        try:
            for i in range(1, parent_folder.Folders.Count + 1):
                folder = parent_folder.Folders.Item(i)
                if folder.Name.lower() == name.lower():
                    return folder
        except Exception:
            pass
        try:
            return parent_folder.Folders.Add(name)
        except Exception as exc:
            raise OutlookError(
                f"Não foi possível criar a pasta '{name}'. "
                f"Se fora da rede corporativa, crie as pastas manualmente no Outlook. "
                f"Detalhe: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Privado — build email
    # ------------------------------------------------------------------

    def _build_email(self, item) -> EmailMessage:
        attachments = self._build_attachments(item)

        recipients: list[str] = []
        try:
            for i in range(1, item.Recipients.Count + 1):
                r = item.Recipients.Item(i)
                recipients.append(r.Address or r.Name)
        except Exception:
            pass

        categories: list[str] = []
        try:
            raw = item.Categories or ""
            categories = [c.strip() for c in raw.split(";") if c.strip()]
        except Exception:
            pass

        importance = _IMPORTANCE_MAP.get(getattr(item, "Importance", 1), "Normal")

        body_html = ""
        try:
            body_html = item.HTMLBody or ""
        except Exception:
            pass

        body = ""
        try:
            body = item.Body or ""
        except Exception:
            pass

        message_size = 0
        try:
            message_size = int(item.Size)
        except Exception:
            pass

        conversation_id = ""
        try:
            conversation_id = item.ConversationID or ""
        except Exception:
            pass

        return EmailMessage(
            entry_id=item.EntryID,
            subject=item.Subject or "",
            sender_name=item.SenderName or "",
            sender_email=item.SenderEmailAddress or "",
            recipients=recipients,
            body=body,
            body_html=body_html,
            received_at=_to_datetime(item.ReceivedTime),
            sent_at=_to_datetime(item.SentOn),
            attachments=attachments,
            attachment_count=len([a for a in attachments if not a.is_inline]),
            importance=importance,
            is_read=bool(item.UnRead is False),
            categories=categories,
            conversation_id=conversation_id,
            message_size=message_size,
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


# ---------------------------------------------------------------------------
# EmailFilterService
# ---------------------------------------------------------------------------

class EmailFilterService:
    """
    Filtra e-mails por keyword (regex configurável).

    Por padrão aceita qualquer email. Para filtrar por assunto/corpo,
    passe um padrão regex no construtor.

    Exemplo:
        svc = EmailFilterService(r"contesta[çc][aã]o")
    """

    def __init__(self, keyword_pattern: str = r".*") -> None:
        self._re = re.compile(keyword_pattern, re.IGNORECASE | re.UNICODE)

    def is_match(self, email: EmailMessage) -> bool:
        """True se o padrão é encontrado no assunto ou corpo do e-mail."""
        return bool(
            self._re.search(email.subject)
            or self._re.search(email.body)
        )

    def filter(self, emails: list[EmailMessage]) -> list[EmailMessage]:
        """Retorna apenas os emails que batem com o padrão."""
        return [e for e in emails if self.is_match(e)]


# ---------------------------------------------------------------------------
# FileOrganizerService
# ---------------------------------------------------------------------------

class FileOrganizerService:
    """Organiza arquivos locais: extrai ZIPs, salva metadados, limpa temporários."""

    def save_metadata(self, email: EmailMessage, email_dir: Path) -> None:
        """Salva metadados do e-mail como metadata.json dentro de email_dir."""
        meta = {
            "entry_id": email.entry_id,
            "subject": email.subject,
            "sender_name": email.sender_name,
            "sender_email": email.sender_email,
            "recipients": email.recipients,
            "body": (email.body or "")[:2000],
            "received_at": email.received_at.isoformat() if email.received_at else None,
            "sent_at": email.sent_at.isoformat() if email.sent_at else None,
            "attachment_count": email.attachment_count,
            "importance": email.importance,
        }
        path = email_dir / "metadata.json"
        try:
            path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.error(f"save_metadata: falha ao escrever {path}: {exc}")

    def extract_archives(self, paths: list[Path]) -> list[Path]:
        """
        Extrai ZIPs para subpasta 'extracted/' no mesmo diretório.

        Arquivos não-ZIP são retornados sem alteração.
        ZIPs extraídos são substituídos pelo seu conteúdo na lista.
        """
        result: list[Path] = []
        for path in paths:
            if path.suffix.lower() != ".zip":
                result.append(path)
                continue

            if not path.exists():
                logger.error(f"extract_archives: ZIP não encontrado: {path}")
                continue

            extract_dir = path.parent / "extracted"
            try:
                extract_dir.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                logger.error(f"extract_archives: falha ao criar pasta: {exc}")
                result.append(path)
                continue

            _RETRY = 3
            last_exc: Exception | None = None
            extracted_ok = False
            for attempt in range(1, _RETRY + 1):
                try:
                    with zipfile.ZipFile(path, "r") as zf:
                        zf.extractall(extract_dir)
                    extracted_ok = True
                    break
                except zipfile.BadZipFile as exc:
                    logger.error(f"extract_archives: ZIP corrompido ({path.name}): {exc}")
                    last_exc = exc
                    break
                except Exception as exc:
                    last_exc = exc
                    logger.warning(
                        "extract_archives: tentativa %d/%d falhou ao extrair %s — %s",
                        attempt, _RETRY, path.name, exc,
                    )
                    if attempt < _RETRY:
                        time.sleep(1)

            if extracted_ok:
                extracted_files = [f for f in extract_dir.rglob("*") if f.is_file()]
                result.extend(extracted_files)
            else:
                logger.error(
                    "extract_archives: falha definitiva extraindo %s — %s",
                    path.name, last_exc,
                )
                result.append(path)

        return result

    def flatten_to_root(self, email_dir: Path, keep: list[Path]) -> list[Path]:
        """
        Move arquivos relevantes para raiz de email_dir e remove o resto.

        Args:
            email_dir: pasta raiz do e-mail.
            keep:      arquivos a preservar (movidos para raiz se em subpasta).

        Returns:
            Novos paths após flatten.
        """
        new_paths: list[Path] = []
        for src in keep:
            if not src.exists():
                continue
            natural_dest = email_dir / src.name
            if src.resolve() == natural_dest.resolve():
                new_paths.append(src)
            else:
                dest = self._unique_path(natural_dest)
                shutil.move(str(src), str(dest))
                new_paths.append(dest)

        preserved = {p.resolve() for p in new_paths}
        preserved.add((email_dir / "metadata.json").resolve())

        for item in list(email_dir.iterdir()):
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            elif item.resolve() not in preserved:
                try:
                    item.unlink()
                except Exception as exc:
                    logger.warning(f"flatten_to_root: falha ao remover {item.name}: {exc}")

        return new_paths

    def cleanup(self, email_dir: Path) -> None:
        """Remove pasta local do e-mail (sempre temporária)."""
        if email_dir.exists():
            shutil.rmtree(email_dir, ignore_errors=True)

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


# ---------------------------------------------------------------------------
# ProcessorFn type alias
# ---------------------------------------------------------------------------

ProcessorFn = Callable[[EmailMessage, Path, list[Path]], None]


# ---------------------------------------------------------------------------
# SkipProcessing
# ---------------------------------------------------------------------------

class SkipProcessing(Exception):
    """
    Lançada pelo processador para manter o e-mail em EM PROCESSAMENTO
    sem retry e sem mover para erro.

    Útil quando o processamento deve ser adiado por decisão de negócio.
    """


# ---------------------------------------------------------------------------
# ProcessingQueueService
# ---------------------------------------------------------------------------

class ProcessingQueueService:
    """
    Gerencia fila de e-mails com retry.

    Fonte de verdade = pasta EM PROCESSAMENTO no Outlook.
    Dados locais são sempre temporários (baixados novamente a cada tentativa).
    """

    def __init__(
        self,
        outlook: OutlookService,
        organizer: FileOrganizerService,
        config: OutlookConfig,
    ) -> None:
        self._outlook = outlook
        self._organizer = organizer
        self._cfg = config

    def get_pending(self) -> list[EmailMessage]:
        """Retorna e-mails pendentes na pasta EM PROCESSAMENTO."""
        return self._outlook.fetch_emails_from_subfolder(self._cfg.em_processamento)

    def process_all(
        self,
        emails: list[EmailMessage],
        processor_fn: ProcessorFn,
    ) -> dict[str, bool]:
        """
        Processa lista de e-mails com retry.

        Cria dest_root/emailN/ para cada e-mail e salva metadata.json
        antes do processamento.

        Args:
            emails:       lista de EmailMessage a processar.
            processor_fn: callback(email, pasta_local, lista_anexos) — sua lógica.

        Returns:
            {entry_id: True = sucesso, False = falha definitiva}
        """
        dest_root = self._cfg.dest_root
        dest_root.mkdir(parents=True, exist_ok=True)

        results: dict[str, bool] = {}
        for i, email in enumerate(emails, 1):
            email_dir = dest_root / f"email{i}"
            email_dir.mkdir(parents=True, exist_ok=True)
            self._organizer.save_metadata(email, email_dir)
            results[email.entry_id] = self._process_one(email, email_dir, processor_fn)
        return results

    def _process_one(
        self,
        email: EmailMessage,
        email_dir: Path,
        processor_fn: ProcessorFn,
    ) -> bool:
        entry_id = email.entry_id
        last_exc: Exception | None = None

        for attempt in range(1, self._cfg.max_retry + 1):
            success = False
            try:
                local_attachments = self._download_to_dir(entry_id, email_dir)
                processor_fn(email, email_dir, local_attachments)
                success = True
            except SkipProcessing as exc:
                logger.info(f"entry_id={entry_id} skip: {exc}")
                return None  # type: ignore[return-value]
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "entry_id=%s attempt=%d/%d error=%s: %s",
                    entry_id, attempt, self._cfg.max_retry, type(exc).__name__, exc,
                )

            if success:
                logger.info("entry_id=%s status=ok", entry_id)
                return True

        logger.error(
            "entry_id=%s status=failed attempts=%d last_error=%s moving_to=%s",
            entry_id, self._cfg.max_retry, last_exc, self._cfg.erro,
        )
        try:
            self._outlook.move_to_folder(entry_id, self._cfg.erro)
        except OutlookError as exc:
            logger.error("entry_id=%s move_failed error=%s", entry_id, exc)

        return False

    def _download_to_dir(self, entry_id: str, email_dir: Path) -> list[Path]:
        """
        Baixa anexos para email_dir.

        Se já existirem arquivos locais (execução anterior interrompida),
        reutiliza sem re-download.
        """
        existentes = [
            f for f in email_dir.rglob("*")
            if f.is_file() and f.name != "metadata.json"
        ]
        if existentes:
            logger.info(
                "Local: %d arquivo(s) já presentes em %s — pulando download",
                len(existentes), email_dir.name,
            )
            return existentes
        return self._outlook.download_attachments(
            entry_id=entry_id,
            dest_folder=email_dir,
        )


# ---------------------------------------------------------------------------
# InboxController
# ---------------------------------------------------------------------------

class InboxController:
    """Filtra e-mails do inbox e move para fila EM PROCESSAMENTO."""

    def __init__(
        self,
        outlook: OutlookService,
        filter_svc: EmailFilterService,
        config: OutlookConfig,
    ) -> None:
        self._outlook = outlook
        self._filter = filter_svc
        self._cfg = config

    def filter_and_enqueue(
        self,
        emails: list[EmailMessage],
    ) -> tuple[list[EmailMessage], dict[str, str]]:
        """
        Filtra emails por keyword e move para EM PROCESSAMENTO.

        Move cada e-mail ANTES de download — Outlook é fonte de verdade.

        Returns:
            (enqueued, errors)
            enqueued — emails movidos com sucesso
            errors   — {entry_id: mensagem_de_erro}
        """
        filtered = self._filter.filter(emails)
        enqueued: list[EmailMessage] = []
        errors: dict[str, str] = {}

        for email in filtered:
            try:
                self._outlook.move_to_folder(email.entry_id, self._cfg.em_processamento)
                enqueued.append(email)
            except OutlookError as exc:
                errors[email.entry_id] = str(exc)

        return enqueued, errors


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def _connect_with_retry(config: OutlookConfig, attempts: int = 3, delay: float = 5.0) -> OutlookService:
    """Conecta ao Outlook com retry. Lança OutlookError se todas tentativas falharem."""
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            svc = OutlookService(config)
            logger.info("Outlook conectado (tentativa %d/%d)", attempt, attempts)
            return svc
        except OutlookError as exc:
            last_exc = exc
            logger.warning(
                "Falha ao conectar ao Outlook (tentativa %d/%d): %s",
                attempt, attempts, exc,
            )
            if attempt < attempts:
                time.sleep(delay)
    raise OutlookError(
        f"Não foi possível conectar ao Outlook após {attempts} tentativas. "
        f"Último erro: {last_exc}"
    )


def run_outlook_pipeline(
    config: OutlookConfig,
    processor_fn: ProcessorFn,
) -> dict[str, bool]:
    """
    Executa o pipeline completo de coleta Outlook.

    Fluxo:
        1. Conecta ao Outlook (retry 3x, 5s entre tentativas)
        2. Verifica emails pendentes em EM PROCESSAMENTO (execuções anteriores)
        3. Busca emails do inbox e filtra por keyword
        4. Move emails filtrados para EM PROCESSAMENTO
        5. Para cada email: baixa anexos, chama processor_fn
        6. Falha após max_retry → move para pasta de erro

    Args:
        config:        Configuração do pipeline.
        processor_fn:  Callback com assinatura:
                           processor_fn(email: EmailMessage, pasta: Path, anexos: list[Path]) -> None
                       Lançar SkipProcessing → mantém em fila sem retry.
                       Lançar qualquer outra exceção → aciona retry.

    Returns:
        {entry_id: True = processado com sucesso, False = falha definitiva}
    """
    logger.info("=== Pipeline Outlook iniciado ===")
    logger.info("Conta: %s | Pasta raiz: %s", config.account or "(padrão)", config.root_folder)
    logger.info("Keyword pattern: %s", config.keyword_pattern)
    logger.info("Destino local: %s", config.dest_root)

    # 1. Conectar
    outlook = _connect_with_retry(config)
    organizer = FileOrganizerService()
    filter_svc = EmailFilterService(config.keyword_pattern)
    inbox_ctrl = InboxController(outlook, filter_svc, config)
    queue_svc = ProcessingQueueService(outlook, organizer, config)

    # 2. Verificar emails já em processamento (execuções anteriores interrompidas)
    pendentes = queue_svc.get_pending()
    logger.info("Emails pendentes em '%s': %d", config.em_processamento, len(pendentes))

    # 3. Buscar inbox e filtrar (só se não há pendentes)
    if not pendentes:
        logger.info("Buscando emails do inbox...")
        todos = outlook.fetch_emails(max_items=config.max_emails)
        logger.info("Emails no inbox: %d", len(todos))

        enqueued, errors = inbox_ctrl.filter_and_enqueue(todos)
        logger.info(
            "Filtrados e movidos para EM PROCESSAMENTO: %d | Erros: %d",
            len(enqueued), len(errors),
        )
        for eid, err in errors.items():
            logger.error("Falha ao mover %s: %s", eid, err)

        pendentes = queue_svc.get_pending()
        logger.info("Total a processar: %d", len(pendentes))

    if not pendentes:
        logger.info("Nenhum email para processar. Pipeline encerrado.")
        return {}

    # 4. Processar fila
    logger.info("Iniciando processamento de %d email(s)...", len(pendentes))
    resultados = queue_svc.process_all(pendentes, processor_fn)

    sucesso = sum(1 for v in resultados.values() if v is True)
    falha = sum(1 for v in resultados.values() if v is False)
    skip = sum(1 for v in resultados.values() if v is None)

    logger.info(
        "=== Pipeline finalizado === sucesso=%d falha=%d skip=%d",
        sucesso, falha, skip,
    )
    return resultados


def run_reset(config: OutlookConfig) -> int:
    """
    Devolve todos os e-mails das pastas do robô de volta para o Inbox.

    Útil para reprocessar tudo do zero.

    Returns:
        Número de emails devolvidos ao inbox.
    """
    logger.info("=== Reset: devolvendo emails para Inbox ===")
    outlook = _connect_with_retry(config)
    total = 0

    for folder_name in [config.em_processamento, config.processados, config.erro]:
        try:
            emails = outlook.fetch_emails_from_subfolder(folder_name)
            for email in emails:
                try:
                    outlook.move_back_to_inbox(email.entry_id)
                    total += 1
                    logger.info("Devolvido ao inbox: %s", email.subject[:60])
                except OutlookError as exc:
                    logger.error("Falha ao devolver %s: %s", email.entry_id, exc)
        except OutlookError as exc:
            logger.warning("Pasta '%s' inacessível: %s", folder_name, exc)

    logger.info("=== Reset concluído: %d email(s) devolvido(s) ===", total)
    return total


# ---------------------------------------------------------------------------
# Exemplo de uso
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="Pipeline Outlook standalone")
    parser.add_argument("--reset", action="store_true", help="Devolver emails ao inbox")
    parser.add_argument("--env", default=".env", help="Caminho do arquivo .env")
    args = parser.parse_args()

    # --- Configure via .env ou direto no código ---
    config = OutlookConfig.from_env(Path(args.env))

    # Ou configure direto:
    # config = OutlookConfig(
    #     account="meu@email.com",
    #     root_folder="MEU-RPA",
    #     em_processamento="1 - EM PROCESSAMENTO",
    #     processados="2 - PROCESSADO",
    #     erro="3 - ERRO",
    #     keyword_pattern=r"minha.*palavra",
    #     dest_root=Path("C:/rpa/emails"),
    # )

    if args.reset:
        n = run_reset(config)
        print(f"Reset: {n} email(s) devolvido(s) ao inbox.")
        sys.exit(0)

    # --- Defina seu processador aqui ---
    def meu_processador(email: EmailMessage, pasta: Path, anexos: list[Path]) -> None:
        """
        Coloque aqui a lógica de negócio do seu robô.

        Args:
            email:  Dados do e-mail (subject, sender_email, body, etc.)
            pasta:  Pasta local onde os anexos foram baixados + metadata.json
            anexos: Lista de paths dos arquivos baixados
        """
        print(f"\n[EMAIL] {email.subject}")
        print(f"  De: {email.sender_email}")
        print(f"  Recebido: {email.received_at}")
        print(f"  Pasta local: {pasta}")
        print(f"  Anexos ({len(anexos)}):")
        for a in anexos:
            print(f"    - {a.name} ({a.stat().st_size} bytes)")

        # Exemplo: extrair ZIPs automaticamente
        org = FileOrganizerService()
        todos_arquivos = org.extract_archives(anexos)
        print(f"  Arquivos após extração: {[f.name for f in todos_arquivos]}")

        # Sua lógica de negócio aqui...
        # raise SkipProcessing("Aguardando aprovação")  # mantém em fila sem retry
        # raise Exception("Erro de negócio")            # aciona retry

    resultados = run_outlook_pipeline(config, meu_processador)
    print(f"\nResultados: {resultados}")
