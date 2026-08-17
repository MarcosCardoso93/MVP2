"""Configuração de testes do RPA 4 (dev isolado).

Mesma disciplina das outras três suítes: `ENV=dev`, `DEBUG_ANO_MES_ATUAL` e
`CAMINHO_SQLITE` definidos **antes** de qualquer `import src...` — este módulo é
carregado pelo pytest antes da coleta, e a configuração lê o ambiente uma vez, no
import.

O seed é feito para a HU-21: linhas de contestação com variação **negativa**, que
é o que caracteriza tráfego recuperado, mais uma positiva e uma já marcada como
carregada, para que os testes possam provar o que o robô **não** pega.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap de path: raiz de unificado/ (para comum.*) e raiz deste RPA (src.*).
_RAIZ_RPA = Path(__file__).resolve().parents[1]
_RAIZ_UNIFICADO = _RAIZ_RPA.parent
for _caminho in (str(_RAIZ_UNIFICADO), str(_RAIZ_RPA)):
    if _caminho not in sys.path:
        sys.path.insert(0, _caminho)

from tests_apoio import silenciar_diagnose_do_log
from tests_apoio.banco import criar_banco_de_teste

silenciar_diagnose_do_log()

# Ponte loguru -> caplog. Sem ela, um teste que afirma "isto foi registrado no
# log" passa em silêncio mesmo quando nada foi registrado.
from tests_apoio import loguru_para_caplog  # noqa: F401 - fixture autouse

import os
import shutil
import tempfile

import pytest

_DB_TEMP_DIR = Path(tempfile.mkdtemp(prefix="detraf_rpa4_teste_"))
_CAMINHO_DB_TESTE = _DB_TEMP_DIR / "TABELAS_DETRAF_TESTE.db"
_CAMINHO_DB_MODELO = _DB_TEMP_DIR / "TABELAS_DETRAF_MODELO.db"

os.environ.setdefault("ENV", "dev")
# ANO_MES_REFERENCIA = 202507 (mês anterior a 202508). A contestação original,
# que a HU-21 procura, é de 202506 — o mês anterior a esse.
os.environ.setdefault("DEBUG_ANO_MES_ATUAL", "202508")
os.environ["CAMINHO_SQLITE"] = str(_CAMINHO_DB_TESTE)

#: Mês da contestação original nas fixtures — o que a detecção deve varrer.
REFERENCIA_CONTESTACAO = "202506"

_OPERADORAS = (
    ("001", "VIVO", "I", "SMP", "S", "Av. Eng. Luís Carlos Berrini, 1376 - São Paulo - SP"),
    ("021", "CLARO", "II", "SMP", "N", "Rua Verbo Divino, 1356 - São Paulo - SP"),
)

#: Quatro cenários, de propósito — o robô só pode pegar o primeiro e o segundo.
#:
#: Ordem das colunas: a de ``DDL_CONFIRMADO[LOG_DESPESA_CONTESTACAO]``.
_CONTESTACAO = (
    # 1 e 2: recuperação — variação negativa, ainda não retificada.
    (
        1, "STFC", "TU-RL", "011", "021", "CLARO", REFERENCIA_CONTESTACAO, "202506",
        5000.0, 500.0, 4000.0, 400.0, -1000.0, -100.0, -20.0, -20.0,
        "não carregado", "com retenção", None,
    ),
    (
        2, "SMP", "VU-M", "012", "021", "CLARO", REFERENCIA_CONTESTACAO, "202505",
        800.0, 80.0, 700.0, 60.0, -100.0, -20.0, -12.5, -25.0,
        "não carregado", "sem retenção", None,
    ),
    # 3: variação POSITIVA — é contestação, não recuperação. O RPA 4 ignora.
    (
        3, "SMP", "VU-M", "012", "021", "CLARO", REFERENCIA_CONTESTACAO, "202506",
        1000.0, 10.0, 1100.0, 11.0, 100.0, 1.0, 10.0, 10.0,
        "não carregado", "sem retenção", None,
    ),
    # 4: negativa, mas já `carregado`. É o freio de idempotência — e também o
    # ponto cego documentado: o RPA 3 grava este mesmo valor com outro sentido.
    (
        4, "STFC", "TU-RL", "011", "021", "CLARO", REFERENCIA_CONTESTACAO, "202504",
        300.0, 30.0, 200.0, 20.0, -100.0, -10.0, -33.3, -33.3,
        "carregado", "com retenção", None,
    ),
)


def _criar_e_popular_sqlite(caminho_db: Path) -> None:
    criar_banco_de_teste(
        caminho_db,
        operadoras=_OPERADORAS,
        contestacao=_CONTESTACAO,
    )


_criar_e_popular_sqlite(_CAMINHO_DB_MODELO)
shutil.copy2(_CAMINHO_DB_MODELO, _CAMINHO_DB_TESTE)


@pytest.fixture
def repo_cache():
    """Cache limpo sobre o SQLite de teste, restaurado antes e depois."""

    from comum.dados.repositorio_cache import RepositorioCache

    RepositorioCache.resetar()
    shutil.copy2(_CAMINHO_DB_MODELO, _CAMINHO_DB_TESTE)

    cache = RepositorioCache()
    yield cache

    RepositorioCache.resetar()
    shutil.copy2(_CAMINHO_DB_MODELO, _CAMINHO_DB_TESTE)


@pytest.fixture
def repo_tabelas(repo_cache):
    """:class:`RepositorioTabelas` sobre o SQLite de teste."""

    from comum.dados.repositorio_tabelas import RepositorioTabelas

    return RepositorioTabelas()
