"""Limpeza de tráfegos (`_BK`/`_LL`) e consolidação do resultado no banco.

Os dois módulos foram corrigidos em 2026-08-04 — cada um escondia uma falha atrás
de um resultado de sucesso. Estes testes existem para que a correção não se
desfaça numa refatoração futura: sem eles, alguém "simplificando" o `except` de
volta para `logger.error` + `return True` não veria nada quebrar.
"""

import pandas as pd
import pytest

from src.services.resultado_validacao import (
    COD_ERRO_LEITURA,
    COD_ERRO_VALIDACAO,
    LeituraDetrafFalhou,
    TransformadorRelatorioRPA,
    obter_codigo_erro,
)
from src.services.validacao_inicial.limpeza_trafegos import LimpadorTrafegos

from conftest import LINHA_VALIDA, linha


def _escrever_detraf(caminho, linhas: list[list[str]]) -> None:
    caminho.write_text(
        "\n".join(";".join(coluna) for coluna in linhas) + "\n", encoding="utf-8"
    )


class TestLimpezaDeTrafegos:
    @pytest.fixture()
    def limpador(self) -> LimpadorTrafegos:
        return LimpadorTrafegos()

    def test_arquivo_ilegivel_propaga_em_vez_de_reportar_sucesso(
        self, limpador, tmp_path
    ):
        """
        Era o defeito: o `except` logava e o método caía num `return True` no
        fim — dizia que a limpeza deu certo, e o Detraf seguia para a validação
        como se estivesse íntegro.
        """
        with pytest.raises(RuntimeError, match="Falha ao separar"):
            limpador.executar(
                caminho_arquivo=tmp_path / "nao_existe.csv",
                tipo_fluxo="BK",
                sufixo="_BK",
            )

    def test_a_mensagem_diz_qual_arquivo_e_qual_fluxo(self, limpador, tmp_path):
        """Quem lê o log precisa saber onde olhar, sem reproduzir a execução."""
        with pytest.raises(RuntimeError) as erro:
            limpador.executar(
                caminho_arquivo=tmp_path / "detraf_claro.csv",
                tipo_fluxo="LL",
                sufixo="_ERRO",
            )

        mensagem = str(erro.value)
        assert "detraf_claro.csv" in mensagem and "LL" in mensagem

    def test_arquivo_sem_o_fluxo_devolve_false_sem_levantar(self, limpador, tmp_path):
        """
        "Não atende ao fluxo" é resposta legítima, não falha — e é o que
        distingue esse caso do arquivo que não pôde ser lido.
        """
        caminho = tmp_path / "detraf.csv"
        _escrever_detraf(caminho, [LINHA_VALIDA])

        resultado = limpador.executar(
            caminho_arquivo=caminho, tipo_fluxo="BK", sufixo="_BK",
            gerar_arquivos=False,
        )

        assert resultado is False


class TestCodigoDeErro:
    """
    O de-para oficial de códigos de erro nunca foi informado (a V2 não traz
    tabela de códigos). Até 2026-08-04 havia **um valor fixo para toda e
    qualquer falha**, o que tornava a coluna inútil para diagnóstico.
    """

    def test_ha_codigo_distinto_para_leitura_e_para_validacao(self):
        assert COD_ERRO_LEITURA != COD_ERRO_VALIDACAO

    def test_reprovacao_de_validacao_usa_o_codigo_de_validacao(self, tmp_path):
        assert obter_codigo_erro(tmp_path / "qualquer.csv") == COD_ERRO_VALIDACAO


class TestResultadoValidacao:
    @pytest.fixture()
    def transformador(self) -> TransformadorRelatorioRPA:
        return TransformadorRelatorioRPA()

    def test_arquivo_ilegivel_levanta_excecao_propria(self, transformador, tmp_path):
        with pytest.raises(LeituraDetrafFalhou):
            transformador._extrair_dados_internos(tmp_path / "inexistente.csv")

    def test_arquivo_lido_e_sem_trafego_devolve_zero(self, transformador, tmp_path):
        """
        Zero é resultado **legítimo**: a operadora não apresentou tráfego. É por
        isso que a falha de leitura não pode devolver zero também — os dois
        ficariam indistinguíveis no banco.
        """
        caminho = tmp_path / "so_totais.csv"
        # Rel = "1" marca linha de total, que o filtro remove; sobra nada.
        _escrever_detraf(caminho, [linha(rel="1")])

        dados = transformador._extrair_dados_internos(caminho)

        assert dados["minuto_desp"] == 0.0
        assert dados["valor_bruto_desp"] == 0.0

    def test_volumetria_e_somada_das_linhas_de_trafego(self, transformador, tmp_path):
        caminho = tmp_path / "duas_linhas.csv"
        _escrever_detraf(
            caminho,
            [linha(minutos="100,0", r_bruto="10,00"),
             linha(minutos="250,5", r_bruto="25,50")],
        )

        dados = transformador._extrair_dados_internos(caminho)

        assert dados["minuto_desp"] == pytest.approx(350.5)
        assert dados["valor_bruto_desp"] == pytest.approx(35.50)

    def test_a_empresa_vem_do_anexo5_pela_eot_credora(self, transformador, tmp_path):
        caminho = tmp_path / "claro.csv"
        _escrever_detraf(caminho, [LINHA_VALIDA])

        assert transformador._extrair_dados_internos(caminho)["empresa"] == "CLARO"


