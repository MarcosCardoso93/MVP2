"""Modelos e configuração da integração com o Outlook Desktop Classic (HU-01)."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config import configuration


@dataclass
class Attachment:
    """Representa um anexo de e-mail."""

    index: int          # posição ordinal no COM (base 1)
    file_name: str
    display_name: str
    file_size: int      # bytes
    file_type: str      # extensão sem ponto, ex: "xlsx"
    is_inline: bool      # True = imagem embutida no corpo HTML


@dataclass
class EmailMessage:
    """Representa um e-mail lido do Outlook com seus metadados."""

    entry_id: str
    subject: str
    sender_name: str
    sender_email: str
    body: str
    received_at: Optional[datetime]
    attachments: list[Attachment]
    attachment_count: int


@dataclass
class OutlookConfig:
    """
    Configuração da integração Outlook para o robô Detraf.

    Attributes:
        account: Conta Outlook (email) a acessar. Ex: detrafTBRA.br@telefonica.com.
        detraf_despesas_folder: Pasta (já existente, alimentada por fora) de
            onde o robô lê os e-mails com Detraf de despesa.
        processados_folder: Subpasta dentro de `detraf_despesas_folder` para
            onde os e-mails já capturados são movidos (idempotência).
        dest_root: Pasta local onde baixar os anexos.
        max_retry: Tentativas de download por e-mail antes de desistir.
        dia_liberacao: Dia do mês a partir do qual o robô deve processar.
    """

    account: str
    detraf_despesas_folder: str
    processados_folder: str
    dest_root: Path
    max_retry: int
    dia_liberacao: int

    @classmethod
    def from_configuration(cls) -> "OutlookConfig":
        """Carrega a configuração a partir de src.config.configuration (.env)."""
        return cls(
            account=configuration.OUTLOOK_ACCOUNT,
            detraf_despesas_folder=configuration.OUTLOOK_DETRAF_DESPESAS_FOLDER,
            processados_folder=configuration.OUTLOOK_PROCESSADOS_FOLDER,
            dest_root=Path(configuration.OUTLOOK_DEST_ROOT),
            max_retry=configuration.OUTLOOK_MAX_RETRY,
            dia_liberacao=configuration.DETRAF_DIA_LIBERACAO,
        )
