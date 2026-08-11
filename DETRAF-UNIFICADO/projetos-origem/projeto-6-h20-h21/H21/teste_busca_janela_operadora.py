"""
HU-21 - Teste pontual: existe alguma janela Win32 (topo ou filha) cujo texto contenha
"Operadora Prestadora"? Enumera TUDO via win32gui, sem depender de pywinauto/UIA.
"""
import win32gui


def listar_todas_janelas():
    resultado = []

    def coletar(hwnd, _):
        resultado.append((hwnd, win32gui.GetWindowText(hwnd), win32gui.GetClassName(hwnd)))
        return True

    win32gui.EnumWindows(coletar, None)

    for hwnd_topo, _, _ in list(resultado):
        try:
            win32gui.EnumChildWindows(hwnd_topo, coletar, None)
        except Exception:
            pass

    return resultado


def main():
    todas = listar_todas_janelas()
    print(f"Total de janelas/handles enumerados: {len(todas)}")

    encontradas = [j for j in todas if "operadora" in j[1].lower()]
    print(f"\nJanelas com 'operadora' no texto ({len(encontradas)}):")
    for hwnd, texto, classe in encontradas:
        print(f"  hwnd={hwnd} texto={texto!r} classe={classe!r}")

    if not encontradas:
        print("  Nenhuma encontrada.")


if __name__ == "__main__":
    main()
