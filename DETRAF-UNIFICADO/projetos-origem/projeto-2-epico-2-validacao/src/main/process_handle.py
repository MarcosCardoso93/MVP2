from src.controllers.validacao_detrafs_controller import ValidacaoDetrafsController
from src.utils.decoradores import log_execucao


@log_execucao
def run():
    # Instancia os controllers
    validacao = ValidacaoDetrafsController()

    # Executa os processos
    validacao.validar_detrafs()
