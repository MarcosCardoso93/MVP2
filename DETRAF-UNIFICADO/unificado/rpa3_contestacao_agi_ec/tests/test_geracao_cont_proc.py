"""Testes da HU-16 — colunas C-H do CONT_PROC (T-100), T-101 parcial e gravação (T-102).

Escopo: tudo exceto `ID_MODALIDADE` (residual de D-4 — máscara real não trouxe a aba de
modalidades). D-7 resolvida — grava `.xlsx`.
"""

from pathlib import Path

import pandas as pd
import pytest

from src.services import geracao_cont_proc as gcp


class _SinalFake:
    def __init__(self, respostas: dict[tuple, str | None]):
        self._respostas = respostas

    def __call__(self, eot_operadora, eot_tbra, referencia, trafego, remuneracao):
        return self._respostas.get((eot_operadora, eot_tbra, referencia, trafego, remuneracao))


def _contest_df(linhas: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(linhas)


def _linha_contestada(
    eot_credora,
    eot_devedora,
    trafego,
    remuneracao="TU-RL",
    contestacao_a_enviar="S",
    minutos_diferenca=100.0,
    vb_diferenca=10.0,
):
    return {
        "eot_credora": eot_credora,
        "eot_devedora": eot_devedora,
        "remuneracao": remuneracao,
        "trafego": trafego,
        "contestacao_a_enviar": contestacao_a_enviar,
        "minutos_diferenca": minutos_diferenca,
        "vb_diferenca": vb_diferenca,
    }


def test_df_vazio_retorna_vazio():
    resultado = gcp.montar_linhas_cont_proc(pd.DataFrame(), "202507", _SinalFake({}))
    assert resultado.empty


def test_exclui_linhas_sem_contestacao_a_enviar():
    df = _contest_df(
        [_linha_contestada("200", "011", "202507", contestacao_a_enviar="N")]
    )
    resultado = gcp.montar_linhas_cont_proc(df, "202507", _SinalFake({}))
    assert resultado.empty


def test_exclui_linha_com_flag_s_mas_sem_sinal_do_analista():
    # AI/09 §0: CONT_PROC so existe nos cenarios SEM/COM retencao, nunca "sem
    # contestacao" — mesmo com contestacao_a_enviar=S (variacao alta), se o analista
    # ainda nao decidiu (sinal None), a linha nao deve entrar.
    df = _contest_df([_linha_contestada("200", "011", "202507", contestacao_a_enviar="S")])
    resultado = gcp.montar_linhas_cont_proc(df, "202507", _SinalFake({}))
    assert resultado.empty


def test_flag_pag_rec_com_retencao():
    df = _contest_df([_linha_contestada("200", "011", "202507")])
    sinal = _SinalFake({("200", "011", "202507", "202507", "TU-RL"): "com retenção"})

    resultado = gcp.montar_linhas_cont_proc(df, "202507", sinal)

    assert resultado.shape[0] == 1
    linha = resultado.iloc[0]
    assert linha[gcp.COL_ID_OPERADORA_JV] == "011"
    assert linha[gcp.COL_ID_OPERADORA_PREST] == "200"
    assert linha[gcp.COL_ID_PERIODO_REF] == "202507"
    assert linha[gcp.COL_ID_PERIODO_TRAF] == "202507"
    assert linha[gcp.COL_DEBIT_CREDIT] == "D"
    assert linha[gcp.COL_FLAG_PAG_REC] == "P"


def test_flag_pag_rec_sem_retencao():
    df = _contest_df([_linha_contestada("200", "011", "202507")])
    sinal = _SinalFake({("200", "011", "202507", "202507", "TU-RL"): "sem retenção"})

    resultado = gcp.montar_linhas_cont_proc(df, "202507", sinal)

    assert resultado.iloc[0][gcp.COL_FLAG_PAG_REC] == "R"


def test_multiplas_linhas_mistas():
    df = _contest_df(
        [
            _linha_contestada("200", "011", "202507"),
            _linha_contestada(
                "201", "012", "202507", remuneracao="VU-M", contestacao_a_enviar="N"
            ),
        ]
    )
    sinal = _SinalFake({("200", "011", "202507", "202507", "TU-RL"): "com retenção"})

    resultado = gcp.montar_linhas_cont_proc(df, "202507", sinal)

    assert resultado.shape[0] == 1
    assert resultado.iloc[0][gcp.COL_ID_OPERADORA_PREST] == "200"


# --------------------------------------------------------------------------
# T-101 (parcial) — DURACAO/VLR_BRUTO negativos, REMUNERACAO_FIXA, ID_MODALIDADE placeholder
# --------------------------------------------------------------------------
def test_duracao_e_vlr_bruto_sao_negativos_da_diferenca():
    """
    ⚠️ **As duas colunas recebem MINUTAGEM** — decisão do PO, 2026-08-06 (Q11).

    A V2 (¶643) manda preencher `VLR_BRUTO` com *"a minutagem total da linha"*,
    texto idêntico ao da coluna `DURACAO`. Parecia erro de redação, e o código
    gravava o valor (`vb_diferenca`) com a divergência registrada como pendência
    — **porque é dado financeiro carregado no AGI**, onde errar não é reversível.

    Perguntado ao PO e respondido: **não é o valor bruto**. Este teste fixa isso.

    O `vb_diferenca` da fixture continua diferente da minutagem de propósito: se
    alguém reintroduzir o valor, o teste falha em vez de passar por coincidência.
    """
    df = _contest_df(
        [_linha_contestada("200", "011", "202507", minutos_diferenca=48316.5, vb_diferenca=295.23)]
    )
    sinal = _SinalFake({("200", "011", "202507", "202507", "TU-RL"): "com retenção"})

    resultado = gcp.montar_linhas_cont_proc(df, "202507", sinal)

    linha = resultado.iloc[0]
    assert linha[gcp.COL_DURACAO] == pytest.approx(-48316.5)
    assert linha[gcp.COL_VLR_BRUTO] == pytest.approx(-48316.5)
    assert linha[gcp.COL_VLR_BRUTO] != pytest.approx(-295.23), "não é o valor bruto"


def test_remuneracao_fixa_vem_do_contest():
    df = _contest_df([_linha_contestada("200", "011", "202507", remuneracao="TU-COM")])
    sinal = _SinalFake({("200", "011", "202507", "202507", "TU-COM"): "com retenção"})

    resultado = gcp.montar_linhas_cont_proc(df, "202507", sinal)

    assert resultado.iloc[0][gcp.COL_REMUNERACAO_FIXA] == "TU-COM"


def test_id_modalidade_e_sempre_00():
    # D-4 resolvida (2026-07-23): usuário confirmou valor fixo "00" a partir dos 2
    # exemplos reais da máscara (ambos com ID_MODALIDADE="00", remunerações diferentes).
    df = _contest_df([_linha_contestada("200", "011", "202507")])
    sinal = _SinalFake({("200", "011", "202507", "202507", "TU-RL"): "com retenção"})

    resultado = gcp.montar_linhas_cont_proc(df, "202507", sinal)

    assert resultado.iloc[0][gcp.COL_ID_MODALIDADE] == "00"


# --------------------------------------------------------------------------
# T-102 — gravação (D-7 resolvida: .xlsx)
# --------------------------------------------------------------------------
def test_gerar_arquivo_nao_grava_quando_vazio(tmp_path: Path):
    caminho = gcp.gerar_arquivo_cont_proc(
        pd.DataFrame(), operadora="Claro", aaaamm="202507", raiz_operadoras=tmp_path
    )
    assert caminho is None
    assert not any(tmp_path.rglob("*.xlsx"))


def test_gerar_arquivo_grava_no_caminho_e_nome_corretos(tmp_path: Path):
    df = _contest_df([_linha_contestada("200", "011", "202507")])
    sinal = _SinalFake({("200", "011", "202507", "202507", "TU-RL"): "com retenção"})
    linhas = gcp.montar_linhas_cont_proc(df, "202507", sinal)

    caminho = gcp.gerar_arquivo_cont_proc(
        linhas, operadora="Claro", aaaamm="202507", raiz_operadoras=tmp_path
    )

    assert caminho.name == "CONT_PROC_MASCARA_Claro_202507.xlsx"
    assert caminho.parent == tmp_path / "Claro" / "2025" / "202507" / "AGI"
    assert caminho.is_file()


# ---------------------------------------------------------------------------
# T-153 — gate extraído (`selecionar_linhas_contestadas`), compartilhado com o
# writeback de `tipo_contestacao` (D-19).
# ---------------------------------------------------------------------------
# Nomes de COLUNA DO BANCO — a saída do gate alimenta `atualizar_tipo_contestacao`.
# Daí `remuneracoes`, no plural; o frame de domínio que entra usa o singular.
COLUNAS_GATE = [
    "eot_operadora",
    "eot_tbra",
    "referencia",
    "trafego",
    "remuneracoes",
    "tipo_contestacao",
]


def test_gate_df_vazio_retorna_vazio_com_o_schema_da_chave():
    resultado = gcp.selecionar_linhas_contestadas(pd.DataFrame(), "202507", _SinalFake({}))

    assert resultado.empty
    assert list(resultado.columns) == COLUNAS_GATE


def test_gate_cenario_sem_contestacao_exclui_linha():
    # Flag "N" (variação abaixo do limiar) => não contestada.
    df = _contest_df(
        [_linha_contestada("200", "011", "202507", contestacao_a_enviar="N")]
    )

    assert gcp.selecionar_linhas_contestadas(df, "202507", _SinalFake({})).empty


def test_gate_flag_s_sem_sinal_do_analista_exclui_linha():
    # D-14: os dois sinais são necessários. Variação alta sem decisão do analista
    # ainda é "sem contestação" — não vai para o CONT_PROC nem para o writeback.
    df = _contest_df([_linha_contestada("200", "011", "202507")])

    assert gcp.selecionar_linhas_contestadas(df, "202507", _SinalFake({})).empty


@pytest.mark.parametrize("sinal_analista", ["sem retenção", "com retenção"])
def test_gate_cenarios_sem_e_com_retencao_selecionam_a_linha(sinal_analista):
    df = _contest_df([_linha_contestada("200", "011", "202507")])
    sinal = _SinalFake({("200", "011", "202507", "202507", "TU-RL"): sinal_analista})

    resultado = gcp.selecionar_linhas_contestadas(df, "202507", sinal)

    assert resultado.shape[0] == 1
    linha = resultado.iloc[0]
    assert linha["eot_operadora"] == "200"
    assert linha["eot_tbra"] == "011"
    assert linha["referencia"] == "202507"
    assert linha["trafego"] == "202507"
    assert linha["remuneracoes"] == "TU-RL"
    # Eco do sinal aplicado (D-19): é exatamente o valor que o CONT_PROC usou.
    assert linha["tipo_contestacao"] == sinal_analista


def test_gate_preserva_o_indice_do_contest():
    # `montar_linhas_cont_proc` recupera as demais colunas por `.loc` — o índice
    # precisa casar com o do `Contest`.
    df = _contest_df(
        [
            _linha_contestada("200", "011", "202507", contestacao_a_enviar="N"),
            _linha_contestada("201", "012", "202507", remuneracao="VU-M"),
        ]
    )
    sinal = _SinalFake({("201", "012", "202507", "202507", "VU-M"): "com retenção"})

    resultado = gcp.selecionar_linhas_contestadas(df, "202507", sinal)

    assert list(resultado.index) == [1]


def test_gate_consulta_o_sinal_uma_vez_por_chave_unica():
    class _SinalContador(_SinalFake):
        def __init__(self, respostas):
            super().__init__(respostas)
            self.chamadas = 0

        def __call__(self, *args):
            self.chamadas += 1
            return super().__call__(*args)

    # Três linhas, duas chaves distintas.
    df = _contest_df(
        [
            _linha_contestada("200", "011", "202507"),
            _linha_contestada("200", "011", "202507"),
            _linha_contestada("201", "012", "202507", remuneracao="VU-M"),
        ]
    )
    sinal = _SinalContador(
        {
            ("200", "011", "202507", "202507", "TU-RL"): "com retenção",
            ("201", "012", "202507", "202507", "VU-M"): "sem retenção",
        }
    )

    gcp.selecionar_linhas_contestadas(df, "202507", sinal)

    assert sinal.chamadas == 2
