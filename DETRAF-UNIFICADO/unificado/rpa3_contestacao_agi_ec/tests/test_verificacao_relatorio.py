"""HU-20 — verificação do Relatório de Receitas e Despesas (Projeto 6).

O Projeto 6 veio **sem nenhum teste**, como os quatro anteriores. E veio só com a
HU-20 — a HU-21 e o RPA 4 continuam sem código.

⚠️ **A própria V2 questiona se esta HU deve existir** (¶706: *"trata-se de uma
dupla checagem, conferir com o solicitante se esse processo vale a pena ou não ser
mantido"*). É a pendência **Q7**. O código foi migrado assim mesmo, atrás de
kill-switch — e estes testes existem para que, se a HU for descartada, dê para
removê-la inteira com confiança.
"""

from pathlib import Path

import pandas as pd
import pytest

from comum.config import configuration
from src.services import verificacao_relatorio as vr

#: Cabeçalho real do export do AGI — 22 colunas, incluindo as três de imposto.
_CABECALHO = (
    "Per. Refer.;Per. Traf.;Grp. Oper .Prest;Oper. Prest.;Natureza;"
    "Vlr. Bruto;Vlr. IBS Estadual;Vlr. IBS Municipal;Vlr. CBS"
)


def _linha(operadora, natureza="D", bruto="100,00", ibs_e="1,00", ibs_m="2,00", cbs="3,00"):
    return f"202507;202507;{operadora};{operadora} S.A;{natureza};{bruto};{ibs_e};{ibs_m};{cbs}"


@pytest.fixture()
def relatorio(tmp_path):
    """Fábrica de CSV no formato do export do AGI."""

    def _criar(*linhas: str, nome: str = "remessa_baixada.csv") -> Path:
        caminho = tmp_path / nome
        caminho.write_text(
            "\n".join([_CABECALHO, *linhas]) + "\n", encoding="utf-8"
        )
        return caminho

    return _criar


class _AGIProibido:
    """Qualquer toque no AGI é falha de teste."""

    def __getattr__(self, nome):
        def _explodir(*args, **kwargs):
            raise AssertionError(f"O AGI foi acionado ('{nome}').")

        return _explodir


class _RepositorioFalso:
    def __init__(self, subtotais: dict[str, float]):
        self._subtotais = subtotais

    def obter_subtotal_despesa_por_operadora(self, referencia):
        return self._subtotais


# ---------------------------------------------------------------------------
# Leitura do relatório
# ---------------------------------------------------------------------------


class TestLeituraDoRelatorio:
    def test_fica_so_com_as_linhas_de_despesa(self, relatorio):
        """A V2 (¶696) manda filtrar pela Natureza "D" — a HU-20 é só despesa."""
        caminho = relatorio(
            _linha("CLARO", natureza="D"),
            _linha("CLARO", natureza="C"),
            _linha("ALGAR", natureza="D"),
        )

        despesa = vr.carregar_relatorio(caminho)

        assert len(despesa) == 2

    def test_relatorio_ausente_acusa_em_vez_de_concluir_que_esta_tudo_certo(
        self, tmp_path
    ):
        """
        Sem relatório não há verificação. Devolver vazio faria a HU concluir
        "nenhuma divergência" — que é o pior desfecho possível para uma HU cuja
        razão de existir é achar divergência.
        """
        with pytest.raises(vr.RelatorioAgiIndisponivel, match="não encontrado"):
            vr.carregar_relatorio(tmp_path / "nao_existe.csv")

    def test_layout_diferente_acusa_e_nomeia_a_coluna(self, tmp_path):
        caminho = tmp_path / "outro_layout.csv"
        caminho.write_text("A;B;C\n1;2;3\n", encoding="utf-8")

        with pytest.raises(vr.RelatorioAgiIndisponivel, match="Vlr. Bruto"):
            vr.carregar_relatorio(caminho)

    def test_export_sem_as_colunas_de_imposto_avisa(self, tmp_path, caplog):
        """A V2 (¶702) manda compará-las; um export antigo não as traz."""
        caminho = tmp_path / "antigo.csv"
        caminho.write_text(
            "Grp. Oper .Prest;Natureza;Vlr. Bruto\nCLARO;D;100,00\n", encoding="utf-8"
        )

        with caplog.at_level("WARNING"):
            vr.carregar_relatorio(caminho)

        assert "Vlr. CBS" in caplog.text


# ---------------------------------------------------------------------------
# Soma por operadora
# ---------------------------------------------------------------------------


