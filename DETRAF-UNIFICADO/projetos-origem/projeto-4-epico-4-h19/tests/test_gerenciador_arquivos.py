"""Smoke tests do toolkit de arquivos reutilizado contra as fixtures (T-005).

Confirma que `carregar_dados` lida com os dois layouts reais (vírgula/sem
cabeçalho e ponto e vírgula/com cabeçalho) e que a remoção de linha de total
funciona posicionalmente. Não reimplementa o toolkit — apenas valida o reuso.
"""

from pathlib import Path

import pandas as pd
import pytest

from src.utils import gerenciador_arquivos as ga

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def csv_smp() -> Path:
    return FIXTURES / "detraf" / "algar_smp_reduzido.csv"


@pytest.fixture
def csv_stfc() -> Path:
    return FIXTURES / "detraf" / "algar_stfc_reduzido.csv"


@pytest.fixture
def csv_expectativa() -> Path:
    return FIXTURES / "expectativa" / "vivo_d_reduzido.csv"


def test_carrega_layout_virgula_sem_cabecalho(csv_smp):
    # 5 linhas, sem cabeçalho detectável (primeiras colunas são numéricas).
    df = ga.carregar_dados(csv_smp)
    assert df.shape[0] == 5
    # Valores lidos como string (L-006): tarifa com vírgula decimal preservada.
    assert df.iloc[0, 10] == "0,00631"


def test_carrega_layout_pontovirgula_com_cabecalho(csv_stfc):
    # Cabeçalho textual é detectado e removido => 4 linhas de dados.
    df = ga.carregar_dados(csv_stfc)
    assert df.shape[0] == 4
    assert df.shape[1] == 18


def test_remove_linha_total_posicional(csv_stfc):
    # No layout STFC a "linha de total" foi marcada com valor 1 na coluna índice 5.
    df = ga.carregar_dados(csv_stfc)
    sem_total = ga.remover_linhas_por_valor(df, 5, "1")
    assert sem_total.shape[0] == df.shape[0] - 1


def test_expectativa_vivo_carrega_com_cabecalho(csv_expectativa):
    df = ga.carregar_dados(csv_expectativa)
    # Cabeçalho removido => 4 linhas de dados.
    assert df.shape[0] == 4


# --------------------------------------------------------------------------
# salvar_planilhas (multi-aba, T-080)
# --------------------------------------------------------------------------
def test_salvar_planilhas_grava_multiplas_abas(tmp_path: Path):
    abas = {
        "Contest": pd.DataFrame({"a": [1, 2]}),
        "TBRA": pd.DataFrame({"b": ["x", "y", "z"]}),
    }
    caminho = tmp_path / "sub" / "arquivo.xlsx"

    resultado = ga.salvar_planilhas(abas, caminho, incluir_cabecalho=True)

    assert resultado == caminho
    assert caminho.is_file()
    recarregado = pd.read_excel(caminho, engine="openpyxl", sheet_name=None)
    assert set(recarregado.keys()) == {"Contest", "TBRA"}
    assert recarregado["Contest"].shape[0] == 2
    assert recarregado["TBRA"].shape[0] == 3


def test_salvar_planilhas_vazio_levanta():
    with pytest.raises(ValueError):
        ga.salvar_planilhas({}, Path("qualquer.xlsx"))
