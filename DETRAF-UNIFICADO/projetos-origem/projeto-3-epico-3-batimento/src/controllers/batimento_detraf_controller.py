from src.services.batimento_detraf import BatimentoDetrafService


class BatimentoDetrafController:
    def __init__(self):
        self.service = BatimentoDetrafService()

    def batimento_detraf(self):
        self.service.executar()
