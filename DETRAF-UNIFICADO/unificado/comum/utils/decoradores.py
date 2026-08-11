import time
import functools
from comum.config.logger_config import logger


def log_execucao(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        inicio = time.time()

        # Verifica se é método de classe
        nome_classe = ""
        if args and hasattr(args[0], "__class__"):
            if hasattr(args[0], func.__name__):
                nome_classe = f"{args[0].__class__.__name__}."

        nome_completo = f"{nome_classe}{func.__name__}"

        logger.info(f"[STEP] Iniciando: {nome_completo}")

        try:
            return func(*args, **kwargs)
        finally:
            tempo_gasto = round(time.time() - inicio, 2)
            logger.info(
                f"[STEP] Finalizando: {nome_completo} | Tempo gasto: {tempo_gasto}s"
            )

    return wrapper
