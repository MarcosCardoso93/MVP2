"""Testes da orquestração das escritas em banco (D-19/D-20, 2026-07-30).

O controller é o único ponto que combina service + repositório: os services não
acessam banco (AI/01 §1). Aqui verificamos a **ordem** exigida pela V2 — o writeback de
`tipo_contestacao` (HU-16) só ocorre **depois** de o CONT_PROC ser efetivamente gravado.

A orquestração completa do Épico 4 (consolidação → EXT → INT → _ENV/carta) continua
pendente em T-120.
"""

from pathlib import Path

import pandas as pd
import pytest

from src.controllers.geracao_agi_controller import GeracaoAgiController


def _linha_contest(
    eot_credora="021",
    eot_devedora="011",
    trafego="202507",
    remuneracao="TU-RL",
    contestacao_a_enviar="S",
):
    return {
        "eot_credora": eot_credora,
        "eot_devedora": eot_devedora,
        "remuneracao": remuneracao,
        "trafego": trafego,
        "contestacao_a_enviar": contestacao_a_enviar,
        "minutos_operadora": 777.0,
        "vb_operadora": 42.0,
        "minutos_diferenca": 111.0,
        "vb_diferenca": 42.0,
        "minutos_variacao_perc": 100.0,
        "vb_variacao_perc": 100.0,
    }


@pytest.fixture
def controller(repo_tabelas) -> GeracaoAgiController:
    return GeracaoAgiController(repositorio=repo_tabelas)


def test_gerar_cont_proc_grava_arquivo_e_regrava_o_sinal(controller, tmp_path: Path):
    # Seed: (021, 011, 202507, 202507, TU-RL) com sinal "com retenção".
    df = pd.DataFrame([_linha_contest()])

    caminho = controller.gerar_cont_proc(
        df_contest=df, operadora="Claro", referencia="202507", raiz_operadoras=tmp_path
    )

    assert caminho is not None and caminho.is_file()

    # D-19 — eco do sinal aplicado: o valor no banco é o mesmo usado no arquivo.
    assert controller.repositorio.obter_tipo_contestacao(
        eot_operadora="021", eot_tbra="011", referencia="202507",
        trafego="202507", remuneracao="TU-RL",
    ) == "com retenção"


def test_gerar_cont_proc_sem_contestacao_nao_gera_nem_regrava(controller, tmp_path: Path):
    # Chave sem linha no banco => sem sinal do analista => cenário "sem contestação".
    df = pd.DataFrame([_linha_contest(eot_credora="999", remuneracao="TU-COM")])

    caminho = controller.gerar_cont_proc(
        df_contest=df, operadora="Claro", referencia="202507", raiz_operadoras=tmp_path
    )

    assert caminho is None
    assert not any(tmp_path.rglob("*.xlsx"))


def test_atualizar_despesa_contestacao_delega_e_devolve_o_resumo(controller):
    df = pd.DataFrame([_linha_contest()])

    resumo = controller.atualizar_despesa_contestacao(df_contest=df, referencia="202507")

    # `colunas_ignoradas` traz a `vb_contestacao`, que o banco real não tem
    # (Q24) — o controller repassa o resumo do repositório inteiro.
    assert resumo == {
        "atualizadas": 1,
        "ausentes": [],
        "colunas_ignoradas": ["vb_contestacao"],
    }

    tabela = controller.repositorio.tbl_contestacao
    linha = tabela[tabela["id"] == 1].iloc[0]
    assert linha["minutos_operadora"] == pytest.approx(777.0)
    assert linha["vb_operadora"] == pytest.approx(-42.0)
