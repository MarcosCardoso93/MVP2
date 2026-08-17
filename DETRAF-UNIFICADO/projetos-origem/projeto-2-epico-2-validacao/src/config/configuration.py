import os
from pathlib import Path
from datetime import datetime
from typing import Set
from dateutil.relativedelta import relativedelta

HOSTNAME = os.getenv("HOSTNAME")
ENV = os.getenv("ENV", "dev").lower()

CAMINHO_DETRAF_RECEBIDO = Path(os.getenv("CAMINHO_DETRAF_RECEBIDO") or "")
CAMINHO_EXPECTATIVA_DETRAF = Path(os.getenv("CAMINHO_EXPECTATIVA_DETRAF") or "")


debug_ano_mes_atual: str | None = os.getenv("DEBUG_ANO_MES_ATUAL", None)

if debug_ano_mes_atual:
    ANO_MES_REFERENCIA: str = (
        datetime.strptime(debug_ano_mes_atual, "%Y%m") - relativedelta(months=1)
    ).strftime("%Y%m")

else:
    ANO_MES_REFERENCIA: str = (datetime.now() - relativedelta(months=1)).strftime(
        "%Y%m"
    )

_env_csv: str = os.getenv("EXTENSOES_CSV", "")

EXTENSOES_CSV: Set[str] = {
    f".{ext.strip().lstrip('.')}".lower() for ext in _env_csv.split(",") if ext.strip()
}

_env_excel: str = os.getenv("EXTENSOES_EXCEL", "")

EXTENSOES_EXCEL: Set[str] = {
    f".{ext.strip().lstrip('.')}".lower()
    for ext in _env_excel.split(",")
    if ext.strip()
}

EXTENSOES_PERMITIDAS: Set[str] = EXTENSOES_CSV.union(EXTENSOES_EXCEL)


_env_pastas: str = os.getenv("PASTAS_EXPECTATIVAS", "")

PASTAS_EXPECTATIVAS: list[str] = [
    pasta.strip() for pasta in _env_pastas.split(",") if pasta.strip()
]

_env_substrings: str = os.getenv("EXPECTATIVA_SUBSTRING", "")
EXPECTATIVA_SUBSTRING: list[str] = [
    sub.strip() for sub in _env_substrings.split(",") if sub.strip()
]


HOST_BD_RPA = os.getenv("HOST_BD_RPA", "")
PORT_BD_RPA = os.getenv("PORT_BD_RPA", "")
DATABASE_RPA = os.getenv("DATABASE_RPA", "")
USUARIO_BD = os.getenv("USUARIO_BD", "")
SENHA_BD = os.getenv("SENHA_BD", "")

NOME_FANTASIA_VIVO = [
    nome.strip()
    for nome in os.getenv("NOME_FANTASIA_VIVO", "").split(",")
    if nome.strip()
]

IGNORAR_ARQUIVOS = [
    sub.strip() for sub in os.getenv("IGNORAR_ARQUIVOS", "").split(",") if sub.strip()
]

DIRETORIO_HISTORICO_ARQUIVOS = Path(os.getenv("DIRETORIO_HISTORICO_ARQUIVOS", ""))

RASTREAMENTO_ARQUIVO_PATH = Path(os.getenv("RASTREAMENTO_ARQUIVO_PATH") or "")
CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO = Path(
    os.getenv("CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO") or ""
)
