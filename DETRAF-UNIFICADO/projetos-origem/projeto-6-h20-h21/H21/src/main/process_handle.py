from src.services.AGI.Retificacao_Contestacao import Retificacao_Contestacao

"""
Orquestrador da HU-21. Mesmo padrao do ProcessHandle do exemplo/Epico 5.
"""


class ProcessHandle:

    def __init__(self):
        self.retificacao = Retificacao_Contestacao()

    def run(self):
        self.retificacao.Fluxo_Retificacao_Recuperacao()
