"""Testes do resolver de remuneração por descritor (D-5 resolvida, incl. refino de
colisões via coluna `produto`, 2026-07-27).

**D-21 (2026-07-30):** a fonte passou a ser a tabela
`tbl_detraf_mapeamento_descritores` do banco Webfat (V2 pág. 7). O CSV
`tests/fixtures/mapeamento_descritores.csv` (derivado de `DOCS/Outros arquivos
auxiliares/Mapeamento_Descritores.xlsx`) agora só semeia o SQLite de teste, de forma
que os valores esperados abaixo continuam sendo os do mapa real.
"""

import pandas as pd
import pytest

from src.services import mapa_remuneracao as mr


@pytest.fixture
def indice(indice_remuneracao) -> dict:
    return indice_remuneracao


def test_carrega_mapa_do_banco_com_25_linhas(repo_tabelas):
    mapa = mr.carregar_mapa_descritores(repo_tabelas.obter_mapa_descritores())

    assert mapa.shape[0] == 25
    assert list(mapa.columns) == mr.COLUNAS_MAPA_DESCRITORES


def test_schema_divergente_levanta():
    # B-D21: o schema real da tabela ainda não foi confirmado — a falha precisa ser
    # explícita, não silenciosa.
    with pytest.raises(ValueError, match="tbl_detraf_mapeamento_descritores"):
        mr.carregar_mapa_descritores(pd.DataFrame({"coluna_inesperada": ["x"]}))


@pytest.mark.parametrize(
    "descritor,esperado",
    [
        ("XPTO_L", "TU-RL"),  # final L -> TU-RL
        ("XPTO_V", "VU-M"),  # final V -> VU-M
        ("XPTO_C", "TU-COM"),  # final C -> TU-COM
        ("XPTO_S", "TIS"),  # final S -> TIS (SMS)
        ("XPTO_X", "PRESEL"),  # final X -> PRESEL
    ],
)
def test_resolve_finais_nao_ambiguos(indice, descritor, esperado):
    assert mr.resolver_remuneracao(descritor, indice) == esperado


def test_final_nao_mapeado_retorna_none(indice):
    # 'I' não existe no mapa real (AI/09 §7 documenta TU-RIU1/2, mas o xlsx não tem
    # entrada para 'I' — refino D-5). Regra: não mapeado => ignorado (None).
    assert mr.resolver_remuneracao("2NENI", indice) is None


@pytest.mark.parametrize(
    "final_antes_ambiguo,esperado",
    [
        ("T", "TU-RIU"),  # colidia com VU-T; produto=DETRAF em ambos -> vence o 1º (id=2)
        ("M", "TC-SMS"),  # colidia com VOZ -> vence o 1º (id=8)
        ("U", "RETUP"),  # colidia com TUP -> vence o 1º (id=11)
        ("W", "WHOLESALE"),  # colidia com VMA -> vence o 1º (id=24)
        ("5", "TU-TX-RIU-F"),  # colidia com TU-TX-RIU-M -> vence o 1º (id=18)
    ],
)
def test_finais_antes_ambiguos_agora_resolvidos_pelo_primeiro(
    indice, final_antes_ambiguo, esperado
):
    # D-5 (2026-07-27): produto=DETRAF não desambigua sozinho nesta fixture (todas as
    # linhas são DETRAF) — a regra "usar a primeira ocorrência" decide deterministicamente.
    assert mr.resolver_remuneracao(f"XPTO_{final_antes_ambiguo}", indice) == esperado


def test_descritor_vazio_retorna_none(indice):
    assert mr.resolver_remuneracao("", indice) is None


# --------------------------------------------------------------------------
# D-5 (2026-07-27): filtro por `produto` na construção do índice
# --------------------------------------------------------------------------
def _linha_mapa(id_, final_descritor, remuneracao_fixa, produto="DETRAF", observacao="X"):
    return {
        "id": id_,
        "final_descritor": final_descritor,
        "remuneracao_fixa": remuneracao_fixa,
        "observacao": observacao,
        "produto": produto,
    }


def test_construir_indice_descarta_linha_de_outro_produto():
    mapa = pd.DataFrame(
        [
            _linha_mapa("1", "T", "TU-RIU", produto="DETRAF"),
            _linha_mapa("2", "T", "OUTRO-PRODUTO-X", produto="ROAMING_INTL"),
        ]
    )

    indice = mr.construir_indice_remuneracao(mapa)

    assert indice["T"] == ["TU-RIU"]


def test_construir_indice_usa_primeira_ocorrencia_quando_ambas_sao_detraf():
    mapa = pd.DataFrame(
        [
            _linha_mapa("1", "T", "PRIMEIRA", produto="DETRAF"),
            _linha_mapa("2", "T", "SEGUNDA", produto="DETRAF"),
        ]
    )

    indice = mr.construir_indice_remuneracao(mapa)

    assert indice["T"] == ["PRIMEIRA"]


def test_construir_indice_filtro_produto_case_insensitive_e_com_espacos():
    mapa = pd.DataFrame([_linha_mapa("1", "T", "TU-RIU", produto=" detraf ")])

    indice = mr.construir_indice_remuneracao(mapa)

    assert indice["T"] == ["TU-RIU"]
