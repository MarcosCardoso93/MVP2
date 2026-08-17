import sys
from pathlib import Path

# Reaproveita o modulo enviado (outlook_standalone_original.py) SEM MODIFICA-LO - import
# direto do arquivo original, que fica intacto nesta mesma pasta.
sys.path.insert(0, str(Path(__file__).parent))
from outlook_standalone_original import (  # noqa: E402
    OutlookService, OutlookConfig, OutlookError, EmailMessage,
    EmailFilterService, FileOrganizerService, logger,
)

"""
HU-15 - Envio do e-mail de contestação à operadora
=====================================================
O modulo outlook_standalone.py fornecido e 100% REAPROVEITADO (arquivo intacto em
outlook_standalone_original.py, sem nenhuma linha alterada) - toda a conexao COM com o
Outlook, tratamento de erro e retry ja vem pronta dele.

UNICA ADAPTACAO necessaria: o metodo OutlookService.send_email() do arquivo original NAO
suporta anexos (so aceita to/subject/body/cc). Como a HU-15 exige 2 anexos (carta +
arquivo _ENV), esta classe AQUI estende OutlookService (heranca, sem tocar no arquivo
original) e adiciona send_email_com_anexos().
"""


class OutlookServiceComAnexo(OutlookService):
    """Estende OutlookService (original, intacto) para enviar e-mail com anexos."""

    def send_email_com_anexos(
        self,
        to,
        subject: str,
        body: str,
        attachments: list | None = None,
        cc=None,
    ) -> None:
        """
        Mesma logica do OutlookService.send_email() original, com um unico acrescimo:
        anexa cada caminho de `attachments` ao e-mail antes de enviar (mail.Attachments.Add).
        """
        try:
            mail = self._app.CreateItem(0)  # olMailItem = 0 - identico ao metodo original
            mail.Subject = subject
            mail.Body = body
            mail.To = "; ".join(to) if isinstance(to, list) else to
            if cc:
                mail.CC = "; ".join(cc) if isinstance(cc, list) else cc

            for caminho in (attachments or []):
                caminho_str = str(caminho)
                if not Path(caminho_str).is_file():
                    raise OutlookError(f"Anexo nao encontrado: {caminho_str}")
                mail.Attachments.Add(caminho_str)

            mail.Send()
        except OutlookError:
            raise
        except Exception as exc:
            raise OutlookError(f"Falha ao enviar e-mail (com anexos) para '{to}': {exc}") from exc
