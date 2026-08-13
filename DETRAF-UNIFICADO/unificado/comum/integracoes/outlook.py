"""
Integração com o Outlook Desktop Classic via COM (pywin32) — base comum.

Requer Outlook instalado, com perfil configurado, em sessão Windows
interativa (COM não funciona em serviço headless).

---

## Origem

Havia **três** implementações de acesso ao Outlook no repositório:

1. ``rpa1_captura/src/services/outlook_service.py`` — leitura da caixa;
2. ``rpa2_.../services/notificacao_email.py`` — ``win32com.client.Dispatch``
   inline, para responder à operadora;
3. o ``outlook_standalone_original.py`` do Projeto 5 — **1.191 linhas
   replicando o Projeto 1 inteiro**, com o envio a mais.

Este módulo unifica as três. A base é a do RPA 1, porque é a aderente à V2: ela
navega por **pasta nomeada** (``fetch_emails_from_folder``), enquanto o
standalone do Projeto 5 usa o modelo antigo, inbox-cêntrico. Do Projeto 5 vieram
``send_email`` e ``send_email_com_anexos`` — a única contribuição de código nova
daquela camada, e justamente a peça que faltava aqui.

Ver ``trabalho/inventarios/inventario-projeto-5.md`` §3 e ``duplicacoes.md`` D-19.

## Consumidores

===  ==========================================================
RPA  Uso
===  ==========================================================
1    lê a caixa, move e-mails processados, baixa anexos
2    responde ao e-mail de origem quando o Detraf é inválido
3    envia a contestação à operadora, com carta e ``_EXP`` (HU-15)
===  ==========================================================

## Envio é irreversível

``send_email`` e ``send_email_com_anexos`` chamam ``Send()``: uma vez disparado,
não se desfaz. Quem chama é responsável por respeitar o kill-switch do seu fluxo
(``NOTIFICAR_OPERADORA_ENVIAR`` no RPA 2, ``PERMITIR_ENVIO_EMAIL`` no RPA 3).
Esta camada não decide isso — ela executa.
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import pythoncom
import win32com.client

from comum.config import configuration
from comum.config.logger_config import logger
from comum.integracoes.outlook_config import Attachment, EmailMessage

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
                f"[OUTLOOK] Não foi possível conectar (conta configurada em "
                f"OUTLOOK_ACCOUNT: '{account or '(vazia)'}').\n"
                f"  -> Confira se o Outlook Desktop Classic está instalado e "
                f"aberto — o 'Novo Outlook' do Windows 11 não expõe COM.\n"
                f"  -> Para homologar SEM Outlook, o RPA 1 aceita "
                f"`main.py --pasta-entrada CAMINHO`: ele pula a captura e "
                f"processa arquivos já em disco, exercitando HU-02 e HU-03."
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

    def fetch_emails_from_inbox(self) -> list[EmailMessage]:
        """
        Retorna e-mails da Caixa de Entrada **de verdade** da conta.

        Diferente de `fetch_emails_from_folder`: aqui a pasta é resolvida pelo
        `Store.GetDefaultFolder`, que não depende do nome de exibição — a Caixa
        de Entrada aparece como "Inbox" em algumas contas do mesmo perfil e
        "Caixa de Entrada" em outras, e um nome fixo casaria só uma das duas.
        """
        parent = self._ns.Folders(self._account)
        folder = parent.Store.GetDefaultFolder(6)  # olFolderInbox
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
                logger.warning(f"Item ignorado ao ler a Caixa de Entrada (não é um e-mail válido?): {exc}")
        logger.debug(
            f"Caixa de Entrada: {len(emails)} e-mail(s) lido(s), {ignorados} item(ns) ignorado(s)."
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
        """
        Baixa os anexos de Detraf de um e-mail para `dest_folder`.

        Só baixa anexos **não-inline** cuja extensão esteja em
        ``EXTENSOES_PERMITIDAS`` (csv/Excel). A V2 é explícita: *"baixar apenas
        os csv ou excel"*.

        O filtro por e-mail (``DetrafEmailFilterService``) garante apenas que
        existe **pelo menos um** anexo csv/Excel; sem este filtro por anexo, PDF,
        Word e imagens de assinatura eram baixados junto, ganhavam registro de
        rastreamento e acabavam copiados para a pasta de rede da operadora — onde
        o RPA 2 os ignora por extensão, mas onde não deveriam estar.
        """
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
        ignorados: list[str] = []

        for idx in range(1, total + 1):
            attach = attachments.Item(idx)
            if self._is_inline(attach):
                continue

            safe_name = _sanitize_filename(attach.FileName)

            if Path(safe_name).suffix.lower() not in configuration.EXTENSOES_PERMITIDAS:
                ignorados.append(safe_name)
                continue

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

        if ignorados:
            logger.info(
                f"E-mail '{entry_id}': {len(ignorados)} anexo(s) ignorado(s) por "
                f"extensão não permitida — {', '.join(ignorados)}"
            )

        logger.info(f"E-mail '{entry_id}': {len(saved)} anexo(s) baixado(s) para '{dest_folder}'.")
        return saved

    # ------------------------------------------------------------------
    # Resposta
    # ------------------------------------------------------------------

    def responder_email(self, entry_id: str, body: str, enviar: bool = False) -> None:
        """
        Responde ao e-mail original: envia (``enviar=True``) ou deixa em Rascunhos.

        O default é o rascunho porque ``Send()`` é irreversível — quem envia
        precisa dizer isso explicitamente, a partir do kill-switch do seu fluxo.

        Origem: o RPA 2 fazia ``win32com.client.Dispatch`` inline em
        ``notificacao_email.py`` só para chegar a este ``Reply()``.
        """
        try:
            item = self._ns.GetItemFromID(entry_id)
        except Exception as exc:
            raise OutlookError(f"Email '{entry_id}' não encontrado para resposta.") from exc
        try:
            reply = item.Reply()
            reply.Subject = f"RES: {item.Subject}"
            reply.Body = body
            if enviar:
                reply.Send()
            else:
                reply.Save()
        except Exception as exc:
            raise OutlookError(f"Falha ao responder o e-mail '{entry_id}': {exc}") from exc
        logger.info(
            f"Resposta {'enviada' if enviar else 'salva como rascunho'} "
            f"para o e-mail '{entry_id}'."
        )

    def create_reply_draft(self, entry_id: str, body: str) -> None:
        """Cria rascunho de resposta ao e-mail original (salvo em Rascunhos)."""
        self.responder_email(entry_id, body, enviar=False)

    # ------------------------------------------------------------------
    # Envio
    #
    # Origem: Projeto 5. O RPA 1 não enviava e-mail — só lia e respondia. Estes
    # dois métodos são a contribuição de código nova daquele projeto.
    #
    # ⚠️ IRREVERSÍVEL: `Send()` não se desfaz. Respeite o kill-switch do fluxo.
    # ------------------------------------------------------------------

    def send_email(
        self,
        to: list[str] | str,
        subject: str,
        body: str,
        cc: list[str] | None = None,
    ) -> None:
        """
        Envia um e-mail.

        Args:
            to: Destinatário, ou lista deles.
            subject: Assunto.
            body: Corpo, em texto puro.
            cc: Cópia, opcional.

        Raises:
            OutlookError: Se o envio falhar.
        """
        self.send_email_com_anexos(to=to, subject=subject, body=body, cc=cc)

    def send_email_com_anexos(
        self,
        to: list[str] | str,
        subject: str,
        body: str,
        anexos: list[Path] | list[str] | None = None,
        cc: list[str] | None = None,
    ) -> None:
        """
        Envia um e-mail com anexos.

        A HU-15 exige dois anexos obrigatórios — a carta de contestação e o
        arquivo ``_EXP``. No Projeto 5 isto era uma subclasse
        (``OutlookServiceComAnexo``) porque o ``send_email`` de lá não aceitava
        anexo; aqui os dois casos são o mesmo método, e ``send_email`` delega
        para cá com a lista vazia.

        Args:
            to: Destinatário, ou lista deles.
            subject: Assunto.
            body: Corpo, em texto puro.
            anexos: Caminhos dos arquivos a anexar.
            cc: Cópia, opcional.

        Raises:
            OutlookError: Se algum anexo não existir, ou se o envio falhar.
        """
        caminhos = [Path(caminho) for caminho in (anexos or [])]

        # Conferir antes de montar o e-mail: um anexo faltando precisa falhar
        # aqui, não depois de o rascunho já existir no Outlook.
        ausentes = [str(caminho) for caminho in caminhos if not caminho.is_file()]
        if ausentes:
            raise OutlookError(
                f"Anexo(s) não encontrado(s), e-mail não enviado: {', '.join(ausentes)}"
            )

        try:
            mail = self._app.CreateItem(0)  # olMailItem
            mail.Subject = subject
            mail.Body = body
            mail.To = "; ".join(to) if isinstance(to, list) else to
            if cc:
                mail.CC = "; ".join(cc) if isinstance(cc, list) else cc

            for caminho in caminhos:
                mail.Attachments.Add(str(caminho.resolve()))

            mail.Send()
        except OutlookError:
            raise
        except Exception as exc:
            raise OutlookError(f"Falha ao enviar e-mail para '{to}': {exc}") from exc

        logger.info(
            f"E-mail enviado para '{to}' — assunto '{subject}', "
            f"{len(caminhos)} anexo(s)."
        )

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

    def move_to_top_level_folder(self, entry_id: str, folder_name: str) -> None:
        """
        Move um e-mail para `folder_name` (pasta de topo, irmã do Inbox).

        Diferente de `move_to_subfolder`: aqui o destino **é** a pasta de topo,
        não uma subpasta dentro de outra — é o caminho inverso de
        `fetch_emails_from_folder`, usado para popular a pasta a partir da
        Caixa de Entrada.
        """
        try:
            item = self._ns.GetItemFromID(entry_id)
        except Exception as exc:
            raise OutlookError(f"Email '{entry_id}' não encontrado para mover.") from exc

        target = self._get_or_create_top_level_folder(folder_name)
        try:
            item.Move(target)
            logger.debug(f"E-mail '{entry_id}' movido para '{folder_name}'.")
        except Exception as exc:
            raise OutlookError(
                f"Falha ao mover email '{entry_id}' para '{folder_name}': {exc}"
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
        """
        Descreve os anexos de um e-mail.

        Uma falha aqui devolve a lista **parcial** — o COM pode falhar num anexo
        e não nos outros. Isso é aceitável, mas não pode ser silencioso: até
        2026-08-04 os dois ``except`` eram ``pass``, e um anexo que sumisse dessa
        lista nunca seria baixado nem apareceria em lugar algum. O e-mail seria
        dado por processado sem ele.
        """
        result: list[Attachment] = []
        total = 0
        try:
            attachments = item.Attachments
            total = attachments.Count
            for i in range(1, total + 1):
                attach = attachments.Item(i)
                inline = self._is_inline(attach)
                name = attach.FileName or attach.DisplayName or f"attachment_{i}"
                ext = Path(name).suffix.lstrip(".").lower()
                size = 0
                try:
                    size = int(attach.Size)
                except Exception as exc:
                    logger.warning(f"Tamanho do anexo '{name}' indisponível: {exc}")
                result.append(Attachment(
                    index=i,
                    file_name=name,
                    display_name=attach.DisplayName or name,
                    file_size=size,
                    file_type=ext,
                    is_inline=inline,
                ))
        except Exception as exc:
            logger.excecao(
                f"Falha ao enumerar os anexos do e-mail: {exc}. "
                f"{len(result)} de {total or '?'} anexo(s) descrito(s) — os "
                f"demais NÃO serão vistos por este robô."
            )
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
