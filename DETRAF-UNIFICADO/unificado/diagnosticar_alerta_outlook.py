"""Diagnóstico de baixo nível (win32gui puro) do alerta de segurança do Outlook.

As duas rodadas anteriores (com `pywinauto`) só devolveram o título da própria
janela, nunca o conteúdo — nem para o suposto alerta, nem para outras janelas
utilitárias do Outlook. Rodar como Administrador não mudou o resultado. Duas
hipóteses ficaram em aberto: (a) o alerta não estava de fato na tela no
instante exato em que o diagnóstico rodou, ou (b) existe uma barreira de
segurança do Windows (UIPI) impedindo a leitura dos controles internos.

Este script tira o `pywinauto` do meio — usa `win32gui` direto (mesma
biblioteca que o resto do projeto já usa) — e não depende de acertar o
timing manualmente: ele fica observando e só reage quando uma janela de
**topo genuinamente nova** aparecer (comparando com o que já existia quando
o script começou). Isso resolve a hipótese (a): dispare o alerta (rode o
RPA1) SOMENTE DEPOIS de este script já estar rodando.

Para cada janela nova, tenta enumerar os filhos via `EnumChildWindows` — se
isso vier vazio mesmo para uma janela que visivelmente tem botões na tela,
é a confirmação definitiva da hipótese (b).

Uso::

    python diagnosticar_alerta_outlook.py
    python diagnosticar_alerta_outlook.py --tempo 90

Deixe rodando, dispare o alerta, espere o script imprimir e terminar sozinho
(ou Ctrl+C). Copie a saída inteira.
"""

from __future__ import annotations

import argparse
import time

import win32gui


def _capturar_janelas_de_topo() -> dict[int, tuple[str, str]]:
    """`{hwnd: (título, classe)}` de toda janela de topo agora."""
    janelas: dict[int, tuple[str, str]] = {}

    def _callback(hwnd, _extra) -> bool:
        try:
            janelas[hwnd] = (win32gui.GetWindowText(hwnd), win32gui.GetClassName(hwnd))
        except Exception:
            pass
        return True

    win32gui.EnumWindows(_callback, None)
    return janelas


def _descrever_hwnd(hwnd: int) -> str:
    try:
        texto = win32gui.GetWindowText(hwnd)
        classe = win32gui.GetClassName(hwnd)
        visivel = win32gui.IsWindowVisible(hwnd)
        habilitada = win32gui.IsWindowEnabled(hwnd)
        return (
            f"hwnd={hwnd} classe='{classe}' texto='{texto}' "
            f"visível={bool(visivel)} habilitada={bool(habilitada)}"
        )
    except Exception as erro:
        return f"hwnd={hwnd} (falha ao ler: {erro})"


def _dump_janela_e_filhos(hwnd: int) -> None:
    print(_descrever_hwnd(hwnd))

    filhos: list[int] = []

    def _callback(h, _extra) -> bool:
        filhos.append(h)
        return True

    try:
        win32gui.EnumChildWindows(hwnd, _callback, None)
    except Exception as erro:
        print(f"  (EnumChildWindows falhou: {erro})")
        return

    if not filhos:
        print("  (nenhum filho encontrado via EnumChildWindows)")
        return

    print(f"  {len(filhos)} filho(s) direto(s):")
    for filho in filhos:
        print(f"  - {_descrever_hwnd(filho)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tempo", type=float, default=60.0,
        help="Segundos a observar antes de desistir (padrão: 60).",
    )
    args = parser.parse_args()

    antes = _capturar_janelas_de_topo()
    print(
        f"[diagnóstico] {len(antes)} janela(s) de topo já existem agora. "
        f"Observando por até {args.tempo:.0f}s — dispare o alerta AGORA "
        "(rode o RPA1). Ctrl+C para parar antes."
    )

    fim = time.time() + args.tempo
    try:
        while time.time() < fim:
            agora = _capturar_janelas_de_topo()
            novas = [hwnd for hwnd in agora if hwnd not in antes]
            if novas:
                for hwnd in novas:
                    print("\n" + "=" * 70)
                    print("JANELA NOVA (apareceu depois que o diagnóstico começou):")
                    print("=" * 70)
                    _dump_janela_e_filhos(hwnd)
                return 0
            antes = agora
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\n[diagnóstico] Interrompido.")
        return 1

    print("[diagnóstico] Nenhuma janela nova apareceu no tempo dado.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
