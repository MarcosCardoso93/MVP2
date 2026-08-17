import pandas as pd

from src.config import configuration
from src.models.dto.arquivo_para_processar import ArquivoParaProcessar
from src.services.operadora_service import normalizar_nome_pasta
from src.services.processamento_service import ProcessamentoService
from src.utils.filesystem import construir_caminho_saida


def _preparar_diretorios(tmp_path, monkeypatch):
    entrada = tmp_path / "entrada"
    saida = tmp_path / "saida"
    entrada.mkdir()
    saida.mkdir()
    monkeypatch.setattr(configuration, "DIRETORIO_ENTRADA", entrada)
    monkeypatch.setattr(configuration, "DIRETORIO_SAIDA", saida)
    monkeypatch.setattr(configuration, "COMPETENCIA", "202603")  # -> competência 202602
    return entrada, saida


def _ler_log(nome_arquivo):
    from src.models.repository.repositorio_tabelas import bd_tabelas
    return pd.read_sql(
        f"SELECT * FROM tbl_detraf_despesa_arquivos WHERE nome_arquivo = '{nome_arquivo}'",
        con=bd_tabelas.cache.engine,
    )


def test_executar_sucesso_identifica_operadora_e_salva(tmp_path, monkeypatch):
    entrada, saida = _preparar_diretorios(tmp_path, monkeypatch)
    nome_arquivo = "sucesso_eot112.csv"
    caminho = entrada / nome_arquivo
    caminho.write_text("Credora;Devedora\n112;010\n")

    pacote = ArquivoParaProcessar(caminho=caminho, sender_email="cristina@chimentao.com.br")
    ProcessamentoService().executar([pacote])

    operadora = normalizar_nome_pasta("Megatelecom Telecomunicações S.A.")
    destino = construir_caminho_saida(saida, operadora, "2026", "202602") / nome_arquivo
    assert destino.exists()

    log = _ler_log(nome_arquivo)
    assert len(log) == 1
    assert log.iloc[0]["empresa"] == operadora


def test_executar_nao_identificado_vai_para_pasta_excecao(tmp_path, monkeypatch):
    entrada, saida = _preparar_diretorios(tmp_path, monkeypatch)
    nome_arquivo = "nao_identificado.csv"
    caminho = entrada / nome_arquivo
    caminho.write_text("Col1;Col2\n999;999\n")

    pacote = ArquivoParaProcessar(caminho=caminho, sender_email="contato@empresainexistente999.com.br")
    ProcessamentoService().executar([pacote])

    destino = saida / "_NAO_IDENTIFICADOS" / "202602" / nome_arquivo
    assert destino.exists()
    assert len(_ler_log(nome_arquivo)) == 0


def test_executar_clona_estrutura_do_mes_anterior(tmp_path, monkeypatch):
    entrada, saida = _preparar_diretorios(tmp_path, monkeypatch)
    operadora = normalizar_nome_pasta("Megatelecom Telecomunicações S.A.")
    mes_anterior_dir = construir_caminho_saida(saida, operadora, "2026", "202601")
    (mes_anterior_dir / "subpasta_existente").mkdir(parents=True)

    nome_arquivo = "clonagem.csv"
    caminho = entrada / nome_arquivo
    caminho.write_text("Credora;Devedora\n112;010\n")
    ProcessamentoService().executar([ArquivoParaProcessar(caminho=caminho, sender_email="x@y.com")])

    mes_atual_dir = construir_caminho_saida(saida, operadora, "2026", "202602")
    assert (mes_atual_dir / "subpasta_existente").is_dir()


def test_executar_sem_argumentos_lista_diretorio_entrada(tmp_path, monkeypatch):
    entrada, _saida = _preparar_diretorios(tmp_path, monkeypatch)
    (entrada / "arquivo_solto.csv").write_text("Col1;Col2\n999;999\n")

    servico = ProcessamentoService()
    servico.executar()

    assert servico._sucessos + len(servico._nao_identificados) == 1
    assert len(servico._erros) == 0
