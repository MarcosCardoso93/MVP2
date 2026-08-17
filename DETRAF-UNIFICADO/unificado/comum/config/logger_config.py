# type: ignore
"""Configuração de logging — base comum dos RPAs do Detraf.

Origem: ``src/config/logger_config.py`` do Projeto 3, escolhido por ser o
superset — é o único que aceita ``%``-args (``logger.info("op %s", nome)``).
Como ``_formatar`` devolve a mensagem intacta quando não há args, é
retrocompatível com as chamadas de P1, P2 e P4.

Os robôs rodam **desassistidos**. O log é a única testemunha do que aconteceu, e
boa parte das falhas não deixa outro rastro — um clique que não achou o botão no
AGI, um e-mail que não casou com a pasta, um arquivo que a operadora mandou
diferente. Por isso as decisões abaixo.

Alterações intencionais registradas na unificação:

1. O nível vem de ``LOG_LEVEL`` (default ``INFO``). O Projeto 1 usava ``DEBUG``
   fixo; os demais, ``INFO``.
2. ``opt(depth=2)`` em todos os métodos do wrapper. Com ``depth=1`` o log reporta
   este arquivo como origem, em vez do código que chamou.

Alterações de 2026-08-04:

3. **Caminho absoluto** (``RAIZ_LOGS``). Era relativo ao diretório de trabalho, e
   como cada robô é lançado da sua própria pasta, nasceram três árvores de log
   separadas no disco. Achar uma execução virava adivinhação.
4. **Um arquivo por robô** (``NOME_RPA``). Os três escreviam no mesmo arquivo do
   dia; isolar a execução de um deles exigia filtrar na mão.
5. **A data deixou de ser congelada no import.** ``{time:YYYY}`` é resolvido pelo
   loguru a cada escrita — antes, um processo que atravessasse a meia-noite
   continuava escrevendo no arquivo do dia anterior.
6. **Retenção de 90 dias**, não 7. O ciclo do Detraf é mensal: uma contestação de
   julho é questionada em agosto, e o log que explicaria o número já teria sido
   apagado.
7. **``logger.excecao``**, que registra o traceback. O wrapper não expunha nada
   equivalente, e o resultado é que **nenhum** dos ``except`` do repositório
   gravava stack trace — só a mensagem do erro, sem dizer de onde veio.
8. ``diagnose`` passa a seguir ``LOG_DIAGNOSE``, desligado em produção: ele
   inclui os valores das variáveis locais no traceback, o que grava senha de
   banco e credencial do AGI em arquivo.
"""

import logging
import socket
import sys

from loguru import logger

from comum.config.configuration import (
    LOG_DIAGNOSE,
    LOG_LEVEL,
    LOG_RETENCAO,
    NOME_RPA,
    RAIZ_LOGS,
)

log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level>|"
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# `NOME_RPA` vazio (import fora de um main.py, ex.: em teste) cai em "comum",
# para não misturar essas linhas com a execução de um robô real.
_pasta_rpa = NOME_RPA or "comum"

#: `{time:...}` é resolvido pelo loguru **a cada escrita**, não no import.
CAMINHO_LOG = (
    RAIZ_LOGS
    / socket.gethostname()
    / _pasta_rpa
    / "{time:YYYY}"
    / "{time:MM}"
    / "{time:DD-MM-YYYY}.log"
)

logger.remove()
logger.add(sys.stderr, format=log_format, level=LOG_LEVEL)
logger.add(
    str(CAMINHO_LOG),
    rotation="100 MB",
    retention=LOG_RETENCAO,
    format=log_format,
    level=LOG_LEVEL,
    encoding="utf-8",
    enqueue=True,
    backtrace=True,
    diagnose=LOG_DIAGNOSE,
)


class LoggerWrapper:
    def __init__(self, original_logger):
        self._logger = original_logger

    @staticmethod
    def _formatar(message, args):
        return message % args if args else message

    def info(self, message, *args):
        self._logger.opt(depth=2).info(self._formatar(message, args))

    def debug(self, message, *args):
        self._logger.opt(depth=2).debug(self._formatar(message, args))

    def warning(self, message, *args):
        self._logger.opt(depth=2).warning(self._formatar(message, args))

    def error(self, message, *args):
        self._logger.opt(depth=2).error(self._formatar(message, args))

    def critical(self, message, *args):
        self._logger.opt(depth=2).critical(self._formatar(message, args))

    def excecao(self, message, *args):
        """
        Registra em nível ERROR **com o traceback** da exceção em tratamento.

        Use dentro de um ``except`` quando a falha for inesperada — I/O, parsing,
        COM. A mensagem sozinha ("erro ao ler o arquivo X: KeyError: 14") diz o
        que quebrou; o traceback diz **onde**, e é o que permite corrigir sem
        reproduzir.

        Para condições previstas — anexo inline ignorado, e-mail sem anexo
        relevante — continue usando ``warning``: ali o traceback é ruído.
        """
        self._logger.opt(depth=2, exception=True).error(self._formatar(message, args))

    @property
    def original(self):
        return self._logger


logger = LoggerWrapper(logger)


class InterceptHandler(logging.Handler):
    """Redireciona o `logging` da biblioteca padrão (e de terceiros) para o loguru."""

    def emit(self, record):
        try:
            level = logger.original.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.original.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


logging.basicConfig(handlers=[InterceptHandler()], level=0)

__all__ = ["logger", "CAMINHO_LOG"]
