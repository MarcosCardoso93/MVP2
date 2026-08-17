import pandas as pd
import pytest

from comum.arquivos.estrutura_pastas import (
    caminho_detrafs_recebidos,
    caminho_mes_operadora,
)
from comum.config import configuration
from comum.dados import tabelas
from src.models.dto.arquivo_para_processar import ArquivoParaProcessar
from src.services.operadora_service import normalizar_nome_pasta
from src.services.processamento_service import ProcessamentoService


def _preparar_diretorios(tmp_path, monkeypatch):
    entrada = tmp_path / "entrada"
    operadoras = tmp_path / "operadoras"
    nao_identificados = tmp_path / "_NAO_IDENTIFICADOS"
    entrada.mkdir()
    operadoras.mkdir()

    monkeypatch.setattr(configuration, "DIRETORIO_ENTRADA", entrada)
    # A raiz das operadoras tem um nome canônico e dois aliases — os três
    # precisam apontar para o mesmo lugar, senão o RPA 2 não acha nada.
    monkeypatch.setattr(configuration, "CAMINHO_OPERADORAS", operadoras)
    monkeypatch.setattr(configuration, "DIRETORIO_SAIDA", operadoras)
    monkeypatch.setattr(configuration, "CAMINHO_DETRAF_RECEBIDO", operadoras)
    # Fica FORA da raiz das operadoras: o RPA 2 varre aquela raiz tratando todo
    # diretório como uma operadora.
    monkeypatch.setattr(
        configuration, "DIRETORIO_NAO_IDENTIFICADOS", nao_identificados
    )
    # 202508 -> competência 202507. É a mesma referência da LINHA_VALIDA de
    # `tests_apoio` e a que está dentro da vigência das tarifas do seed: desde
    # que o RPA 1 valida, um arquivo de outro mês seria REPROVADO aqui.
    monkeypatch.setattr(configuration, "COMPETENCIA", "202508")
    return entrada, operadoras, nao_identificados


#: Os nomes reais variam por operadora e a validação é posicional — só
#: "Credora" importa, e por causa de `extrair_eot_arquivo`, que procura por nome.
CABECALHO = [
    "Credora", "Devedora", "Referencia", "Trafego", "POI", "Rel", "DESC", "GH",
    "Chamadas", "Minutos", "Tarifa", "R$_Liq", "PIS_Cofins", "ICMS", "R$_Bruto",
]


def _escrever_detraf(caminho, **alteracoes) -> None:
    """
    Grava um Detraf VÁLIDO de uma linha.

    Os testes escreviam duas colunas — `Credora;Devedora`. Isso bastava enquanto
    a captura só lia a EOT credora; desde que ela valida o arquivo (2026-08-06),
    duas colunas são recusadas pelo layout e o arquivo vai para a quarentena em
    vez da pasta da operadora.

    As EOTs são as desta suíte: 112 (Megatelecom, região II) como credora — é a
    que os testes identificam — e 010 (Vivo) como devedora.

    O cabeçalho é obrigatório: `extrair_eot_arquivo` lê a coluna cujo título é
    "credora" e, sem ele, tomaria a primeira linha de dados como títulos.
    """
    from tests_apoio import linha

    alteracoes.setdefault("credora", "112")
    alteracoes.setdefault("devedora", "010")
    caminho.write_text(
        ";".join(CABECALHO) + "\n" + ";".join(linha(**alteracoes)) + "\n",
        encoding="utf-8",
    )


def _ler_log(nome_arquivo):
    from comum.dados.repositorio_tabelas import bd_tabelas

    return pd.read_sql(
        f"SELECT * FROM {tabelas.LOG_DESPESA_ARQUIVOS} "
        f"WHERE nome_arquivo = '{nome_arquivo}'",
        con=bd_tabelas.cache.engine,
    )


def test_executar_sucesso_identifica_operadora_e_salva(tmp_path, monkeypatch):
    """
    🔴 O arquivo VÁLIDO não gera linha no banco (decisão de 2026-08-10).

    Este teste afirmava `len(log) == 1`. O RPA 1 gravava, e o RPA 2 gravava de
    novo o mesmo arquivo — duas linhas por Detraf válido, sem chave de
    deduplicação, a daqui com seis campos zerados porque nesta etapa eles não são
    conhecidos. Quem contasse arquivos no WebFat via o dobro.

    A regra passou a ser: o RPA 1 só grava o que só ele sabe (o recusado e o não
    identificado). O registro do arquivo válido é do RPA 2, que tem a apuração.
    """
    entrada, operadoras, _ = _preparar_diretorios(tmp_path, monkeypatch)
    nome_arquivo = "sucesso_eot112.csv"
    caminho = entrada / nome_arquivo
    _escrever_detraf(caminho)

    pacote = ArquivoParaProcessar(
        caminho=caminho, sender_email="cristina@chimentao.com.br"
    )
    ProcessamentoService().executar([pacote])

    operadora = normalizar_nome_pasta("Megatelecom Telecomunicações S.A.")

    # O arquivo vai para a subpasta "Detrafs Recebidos" exigida pela V2 — que é
    # exatamente onde o RPA 2 varre.
    destino = (
        caminho_detrafs_recebidos(operadora, "202507", raiz_operadoras=operadoras)
        / nome_arquivo
    )
    assert destino.exists()

    assert len(_ler_log(nome_arquivo)) == 0, (
        "o arquivo válido é registrado pelo RPA 2, que conhece os valores — "
        "gravar aqui produzia a segunda linha do mesmo arquivo"
    )


