import os
from pathlib import Path
from typing import Set

from dotenv import load_dotenv

load_dotenv()

DIRETORIO_ENTRADA: Path = Path(os.getenv("DIRETORIO_ENTRADA", "entrada"))
DIRETORIO_SAIDA: Path = Path(os.getenv("DIRETORIO_SAIDA", "saida"))
COMPETENCIA: str = os.getenv("COMPETENCIA", "")

_env_csv: str = os.getenv("EXTENSOES_CSV", "")
EXTENSOES_CSV: Set[str] = {
    f".{ext.strip().lstrip('.')}".lower()
    for ext in _env_csv.split(",")
    if ext.strip()
}

_env_excel: str = os.getenv("EXTENSOES_EXCEL", "")
EXTENSOES_EXCEL: Set[str] = {
    f".{ext.strip().lstrip('.')}".lower()
    for ext in _env_excel.split(",")
    if ext.strip()
}

EXTENSOES_PERMITIDAS: Set[str] = EXTENSOES_CSV.union(EXTENSOES_EXCEL)

# Banco de dados WebFat (Anexo 5 / log de despesas) — ver src/models/repository/repositorio_tabelas.py
ENV: str = os.getenv("ENV", "dev").lower()

CAMINHO_SQLITE: str = os.getenv(
    "CAMINHO_SQLITE",
    str(Path(__file__).resolve().parent.parent.parent / "banco_de_dados" / "TABELAS_DETRAF.db"),
)

HOST_BD_RPA: str = os.getenv("HOST_BD_RPA", "")
PORT_BD_RPA: str = os.getenv("PORT_BD_RPA", "")
DATABASE_RPA: str = os.getenv("DATABASE_RPA", "")
USUARIO_BD: str = os.getenv("USUARIO_BD", "")
SENHA_BD: str = os.getenv("SENHA_BD", "")

# Outlook (HU-01)
OUTLOOK_ACCOUNT: str = os.getenv("OUTLOOK_ACCOUNT", "")
OUTLOOK_DETRAF_DESPESAS_FOLDER: str = os.getenv("OUTLOOK_DETRAF_DESPESAS_FOLDER", "Detraf Despesas")
OUTLOOK_PROCESSADOS_FOLDER: str = os.getenv("OUTLOOK_PROCESSADOS_FOLDER", "PROCESSADOS")
OUTLOOK_DEST_ROOT: str = os.getenv("OUTLOOK_DEST_ROOT", "") or str(DIRETORIO_ENTRADA)
OUTLOOK_MAX_RETRY: int = int(os.getenv("OUTLOOK_MAX_RETRY", "3"))
DETRAF_DIA_LIBERACAO: int = int(os.getenv("DETRAF_DIA_LIBERACAO", "5"))
RASTREAMENTO_ARQUIVO_PATH: str = os.getenv(
    "RASTREAMENTO_ARQUIVO_PATH",
    str(Path(str(DIRETORIO_ENTRADA)) / "_rastreamento.json"),
)
