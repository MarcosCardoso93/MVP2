from src.controllers.batimento_detraf_controller import BatimentoDetrafController
from src.utils.decoradores import log_execucao


@log_execucao
def run():
    batimento = BatimentoDetrafController()
    batimento.batimento_detraf()
