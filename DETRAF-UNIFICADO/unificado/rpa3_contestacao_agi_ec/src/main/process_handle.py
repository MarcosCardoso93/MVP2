"""Entrypoint do RPA 3 — instancia e dispara o controller de orquestração."""

from src.controllers.geracao_agi_controller import GeracaoAgiController
from comum.utils.decoradores import log_execucao


@log_execucao
def run(
    operadoras: list[str] | None = None,
    referencia: str | None = None,
    etapa: str | None = None,
    diagnostico=None,
) -> int:
    """
    Executa o fluxo do RPA 3 no mês corrente.

    Args:
        operadoras: Recorte de ``--operadoras``. `None` (o normal) varre a raiz e
            processa todas as operadoras com Detraf no mês.
        referencia: Recorte de ``--referencia``. `None` usa a competência.
        etapa: Recorte de ``--etapa``. `None` executa as quatro na ordem.
        diagnostico: `DiagnosticoDeExecucao`, para o `.txt` por etapa. `None`
            executa como antes, sem registrar nada.

    Returns:
        Quantidade de operadoras que terminaram com erro. O `main.py` usa isso
        como código de saída: uma execução em que metade das operadoras falhou
        não pode terminar dizendo "sucesso" ao agendador.
    """

    resultados = GeracaoAgiController().gerar_artefatos(
        operadoras=operadoras or None,
        referencia=referencia,
        etapa=etapa,
        diagnostico=diagnostico,
    )
    return sum(1 for resultado in resultados if resultado.erro)
