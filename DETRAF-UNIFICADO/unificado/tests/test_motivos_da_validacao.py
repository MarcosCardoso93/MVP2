"""Os motivos da reprovação, e o terceiro estado (2026-08-06).

Até aqui `validar_tudo` devolvia `bool` e jogava fora o dicionário que sabia
**qual** regra tinha falhado. Isso bastava enquanto o destino do veredito era
renomear o arquivo para `_ERRO`. Passou a não bastar quando o RPA 1 virou o
portão e passou a responder à operadora: "seu arquivo está inválido" sem dizer o
quê é um e-mail que não permite à operadora corrigir nada.

O que se protege aqui:

1. que o RPA 2 **não mudou** — `validar_tudo` continua valendo exatamente o que
   valia, regra por regra;
2. que cada regra produz um motivo legível e específico;
3. que "não consegui validar" **nunca** se disfarça de "reprovado".
"""

import pandas as pd
import pytest

from comum.dominio import validacao_colunas as vc
from comum.dominio.validacao_colunas import (
    REGRAS,
    ValidacaoIndisponivel,
    ValidadorColunas,
)

#: Um desvio por regra, para varrer as dez de uma vez. `v_col1_2` e
#: `v_col2_vivo` usam EOTs que não estão no seed; as demais são puro pandas.
DESVIO_POR_REGRA = {
    "v_col1_2": {"credora": "999"},
    "v_col2_vivo": {"devedora": "021"},   # existe no Anexo 5, mas não é Vivo
    "v_col3": {"referencia": "201001"},
    "v_col4": {"trafego": "201001"},
    "v_col8": {"gh": "X"},
    "v_col9": {"chamadas": "10,5"},
    "v_col10": {"minutos": "500,55"},
    "v_col11": {"tarifa": "0"},
    "v_col12_15": {"r_liq": "7,555"},
    "v_tarifas_remuneradas": {"tarifa": "0,99999"},
}


@pytest.fixture()
def validador() -> ValidadorColunas:
    return ValidadorColunas(referencia="202507")


class TestOResultadoDetalhadoNaoMudaOVeredito:
    """
    `validar_tudo` virou adaptador de `validar_tudo_detalhado`. Se os dois
    discordassem em qualquer caso, o RPA 2 teria mudado de comportamento numa
    mudança que se propôs a não tocá-lo.
    """

    def test_linha_valida_concorda(self, validador, df_valido, repo_cache):
        detalhado = validador.validar_tudo_detalhado(df_valido, "detraf")

        assert validador.validar_tudo(df_valido, "detraf") is detalhado.conforme
        assert detalhado.conforme is True
        assert detalhado.motivos() == []

    @pytest.mark.parametrize("regra", sorted(DESVIO_POR_REGRA))
    def test_cada_desvio_concorda(self, validador, df_com, repo_cache, regra):
        df = df_com(**DESVIO_POR_REGRA[regra])

        assert validador.validar_tudo(df, "detraf") is (
            validador.validar_tudo_detalhado(df, "detraf").conforme
        )


class TestCadaRegraDizOQueQuebrou:
    @pytest.mark.parametrize("regra", sorted(DESVIO_POR_REGRA))
    def test_a_regra_desviada_aparece_nas_falhas(
        self, validador, df_com, repo_cache, regra
    ):
        resultado = validador.validar_tudo_detalhado(
            df_com(**DESVIO_POR_REGRA[regra]), "detraf"
        )

        assert not resultado.conforme
        assert regra in [falha.regra for falha in resultado.falhas], (
            f"o desvio de {regra} não foi atribuído a ela — a tabela REGRAS e o "
            "dicionário de validações saíram de sincronia"
        )

    def test_o_motivo_nomeia_a_coluna_e_e_legivel(self, validador, df_com, repo_cache):
        resultado = validador.validar_tudo_detalhado(df_com(gh="X"), "detraf")

        motivo = "\n".join(resultado.motivos())
        assert "Coluna 8" in motivo
        assert "S, R, N ou D" in motivo

    def test_nenhum_motivo_fica_com_placeholder_por_substituir(
        self, validador, df_com, repo_cache
    ):
        """Um `{referencia}` cru no corpo do e-mail é pior que não dizer nada."""
        for regra in DESVIO_POR_REGRA:
            resultado = validador.validar_tudo_detalhado(
                df_com(**DESVIO_POR_REGRA[regra]), "detraf"
            )
            for texto in resultado.motivos():
                assert "{" not in texto, texto

    def test_toda_regra_da_tabela_tem_texto(self):
        for regra in REGRAS:
            assert regra.coluna and regra.motivo


