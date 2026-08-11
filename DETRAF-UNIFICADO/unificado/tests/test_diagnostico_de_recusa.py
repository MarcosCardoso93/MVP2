"""A forma comum da recusa, e o corpo do e-mail (2026-08-06).

Duas coisas recusam um Detraf — o layout ("não é o arquivo que eu esperava") e as
regras de coluna ("é um Detraf, mas com valor fora da regra"). Quem grava o
`_RECUSADO.md` e quem monta o e-mail não deveriam saber de qual delas o veredito
veio.

O que se protege: que a conversão seja **explícita**. Antes ela era coincidência
de nomes de atributo — bastaria renomear um campo no `ResultadoLayout` para o
diagnóstico sumir sem nenhum teste reclamar.
"""

import pandas as pd
import pytest

from comum.arquivos.recusa import SUFIXO_RECUSA, registrar_recusa
from comum.dominio.diagnostico_de_recusa import Diagnostico
from comum.dominio.layout_detraf import validar_layout
from comum.dominio.validacao_colunas import ValidadorColunas


class TestOsDoisVereditosViramAMesmaCoisa:
    def test_layout_produz_diagnostico(self):
        resultado = validar_layout(pd.DataFrame([["a", "b"]]))

        diagnostico = resultado.diagnostico()

        assert isinstance(diagnostico, Diagnostico)
        assert diagnostico.total_colunas == 2

    def test_colunas_produz_diagnostico(self, df_com, repo_cache):
        resultado = ValidadorColunas(referencia="202507").validar_tudo_detalhado(
            df_com(gh="X"), "detraf"
        )

        diagnostico = resultado.diagnostico(total_colunas=15)

        assert isinstance(diagnostico, Diagnostico)
        assert any("Coluna 8" in motivo for motivo in diagnostico.motivos_por_regra)

    def test_motivos_junta_as_duas_origens(self):
        diagnostico = Diagnostico(
            total_colunas=15, motivos_por_regra=["Coluna 8 (GH): errado"]
        )

        assert diagnostico.motivos() == ["Coluna 8 (GH): errado"]

    def test_sem_divergencia_nem_regra_o_motivo_solto_serve(self):
        """"arquivo vazio ou sem linhas" é tudo o que se sabe — e precisa sair."""
        diagnostico = Diagnostico(total_colunas=0, motivo="arquivo vazio")

        assert diagnostico.motivos() == ["arquivo vazio"]


class TestOArquivoDeRecusa:
    def test_aceita_um_resultado_de_layout(self, tmp_path):
        arquivo = tmp_path / "DETRAF.csv"
        arquivo.write_text("a;b\n", encoding="utf-8")
        resultado = validar_layout(pd.DataFrame([["a", "b"]]))

        destino = registrar_recusa(arquivo, resultado, None)

        assert destino == tmp_path / f"DETRAF{SUFIXO_RECUSA}"
        assert "recusado" in destino.read_text(encoding="utf-8").lower()

    def test_aceita_um_resultado_de_colunas(self, tmp_path, df_com, repo_cache):
        arquivo = tmp_path / "DETRAF.csv"
        arquivo.write_text("x\n", encoding="utf-8")
        df = df_com(gh="X")
        resultado = ValidadorColunas(referencia="202507").validar_tudo_detalhado(
            df, "detraf"
        )

        destino = registrar_recusa(arquivo, resultado, df)

        assert "Coluna 8" in destino.read_text(encoding="utf-8")

    def test_aceita_um_diagnostico_pronto(self, tmp_path):
        arquivo = tmp_path / "DETRAF.csv"
        arquivo.write_text("x\n", encoding="utf-8")

        destino = registrar_recusa(
            arquivo, Diagnostico(total_colunas=15, motivo="algo"), None
        )

        assert "algo" in destino.read_text(encoding="utf-8")


class TestCorpoDoEmail:
    def test_substitui_os_placeholders(self):
        from comum.integracoes.corpo_email import renderizar

        corpo = renderizar(
            "Olá, o arquivo {nome_arquivo} de {remetente}.",
            {"nome_arquivo": "DETRAF.csv", "remetente": "ops@operadora.com"},
        )

        assert corpo == "Olá, o arquivo DETRAF.csv de ops@operadora.com."

    def test_placeholder_desconhecido_fica_literal(self):
        """
        Melhor um `{campo_novo}` visível no rascunho — que quem revisa vê e
        corrige — do que uma exceção que impede o aviso inteiro de sair.
        """
        from comum.integracoes.corpo_email import renderizar

        assert renderizar("{nao_existe}", {"outro": "x"}) == "{nao_existe}"

    def test_os_motivos_cabem_no_corpo(self, df_com, repo_cache):
        """O que a mudança de 2026-08-06 acrescentou: dizer POR QUE foi recusado."""
        from comum.integracoes.corpo_email import renderizar

        resultado = ValidadorColunas(referencia="202507").validar_tudo_detalhado(
            df_com(gh="X"), "detraf"
        )
        motivos = "\n".join(f"- {m}" for m in resultado.motivos())

        corpo = renderizar("Motivos:\n{motivos}", {"motivos": motivos})

        assert "- Coluna 8 (GH):" in corpo
