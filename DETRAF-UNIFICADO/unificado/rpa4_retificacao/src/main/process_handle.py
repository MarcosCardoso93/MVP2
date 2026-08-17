"""Entrypoint do RPA 4 — instancia e dispara o controller de orquestração."""

from __future__ import annotations

from comum.utils.decoradores import log_execucao
from src.controllers.retificacao_controller import RetificacaoController


@log_execucao
def run(referencia=None, etapa=None, diagnostico=None) -> int:
    """
    Roda a retificação e devolve quantos processos falharam.

    Camada fina de propósito: quem orquetra as etapas é o controller. Aqui só se
    adapta o que o `main.py` conhece (argumentos) ao que o controller espera, e
    se converte o resultado no código de saída do processo.
    """
    resultados = RetificacaoController().retificar(
        referencia=referencia,
        etapa=etapa,
        diagnostico=diagnostico,
    )
    return sum(1 for resultado in resultados if resultado.erro)
