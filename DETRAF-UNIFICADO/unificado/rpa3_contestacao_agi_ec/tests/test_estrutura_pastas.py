"""Testes de src/utils/estrutura_pastas.py (T-007)."""

import pytest

from comum.config import configuration as cfg
from comum.arquivos import estrutura_pastas as ep


class TestAnoDe:
    def test_extrai_ano(self):
        assert ep.ano_de("202507") == "2025"

    @pytest.mark.parametrize("periodo", ["2025", "abcdef", "2025071", ""])
    def test_invalido_levanta(self, periodo):
        with pytest.raises(ValueError):
            ep.ano_de(periodo)


class TestListarOperadorasDoMes:
    """
    A varredura estava duplicada no RPA 2 (`batimento_detraf` e
    `validacao_detrafs`) e o RPA 3 precisava dela para saber o que processar.
    """

    def test_lista_quem_tem_pasta_do_mes(self, raiz_operadoras):
        for operadora in ("Claro", "Algar"):
            (raiz_operadoras / operadora / "2025" / "202507").mkdir(parents=True)

        assert ep.listar_operadoras_do_mes("202507", raiz_operadoras) == [
            "Algar",
            "Claro",
        ]

    def test_ignora_quem_so_tem_outro_mes(self, raiz_operadoras):
        (raiz_operadoras / "Claro" / "2025" / "202506").mkdir(parents=True)

        assert ep.listar_operadoras_do_mes("202507", raiz_operadoras) == []

    def test_a_subpasta_pode_ser_exigida(self, raiz_operadoras):
        """
        O RPA 2 varre exigindo `Detrafs Recebidos`: uma operadora com a pasta do
        mês mas sem arquivo recebido não deve entrar na lista de trabalho.
        """
        (raiz_operadoras / "Claro" / "2025" / "202507" / cfg.SUBPASTA_DETRAFS_RECEBIDOS).mkdir(
            parents=True
        )
        (raiz_operadoras / "Algar" / "2025" / "202507").mkdir(parents=True)

        assert ep.listar_operadoras_do_mes(
            "202507", raiz_operadoras, subpasta=cfg.SUBPASTA_DETRAFS_RECEBIDOS
        ) == ["Claro"]

    def test_arquivo_solto_na_raiz_nao_e_operadora(self, raiz_operadoras):
        (raiz_operadoras / "leiame.txt").write_text("x", encoding="utf-8")

        assert ep.listar_operadoras_do_mes("202507", raiz_operadoras) == []

    def test_raiz_inexistente_devolve_vazio_sem_levantar(self, tmp_path):
        """Um mês sem nenhuma operadora é estado possível — quem chama decide."""
        assert ep.listar_operadoras_do_mes("202507", tmp_path / "nao_existe") == []

    def test_o_nome_da_pasta_e_preservado(self, raiz_operadoras):
        """
        Sem normalização de caixa nem de espaço: é este nome que
        `caminho_mes_operadora` usa para remontar o caminho, e uma divergência
        levaria o robô a procurar arquivo numa pasta que não existe.
        """
        (raiz_operadoras / "Vivo - SP1" / "2025" / "202507").mkdir(parents=True)

        assert ep.listar_operadoras_do_mes("202507", raiz_operadoras) == ["Vivo - SP1"]


class TestArvoreOperadora:
    def test_caminho_mes_operadora(self, raiz_operadoras):
        caminho = ep.caminho_mes_operadora(
            "Claro", "202507", raiz_operadoras=raiz_operadoras
        )
        assert caminho == raiz_operadoras / "Claro" / "2025" / "202507"
        # criar=False não deve criar no disco
        assert not caminho.exists()

    def test_subpastas_derivadas(self, raiz_operadoras):
        base = raiz_operadoras / "Claro" / "2025" / "202507"
        assert (
            ep.caminho_agi("Claro", "202507", raiz_operadoras=raiz_operadoras)
            == base / cfg.SUBPASTA_AGI
        )
        assert (
            ep.caminho_contestacoes("Claro", "202507", raiz_operadoras=raiz_operadoras)
            == base / cfg.SUBPASTA_CONTESTACOES
        )
        assert (
            ep.caminho_detrafs_recebidos(
                "Claro", "202507", raiz_operadoras=raiz_operadoras
            )
            == base / cfg.SUBPASTA_DETRAFS_RECEBIDOS
        )
        assert (
            ep.caminho_detrafs_enviados(
                "Claro", "202507", raiz_operadoras=raiz_operadoras
            )
            == base / cfg.SUBPASTA_DETRAFS_ENVIADOS
        )

    def test_criar_true_cria_no_disco(self, raiz_operadoras):
        caminho = ep.caminho_agi(
            "Claro", "202507", raiz_operadoras=raiz_operadoras, criar=True
        )
        assert caminho.is_dir()


class TestControleCt:
    def test_caminho_controle_ct(self, raiz_controle_ct):
        caminho = ep.caminho_controle_ct("202507", raiz_controle_ct=raiz_controle_ct)
        assert caminho == raiz_controle_ct / "2025"

    def test_criar_true(self, raiz_controle_ct):
        caminho = ep.caminho_controle_ct(
            "202507", raiz_controle_ct=raiz_controle_ct, criar=True
        )
        assert caminho.is_dir()
