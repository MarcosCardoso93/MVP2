"""Comparação de comportamento entre a base comum e os projetos de origem.

A unificação preserva comportamento, **exceto** onde uma divergência foi
decidida e registrada. Estes testes fixam as duas coisas:

- o que deve ter permanecido igual (o núcleo do gerenciador de arquivos, lido
  contra as fixtures reais do Projeto 4);
- o que **mudou de propósito**, para que a mudança não passe despercebida numa
  regressão futura.

Ver ``trabalho/inventarios/duplicacoes.md``.
"""

from pathlib import Path

import pandas as pd
import pytest

_RAIZ = Path(__file__).resolve().parents[2]
_FIXTURES = (
    _RAIZ
    / "projetos-origem"
    / "projeto-4-epico-4-h19"
    / "tests"
    / "fixtures"
)

pytestmark = pytest.mark.skipif(
    not _FIXTURES.is_dir(), reason="fixtures do Projeto 4 não disponíveis"
)


# ---------------------------------------------------------------------------
# O que permaneceu igual — leitura dos arquivos reais
# ---------------------------------------------------------------------------


def test_le_detraf_da_operadora_sem_cabecalho_e_com_virgula():
    """Fixture ALGAR SMP: vírgula como separador, sem cabeçalho."""
    from comum.arquivos.gerenciador import carregar_dados

    df = carregar_dados(_FIXTURES / "detraf" / "algar_smp_reduzido.csv")

    assert df is not None
    assert not df.empty
    assert len(df.columns) == 18


def test_le_detraf_da_operadora_com_cabecalho_e_ponto_e_virgula():
    """Fixture ALGAR STFC: ponto e vírgula, com cabeçalho."""
    from comum.arquivos.gerenciador import carregar_dados

    df = carregar_dados(_FIXTURES / "detraf" / "algar_stfc_reduzido.csv")

    assert df is not None
    assert not df.empty


def test_le_expectativa_vivo():
    from comum.arquivos.gerenciador import carregar_dados

    df = carregar_dados(_FIXTURES / "expectativa" / "vivo_d_reduzido.csv")

    assert df is not None
    assert not df.empty


# ---------------------------------------------------------------------------
# Layout — a correção de COL_REL
# ---------------------------------------------------------------------------


def test_col_rel_aponta_para_a_coluna_de_relatorio_no_arquivo_real():
    """
    MUDANÇA REGISTRADA: ``COL_REL`` era 4 no Projeto 4 e passou para 5.

    O índice 4 é o POI. Com o valor antigo, o filtro de linhas de total agia
    sobre o POI e nada era removido. A fixture com cabeçalho prova o índice.
    """
    from comum.config import constantes as const

    cabecalho = (
        (_FIXTURES / "detraf" / "algar_stfc_reduzido.csv")
        .read_text(encoding="utf-8")
        .splitlines()[0]
        .split(";")
    )

    assert cabecalho[const.COL_REL] == "tipo_relatorio"
    assert cabecalho[const.COL_DESCRITOR] == "descritor"
    assert cabecalho[const.COL_POI] == "poi"
    assert cabecalho[const.COL_GH] == "grupo_horario"
    assert cabecalho[const.COL_MINUTOS] == "minutos"
    assert cabecalho[const.COL_R_BRUTO] == "valor_total"


def test_layout_da_expectativa_e_diferente_do_da_operadora():
    """
    ACHADO REGISTRADO (pendência N3): o arquivo de expectativa Vivo tem outro
    layout — e **não tem coluna de R$_Bruto**, enquanto a comparação da HU-10 é
    justamente sobre R$_Bruto.

    O Projeto 3 aplicava os índices da operadora aos dois lados.
    """
    from comum.config import constantes as const

    cabecalho = (
        (_FIXTURES / "expectativa" / "vivo_d_reduzido.csv")
        .read_text(encoding="utf-8")
        .splitlines()[0]
        .split(";")
    )

    # Os índices da expectativa são outros.
    assert cabecalho[const.EXPECTATIVA_COL_DEVEDORA] == "EOT_DEVEDORA"
    assert cabecalho[const.EXPECTATIVA_COL_REL] == "REL"
    assert cabecalho[const.EXPECTATIVA_COL_DESCRITOR] == "DESCRITOR"
    assert cabecalho[const.EXPECTATIVA_COL_MINUTOS] == "MINUTOS_TARIFADOS"

    # Aplicar os índices da operadora aqui daria os campos errados.
    assert cabecalho[const.COL_DEVEDORA] != "EOT_DEVEDORA"
    assert cabecalho[const.COL_REL] != "REL"
    assert cabecalho[const.COL_MINUTOS] != "MINUTOS_TARIFADOS"

    # E não existe coluna de valor bruto do lado da expectativa.
    assert const.EXPECTATIVA_COL_R_BRUTO is None
    assert not any("BRUTO" in coluna.upper() for coluna in cabecalho)


# ---------------------------------------------------------------------------
# O que mudou de propósito — a regra de variação
# ---------------------------------------------------------------------------


def test_divergencia_registrada_base_do_percentual():
    """
    MUDANÇA REGISTRADA: o Projeto 3 usava a expectativa como base; agora é a
    operadora. Para 110 contra 100, o resultado deixa de ser 10% e passa a
    9,09%.
    """
    from comum.dominio.variacao import calcular_variacao

    unificado = calcular_variacao(pd.Series([110.0]), pd.Series([100.0])).iloc[0]
    como_era_no_p3 = (110.0 - 100.0) / 100.0 * 100

    assert unificado == pytest.approx(9.0909, abs=1e-4)
    assert como_era_no_p3 == pytest.approx(10.0)
    assert unificado != pytest.approx(como_era_no_p3)


def test_divergencia_registrada_expectativa_ausente():
    """
    MUDANÇA REGISTRADA: sem arquivo de expectativa, o Projeto 3 devolvia ``NA``
    e a flag saía ``"N"`` — deixava de contestar o caso mais contestável. A V2
    manda processar com expectativa zerada.
    """
    from comum.dominio.variacao import FLAG_CONTESTAR, calcular_variacao, deve_contestar

    variacao = calcular_variacao(pd.Series([500.0]), pd.Series([0.0]))

    assert deve_contestar(variacao).iloc[0] == FLAG_CONTESTAR


def test_comportamento_preservado_do_sinal():
    """
    PRESERVADO do Projeto 3 (e divergente do Projeto 4, que usava ``abs()``):
    cobrar a menos que o esperado não gera contestação.
    """
    from comum.dominio.variacao import FLAG_NAO_CONTESTAR, calcular_variacao, deve_contestar

    variacao = calcular_variacao(pd.Series([10.0]), pd.Series([100.0]))

    assert deve_contestar(variacao).iloc[0] == FLAG_NAO_CONTESTAR
