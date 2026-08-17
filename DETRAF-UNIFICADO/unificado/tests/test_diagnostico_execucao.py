"""O `.txt` que diz em qual etapa parou (2026-08-07).

Antes disto, os três `main.py` tinham o mesmo `except Exception` cego: registravam
"Execução interrompida por erro não tratado" e devolviam 1, **sem saber em qual
etapa estavam**. Numa homologação manual, sem IA no ambiente, responder "onde
parou e por quê" era ler o `.log` cronológico inteiro.

O que estes testes protegem:

1. que a exceção seja registrada **com o nome da etapa** — e ainda assim
   re-levantada, para o fluxo de erro não mudar;
2. que o arquivo saia **também quando dá tudo certo** — a etapa que passou é o
   contexto que diz se o erro é dela ou do que veio antes;
3. que "rodou e não produziu nada" não se confunda com "não rodou". É o modo de
   falha silencioso mais comum deste projeto.
"""

from pathlib import Path

import pytest

from comum.config import configuration
from comum.config.diagnostico_execucao import DiagnosticoDeExecucao


@pytest.fixture()
def diagnostico(tmp_path, monkeypatch) -> DiagnosticoDeExecucao:
    monkeypatch.setattr(configuration, "RAIZ_LOGS", tmp_path)
    return DiagnosticoDeExecucao(robo="rpa2_validacao_apuracao", referencia="202507")


class TestAEtapaQueDeuCerto:
    def test_registra_o_que_produziu(self, diagnostico):
        with diagnostico.etapa("validacao") as etapa:
            etapa.produzido = ["Detraf válidos: 3", "Detraf inválidos: 1"]

        texto = diagnostico.montar()
        assert "ETAPA 1/1: validacao" in texto
        assert "[ok]" in texto
        assert "Detraf válidos: 3" in texto

    def test_registra_a_entrada(self, diagnostico):
        """A primeira coisa que se confere quando o resultado surpreende."""
        with diagnostico.etapa("validacao", {"pasta": "C:/x"}):
            pass

        assert "pasta = C:/x" in diagnostico.montar()

    def test_cronometra(self, diagnostico):
        with diagnostico.etapa("validacao"):
            pass

        assert diagnostico.etapas[0].duracao >= 0

    def test_rodou_sem_produzir_nada_e_dito_explicitamente(self, diagnostico):
        """
        🔴 "Terminou bem sem fazer nada" é o modo de falha mais comum aqui — lista
        de filtro vazia, pasta errada, mês sem arquivo. Um espaço em branco no
        relatório se lê como "não registrei", e não como "não produziu".
        """
        with diagnostico.etapa("batimento"):
            pass

        assert "a etapa rodou sem gerar resultado" in diagnostico.montar()


class TestAEtapaQueFalhou:
    def test_a_excecao_e_re_levantada(self, diagnostico):
        """O diagnóstico observa; ele não muda o fluxo de erro."""
        with pytest.raises(ValueError, match="algo"):
            with diagnostico.etapa("carga"):
                raise ValueError("algo")

    def test_o_erro_fica_amarrado_a_ETAPA(self, diagnostico):
        """É o ponto da mudança: o `except` de topo não sabia onde estava."""
        with pytest.raises(ValueError):
            with diagnostico.etapa("carga"):
                raise ValueError("algo")

        assert diagnostico.desfecho == "ERRO na etapa 1/1 (carga)"

    def test_grava_o_traceback_completo(self, diagnostico):
        with pytest.raises(ValueError):
            with diagnostico.etapa("carga"):
                raise ValueError("algo")

        texto = diagnostico.montar()
        assert "ValueError: algo" in texto
        assert "traceback:" in texto
        assert "test_diagnostico_execucao.py" in texto

    def test_a_etapa_anterior_continua_no_arquivo(self, diagnostico):
        """
        Sem ela não dá para saber se o erro é do passo ou do que veio antes — é
        a razão de gravar as que deram certo.
        """
        with diagnostico.etapa("artefatos") as etapa:
            etapa.produzido = ["EXT: 3"]
        with pytest.raises(RuntimeError):
            with diagnostico.etapa("carga"):
                raise RuntimeError("AGI fora")

        texto = diagnostico.montar()
        assert "ETAPA 1/2: artefatos" in texto
        assert "EXT: 3" in texto
        assert "ETAPA 2/2: carga" in texto


