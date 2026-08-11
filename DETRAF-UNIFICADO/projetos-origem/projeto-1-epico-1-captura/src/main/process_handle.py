"""
Módulo responsável por inicializar e disparar a execução da aplicação.

Ponto de ligação entre o main.py e a camada de controllers.
"""

from src.config.logger_config import logger
from src.controllers.processamento_controller import ProcessamentoController


def run() -> None:
    """
    Inicializa e executa a aplicação de processamento de arquivos.

    Instancia o controller e dispara o fluxo principal.

    Returns:
        None.
    """
    logger.info("Aplicação iniciada")
    controller = ProcessamentoController()
    controller.processar()
    logger.info("Aplicação finalizada")
