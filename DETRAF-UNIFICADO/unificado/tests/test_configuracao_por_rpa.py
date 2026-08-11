"""Modo e variáveis por robô, e a tradução da linha de comando (2026-08-06).

Duas mecânicas que existem para a **homologação manual**, e que quebram de forma
silenciosa se alguém mexer sem olhar:

1. **`ENV_RPA3` vence `ENV`.** Os quatro robôs são agendados separadamente e
   podem estar em fases diferentes. Alternar reescrevendo o `.env` entre
   execuções é como se esquece um kill-switch ligado.
2. **Os argumentos viram ambiente antes do import da configuração.** A
   configuração lê o ambiente uma vez, no import; depois disso, escrever em
   `os.environ` não tem efeito nenhum — e o argumento seria aceito e ignorado,
   que é o pior dos dois mundos.

Cada teste recarrega o módulo de configuração, porque é justamente o momento do
import que está sob teste.
"""

import argparse
import importlib
import sys

import pytest

from comum.config import linha_de_comando as cli


def _recarregar_configuracao():
    """Reimporta a configuração para que ela releia o ambiente."""
    import comum.config.configuration as configuration

    return importlib.reload(configuration)


@pytest.fixture(autouse=True)
def _ambiente_limpo(monkeypatch):
    """
    Tira do ambiente tudo o que estes testes manipulam.

    A máquina de quem roda a suíte pode ter um `.env` carregado, e um `ENV=prod`
    herdado transformaria estes testes em falso-positivo.
    """
    for variavel in (
        "ENV", "ENV_RPA1", "ENV_RPA2", "ENV_RPA3",
        "NOME_RPA", "LOG_LEVEL", "LOG_LEVEL_RPA3",
        "COMPETENCIA", "DEBUG_ANO_MES_ATUAL",
        "PERMITIR_ENVIO_EMAIL", "PERMITIR_UPLOAD_AGI",
        "PERMITIR_ACESSO_AGI", "PERMITIR_ACESSO_AGI_RPA3",
        "NOTIFICAR_OPERADORA_ENVIAR", "DIRETORIO_ENTRADA",
    ):
        monkeypatch.delenv(variavel, raising=False)
    yield
    # Devolve o módulo ao estado que o resto da suíte espera.
    _recarregar_configuracao()


class TestVariavelPorRobo:
    def test_o_sufixo_do_robo_vence_o_valor_geral(self, monkeypatch):
        monkeypatch.setenv("NOME_RPA", "rpa3_contestacao_agi_ec")
        monkeypatch.setenv("ENV", "prod")
        monkeypatch.setenv("ENV_RPA3", "dev")

        configuration = _recarregar_configuracao()

        assert configuration.ENV == "dev"
        assert configuration.ORIGEM_DAS_VARIAVEIS["ENV"] == "ENV_RPA3"

    def test_sem_o_sufixo_vale_o_valor_geral(self, monkeypatch):
        monkeypatch.setenv("NOME_RPA", "rpa1_captura")
        monkeypatch.setenv("ENV", "prod")
        monkeypatch.setenv("ENV_RPA3", "dev")

        configuration = _recarregar_configuracao()

        assert configuration.ENV == "prod", "o sufixo do RPA 3 não vale para o RPA 1"
        assert configuration.ORIGEM_DAS_VARIAVEIS["ENV"] == "ENV"

    def test_sufixo_vazio_nao_vence(self, monkeypatch):
        """`ENV_RPA3=` no `.env` é linha esquecida, não intenção de trocar."""
        monkeypatch.setenv("NOME_RPA", "rpa3_contestacao_agi_ec")
        monkeypatch.setenv("ENV", "prod")
        monkeypatch.setenv("ENV_RPA3", "   ")

        configuration = _recarregar_configuracao()

        assert configuration.ENV == "prod"

    def test_fora_de_um_robo_nao_ha_sufixo(self, monkeypatch):
        """Teste e script solto se comportam como antes desta mudança."""
        monkeypatch.setenv("ENV", "prod")
        monkeypatch.setenv("ENV_RPA3", "dev")

        configuration = _recarregar_configuracao()

        assert configuration.SUFIXO_RPA == ""
        assert configuration.ENV == "prod"

    def test_o_sufixo_vale_tambem_para_kill_switch(self, monkeypatch):
        """
        É o caso de uso real: ligar o acesso ao AGI só no RPA 3, durante a
        validação em produção, sem tocar nos outros robôs.
        """
        monkeypatch.setenv("NOME_RPA", "rpa3_contestacao_agi_ec")
        monkeypatch.setenv("PERMITIR_ACESSO_AGI_RPA3", "true")

        configuration = _recarregar_configuracao()

        assert configuration.PERMITIR_ACESSO_AGI is True

    def test_o_resumo_diz_o_modo_e_de_onde_ele_veio(self, monkeypatch):
        monkeypatch.setenv("NOME_RPA", "rpa3_contestacao_agi_ec")
        monkeypatch.setenv("ENV", "prod")
        monkeypatch.setenv("ENV_RPA3", "dev")

        configuration = _recarregar_configuracao()
        resumo = "\n".join(configuration.resumo_do_ambiente())

        assert "DEV" in resumo
        assert "ENV_RPA3" in resumo, "sem a origem, achar a linha do .env é caça"

    def test_o_resumo_nao_expoe_senha(self, monkeypatch):
        monkeypatch.setenv("ENV", "prod")
        monkeypatch.setenv("SENHA_BD", "senha-secreta-do-banco")

        configuration = _recarregar_configuracao()
        resumo = "\n".join(configuration.resumo_do_ambiente())

        assert "senha-secreta-do-banco" not in resumo
        assert "definida" in resumo, "mas precisa dizer que existe"

    def test_o_resumo_destaca_os_efeitos_externos(self, monkeypatch):
        """É a linha que decide se a rodada escreve para fora."""
        monkeypatch.setenv("PERMITIR_UPLOAD_AGI", "true")

        configuration = _recarregar_configuracao()
        resumo = "\n".join(configuration.resumo_do_ambiente())

        assert "EFEITOS EXTERNOS" in resumo
        assert "upload AGI: LIGADO" in resumo


