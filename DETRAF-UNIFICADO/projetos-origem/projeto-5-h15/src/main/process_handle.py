from src.services.Contestacao.Envio_Email_Contestacao import Envio_Email_Contestacao

"""
Orquestrador da HU-15. Mesmo padrao do ProcessHandle usado nos pacotes anteriores
(Epico 5, HU-20, HU-21): so encadeia o fluxo, sem logica de negocio aqui.
"""


class ProcessHandle:

    def __init__(self):
        self.envio_email = Envio_Email_Contestacao()

    def run(self):
        self.envio_email.Fluxo_Envio_Email_Contestacao()