class TestSomaPorOperadora:
    def test_soma_o_valor_bruto_por_operadora(self, relatorio):
        despesa = vr.carregar_relatorio(
            relatorio(
                _linha("CLARO", bruto="100,00"),
                _linha("CLARO", bruto="250,50"),
                _linha("ALGAR", bruto="10,00"),
            )
        )

        somas = vr.somar_por_operadora(despesa).set_index("operadora")

        assert somas.loc["CLARO", vr.COL_VALOR_BRUTO] == pytest.approx(350.50)
        assert somas.loc["ALGAR", vr.COL_VALOR_BRUTO] == pytest.approx(10.00)

    def test_o_separador_de_milhar_do_agi_e_tratado(self, relatorio):
        """
        O export vem no formato brasileiro: `"1.234,56"`. O ponto de milhar é
        removido **antes** da troca da vírgula — a ordem importa.
        """
        despesa = vr.carregar_relatorio(relatorio(_linha("CLARO", bruto="1.234,56")))

        somas = vr.somar_por_operadora(despesa)

        assert somas.iloc[0][vr.COL_VALOR_BRUTO] == pytest.approx(1234.56)

    def test_as_tres_colunas_de_imposto_entram(self, relatorio):
        """
        🆕 Acrescentado em 2026-08-05. O Projeto 6 somava só `Vlr. Bruto` — uma
        tupla de **um** elemento —, enquanto o CSV entregue no próprio pacote já
        trazia as três colunas novas. A V2 (¶702) manda compará-las.
        """
        despesa = vr.carregar_relatorio(
            relatorio(
                _linha("CLARO", ibs_e="1,00", ibs_m="2,00", cbs="3,00"),
                _linha("CLARO", ibs_e="0,50", ibs_m="0,50", cbs="0,50"),
            )
        )

        somas = vr.somar_por_operadora(despesa).iloc[0]

        assert somas[vr.COL_IBS_ESTADUAL] == pytest.approx(1.50)
        assert somas[vr.COL_IBS_MUNICIPAL] == pytest.approx(2.50)
        assert somas[vr.COL_CBS] == pytest.approx(3.50)

    def test_relatorio_sem_despesa_devolve_vazio_sem_quebrar(self, relatorio):
        despesa = vr.carregar_relatorio(relatorio(_linha("CLARO", natureza="C")))

        assert vr.somar_por_operadora(despesa).empty


# ---------------------------------------------------------------------------
# Comparação com o Encontro de Contas
# ---------------------------------------------------------------------------


class TestComparacao:
    def _somas(self, **por_operadora) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"operadora": nome, vr.COL_VALOR_BRUTO: valor}
                for nome, valor in por_operadora.items()
            ]
        )

    def test_valores_que_batem_nao_geram_inconsistencia(self):
        comparado = vr.comparar_com_encontro_de_contas(
            self._somas(CLARO=1000.00), {"CLARO": -1000.00}
        )

        assert comparado.iloc[0]["inconsistente"] is False or not comparado.iloc[0]["inconsistente"]

    def test_o_sinal_do_ec_e_normalizado(self):
        """
        O EC guarda a despesa como **negativo**; o AGI soma como positivo.
        Comparar sem normalizar acusaria o dobro do valor como divergência em
        toda operadora — e a HU inteira viraria ruído.
        """
        comparado = vr.comparar_com_encontro_de_contas(
            self._somas(CLARO=521.60), {"CLARO": -521.60}
        )

        assert comparado.iloc[0]["diferenca"] == pytest.approx(0.0)

    def test_diferenca_acima_da_tolerancia_e_inconsistente(self):
        comparado = vr.comparar_com_encontro_de_contas(
            self._somas(CLARO=1000.00), {"CLARO": -950.00}
        )

        assert comparado.iloc[0]["inconsistente"]
        assert comparado.iloc[0]["diferenca"] == pytest.approx(50.0)

    def test_diferenca_de_centavos_fica_dentro_da_tolerancia(self):
        comparado = vr.comparar_com_encontro_de_contas(
            self._somas(CLARO=1000.00), {"CLARO": -1000.005}, tolerancia=0.01
        )

        assert not comparado.iloc[0]["inconsistente"]

    def test_operadora_ausente_do_ec_e_inconsistente_e_nao_zero(self):
        """
        Uma operadora que aparece no AGI e não no Encontro de Contas é
        **exatamente** o que esta HU existe para pegar. Tratar como zero a faria
        passar batido.
        """
        comparado = vr.comparar_com_encontro_de_contas(
            self._somas(OPERADORA_NOVA=800.00), {}
        )

        assert comparado.iloc[0]["inconsistente"]
        assert pd.isna(comparado.iloc[0]["diferenca"])

    def test_o_ec_ausente_nao_quebra_o_abs(self):
        """
        Regressão apanhada no Projeto 6: com `None` em vez de `NaN`, a coluna fica
        com dtype `object` e o `.abs()` estoura com *"bad operand type for abs()"*.
        """
        comparado = vr.comparar_com_encontro_de_contas(
            self._somas(A=1.0, B=2.0), {"A": -1.0}
        )

        assert len(comparado) == 2

    def test_a_tolerancia_e_configuravel(self, monkeypatch):
        """
        ⚠️ O limiar veio do Projeto 6 com um TODO admitindo que **o valor oficial
        não foi confirmado** com a área cliente (pendência nova).
        """
        monkeypatch.setattr(configuration, "TOLERANCIA_VERIFICACAO", 100.0)

        comparado = vr.comparar_com_encontro_de_contas(
            self._somas(CLARO=1000.00), {"CLARO": -950.00}
        )

        assert not comparado.iloc[0]["inconsistente"]


