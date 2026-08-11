"""Smoke tests do ambiente/infra da Fundação (T-000/T-003/T-004).

Garante que a esteira importa sem exigir banco no import (L-004), que o período
de referência é determinístico e que o RepositorioCache carrega o SQLite de teste.
"""

from comum.config import configuration as cfg


def test_periodo_referencia_deterministico():
    # conftest fixa DEBUG_ANO_MES_ATUAL=202508 => referência = mês anterior.
    assert cfg.ANO_MES_REFERENCIA == "202507"


def test_env_dev_e_caminho_sqlite_de_teste(caminho_sqlite_teste):
    assert cfg.ENV == "dev"
    assert cfg.CAMINHO_SQLITE == str(caminho_sqlite_teste)


def test_extensoes_default():
    assert ".csv" in cfg.EXTENSOES_CSV
    assert ".xlsx" in cfg.EXTENSOES_EXCEL
    assert cfg.EXTENSOES_PERMITIDAS == cfg.EXTENSOES_CSV | cfg.EXTENSOES_EXCEL


def test_repositorio_cache_carrega_tabelas(repo_cache):
    anexo5 = repo_cache.obter_tabela("tbl_anexo5_processado")
    assert not anexo5.empty
    tarifas = repo_cache.obter_tabela("tbl_detraf_tarifas")
    assert not tarifas.empty
    contestacao = repo_cache.obter_tabela("tbl_rpa_log_detraf_despesa_contestacao")
    assert not contestacao.empty


def test_repositorio_tabelas_valida_eot(repo_cache):
    # Importado aqui dentro para garantir que o cache já foi preparado (L-004).
    from comum.dados.repositorio_tabelas import RepositorioTabelas

    repo = RepositorioTabelas()
    assert repo.validar_eot("021") == "CLARO"
    assert repo.validar_eot("999") is None


def test_repositorio_tabelas_obtem_endereco_por_eot(repo_cache):
    from comum.dados.repositorio_tabelas import RepositorioTabelas

    repo = RepositorioTabelas()
    assert repo.obter_endereco_por_eot("021") == "Rua Verbo Divino, 1356 - São Paulo - SP"
    assert repo.obter_endereco_por_eot("999") is None


def test_import_process_handle_nao_conecta_banco():
    # Importar a orquestração NÃO pode exigir banco (sem instância global — L-004).
    from src.main.process_handle import run  # noqa: F401
