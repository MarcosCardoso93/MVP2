"""Competência de processamento — base comum dos RPAs do Detraf.

Regra de negócio: processa-se sempre o **mês anterior** à referência. Se
``DEBUG_ANO_MES_ATUAL`` (ou ``COMPETENCIA``) estiver definido, ele é a
referência; senão, usa-se o mês corrente.

Origem: unificação de ``competencia_service.py`` + ``filesystem.mes_anterior``
(Projeto 1) com a constante ``ANO_MES_REFERENCIA`` (Projetos 2, 3 e 4). Os
projetos calculavam a mesma coisa de duas formas — ver
``trabalho/inventarios/duplicacoes.md`` D-17.

O Projeto 1 precisa do par ano/competência; os demais só da string. As duas
formas são expostas.
"""

from dataclasses import dataclass
from datetime import datetime

from dateutil.relativedelta import relativedelta

from comum.config import configuration


@dataclass(frozen=True)
class Competencia:
    """Período de processamento.

    Attributes:
        ano: Ano no formato ``YYYY``.
        competencia: Período no formato ``YYYYMM`` (mês anterior à referência).
    """

    ano: str
    competencia: str


def obter_competencia() -> Competencia:
    """
    Calcula a competência de processamento **no momento da chamada**.

    Lê ``configuration.COMPETENCIA`` a cada invocação, e não uma constante
    resolvida no import — comportamento do Projeto 1, preservado porque é o que
    permite ajustar o período em teste sem reimportar o módulo.

    Returns:
        ``Competencia`` com ano e competência.

    Examples:
        ``COMPETENCIA=202606`` -> ``Competencia('2026', '202605')``
        ``COMPETENCIA=202601`` -> ``Competencia('2025', '202512')``
        Sem override, em 2026-06 -> ``Competencia('2026', '202605')``
    """
    override: str = configuration.COMPETENCIA

    if override:
        referencia = datetime(int(override[:4]), int(override[4:6]), 1)
    else:
        referencia = datetime.now().replace(day=1)

    anterior = referencia - relativedelta(months=1)

    return Competencia(ano=str(anterior.year), competencia=anterior.strftime("%Y%m"))


def mes_anterior(competencia: str) -> str:
    """
    Retorna a competência do mês civil anterior à informada.

    Args:
        competencia: Competência no formato ``YYYYMM``.

    Returns:
        Competência do mês anterior, no formato ``YYYYMM``.

    Examples:
        >>> mes_anterior("202506")
        '202505'
        >>> mes_anterior("202601")
        '202512'
    """
    data = datetime(int(competencia[:4]), int(competencia[4:6]), 1)
    return (data - relativedelta(months=1)).strftime("%Y%m")


def ano_de(competencia: str) -> str:
    """
    Extrai o ano (``YYYY``) de uma competência (``YYYYMM``).

    Args:
        competencia: Competência no formato ``YYYYMM``.

    Returns:
        Ano com quatro dígitos.
    """
    return competencia[:4]
