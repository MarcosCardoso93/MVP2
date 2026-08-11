"""Executa as quatro suítes de teste, uma por processo.

Os três RPAs têm um pacote chamado ``src``; eles não coexistem num mesmo
processo Python, então cada suíte precisa de uma invocação separada do pytest.
Este script faz isso e consolida o resultado.

Uso:
    .venv\\Scripts\\python executar_testes.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

SUITES = [
    ("base comum", "tests"),
    ("RPA 1 — captura", "rpa1_captura/tests"),
    ("RPA 2 — validação e apuração", "rpa2_validacao_apuracao/tests"),
    ("RPA 3 — contestação, AGI e EC", "rpa3_contestacao_agi_ec/tests"),
    ("RPA 4 — retificação", "rpa4_retificacao/tests"),
]


def main() -> int:
    resultados: list[tuple[str, str]] = []
    houve_falha = False

    for rotulo, caminho in SUITES:
        alvo = RAIZ / caminho

        if not alvo.is_dir() or not any(alvo.glob("test_*.py")):
            resultados.append((rotulo, "sem testes"))
            continue

        processo = subprocess.run(
            [sys.executable, "-m", "pytest", caminho, "-p", "no:cacheprovider", "--tb=short"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
        )

        resumo = "sem resumo"
        for linha in reversed(processo.stdout.splitlines()):
            if "passed" in linha or "failed" in linha or "error" in linha:
                resumo = linha.strip("= ").strip()
                break

        if processo.returncode != 0:
            houve_falha = True
            print(f"\n{'=' * 70}\nFALHA em {rotulo}\n{'=' * 70}")
            print(processo.stdout[-4000:])

        resultados.append((rotulo, resumo))

    print(f"\n{'=' * 70}")
    for rotulo, resumo in resultados:
        print(f"  {rotulo:<34} {resumo}")
    print("=" * 70)

    return 1 if houve_falha else 0


if __name__ == "__main__":
    raise SystemExit(main())
