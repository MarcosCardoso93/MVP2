"""Teste isolado da vigília do alerta de segurança do Outlook.

Só leitura — não move, não baixa, não altera nada na caixa. Conecta no
Outlook e lê `SenderEmailAddress` de alguns e-mails da Caixa de Entrada,
que é exatamente a ação que dispara o alerta:

    "Progr. tentando acessar inform. de endereço de email armazenados no
    Outlook."

O ajuste de registro (``Policies\\...\\16.0\\Outlook\\Security``) não
suprimiu o alerta — descartada também a hipótese de política de domínio
(confirmado via ``rsop.msc``, sem nenhuma política de Outlook aplicada).
Suspeita atual: builds recentes do Outlook (Click-to-Run) deixaram de
respeitar o valor "aprovar automaticamente" para este guard específico.

Por isso este script agora **testa o clique automático** (o mesmo
mecanismo de ``comum/integracoes/outlook_alerta_seguranca.py`` — processo
separado, clique por mensagem direta ao controle, sem mover o mouse de
verdade) — só aqui, num script que não move nem baixa nada, antes de
reintegrar ao RPA1.

Uso::

    python testar_alerta_registro.py

O que observar: se o alerta aparecer na tela e for clicado sozinho (sem
você precisar tocar em nada) e a lista de e-mails aparecer no final, a
automação funcionou. Se alguma janela estranha abrir na tela (algo além do
próprio alerta sendo clicado), pare com Ctrl+C imediatamente e me avise —
é o mesmo tipo de sintoma do incidente anterior.
"""

from __future__ import annotations

import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

import pythoncom
import win32com.client

from comum.config import configuration
from comum.integracoes.outlook_alerta_seguranca import vigiar_alerta_seguranca


def main() -> int:
    print(f"Conectando ao Outlook (conta: '{configuration.OUTLOOK_ACCOUNT}')...")
    print("Vigília do alerta ligada — se ele aparecer, deve ser clicado sozinho.\n")

    with vigiar_alerta_seguranca():
        pythoncom.CoInitialize()
        app = win32com.client.Dispatch("Outlook.Application")
        ns = app.GetNamespace("MAPI")

        parent = ns.Folders(configuration.OUTLOOK_ACCOUNT)
        inbox = parent.Store.GetDefaultFolder(6)  # olFolderInbox
        items = inbox.Items
        items.Sort("[ReceivedTime]", True)

        total = min(5, items.Count)
        print(f"Lendo o remetente dos {total} e-mail(s) mais recente(s) da Caixa de Entrada...")

        for i in range(1, total + 1):
            item = items.Item(i)
            try:
                if item.Class != 43:  # olMailItem
                    continue
                print(f"  {i}. assunto='{item.Subject}' remetente='{item.SenderEmailAddress}'")
            except Exception as erro:
                print(f"  {i}. (falha ao ler: {erro})")

    print("\nTerminou sem precisar de clique manual? A automação funcionou.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
