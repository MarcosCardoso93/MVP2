"""Entrypoint do Épico 4 — instancia e dispara o controller de orquestração."""

from src.controllers.geracao_agi_controller import GeracaoAgiController
from src.utils.decoradores import log_execucao


@log_execucao
def run() -> None:
    """Executa a geração dos artefatos do Épico 4 (Bootstrap: orquestração stub)."""

    controller = GeracaoAgiController()
    controller.gerar_artefatos()
