from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArquivoParaProcessar:
    """
    Pacote de trabalho que propaga a origem (e-mail) de um arquivo baixado
    até o pipeline de processamento/salvamento.

    Attributes:
        caminho: Caminho local do arquivo baixado.
        sender_email: E-mail do remetente do e-mail de origem (usado para
            identificar a operadora via WebFat).
        entry_id: EntryID do e-mail de origem no Outlook (usado para
            rastreamento e resposta por e-mail).
    """

    caminho: Path
    sender_email: str = ""
    entry_id: str = ""
