"""Regra de negócio de filtro dos e-mails da pasta 'Detraf Despesas' (HU-01)."""

from src.config import configuration
from src.config.outlook_config import EmailMessage

PALAVRA_EXCLUSAO = "contestação"


class DetrafEmailFilterService:
    """Decide se um e-mail da pasta 'Detraf Despesas' deve ser capturado."""

    @staticmethod
    def deve_processar(email: EmailMessage) -> bool:
        """
        Um e-mail deve ser processado quando:
          - "CONTESTAÇÃO" (case-insensitive) não aparece no assunto nem no corpo; e
          - há pelo menos um anexo (não inline) com extensão Excel ou CSV.
        """
        texto = f"{email.subject}\n{email.body}".lower()
        if PALAVRA_EXCLUSAO in texto:
            return False

        extensoes_aceitas = {
            ext.lstrip(".") for ext in configuration.EXTENSOES_EXCEL | configuration.EXTENSOES_CSV
        }
        return any(
            not anexo.is_inline and anexo.file_type.lower() in extensoes_aceitas
            for anexo in email.attachments
        )
