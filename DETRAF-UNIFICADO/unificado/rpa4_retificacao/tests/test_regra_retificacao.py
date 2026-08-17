"""As funções puras da HU-21: o cálculo do evento e a busca do processo.

A fixture `grid_contestacao_exportada.csv` é um **export real** da grid do AGI,
trazido da origem. Ele contém o caso adversarial que motivou a regra: as linhas
590969 e 590971 têm o mesmo EOT, a mesma referência e o mesmo tráfego, e só
diferem no valor. Sem o valor no cruzamento, o robô escolheria uma das duas e
lançaria a Recuperação no processo errado — e isso não se desfaz.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from comum.config.constantes import FATOR_LIQUIDO_PIS_COFINS
from comum.dominio.retificacao import (
    ProcessoNaoIdentificado,
    achar_id_processo,
    calcular_valores_evento,
    converter_valor_br,
)

CSV_GRID = Path(__file__).parent / "fixtures" / "grid_contestacao_exportada.csv"


class TestCalculoDoEvento:
    def test_os_tres_valores_fecham_entre_si(self):
        """
        Líquido + PIS/Cofins tem de dar exatamente o bruto.

        Por isso o PIS/Cofins é a **subtração**, e não `bruto × (1 - fator)`:
        calculado dos dois lados, o arredondamento deixaria centavo sobrando.
        """
        valores = calcular_valores_evento(minutos=1000.0, valor_bruto=852618.97)

        assert (
            valores["valor_liquido"] + valores["valor_pis_cofins"]
            == pytest.approx(852618.97)
        )

    def test_usa_a_constante_e_nao_um_literal(self):
        """
        🔴 Na origem o 0,9635 era literal no meio do cálculo. As premissas
        10.3/10.4 da V2 proíbem regra volátil embutida — e esta muda com CBS/IBS
        em 2027.
        """
        valores = calcular_valores_evento(minutos=1.0, valor_bruto=1000.0)

        assert valores["valor_liquido"] == round(1000.0 * FATOR_LIQUIDO_PIS_COFINS, 2)

    def test_duracao_e_bruto_passam_intactos(self):
        valores = calcular_valores_evento(minutos=409534.6, valor_bruto=2624.88)

        assert valores["duracao"] == 409534.6
        assert valores["valor_bruto_negociado"] == 2624.88

    def test_valor_zero_nao_quebra(self):
        valores = calcular_valores_evento(minutos=0.0, valor_bruto=0.0)

        assert valores["valor_liquido"] == 0.0
        assert valores["valor_pis_cofins"] == 0.0


class TestValorBrasileiro:
    @pytest.mark.parametrize(
        "texto, esperado",
        [
            ("852.618,97", 852618.97),
            ("509.114,3", 509114.3),
            ("0,01", 0.01),
            ("1.000.000,00", 1000000.0),
            ("  46,57  ", 46.57),
        ],
    )
    def test_converte_o_formato_do_agi(self, texto, esperado):
        """
        `float("852.618")` devolveria 852.618 — o número errado, sem erro nenhum.
        """
        assert converter_valor_br(texto) == pytest.approx(esperado)


class TestAcharProcesso:
    def test_acha_o_processo_certo(self):
        assert (
            achar_id_processo(
                CSV_GRID,
                eot_operadora="076",
                periodo_referencia="202607",
                periodo_trafego="202605",
                valor_bruto=586631.59,
            )
            == "590970"
        )

    def test_o_valor_desempata_as_linhas_gemeas(self):
        """
        O caso que motivou a regra: 590969 e 590971 só diferem no valor.
        """
        assert (
            achar_id_processo(
                CSV_GRID, "076", "202607", "202606", valor_bruto=852618.97
            )
            == "590969"
        )
        assert (
            achar_id_processo(
                CSV_GRID, "076", "202607", "202606", valor_bruto=694145.73
            )
            == "590971"
        )

    def test_sem_o_valor_haveria_duas_candidatas(self):
        """
        Prova por absurdo de que as três primeiras chaves não bastam: com um
        valor que casa nas duas, a busca recusa em vez de escolher.
        """
        with pytest.raises(ProcessoNaoIdentificado, match="encontrei 2"):
            achar_id_processo(
                CSV_GRID, "076", "202607", "202606", valor_bruto=0.0, tolerancia=10**9
            )

    def test_tolera_centavo_de_arredondamento(self):
        assert (
            achar_id_processo(
                CSV_GRID, "076", "202607", "202605", valor_bruto=586631.58
            )
            == "590970"
        )

    def test_nao_achar_e_erro_e_nao_none(self):
        """
        Devolver `None` faria o passo seguinte pesquisar um processo vazio e
        abrir sabe-se lá qual linha. Zero e vários são erro pelo mesmo motivo.
        """
        with pytest.raises(ProcessoNaoIdentificado, match="encontrei 0"):
            achar_id_processo(CSV_GRID, "999", "202607", "202606", valor_bruto=1.0)

    def test_a_mensagem_diz_o_que_procurava(self, tmp_path):
        """Quem lê o log precisa saber com que chaves a busca falhou."""
        with pytest.raises(ProcessoNaoIdentificado) as erro:
            achar_id_processo(CSV_GRID, "076", "209901", "209901", valor_bruto=7.77)

        assert "076" in str(erro.value)
        assert "209901" in str(erro.value)
        assert "7.77" in str(erro.value)

    def test_layout_diferente_falha_dizendo_qual_coluna_falta(self, tmp_path):
        """
        Se a grid do AGI mudar, a falha precisa nomear a coluna — e não sair como
        `KeyError` no meio do pandas.
        """
        csv_errado = tmp_path / "outro.csv"
        csv_errado.write_text("A;B\n1;2\n", encoding="utf-8")

        with pytest.raises(ProcessoNaoIdentificado, match="ID Processo"):
            achar_id_processo(csv_errado, "076", "202607", "202606", valor_bruto=1.0)
