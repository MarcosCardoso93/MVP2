"""Testes da escrita em banco (D-19/D-20, adequação à V2 — 2026-07-30).

Cobre:

- `RepositorioCache.atualizar_dados` — UPDATE parametrizado e transacional, único
  caminho de atualização do repositório (AI/01 §1);
- `RepositorioTabelas.atualizar_despesa_contestacao` — HU-19, os seis campos de despesa
  da operadora (V2 pág. 38, D-20);
- `RepositorioTabelas.atualizar_tipo_contestacao` — HU-16, eco do sinal aplicado após a
  geração do CONT_PROC (V2 pág. 34, D-19).

O seed de `tests/conftest.py` tem duas linhas: `(021, 011, 202507, 202507, TU-RL)` com
sinal "com retenção" e `(021, 012, 202507, 202507, VU-M)` com "sem retenção".
"""

import pandas as pd
import pytest

from src.models.repository.repositorio_cache import RepositorioCache
from src.services import encontro_contas as ec

TABELA = "tbl_rpa_log_detraf_despesa_contestacao"


def _linha_contest(
    eot_credora,
    eot_devedora,
    trafego,
    remuneracao="TU-RL",
    vb_operadora=42.0,
    vb_diferenca=42.0,
):
    return {
        "eot_credora": eot_credora,
        "eot_devedora": eot_devedora,
        "remuneracao": remuneracao,
        "trafego": trafego,
        "minutos_tbra": 0.0,
        "vb_tbra": 0.0,
        "minutos_operadora": 777.0,
        "vb_operadora": vb_operadora,
        "minutos_diferenca": 111.0,
        "vb_diferenca": vb_diferenca,
        "minutos_variacao_perc": 100.0,
        "vb_variacao_perc": 100.0,
    }


# ---------------------------------------------------------------------------
# RepositorioCache.atualizar_dados (T-150)
# ---------------------------------------------------------------------------
def test_atualizar_dados_aplica_update_e_retorna_rowcount(repo_cache):
    afetadas = repo_cache.atualizar_dados(
        nome_tabela=TABELA, valores={"vb_operadora": -9.5}, chave={"id": 1}
    )

    assert afetadas == 1

    tabela = repo_cache.obter_tabela(TABELA)
    assert tabela[tabela["id"] == 1].iloc[0]["vb_operadora"] == pytest.approx(-9.5)


def test_atualizar_dados_chave_inexistente_retorna_zero(repo_cache):
    afetadas = repo_cache.atualizar_dados(
        nome_tabela=TABELA, valores={"vb_operadora": -1.0}, chave={"id": 9999}
    )

    assert afetadas == 0


def test_atualizar_dados_sem_chave_levanta(repo_cache):
    # Um UPDATE sem WHERE atingiria a tabela inteira.
    with pytest.raises(ValueError):
        repo_cache.atualizar_dados(
            nome_tabela=TABELA, valores={"vb_operadora": 0.0}, chave={}
        )


def test_atualizar_dados_rejeita_tabela_desconhecida(repo_cache):
    with pytest.raises(KeyError):
        repo_cache.atualizar_dados(
            nome_tabela="tbl_inexistente", valores={"x": 1}, chave={"id": 1}
        )


def test_inserir_dados_rejeita_tabela_desconhecida(repo_cache):
    with pytest.raises(KeyError):
        repo_cache.inserir_dados("tbl_inexistente", pd.DataFrame([{"x": 1}]))


def test_inserir_dados_vazio_nao_falha(repo_cache):
    repo_cache.inserir_dados(TABELA, pd.DataFrame())

    assert len(repo_cache.obter_tabela(TABELA)) == 2


def test_atualizar_dados_nao_vaza_valor_para_a_sql(repo_cache):
    # A SQL é parametrizada: um valor com aspas/; é gravado literalmente, não executado.
    malicioso = "'; DROP TABLE tbl_rpa_log_detraf_despesa_contestacao; --"

    repo_cache.atualizar_dados(
        nome_tabela=TABELA, valores={"tipo_contestacao": malicioso}, chave={"id": 1}
    )

    tabela = repo_cache.obter_tabela(TABELA)
    assert len(tabela) == 2
    assert tabela[tabela["id"] == 1].iloc[0]["tipo_contestacao"] == malicioso


# ---------------------------------------------------------------------------
# HU-19 — atualizar_despesa_contestacao (T-152 / D-20)
# ---------------------------------------------------------------------------
def test_atualizar_despesa_atualiza_os_seis_campos_sem_criar_linha(repo_tabelas):
    df_contest = pd.DataFrame([_linha_contest("021", "011", "202507")])
    linhas = ec.preparar_atualizacoes_despesa_contestacao(df_contest, "202507")

    total_antes = len(repo_tabelas.tbl_contestacao)
    resumo = repo_tabelas.atualizar_despesa_contestacao(linhas)

    assert resumo == {"atualizadas": 1, "ausentes": []}
    # D-20: a HU-19 nunca insere — a linha-base é do Épico 3.
    assert len(repo_tabelas.tbl_contestacao) == total_antes

    alvo = repo_tabelas.tbl_contestacao
    linha = alvo[alvo["id"] == 1].iloc[0]
    assert linha["minutos_operadora"] == pytest.approx(777.0)
    assert linha["vb_operadora"] == pytest.approx(-42.0)
    assert linha["minutos_diferenca"] == pytest.approx(111.0)
    assert linha["vb_diferenca"] == pytest.approx(-42.0)