class TestLinhaDeComando:
    def _parsear(self, robo="RPA 3", argv=(), **kwargs):
        parser = cli.construir_parser(robo=robo, descricao="teste", **kwargs)
        return parser.parse_args(list(argv))

    def test_sem_argumento_nada_e_recortado(self):
        recorte = cli.aplicar(self._parsear(), "rpa3_contestacao_agi_ec")

        assert recorte.houve_recorte is False
        assert "execução completa" in recorte.descrever()[0]

    def test_referencia_vira_a_competencia_do_mes_seguinte(self, monkeypatch):
        """
        O robô processa o mês **anterior** à competência. Quem digita
        `--referencia 202507` quer processar julho, então a competência é agosto
        — e errar essa conta faria o robô processar junho em silêncio.
        """
        args = self._parsear(argv=["--referencia", "202507"], aceita_operadoras=True)
        cli.aplicar(args, "rpa3_contestacao_agi_ec")

        configuration = _recarregar_configuracao()

        assert configuration.ANO_MES_REFERENCIA == "202507"

    def test_referencia_vence_o_env_antigo(self, monkeypatch):
        """
        `DEBUG_ANO_MES_ATUAL` é sinônimo com precedência. Se ficasse para trás,
        um `.env` antigo venceria o argumento — o robô rodaria outro mês e
        diria que rodou o pedido.
        """
        monkeypatch.setenv("DEBUG_ANO_MES_ATUAL", "202601")

        args = self._parsear(argv=["--referencia", "202507"])
        cli.aplicar(args, "rpa3_contestacao_agi_ec")

        configuration = _recarregar_configuracao()

        assert configuration.ANO_MES_REFERENCIA == "202507"

    def test_referencia_malformada_e_recusada(self):
        with pytest.raises(SystemExit):
            self._parsear(argv=["--referencia", "julho"])

    def test_dry_run_desliga_todos_os_efeitos_externos(self, monkeypatch):
        monkeypatch.setenv("PERMITIR_ENVIO_EMAIL", "true")
        monkeypatch.setenv("PERMITIR_UPLOAD_AGI", "true")
        monkeypatch.setenv("PERMITIR_ACESSO_AGI", "true")
        monkeypatch.setenv("NOTIFICAR_OPERADORA_ENVIAR", "true")

        cli.aplicar(self._parsear(argv=["--dry-run"]), "rpa3_contestacao_agi_ec")
        configuration = _recarregar_configuracao()

        assert configuration.PERMITIR_ENVIO_EMAIL is False
        assert configuration.PERMITIR_UPLOAD_AGI is False
        assert configuration.PERMITIR_ACESSO_AGI is False
        assert configuration.NOTIFICAR_OPERADORA_ENVIAR is False

    def test_dry_run_vence_ate_o_kill_switch_por_robo(self, monkeypatch):
        """
        O sufixo por robô vence o valor geral — então escrever só o geral
        deixaria o `--dry-run` sem efeito exatamente no robô mais perigoso.
        """
        monkeypatch.setenv("PERMITIR_ACESSO_AGI_RPA3", "true")

        cli.aplicar(self._parsear(argv=["--dry-run"]), "rpa3_contestacao_agi_ec")
        configuration = _recarregar_configuracao()

        assert configuration.PERMITIR_ACESSO_AGI is False

    def test_log_nivel_vence_o_sufixo_por_robo(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL_RPA3", "ERROR")

        cli.aplicar(
            self._parsear(argv=["--log-nivel", "DEBUG"]), "rpa3_contestacao_agi_ec"
        )
        configuration = _recarregar_configuracao()

        assert configuration.LOG_LEVEL == "DEBUG"

    def test_operadoras_sao_separadas_e_limpas(self):
        args = self._parsear(
            argv=["--operadoras", "CLARO, TIM ,"], aceita_operadoras=True
        )
        recorte = cli.aplicar(args, "rpa3_contestacao_agi_ec")

        assert recorte.operadoras == ["CLARO", "TIM"]

    def test_pasta_entrada_aponta_o_diretorio_de_entrada(self, tmp_path):
        args = self._parsear(
            robo="RPA 1",
            argv=["--pasta-entrada", str(tmp_path)],
            aceita_pasta_entrada=True,
        )
        recorte = cli.aplicar(args, "rpa1_captura")
        configuration = _recarregar_configuracao()

        assert recorte.pasta_entrada == str(tmp_path)
        assert str(configuration.DIRETORIO_ENTRADA) == str(tmp_path)

    def test_o_recorte_e_descrito_para_o_log(self):
        args = self._parsear(
            argv=["--referencia", "202507", "--operadoras", "CLARO", "--dry-run"],
            aceita_operadoras=True,
        )
        descricao = cli.aplicar(args, "rpa3_contestacao_agi_ec").descrever()[0]

        assert "202507" in descricao
        assert "CLARO" in descricao
        assert "DRY-RUN" in descricao

    def test_a_etapa_so_aceita_o_que_o_robo_conhece(self):
        with pytest.raises(SystemExit):
            self._parsear(argv=["--etapa", "inexistente"], etapas=("validacao",))
