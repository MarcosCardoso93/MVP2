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


def _criar_e_popular_sqlite(caminho_db: Path) -> None:
    """Cria o SQLite de teste e insere os seeds mínimos."""

    conexao = sqlite3.connect(caminho_db)
    try:
        cursor = conexao.cursor()

        # tbl_anexo5_processado: EOT -> Nome Fantasia, Região, Tipo de Serviço, Concessão,
        # Endereço de Correspondência (coluna confirmada pelo usuário, 2026-07-23 — usada
        # no cabeçalho da carta HU-14, T-082).
        cursor.execute(
            """
            CREATE TABLE tbl_anexo5_processado (
                "EOT" TEXT,
                "Nome Fantasia" TEXT,
                "Região" TEXT,
                "Tipo de Serviço" TEXT,
                "Concessão" TEXT,
                "Endereço de Correspondência" TEXT
            )
            """
        )
        cursor.executemany(
            'INSERT INTO tbl_anexo5_processado VALUES (?, ?, ?, ?, ?, ?)',
            [
                ("001", "VIVO", "I", "SMP", "S", "Av. Eng. Luís Carlos Berrini, 1376 - São Paulo - SP"),
                ("002", "VIVO", "I", "STFC", "S", "Av. Eng. Luís Carlos Berrini, 1376 - São Paulo - SP"),
                ("021", "CLARO", "II", "SMP", "N", "Rua Verbo Divino, 1356 - São Paulo - SP"),
            ],
        )

        # tbl_detraf_tarifas: contexto de tarifa regulada (seed mínimo)
        cursor.execute(
            """
            CREATE TABLE tbl_detraf_tarifas (
                "id" INTEGER,
                "regiao" TEXT,
                "gh" TEXT,
                "regra_desc" TEXT,
                "tipo_remuneracao" TEXT,
                "tarifa" TEXT,
                "data_inicio" TEXT,
                "data_fim" TEXT
            )
            """
        )
        cursor.executemany(
            'INSERT INTO tbl_detraf_tarifas VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            [
                (1, "I", None, "VU-M", "VU-M", "0,03000", "2025-01-01", "2025-12-31"),
                (2, "II", None, "TU-RL", "TU-RL", "0,01500", "2025-01-01", "2025-12-31"),
            ],
        )

        # tbl_detraf_mapeamento_descritores: descritor -> remuneração (D-21, V2 pág. 7 —
        # "a relação entre descritores e remuneração está disponível para consulta na
        # tabela 'tbl_detraf_mapeamento_descritores' do banco webfat"). O schema é o
        # presumido pela D-21: mesmas colunas de Mapeamento_Descritores.xlsx. O CSV em
        # tests/fixtures deixou de ser fonte de produção e virou seed deste banco.
        cursor.execute(
            """
            CREATE TABLE tbl_detraf_mapeamento_descritores (
                "id" INTEGER,
                "final_descritor" TEXT,
                "remuneracao_fixa" TEXT,
                "observacao" TEXT,
                "produto" TEXT
            )
            """
        )
        cursor.executemany(
            'INSERT INTO tbl_detraf_mapeamento_descritores VALUES (?, ?, ?, ?, ?)',
            _ler_seed_mapeamento_descritores(),
        )

        # tbl_rpa_log_detraf_despesa_contestacao: sinal COM/SEM retenção (D-6 RESOLVIDA) +
        # despesa da contestação (HU-19, D-16 revisada 2026-07-28). Schema real confirmado
        # em "DOCS/Outros arquivos auxiliares/Tabelas para o RPA alimentar o Webfat -
        # despesa.xlsx" (aba "Contestação") + coluna `remuneracao` (decisão do usuário,
        # 2026-07-28 — a tabela real não tinha essa coluna, mas o sinal de contestação
        # pode variar por remuneração dentro do mesmo par de EOT, então ela é necessária
        # tanto para a escrita da despesa (HU-19) quanto para a leitura do sinal (T-024)).
        cursor.execute(
            """
            CREATE TABLE tbl_rpa_log_detraf_despesa_contestacao (
                "id" INTEGER,
                "tipo_servico_vivo" TEXT,
                "eot_tbra" TEXT,
                "eot_operadora" TEXT,
                "empresa" TEXT,
                "referencia" TEXT,
                "trafego" TEXT,
                "remuneracao" TEXT,
                "minutos_tbra" REAL,
                "vb_tbra" REAL,
                "minutos_operadora" REAL,
                "vb_operadora" REAL,
                "minutos_diferenca" REAL,
                "vb_diferenca" REAL,
                "minutos_variacao_perc" REAL,
                "vb_variacao_perc" REAL,
                "carga_agi" TEXT,
                "tipo_contestacao" TEXT
            )
            """
        )
        cursor.executemany(
            """
            INSERT INTO tbl_rpa_log_detraf_despesa_contestacao VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    1, "STFC", "011", "021", "CLARO", "202507", "202507", "TU-RL",
                    4790.20, 29.18, 53106.70, 324.41, 48316.5, 295.23, 91.0, 91.0,
                    "não carregado", "com retenção",
                ),
                (
                    2, "SMP", "012", "021", "CLARO", "202507", "202507", "VU-M",
                    1000.0, 10.0, 1005.0, 10.05, 5.0, 0.05, 0.5, 0.5,
                    "não carregado", "sem retenção",
                ),
            ],
        )

        conexao.commit()
    finally:
        conexao.close()


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

    from src.models.repository.repositorio_cache import RepositorioCache

    RepositorioCache.resetar()
    shutil.copy2(_CAMINHO_DB_MODELO, _CAMINHO_DB_TESTE)

    cache = RepositorioCache()
    yield cache

    RepositorioCache.resetar()
    shutil.copy2(_CAMINHO_DB_MODELO, _CAMINHO_DB_TESTE)


@pytest.fixture
def repo_tabelas(repo_cache):
    """:class:`RepositorioTabelas` sobre o SQLite de teste."""

    from src.models.repository.repositorio_tabelas import RepositorioTabelas

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