# ---------------------------------------------------------------------------
# Relatório de inconsistências
# ---------------------------------------------------------------------------


class TestRelatorioDeInconsistencias:
    def _comparado(self, inconsistente: bool) -> pd.DataFrame:
        return pd.DataFrame([{
            "operadora": "CLARO",
            "vb_agi": 1000.0,
            "vb_ec": 950.0 if inconsistente else 1000.0,
            "diferenca": 50.0 if inconsistente else 0.0,
            "inconsistente": inconsistente,
        }])

    def test_grava_o_xlsx_quando_ha_divergencia(self, tmp_path):
        caminho = vr.gravar_inconsistencias(
            self._comparado(True), "202507", diretorio=tmp_path
        )

        assert caminho is not None and caminho.is_file()
        assert caminho.suffix == ".xlsx"

    def test_o_nome_traz_a_competencia(self, tmp_path):
        """Sem isso, uma reexecução apagaria a evidência da anterior."""
        caminho = vr.gravar_inconsistencias(
            self._comparado(True), "202507", diretorio=tmp_path
        )

        assert "202507" in caminho.name

    def test_sem_divergencia_nao_grava_nada(self, tmp_path):
        assert (
            vr.gravar_inconsistencias(self._comparado(False), "202507", tmp_path)
            is None
        )
        assert list(tmp_path.glob("*.xlsx")) == []

    def test_cada_divergencia_aparece_no_log(self, tmp_path, caplog):
        with caplog.at_level("WARNING"):
            vr.gravar_inconsistencias(self._comparado(True), "202507", tmp_path)

        assert "CLARO" in caplog.text

    def test_a_operadora_ausente_do_ec_e_descrita_como_tal(self, tmp_path, caplog):
        """Diferente de "diferença de R$ X" — a causa é outra e o texto precisa dizer."""
        comparado = pd.DataFrame([{
            "operadora": "NOVA",
            "vb_agi": 800.0,
            "vb_ec": float("nan"),
            "diferenca": float("nan"),
            "inconsistente": True,
        }])

        with caplog.at_level("WARNING"):
            vr.gravar_inconsistencias(comparado, "202507", tmp_path)

        assert "ausente no Encontro de Contas" in caplog.text

    def test_o_default_e_a_pasta_comum_de_logs(self):
        """Decisão de 2026-08-05: o relatório fica junto do log."""
        assert (
            configuration.DIRETORIO_INCONSISTENCIAS.name == "inconsistencias"
        )
        assert (
            configuration.RAIZ_LOGS in configuration.DIRETORIO_INCONSISTENCIAS.parents
        )


# ---------------------------------------------------------------------------
# Kill-switch
# ---------------------------------------------------------------------------


