"""Falha tem que parecer falha.

Este arquivo cobre um defeito de uma classe só, que apareceu em cinco lugares
diferentes: **o robô concluía com sucesso em cima de uma falha.** É o padrão que
`configuration.py` já registrava como causa de incidente — *"nenhuma operadora era
notificada, e o robô reportava sucesso"*.

Os casos do RPA 2 são exercitados por caminho de arquivo (`importlib`), como em
`test_equivalencia_com_origem.py`, porque os três RPAs têm um pacote `src` e não
coexistem num mesmo processo. Quando a suíte própria do RPA 2 existir, eles migram
para lá.
"""

import json

import pytest

from tests.conftest import carregar_modulo_de_rpa


class TestHistoricoCorrompido:
    """
    O histórico é a proteção anti-reprocessamento. Um JSON corrompido devolvia
    `{}` **sem log**: o robô refazia o mês inteiro como se fosse a primeira
    execução, reenviando arquivos e duplicando registros.
    """

    @pytest.fixture()
    def validador(self, tmp_path, monkeypatch):
        from comum.arquivos import historico
        from comum.config import configuration

        monkeypatch.setattr(configuration, "DIRETORIO_HISTORICO_ARQUIVOS", tmp_path)
        monkeypatch.setattr(historico, "DIRETORIO_HISTORICO_ARQUIVOS", tmp_path)
        return historico.ValidadorHistoricoRPA

    def test_json_intacto_e_lido_normalmente(self, validador, tmp_path):
        instancia = validador()
        instancia.caminho_json.write_text(
            json.dumps({"C:/x/detraf.csv": True}), encoding="utf-8"
        )

        assert instancia._carregar_json() == {"C:/x/detraf.csv": True}

    def test_json_corrompido_e_preservado_e_nao_apagado(self, validador, caplog):
        instancia = validador()
        instancia.caminho_json.write_text("{isto não é json", encoding="utf-8")

        assert instancia._carregar_json() == {}

        preservados = list(instancia.caminho_json.parent.glob("*.corrompido-*.json"))
        assert len(preservados) == 1, "o arquivo corrompido é registro de auditoria"
        assert preservados[0].read_text(encoding="utf-8") == "{isto não é json"

    def test_o_reprocessamento_e_anunciado(self, validador, caplog):
        """Quem lê o log precisa entender por que o mês foi refeito."""
        instancia = validador()
        instancia.caminho_json.write_text("{corrompido", encoding="utf-8")

        with caplog.at_level("ERROR"):
            instancia._carregar_json()

        assert "REPROCESSADOS" in caplog.text

    def test_arquivo_ausente_nao_gera_alarme(self, validador, caplog):
        """Primeira execução do mês é normal, não é incidente."""
        instancia = validador()

        with caplog.at_level("ERROR"):
            assert instancia._carregar_json() == {}

        assert caplog.text == ""


class TestContagemDeLinhas:
    """
    O metadado que o histórico guarda de cada arquivo processado. Até 2026-08-04
    uma falha de leitura devolvia **zero, sem log** — e zero linhas é resultado
    legítimo de um arquivo vazio, então os dois casos ficavam indistinguíveis.
    """

    @pytest.fixture()
    def validador(self, tmp_path, monkeypatch):
        from comum.arquivos import historico
        from comum.config import configuration

        monkeypatch.setattr(configuration, "DIRETORIO_HISTORICO_ARQUIVOS", tmp_path)
        monkeypatch.setattr(historico, "DIRETORIO_HISTORICO_ARQUIVOS", tmp_path)
        return historico.ValidadorHistoricoRPA()

    def test_conta_as_linhas_de_um_csv(self, validador, tmp_path):
        arquivo = tmp_path / "detraf.csv"
        arquivo.write_text("a;b\nc;d\ne;f\n", encoding="utf-8")

        assert validador._contar_linhas_csv(arquivo) == 3

    def test_arquivo_vazio_conta_zero(self, validador, tmp_path):
        """Zero é resposta legítima — e é por isso que a falha não pode ser zero."""
        arquivo = tmp_path / "vazio.csv"
        arquivo.write_text("", encoding="utf-8")

        assert validador._contar_linhas_csv(arquivo) == 0

    def test_csv_ilegivel_devolve_none_e_avisa(self, validador, tmp_path, caplog):
        with caplog.at_level("WARNING"):
            resultado = validador._contar_linhas_csv(tmp_path / "nao_existe.csv")

        assert resultado is None
        assert "nao_existe.csv" in caplog.text

    def test_planilha_ilegivel_devolve_none_e_avisa(self, validador, tmp_path, caplog):
        """Um `.xlsx` que na verdade é texto — acontece quando a operadora renomeia."""
        arquivo = tmp_path / "falso.xlsx"
        arquivo.write_text("isto não é uma planilha", encoding="utf-8")

        with caplog.at_level("WARNING"):
            resultado = validador._contar_linhas_excel(arquivo)

        assert resultado is None
        assert "falso.xlsx" in caplog.text


