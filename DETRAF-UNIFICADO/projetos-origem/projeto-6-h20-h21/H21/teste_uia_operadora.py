"""
HU-21 - Teste exploratorio: pywinauto com backend UIA no modal "Filtro de Registros".

Objetivo: verificar se o Adobe AIR/Flex do Portal Triad expoe os campos via UI Automation
(o resto do projeto assume que NAO expoe, por isso usa reconhecimento de imagem +
Ctrl+A/Ctrl+C via clipboard - que falha por causa de foco de janela, ver
AGI_CONFIG._ler_valor_dropdown). Se UIA funcionar de verdade aqui, da pra ler/selecionar
o valor de "Operadora Prestadora" direto pelos controles, sem depender de foco nem de
imagem, e sem o problema de navegar Down por ate 2776 EOTs (tbl_anexo5_processado).

PRE-REQUISITO: Portal Triad ja aberto, logado, na tela "Contestacao > Gerenciar"
(este script NAO faz login/navegacao - so abre o Filtro e inspeciona os controles).

Rodar direto (fora do fluxo principal, so para diagnostico):
    python teste_uia_operadora.py
"""
import time

import pyautogui
from pywinauto.application import Application
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

NOME_JANELA = "Portal Triad: Vivo - Produção: "


def conectar_portal_triad(nome_janela=NOME_JANELA):
    for w in Desktop(backend="uia").windows():
        if w.window_text() == nome_janela:
            app = Application(backend="uia").connect(title=nome_janela)
            return app.window(title=nome_janela)
    raise RuntimeError(
        f"Janela '{nome_janela}' nao encontrada - confirme que o Portal Triad esta "
        f"aberto e logado antes de rodar este teste."
    )


def abrir_filtro(janela):
    btn_filtro = janela.child_window(title="Filtro", control_type="Button")
    btn_filtro.wait("visible", timeout=10)
    btn_filtro.click_input()


def abrir_dropdown_operadora_por_tab(janela, qtd_tabs=17):
    # Volta pra abordagem original (a que voce confirmou funcionar, com print da lista
    # aberta) - clique de mouse (via UIA invoke ou via pyautogui em coordenada absoluta)
    # NAO abriu a lista nas duas tentativas anteriores (dump identico antes/depois).
    # Navegar por Tab ate o campo e mandar Ctrl+Down e o que comprovadamente funciona.
    campo_operadora = janela.child_window(title="Operadora Prestadora:", control_type="Text")
    campo_operadora.wait("visible", timeout=10)
    campo_operadora.click_input()  # foca a area do modal antes de comecar a tabular
    time.sleep(1)

    for _ in range(qtd_tabs):
        send_keys("{TAB}")
        time.sleep(0.05)

    send_keys("^({DOWN})")
    time.sleep(1)
    return campo_operadora


def inspecionar_valor_operadora(janela):
    # SO LEITURA (nao clica, nao digita) - por isso nao compete pelo foco de tela com
    # outra coisa que voce estiver usando ao mesmo tempo (VSCode, etc.). Tenta ler
    # propriedades de 'Operadora Prestadora:Image' (a caixa de VALOR, nao o label) sem
    # exigir que a janela esteja em primeiro plano.
    campo_valor = janela.child_window(title="Operadora Prestadora:Image", control_type="Image")

    print(f".exists(): {campo_valor.exists()}")
    if not campo_valor.exists():
        print("Elemento nao encontrado - nao da pra ler mais nada dele.")
        return

    print(f".rectangle(): {campo_valor.rectangle()}")
    print(f".window_text(): {campo_valor.window_text()!r}")

    try:
        print(f".legacy_properties(): {campo_valor.legacy_properties()}")
    except Exception as e:
        print(f"legacy_properties() falhou: {e}")

    try:
        print(f".get_value(): {campo_valor.get_value()}")
    except Exception as e:
        print(f"get_value() falhou (esperado se nao suportar ValuePattern): {e}")


def main():
    janela = conectar_portal_triad()
    print(f"Conectado: {janela.window_text()!r}")

    # PASSO 1 - abre o modal de Filtro (ja confirmado que funciona via UIA). Se o modal
    # ja estiver aberto (ex.: voce deixou aberto manualmente), o clique pode falhar ou nao
    # fazer nada - nao interrompe o script, so avisa e segue.
    try:
        abrir_filtro(janela)
        print("Filtro aberto.")
    except Exception as e:
        print(f"[AVISO] abrir_filtro nao confirmou (pode ja estar aberto): {e}")

    time.sleep(1)

    # PASSO 2 - abre a lista via Tab+Ctrl+Down (unica forma confirmada que funciona).
    try:
        abrir_dropdown_operadora_por_tab(janela)
        print("Navegacao por Tab ate Operadora Prestadora concluida.")
    except Exception as e:
        print(f"[FALHOU] abrir_dropdown_operadora_por_tab: {e}")
        return

    # PASSO 3 - print de tela com a lista aberta, pra inspecionar visualmente o que
    # renderiza ali (primeiro passo necessario pra OCR de qualquer forma).
    caminho_print = "print_dropdown_operadora.png"
    time.sleep(1)
    pyautogui.screenshot(caminho_print)
    print(f"Print salvo em: {caminho_print}")

    # PASSO 4 - dump do pywinauto (child_window paths) NESSE EXATO MOMENTO, com a lista
    # aberta - repetindo o teste ja feito antes (3x, sempre com resultado negativo) so
    # que agora junto com o print, pra comparar lado a lado.
    print("=" * 60)
    print("Arvore/paths do pywinauto com a lista de Operadora aberta:")
    janela.print_control_identifiers(depth=14)

    # PASSO 5 - leitura SO DE PROPRIEDADES (nao clica/digita) do elemento de valor -
    # nao compete pelo foco de tela, entao vale rodar mesmo que a janela esteja atras
    # de outra (ex.: VSCode em primeiro plano).
    print("=" * 60)
    print("Inspecao (so leitura) de 'Operadora Prestadora:Image':")
    inspecionar_valor_operadora(janela)


if __name__ == "__main__":
    main()
