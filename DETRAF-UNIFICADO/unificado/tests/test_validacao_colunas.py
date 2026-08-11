"""As 15 colunas do Detraf, uma a uma (HU-04).

A V2 descreve cada coluna em um parágrafo próprio, na seção *Regras de negócio*.
Este arquivo transcreve cada regra num teste, com a citação ao lado — é o módulo
que a documentação mais detalha e o que decide se o arquivo da operadora é aceito
ou devolvido com `_ERRO`.

Cada teste altera **uma** posição da linha válida. Se dois campos mudassem
juntos, a reprovação não diria qual regra quebrou.
"""

import pandas as pd
import pytest

from comum.dominio.validacao_colunas import ValidadorColunas


@pytest.fixture()
def validador() -> ValidadorColunas:
    instancia = ValidadorColunas()
    instancia._preparar_datas_referencia()
    return instancia


class TestColuna3Referencia:
    """*"3ª coluna 'Referencia' deve aceitar apenas o mês corrente -1"*."""

    def test_mes_corrente_menos_1_passa(self, validador, df_valido):
        assert validador._validar_col_3_referencia(df_valido) is True

    @pytest.mark.parametrize("valor", ["202506", "202508", "2025-07", "", "abc"])
    def test_qualquer_outro_reprova(self, validador, df_com, valor):
        assert validador._validar_col_3_referencia(df_com(referencia=valor)) is False

    def test_espaco_em_volta_nao_reprova(self, validador, df_com):
        """A operadora manda com espaço; isso é formatação, não erro de conteúdo."""
        assert validador._validar_col_3_referencia(df_com(referencia=" 202507 ")) is True


class TestColuna4Trafego:
    """*"4ª coluna 'Tráfego' deve aceitar os meses: mês corrente -1, -2, -3"*."""

    @pytest.mark.parametrize("valor", ["202507", "202506", "202505"])
    def test_a_janela_de_tres_meses_passa(self, validador, df_com, valor):
        """
        `ANO_MES_REFERENCIA` já é o "mês corrente -1" da V2 (202507 aqui), então
        a janela vai dele até dois meses atrás.
        """
        assert validador._validar_col_4_trafego(df_com(trafego=valor)) is True

    @pytest.mark.parametrize("valor", ["202504", "202508", "202512", ""])
    def test_fora_da_janela_reprova(self, validador, df_com, valor):
        """202508 é o mês corrente: tráfego futuro não existe."""
        assert validador._validar_col_4_trafego(df_com(trafego=valor)) is False


class TestColuna8GH:
    """*"8ª coluna 'GH' deve estar preenchida com as opções (S,R,N,D)"*."""

    @pytest.mark.parametrize("valor", ["S", "R", "N", "D"])
    def test_as_quatro_opcoes_passam(self, validador, df_com, valor):
        assert validador._validar_col_8_gh(df_com(gh=valor)) is True

    @pytest.mark.parametrize("valor", ["X", "s", "", "SR"])
    def test_qualquer_outra_reprova(self, validador, df_com, valor):
        """Inclusive minúscula: a V2 lista as opções em maiúsculo."""
        assert validador._validar_col_8_gh(df_com(gh=valor)) is False


class TestColuna9Chamadas:
    """*"9ª coluna 'Chamadas' deve conter apenas números inteiros"*."""

    def test_inteiro_passa(self, validador, df_com):
        assert validador._validar_col_9_chamadas(df_com(chamadas="1500")) is True

    def test_decimal_reprova(self, validador, df_com):
        assert validador._validar_col_9_chamadas(df_com(chamadas="1500.5")) is False

    @pytest.mark.parametrize("valor", ["", "abc", "N/A"])
    def test_nao_numerico_reprova(self, validador, df_com, valor):
        assert validador._validar_col_9_chamadas(df_com(chamadas=valor)) is False

    def test_zero_e_um_inteiro_valido(self, validador, df_com):
        """Zero chamada é um resultado possível — não é o mesmo que campo vazio."""
        assert validador._validar_col_9_chamadas(df_com(chamadas="0")) is True


class TestColuna10Minutos:
    """*"10ª coluna 'Minutos' deve conter apenas números com até uma casa decimal"*."""

    @pytest.mark.parametrize("valor", ["500,0", "500", "0,5", "1234567,8"])
    def test_ate_uma_casa_passa(self, validador, df_com, valor):
        assert validador._validar_col_10_minutos(df_com(minutos=valor)) is True

    @pytest.mark.parametrize("valor", ["500,25", "0,123"])
    def test_mais_de_uma_casa_reprova(self, validador, df_com, valor):
        assert validador._validar_col_10_minutos(df_com(minutos=valor)) is False

    def test_a_virgula_decimal_brasileira_e_aceita(self, validador, df_com):
        """Os arquivos vêm com vírgula; trocar por ponto é do parser, não da regra."""
        assert validador._validar_col_10_minutos(df_com(minutos="1500,7")) is True

    def test_vazio_reprova(self, validador, df_com):
        assert validador._validar_col_10_minutos(df_com(minutos="")) is False


