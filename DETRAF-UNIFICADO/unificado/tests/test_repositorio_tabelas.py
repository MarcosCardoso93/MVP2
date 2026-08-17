"""Testes de fumaça da camada de dados unificada, contra um SQLite real.

Exercitam o caminho completo — engine, cache preguiçoso e consultas — usando o
banco de desenvolvimento gerado por ``preparar_banco_dev.py``. O objetivo não é
cobrir cada regra, e sim provar que a união dos quatro repositórios de origem
funciona: as tabelas carregam, as consultas devolvem o esperado e o carregamento
preguiçoso não exige tabelas que o RPA não usa.

O banco de dev é usado em vez do que veio com o Projeto 2 porque a tabela de log
foi renomeada para o nome da V2 (decisão do cliente, 2026-07-31) e os SQLite de
origem — que são somente leitura — ainda têm o nome antigo.

## Preferem o ESPELHO do banco real (2026-08-06)

Estes testes são os únicos que rodam contra um SQLite de verdade, e são
**independentes de dados**: pegam a primeira linha do que encontrarem e afirmam
sobre ela. Isso os deixa rodar tanto no banco de dev quanto no espelho gerado por
``espelhar_banco.py`` — e o espelho é estritamente melhor, porque tem o **schema
real com dados reais**, 2.793 operadoras em vez de quatro seeds.

Importa porque foi exatamente aqui que os três defeitos de schema passaram: com o
espelho, ``test_obter_tipo_servico_por_eot`` atravessa o caminho que levantava
``KeyError`` contra o MySQL, e falha se ele voltar.

⚠️ Até 2026-08-06 o módulo INTEIRO era pulado em silêncio — o `skipif` procurava
só o ``TABELAS_DETRAF.db``, que não existe em máquina nenhuma que não tenha
rodado o ``preparar_banco_dev.py``.
"""

import os
from pathlib import Path

import pytest

_RAIZ = Path(__file__).resolve().parents[1]
_ESPELHO = _RAIZ / "banco_de_dados" / "TABELAS_DETRAF_espelho.db"
_BANCO_DEV = _RAIZ / "banco_de_dados" / "TABELAS_DETRAF.db"

#: O espelho vence quando existe: schema real, dados reais.
_SQLITE_DEV = _ESPELHO if _ESPELHO.exists() else _BANCO_DEV

pytestmark = pytest.mark.skipif(
    not _SQLITE_DEV.exists(),
    reason=(
        "sem SQLite real — rode `python espelhar_banco.py` (preferido) ou "
        "`python preparar_banco_dev.py`"
    ),
)


@pytest.fixture()
def repositorio(monkeypatch):
    """Repositório apontado para o banco de dev, isolado por teste."""
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.setenv("CAMINHO_SQLITE", str(_SQLITE_DEV))

    import comum.config.configuration as cfg
    from comum.dados.repositorio_cache import RepositorioCache
    from comum.dados.repositorio_tabelas import RepositorioTabelas

    # A configuração é lida no import; para o teste, aponta direto.
    monkeypatch.setattr(cfg, "CAMINHO_SQLITE", str(_SQLITE_DEV))
    monkeypatch.setattr(cfg, "ENV", "dev")

    import comum.dados.repositorio_cache as mod_cache

    monkeypatch.setattr(mod_cache, "CAMINHO_SQLITE", str(_SQLITE_DEV))
    monkeypatch.setattr(mod_cache, "ENV", "dev")

    RepositorioCache.resetar()
    yield RepositorioTabelas()
    RepositorioCache.resetar()


# ---------------------------------------------------------------------------
# Carregamento preguiçoso
# ---------------------------------------------------------------------------


def test_construir_repositorio_nao_carrega_nenhuma_tabela(repositorio):
    # Alteração intencional da unificação: os projetos carregavam tudo no
    # __init__, o que faria o RPA 1 exigir a tabela de tarifas que não usa.
    assert repositorio.cache.tabelas == {}


def test_anexo5_carrega_no_primeiro_acesso(repositorio):
    from comum.dados import tabelas

    df = repositorio.tbl_anexo5_processado

    assert not df.empty
    assert "EOT" in df.columns
    assert "Nome Fantasia" in df.columns
    assert tabelas.ANEXO5 in repositorio.cache.tabelas


def test_tabela_e_carregada_uma_unica_vez(repositorio):
    primeiro = repositorio.tbl_anexo5_processado
    segundo = repositorio.tbl_anexo5_processado

    assert primeiro is segundo


# ---------------------------------------------------------------------------
# Anexo 5
# ---------------------------------------------------------------------------


def test_normalizacao_de_eot_remove_parte_decimal(repositorio):
    # Borda que separava o Projeto 1 dos demais (duplicação D-07): lendo de
    # Excel, uma EOT chega como float e virava "11.0", que não casa no Anexo 5.
    assert repositorio._tratar_eot("11.0") == "011"
    assert repositorio._tratar_eot("11") == "011"
    assert repositorio._tratar_eot(" 25 ") == "025"
    assert repositorio._tratar_eot("112") == "112"


