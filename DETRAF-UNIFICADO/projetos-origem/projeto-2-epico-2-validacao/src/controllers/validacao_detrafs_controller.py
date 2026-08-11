from src.services.validacao_detrafs import ValidacaoDetrafsService


class ValidacaoDetrafsController:
    def __init__(self):
        self.service = ValidacaoDetrafsService()

    def validar_detrafs(self):
        self.service.executar()
