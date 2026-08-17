from src.services.AGI.Verificacao_Relatorio import Verificacao_Relatorio

"""
Orquestrador da HU-20. Mesmo padrao do ProcessHandle do exemplo/Epico 5: so encadeia
o fluxo, sem logica de negocio aqui.
"""


class ProcessHandle:

    def __init__(self):
        self.verificacao = Verificacao_Relatorio()

    def run(self):
        self.verificacao.Fluxo_Verificacao_Relatorio()