def test_atualizar_despesa_preserva_lado_tbra_e_sinal_do_analista(repo_tabelas):
    df_contest = pd.DataFrame([_linha_contest("021", "011", "202507")])
    linhas = ec.preparar_atualizacoes_despesa_contestacao(df_contest, "202507")

    repo_tabelas.atualizar_despesa_contestacao(linhas)

    alvo = repo_tabelas.tbl_contestacao
    linha = alvo[alvo["id"] == 1].iloc[0]
    # Colunas do INSERT do Épico 3 permanecem intactas.
    assert linha["vb_tbra"] == pytest.approx(29.18)
    assert linha["empresa"] == "CLARO"
    assert linha["tipo_contestacao"] == "com retenção"


def test_atualizar_despesa_chave_ausente_nao_aborta_o_lote(repo_tabelas):
    # B-D20: sem o INSERT do Épico 3 a chave não existe — vira WARNING no resumo.
    df_contest = pd.DataFrame(
        [
            _linha_contest("021", "011", "202507"),
            _linha_contest("999", "099", "202507", remuneracao="TU-COM"),
        ]
    )
    linhas = ec.preparar_atualizacoes_despesa_contestacao(df_contest, "202507")

    resumo = repo_tabelas.atualizar_despesa_contestacao(linhas)

    assert resumo["atualizadas"] == 1
    assert len(resumo["ausentes"]) == 1
    assert resumo["ausentes"][0]["eot_operadora"] == "999"


def test_atualizar_despesa_lote_vazio_nao_falha(repo_tabelas):
    resumo = repo_tabelas.atualizar_despesa_contestacao(pd.DataFrame())

    assert resumo == {"atualizadas": 0, "ausentes": []}


def test_atualizar_despesa_normaliza_eot_como_a_leitura_do_sinal(repo_tabelas):
    # O Detraf traz "21"/"11"; o banco guarda "021"/"011" (L-006 + _tratar_eot).
    df_contest = pd.DataFrame([_linha_contest("21", "11", "202507")])
    linhas = ec.preparar_atualizacoes_despesa_contestacao(df_contest, "202507")

    resumo = repo_tabelas.atualizar_despesa_contestacao(linhas)

    assert resumo["atualizadas"] == 1


# ---------------------------------------------------------------------------
# HU-16 — atualizar_tipo_contestacao (T-154 / D-19)
# ---------------------------------------------------------------------------
def test_atualizar_tipo_contestacao_regrava_o_sinal_aplicado(repo_tabelas):
    linhas = pd.DataFrame(
        [
            {
                "eot_operadora": "021",
                "eot_tbra": "011",
                "referencia": "202507",
                "trafego": "202507",
                "remuneracao": "TU-RL",
                "tipo_contestacao": "com retenção",
            }
        ]
    )

    resumo = repo_tabelas.atualizar_tipo_contestacao(linhas)

    assert resumo["atualizadas"] == 1
    assert repo_tabelas.obter_tipo_contestacao(
        eot_operadora="021", eot_tbra="011", referencia="202507",
        trafego="202507", remuneracao="TU-RL",
    ) == "com retenção"


def test_atualizar_tipo_contestacao_nao_toca_nos_campos_de_despesa(repo_tabelas):
    linhas = pd.DataFrame(
        [
            {
                "eot_operadora": "021",
                "eot_tbra": "012",
                "referencia": "202507",
                "trafego": "202507",
                "remuneracao": "VU-M",
                "tipo_contestacao": "sem retenção",
            }
        ]
    )

    repo_tabelas.atualizar_tipo_contestacao(linhas)

    alvo = repo_tabelas.tbl_contestacao
    linha = alvo[alvo["id"] == 2].iloc[0]
    assert linha["vb_operadora"] == pytest.approx(10.05)
    assert linha["minutos_tbra"] == pytest.approx(1000.0)


def test_atualizar_tipo_contestacao_chave_ausente_entra_no_resumo(repo_tabelas):
    linhas = pd.DataFrame(
        [
            {
                "eot_operadora": "888",
                "eot_tbra": "011",
                "referencia": "202507",
                "trafego": "202507",
                "remuneracao": "TU-RL",
                "tipo_contestacao": "com retenção",
            }
        ]
    )

    resumo = repo_tabelas.atualizar_tipo_contestacao(linhas)

    assert resumo["atualizadas"] == 0
    assert len(resumo["ausentes"]) == 1


def test_cache_e_recarregado_apos_update(repo_tabelas):
    # O cache em RAM não pode ficar defasado — a leitura do sinal depende dele.
    cache = RepositorioCache()
    cache.atualizar_dados(
        nome_tabela=TABELA, valores={"tipo_contestacao": "sem retenção"}, chave={"id": 1}
    )

    assert cache.obter_tabela(TABELA).set_index("id").loc[1, "tipo_contestacao"] == (
        "sem retenção"
    )
