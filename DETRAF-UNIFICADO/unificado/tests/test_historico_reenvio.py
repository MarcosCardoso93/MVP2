"""O histórico distingue "já processei" de "tem o mesmo nome".

🔴 Até 2026-08-10 a comparação era só pelo caminho absoluto. Isso quebrava um
critério explícito da HU-03 — *"reenvio de arquivo com o mesmo nome sobrescreve o
anterior e inicia novo processamento"* — do jeito mais perigoso possível: o RPA 1
sobrescrevia o arquivo, o caminho continuava o mesmo, e a correção enviada pela
operadora era ignorada em silêncio pela validação e pelo batimento.

O que estes testes travam é a distinção. O arquivo idêntico continua sendo
pulado, porque é para isso que o histórico existe.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from comum.arquivos.historico import ValidadorHistoricoRPA


@pytest.fixture
def historico(tmp_path, monkeypatch):
    """`ValidadorHistoricoRPA` com o JSON num diretório temporário."""
    monkeypatch.setenv("DIRETORIO_HISTORICO_ARQUIVOS", str(tmp_path))

    import comum.arquivos.historico as modulo

    monkeypatch.setattr(modulo, "DIRETORIO_HISTORICO_ARQUIVOS", str(tmp_path))
    monkeypatch.setattr(modulo, "ANO_MES_REFERENCIA", "202603")

    return ValidadorHistoricoRPA()


@pytest.fixture
def detraf(tmp_path) -> Path:
    arquivo = tmp_path / "DETRAF_ALGAR.csv"
    arquivo.write_text("linha1\nlinha2\n", encoding="utf-8")
    return arquivo


def _envelhecer(caminho: Path, segundos: int = 10) -> None:
    """Recua o mtime, para o teste não depender do relógio."""
    informacao = caminho.stat()
    os.utime(caminho, (informacao.st_atime, informacao.st_mtime - segundos))


class TestArquivoIdentico:
    def test_o_mesmo_arquivo_nao_e_reprocessado(self, historico, detraf):
        """A proteção anti-reprocessamento continua valendo — é o caso comum."""
        historico.registrar_arquivos([detraf], status_valido=True)

        assert historico.arquivo_ja_processado(str(detraf)) is True

    def test_arquivo_nunca_visto_e_novo(self, historico, detraf):
        assert historico.arquivo_ja_processado(str(detraf)) is False

    def test_filtrar_remove_o_ja_processado(self, historico, detraf):
        historico.registrar_arquivos([detraf], status_valido=True)

        assert historico.filtrar_arquivos_novos([detraf]) == []


class TestReenvioComOMesmoNome:
    def test_conteudo_diferente_volta_a_ser_processado(self, historico, detraf):
        """O caso da HU-03: a operadora corrigiu e mandou de novo."""
        historico.registrar_arquivos([detraf], status_valido=False)
        detraf.write_text("linha1\nlinha2\nlinha3 corrigida\n", encoding="utf-8")

        assert historico.arquivo_ja_processado(str(detraf)) is False

    def test_o_filtro_devolve_o_arquivo_corrigido(self, historico, detraf):
        historico.registrar_arquivos([detraf], status_valido=False)
        detraf.write_text("outro conteudo bem maior aqui\n", encoding="utf-8")

        assert historico.filtrar_arquivos_novos([detraf]) == [detraf]

    def test_mesmo_tamanho_mas_data_diferente_reprocessa(self, historico, detraf):
        """
        Substituição por arquivo de tamanho igual e conteúdo diferente é
        plausível — layout fixo, um dígito trocado. O tamanho sozinho não pega.
        """
        historico.registrar_arquivos([detraf], status_valido=True)
        detraf.write_text("linha9\nlinha8\n", encoding="utf-8")  # mesmo tamanho
        _envelhecer(detraf, segundos=-30)  # mtime para a frente

        assert historico.arquivo_ja_processado(str(detraf)) is False

    def test_reprocessar_avisa_no_log(self, historico, detraf, caplog):
        """
        Reprocessar é raro e consequente — quem lê o log precisa entender por que
        um arquivo que já tinha passado voltou.
        """
        historico.registrar_arquivos([detraf], status_valido=True)
        detraf.write_text("conteudo novo e diferente\n", encoding="utf-8")

        historico.arquivo_ja_processado(str(detraf))

        assert "reenvio" in caplog.text.lower()


class TestCasosDeBorda:
    def test_arquivo_que_sumiu_do_disco_nao_volta(self, historico, detraf):
        """
        Está no histórico e não existe mais: não há o que reprocessar, e
        devolvê-lo faria a varredura seguinte tentar abrir o que não está lá.
        """
        historico.registrar_arquivos([detraf], status_valido=True)
        detraf.unlink()

        assert historico.arquivo_ja_processado(str(detraf)) is True

    def test_registro_antigo_sem_assinatura_continua_valendo(
        self, historico, detraf
    ):
        """
        Compatibilidade: quem já rodou tem entradas sem `modificado_em`. Elas não
        podem fazer o mês inteiro ser reprocessado na primeira execução após a
        mudança — o tamanho sozinho decide.
        """
        historico.registrar_arquivos([detraf], status_valido=True)
        registro = historico.historico[str(detraf.resolve())]
        del registro["modificado_em"]

        assert historico.arquivo_ja_processado(str(detraf)) is True

        detraf.write_text("agora mudou de tamanho\n", encoding="utf-8")
        assert historico.arquivo_ja_processado(str(detraf)) is False

    def test_registro_sem_tamanho_nem_data_e_tratado_como_processado(
        self, historico, detraf
    ):
        """Sem nada com que comparar, vale o comportamento antigo."""
        historico.registrar_arquivos([detraf], status_valido=True)
        registro = historico.historico[str(detraf.resolve())]
        registro.pop("modificado_em")
        registro.pop("tamanho_bytes")

        assert historico.arquivo_ja_processado(str(detraf)) is True