class TestOMotivoDaColuna3CitaOMesCerto:
    """
    🔴 Regressão de um defeito real.

    A máscara sempre comparou contra a referência; a mensagem dizia
    `ref_mes_menos_1` — **o mês anterior ao exigido**. Enquanto era log, era
    ruído. Como corpo de e-mail, manda a operadora reenviar o mês errado.
    """

    def test_o_motivo_cita_a_referencia_exigida(self, validador, df_com, repo_cache):
        resultado = validador.validar_tudo_detalhado(
            df_com(referencia="201001"), "detraf"
        )

        motivo = "\n".join(resultado.motivos())
        assert "202507" in motivo
        assert "202506" not in motivo, "voltou a citar o mês anterior ao exigido"

    def test_o_log_tambem_cita_a_referencia_exigida(self, validador, df_com, caplog):
        validador._preparar_datas_referencia()
        validador._validar_col_3_referencia(df_com(referencia="201001"))

        assert "202507" in caplog.text
        assert "202506" not in caplog.text


class TestAReferenciaVemPorParametro:
    """
    Antes, a classe lia `ANO_MES_REFERENCIA` — resolvido **no import** —
    enquanto o resto do robô resolve a competência **em tempo de chamada**. Em
    produção coincidem; num teste que troca a competência, não. O robô validaria
    contra um mês e gravaria no caminho de outro.
    """

    def test_a_referencia_informada_e_a_exigida(self, df_com, repo_cache):
        """
        Sobre a coluna 3 isolada, e não sobre `validar_tudo`: a linha padrão tem
        tarifa vigente em 2025, então em 202401 ela reprovaria também na regra de
        tarifa — e o teste passaria pelo motivo errado.
        """
        validador = ValidadorColunas(referencia="202401")
        validador._preparar_datas_referencia()

        assert validador._validar_col_3_referencia(df_com(referencia="202401"))
        assert not validador._validar_col_3_referencia(df_com(referencia="202507"))

    def test_sem_argumento_resolve_pela_competencia(self):
        from comum.dominio.competencia import obter_competencia

        assert ValidadorColunas().referencia == obter_competencia().competencia

    def test_referencia_malformada_acusa_o_valor(self):
        with pytest.raises(ValueError, match="banana"):
            ValidadorColunas(referencia="banana")._preparar_datas_referencia()


class TestValidacaoIndisponivelNaoEReprovacao:
    """
    O risco que esta exceção existe para evitar: uma queda do WebFat durante a
    captura poria o lote inteiro em quarentena e responderia a **todas** as
    operadoras dizendo que os arquivos delas estão errados.
    """

    def _quebrar_o_banco(self, monkeypatch):
        def _estourar(*args, **kwargs):
            raise RuntimeError("Can't connect to MySQL server")

        monkeypatch.setattr(vc.bd_tabelas, "validar_coluna_eot_df", _estourar)

    def test_falha_de_banco_vira_indisponivel(self, validador, df_valido, monkeypatch):
        self._quebrar_o_banco(monkeypatch)

        with pytest.raises(ValidacaoIndisponivel):
            validador.validar_tudo_detalhado(df_valido, "detraf")

    def test_e_nao_um_conforme_False(self, validador, df_valido, monkeypatch):
        """O modo de falha que se quer impossível: reprovar por culpa nossa."""
        self._quebrar_o_banco(monkeypatch)

        with pytest.raises(ValidacaoIndisponivel):
            validador.validar_tudo(df_valido, "detraf")

    def test_a_causa_original_e_preservada(self, validador, df_valido, monkeypatch):
        """Sem o `from`, quem investiga perde a mensagem do driver."""
        self._quebrar_o_banco(monkeypatch)

        with pytest.raises(ValidacaoIndisponivel) as erro:
            validador.validar_tudo_detalhado(df_valido, "detraf")

        assert "MySQL" in str(erro.value.__cause__)

    def test_dataframe_estreito_nao_vira_indisponivel(self, validador):
        """
        🔴 Regressão. Um DataFrame com menos colunas que o layout estourava
        dentro do `try` do banco ("index out-of-bounds") e virava
        `ValidacaoIndisponivel` — ou seja, um arquivo irremediavelmente quebrado
        passaria a ser tratado como "o banco caiu": preso na entrada, retentado a
        cada execução, para sempre, sem nunca notificar ninguém.

        Chegar aqui com df estreito é erro de programação — `validar_layout`
        roda antes — e o erro precisa dizer isso.
        """
        with pytest.raises(ValueError, match="validar_layout"):
            validador.validar_tudo_detalhado(pd.DataFrame([["a", "b"]]), "detraf")

    def test_o_estreito_nao_e_confundido_com_indisponibilidade(self, validador):
        with pytest.raises(Exception) as erro:
            validador.validar_tudo_detalhado(pd.DataFrame([["a", "b"]]), "detraf")

        assert not isinstance(erro.value, ValidacaoIndisponivel)