def test_buscar_nome_fantasia_por_eot_existente(repositorio):
    df = repositorio.tbl_anexo5_processado
    eot = str(df.iloc[0]["EOT"]).strip()
    esperado = df.iloc[0]["Nome Fantasia"]

    assert repositorio.buscar_nome_fantasia_por_eot(eot) == esperado


def test_buscar_nome_fantasia_por_eot_inexistente(repositorio):
    assert repositorio.buscar_nome_fantasia_por_eot("999999") is None


def test_obter_tipo_servico_por_eot(repositorio):
    df = repositorio.tbl_anexo5_processado
    eot = str(df.iloc[0]["EOT"]).strip()

    tipo = repositorio.obter_tipo_servico_por_eot(eot)

    assert tipo is None or isinstance(tipo, str)


# ---------------------------------------------------------------------------
# Regressão do D1 — as colunas SEM acento (2026-08-06)
#
# 🔴 Os quatro acessos abaixo levantavam `KeyError` contra o banco real, nos três
# RPAs, porque o código procurava `Região`, `Tipo de Serviço`, `Concessão` e
# `Endereço de Correspondência` — e o MySQL não tem acento em nome de coluna
# nenhum. A suíte não pegava: os `fixtures` criavam as colunas acentuadas.
#
# Rodando contra o espelho, estes testes atravessam o caminho de verdade. Um
# `KeyError` aqui é o defeito voltando.
# ---------------------------------------------------------------------------


def test_as_colunas_do_anexo5_nao_tem_acento(repositorio):
    from comum.dados import tabelas

    colunas = set(repositorio.tbl_anexo5_processado.columns)

    for constante in (
        tabelas.COL_ANEXO5_EOT,
        tabelas.COL_ANEXO5_NOME_FANTASIA,
        tabelas.COL_ANEXO5_REGIAO,
        tabelas.COL_ANEXO5_TIPO_SERVICO,
        tabelas.COL_ANEXO5_CONCESSAO,
        tabelas.COL_ANEXO5_ENDERECO_CORRESP,
    ):
        assert constante in colunas, f"coluna {constante!r} sumiu do banco"

    for acentuada in (
        "Região",
        "Tipo de Serviço",
        "Concessão",
        "Endereço de Correspondência",
    ):
        assert acentuada not in colunas, (
            f"{acentuada!r} apareceu no banco — se o DBA renomeou, as constantes "
            f"COL_ANEXO5_* precisam acompanhar"
        )


def test_obter_endereco_por_eot(repositorio):
    from comum.dados import tabelas

    df = repositorio.tbl_anexo5_processado
    eot = str(df.iloc[0][tabelas.COL_ANEXO5_EOT]).strip()

    endereco = repositorio.obter_endereco_por_eot(eot)

    assert endereco is None or isinstance(endereco, str)


def test_obter_concessao_por_eot(repositorio):
    from comum.dados import tabelas

    df = repositorio.tbl_anexo5_processado
    eot = str(df.iloc[0][tabelas.COL_ANEXO5_EOT]).strip()

    concessao = repositorio.obter_concessao_por_eot(eot)

    assert concessao is None or isinstance(concessao, str)


def test_mapa_de_regiao_cobre_o_anexo5_inteiro(repositorio):
    """`_mapa_regiao_cache` é o `set_index("EOT")["Regiao"]` que estourava."""
    mapa = repositorio._mapa_regiao_cache

    assert isinstance(mapa, dict)
    assert mapa, "o mapa EOT -> região saiu vazio"


# ---------------------------------------------------------------------------
# Tarifas e descritores
# ---------------------------------------------------------------------------


def test_regioes_validas_vem_da_tabela_de_tarifas(repositorio):
    regioes = repositorio.regioes_validas_cache

    assert isinstance(regioes, set)
    assert regioes


def test_mapa_de_descritores_carrega(repositorio):
    df = repositorio.obter_mapa_descritores()

    assert not df.empty


# ---------------------------------------------------------------------------
# Nomes de tabela
# ---------------------------------------------------------------------------


def test_nomes_de_tabela_batem_com_o_banco_real(repositorio):
    from sqlalchemy import inspect

    from comum.dados import tabelas

    existentes = set(inspect(repositorio.cache.engine).get_table_names())

    assert tabelas.ANEXO5 in existentes
    assert tabelas.TARIFAS in existentes
    assert tabelas.MAPEAMENTO_DESCRITORES in existentes
    # O nome da V2 (decisão do cliente, 2026-07-31). O SQLite de homologação
    # do Projeto 2 usa o nome antigo — por isso este teste roda contra o banco
    # preparado por preparar_banco_dev.py, que aplica a renomeação.
    assert tabelas.LOG_DESPESA_ARQUIVOS in existentes
