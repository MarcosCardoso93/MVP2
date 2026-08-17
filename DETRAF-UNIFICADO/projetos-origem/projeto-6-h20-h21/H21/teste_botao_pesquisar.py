"""
Teste pontual: confirma se o botao "Pesquisar" (tela principal de Contestacao) e
acessivel via UIA, e com qual title/control_type exato.
"""
from pywinauto.application import Application
from pywinauto import Desktop

NOME_JANELA = "Portal Triad: Vivo - Produção: "


def main():
    janela = None
    for w in Desktop(backend="uia").windows():
        if w.window_text() == NOME_JANELA:
            app = Application(backend="uia").connect(title=NOME_JANELA)
            janela = app.window(title=NOME_JANELA)
            break
    if janela is None:
        raise RuntimeError(f"Janela '{NOME_JANELA}' nao encontrada.")

    print("Conectado.")

    botao = janela.child_window(title="Pesquisar", control_type="Button")
    print(f".exists(): {botao.exists()}")
    if botao.exists():
        print(f".window_text(): {botao.window_text()!r}")
        print(f".rectangle(): {botao.rectangle()}")

    # Dump completo salvo em arquivo, pra caso o nome nao seja exatamente "Pesquisar"
    # (ex.: espaco extra) - assim da pra ver o nome real na lista de Button.
    with open("dump_tela_principal.txt", "w", encoding="utf-8") as f:
        import contextlib
        with contextlib.redirect_stdout(f):
            janela.print_control_identifiers(depth=12)
    print("Dump completo salvo em: dump_tela_principal.txt")


if __name__ == "__main__":
    main()