class TestColuna11Tarifa:
    """
    *"11ª coluna 'Tarifa' deve conter apenas números com no máximo 5 casas
    decimais. [...] **Não existe tarifa zero**"*.
    """

    @pytest.mark.parametrize("valor", ["0,01500", "0,03", "1,23456"])
    def test_ate_cinco_casas_passa(self, validador, df_com, valor):
        assert validador._validar_col_11_tarifa(df_com(tarifa=valor)) is True

    def test_seis_casas_reprova(self, validador, df_com):
        assert validador._validar_col_11_tarifa(df_com(tarifa="0,123456")) is False

    @pytest.mark.parametrize("valor", ["0", "0,00000", "0,0"])
    def test_tarifa_zero_reprova(self, validador, df_com, valor):
        """A V2 é literal: "Não existe tarifa zero"."""
        assert validador._validar_col_11_tarifa(df_com(tarifa=valor)) is False

    @pytest.mark.parametrize("valor", ["", "grátis"])
    def test_nao_numerico_reprova(self, validador, df_com, valor):
        assert validador._validar_col_11_tarifa(df_com(tarifa=valor)) is False


class TestColunasFinanceiras12a15:
    """
    Colunas 12 a 15 (`R$_Liq`, `PIS_Cofins`, `ICMS`, `R$_Bruto`): *"é um campo
    valor com até duas casas decimais"*.
    """

    def test_duas_casas_passa(self, validador, df_valido):
        assert validador._validar_cols_financeiras_12_15(df_valido) is True

    @pytest.mark.parametrize(
        "campo", ["r_liq", "pis_cofins", "icms", "r_bruto"]
    )
    def test_tres_casas_reprova_em_qualquer_uma_delas(self, validador, df_com, campo):
        assert (
            validador._validar_cols_financeiras_12_15(df_com(**{campo: "1,234"}))
            is False
        )

    def test_zero_e_valor_valido(self, validador, df_com):
        """Diferente da tarifa: um valor financeiro zerado é resultado possível."""
        assert (
            validador._validar_cols_financeiras_12_15(df_com(r_liq="0,00")) is True
        )


class TestColunas1e2EOT:
    """
    *"1ª coluna 'Credora' deve estar preenchida com uma EOT relacionada à
    operadora"*, *"2ª coluna 'Devedora' [...] uma das EOTs da Vivo"*. A base de
    busca é o Anexo 5 nos dois casos.
    """

    def test_eots_do_anexo5_passam(self, validador, df_valido):
        assert validador._validar_col_1_2_eot(df_valido) is True

    def test_eot_fora_do_anexo5_reprova(self, validador, df_com):
        assert validador._validar_col_1_2_eot(df_com(credora="999")) is False

    def test_devedora_precisa_ser_da_vivo(self, validador, df_com):
        """
        A 2ª coluna é a Vivo — é ela que deve. Uma EOT de outra operadora ali
        significa que o arquivo não é uma cobrança contra a Vivo.
        """
        assert (
            validador._validar_col_2_eot_vivo(df_com(devedora="021"), ["VIVO"]) is False
        )

    def test_devedora_da_vivo_passa(self, validador, df_valido):
        assert validador._validar_col_2_eot_vivo(df_valido, ["VIVO"]) is True


