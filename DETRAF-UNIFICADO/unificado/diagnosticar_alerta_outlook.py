"""Diagnóstico único do alerta de segurança do Outlook.

O clique automático em `comum/integracoes/outlook_alerta_seguranca.py` está
baseado em suposições sobre a janela do alerta (nome de classe `#32770`,
texto contendo "endere[ço]", botão com título "Permitir") tiradas só do
print de tela — e não está funcionando, o que sugere que alguma dessas
suposições está errada para esta versão do Outlook.

Este script não tenta clicar em nada — só lista, com dados reais do
`pywinauto`, toda janela com "outlook" no título e a árvore completa de
controles dela (título exato, nome de classe, texto de cada botão/caixa/
combo). Com isso corrige-se o vigia sem chutar de novo.

**Rode manualmente, uma vez, com o alerta já aberto na tela** — depois é
só copiar a saída inteira e mandar de volta.

Uso::

    python diagnosticar_alerta_outlook.py
"""

from __future__ import annotations

from pywinauto import Desktop


def main() -> int:
    desktop = Desktop(backend="win32")
    encontrou = False

    for janela in desktop.windows():
        try:
            titulo = janela.window_text()
        except Exception:
            continue
        if "outlook" not in titulo.lower():
            continue

        encontrou = True
        print("=" * 70)
        print(f"Janela: título='{titulo}' | classe='{janela.class_name()}'")
        print("=" * 70)
        try:
            print("Textos (própria janela + todos os descendentes, em ordem):")
            for texto in janela.texts():
                print(f"  - {texto!r}")
        except Exception as erro:
            print(f"(falha ao ler os textos desta janela: {erro})")
        try:
            print("print_control_identifiers() (se disponível nesta versão do pywinauto):")
            janela.print_control_identifiers()
        except Exception as erro:
            print(f"(não disponível nesta versão/wrapper: {erro})")
        print()

    if not encontrou:
        print(
            "Nenhuma janela com 'outlook' no título foi encontrada. "
            "O alerta está mesmo aberto na tela agora?"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
