"""A montagem do corpo da resposta à operadora (2026-08-06).

Cobre o que o teste do template não alcança: como a lista de arquivos é
formatada, o que acontece sem template, e a data.

O ponto que se repete aqui: **nada levanta**. Quando estas funções rodam, as
recusas já estão consumadas — os arquivos estão na quarentena, com o diagnóstico
ao lado. Falhar em avisar é ruim; desfazer a recusa por causa disso seria pior.
"""

from pathlib import Path

import pytest

from comum.config import configuration
from src.models.dto.arquivo_para_processar import ArquivoParaProcessar
from src.models.dto.arquivo_recusado import ArquivoRecusado
from src.services.notificacao_operadora import (
    formatar_arquivos,
    formatar_data,
    notificar_arquivos_recusados,
)


def _pacote(tmp_path) -> ArquivoParaProcessar:
    return ArquivoParaProcessar(
        caminho=tmp_path / "DETRAF.csv",
        sender_email="ops@operadora.com.br",
        entry_id="ENTRY-1",
        subject="Detraf julho",
        received_at="2026-08-03T09:14:00",
    )


class _ResponderFalso:
    def __init__(self, resultado: bool = True):
        self.corpo = None
        self.enviar = None
        self._resultado = resultado

    def __call__(self, pacote, corpo, enviar) -> bool:
        self.corpo = corpo
        self.enviar = enviar
        return self._resultado


class TestListaDeArquivos:
    def test_um_arquivo_sai_sem_numeracao(self):
        """Um "1)" solitário parece um fragmento de lista, e um anexo é o caso comum."""
        texto = formatar_arquivos([ArquivoRecusado("A.csv", ["motivo um"])])

        assert texto.startswith("A.csv")
        assert "1)" not in texto

    def test_varios_arquivos_saem_numerados(self):
        """A numeração é o que permite a operadora conferir item a item."""
        texto = formatar_arquivos([
            ArquivoRecusado("A.csv", ["motivo um"]),
            ArquivoRecusado("B.csv", ["motivo dois"]),
        ])

        assert "1) A.csv" in texto
        assert "2) B.csv" in texto

    def test_cada_motivo_fica_sob_o_seu_arquivo(self):
        texto = formatar_arquivos([
            ArquivoRecusado("A.csv", ["erro do A"]),
            ArquivoRecusado("B.csv", ["erro do B"]),
        ])

        assert texto.index("A.csv") < texto.index("erro do A") < texto.index("B.csv")

    def test_varios_motivos_do_mesmo_arquivo_saem_um_por_linha(self):
        texto = formatar_arquivos([ArquivoRecusado("A.csv", ["um", "dois"])])

        assert "   - um" in texto
        assert "   - dois" in texto

    def test_arquivo_sem_motivo_nao_deixa_buraco(self):
        """
        Um item de lista vazio faria a operadora achar que faltou conteúdo — e
        ela não teria como saber que é o robô que não soube explicar.
        """
        texto = formatar_arquivos([ArquivoRecusado("A.csv", [])])

        assert "A.csv" in texto
        assert "consulte o remetente" in texto

    def test_lista_vazia_nao_estoura(self):
        assert "consulte o remetente" in formatar_arquivos([])


class TestData:
    def test_iso_vira_formato_brasileiro(self):
        """
        `received_at.isoformat()` é ótimo para guardar e ruim para ler — e este é
        o único texto do projeto que a operadora vê.
        """
        assert formatar_data("2026-08-03T09:14:00") == "03/08/2026 09:14"

    def test_valor_incompreensivel_volta_como_veio(self):
        """Melhor uma data estranha do que uma data errada."""
        assert formatar_data("terça-feira") == "terça-feira"

    def test_vazio_continua_vazio(self):
        assert formatar_data("") == ""


class TestNotificacao:
    def test_o_corpo_leva_os_arquivos_e_a_quantidade(self, tmp_path, monkeypatch):
        template = tmp_path / "modelo.txt"
        template.write_text("{quantidade}\n{arquivos}", encoding="utf-8")
        monkeypatch.setattr(
            configuration, "CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO", template
        )
        responder = _ResponderFalso()

        notificar_arquivos_recusados(
            responder,
            _pacote(tmp_path),
            [ArquivoRecusado("A.csv", ["x"]), ArquivoRecusado("B.csv", ["y"])],
        )

        assert responder.corpo.startswith("2")
        assert "A.csv" in responder.corpo and "B.csv" in responder.corpo

    def test_rascunho_e_o_padrao(self, tmp_path, monkeypatch):
        """O envio é irreversível e externo — só sai com a chave explicitamente ligada."""
        template = tmp_path / "modelo.txt"
        template.write_text("{arquivos}", encoding="utf-8")
        monkeypatch.setattr(
            configuration, "CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO", template
        )
        monkeypatch.setattr(configuration, "NOTIFICAR_OPERADORA_ENVIAR", False)
        responder = _ResponderFalso()

        notificar_arquivos_recusados(
            responder, _pacote(tmp_path), [ArquivoRecusado("A.csv", ["x"])]
        )

        assert responder.enviar is False

    def test_template_nao_configurado_devolve_False_sem_estourar(
        self, tmp_path, monkeypatch, caplog
    ):
        monkeypatch.setattr(
            configuration, "CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO", None
        )
        responder = _ResponderFalso()

        resultado = notificar_arquivos_recusados(
            responder, _pacote(tmp_path), [ArquivoRecusado("A.csv", ["x"])]
        )

        assert resultado is False
        assert responder.corpo is None
        assert "não está configurada" in caplog.text

    def test_template_inexistente_devolve_False(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr(
            configuration,
            "CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO",
            tmp_path / "nao-existe.txt",
        )

        resultado = notificar_arquivos_recusados(
            _ResponderFalso(), _pacote(tmp_path), [ArquivoRecusado("A.csv", ["x"])]
        )

        assert resultado is False
        assert "não encontrado" in caplog.text

    def test_sem_recusas_nao_manda_nada(self, tmp_path):
        """Um e-mail dizendo que zero arquivos foram recusados seria ruído puro."""
        responder = _ResponderFalso()

        assert notificar_arquivos_recusados(responder, _pacote(tmp_path), []) is False
        assert responder.corpo is None
