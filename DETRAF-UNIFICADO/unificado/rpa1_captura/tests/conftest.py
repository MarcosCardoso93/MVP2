"""Bootstrap de path para a suíte deste RPA.

Insere a raiz de ``unificado/`` (para ``comum.*``) e a raiz deste RPA (para
``src.*``) no ``sys.path``, tornando a suíte executável sem depender de
``PYTHONPATH`` externo.

⚠️ Os três RPAs têm um pacote chamado ``src``. Eles não coexistem num mesmo
processo Python, então **cada suíte roda em uma invocação separada do pytest**.
Ver o README de ``unificado/``.
"""

import sys
from pathlib import Path

_RAIZ_RPA = Path(__file__).resolve().parents[1]
_RAIZ_UNIFICADO = _RAIZ_RPA.parent

for _caminho in (str(_RAIZ_UNIFICADO), str(_RAIZ_RPA)):
    if _caminho not in sys.path:
        sys.path.insert(0, _caminho)

from tests_apoio import criar_banco_de_teste, silenciar_diagnose_do_log

silenciar_diagnose_do_log()

# Ponte loguru -> caplog, compartilhada com as demais suites. Sem ela, um teste
# que afirma "isto foi registrado no log" passa em silencio mesmo quando nada
# foi registrado.
from tests_apoio import loguru_para_caplog  # noqa: F401 - fixture autouse



"""
Configuração global dos testes.

IMPORTANTE: RepositorioCache/RepositorioTabelas (src/models/repository/) se
conectam ao banco e carregam tbl_anexo5_processado em memória no momento em
que o módulo é importado pela primeira vez (padrão Singleton). Por isso, as
variáveis de ambiente abaixo são configuradas em código de nível de módulo
(executado assim que este conftest.py é carregado pelo pytest), ANTES de
qualquer import de código de `src` — inclusive antes dos imports feitos
pelos próprios arquivos de teste. Não mover essa configuração para dentro de
uma fixture: fixtures só rodam depois que os módulos de teste já foram
importados, tarde demais para esse singleton.
"""

import os
import tempfile

_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(suffix=".db", prefix="detraf_test_")
os.close(_TEST_DB_FD)

# As operadoras são as desta suíte — os testes as referenciam por EOT. O que se
# compartilha com as outras suítes é o **schema**, e é por isso que o helper
# existe: o seed antigo daqui criava `tbl_anexo5_processado` com duas colunas, e
# a validação lê seis (`validar_regiao` procura `Região`). Enquanto o RPA 1 não
# validava nada, ninguém notou.
# Só as desta suíte. Juntar as `OPERADORAS_PADRAO` faria "VIVO" e "Vivo"
# coexistirem, e `buscar_nome_fantasia("vivo")` passaria a devolver a outra.
criar_banco_de_teste(
    _TEST_DB_PATH,
    operadoras=[
        ("002", "Desktop Sigmanet", "II", "SCM", "N", "Rua A, 1 - SP"),
        ("112", "Megatelecom Telecomunicações S.A.", "II", "STFC", "N", "Rua B, 2 - RJ"),
        ("010", "Vivo", "I", "STFC", "S", "Av. Berrini, 1376 - São Paulo - SP"),
    ],
)

os.environ["ENV"] = "dev"
os.environ["CAMINHO_SQLITE"] = _TEST_DB_PATH
os.environ["DIRETORIO_ENTRADA"] = tempfile.mkdtemp(prefix="detraf_test_entrada_")
os.environ["DIRETORIO_SAIDA"] = tempfile.mkdtemp(prefix="detraf_test_saida_")
os.environ["COMPETENCIA"] = ""
os.environ["EXTENSOES_CSV"] = "csv"
os.environ["EXTENSOES_EXCEL"] = "xlsx,xls,ods"