def test_executar_nao_identificado_vai_para_pasta_excecao(tmp_path, monkeypatch):
    """
    ⚠️ Este caso ficou **raro** desde que o RPA 1 valida (2026-08-06), e vale
    entender por quê antes de mexer aqui.

    A validação exige que a EOT credora exista no Anexo 5 (`_validar_col_1_2_eot`)
    e a identificação procura o nome fantasia **nessa mesma tabela**. Um arquivo
    que passa na validação tem, portanto, a credora cadastrada — e é identificado.
    Antes, o teste usava EOT 999 para chegar aqui; hoje EOT 999 é REPROVADA, e o
    arquivo vai para a quarentena.

    O que sobra são as divergências entre os dois caminhos de leitura da EOT
    (normalização, Excel devolvendo `11.0`). O ramo continua valendo como rede de
    segurança, e é ele que este teste cobre — forçando o desfecho, já que o
    conteúdo do arquivo não o alcança mais.
    """
    from src.models.dto.operadora_resultado import OperadoraResultado
    from src.services import processamento_service as ps

    entrada, operadoras, nao_identificados = _preparar_diretorios(tmp_path, monkeypatch)
    nome_arquivo = "nao_identificado.csv"
    caminho = entrada / nome_arquivo
    _escrever_detraf(caminho)

    monkeypatch.setattr(
        ps.OperadoraService,
        "obter_operadora",
        staticmethod(
            lambda *args, **kwargs: OperadoraResultado(
                identificada=False, dominio="", nome=""
            )
        ),
    )

    pacote = ArquivoParaProcessar(
        caminho=caminho, sender_email="contato@empresainexistente999.com.br"
    )
    ProcessamentoService().executar([pacote])

    destino = nao_identificados / "202507" / nome_arquivo
    assert destino.exists()

    # 🔴 Passou a registrar no WebFat em 2026-08-10. Antes este teste afirmava
    # `== 0`, com o argumento de que o arquivo não fora salvo na estrutura
    # definitiva. O efeito era pior que o argumento: o arquivo CHEGOU e sumia —
    # nem verde nem vermelho —, e como ele vai para `_NAO_IDENTIFICADOS`, fora
    # da árvore que o RPA 2 varre, ninguém mais o registraria depois.
    log = _ler_log(nome_arquivo)
    assert len(log) == 1
    assert log.iloc[0]["tipo_registro"] == "ERRO", (
        "sem a EOT resolvida não se sabe se é Detraf ou expectativa"
    )
    assert log.iloc[0]["status"] == "Não validado"

    # E, principalmente: nada foi criado dentro da raiz que o RPA 2 varre.
    assert list(operadoras.iterdir()) == []


def test_executar_clona_estrutura_do_mes_anterior(tmp_path, monkeypatch):
    entrada, operadoras, _ = _preparar_diretorios(tmp_path, monkeypatch)
    operadora = normalizar_nome_pasta("Megatelecom Telecomunicações S.A.")

    # O clone opera sobre a pasta do MÊS, que é quem carrega as subpastas.
    mes_anterior_dir = caminho_mes_operadora(
        operadora, "202506", raiz_operadoras=operadoras
    )
    (mes_anterior_dir / "subpasta_existente").mkdir(parents=True)

    nome_arquivo = "clonagem.csv"
    caminho = entrada / nome_arquivo
    _escrever_detraf(caminho)
    ProcessamentoService().executar(
        [ArquivoParaProcessar(caminho=caminho, sender_email="x@y.com")]
    )

    mes_atual_dir = caminho_mes_operadora(
        operadora, "202507", raiz_operadoras=operadoras
    )
    assert (mes_atual_dir / "subpasta_existente").is_dir()


def test_executar_sem_argumentos_lista_diretorio_entrada(tmp_path, monkeypatch):
    entrada, _operadoras, _ = _preparar_diretorios(tmp_path, monkeypatch)
    _escrever_detraf(entrada / "arquivo_solto.csv")

    servico = ProcessamentoService()
    servico.executar()

    assert servico._sucessos + len(servico._nao_identificados) == 1
    assert len(servico._erros) == 0
    assert len(servico._reprovados) == 0


# ---------------------------------------------------------------------------
# As duas etapas: `captura` e `processamento` (2026-08-06)
# ---------------------------------------------------------------------------


