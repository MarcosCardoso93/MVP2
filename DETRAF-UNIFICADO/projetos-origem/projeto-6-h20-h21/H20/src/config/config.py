import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Caminho explicito (raiz do projeto, 2 niveis acima de src/config) - evita que o load_dotenv()
# "sem endereco" suba pastas e ache o .env errado de outro projeto/pasta compartilhada.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# ==========================================================================
# REAPROVEITADO do RPA_DETRAF_RECEITA (src/config/config.py), adaptado para o
# contexto da HU-20 (Verificacao do Relatorio Receitas e Despesas x Encontro
# de Contas). Mesmo padrao de leitura de env do exemplo.
# ==========================================================================


def _flag(nome, padrao="False"):
    return str(os.getenv(nome, padrao)).strip().lower() in ("1", "true", "sim", "yes", "on")


# Kill-switch: HU-20 e so LEITURA/conferencia (nao sobe/altera nada no AGI), mas mantido
# pelo mesmo padrao do projeto caso a sinalizacao de inconsistencia passe a escrever em
# algum sistema (Webfat, e-mail, banco).
PERMITIR_ACAO_AGI = _flag("PERMITIR_ACAO_AGI")

PERIODO = os.getenv("PERIODO_REF") or datetime.now().strftime("%Y%m")
PERIODO_REF = PERIODO

# Credenciais (mesmo padrao do exemplo - variavel de ambiente do Windows, nao fica no .env)
# TODO: confirmar se reaproveita a MESMA credencial do AGI ja usada no Epico 5 (HU-17/18)
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

# ---- Imagens (REAPROVEITADAS 100% do exemplo - o metodo Baixar_Remessa ja usa estas) ----
DIRETORIO_IMGS_AGI_CONFIG = os.getenv("DIRETORIO_IMGS_AGI_CONFIG")

# ---- Pastas de dados ----
DIRETORIO_RELATORIO_BAIXADO = os.getenv("DIRETORIO_RELATORIO_BAIXADO")  # export de Relatorios>Detraf>Receitas e Despesas

# CONFIRMADO (22/07, print real do As Is - imagem 10 do docx): o Encontro de Contas E uma
# planilha Excel de verdade, com uma ABA POR OPERADORA (ex.: aba "AMPERNET"), e a celula
# "Subtotal Despesa" fica na linha 87 (rotulo em alguma coluna a esquerda, valor na coluna
# O - ex.: O87 = -521,60). NAO e um CSV com groupby como no exemplo de Receita - a leitura
# tem que ser por aba (nome da operadora) + celula fixa via openpyxl.
DIRETORIO_ENCONTRO_CONTAS = os.getenv("DIRETORIO_ENCONTRO_CONTAS")  # caminho do .xlsx do EC
CELULA_SUBTOTAL_DESPESA = os.getenv("CELULA_SUBTOTAL_DESPESA", "O87")  # confirmado no print; parametrizavel
DIRETORIO_TEMP = os.getenv("DIRETORIO_TEMP")
# NOVO - pasta de saida do relatorio de inconsistencia (nao existia equivalente no exemplo,
# que so gerava planilhas locais sem nenhum mecanismo de alerta/escalonamento)
DIRETORIO_INCONSISTENCIAS = os.getenv("DIRETORIO_INCONSISTENCIAS")
DIRETORIO_REMESSA_BAIXADA  = os.getenv("DIRETORIO_REMESSA_BAIXADA")