from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RegistroRastreamento:
    """Vincula um arquivo baixado ao e-mail (Outlook) do qual ele veio."""

    caminho_arquivo: str
    entry_id: str
    subject: str
    sender_email: str
    received_at: Optional[str]
