"""O contrato entre quem GRAVA a saída da validação e quem a LÊ.

🔴 Estes testes existem por causa de um defeito que viveu meses sem uma única
falha: a validação gravava em `{operadora}/{ano}/{aaaamm}/Detrafs Recebidos` e o
batimento procurava em `{operadora}/{ano}/{aaaamm}`. Ele **nunca encontrava um
Detraf** — e o efeito não era um erro, era uma contestação com o lado da
operadora zerado e variação de -100%, que parece um resultado.

Um caminho derivado em dois lugares diverge. A partir de 2026-08-10 ele é
derivado num só, e o que este arquivo trava é justamente isso: dado o caminho de
ENTRADA de um arquivo, `caminho_de_saida` tem que devolver exatamente a pasta que
o batimento monta com `caminho_saida_operadora` / `caminho_saida_expectativa`.
"""

from pathlib import Path

import pytest

from comum.arquivos import estrutura_pastas as ep
from comum.config import configuration as cfg


@pytest.fixture
def raizes(tmp_path: Path) -> dict[str, Path]:
    return {
        "raiz_saida": tmp_path / "_SAIDA",
        "raiz_operadoras": tmp_path / "Operadoras",
        "raiz_expectativa": tmp_path / "Expectativa",
    }


class TestOContratoDosDoisLados:
    """O que a validação grava é onde o batimento lê. Ponto."""

    def test_o_detraf_cai_onde_o_batimento_procura(self, raizes):
        entrada = ep.caminho_detrafs_recebidos(
            "ALGAR", "202603", raiz_operadoras=raizes["raiz_operadoras"]
        )

        gravado = ep.caminho_de_saida(entrada, "202603", **raizes)
        lido = ep.caminho_saida_operadora(
            "ALGAR", "202603", raiz_saida=raizes["raiz_saida"]
        )

        assert gravado == lido

    def test_a_expectativa_cai_onde_o_batimento_procura(self, raizes):
        entrada = raizes["raiz_expectativa"] / "Vivo"
        entrada.mkdir(parents=True)

        gravado = ep.caminho_de_saida(entrada, "202603", **raizes)
        lido = ep.caminho_saida_expectativa(
            "Vivo", "202603", raiz_saida=raizes["raiz_saida"]
        )

        assert gravado == lido

    def test_o_batimento_enxerga_a_operadora_que_a_validacao_entregou(self, raizes):
        entrada = ep.caminho_detrafs_recebidos(
            "ALGAR", "202603", raiz_operadoras=raizes["raiz_operadoras"]
        )
        destino = ep.caminho_de_saida(entrada, "202603", criar=True, **raizes)
        (destino / "X_ENV.csv").write_text("a\n", encoding="utf-8")

        assert ep.listar_operadoras_com_saida(
            "202603", raiz_saida=raizes["raiz_saida"]
        ) == ["ALGAR"]


class TestEstruturaDaSaida:
    def test_o_ano_e_o_mes_nao_se_repetem_no_caminho(self, raizes):
        """A raiz já é por mês; repetir `{ano}/{aaaamm}` dentro dela é ruído."""
        caminho = ep.caminho_saida_operadora(
            "ALGAR", "202603", raiz_saida=raizes["raiz_saida"]
        )

        assert caminho.relative_to(raizes["raiz_saida"]).parts == (
            "202603",
            "Operadoras",
            "ALGAR",
            cfg.SUBPASTA_DETRAFS_RECEBIDOS,
        )

    def test_expectativa_e_operadoras_ficam_em_ramos_separados(self, raizes):
        """
        🔴 Sem esta separação, a pasta `Expectativa` ficaria irmã dos nomes de
        operadora — e quem varre a raiz tratando todo diretório como uma
        operadora processaria a expectativa como se fosse uma.
        """
        operadora = ep.caminho_saida_operadora(
            "Expectativa", "202603", raiz_saida=raizes["raiz_saida"]
        )
        expectativa = ep.caminho_saida_expectativa(
            "Vivo", "202603", raiz_saida=raizes["raiz_saida"]
        )

        # `.../Operadoras/Expectativa/{subpasta}` — o ramo é o avô do subpasta.
        assert operadora.parent.parent.name == "Operadoras"
        assert expectativa.parent.name == "Expectativa"
        assert operadora != expectativa

    def test_uma_operadora_chamada_expectativa_nao_e_confundida(self, raizes):
        entrada = ep.caminho_detrafs_recebidos(
            "Expectativa", "202603", raiz_operadoras=raizes["raiz_operadoras"]
        )
        destino = ep.caminho_de_saida(entrada, "202603", criar=True, **raizes)

        assert "Operadoras" in destino.parts
        assert ep.listar_operadoras_com_saida(
            "202603", raiz_saida=raizes["raiz_saida"]
        ) == ["Expectativa"]

    def test_criar_faz_a_arvore_no_disco(self, raizes):
        caminho = ep.caminho_saida_operadora(
            "ALGAR", "202603", raiz_saida=raizes["raiz_saida"], criar=True
        )

        assert caminho.is_dir()

    def test_sem_criar_nada_toca_o_disco(self, raizes):
        ep.caminho_saida_operadora("ALGAR", "202603", raiz_saida=raizes["raiz_saida"])

        assert not raizes["raiz_saida"].exists()


class TestOrigemDesconhecida:
    def test_pasta_fora_das_raizes_conhecidas_devolve_none(self, raizes, tmp_path):
        """
        `None` e não um palpite: um artefato entregue numa pasta que ninguém lê
        some sem deixar rastro. Melhor ele ficar na área de trabalho, com o
        motivo no log.
        """
        assert ep.caminho_de_saida(tmp_path / "qualquer", "202603", **raizes) is None

    def test_arvore_de_operadora_incompleta_devolve_none(self, raizes):
        """Faltando `{ano}/{aaaamm}/{subpasta}`, não dá para saber a operadora."""
        rasa = raizes["raiz_operadoras"] / "ALGAR" / "2026"

        assert ep.caminho_de_saida(rasa, "202603", **raizes) is None

    def test_expectativa_nao_configurada_nao_quebra(self, raizes, tmp_path):
        sem_expectativa = dict(raizes, raiz_expectativa=None)

        assert (
            ep.caminho_de_saida(tmp_path / "Expectativa" / "Vivo", "202603", **sem_expectativa)
            is None
        )


class TestListagem:
    def test_mes_sem_saida_devolve_lista_vazia(self, raizes):
        assert ep.listar_operadoras_com_saida(
            "202603", raiz_saida=raizes["raiz_saida"]
        ) == []

    def test_so_lista_o_mes_pedido(self, raizes):
        ep.caminho_saida_operadora(
            "ALGAR", "202602", raiz_saida=raizes["raiz_saida"], criar=True
        )

        assert ep.listar_operadoras_com_saida(
            "202603", raiz_saida=raizes["raiz_saida"]
        ) == []
