from src.config.logger_config import logger
from src.controllers.outlook_controller import OutlookController
from src.services.processamento_service import ProcessamentoService


class ProcessamentoController:
    """
    Controller do fluxo de processamento de arquivos.

    Atua como camada de coordenação entre o ponto de entrada da aplicação
    e a camada de serviços, sem conter qualquer lógica de negócio.
    """

    def __init__(self) -> None:
        self._outlook = OutlookController()
        self._servico = ProcessamentoService()

    def processar(self) -> None:
        """
        Captura os arquivos do Outlook (HU-01) e delega o processamento
        (identificação de operadora + salvamento) ao serviço principal.

        Returns:
            None.
        """
        logger.info("Controller capturando arquivos do Outlook")
        arquivos = self._outlook.capturar_arquivos()

        logger.info("Controller delegando execução ao serviço")
        self._servico.executar(arquivos)
