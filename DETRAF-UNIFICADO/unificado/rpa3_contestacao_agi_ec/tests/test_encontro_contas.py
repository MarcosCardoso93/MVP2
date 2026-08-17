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

from comum.config import constantes as const
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
    # Saída = payload do banco, então a coluna é `remuneracoes` (plural). A
    # ENTRADA (`_linha_contest`) é o frame de domínio e usa `remuneracao`. As
    # duas grafias estão certas; a tradução é o que este teste verifica.
    assert linha["remuneracoes"] == "TU-RL"


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


def test_preparar_atualizacoes_atualiza_os_seis_campos_da_v2_mais_o_942():
    """
    Os seis da V2 pág. 38 (D-20) **e mais nenhum**, exceto o `vb_contestacao`
    acrescentado pela Q24 em 2026-08-05 — que é regra do ¶942 (bloco antigo da V2
    e V1), não do texto vigente, e está registrado como acréscimo da unificação.
    """
    df = pd.DataFrame([_linha_contest("200", "011", "202507")])

    resultado = ec.preparar_atualizacoes_despesa_contestacao(df, "202507")

    assert ec.COLUNAS_ATUALIZADAS_DESPESA_CONTESTACAO == [
        "minutos_operadora",
        "vb_operadora",
        "minutos_diferenca",
        "vb_diferenca",
        "minutos_variacao_perc",
        "vb_variacao_perc",
        "vb_contestacao",
    ]
    assert list(resultado.columns) == ec.COLUNAS_DESPESA_CONTESTACAO


# ---------------------------------------------------------------------------
# Q24 — a coluna do ¶942
# ---------------------------------------------------------------------------


def _sinal_fixo(mapa: dict):
    """Dublê de `obter_tipo_contestacao`, indexado pela chave de negócio."""

    def _obter(eot_operadora, eot_tbra, referencia, trafego, remuneracao):
        return mapa.get((eot_operadora, eot_tbra, referencia, trafego, remuneracao))

    return _obter


def test_vb_contestacao_so_e_preenchido_na_linha_com_retencao():
    """
    ¶942: *"Quando acontece a contestação com retenção, o robô também preenche a
    coluna de contestação [...] com o valor bruto da Diferença apresentada aba
    Contest."* A linha SEM retenção fica vazia, não zero — zero diria "nada
    retido apurado", e o que se quer dizer é "não se aplica".
    """
    com = _linha_contest("021", "011", "202507")
    sem = _linha_contest("021", "012", "202507")
    df = pd.DataFrame([com, sem])

    resultado = ec.preparar_atualizacoes_despesa_contestacao(
        df,
        "202507",
        obter_tipo_contestacao=_sinal_fixo(
            {
                ("021", "011", "202507", com["trafego"], com["remuneracao"]): const.CENARIO_COM_RETENCAO,
                ("021", "012", "202507", sem["trafego"], sem["remuneracao"]): const.CENARIO_SEM_RETENCAO,
            }
        ),
    )

    assert resultado.loc[0, "vb_contestacao"] == resultado.loc[0, "vb_diferenca"]
    assert resultado.loc[1, "vb_contestacao"] is None


def test_vb_contestacao_e_negativo_como_o_resto_da_despesa():
    linha = _linha_contest("021", "011", "202507")
    df = pd.DataFrame([linha])

    resultado = ec.preparar_atualizacoes_despesa_contestacao(
        df,
        "202507",
        obter_tipo_contestacao=lambda *_: const.CENARIO_COM_RETENCAO,
    )

    assert resultado.loc[0, "vb_contestacao"] < 0


def test_sem_a_leitura_do_sinal_a_coluna_sai_vazia():
    """A parte pura da HU-19 continua testável sem banco."""
    df = pd.DataFrame([_linha_contest("021", "011", "202507")])

    resultado = ec.preparar_atualizacoes_despesa_contestacao(df, "202507")

    assert resultado["vb_contestacao"].isna().all()
    assert resultado["vb_contestacao"].tolist() == [None]


def test_linha_sem_sinal_algum_nao_recebe_valor():
    """`None` do banco significa "sem contestação" — não é COM retenção."""
    df = pd.DataFrame([_linha_contest("021", "011", "202507")])

    resultado = ec.preparar_atualizacoes_despesa_contestacao(
        df, "202507", obter_tipo_contestacao=lambda *_: None
    )

    assert resultado.loc[0, "vb_contestacao"] is None
