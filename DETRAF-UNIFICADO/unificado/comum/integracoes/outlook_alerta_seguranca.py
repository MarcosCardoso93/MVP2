"""Vigia do alerta de segurança do Outlook — "Permitir" automático.

Contexto: enquanto o ajuste de registro
(``HKCU\\Software\\Policies\\Microsoft\\Office\\16.0\\Outlook\\Security``) não
pega — ou como reforço, se uma política de domínio (GPO) sobrescrever esse
ajuste local — o Outlook mostra, ao conectar/ler a caixa via COM, o alerta:

    "Progr. tentando acessar inform. de endereço de email armazenados no
    Outlook."

``vigiar_alerta_seguranca()`` é um *context manager*: liga um **processo**
em segundo plano que fica só observando esse alerta, e desliga sozinho ao
saír do bloco ``with``.

🔴 **Por que processo, e não thread (2026-08-21).** A primeira versão usava
uma `threading.Thread`. Não funcionou: a chamada COM que dispara o alerta
(via `pywin32`) trava dentro de uma função C que não libera o GIL enquanto
espera o usuário responder ao diálogo modal — então nenhuma outra thread do
mesmo processo Python roda nesse meio tempo, incluindo a que deveria clicar
"Permitir". Um processo separado tem seu próprio interpretador e GIL, e por
isso continua rodando mesmo com o processo principal congelado dentro da
chamada COM.

Quando os controles existirem, também marca a caixa "Permitir acesso por" e
escolhe a maior duração disponível na lista — o alerta demora mais para
reaparecer, em vez de voltar em 1 minuto.

⚠️ Cobre só este alerta específico (acesso a informação de endereço). Um
alerta do Outlook com outro texto (ex.: "um programa está tentando enviar um
e-mail") não é reconhecido por este módulo.
"""

from __future__ import annotations

import multiprocessing
from contextlib import contextmanager
from typing import Iterator

_TITULO_JANELA = "Microsoft Outlook"


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
    """
    Procura o alerta e clica 'Permitir'. Devolve se encontrou (e clicou).

    Importa `pywinauto` aqui dentro, não no topo do módulo: esta função roda
    num processo separado (`multiprocessing`, método `spawn` no Windows), que
    reimporta o módulo do zero — mantendo o import pesado só onde é de fato
    usado evita puxá-lo também no processo principal, que não precisa dele.

    🔴 2026-08-21: existem **duas** janelas com título 'Microsoft Outlook' e
    classe '#32770' ao mesmo tempo — uma delas parece ser algo interno do
    Outlook, sempre presente, sem conteúdo visível; a outra é o alerta de
    verdade, só quando está na tela. `Desktop.window()` (singular) exige
    exatamente 1 resultado e estourava `ElementAmbiguousError` a cada
    tentativa — sem nunca chegar a procurar o botão. Por isso troquei para
    `.windows()` (plural) e desambiguo pela única coisa que realmente
    diferencia as duas: só o alerta de verdade tem um botão 'Permitir'.
    """
    from pywinauto import Desktop

    candidatas = Desktop(backend="win32").windows(
        title=_TITULO_JANELA, class_name="#32770"
    )
    for janela in candidatas:
        try:
            botao = janela.child_window(title="Permitir", class_name="Button")
            if not botao.exists(timeout=0.2):
                continue
        except Exception:
            continue

        _tentar_prolongar_acesso(janela)
        botao.click_input()
        print("[vigia-outlook] Alerta de acesso a endereço apareceu — 'Permitir' clicado.")
        return True

    return False


def _vigiar(parar, intervalo: float) -> None:
    """Corpo do processo filho. `parar` é um `multiprocessing.Event`."""
    while not parar.is_set():
        try:
            _tentar_clicar_permitir()
        except Exception as erro:
            print(f"[vigia-outlook] Falha ao tentar clicar (ignorando): {erro}")
        parar.wait(intervalo)


@contextmanager
def vigiar_alerta_seguranca(intervalo: float = 0.3) -> Iterator[None]:
    """
    Liga a vigília do alerta (processo separado) enquanto o bloco ``with``
    roda; desliga ao saír.

    Args:
        intervalo: Segundos entre cada verificação (padrão: 0.3s — o alerta é
            modal, então vale checar com frequência).
    """
    parar = multiprocessing.Event()
    processo = multiprocessing.Process(target=_vigiar, args=(parar, intervalo), daemon=True)
    processo.start()
    try:
        yield
    finally:
        parar.set()
        processo.join(timeout=2)
        if processo.is_alive():
            processo.terminate()
