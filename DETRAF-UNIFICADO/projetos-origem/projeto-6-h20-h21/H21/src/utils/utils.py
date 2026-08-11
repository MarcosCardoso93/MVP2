import unicodedata
import re
@staticmethod
def Remover_acento(texto):

    if not isinstance(texto, str):
        return texto

    return (
        unicodedata
        .normalize('NFD', texto)
        .encode('ascii', 'ignore')
        .decode('utf-8')
    )

@staticmethod
def Remover_sufixos(texto):

    if not isinstance(texto, str):
        return texto

    tipos_empresa = ['_EPP', '_LTDA', '_SA', '_S/A', '_MEI', '_EI', '_EIRELI','_S.A.','_S.A','- SP2','- SP1','LTDA','S.A','S.A.','LTDA']
    for tipo in tipos_empresa:
        texto = texto.replace(tipo, '').strip()
    return texto