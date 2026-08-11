"""
Módulo responsável por inicializar e disparar a execução da aplicação.

Ponto de ligação entre o main.py e a camada de controllers.
"""

from comum.config.logger_config import logger
from src.controllers.processamento_controller import ProcessamentoController


def run(
    pasta_entrada: str | None = None,
    etapa: str | None = None,
    diagnostico=None,
) -> None:
    """
    Inicializa e executa a aplicação de processamento de arquivos.

    Instancia o controller e dispara o fluxo principal.

    Args:
        pasta_entrada: Recorte de ``--pasta-entrada``. Quando informada, a
            captura por e-mail é pulada e os arquivos já presentes na pasta são
            processados — o que permite exercitar HU-02 e HU-03 sem Outlook.
        etapa: Recorte de ``--etapa``. `None` executa as duas na ordem.
        diagnostico: `DiagnosticoDeExecucao`, para o `.txt` por etapa. `None`
            executa como antes, sem registrar nada.

    Returns:
        None.
    """
    logger.info("Aplicação iniciada")
    controller = ProcessamentoController()
    controller.processar(
        pasta_entrada=pasta_entrada, etapa=etapa, diagnostico=diagnostico
    )
    logger.info("Aplicação finalizada")
