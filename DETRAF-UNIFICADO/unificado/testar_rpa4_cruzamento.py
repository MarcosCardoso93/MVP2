"""Teste isolado do cruzamento `achar_id_processo` (RPA 4, HU-21).

Não abre o AGI, não usa banco, não usa `.env`: fabrica um CSV local no formato
que `exportar_grid_csv` produziria e confere se o cruzamento por EOT + Período
Referência + Período Tráfego + Valor Bruto acha a linha certa.

Cobre também o caso real que motivou o valor entrar no cruzamento (achado em
2026-08-03: duas linhas com EOT + Referência + Tráfego iguais, valor diferente)
— sem ele, `achar_id_processo` escolheria uma das duas e lançaria a Recuperação
no processo errado, que é irreversível.

Uso::

    python testar_rpa4_cruzamento.py
"""

from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum.dominio.retificacao import ProcessoNaoIdentificado, achar_id_processo

COLUNAS = ["ID Processo", "Ope. Prest.", "Per. Ref.", "Per. Traf.", "Valor Bruto"]


def _escrever_csv(caminho: Path, linhas: list[dict]) -> None:
    with caminho.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS, delimiter=";")
        escritor.writeheader()
        escritor.writerows(linhas)


def main() -> int:
    pasta = Path(tempfile.mkdtemp(prefix="rpa4_cruzamento_"))
    ok = True

    # Cenário 1: uma linha só, tudo bate — acha o processo.
    # ⚠️ "Valor Bruto" no CSV do AGI vem em formato BR (vírgula decimal) —
    # ver `converter_valor_br`. Escrever em formato americano aqui faria o
    # teste "achar" o número errado por 100x, não por não achar nada.
    caminho1 = pasta / "cenario1.csv"
    _escrever_csv(caminho1, [
        {"ID Processo": "590969", "Ope. Prest.": "406", "Per. Ref.": "202606",
         "Per. Traf.": "202605", "Valor Bruto": "125,30"},
    ])
    try:
        achado = achar_id_processo(caminho1, "406", "202606", "202605", 125.30)
        print(f"[cenário 1] OK — achou {achado!r} (esperado '590969').")
        ok = ok and achado == "590969"
    except Exception as erro:
        print(f"[cenário 1] FALHOU — deveria achar, e levantou: {erro}")
        ok = False

    # Cenário 2: duas linhas com EOT+Referência+Tráfego iguais, valor diferente
    # — o caso real de 2026-08-03. Sem o valor no cruzamento, escolheria uma
    # das duas errado; com ele, acha a certa.
    caminho2 = pasta / "cenario2.csv"
    _escrever_csv(caminho2, [
        {"ID Processo": "590969", "Ope. Prest.": "406", "Per. Ref.": "202606",
         "Per. Traf.": "202605", "Valor Bruto": "125,30"},
        {"ID Processo": "590971", "Ope. Prest.": "406", "Per. Ref.": "202606",
         "Per. Traf.": "202605", "Valor Bruto": "88,10"},
    ])
    try:
        achado = achar_id_processo(caminho2, "406", "202606", "202605", 88.10)
        print(f"[cenário 2] OK — achou {achado!r} entre duas parecidas (esperado '590971').")
        ok = ok and achado == "590971"
    except Exception as erro:
        print(f"[cenário 2] FALHOU — deveria distinguir pelo valor, e levantou: {erro}")
        ok = False

    # Cenário 3: nenhuma linha bate — tem que levantar ProcessoNaoIdentificado,
    # nunca escolher a "mais parecida".
    try:
        achar_id_processo(caminho1, "406", "202606", "202605", 999.99)
        print("[cenário 3] FALHOU — deveria levantar ProcessoNaoIdentificado, e não levantou.")
        ok = False
    except ProcessoNaoIdentificado:
        print("[cenário 3] OK — valor sem correspondência corretamente rejeitado.")
    except Exception as erro:
        print(f"[cenário 3] FALHOU — levantou o erro errado: {erro}")
        ok = False

    print(f"\nCSVs de teste em: {pasta}")
    print("RESULTADO: " + ("tudo passou" if ok else "algo falhou — veja acima"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
