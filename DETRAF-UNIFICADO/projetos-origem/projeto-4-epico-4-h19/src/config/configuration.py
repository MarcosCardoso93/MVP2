"""Leitura centralizada de variáveis de ambiente do Épico 4.

Único ponto do projeto autorizado a ler `os.getenv` (ver
`AI/01-Arquitetura.md` §1). Cada variável é lida uma única vez e exposta como
constante tipada. Carrega um `.env` se `python-dotenv` estiver disponível.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Set

from dateutil.relativedelta import relativedelta

# Carrega variáveis de um arquivo .env, se existir (opcional em dev/testes).
try:  # pragma: no cover - dependência opcional
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


HOSTNAME = os.getenv("HOSTNAME")
ENV = os.getenv("ENV", "dev").lower()


# ---------------------------------------------------------------------------
# Período de referência (AAAAMM)
# ---------------------------------------------------------------------------
# Override do mês/ano de referência para testes (formato AAAAMM). Se vazio, usa
# o mês atual - 1 (regra de negócio do DETRAF: sempre o mês anterior).
debug_ano_mes_atual: str | None = os.getenv("DEBUG_ANO_MES_ATUAL", None)

if debug_ano_mes_atual:
    ANO_MES_REFERENCIA: str = (
        datetime.strptime(debug_ano_mes_atual, "%Y%m") - relativedelta(months=1)
    ).strftime("%Y%m")
else:
    ANO_MES_REFERENCIA: str = (datetime.now() - relativedelta(months=1)).strftime(
        "%Y%m"
    )


# ---------------------------------------------------------------------------
# Extensões de arquivo aceitas por gerenciador_arquivos.py
# ---------------------------------------------------------------------------
_env_csv: str = os.getenv("EXTENSOES_CSV", "csv,txt")

EXTENSOES_CSV: Set[str] = {
    f".{ext.strip().lstrip('.')}".lower() for ext in _env_csv.split(",") if ext.strip()
}

_env_excel: str = os.getenv("EXTENSOES_EXCEL", "xlsx,xls")

EXTENSOES_EXCEL: Set[str] = {
    f".{ext.strip().lstrip('.')}".lower()
    for ext in _env_excel.split(",")
    if ext.strip()
}

EXTENSOES_PERMITIDAS: Set[str] = EXTENSOES_CSV.union(EXTENSOES_EXCEL)


# ---------------------------------------------------------------------------
# Banco de dados (MySQL em prod, SQLite local em dev)
# ---------------------------------------------------------------------------
# Caminho do SQLite em dev — substitui o caminho hardcoded da referência (T-003).
# Vazio => o repositório de cache resolve um SQLite local padrão.
CAMINHO_SQLITE: str = os.getenv("CAMINHO_SQLITE", "")

HOST_BD_RPA = os.getenv("HOST_BD_RPA", "")
PORT_BD_RPA = os.getenv("PORT_BD_RPA", "")
DATABASE_RPA = os.getenv("DATABASE_RPA", "")
USUARIO_BD = os.getenv("USUARIO_BD", "")
SENHA_BD = os.getenv("SENHA_BD", "")


# ---------------------------------------------------------------------------
# Caminhos de I/O do Épico 4 (estrutura de pastas — AI/09 §9, AI/10)
# ---------------------------------------------------------------------------
# Raiz "...\Operadoras" que contém {operadora}\{ano}\{aaaamm}\...
CAMINHO_OPERADORAS = Path(os.getenv("CAMINHO_OPERADORAS", ""))

# Controle de numeração de carta: "...\Correspondências Enviadas\CT\{ano}".
CAMINHO_CONTROLE_CT = Path(os.getenv("CAMINHO_CONTROLE_CT", ""))

# Nomes das subpastas de saída (configuráveis — AI/09 §9).
SUBPASTA_AGI: str = os.getenv("SUBPASTA_AGI", "AGI")
SUBPASTA_CONTESTACOES: str = os.getenv("SUBPASTA_CONTESTACOES", "Contestações")
SUBPASTA_DETRAFS_RECEBIDOS: str = os.getenv(
    "SUBPASTA_DETRAFS_RECEBIDOS", "Detrafs Recebidos"
)
SUBPASTA_DETRAFS_ENVIADOS: str = os.getenv(
    "SUBPASTA_DETRAFS_ENVIADOS", "Detrafs Enviados"
)

# Modelos/máscaras externas — BLOQUEADOS (ver TODO/bloqueios.md D-3/D-4/D-5).
CAMINHO_MODELO_CARTA = Path(os.getenv("CAMINHO_MODELO_CARTA", ""))
CAMINHO_MASCARA_CONT_PROC = Path(os.getenv("CAMINHO_MASCARA_CONT_PROC", ""))


# Diretório onde historico_arquivos.py salva o JSON de controle de reprocessamento.
DIRETORIO_HISTORICO_ARQUIVOS = Path(os.getenv("DIRETORIO_HISTORICO_ARQUIVOS", ""))
