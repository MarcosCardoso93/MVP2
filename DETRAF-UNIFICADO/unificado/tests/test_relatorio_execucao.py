"""Relatório de execução e reset de homologação (2026-08-06).

Homologar é comparar esperado × obtido. O obtido estava só no log — cronológico,
centenas de linhas por rodada, misturando os passos de todas as operadoras.

O que se cobre aqui é o que faz o relatório servir a isso: a tabela por
operadora, o motivo do pulo (a coluna mais consultada), e o cabeçalho de
ambiente — porque a primeira pergunta sobre qualquer resultado estranho é *em que
modo isso rodou?*.
"""

import pytest

import resetar_homologacao
from comum.config import relatorio_execucao as rel


@pytest.fixture()
def relatorio(tmp_path, monkeypatch):
    from comum.config import configuration

    monkeypatch.setattr(configuration, "RAIZ_LOGS", tmp_path)
    return rel.RelatorioExecucao("rpa3_contestacao_agi_ec", "202507")


class TestSituacaoDaLinha:
    def test_produziu_tudo_e_ok(self):
        linha = rel.LinhaDeRelatorio("CLARO", {"EXT": "sim"})

        assert linha.situacao == "ok"

    def test_produziu_e_pulou_e_parcial(self):
        linha = rel.LinhaDeRelatorio("CLARO", {"EXT": "sim"}, pulos=["sem expectativa"])

        assert linha.situacao == "parcial"

    def test_so_pulou_e_nada_gerado(self):
        """Diferente de erro: nada saiu, mas por motivo conhecido."""
        linha = rel.LinhaDeRelatorio("CLARO", {}, pulos=["sem Detraf recebido"])

        assert linha.situacao == "nada gerado"

    def test_erro_vence_o_resto(self):
        linha = rel.LinhaDeRelatorio("CLARO", {"EXT": "sim"}, ["algo"], erro="estourou")

        assert linha.situacao == "ERRO"


class TestConteudoDoRelatorio:
    def test_uma_linha_por_operadora(self, relatorio):
        relatorio.acrescentar(rel.LinhaDeRelatorio("CLARO", {"EXT": "sim"}))
        relatorio.acrescentar(rel.LinhaDeRelatorio("TIM", {"EXT": "sim"}))

        texto = relatorio.gravar().read_text(encoding="utf-8")

        assert "| CLARO |" in texto
        assert "| TIM |" in texto

    def test_o_motivo_do_pulo_aparece(self, relatorio):
        """É a coluna mais consultada: quase toda dúvida é 'por que não saiu?'."""
        relatorio.acrescentar(
            rel.LinhaDeRelatorio("TIM", {}, pulos=["_ENV e carta sem expectativa Vivo"])
        )

        texto = relatorio.gravar().read_text(encoding="utf-8")

        assert "sem expectativa Vivo" in texto

    def test_o_erro_e_destacado(self, relatorio):
        relatorio.acrescentar(rel.LinhaDeRelatorio("ALGAR", {}, erro="arquivo ilegível"))

        texto = relatorio.gravar().read_text(encoding="utf-8")

        assert "**ERRO:** arquivo ilegível" in texto

    def test_traz_o_modo_e_os_efeitos_externos(self, relatorio):
        """A primeira pergunta sobre resultado estranho é em que modo rodou."""
        texto = relatorio.gravar().read_text(encoding="utf-8")

        assert "modo:" in texto
        assert "EFEITOS EXTERNOS" in texto

    def test_execucao_sem_operadora_nao_quebra(self, relatorio):
        texto = relatorio.gravar().read_text(encoding="utf-8")

        assert "Nenhuma operadora processada" in texto

    def test_as_colunas_sao_a_uniao_do_que_saiu(self, relatorio):
        """Operadoras diferentes produzem coisas diferentes; a tabela acomoda."""
        relatorio.acrescentar(rel.LinhaDeRelatorio("CLARO", {"EXT": "sim", "cartas": "2"}))
        relatorio.acrescentar(rel.LinhaDeRelatorio("TIM", {"EXT": "sim"}))

        texto = relatorio.gravar().read_text(encoding="utf-8")

        assert "cartas" in texto
        assert "| TIM | ok | sim | - |" in texto, "TIM não gerou carta, e a célula fica '-'"

    def test_um_arquivo_por_execucao(self, relatorio, tmp_path):
        """A comparação da homologação é rodada a rodada, não acumulada."""
        caminho = relatorio.gravar()

        assert caminho.parent.name == "execucoes"
        assert caminho.suffix == ".md"

    def test_falha_ao_gravar_nao_derruba(self, relatorio, monkeypatch):
        """O relatório sai depois do trabalho feito; perdê-lo não é prejuízo."""
        from pathlib import Path

        monkeypatch.setattr(
            Path, "write_text", lambda *a, **k: (_ for _ in ()).throw(PermissionError())
        )

        assert relatorio.gravar() is None


class TestResetDeHomologacao:
    def test_recusa_rodar_em_producao(self, monkeypatch, capsys):
        """
        Apagar artefato de produção é perda de dado: eles são o que foi enviado
        à operadora e carregado no AGI.
        """
        from comum.config import configuration

        monkeypatch.setattr(configuration, "ENV", "prod")

        codigo = resetar_homologacao.main(["--referencia", "202507", "--sim"])

        assert codigo == 2
        assert "RECUSADO" in capsys.readouterr().out

    def test_referencia_malformada_e_recusada(self, capsys):
        assert resetar_homologacao.main(["--referencia", "julho", "--sim"]) == 2

    def test_encontra_os_artefatos_do_mes(self, tmp_path, monkeypatch):
        from comum.config import configuration

        monkeypatch.setattr(configuration, "ENV", "dev")
        monkeypatch.setattr(configuration, "CAMINHO_OPERADORAS", tmp_path)

        pasta = tmp_path / "CLARO" / "2025" / "202507" / "AGI"
        pasta.mkdir(parents=True)
        # O nome real que a HU-12 grava (nomenclatura.nome_ext).
        (pasta / "DE_AGI_D_202507_TBRA_X_CLARO_EXT.xlsx").write_text("x", encoding="utf-8")
        (pasta / "DETRAF_D_CLARO_202507.csv").write_text("x", encoding="utf-8")

        achados = resetar_homologacao._localizar_artefatos("202507")

        nomes = [c.name for c in achados]
        assert "DE_AGI_D_202507_TBRA_X_CLARO_EXT.xlsx" in nomes
        assert "DETRAF_D_CLARO_202507.csv" not in nomes, "o Detraf recebido é insumo"

    def test_a_carta_ct_nao_e_apagada(self, tmp_path, monkeypatch):
        """
        O número dela já foi consumido da sequência global e apagar o arquivo
        não o devolve — e a sequência é compartilhada com todo mundo.
        """
        from comum.config import configuration

        monkeypatch.setattr(configuration, "ENV", "dev")
        monkeypatch.setattr(configuration, "CAMINHO_OPERADORAS", tmp_path)

        pasta = tmp_path / "CLARO" / "2025" / "202507" / "Contestações"
        pasta.mkdir(parents=True)
        (pasta / "CT - 363.docx").write_text("x", encoding="utf-8")

        achados = resetar_homologacao._localizar_artefatos("202507")

        assert [c.name for c in achados] == []

    def test_mes_sem_pasta_nao_quebra(self, tmp_path, monkeypatch):
        from comum.config import configuration

        monkeypatch.setattr(configuration, "CAMINHO_OPERADORAS", tmp_path / "inexistente")

        assert resetar_homologacao._localizar_artefatos("202507") == []
