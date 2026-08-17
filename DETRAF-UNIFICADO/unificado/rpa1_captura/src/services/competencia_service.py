"""Competência de processamento — fachada sobre a base comum.

O cálculo passou para ``comum.dominio.competencia``, porque os quatro projetos
o repetiam de duas formas diferentes: o Projeto 1 com este serviço, os demais
com a constante ``ANO_MES_REFERENCIA`` (duplicação D-17).

Este módulo permanece como fachada para que os imports e os testes do Projeto 1
sigam válidos sem alteração.
"""

from comum.dominio.competencia import Competencia, obter_competencia

__all__ = ["Competencia", "CompetenciaService"]


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
        return obter_competencia()
