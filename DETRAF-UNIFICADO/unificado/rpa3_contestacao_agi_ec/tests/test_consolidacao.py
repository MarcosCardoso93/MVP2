"""Testes da Consolidação — abas `{operadora}`/`TBRA`/`RESUMO`/`Contest`
(T-020..T-023).

Valida a mecânica de concatenação + remoção de linhas de total. O índice da
coluna de total das fixtures ALGAR é **5** (ver D-8: o índice varia por layout,
por isso é parametrizável).
"""

import shutil
from pathlib import Path

import pandas as pd
import pytest

from src.services import consolidacao_contestacao as cc
from src.services import mapa_remuneracao as mr

FIXTURES = Path(__file__).parent / "fixtures" / "detraf"
FIXTURES_EXP = Path(__file__).parent / "fixtures" / "expectativa"

# Nas fixtures ALGAR a coluna de total (tipo_relatorio/Rel) fica no índice 5.
INDICE_TOTAL_ALGAR = 5
# Na expectativa Vivo a coluna REL fica no índice 6 (ver D-8 / fixtures/README).
INDICE_TOTAL_VIVO = 6


@pytest.fixture
def pasta_operadora(tmp_path: Path) -> Path:
    """Pasta temporária com os dois layouts ALGAR (SMP + STFC)."""

    pasta = tmp_path / "Detrafs Recebidos"
    pasta.mkdir()
    shutil.copy(FIXTURES / "algar_smp_reduzido.csv", pasta / "algar_smp.csv")
    shutil.copy(FIXTURES / "algar_stfc_reduzido.csv", pasta / "algar_stfc.csv")
    return pasta


def test_listar_arquivos_pasta_inexistente(tmp_path: Path):
    assert cc.listar_arquivos_detraf(tmp_path / "nao_existe") == []


def test_consolida_e_remove_totais(pasta_operadora: Path):
    df = cc.consolidar_detrafs_operadora(
        pasta_operadora, indice_total=INDICE_TOTAL_ALGAR
    )
    # SMP: 5 linhas - 1 total = 4; STFC: 4 linhas (cabeçalho removido) - 1 total = 3.
    assert df.shape[0] == 7
    # Nenhuma linha de total remanescente.
    assert not (df.iloc[:, INDICE_TOTAL_ALGAR] == "1").any()
    # Lido como string (L-006).
    assert df.iloc[:, 0].map(type).eq(str).all()


def test_pasta_vazia_retorna_df_vazio(tmp_path: Path):
    pasta = tmp_path / "vazia"
    pasta.mkdir()
    df = cc.consolidar_detrafs_operadora(pasta)
    assert df.empty


def test_fail_fast_colunas_insuficientes(tmp_path: Path):
    pasta = tmp_path / "Detrafs Recebidos"
    pasta.mkdir()
    (pasta / "curto.csv").write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    with pytest.raises(ValueError):
        cc.consolidar_detrafs_operadora(pasta)


# --------------------------------------------------------------------------
# T-021 — aba TBRA (expectativa Vivo)
# --------------------------------------------------------------------------
@pytest.fixture
def pasta_enviados(tmp_path: Path) -> Path:
    """Pasta com um arquivo de expectativa Vivo (_D) e um arquivo não-_D (ruído)."""

    pasta = tmp_path / "Detrafs Enviados"
    pasta.mkdir()
    shutil.copy(
        FIXTURES_EXP / "vivo_d_reduzido.csv",
        pasta / "DETRAF_FINAL_TRP_202605_CTB_STF_VIVO_D.csv",
    )
    # Arquivo sem _D no nome: deve ser ignorado pela aba TBRA.
    shutil.copy(FIXTURES / "algar_smp_reduzido.csv", pasta / "ruido_sem_marcador.csv")
    return pasta


def test_eh_arquivo_expectativa():
    assert cc.eh_arquivo_expectativa(Path("X_VIVO_D.csv"))
    assert cc.eh_arquivo_expectativa(Path("a_D_b.csv"))
    assert not cc.eh_arquivo_expectativa(Path("algar_smp.csv"))


