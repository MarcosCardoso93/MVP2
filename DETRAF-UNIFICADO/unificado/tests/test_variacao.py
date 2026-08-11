"""Testes da regra de variação unificada.

Cobrem especificamente as **três bordas que separavam o Projeto 3 do Projeto 4**
(ver ``trabalho/inventarios/duplicacoes.md`` D-13), porque é nelas que a
migração muda comportamento em relação a pelo menos uma das origens.
"""

import pandas as pd
import pytest

from comum.dominio.variacao import (
    FLAG_CONTESTAR,
    FLAG_NAO_CONTESTAR,
    aplicar,
    calcular_variacao,
    deve_contestar,
)


def _serie(*valores):
    return pd.Series(list(valores), dtype="float64")


# ---------------------------------------------------------------------------
# Borda 1 — base do percentual
#
# P3 usava a expectativa; P4 e a unificação usam a operadora.
# ---------------------------------------------------------------------------


def test_base_do_percentual_e_o_lado_operadora():
    # operadora 110, expectativa 100.
    # Base operadora: (110-100)/110 = 9,09%. Base expectativa seria 10%.
    variacao = calcular_variacao(_serie(110.0), _serie(100.0))
    assert variacao.iloc[0] == pytest.approx(9.0909, abs=1e-4)


# ---------------------------------------------------------------------------
# Borda 2 — par ausente (sem arquivo de expectativa)
#
# P3 devolvia NA e a flag saía "N" — deixava de contestar o caso mais
# contestável. A V2 manda processar com expectativa zerada.
# ---------------------------------------------------------------------------


def test_expectativa_ausente_gera_variacao_de_100_por_cento():
    variacao = calcular_variacao(_serie(500.0), _serie(0.0))
    assert variacao.iloc[0] == pytest.approx(100.0)


def test_expectativa_ausente_contesta():
    variacao = calcular_variacao(_serie(500.0), _serie(0.0))
    assert deve_contestar(variacao).iloc[0] == FLAG_CONTESTAR


def test_operadora_ausente_com_expectativa_nao_contesta():
    # A Vivo esperava, a operadora não cobrou. Não há o que contestar.
    variacao = calcular_variacao(_serie(0.0), _serie(500.0))
    assert variacao.iloc[0] == pytest.approx(-100.0)
    assert deve_contestar(variacao).iloc[0] == FLAG_NAO_CONTESTAR


def test_ambos_zerados_nao_contesta():
    variacao = calcular_variacao(_serie(0.0), _serie(0.0))
    assert variacao.iloc[0] == pytest.approx(0.0)
    assert deve_contestar(variacao).iloc[0] == FLAG_NAO_CONTESTAR


# ---------------------------------------------------------------------------
# Borda 3 — sinal
#
# P4 usava abs() e contestaria nos dois sentidos. A V2 fala em "+1%", e a
# variação negativa tem destino próprio (retificação, HU-21).
# ---------------------------------------------------------------------------


def test_operadora_cobrando_a_menos_nao_contesta():
    # operadora 90, expectativa 100 -> variação negativa.
    variacao = calcular_variacao(_serie(90.0), _serie(100.0))
    assert variacao.iloc[0] < 0
    assert deve_contestar(variacao).iloc[0] == FLAG_NAO_CONTESTAR


def test_operadora_cobrando_muito_a_menos_ainda_nao_contesta():
    # Com abs() isto daria 900% e contestaria. Com sinal, não.
    variacao = calcular_variacao(_serie(10.0), _serie(100.0))
    assert deve_contestar(variacao).iloc[0] == FLAG_NAO_CONTESTAR


def test_operadora_cobrando_a_mais_contesta():
    variacao = calcular_variacao(_serie(200.0), _serie(100.0))
    assert variacao.iloc[0] > 0
    assert deve_contestar(variacao).iloc[0] == FLAG_CONTESTAR


# ---------------------------------------------------------------------------
# Borda do limiar
# ---------------------------------------------------------------------------


def test_abaixo_do_limiar_nao_contesta():
    # 0,5% de variação.
    variacao = calcular_variacao(_serie(100.5), _serie(100.0))
    assert variacao.iloc[0] < 1.0
    assert deve_contestar(variacao).iloc[0] == FLAG_NAO_CONTESTAR


def test_exatamente_no_limiar_contesta():
    # Pendência residual Q2: a V2 diz "superior a 1%" (>), o código usa >=.
    variacao = pd.Series([1.0])
    assert deve_contestar(variacao).iloc[0] == FLAG_CONTESTAR


def test_acima_do_limiar_contesta():
    variacao = pd.Series([1.0001])
    assert deve_contestar(variacao).iloc[0] == FLAG_CONTESTAR


def test_limiar_e_parametrizavel():
    variacao = pd.Series([3.0])
    assert deve_contestar(variacao, limiar=0.05).iloc[0] == FLAG_NAO_CONTESTAR
    assert deve_contestar(variacao, limiar=0.01).iloc[0] == FLAG_CONTESTAR


# ---------------------------------------------------------------------------
# Robustez
# ---------------------------------------------------------------------------


def test_valores_nao_numericos_viram_zero():
    variacao = calcular_variacao(pd.Series(["abc"]), pd.Series(["def"]))
    assert variacao.iloc[0] == pytest.approx(0.0)


def test_valores_em_texto_sao_convertidos():
    variacao = calcular_variacao(pd.Series(["200"]), pd.Series(["100"]))
    assert variacao.iloc[0] == pytest.approx(50.0)


def test_preserva_o_indice_de_entrada():
    operadora = pd.Series([200.0, 100.0], index=["a", "b"])
    expectativa = pd.Series([100.0, 100.0], index=["a", "b"])
    variacao = calcular_variacao(operadora, expectativa)
    assert list(variacao.index) == ["a", "b"]


# ---------------------------------------------------------------------------
# aplicar() — a conveniência usada pelos dois consumidores
# ---------------------------------------------------------------------------


def test_aplicar_acrescenta_variacao_e_flag():
    df = pd.DataFrame({"vb_op": [200.0, 100.5], "vb_exp": [100.0, 100.0]})

    resultado = aplicar(
        df,
        coluna_operadora="vb_op",
        coluna_expectativa="vb_exp",
        coluna_variacao="vb_variacao_perc",
        coluna_flag="flag_contestacao",
    )

    assert list(resultado["flag_contestacao"]) == [FLAG_CONTESTAR, FLAG_NAO_CONTESTAR]
    assert resultado["vb_variacao_perc"].iloc[0] == pytest.approx(50.0)


def test_aplicar_nao_altera_o_dataframe_original():
    df = pd.DataFrame({"vb_op": [200.0], "vb_exp": [100.0]})
    colunas_antes = list(df.columns)

    aplicar(
        df,
        coluna_operadora="vb_op",
        coluna_expectativa="vb_exp",
        coluna_variacao="variacao",
    )

    assert list(df.columns) == colunas_antes


def test_aplicar_sem_coluna_flag_nao_cria_flag():
    df = pd.DataFrame({"vb_op": [200.0], "vb_exp": [100.0]})

    resultado = aplicar(
        df,
        coluna_operadora="vb_op",
        coluna_expectativa="vb_exp",
        coluna_variacao="variacao",
    )

    assert "variacao" in resultado.columns
    assert len(resultado.columns) == 3
