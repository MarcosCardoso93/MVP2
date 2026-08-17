import pandas as pd

from comum.dados import tabelas
from comum.dados.repositorio_tabelas import bd_tabelas


def test_buscar_nome_fantasia_por_eot_encontrado():
    assert bd_tabelas.buscar_nome_fantasia_por_eot("112") == "Megatelecom Telecomunicações S.A."


def test_buscar_nome_fantasia_por_eot_nao_encontrado():
    assert bd_tabelas.buscar_nome_fantasia_por_eot("999") is None


def test_buscar_nome_fantasia_substring_case_insensitive():
    assert bd_tabelas.buscar_nome_fantasia("vivo") == "Vivo"


def test_buscar_nome_fantasia_nao_encontrado():
    assert bd_tabelas.buscar_nome_fantasia("naoexisteoperadora") is None


def test_salvar_dados_tabela_despesa_insere_e_le_de_volta():
    df = pd.DataFrame([{
        "tipo_registro": "DETRAF",
        "nome_arquivo": "teste_repositorio_tabelas_unico.csv",
        "periodo": 202602,
        "empresa": "Vivo",
        "tipo_servico_operadora": None,
        "tipo_servico_vivo": None,
        "remuneracoes": None,
        "minuto_desp": 0.0,
        "valor_bruto_desp": 0.0,
        "status": "Validado",
        "codigo_erro": None,
        "created_at": "2026-07-17 00:00:00",
    }])

    bd_tabelas.salvar_dados_tabela_despesa(df)

    lido = pd.read_sql(
        f"SELECT * FROM {tabelas.LOG_DESPESA_ARQUIVOS} "
        "WHERE nome_arquivo = 'teste_repositorio_tabelas_unico.csv'",
        con=bd_tabelas.cache.engine,
    )
    assert len(lido) == 1
    assert lido.iloc[0]["empresa"] == "Vivo"


def test_salvar_dados_tabela_despesa_vazio_nao_lanca_excecao():
    bd_tabelas.salvar_dados_tabela_despesa(pd.DataFrame())
