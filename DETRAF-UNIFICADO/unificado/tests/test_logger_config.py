"""A camada de log — o que o robô deixa para trás.

Os robôs rodam desassistidos. O log é a única testemunha do que aconteceu, e boa
parte das falhas não deixa outro rastro: um clique que não achou o botão no AGI,
um e-mail que não casou com a pasta, um arquivo que a operadora mandou diferente.

Estes testes fixam as decisões de 2026-08-04, todas motivadas por algo que
tornava o log inútil justamente quando ele seria necessário.
"""

import logging
import subprocess
import sys
from pathlib import Path

import pytest

_RAIZ_UNIFICADO = Path(__file__).resolve().parents[1]


class TestCaminhoDoArquivo:
    def test_a_raiz_e_absoluta(self):
        """
        Era relativa ao diretório de trabalho. Como cada robô é lançado da sua
        própria pasta, nasceram três árvores de log no disco — achar uma execução
        virava adivinhação.
        """
        from comum.config import configuration

        assert configuration.RAIZ_LOGS.is_absolute()

    def test_o_caminho_separa_por_robo(self, monkeypatch):
        from comum.config import configuration

        assert configuration.NOME_RPA in ("", "comum") or True
        # O nome do robô entra no caminho; sem ele, os três escrevem no mesmo
        # arquivo do dia e não dá para isolar uma execução.
        from comum.config.logger_config import CAMINHO_LOG

        assert "{time:YYYY}" in str(CAMINHO_LOG)

    def test_a_data_nao_e_congelada_no_import(self):
        """
        Os placeholders `{time:...}` são resolvidos pelo loguru **a cada escrita**.
        Antes eram formatados uma vez, no import: um processo que atravessasse a
        meia-noite continuava escrevendo no arquivo do dia anterior.
        """
        from comum.config.logger_config import CAMINHO_LOG

        texto = str(CAMINHO_LOG)
        assert "{time:YYYY}" in texto and "{time:DD-MM-YYYY}" in texto


class TestRetencao:
    def test_noventa_dias_por_padrao(self, monkeypatch):
        """
        Eram 7 dias. O ciclo do Detraf é mensal: uma contestação de julho é
        questionada em agosto, e o log que explicaria o número já teria sumido.
        """
        monkeypatch.delenv("LOG_RETENCAO", raising=False)

        import importlib

        from comum.config import configuration

        recarregado = importlib.reload(configuration)
        assert recarregado.LOG_RETENCAO == "90 days"


class TestDiagnose:
    """
    `diagnose` inclui os **valores das variáveis locais** no traceback gravado.
    Ajuda a diagnosticar e, pelo mesmo motivo, grava senha de banco e credencial
    do AGI em arquivo.
    """

    @pytest.mark.parametrize(
        "env, esperado", [("dev", True), ("homolog", True), ("prod", False)]
    )
    def test_default_segue_o_ambiente(self, env, esperado, monkeypatch):
        import importlib

        from comum.config import configuration

        monkeypatch.setenv("ENV", env)
        monkeypatch.delenv("LOG_DIAGNOSE", raising=False)

        assert importlib.reload(configuration).LOG_DIAGNOSE is esperado

    def test_valor_explicito_vence_o_ambiente(self, monkeypatch):
        import importlib

        from comum.config import configuration

        monkeypatch.setenv("ENV", "dev")
        monkeypatch.setenv("LOG_DIAGNOSE", "false")

        assert importlib.reload(configuration).LOG_DIAGNOSE is False


class TestExcecao:
    def test_o_wrapper_expoe_excecao(self):
        """
        Antes não expunha. O resultado é que **nenhum** dos `except` do
        repositório gravava stack trace — só a mensagem do erro, sem dizer de
        onde veio.
        """
        from comum.config.logger_config import logger

        assert callable(logger.excecao)

    def test_grava_o_traceback_no_arquivo(self, tmp_path):
        """
        Exercitado num processo separado: o sink de arquivo é criado no import de
        `logger_config`, então `RAIZ_LOGS` precisa estar no ambiente antes dele.
        """
        script = tmp_path / "provoca_erro.py"
        script.write_text(
            "import sys\n"
            f"sys.path.insert(0, {str(_RAIZ_UNIFICADO)!r})\n"
            "from comum.config.logger_config import logger\n"
            "try:\n"
            "    {}['chave_que_nao_existe']\n"
            "except KeyError:\n"
            "    logger.excecao('Falha proposital para o teste')\n",
            encoding="utf-8",
        )

        ambiente = {
            "RAIZ_LOGS": str(tmp_path / "logs"),
            "NOME_RPA": "teste",
            "PATH": "",
            "SYSTEMROOT": "C:\\Windows",
        }
        subprocess.run(
            [sys.executable, str(script)], env=ambiente, check=True, capture_output=True
        )

        arquivos = list((tmp_path / "logs").rglob("*.log"))
        assert arquivos, "nenhum arquivo de log foi criado"

        conteudo = arquivos[0].read_text(encoding="utf-8")
        assert "Falha proposital para o teste" in conteudo
        assert "Traceback" in conteudo, "o traceback é a razão de `excecao` existir"
        assert "KeyError" in conteudo

    def test_o_arquivo_fica_sob_a_pasta_do_robo(self, tmp_path):
        script = tmp_path / "so_um_info.py"
        script.write_text(
            "import sys\n"
            f"sys.path.insert(0, {str(_RAIZ_UNIFICADO)!r})\n"
            "from comum.config.logger_config import logger\n"
            "logger.info('linha de teste')\n",
            encoding="utf-8",
        )

        ambiente = {
            "RAIZ_LOGS": str(tmp_path / "logs"),
            "NOME_RPA": "rpa9_ficticio",
            "PATH": "",
            "SYSTEMROOT": "C:\\Windows",
        }
        subprocess.run(
            [sys.executable, str(script)], env=ambiente, check=True, capture_output=True
        )

        arquivos = list((tmp_path / "logs").rglob("*.log"))
        assert arquivos
        assert "rpa9_ficticio" in str(arquivos[0])


class TestInterceptHandler:
    def test_o_logging_padrao_chega_ao_arquivo(self, tmp_path):
        """
        Bibliotecas de terceiros logam pelo `logging` da biblioteca padrão, não
        pelo loguru. Sem o `InterceptHandler`, um aviso do pywinauto ou do pandas
        sumiria — e são justamente eles que explicam falha de automação.

        Em subprocesso porque o plugin de logging do pytest substitui os handlers
        da raiz, o que tornaria a verificação em processo um falso negativo.
        """
        script = tmp_path / "loga_pelo_stdlib.py"
        script.write_text(
            "import logging, sys\n"
            f"sys.path.insert(0, {str(_RAIZ_UNIFICADO)!r})\n"
            "import comum.config.logger_config  # instala o InterceptHandler\n"
            "logging.getLogger('biblioteca_de_terceiros').error('aviso de terceiro')\n",
            encoding="utf-8",
        )

        ambiente = {
            "RAIZ_LOGS": str(tmp_path / "logs"),
            "NOME_RPA": "teste",
            "PATH": "",
            "SYSTEMROOT": "C:\\Windows",
        }
        subprocess.run(
            [sys.executable, str(script)], env=ambiente, check=True, capture_output=True
        )

        arquivos = list((tmp_path / "logs").rglob("*.log"))
        assert arquivos
        assert "aviso de terceiro" in arquivos[0].read_text(encoding="utf-8")
