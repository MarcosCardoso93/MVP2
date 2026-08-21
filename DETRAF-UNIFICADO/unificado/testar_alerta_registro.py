"""Confirma se o ajuste de registro suprimiu o alerta de segurança do Outlook.

Só leitura — não move, não baixa, não altera nada na caixa. Conecta no
Outlook e lê `SenderEmailAddress` de alguns e-mails da Caixa de Entrada,
que é exatamente a ação que dispara o alerta:

    "Progr. tentando acessar inform. de endereço de email armazenados no
    Outlook."

Serve para testar o ajuste de registro
(``HKCU\\Software\\Policies\\Microsoft\\Office\\16.0\\Outlook\\Security``)
em segundos, sem precisar rodar o RPA1 inteiro (que move e-mails e baixa
anexo — não é o ideal pra um teste repetido).

Uso::

    python testar_alerta_registro.py

Se o alerta aparecer, o registro não pegou (confira o caminho, o tipo
DWORD, e se o Outlook foi reaberto por completo depois do ajuste). Se não
aparecer e a lista de e-mails for impressa, o registro funcionou.
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


def main() -> int:
    print(f"Conectando ao Outlook (conta: '{configuration.OUTLOOK_ACCOUNT}')...")
    pythoncom.CoInitialize()
    app = win32com.client.Dispatch("Outlook.Application")
    ns = app.GetNamespace("MAPI")

    parent = ns.Folders(configuration.OUTLOOK_ACCOUNT)
    inbox = parent.Store.GetDefaultFolder(6)  # olFolderInbox
    items = inbox.Items
    items.Sort("[ReceivedTime]", True)

    total = min(5, items.Count)
    print(f"Lendo o remetente dos {total} e-mail(s) mais recente(s) da Caixa de Entrada...")
    print("(se o alerta aparecer agora, é aqui que ele apareceria)\n")

    for i in range(1, total + 1):
        item = items.Item(i)
        try:
            if item.Class != 43:  # olMailItem
                continue
            print(f"  {i}. assunto='{item.Subject}' remetente='{item.SenderEmailAddress}'")
        except Exception as erro:
            print(f"  {i}. (falha ao ler: {erro})")

    print("\nSe você leu esta linha sem nenhum alerta ter aparecido na tela, o registro funcionou.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
