from src.services.AGI.Upload_Detraf_EXT_INT import Upload_Detraf_EXT_INT
from src.services.AGI.Upload_Contestacao import Upload_Contestacao

"""
Orquestrador do Epico 5 - Carga no AGI (Despesa).
Segue o mesmo padrao do ProcessHandle do exemplo RPA_DETRAF_RECEITA
(src/main/process_handle.py): so encadeia os fluxos, sem logica de negocio aqui.
"""


class ProcessHandle:

    def __init__(self):
        self.upload_detraf = Upload_Detraf_EXT_INT()   # HU-17
        self.upload_contestacao = Upload_Contestacao()  # HU-18

    def run(self):
        # HU-17: Detraf > Importar Dados (arquivos EXT sempre; INT so em contestacao com retencao)
        self.upload_detraf.Fluxo_Upload_Detraf()

        # HU-18: Contestação > Gerenciar (so roda quando ha contestacao; ver TODOs no modulo)
        self.upload_contestacao.Fluxo_Upload_Contestacao()