def test_consolida_expectativa_filtra_D_e_remove_totais(pasta_enviados: Path):
    df = cc.consolidar_expectativa_vivo(
        pasta_enviados, indice_total=INDICE_TOTAL_VIVO
    )
    # Só o arquivo _D entra: 4 linhas de dados - 1 total = 3.
    assert df.shape[0] == 3
    assert not (df.iloc[:, INDICE_TOTAL_VIVO] == "1").any()


def test_expectativa_truncamento_ate_coluna(pasta_enviados: Path):
    df = cc.consolidar_expectativa_vivo(
        pasta_enviados, indice_total=INDICE_TOTAL_VIVO, indice_ultima_coluna=5
    )
    # Corte "até R$_Bruto" (parametrizado): mantém colunas 0..5 => 6 colunas.
    assert df.shape[1] == 6


def test_expectativa_sem_arquivo_D_retorna_vazio(tmp_path: Path):
    pasta = tmp_path / "Detrafs Enviados"
    pasta.mkdir()
    shutil.copy(FIXTURES / "algar_smp_reduzido.csv", pasta / "sem_marcador.csv")
    assert cc.consolidar_expectativa_vivo(pasta).empty


# --------------------------------------------------------------------------
# T-022 — aba RESUMO
# --------------------------------------------------------------------------
def _df_15_colunas(linhas: list[list[str]]) -> pd.DataFrame:
    """Monta um DataFrame com 15 colunas (índices 0..14, como no layout §6)."""

    return pd.DataFrame(linhas)


def test_montar_resumo_agrupa_por_referencia_e_trafego():
    # colunas: 0 credora,1 devedora,2 referencia,3 trafego,...,9 minutos,...,14 r_bruto
    linhas = [
        ["021", "011", "202507", "202507", "0", "p", "d", "N", "1", "10,5", "0,01", "0,1", "0", "0", "0,1"],
        ["021", "011", "202507", "202507", "0", "p", "d", "N", "1", "5,5", "0,01", "0,1", "0", "0", "0,05"],
        ["021", "011", "202507", "202506", "0", "p", "d", "N", "1", "2,0", "0,01", "0,1", "0", "0", "0,02"],
    ]
    df = _df_15_colunas(linhas)
    resumo = cc.montar_resumo(df)
    assert resumo.shape[0] == 2  # duas combinações Referência x Tráfego
    linha_202507 = resumo[resumo["Tráfego"] == "202507"].iloc[0]
    assert linha_202507["Minutos"] == pytest.approx(16.0)
    assert linha_202507["R$_Bruto"] == pytest.approx(0.15)


def test_montar_resumo_vazio_retorna_df_vazio_com_colunas():
    resumo = cc.montar_resumo(pd.DataFrame())
    assert resumo.empty
    assert list(resumo.columns) == ["Referência", "Tráfego", "Minutos", "R$_Bruto"]


# --------------------------------------------------------------------------
# T-023 — aba Contest
# --------------------------------------------------------------------------
INDICE_DESCRITOR_TESTE = 6  # posição arbitrária controlada pelo teste (sem posição fixa na doc)


def _linha_contest(credora, devedora, referencia, trafego, descritor, minutos, r_bruto):
    linha = ["0"] * 15
    linha[0] = credora
    linha[1] = devedora
    linha[2] = referencia
    linha[3] = trafego
    linha[6] = descritor
    linha[9] = minutos
    linha[14] = r_bruto
    return linha


def test_montar_contest_bate_com_exemplo_real_da_carta(indice_remuneracao):
    # Exemplo real do ToBe (screenshot da carta CT-334/2025, EOT 11/200, STFC):
    # TBRA: Minutos 4.790,20 / VB 29,18 | AMPERNET (operadora): Minutos 53.106,70 / VB 324,41
    # Diferença: Minutos 48.316,5 / VB 295,23 | Variação: 91,0% / 91,0%
    df_operadora = _df_15_colunas(
        [_linha_contest("200", "011", "202506", "202506", "XPTO_L", "53106,70", "324,41")]
    )
    df_tbra = _df_15_colunas(
        [_linha_contest("200", "011", "202506", "202506", "XPTO_L", "4790,20", "29,18")]
    )

    contest = cc.montar_contest(
        df_operadora, df_tbra, INDICE_DESCRITOR_TESTE, indice_remuneracao
    )

    assert contest.shape[0] == 1
    linha = contest.iloc[0]
    assert linha["eot_devedora"] == "011"
    assert linha["eot_credora"] == "200"
    assert linha["minutos_operadora"] == pytest.approx(53106.70)
    assert linha["vb_operadora"] == pytest.approx(324.41)
    assert linha["minutos_tbra"] == pytest.approx(4790.20)
    assert linha["vb_tbra"] == pytest.approx(29.18)
    assert linha["minutos_diferenca"] == pytest.approx(48316.5, abs=0.1)
    assert linha["vb_diferenca"] == pytest.approx(295.23, abs=0.01)
    assert round(linha["minutos_variacao_perc"], 1) == pytest.approx(91.0)
    assert round(linha["vb_variacao_perc"], 1) == pytest.approx(91.0)
    assert linha["contestacao_a_enviar"] == "S"


