"""Testes de src/utils/nomenclatura.py (T-006).

Cobre os padrões de nome de artefato do Épico 4 (AI/02 §7) e a normalização de
nome de operadora (acentos/espaços).
"""

import pytest

from src.utils import nomenclatura as nom


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
    def test_base_contestacao(self):
        assert (
            nom.nome_base_contestacao("Claro", "202507")
            == "Base_Contestação_Claro_202507"
        )

    def test_modelo_base(self):
        assert (
            nom.nome_modelo_base_contestacao("Claro", "202507")
            == "Base_Contestação_Claro_202507_M"
        )

    def test_env_usa_espaco_entre_base_e_contestacao(self):
        # Grafia literal da documentação (AI/09 §4.1): "Base Contestação..._ENV".
        assert nom.nome_env("Claro", "202507") == "Base Contestação_Claro_202507_ENV"


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
