from src.config.outlook_config import Attachment, EmailMessage
from src.services.email_filter_service import DetrafEmailFilterService


def _email(subject="", body="", attachments=None):
    attachments = attachments or []
    return EmailMessage(
        entry_id="1",
        subject=subject,
        sender_name="Remetente Teste",
        sender_email="teste@example.com",
        body=body,
        received_at=None,
        attachments=attachments,
        attachment_count=len([a for a in attachments if not a.is_inline]),
    )


def _anexo(file_type, is_inline=False):
    return Attachment(
        index=1,
        file_name=f"arquivo.{file_type}",
        display_name=f"arquivo.{file_type}",
        file_size=100,
        file_type=file_type,
        is_inline=is_inline,
    )


def test_email_valido_passa_no_filtro():
    email = _email(subject="Detraf mensal", body="segue detraf", attachments=[_anexo("xlsx")])

    assert DetrafEmailFilterService.deve_processar(email) is True


def test_contestacao_no_assunto_bloqueia():
    email = _email(subject="CONTESTAÇÃO detraf", body="", attachments=[_anexo("xlsx")])

    assert DetrafEmailFilterService.deve_processar(email) is False


def test_contestacao_no_corpo_bloqueia():
    email = _email(subject="Detraf", body="isso é uma contestação do valor", attachments=[_anexo("csv")])

    assert DetrafEmailFilterService.deve_processar(email) is False


def test_sem_anexo_valido_bloqueia():
    email = _email(subject="Detraf", body="segue anexo", attachments=[_anexo("pdf")])

    assert DetrafEmailFilterService.deve_processar(email) is False


def test_anexo_valido_apenas_inline_bloqueia():
    email = _email(subject="Detraf", body="", attachments=[_anexo("xlsx", is_inline=True)])

    assert DetrafEmailFilterService.deve_processar(email) is False


def test_sem_nenhum_anexo_bloqueia():
    email = _email(subject="Detraf", body="")

    assert DetrafEmailFilterService.deve_processar(email) is False