def test_montar_contest_variacao_abaixo_do_limiar_marca_N(indice_remuneracao):
    df_operadora = _df_15_colunas(
        [_linha_contest("200", "011", "202506", "202506", "XPTO_L", "1000,0", "100,00")]
    )
    df_tbra = _df_15_colunas(
        [_linha_contest("200", "011", "202506", "202506", "XPTO_L", "1000,0", "100,50")]
    )
    contest = cc.montar_contest(
        df_operadora, df_tbra, INDICE_DESCRITOR_TESTE, indice_remuneracao
    )
    linha = contest.iloc[0]
    assert linha["vb_variacao_perc"] < 1.0
    assert linha["contestacao_a_enviar"] == "N"


def test_montar_contest_par_ausente_lado_zerado(indice_remuneracao):
    # Só a operadora tem tráfego para esta combinação; TBRA não tem par (AI/09 §1: zerado).
    df_operadora = _df_15_colunas(
        [_linha_contest("200", "011", "202506", "202506", "XPTO_L", "500,0", "50,00")]
    )
    df_tbra = _df_15_colunas([])

    contest = cc.montar_contest(
        df_operadora, df_tbra, INDICE_DESCRITOR_TESTE, indice_remuneracao
    )
    linha = contest.iloc[0]
    assert linha["minutos_tbra"] == 0.0
    assert linha["vb_tbra"] == 0.0
    assert linha["contestacao_a_enviar"] == "S"  # par ausente => variação 100%


def test_montar_contest_descritor_nao_mapeado_e_ignorado(indice_remuneracao):
    # Final 'I' não existe no mapa real (ver test_mapa_remuneracao) => linha ignorada.
    df_operadora = _df_15_colunas(
        [_linha_contest("200", "011", "202506", "202506", "2NENI", "500,0", "50,00")]
    )
    df_tbra = _df_15_colunas([])
    contest = cc.montar_contest(
        df_operadora, df_tbra, INDICE_DESCRITOR_TESTE, indice_remuneracao
    )
    assert contest.empty


def test_montar_contest_descritor_antes_ambiguo_agora_resolvido(indice_remuneracao):
    # Final 'T' colidia entre TU-RIU/VU-T no mapa real; D-5 (2026-07-27) resolveu
    # deterministicamente via produto=DETRAF + primeira ocorrência (vence TU-RIU) — a
    # linha não é mais ignorada.
    df_operadora = _df_15_colunas(
        [_linha_contest("200", "011", "202506", "202506", "XPTO_T", "500,0", "50,00")]
    )
    df_tbra = _df_15_colunas([])
    contest = cc.montar_contest(
        df_operadora, df_tbra, INDICE_DESCRITOR_TESTE, indice_remuneracao
    )
    assert not contest.empty
    assert contest.iloc[0]["remuneracao"] == "TU-RIU"


def test_montar_contest_tipo_operacao_opcional(indice_remuneracao):
    df_operadora = _df_15_colunas(
        [_linha_contest("200", "011", "202506", "202506", "XPTO_L", "500,0", "50,00")]
    )
    df_tbra = _df_15_colunas([])
    contest = cc.montar_contest(
        df_operadora,
        df_tbra,
        INDICE_DESCRITOR_TESTE,
        indice_remuneracao,
        mapa_tipo_operacao={"011": "STFC"},
    )
    assert contest.iloc[0]["tipo_operacao"] == "STFC"
