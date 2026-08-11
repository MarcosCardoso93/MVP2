"""Ponte entre o loguru e o `caplog` do pytest, e o silenciamento do diagnose."""

from __future__ import annotations

import logging
import os

import pytest


def silenciar_diagnose_do_log() -> None:
    """
    Desliga `LOG_DIAGNOSE` antes de `logger_config` ser importado.

    Com ele ligado — o default fora de produção — o loguru inclui o **valor de
    cada variável local** em todo traceback. Num teste que provoca exceção de
    propósito, isso despeja centenas de linhas de estado interno do pytest na
    saída e esconde a falha de verdade.
    """
    os.environ.setdefault("LOG_DIAGNOSE", "false")


@pytest.fixture(autouse=True)
def loguru_para_caplog(caplog):
    """
    Espelha as mensagens do loguru no `caplog` do pytest.

    O `caplog` lê o `logging` da biblioteca padrão; o loguru não passa por lá.
    Sem esta ponte, um teste que afirma "isto foi registrado no log" **passa em
    silêncio mesmo quando nada foi registrado** — o que seria especialmente ruim
    neste repositório, onde boa parte das correções recentes é justamente "passar
    a registrar o que era engolido".
    """
    from comum.config.logger_config import logger

    def _repassar(mensagem):
        registro = mensagem.record
        caplog.handler.emit(
            logging.LogRecord(
                name=registro["name"] or "loguru",
                level=registro["level"].no,
                pathname=registro["file"].path,
                lineno=registro["line"],
                msg=registro["message"],
                args=(),
                exc_info=registro["exception"],
            )
        )

    id_sink = logger.original.add(_repassar, format="{message}", level=0)
    try:
        yield caplog
    finally:
        logger.original.remove(id_sink)
