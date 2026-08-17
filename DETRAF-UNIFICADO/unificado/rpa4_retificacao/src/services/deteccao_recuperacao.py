"""Passo 1 da HU-21 — quem foi recuperado, e quanto vai para o AGI.

Não abre o AGI, não escreve em lugar nenhum: lê a contestação do mês anterior,
separa o que teve variação negativa e calcula os valores do evento. É a metade
conferível do robô, e a que responde "há trabalho este mês?" sem risco nenhum.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from comum.config.logger_config import logger
from comum.dominio.competencia import obter_competencia
from comum.dominio.retificacao import calcular_valores_evento


@dataclass
class Recuperacao:
    """Uma linha de contestação que virou recuperação, pronta para o AGI."""

    id_contestacao: int
    operadora: str
    eot_operadora: str
    periodo: str
    periodo_trafego: str
    minutos: float
    valor_bruto: float
    valores_evento: dict = field(default_factory=dict)

    def descrever(self) -> str:
        return (
            f"{self.operadora} (EOT {self.eot_operadora}) ref {self.periodo} "
            f"tráfego {self.periodo_trafego}: {self.minutos} min, "
            f"R$ {self.valor_bruto}"
        )


def mes_anterior(aaaamm: str) -> str:
    """
    ``202607`` → ``202606``.

    A recuperação é percebida no mês **seguinte** ao da contestação, então a
    detecção varre o mês anterior ao de processamento.
    """
    ano, mes = int(str(aaaamm)[:4]), int(str(aaaamm)[4:6])
    mes -= 1
    if mes == 0:
        mes, ano = 12, ano - 1
    return f"{ano:04d}{mes:02d}"


def detectar(repositorio, referencia: str | None = None) -> list[Recuperacao]:
    """
    As recuperações a lançar, já com os valores do evento calculados.

    Args:
        repositorio: `RepositorioTabelas` (injetado para poder testar).
        referencia: Mês de processamento ``AAAAMM``. Sem ele, o do ambiente.

    Returns:
        Lista possivelmente vazia — e vazia é um resultado legítimo: num mês sem
        recuperação não há o que retificar.
    """
    processamento = referencia or obter_competencia().competencia
    contestacao_original = mes_anterior(processamento)

    logger.info(
        f"[HU-21] Processando {processamento}: procuro recuperações na "
        f"contestação de {contestacao_original}."
    )

    recuperacoes = [
        Recuperacao(
            id_contestacao=linha["id"],
            operadora=linha["operadora"],
            eot_operadora=linha["eot_operadora"],
            periodo=linha["periodo"],
            periodo_trafego=linha["periodo_trafego"],
            minutos=linha["minutos"],
            valor_bruto=linha["valor_bruto"],
            valores_evento=calcular_valores_evento(
                minutos=linha["minutos"], valor_bruto=linha["valor_bruto"]
            ),
        )
        for linha in repositorio.obter_trafego_recuperado(contestacao_original)
    ]

    for recuperacao in recuperacoes:
        logger.info(f"[HU-21] Recuperação: {recuperacao.descrever()}")

    return recuperacoes
