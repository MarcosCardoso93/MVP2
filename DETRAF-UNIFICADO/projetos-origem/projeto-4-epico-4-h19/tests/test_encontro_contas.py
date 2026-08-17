"""Testes da HU-19 — despesa da contestação (Épico 6, D-16 revisada / D-20).

**D-20 (2026-07-30, adequação à V2 pág. 38):** a escrita da HU-19 é um **UPDATE** dos
seis campos de despesa da operadora, não mais um INSERT da linha inteira. A linha-base
é inserida pelo Épico 3, fora do escopo deste projeto (B-D20).

Este módulo testa apenas a preparação pura do DataFrame
(`preparar_atualizacoes_despesa_contestacao`); a gravação é responsabilidade de
`RepositorioTabelas.atualizar_despesa_contestacao`, testada em
`test_repositorio_escrita.py`.
"""

import pandas as pd
import pytest

from src.services import encontro_contas as ec


def _linha_contest(
    eot_credora,
    eot_devedora,
    trafego,
    remuneracao="TU-RL",
    minutos_tbra=0.0,
    vb_tbra=0.0,
    minutos_operadora=0.0,
    vb_operadora=100.0,
    minutos_diferenca=0.0,
    vb_diferenca=50.0,
    minutos_variacao_perc=0.0,
    vb_variacao_perc=50.0,
    contestacao_a_enviar="N",
    tipo_operacao=None,
):
    linha = {
        "eot_credora": eot_credora,
        "eot_devedora": eot_devedora,
        "remuneracao": remuneracao,
        "trafego": trafego,
        "minutos_tbra": minutos_tbra,
        "vb_tbra": vb_tbra,
        "minutos_operadora": minutos_operadora,
        "vb_operadora": vb_operadora,
        "minutos_diferenca": minutos_diferenca,
        "vb_diferenca": vb_diferenca,
        "minutos_variacao_perc": minutos_variacao_perc,
        "vb_variacao_perc": vb_variacao_perc,
        "contestacao_a_enviar": contestacao_a_enviar,
    }
    if tipo_operacao is not None:
        linha["tipo_operacao"] = tipo_operacao
    return linha


def test_preparar_atualizacoes_vazio_retorna_vazio():
    resultado = ec.preparar_atualizacoes_despesa_contestacao(pd.DataFrame(), "202507")

    assert resultado.empty
    assert list(resultado.columns) == ec.COLUNAS_DESPESA_CONTESTACAO


def test_preparar_atualizacoes_inclui_todas_independente_de_contestacao_a_enviar():
    # Decisão do usuário (2026-07-28, mantida na D-20): TODAS as linhas do Contest são
    # atualizadas, não só as contestacao_a_enviar="S" — o analista precisa do panorama.
    df = pd.DataFrame(
        [
            _linha_contest("200", "011", "202507", contestacao_a_enviar="S"),
            _linha_contest("201", "012", "202507", contestacao_a_enviar="N"),
        ]
    )

    resultado = ec.preparar_atualizacoes_despesa_contestacao(df, "202507")

    assert resultado.shape[0] == 2


def test_preparar_atualizacoes_monta_a_chave_da_linha():
    df = pd.DataFrame([_linha_contest("200", "011", "202507")])

    linha = ec.preparar_atualizacoes_despesa_contestacao(df, "202507").iloc[0]

    assert linha["eot_operadora"] == "200"
    assert linha["eot_tbra"] == "011"
    assert linha["referencia"] == "202507"
    assert linha["trafego"] == "202507"
    assert linha["remuneracao"] == "TU-RL"


def test_preparar_atualizacoes_vb_operadora_e_vb_diferenca_sempre_negativos():
    df = pd.DataFrame(
        [
            _linha_contest("200", "011", "202507", vb_operadora=100.0, vb_diferenca=50.0),
            _linha_contest("201", "012", "202507", vb_operadora=-30.0, vb_diferenca=-10.0),
        ]
    )

    resultado = ec.preparar_atualizacoes_despesa_contestacao(df, "202507")

    assert (resultado["vb_operadora"] <= 0).all()
    assert (resultado["vb_diferenca"] <= 0).all()
    assert resultado.iloc[0]["vb_operadora"] == pytest.approx(-100.0)
    assert resultado.iloc[0]["vb_diferenca"] == pytest.approx(-50.0)
    assert resultado.iloc[1]["vb_operadora"] == pytest.approx(-30.0)
    assert resultado.iloc[1]["vb_diferenca"] == pytest.approx(-10.0)


def test_preparar_atualizacoes_nao_escreve_campos_de_outras_hus():
    # D-19/D-20: `tipo_contestacao` é regravado pela HU-16; `carga_agi` é da HU-18
    # (Épico 5, fora de escopo); o lado TBRA e `empresa` vêm do INSERT do Épico 3.
    df = pd.DataFrame([_linha_contest("200", "011", "202507", tipo_operacao="STFC")])

    resultado = ec.preparar_atualizacoes_despesa_contestacao(df, "202507")

    for coluna in (
        "tipo_contestacao",
        "carga_agi",
        "empresa",
        "tipo_servico_vivo",
        "minutos_tbra",
        "vb_tbra",
    ):
        assert coluna not in resultado.columns


def test_preparar_atualizacoes_atualiza_exatamente_os_seis_campos_da_v2():
    df = pd.DataFrame([_linha_contest("200", "011", "202507")])

    resultado = ec.preparar_atualizacoes_despesa_contestacao(df, "202507")

    assert ec.COLUNAS_ATUALIZADAS_DESPESA_CONTESTACAO == [
        "minutos_operadora",
        "vb_operadora",
        "minutos_diferenca",
        "vb_diferenca",
        "minutos_variacao_perc",
        "vb_variacao_perc",
    ]
    assert list(resultado.columns) == ec.COLUNAS_DESPESA_CONTESTACAO
