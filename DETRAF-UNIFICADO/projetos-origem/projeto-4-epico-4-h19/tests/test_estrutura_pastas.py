"""Testes de src/utils/estrutura_pastas.py (T-007)."""

import pytest

from src.config import configuration as cfg
from src.utils import estrutura_pastas as ep


class TestAnoDe:
    def test_extrai_ano(self):
        assert ep.ano_de("202507") == "2025"

    @pytest.mark.parametrize("periodo", ["2025", "abcdef", "2025071", ""])
    def test_invalido_levanta(self, periodo):
        with pytest.raises(ValueError):
            ep.ano_de(periodo)


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
