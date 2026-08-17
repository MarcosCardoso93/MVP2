from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ArquivoRecusado:
    """
    Um arquivo reprovado na validação, com o que se vai dizer sobre ele.

    Existe porque a resposta à operadora é **por e-mail de origem**, e não por
    arquivo: um e-mail pode trazer vários anexos, e vários deles podem ser
    reprovados. Mandar uma mensagem por arquivo faria a operadora receber três
    avisos sobre o mesmo envio — e agir só no primeiro.

    Attributes:
        nome: Nome do arquivo, como a operadora o enviou.
        motivos: Uma frase por regra reprovada, em português.
    """

    nome: str
    motivos: List[str]
