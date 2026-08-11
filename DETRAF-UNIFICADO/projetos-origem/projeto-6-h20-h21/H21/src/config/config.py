import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Caminho explicito (raiz do projeto, 2 niveis acima de src/config) - evita que o load_dotenv()
# "sem endereco" suba pastas e ache o .env errado de outro projeto/pasta compartilhada.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# ==========================================================================
# REAPROVEITADO do RPA_DETRAF_RECEITA (src/config/config.py), adaptado para a
# HU-21 (Retificacao de Contestacao - evento de Recuperacao no AGI).
# ==========================================================================


def _flag(nome, padrao="False"):
    return str(os.getenv(nome, padrao)).strip().lower() in ("1", "true", "sim", "yes", "on")


# Kill-switch (mesmo padrao do Epico 5): False = nao grava nada no AGI, so identifica e
# calcula os valores da retificacao.
PERMITIR_ACAO_AGI = _flag("PERMITIR_ACAO_AGI")

PERIODO = os.getenv("PERIODO_REF") or datetime.now().strftime("%Y%m")
PERIODO_REF = PERIODO

# TODO: confirmar se e a MESMA credencial do AGI ja usada no Epico 5 (HU-17/18)
USUARIO_AGI = os.environ.get("RPA_DETRAF_DESPESA_AGI_USER")
SENHA_AGI = os.environ.get("RPA_DETRAF_DESPESA_AGI_PASSWORD")
DIRETORIO_AGI = os.getenv("DIRETORIO_AGI")
AGI_JANELA_HOST = os.getenv("AGI_JANELA_HOST")

USUARIO_BD = os.environ.get("RPA_DETRAF_DESPESA_DB_USER")
SENHA_BD = os.environ.get("RPA_DETRAF_DESPESA_DB_PASSWORD")
CONFIG_WEBFAT = {
    'host': os.getenv("HOST_BD_WEBFAT"),
    'port': os.getenv("PORT_BD_WEBFAT"),
    'user': USUARIO_BD,
    'password': SENHA_BD,
    'database': os.getenv("DATABASE_WEBFAT"),
}

# ---- Banco de LOGS (mesma estrutura do RPA_DETRAF_RECEITA - conexao.py/Banco.log(), so
# muda o nome da tabela em conexao.py). TODO: confirmar se este RPA usa a MESMA base de
# logs compartilhada (host .79/'rpa') ou precisa de uma propria.
CONFIG_RPA = {
    'host': os.getenv("HOST_BD_RPA"),
    'port': os.getenv("PORT_BD_RPA"),
    'user': USUARIO_BD,
    'password': SENHA_BD,
    'database': os.getenv("DATABASE_RPA"),
}

# ---- Imagens ----
DIRETORIO_IMGS_AGI_CONFIG = os.getenv("DIRETORIO_IMGS_AGI_CONFIG")  # REAPROVEITADO (login)
# NOVO - pasta praticamente vazia; ver MANIFESTO_IMAGENS.md. Compartilha 2 imagens de menu
# (bnt_contestacao.png / bnt_submenu_gerenciar.png) com a HU-18 do Epico 5 - se aquela HU
# capturar primeiro, so copiar as mesmas 2 imagens pra ca (ver README).
DIRETORIO_IMGS_CONTESTACAO_GERENCIAR = os.getenv("DIRETORIO_IMGS_CONTESTACAO_GERENCIAR")

# ---- Pastas de dados ----
DIRETORIO_TEMP = os.getenv("DIRETORIO_TEMP")
# TODO [NOVO]: fonte de dados para identificar "tráfego recuperado" (variacao negativa no
# mes corrente comparado a contestacao de mes anterior) - confirmar de onde vem essa
# informacao (Base_Contestacao do mes atual x historico de contestacoes ja enviadas).
DIRETORIO_REFERENCIA_CONTESTACOES = os.getenv("DIRETORIO_REFERENCIA_CONTESTACOES")
DIRETORIO_REMESSA_BAIXADA = os.getenv("DIRETORIO_REMESSA_BAIXADA")