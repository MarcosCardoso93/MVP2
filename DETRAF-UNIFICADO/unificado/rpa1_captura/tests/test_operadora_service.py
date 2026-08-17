import openpyxl

from src.services.operadora_service import (
    OperadoraService,
    extrair_eot_arquivo,
    extrair_texto_busca_operadora,
    normalizar_nome_pasta,
)


def test_extrair_texto_busca_operadora():
    assert extrair_texto_busca_operadora("contato@vivo.com.br") == "vivo"


def test_normalizar_nome_pasta_remove_acentos():
    assert normalizar_nome_pasta("Telefônica Brasil") == "Telefonica Brasil"


def test_normalizar_nome_pasta_remove_caracteres_invalidos():
    assert normalizar_nome_pasta("A/B:C*D") == "A_B_C_D"


def _escrever_csv(tmp_path, conteudo, nome="arquivo.csv"):
    caminho = tmp_path / nome
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


def test_extrair_eot_csv_coluna_credora(tmp_path):
    caminho = _escrever_csv(
        tmp_path,
        "Credora;Devedora;Referencia\n112;010;202602\n",
    )

    assert extrair_eot_arquivo(caminho) == "112"


def test_extrair_eot_csv_fallback_por_posicao(tmp_path):
    caminho = _escrever_csv(
        tmp_path,
        "Col1;Col2\n45;99\n",
    )

    assert extrair_eot_arquivo(caminho) == "045"


def test_extrair_eot_csv_vazio_retorna_none(tmp_path):
    caminho = _escrever_csv(tmp_path, "")

    assert extrair_eot_arquivo(caminho) is None


def test_extrair_eot_xlsx(tmp_path):
    caminho = tmp_path / "arquivo.xlsx"
    workbook = openpyxl.Workbook()
    planilha = workbook.active
    planilha.append(["Credora", "Devedora"])
    planilha.append(["002", "010"])
    workbook.save(caminho)

    assert extrair_eot_arquivo(caminho) == "002"


def test_obter_operadora_identificada_por_eot(tmp_path):
    caminho = _escrever_csv(tmp_path, "Credora;Devedora\n112;010\n")

    resultado = OperadoraService.obter_operadora(caminho, "cristina@chimentao.com.br")

    assert resultado.identificada is True
    assert resultado.origem == "eot"
    assert resultado.nome == "Megatelecom Telecomunicacoes S.A."


def test_obter_operadora_identificada_por_dominio_fallback(tmp_path):
    caminho = _escrever_csv(tmp_path, "Col1;Col2\n999;999\n")

    resultado = OperadoraService.obter_operadora(caminho, "contato@vivo.com.br")

    assert resultado.identificada is True
    assert resultado.origem == "dominio"
    assert resultado.nome == "Vivo"


def test_obter_operadora_nao_identificada(tmp_path):
    caminho = _escrever_csv(tmp_path, "Col1;Col2\n999;999\n")

    resultado = OperadoraService.obter_operadora(caminho, "contato@empresainexistente999.com.br")

    assert resultado.identificada is False
    assert resultado.nome is None
