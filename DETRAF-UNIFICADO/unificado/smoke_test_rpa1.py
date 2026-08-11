"""Teste rápido do RPA 1 — "o robô ainda liga?", antes de caçar defeito.

`testar_rpa1.py` é o roteiro completo: doze casos, incluindo vários que forçam
recusa de propósito, para achar onde o robô se comporta errado. Esse script é
outra coisa — mais simples e mais rápido, para responder uma pergunta anterior:
**o ambiente está pronto, e o caminho feliz funciona?**

Três checagens, cada uma podendo ser a razão de uma falha:

1. As dependências do `requirements.txt` importam sem erro.
2. O espelho do banco existe e tem o Anexo 5 com as EOTs que o teste usa.
3. Um Detraf válido — identificado, aprovado na validação e salvo byte a byte
   igual — de fato chega à pasta da operadora.

Se (1) ou (2) falhar, o problema é do AMBIENTE desta máquina, e nenhuma parte do
código do RPA 1 chegou a ser exercitada. Só depois de (3) passar é que vale a
pena ir para `testar_rpa1.py` caçar defeito — falhas ali, com isto passando, são
do robô.

Roda em caixa de areia própria (`arquivos/_SMOKE_RPA1/`, com uma CÓPIA do
SQLite) — nada na árvore de homologação nem no `.env` é tocado. Ver o mesmo
mecanismo, com mais detalhe, no cabeçalho de `testar_rpa1.py`.

Uso::

    .venv\\Scripts\\python smoke_test_rpa1.py
    .venv\\Scripts\\python smoke_test_rpa1.py --referencia 202603

Código de saída: 0 se as três checagens passaram, 1 se alguma falhou.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SANDBOX = RAIZ / "arquivos" / "_SMOKE_RPA1"
BANCO_ESPELHO = RAIZ / "banco_de_dados" / "TABELAS_DETRAF_espelho.db"

REFERENCIA_PADRAO = "202603"

#: EOT da ALGAR no Anexo 5, e o nome de pasta que ela gera — usada como credora.
EOT_ALGAR = "025"
OPERADORA_ALGAR = "Algar"

#: EOT da Vivo — exigida na coluna 2 (devedora) pela regra `v_col2_vivo`.
EOT_VIVO = "010"

#: Descritor cuja última letra (`L`) mapeia para `TU-RL`, a remuneração que a
#: regra de tarifas confere contra `tbl_detraf_tarifas`.
DESCRITOR_REMUNERADO = "LENL"
#: Fora do conjunto remunerado (não termina em V, L, C ou I) — sai do escopo da
#: regra de tarifa sem deixar de ser um layout válido.
DESCRITOR_NAO_REMUNERADO = "LENX"

#: Os pacotes de que o RPA 1 depende para arrancar (`requirements.txt`), com o
#: nome do módulo Python quando difere do nome do pacote.
DEPENDENCIAS: dict[str, str] = {
    "pandas": "pandas",
    "loguru": "loguru",
    "python-dotenv": "dotenv",
    "openpyxl": "openpyxl",
    "python-dateutil": "dateutil",
    "SQLAlchemy": "sqlalchemy",
    "pywin32": "win32com.client",
}


class Falha(Exception):
    """Uma checagem falhou. A mensagem já é o que vai para o console."""


# ---------------------------------------------------------------------------
# 1. Dependências
# ---------------------------------------------------------------------------
def checar_dependencias() -> None:
    faltando = []
    for pacote, modulo in DEPENDENCIAS.items():
        try:
            importlib.import_module(modulo)
        except ImportError:
            faltando.append(pacote)

    if faltando:
        raise Falha(
            f"Faltam pacotes: {', '.join(faltando)}.\n"
            f"        Instale com: .venv\\Scripts\\pip install -r requirements.txt\n"
            f"        (rode este script com .venv\\Scripts\\python, não com o "
            f"Python do sistema — é o venv que tem essas dependências.)"
        )
    print(f"  [1/3] Dependências: {len(DEPENDENCIAS)} pacotes OK.")


# ---------------------------------------------------------------------------
# 2. Pré-condições — o espelho do banco
# ---------------------------------------------------------------------------
def checar_banco_espelho() -> None:
    if not BANCO_ESPELHO.is_file():
        raise Falha(
            f"O espelho do banco não existe em [{BANCO_ESPELHO}].\n"
            f"        Gere-o com: .venv\\Scripts\\python espelhar_banco.py\n"
            f"        (ou preparar_banco_dev.py, para dados de exemplo de 2025)."
        )

    with sqlite3.connect(BANCO_ESPELHO) as conexao:
        presentes = {
            str(linha[0]).strip()
            for linha in conexao.execute(
                "SELECT EOT FROM tbl_anexo5_processado WHERE TRIM(EOT) IN (?, ?)",
                (EOT_ALGAR, EOT_VIVO),
            )
        }

    faltando = {EOT_ALGAR, EOT_VIVO} - presentes
    if faltando:
        raise Falha(
            f"O Anexo 5 do espelho não tem as EOTs {sorted(faltando)}. "
            f"Regere o espelho com espelhar_banco.py — ele pode estar "
            f"desatualizado ou vir de outra base."
        )

    print(f"  [2/3] Espelho do banco: OK, com Anexo 5 (ALGAR e Vivo presentes).")


def tarifa_regulada(referencia: str) -> tuple[str, str]:
    """
    A tarifa vigente para a ALGAR no mês, lida do espelho — ou `None` se o
    espelho não tiver vigência, caso em que o insumo usa um descritor fora do
    escopo da regra em vez de arriscar uma tarifa que seria recusada.

    Returns:
        `(descritor, tarifa)` a usar na linha do Detraf sintético.
    """
    primeiro_dia_do_mes = f"{referencia[:4]}-{referencia[4:]}-01"

    with sqlite3.connect(BANCO_ESPELHO) as conexao:
        regiao = conexao.execute(
            'SELECT "Regiao" FROM tbl_anexo5_processado WHERE TRIM(EOT) = ?',
            (EOT_ALGAR,),
        ).fetchone()
        regiao = str(regiao[0]).strip() if regiao and regiao[0] else None

        tarifas = (
            conexao.execute(
                """
                SELECT tarifa FROM tbl_detraf_tarifas
                 WHERE (TRIM(COALESCE(gh, '')) = 'N' OR TRIM(COALESCE(gh, '')) = '')
                   AND TRIM(regiao) = ?
                   AND regra_desc = 'DESC final L""'
                   AND tipo_remuneracao = 'TU-RL'
                   AND date(data_inicio) <= ?
                   AND ? <= date(data_fim)
                """,
                (regiao, primeiro_dia_do_mes, primeiro_dia_do_mes),
            ).fetchall()
            if regiao
            else []
        )

    for (valor,) in tarifas:
        if valor:
            texto = f"{float(valor):.5f}".rstrip("0")
            if float(texto) == float(valor):
                return DESCRITOR_REMUNERADO, texto.replace(".", ",")

    return DESCRITOR_NAO_REMUNERADO, "0,00631"


# ---------------------------------------------------------------------------
# 3. O caminho feliz
# ---------------------------------------------------------------------------
def escrever_detraf_valido(destino: Path, referencia: str) -> Path:
    descritor, tarifa = tarifa_regulada(referencia)
    linha = [
        EOT_ALGAR, EOT_VIVO, referencia, referencia, "SPOX_0001", "0",
        descritor, "N", "1", "2,0", tarifa, "0,01", "0,00", "0,00", "0,01",
    ]
    with destino.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo, lineterminator="\n")
        for _ in range(5):
            escritor.writerow(linha)
    return destino


def montar_ambiente(entrada: Path, operadoras: Path, banco: Path, raiz_logs: Path) -> dict[str, str]:
    """
    O ambiente do subprocesso — a caixa de areia inteira, por variável.

    `load_dotenv()` não sobrescreve o que já existe em `os.environ`, então
    estas vencem o `.env` sem que ele seja tocado. As variantes com sufixo por
    robô são apagadas: elas venceriam estas, e o teste rodaria contra a árvore
    de verdade sem avisar.
    """
    variaveis = {
        "ENV": "dev",
        "CAMINHO_SQLITE": str(banco),
        "CAMINHO_SQLITE_DEV": "",
        "CAMINHO_OPERADORAS": str(operadoras),
        "CAMINHO_DETRAF_RECEBIDO": str(operadoras),
        "DIRETORIO_SAIDA": str(operadoras),
        "DIRETORIO_NAO_IDENTIFICADOS": str(SANDBOX / "_NAO_IDENTIFICADOS"),
        "DIRETORIO_QUARENTENA": str(SANDBOX / "_QUARENTENA"),
        "DIRETORIO_TEMP": str(SANDBOX / "_TEMP"),
        "DIRETORIO_SAIDA_VALIDACAO": str(SANDBOX / "_SAIDA"),
        "DIRETORIO_HISTORICO_ARQUIVOS": str(SANDBOX / "historico"),
        "RASTREAMENTO_ARQUIVO_PATH": str(entrada / "_rastreamento.json"),
        "RAIZ_LOGS": str(raiz_logs),
        "NOTIFICAR_OPERADORA_ENVIAR": "false",
        "PERMITIR_ENVIO_EMAIL": "false",
        "PERMITIR_UPLOAD_AGI": "false",
        "PERMITIR_ACESSO_AGI": "false",
        "PERMITIR_DOWNLOAD_SFTP": "false",
        "PAUSA_ENTRE_ETAPAS": "false",
    }

    do_processo = dict(os.environ)
    for nome in list(do_processo):
        if any(nome == f"{base}_RPA1" for base in variaveis):
            del do_processo[nome]
    do_processo.update(variaveis)
    return do_processo


def checar_caminho_feliz(referencia: str) -> None:
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)

    entrada = SANDBOX / "Entrada"
    entrada.mkdir(parents=True)
    operadoras = SANDBOX / "Operadoras"
    banco = SANDBOX / "banco.db"
    shutil.copy2(BANCO_ESPELHO, banco)

    arquivo = escrever_detraf_valido(entrada / "VALIDO_smoke.csv", referencia)
    hash_original = hashlib.sha256(arquivo.read_bytes()).hexdigest()

    comando = [
        sys.executable,
        str(RAIZ / "rpa1_captura" / "main.py"),
        "--pasta-entrada", str(entrada),
        "--referencia", referencia,
        "--etapa", "processamento",
        "--dry-run",
    ]
    processo = subprocess.run(
        comando,
        cwd=RAIZ,
        env=montar_ambiente(entrada, operadoras, banco, SANDBOX / "logs"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if processo.returncode != 0:
        raise Falha(
            f"O robô terminou com código {processo.returncode} (esperado: 0).\n"
            + _indentar(processo.stdout[-3000:] + processo.stderr[-1000:])
        )

    destino = (
        operadoras / OPERADORA_ALGAR / referencia[:4] / referencia / "Detrafs Recebidos"
        / arquivo.name
    )
    if not destino.is_file():
        raise Falha(
            f"O arquivo válido não chegou a [{destino.relative_to(SANDBOX)}].\n"
            + _onde_foi_parar(operadoras, arquivo.name)
            + "\n"
            + _indentar(processo.stdout[-3000:])
        )

    if hashlib.sha256(destino.read_bytes()).hexdigest() != hash_original:
        raise Falha("O arquivo chegou, mas o conteúdo mudou — a captura não pode transformar o arquivo.")

    print(f"  [3/3] Caminho feliz: OK — identificado, validado e salvo em [{destino.parent.relative_to(SANDBOX)}].")


def _onde_foi_parar(operadoras: Path, nome_arquivo: str) -> str:
    for raiz in (operadoras, SANDBOX / "_QUARENTENA", SANDBOX / "_NAO_IDENTIFICADOS"):
        if raiz.is_dir() and any(raiz.rglob(nome_arquivo)):
            return f"        Encontrado em: {raiz.relative_to(SANDBOX)}."
    return "        Não está em lugar nenhum dentro da caixa de areia."


def _indentar(texto: str) -> str:
    return "\n".join(f"        {linha}" for linha in texto.splitlines())


# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="smoke_test_rpa1.py",
        description=(
            "Três checagens rápidas — dependências, banco espelho e o caminho "
            "feliz do RPA 1 — antes de caçar defeito com testar_rpa1.py."
        ),
    )
    parser.add_argument(
        "--referencia",
        default=REFERENCIA_PADRAO,
        metavar="AAAAMM",
        help=f"Mês de tráfego a simular (default: {REFERENCIA_PADRAO}).",
    )
    args = parser.parse_args(argv)

    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8", errors="replace")

    if not args.referencia.isdigit() or len(args.referencia) != 6:
        parser.error(f"'{args.referencia}' não é AAAAMM — ex.: {REFERENCIA_PADRAO}.")

    print("\n--- Smoke test do RPA 1 ---\n")

    for checagem in (
        checar_dependencias,
        checar_banco_espelho,
        lambda: checar_caminho_feliz(args.referencia),
    ):
        try:
            checagem()
        except Falha as falha:
            print(f"\nFALHOU: {falha}\n")
            return 1
        except Exception as erro:  # falha inesperada na checagem, não no robô
            print(f"\nFALHOU (erro inesperado no próprio teste): {erro!r}\n")
            return 1

    print("\nAmbiente pronto e caminho feliz funcionando. Pode ir para "
          "testar_rpa1.py caçar defeito.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