class TestDivisaoEmEtapas:
    """
    A divisão só vale se as duas execuções separadas derem **o mesmo resultado**
    da execução única. Senão é promessa falsa: quem homologa roda a etapa,
    parece funcionar, e o resultado é outro.

    Duas coisas fazem isso valer, e as duas eram armadilhas:

    1. **A captura grava em `dest_root/{entry_id}/`** — uma subpasta por
       e-mail —, e `RepositorioArquivos.listar_arquivos` é deliberadamente
       **raso**. Uma varredura rasa na etapa `processamento` não acharia nada;
    2. **o remetente se perderia**, e com ele o fallback de identificação por
       domínio. Ele é recuperado do `RastreamentoRepository`, que a captura já
       alimenta.
    """

    def _rastrear(self, tmp_path, monkeypatch, caminho, sender_email):
        """Simula o que a etapa `captura` deixa gravado."""
        from src.models.dto.registro_rastreamento import RegistroRastreamento
        from src.models.repository.rastreamento_repository import (
            RastreamentoRepository,
        )

        monkeypatch.setattr(
            configuration, "RASTREAMENTO_ARQUIVO_PATH", tmp_path / "rastreamento.json"
        )
        RastreamentoRepository().registrar(
            RegistroRastreamento(
                caminho_arquivo=str(caminho),
                entry_id="ENTRY-1",
                subject="Detraf 202507",
                sender_email=sender_email,
                received_at=None,
            )
        )

    def test_arquivo_em_subpasta_e_encontrado(self, tmp_path, monkeypatch):
        """
        É o caso real: a captura cria uma subpasta por e-mail. Uma varredura
        rasa devolveria zero arquivo, e a etapa `processamento` terminaria com
        sucesso sem ter feito nada.
        """
        entrada, operadoras, _ = _preparar_diretorios(tmp_path, monkeypatch)
        subpasta = entrada / "ENTRY-1"
        subpasta.mkdir()
        caminho = subpasta / "detraf.csv"
        _escrever_detraf(caminho)

        pacotes = ProcessamentoService()._varrer_pasta_de_entrada()

        assert [p.caminho for p in pacotes] == [caminho]

    def test_o_remetente_vem_do_rastreamento(self, tmp_path, monkeypatch):
        """
        Sem isto, a etapa `processamento` perderia o fallback por domínio — e a
        divisão deixaria de ser equivalente à execução única.
        """
        entrada, _, _ = _preparar_diretorios(tmp_path, monkeypatch)
        caminho = entrada / "detraf.csv"
        _escrever_detraf(caminho)
        self._rastrear(tmp_path, monkeypatch, caminho, "cristina@chimentao.com.br")

        pacotes = ProcessamentoService()._varrer_pasta_de_entrada()

        assert pacotes[0].sender_email == "cristina@chimentao.com.br"
        assert pacotes[0].entry_id == "ENTRY-1"

    def test_arquivo_sem_rastreamento_nao_quebra(self, tmp_path, monkeypatch):
        """Pasta preparada à mão (`--pasta-entrada`) não tem rastreamento."""
        entrada, _, _ = _preparar_diretorios(tmp_path, monkeypatch)
        monkeypatch.setattr(
            configuration, "RASTREAMENTO_ARQUIVO_PATH", tmp_path / "vazio.json"
        )
        _escrever_detraf(entrada / "detraf.csv")

        pacotes = ProcessamentoService()._varrer_pasta_de_entrada()

        assert len(pacotes) == 1
        assert pacotes[0].sender_email == ""

    def test_extensao_nao_permitida_e_ignorada(self, tmp_path, monkeypatch):
        entrada, _, _ = _preparar_diretorios(tmp_path, monkeypatch)
        _escrever_detraf(entrada / "detraf.csv")
        (entrada / "leia-me.pdf").write_text("nada")

        pacotes = ProcessamentoService()._varrer_pasta_de_entrada()

        assert [p.caminho.name for p in pacotes] == ["detraf.csv"]

    def test_pasta_inexistente_acusa_a_variavel(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            configuration, "DIRETORIO_ENTRADA", tmp_path / "nao-existe"
        )

        with pytest.raises(FileNotFoundError, match="DIRETORIO_ENTRADA"):
            ProcessamentoService()._varrer_pasta_de_entrada()

    def test_dividido_produz_o_mesmo_que_a_execucao_unica(self, tmp_path, monkeypatch):
        """
        **O teste que justifica a etapa existir.**

        Processar direto o pacote da captura, ou reconstruí-lo do disco e do
        rastreamento, tem que dar o mesmo arquivo no mesmo lugar, com a mesma
        operadora.
        """
        entrada, operadoras, _ = _preparar_diretorios(tmp_path, monkeypatch)
        subpasta = entrada / "ENTRY-1"
        subpasta.mkdir()
        caminho = subpasta / "detraf.csv"
        _escrever_detraf(caminho)
        self._rastrear(tmp_path, monkeypatch, caminho, "cristina@chimentao.com.br")

        # Etapa `processamento` sozinha: reconstrói do disco.
        ProcessamentoService().executar(None)

        operadora = normalizar_nome_pasta("Megatelecom Telecomunicações S.A.")
        destino = caminho_detrafs_recebidos(
            operadora=operadora, aaaamm="202507", raiz_operadoras=operadoras
        )
        assert (destino / "detraf.csv").is_file()