class TestTraducaoDoErroDeBanco:
    """
    `explicar_erro_de_banco` já traduzia os cinco erros do driver em causa +
    correção, e até aqui só o `verificar_ambiente.py` a consumia — justamente o
    script que roda ANTES, quando ainda não há erro nenhum para traduzir.
    """

    def test_erro_de_coluna_vira_causa_e_correcao(self, diagnostico):
        with pytest.raises(Exception):
            with diagnostico.etapa("batimento"):
                raise Exception("(1054, \"Unknown column 'vb_contestacao'\")")

        texto = diagnostico.montar()
        assert "causa provável:" in texto
        assert "falta uma coluna" in texto

    def test_erro_comum_nao_inventa_causa(self, diagnostico):
        """Melhor sem explicação do que com uma explicação errada."""
        with pytest.raises(ValueError):
            with diagnostico.etapa("validacao"):
                raise ValueError("planilha sem a aba esperada")

        assert diagnostico.etapas[0].causa_provavel == ""


class TestAEtapaPulada:
    def test_registra_o_motivo(self, diagnostico):
        """
        Etapa ausente do arquivo é indistinguível de etapa que ninguém pensou em
        registrar. "Pulada por --etapa=validacao" é resposta; o silêncio não é.
        """
        diagnostico.pular("batimento", "pulada por --etapa=validacao")

        texto = diagnostico.montar()
        assert "[pulada]" in texto
        assert "motivo: pulada por --etapa=validacao" in texto

    def test_pulada_nao_conta_como_erro(self, diagnostico):
        with diagnostico.etapa("validacao"):
            pass
        diagnostico.pular("batimento", "pulada por --etapa=validacao")

        assert diagnostico.desfecho == "OK"


class TestOArquivo:
    def test_grava_e_devolve_o_caminho(self, diagnostico, tmp_path):
        with diagnostico.etapa("validacao"):
            pass

        destino = diagnostico.gravar()

        assert destino is not None
        assert destino.suffix == ".txt"
        assert destino.parent.name == "diagnosticos"
        assert tmp_path in destino.parents

    def test_grava_mesmo_quando_tudo_deu_certo(self, diagnostico):
        """A decisão de 2026-08-07: sempre, não só em erro."""
        with diagnostico.etapa("validacao"):
            pass

        assert diagnostico.gravar() is not None

    def test_o_cabecalho_traz_ambiente_e_desfecho(self, diagnostico):
        with diagnostico.etapa("validacao"):
            pass

        texto = diagnostico.gravar().read_text(encoding="utf-8")
        assert "EXECUÇÃO" in texto
        assert "AMBIENTE" in texto
        assert "desfecho:   OK" in texto
        assert "referência: 202507" in texto

    def test_aponta_para_o_log_completo(self, diagnostico):
        """O diagnóstico é o resumo; quem tem a sequência inteira é o log."""
        with diagnostico.etapa("validacao"):
            pass

        assert "LOG COMPLETO" in diagnostico.gravar().read_text(encoding="utf-8")

    def test_falha_ao_gravar_nao_levanta(self, diagnostico, monkeypatch, tmp_path):
        """
        Ele é gravado depois de o trabalho estar feito. Perdê-lo por falta de
        permissão seria trocar um inconveniente por um prejuízo.
        """
        arquivo = tmp_path / "ocupado"
        arquivo.write_text("x", encoding="utf-8")
        monkeypatch.setattr(configuration, "RAIZ_LOGS", arquivo)

        assert diagnostico.gravar() is None

    def test_um_arquivo_por_execucao(self, diagnostico):
        """A comparação da homologação é rodada a rodada, não acumulada."""
        assert diagnostico.inicio.strftime("%Y-%m-%d") in diagnostico.caminho().name


class TestExecucaoSemEtapaNenhuma:
    def test_nao_estoura_e_diz_o_que_houve(self, diagnostico):
        assert diagnostico.desfecho == "nenhuma etapa executada"
        assert diagnostico.gravar() is not None
