from dataclasses import dataclass
from datetime import datetime

from dateutil.relativedelta import relativedelta

from src.config import configuration


@dataclass(frozen=True)
class Competencia:
    """
    Representa a competência calculada para o processamento.

    Attributes:
        ano: Ano de referência no formato YYYY.
        competencia: Período no formato YYYYMM (mês anterior à referência).
    """

    ano: str
    competencia: str


class CompetenciaService:
    """Serviço responsável por calcular a competência do processamento."""

    @staticmethod
    def obter_competencia() -> Competencia:
        """
        Calcula e retorna a competência com base na configuração ou data atual.

        Regras:
        - Se COMPETENCIA estiver definida no .env, utiliza aquele mês como
          referência e retorna o mês anterior.
        - Caso contrário, utiliza a data atual como referência.
        - Trata corretamente a virada de ano (ex: 202601 → 202512 / 2025).

        Returns:
            Instância de Competencia com ano e competência calculados.

        Examples:
            COMPETENCIA=202606 → competencia='202605', ano='2026'
            COMPETENCIA=202601 → competencia='202512', ano='2025'
            Sem configuração (data atual 2026-06-15) → competencia='202605', ano='2026'
        """
        competencia_env: str = configuration.COMPETENCIA

        if competencia_env:
            ano_ref = int(competencia_env[:4])
            mes_ref = int(competencia_env[4:6])
            data_referencia = datetime(ano_ref, mes_ref, 1)
        else:
            data_referencia = datetime.now().replace(day=1)

        data_anterior = data_referencia - relativedelta(months=1)

        return Competencia(
            ano=str(data_anterior.year),
            competencia=data_anterior.strftime("%Y%m"),
        )
