# type: ignore
import sys
import logging
from loguru import logger
import socket
from datetime import datetime

now = datetime.now()

year = now.strftime("%Y")
month = now.strftime("%m")
today = now.strftime("%d-%m-%Y")

log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level>|"
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

logger.remove()
logger.add(sys.stderr, format=log_format, level="INFO")


logger.add(
    f"logs/{socket.gethostname()}/{year}/{month}/{today}.log",
    rotation="100 MB",
    retention="7 days",
    format=log_format,
    level="INFO",
    encoding="utf-8",
    enqueue=True,
    backtrace=True,
    diagnose=True,
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
        self._logger.opt(depth=1).error(self._formatar(message, args))

    def critical(self, message, *args):
        self._logger.opt(depth=2).critical(self._formatar(message, args))

    @property
    def original(self):
        return self._logger


logger = LoggerWrapper(logger)


class InterceptHandler(logging.Handler):
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

__all__ = ["logger"]