class TestTarifaContraATabela:
    """
    *"A tarifa deve ser uma tarifa correspondente ao descritor da coluna 'DESC'"*
    — a comparação é contra `tbl_detraf_tarifas`, filtrando por GH, região,
    regra do descritor e vigência.
    """

    def test_tarifa_que_bate_com_a_tabela_passa(self, validador, df_valido):
        assert validador._validar_tarifas_remuneradas(df_valido) is True

    def test_tarifa_diferente_da_tabela_reprova(self, validador, df_com):
        """Valor bem formatado, mas que não é a tarifa regulada daquele tráfego."""
        assert validador._validar_tarifas_remuneradas(df_com(tarifa="0,09900")) is False

    def test_descritor_nao_remunerado_nao_e_validado(self, validador, df_com):
        """
        Decisão Q9: tarifa não regulada é **só formato**. Um descritor que não
        mapeia para remuneração sai do filtro antes da comparação de valor.
        """
        assert validador._validar_tarifas_remuneradas(df_com(desc="ZZ")) is True

    def test_tarifa_com_virgula_no_banco_quebra(self, validador, df_valido, repo_cache):
        """
        A coluna `tarifa` é **numérica**, e o código depende disso.

        ✅ **Pendência N10 fechada em 2026-08-05.** Um print do MySQL Workbench
        embutido no `.docx` normativo mostra
        `webfat.tbl_detraf_tarifas.tarifa` tipada como **`float`**, com valores
        como `0.00602` — ponto decimal, valor numérico, não string.

        Antes disso este teste documentava uma **inconsistência**: metade do
        fluxo fazia `.astype(float)` (exige ponto) e a outra `replace(",", ".")`
        (tolera vírgula), e o teste fixava o comportamento sem escolher lado,
        porque o formato real não era conhecido.

        Agora há lado. O `replace` redundante do lado da tabela saiu, e este
        teste passa a ter outro sentido: ele **garante que a leitura não faz
        coerção de string**. Se alguém reintroduzir uma tolerância a vírgula
        "por segurança", ele falha — e é o que se quer, porque essa tolerância
        esconderia uma tabela com o tipo errado em vez de acusá-la.

        O que continua valendo: a tarifa **do arquivo** vem com vírgula, e o
        `replace` daquele lado é necessário. Ver
        `test_tarifa_do_arquivo_com_virgula_e_aceita`.
        """
        import sqlite3

        import os

        from comum.dados.repositorio_tabelas import bd_tabelas

        # Pelo ambiente, e nao pelo conftest: este teste ja mudou de suite uma
        # vez (subiu do RPA 2 com o `ValidadorColunas`), e `CAMINHO_SQLITE` e a
        # unica referencia que vale igual nas quatro.
        def _gravar_tarifa(valor: str) -> None:
            conexao = sqlite3.connect(os.environ["CAMINHO_SQLITE"])
            try:
                conexao.execute("UPDATE tbl_detraf_tarifas SET tarifa = ?", (valor,))
                conexao.commit()
            finally:
                conexao.close()
            # Recarrega o cache vivo: `bd_tabelas` é instância de módulo e não
            # veria a alteração no disco de outra forma.
            bd_tabelas.cache.recarregar_cache_local(nome_tabela="tbl_detraf_tarifas")

        _gravar_tarifa("0,01500")
        try:
            with pytest.raises(ValueError, match="could not convert"):
                validador._validar_tarifas_remuneradas(df_valido)
        finally:
            # Restaura o seed: o SQLite é compartilhado pela suíte inteira.
            _gravar_tarifa("0.01500")

    def test_tarifa_do_arquivo_com_virgula_e_aceita(self, validador, df_com):
        """
        O outro lado da N10, e o motivo de o `replace` não sair inteiro.

        O arquivo da operadora é um CSV em formato brasileiro: a tarifa vem
        como `"0,01500"`. Remover o `replace` desse lado — como uma leitura
        apressada da N10 sugeriria — faria **todo arquivo real ser reprovado**.
        """
        assert validador._validar_tarifas_remuneradas(df_com(tarifa="0,01500")) is True


class TestValidacaoCompleta:
    def test_linha_valida_passa_em_tudo(self, validador, df_valido):
        assert validador.validar_tudo(df_valido, tipo_arquivo="DETRAF") is True

    def test_uma_regra_quebrada_reprova_o_arquivo(self, validador, df_com):
        assert (
            validador.validar_tudo(df_com(gh="X"), tipo_arquivo="DETRAF") is False
        )

    def test_todas_as_falhas_aparecem_no_log(self, validador, df_com, caplog):
        """
        A V2 manda devolver o arquivo para a operadora corrigir. Reportar só a
        primeira falha faria a operadora reenviar N vezes, uma por regra.
        """
        df = df_com(gh="X", chamadas="abc", tarifa="0")

        with caplog.at_level("INFO"):
            validador.validar_tudo(df, tipo_arquivo="DETRAF")

        assert "Coluna 8" in caplog.text
        assert "Coluna 9" in caplog.text
        assert "Coluna 11" in caplog.text

    def test_uma_linha_ruim_reprova_o_conjunto(self, validador):
        """
        A validação é do arquivo, não da linha: basta uma linha fora da regra
        para o arquivo virar `_ERRO`.
        """
        from tests_apoio import LINHA_VALIDA, linha

        df = pd.DataFrame([LINHA_VALIDA, linha(gh="X")])

        assert validador.validar_tudo(df, tipo_arquivo="DETRAF") is False
