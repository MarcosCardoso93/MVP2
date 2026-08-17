"""Configuração global de testes (dev isolado — AI/05-Testes.md, D-9).

Pontos críticos:

- Define ``ENV=dev``, ``DEBUG_ANO_MES_ATUAL`` e ``CAMINHO_SQLITE`` **antes** de
  qualquer ``import src...`` (este módulo é carregado pelo pytest antes da coleta),
  para que ``src.config.configuration`` leia os valores certos e para evitar que
  módulos que conectam no banco quebrem no import (lição L-004).
- Cria um SQLite temporário e o popula com seeds mínimos das tabelas de
  referência (``tbl_anexo5_processado``, ``tbl_detraf_tarifas``,
  ``tbl_detraf_mapeamento_descritores``) e da tabela de sinal/despesa da
  contestação (``tbl_rpa_log_detraf_despesa_contestacao`` — mock, D-6).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap de path: raiz de unificado/ (para comum.*) e raiz deste RPA (para src.*).
# Os tres RPAs tem um pacote `src`; por isso cada suite roda numa invocacao
# separada do pytest. Ver o README de unificado/.
_RAIZ_RPA = Path(__file__).resolve().parents[1]
_RAIZ_UNIFICADO = _RAIZ_RPA.parent
for _caminho in (str(_RAIZ_UNIFICADO), str(_RAIZ_RPA)):
    if _caminho not in sys.path:
        sys.path.insert(0, _caminho)

from tests_apoio import silenciar_diagnose_do_log
from tests_apoio.banco import criar_banco_de_teste

silenciar_diagnose_do_log()

# Ponte loguru -> caplog, compartilhada com as demais suites. Sem ela, um teste
# que afirma "isto foi registrado no log" passa em silencio mesmo quando nada
# foi registrado.
from tests_apoio import loguru_para_caplog  # noqa: F401 - fixture autouse


import csv
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

import pytest

_DIRETORIO_FIXTURES = Path(__file__).parent / "fixtures"
_CSV_MAPEAMENTO_DESCRITORES = _DIRETORIO_FIXTURES / "mapeamento_descritores.csv"

# ---------------------------------------------------------------------------
# 1. Ambiente determinístico ANTES de importar qualquer coisa de `src`.
# ---------------------------------------------------------------------------
_DB_TEMP_DIR = Path(tempfile.mkdtemp(prefix="detraf_epico4_teste_"))
_CAMINHO_DB_TESTE = _DB_TEMP_DIR / "TABELAS_DETRAF_TESTE.db"
# Cópia pristina dos seeds. Desde a D-19/D-20 os testes fazem UPDATE no banco, então
# cada teste precisa partir do mesmo estado — o modelo é recopiado pela fixture
# `repo_cache`.
_CAMINHO_DB_MODELO = _DB_TEMP_DIR / "TABELAS_DETRAF_MODELO.db"

os.environ.setdefault("ENV", "dev")
# Período de referência fixo => ANO_MES_REFERENCIA = 202507 (mês anterior a 202508).
os.environ.setdefault("DEBUG_ANO_MES_ATUAL", "202508")
os.environ["CAMINHO_SQLITE"] = str(_CAMINHO_DB_TESTE)


def _ler_seed_mapeamento_descritores() -> list[tuple]:
    """Lê o CSV de fixtures como seed de ``tbl_detraf_mapeamento_descritores``."""

    with _CSV_MAPEAMENTO_DESCRITORES.open(encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        return [
            (
                int(linha["id"]),
                linha["final_descritor"],
                linha["remuneracao_fixa"],
                linha["observacao"],
                linha["produto"],
            )
            for linha in leitor
        ]


#: Operadoras desta suíte, na ordem de ``tests_apoio.banco.COLUNAS_ANEXO5``.
_OPERADORAS = (
    ("001", "VIVO", "I", "SMP", "S", "Av. Eng. Luís Carlos Berrini, 1376 - São Paulo - SP"),
    ("002", "VIVO", "I", "STFC", "S", "Av. Eng. Luís Carlos Berrini, 1376 - São Paulo - SP"),
    ("021", "CLARO", "II", "SMP", "N", "Rua Verbo Divino, 1356 - São Paulo - SP"),
)

#: Tarifas, na ordem de ``tests_apoio.banco.COLUNAS_TARIFAS``. Seed mínimo — o
#: RPA 3 não carrega esta tabela (ver ``tabelas.CACHE_RPA3``), ela existe só para
#: o banco de teste ter o mesmo formato do real.
#:
#: ⚠️ Tarifa com **ponto**: no banco real a coluna é `float`. Este seed usava
#: vírgula, que num `float` nem seria representável.
_TARIFAS = (
    (1, "I", None, "VU-M", "VU-M", "0.03000", "2025-01-01", "2025-12-31"),
    (2, "II", None, "TU-RL", "TU-RL", "0.01500", "2025-01-01", "2025-12-31"),
)

#: Sinal COM/SEM retenção (D-6) + despesa da contestação (HU-19, D-16 revisada).
#:
#: Ordem: a de ``DDL_CONFIRMADO[LOG_DESPESA_CONTESTACAO]``, que é a do banco real
#: — nela `remuneracoes` vem logo após `tipo_servico_vivo`, e **não** existe
#: `vb_contestacao`.
_CONTESTACAO = (
    (
        1, "STFC", "TU-RL", "011", "021", "CLARO", "202507", "202507",
        4790.20, 29.18, 53106.70, 324.41, 48316.5, 295.23, 91.0, 91.0,
        "não carregado", "com retenção", None,
    ),
    (
        2, "SMP", "VU-M", "012", "021", "CLARO", "202507", "202507",
        1000.0, 10.0, 1005.0, 10.05, 5.0, 0.05, 0.5, 0.5,
        "não carregado", "sem retenção", None,
    ),
)


def _criar_e_popular_sqlite(caminho_db: Path) -> None:
    """
    Cria o SQLite de teste e insere os seeds mínimos.

    Até 2026-08-06 este arquivo trazia a sua **própria** cópia do `CREATE TABLE`
    das quatro tabelas — a única suíte que não usava o helper compartilhado. As
    duas declarações divergiram sem ninguém notar, e as duas estavam erradas: os
    nomes do Anexo 5 com acento, e `remuneracao` no singular.

    Agora o schema sai de ``tests_apoio.banco``, que o deriva de
    ``tabelas.DDL_CONFIRMADO`` — transcrição do DDL real. Só os **seeds** moram
    aqui, que é o que de fato é específico desta suíte.
    """

    criar_banco_de_teste(
        caminho_db,
        operadoras=_OPERADORAS,
        tarifas=_TARIFAS,
        descritores=_ler_seed_mapeamento_descritores(),
        contestacao=_CONTESTACAO,
    )


# Popula o banco-modelo na importação do conftest (antes de qualquer teste rodar).
_criar_e_popular_sqlite(_CAMINHO_DB_MODELO)
shutil.copy2(_CAMINHO_DB_MODELO, _CAMINHO_DB_TESTE)


# ---------------------------------------------------------------------------
# 2. Fixtures reutilizáveis
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def caminho_sqlite_teste() -> Path:
    """Caminho do SQLite de teste populado com os seeds mínimos."""

    return _CAMINHO_DB_TESTE


@pytest.fixture
def repo_cache():
    """
    Instância limpa do :class:`RepositorioCache` apontando para o SQLite de teste.

    Reseta o Singleton **e restaura o banco a partir do modelo** antes e depois, para
    que os testes de escrita (D-19/D-20) não vazem estado entre si.
    """

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


@pytest.fixture
def indice_remuneracao(repo_tabelas) -> dict:
    """
    Índice ``descritor final -> remuneração`` (D-5) montado a partir do banco.

    Desde a D-21 (2026-07-30) a fonte é ``tbl_detraf_mapeamento_descritores``, semeada
    no SQLite de teste a partir de ``tests/fixtures/mapeamento_descritores.csv``.
    """

    from src.services import mapa_remuneracao as mr

    mapa = mr.carregar_mapa_descritores(repo_tabelas.obter_mapa_descritores())
    return mr.construir_indice_remuneracao(mapa)


@pytest.fixture
def raiz_operadoras(tmp_path: Path) -> Path:
    """Raiz temporária simulando "...\\Operadoras" para testes de I/O."""

    raiz = tmp_path / "Operadoras"
    raiz.mkdir(parents=True, exist_ok=True)
    return raiz


@pytest.fixture
def raiz_controle_ct(tmp_path: Path) -> Path:
    """Raiz temporária simulando "...\\Correspondências Enviadas\\CT"."""

    raiz = tmp_path / "CT"
    raiz.mkdir(parents=True, exist_ok=True)
    return raiz
