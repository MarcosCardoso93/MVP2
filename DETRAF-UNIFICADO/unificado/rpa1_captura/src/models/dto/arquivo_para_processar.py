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
        subject: Assunto do e-mail de origem, para o corpo da resposta.
        received_at: Quando o e-mail chegou (ISO), idem.

    `subject` e `received_at` entraram em 2026-08-06, quando o RPA 1 passou a
    responder à operadora sobre arquivo reprovado. Antes, quem respondia era o
    RPA 2 — e, como ele não recebia este pacote, tinha de ir buscar esses dois
    campos no `_rastreamento.json` procurando **pelo nome do arquivo**. Trazê-los
    aqui é o que dispensa aquela busca, que era ambígua por construção: dois
    e-mails com anexos de mesmo nome empatavam.
    """

    caminho: Path
    sender_email: str = ""
    entry_id: str = ""
    subject: str = ""
    received_at: str = ""
