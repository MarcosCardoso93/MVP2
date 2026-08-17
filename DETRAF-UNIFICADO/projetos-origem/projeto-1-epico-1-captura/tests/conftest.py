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
import sqlite3
import tempfile

_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(suffix=".db", prefix="detraf_test_")
os.close(_TEST_DB_FD)

_conexao = sqlite3.connect(_TEST_DB_PATH)
_conexao.execute(
    'CREATE TABLE tbl_anexo5_processado ("EOT" TEXT, "Nome Fantasia" TEXT)'
)
_conexao.executemany(
    'INSERT INTO tbl_anexo5_processado ("EOT", "Nome Fantasia") VALUES (?, ?)',
    [
        ("002", "Desktop Sigmanet"),
        ("112", "Megatelecom Telecomunicações S.A."),
        ("010", "Vivo"),
    ],
)
_conexao.commit()
_conexao.close()

os.environ["ENV"] = "dev"
os.environ["CAMINHO_SQLITE"] = _TEST_DB_PATH
os.environ["DIRETORIO_ENTRADA"] = tempfile.mkdtemp(prefix="detraf_test_entrada_")
os.environ["DIRETORIO_SAIDA"] = tempfile.mkdtemp(prefix="detraf_test_saida_")
os.environ["COMPETENCIA"] = ""
os.environ["EXTENSOES_CSV"] = "csv"
os.environ["EXTENSOES_EXCEL"] = "xlsx,xls,ods"