class TestLimpezaDeTrafegos:
    """
    `executar` caía num `return True` no fim do método: reportava que a limpeza
    deu certo mesmo com o arquivo falhado, e o Detraf seguia para a validação como
    se estivesse íntegro.
    """

    @pytest.fixture()
    def modulo(self):
        return carregar_modulo_de_rpa(
            "rpa2_validacao_apuracao/src/services/validacao_inicial/limpeza_trafegos.py",
            "_limpeza_trafegos_sob_teste",
        )

    def test_falha_de_leitura_propaga_em_vez_de_devolver_sucesso(
        self, modulo, tmp_path
    ):
        instancia = modulo.LimpadorTrafegos()

        with pytest.raises(RuntimeError, match="Falha ao separar"):
            instancia.executar(
                caminho_arquivo=tmp_path / "nao_existe.csv",
                tipo_fluxo="BK",
                sufixo="_BK",
            )

    def test_a_mensagem_nomeia_o_arquivo_e_o_fluxo(self, modulo, tmp_path):
        instancia = modulo.LimpadorTrafegos()

        with pytest.raises(RuntimeError) as erro:
            instancia.executar(
                caminho_arquivo=tmp_path / "detraf_algar.csv",
                tipo_fluxo="LL",
                sufixo="_ERRO",
            )

        assert "detraf_algar.csv" in str(erro.value) and "LL" in str(erro.value)


class TestResultadoValidacao:
    """
    Falha de I/O gravava o registro no banco **com zeros** e marcava o arquivo
    como processado. Zero é resultado legítimo — operadora sem tráfego no mês —,
    então os dois casos ficavam indistinguíveis depois.
    """

    @pytest.fixture()
    def modulo(self):
        return carregar_modulo_de_rpa(
            "rpa2_validacao_apuracao/src/services/resultado_validacao.py",
            "_resultado_validacao_sob_teste",
        )

    def test_leitura_falha_levanta_excecao_propria(self, modulo, tmp_path):
        transformador = modulo.TransformadorRelatorioRPA()

        with pytest.raises(modulo.LeituraDetrafFalhou):
            transformador._extrair_dados_internos(tmp_path / "inexistente.csv")

    def test_lote_registra_a_falha_sem_zerar_a_volumetria(self, modulo, tmp_path):
        transformador = modulo.TransformadorRelatorioRPA()

        lote = transformador.preparar_lote(
            [tmp_path / "inexistente.csv"], "DETRAF_SUCESSO"
        )

        assert len(lote) == 1, "o arquivo continua registrado, para auditoria"
        linha = lote.iloc[0]
        assert linha["status"] == "Não validado"
        assert linha["codigo_erro"] == modulo.COD_ERRO_LEITURA
        # `None`, não 0.0 — é o que distingue "não li" de "li e não tem tráfego".
        assert linha["minuto_desp"] is None
        assert linha["valor_bruto_desp"] is None

    def test_o_codigo_de_erro_distingue_leitura_de_validacao(self, modulo):
        assert modulo.COD_ERRO_LEITURA != modulo.COD_ERRO_VALIDACAO


class TestCaminhosNaoConfigurados:
    """
    `Path("")` vira `Path(".")`, e o diretório atual **existe e é um diretório** —
    então toda guarda `exists()`/`is_dir()` passa. Foi assim que o RPA 2 chegou a
    varrer o CWD achando que era a árvore da expectativa.
    """

    def test_expectativa_nao_configurada_e_none(self, monkeypatch):
        monkeypatch.delenv("CAMINHO_EXPECTATIVA_DETRAF", raising=False)

        from comum.config.configuration import _caminho_opcional

        assert _caminho_opcional("CAMINHO_EXPECTATIVA_DETRAF") is None

    def test_controle_ct_nao_configurado_acusa_a_variavel(self, monkeypatch):
        from comum.arquivos import estrutura_pastas as ep
        from comum.config import configuration

        monkeypatch.setattr(configuration, "CAMINHO_CONTROLE_CT", None)

        with pytest.raises(ValueError, match="CAMINHO_CONTROLE_CT"):
            ep.caminho_controle_ct("202507")

    def test_controle_ct_explicito_continua_valendo(self, tmp_path):
        from comum.arquivos import estrutura_pastas as ep

        assert ep.caminho_controle_ct("202507", tmp_path) == tmp_path / "2025"


class TestDelimitadorAssumido:
    """Assumir `;` é o default certo para o Detraf — mas não pode ser mudo."""

    def test_arquivo_sem_separador_reconhecivel_avisa(self, tmp_path, caplog):
        from comum.arquivos import gerenciador as ga

        arquivo = tmp_path / "sem_separador.csv"
        arquivo.write_text("linha sem nenhum separador aqui\n" * 3, encoding="utf-8")

        with caplog.at_level("WARNING"):
            ga.carregar_dados(arquivo)

        assert "separador" in caplog.text.lower()
