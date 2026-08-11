"""Testes de src/utils/nomenclatura.py (T-006).

Cobre os padrões de nome de artefato do Épico 4 (AI/02 §7) e a normalização de
nome de operadora (acentos/espaços).
"""

import pytest

from comum.arquivos import nomenclatura as nom


class TestNormalizarOperadora:
    def test_remove_acentos_e_apara(self):
        assert nom.normalizar_operadora("  Álgar  ") == "Algar"

    def test_colapsa_espacos_internos(self):
        assert nom.normalizar_operadora("Algar   Telecom") == "Algar Telecom"

    def test_maiuscula(self):
        assert nom.normalizar_operadora("Telefônica", maiuscula=True) == "TELEFONICA"

    def test_vazio_levanta(self):
        with pytest.raises(ValueError):
            nom.normalizar_operadora("   ")

    def test_none_levanta(self):
        with pytest.raises(ValueError):
            nom.normalizar_operadora(None)


class TestNomesAgi:
    def test_nome_ext(self):
        assert nom.nome_ext("202507", "Claro") == "DE_AGI_D_202507_TBRA_X_CLARO_EXT"

    def test_nome_int(self):
        assert nom.nome_int("202507", "Claro") == "DE_AGI_D_202507_TBRA_X_CLARO_INT"

    def test_ext_normaliza_operadora_com_acento_e_espaco(self):
        assert (
            nom.nome_ext("202507", " Álgar Telecom ")
            == "DE_AGI_D_202507_TBRA_X_ALGAR TELECOM_EXT"
        )

    @pytest.mark.parametrize("periodo", ["2025", "20250", "2025071", "abcdef", ""])
    def test_periodo_invalido_levanta(self, periodo):
        with pytest.raises(ValueError):
            nom.nome_ext(periodo, "Claro")


class TestBaseEEnv:
    """
    `nome_base_contestacao` e `nome_modelo_base_contestacao` foram removidas em
    2026-08-04: a base de contestação virou tabela, e o modelo `_M` deixou de
    existir junto com o arquivo. O `_EXP` continua sendo arquivo.
    """

    def test_a_base_contestacao_nao_e_mais_um_arquivo(self):
        assert not hasattr(nom, "nome_base_contestacao")
        assert not hasattr(nom, "nome_modelo_base_contestacao")

    def test_env_usa_espaco_entre_base_e_contestacao(self):
        # Grafia literal da documentação (AI/09 §4.1): "Base Contestação..._ENV".
        # O sufixo em si foi renomeado para `_EXP` nesta troca — ver
        # `nomenclatura.nome_env` e `constantes.SUFIXO_EXP`.
        assert nom.nome_env("Claro", "202507") == "Base Contestação_Claro_202507_EXP"


class TestContProcECarta:
    def test_cont_proc_tem_extensao_xlsx_por_padrao(self):
        # D-7 resolvida (2026-07-23): o AGI aceita .xlsx.
        assert (
            nom.nome_cont_proc("Claro", "202507")
            == "CONT_PROC_MASCARA_Claro_202507.xlsx"
        )

    def test_cont_proc_extensao_parametrizavel(self):
        assert (
            nom.nome_cont_proc("Claro", "202507", extensao=".xls")
            == "CONT_PROC_MASCARA_Claro_202507.xls"
        )

    def test_nome_carta(self):
        assert nom.nome_carta(363) == "CT - 363"

    def test_numero_carta_invalido_levanta(self):
        with pytest.raises(ValueError):
            nom.nome_carta(0)