class TestLoteParaOBanco:
    @pytest.fixture()
    def transformador(self) -> TransformadorRelatorioRPA:
        return TransformadorRelatorioRPA()

    def test_falha_de_leitura_vira_registro_nao_validado(self, transformador, tmp_path):
        """
        Era o defeito: gravava com minutos e valor **zerados** e marcava o
        arquivo como processado. Agora o registro existe (para auditoria), mas
        diz o que aconteceu.
        """
        lote = transformador.preparar_lote(
            [tmp_path / "inexistente.csv"], "DETRAF_SUCESSO"
        )

        linha_gravada = lote.iloc[0]
        assert linha_gravada["status"] == "Não validado"
        assert linha_gravada["codigo_erro"] == COD_ERRO_LEITURA

    def test_volumetria_nula_nao_zerada_quando_a_leitura_falha(
        self, transformador, tmp_path
    ):
        lote = transformador.preparar_lote(
            [tmp_path / "inexistente.csv"], "DETRAF_SUCESSO"
        )

        assert lote.iloc[0]["minuto_desp"] is None
        assert lote.iloc[0]["valor_bruto_desp"] is None

    def test_arquivo_valido_entra_como_validado(self, transformador, tmp_path):
        caminho = tmp_path / "ok.csv"
        _escrever_detraf(caminho, [LINHA_VALIDA])

        lote = transformador.preparar_lote([caminho], "DETRAF_SUCESSO")

        assert lote.iloc[0]["status"] == "Validado"
        assert lote.iloc[0]["codigo_erro"] is None
        assert lote.iloc[0]["minuto_desp"] == pytest.approx(500.0)

    def test_lote_de_erro_recebe_codigo(self, transformador, tmp_path):
        caminho = tmp_path / "reprovado.csv"
        _escrever_detraf(caminho, [LINHA_VALIDA])

        lote = transformador.preparar_lote([caminho], "EXPECTATIVA_ERRO")

        assert lote.iloc[0]["tipo_registro"] == "ERRO"
        assert lote.iloc[0]["codigo_erro"] == COD_ERRO_VALIDACAO

    def test_tipo_de_lote_desconhecido_e_ignorado_com_aviso(
        self, transformador, tmp_path, caplog
    ):
        with caplog.at_level("WARNING"):
            lote = transformador.preparar_lote([tmp_path / "x.csv"], "TIPO_INVENTADO")

        assert lote.empty
        assert "desconhecido" in caplog.text

    def test_um_arquivo_ruim_nao_impede_os_demais(self, transformador, tmp_path):
        """O lote é do mês inteiro; um arquivo corrompido não derruba os outros."""
        bom = tmp_path / "bom.csv"
        _escrever_detraf(bom, [LINHA_VALIDA])

        lote = transformador.preparar_lote(
            [tmp_path / "inexistente.csv", bom], "DETRAF_SUCESSO"
        )

        assert len(lote) == 2
        assert set(lote["status"]) == {"Não validado", "Validado"}


class TestEnumDoTipoRegistro:
    """
    ✅ **Pendência N4 fechada em 2026-08-05.** Um print do MySQL Workbench
    embutido no `.docx` mostra o DDL real::

        tipo_registro   enum('DETRAF','EXPECTATIVA','ERRO')   NOT NULL

    Enum **fechado**. Gravar qualquer outro valor falha o INSERT com
    `STRICT_TRANS_TABLES`, ou — pior — grava string vazia em silêncio sem ele.

    **O código já estava certo, e vale registrar por quê.** Os quatro valores
    do projeto de origem (`DETRAF_SUCESSO`, `DETRAF_ERRO`,
    `EXPECTATIVA_SUCESSO`, `EXPECTATIVA_ERRO`) nunca chegaram ao banco: eles são
    **parâmetro interno** de `preparar_lote`, e a unificação já os mapeia para os
    três do enum. Uma leitura apressada da N4 concluiria que há quatro valores a
    corrigir — não há.

    O mapeamento também bate com a planilha de referência, que descreve `ERRO`
    como *"arquivo de expectativa que não passou pela validação"*: por isso
    `DETRAF_ERRO` vira `DETRAF`, e não `ERRO`.

    Esta classe existe para que a correspondência não se perca — se alguém
    acrescentar um quinto tipo de lote sem mapear, o teste acusa.
    """

    #: Os únicos valores que o banco aceita.
    ENUM = {"DETRAF", "EXPECTATIVA", "ERRO"}

    @pytest.fixture()
    def transformador(self) -> TransformadorRelatorioRPA:
        return TransformadorRelatorioRPA()

    @pytest.mark.parametrize(
        "tipo_lote, esperado",
        [
            ("DETRAF_SUCESSO", "DETRAF"),
            ("DETRAF_ERRO", "DETRAF"),
            ("EXPECTATIVA_SUCESSO", "EXPECTATIVA"),
            ("EXPECTATIVA_ERRO", "ERRO"),
        ],
    )
    def test_cada_tipo_de_lote_vira_um_valor_do_enum(
        self, transformador, tmp_path, tipo_lote, esperado
    ):
        caminho = tmp_path / "arquivo.csv"
        _escrever_detraf(caminho, [LINHA_VALIDA])

        lote = transformador.preparar_lote([caminho], tipo_lote)

        assert lote.iloc[0]["tipo_registro"] == esperado
        assert lote.iloc[0]["tipo_registro"] in self.ENUM

    def test_detraf_reprovado_nao_vira_erro(self, transformador, tmp_path):
        """
        `ERRO` é valor **só de expectativa**, conforme a planilha de referência.
        Um Detraf reprovado continua sendo `DETRAF`; o que muda é o `status`.

        É o detalhe que faz os dois recortes parecerem "quatro contra três"
        quando na verdade não se sobrepõem linha a linha.
        """
        caminho = tmp_path / "reprovado.csv"
        _escrever_detraf(caminho, [LINHA_VALIDA])

        lote = transformador.preparar_lote([caminho], "DETRAF_ERRO")

        assert lote.iloc[0]["tipo_registro"] == "DETRAF"
        assert lote.iloc[0]["status"] == "Não validado"