class TestKillSwitch:
    def test_com_o_switch_desligado_o_agi_nao_e_aberto(
        self, relatorio, tmp_path, monkeypatch
    ):
        """
        A HU-20 é leitura, mas **abre e loga no AGI de produção** — e não há
        ambiente de teste (Q20). O Projeto 6 declarava `PERMITIR_ACAO_AGI` e
        **nunca o lia**: era decorativo.
        """
        monkeypatch.setattr(configuration, "PERMITIR_ACESSO_AGI", False)
        caminho = relatorio(_linha("CLARO", bruto="1000,00"))

        servico = vr.VerificacaoRelatorio(
            agi=_AGIProibido(), repositorio=_RepositorioFalso({"CLARO": -1000.00})
        )

        assert (
            servico.executar(
                "202507",
                caminho_relatorio=caminho,
                diretorio_inconsistencias=tmp_path,
            )
            is None
        )

    def test_sem_relatorio_e_com_o_switch_desligado_a_execucao_falha(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(configuration, "PERMITIR_ACESSO_AGI", False)

        servico = vr.VerificacaoRelatorio(
            agi=_AGIProibido(), repositorio=_RepositorioFalso({})
        )

        with pytest.raises(vr.RelatorioAgiIndisponivel):
            servico.executar("202507", caminho_relatorio=tmp_path / "nada.csv")


class TestFluxoCompleto:
    def test_do_csv_ao_xlsx_de_divergencia(self, relatorio, tmp_path, monkeypatch):
        monkeypatch.setattr(configuration, "PERMITIR_ACESSO_AGI", False)
        caminho = relatorio(
            _linha("CLARO", bruto="1.000,00"),
            _linha("ALGAR", bruto="500,00"),
            _linha("VIVO", natureza="C", bruto="999,00"),
        )

        servico = vr.VerificacaoRelatorio(
            agi=_AGIProibido(),
            # ALGAR bate; CLARO diverge em 100; VIVO é receita e não entra.
            repositorio=_RepositorioFalso({"CLARO": -900.00, "ALGAR": -500.00}),
        )

        saida = servico.executar(
            "202507", caminho_relatorio=caminho, diretorio_inconsistencias=tmp_path
        )

        assert saida is not None
        divergentes = pd.read_excel(saida)
        assert list(divergentes["operadora"]) == ["CLARO"]


class TestTotaisDeImpostoNoLog:
    """
    Q6, decisão de 2026-08-06 — os impostos passam a deixar rastro todo mês.

    A V2 (¶702) manda comparar CBS e IBS, mas o Encontro de Contas não tem
    coluna de imposto: não há contra o que comparar. E não corre — o ¶367 diz
    que eles são informativos até 2027.

    O problema não era a falta de comparação; era a **falta de registro**. As
    somas iam junto no `.xlsx` de inconsistências, e num mês **sem** divergência
    nenhum arquivo era gravado. Em 2027, "quanto foi de CBS em julho de 2026?"
    não teria resposta.
    """

    def _comparado(self, com_imposto: bool = True, inconsistente: bool = False):
        linha = {
            "operadora": "CLARO",
            vr.COL_VALOR_BRUTO: 1000.0,
            "vb_agi": 1000.0,
            "vb_ec": 1000.0,
            "diferenca": 0.0,
            "inconsistente": inconsistente,
        }
        if com_imposto:
            linha[vr.COL_CBS] = 88.0
            linha[vr.COL_IBS_ESTADUAL] = 55.0
            linha[vr.COL_IBS_MUNICIPAL] = 22.0
        return pd.DataFrame([linha])

    def test_mes_sem_divergencia_registra_os_impostos(self, tmp_path, caplog):
        """É o caso que antes não deixava rastro nenhum."""
        with caplog.at_level("INFO"):
            caminho = vr.gravar_inconsistencias(
                self._comparado(), "202507", diretorio=tmp_path
            )

        assert caminho is None, "sem divergência, não há planilha — isso não mudou"
        assert "88" in caplog.text and "55" in caplog.text and "22" in caplog.text
        assert "Q6" in caplog.text, "quem lê o log precisa saber por que não há comparação"

    def test_o_registro_diz_que_e_informativo(self, tmp_path, caplog):
        """
        Sem isso, um total de imposto no log parece resultado de conferência —
        e não é: nada foi comparado.
        """
        with caplog.at_level("INFO"):
            vr.gravar_inconsistencias(self._comparado(), "202507", diretorio=tmp_path)

        assert "Informativo" in caplog.text
        assert "2027" in caplog.text

    def test_relatorio_antigo_sem_as_colunas_nao_quebra(self, tmp_path, caplog):
        """Export antigo do AGI não tem CBS/IBS — não é motivo para falhar."""
        with caplog.at_level("INFO"):
            vr.gravar_inconsistencias(
                self._comparado(com_imposto=False), "202507", diretorio=tmp_path
            )

        assert "Impostos somados" not in caplog.text

    def test_a_planilha_de_divergencia_continua_saindo(self, tmp_path):
        caminho = vr.gravar_inconsistencias(
            self._comparado(inconsistente=True), "202507", diretorio=tmp_path
        )

        assert caminho is not None and caminho.is_file()
