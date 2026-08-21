"""Vigia do alerta de segurança do Outlook — "Permitir" automático.

Contexto: enquanto o ajuste de registro
(``HKCU\\Software\\Policies\\Microsoft\\Office\\16.0\\Outlook\\Security``) não
pega — ou como reforço, se uma política de domínio (GPO) sobrescrever esse
ajuste local — o Outlook mostra, ao conectar/ler a caixa via COM, o alerta:

    "Progr. tentando acessar inform. de endereço de email armazenados no
    Outlook."

``vigiar_alerta_seguranca()`` é um *context manager*: liga uma thread em
segundo plano que fica só observando esse alerta, e desliga sozinha ao saír
do bloco ``with``. Não é um script solto rodando pra sempre numa janela
separada — a vigília nasce e morre junto do trecho de código que realmente
toca o Outlook, no momento em que o alerta normalmente aparece.

Quando os controles existirem, também marca a caixa "Permitir acesso por" e
escolhe a maior duração disponível na lista — o alerta demora mais para
reaparecer, em vez de voltar em 1 minuto.

⚠️ Cobre só este alerta específico (acesso a informação de endereço). Um
alerta do Outlook com outro texto (ex.: "um programa está tentando enviar um
e-mail") não é reconhecido por este módulo.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator

from pywinauto import Desktop
from pywinauto.findwindows import ElementNotFoundError

from comum.config.logger_config import logger

_TITULO_JANELA = "Microsoft Outlook"
#: Trecho de "endereço" sem o "ç" — evita depender de acento/encoding.
_TRECHO_ESPERADO = "endere"


def _e_o_alerta_certo(janela) -> bool:
    """Confere que é o alerta de acesso a endereço, não outra janela com o mesmo título."""
    try:
        textos = " ".join(janela.children_texts()).lower()
    except Exception:
        return False
    return _TRECHO_ESPERADO in textos


def _tentar_prolongar_acesso(janela) -> None:
    """Marca 'Permitir acesso por' e escolhe a maior duração, se os controles existirem."""
    try:
        caixa = janela.child_window(title="Permitir acesso por", class_name="Button")
        if not caixa.get_toggle_state():
            caixa.click_input()
        combo = janela.child_window(class_name="ComboBox")
        combo.select(combo.item_count() - 1)
    except Exception:
        pass


def _tentar_clicar_permitir() -> bool:
    """Procura o alerta e clica 'Permitir'. Devolve se encontrou (e clicou)."""
    try:
        janela = Desktop(backend="win32").window(
            title=_TITULO_JANELA, class_name="#32770"
        )
        if not janela.exists(timeout=0.3):
            return False
    except ElementNotFoundError:
        return False

    if not _e_o_alerta_certo(janela):
        return False

    _tentar_prolongar_acesso(janela)
    janela.child_window(title="Permitir", class_name="Button").click_input()
    logger.info("[vigia-outlook] Alerta de acesso a endereço apareceu — 'Permitir' clicado.")
    return True


def _vigiar(parar: threading.Event, intervalo: float) -> None:
    while not parar.is_set():
        try:
            _tentar_clicar_permitir()
        except Exception as erro:
            logger.warning(f"[vigia-outlook] Falha ao tentar clicar (ignorando): {erro}")
        parar.wait(intervalo)


@contextmanager
def vigiar_alerta_seguranca(intervalo: float = 0.5) -> Iterator[None]:
    """
    Liga a vigília do alerta enquanto o bloco ``with`` roda; desliga ao saír.

    Args:
        intervalo: Segundos entre cada verificação (padrão: 0.5s — o alerta é
            modal e bloqueia a chamada COM que o disparou, então vale checar
            com frequência para não deixar o robô parado à toa).
    """
    parar = threading.Event()
    thread = threading.Thread(target=_vigiar, args=(parar, intervalo), daemon=True)
    thread.start()
    try:
        yield
    finally:
        parar.set()
        thread.join(timeout=2)
