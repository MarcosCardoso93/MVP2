import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Caminho explicito (raiz do projeto, 2 niveis acima de src/config) - evita que o load_dotenv()
# "sem endereco" suba pastas e ache o .env errado de outro projeto/pasta compartilhada.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# ==========================================================================
# REAPROVEITADO do RPA_DETRAF_RECEITA (src/config/config.py), com os nomes de
# variavel/pasta trocados para o contexto da Despesa - Epico 5 (Carga no AGI).
# A logica de leitura de env e o kill-switch sao identicos ao exemplo.
# ==========================================================================


def _flag(nome, padrao="False"):
    """Le uma flag booleana do .env. Default seguro (False): se a var faltar, NAO libera a acao."""
    return str(os.getenv(nome, padrao)).strip().lower() in ("1", "true", "sim", "yes", "on")


# ==== KILL-SWITCH DE SEGURANCA EM PRODUCAO (ver .env.example) ====
# False (padrao) = modo seguro: gera/valida os arquivos mas NAO sobe/altera nada no AGI.
PERMITIR_UPLOAD_AGI = _flag("PERMITIR_UPLOAD_AGI")

# Periodo de referencia: vem do .env (PERIODO_REF) ou, se vazio, usa o mes corrente
PERIODO = os.getenv("PERIODO_REF") or datetime.now().strftime("%Y%m")
PERIODO_REF = PERIODO

# Credenciais (mesmo padrao do exemplo: NAO ficam no .env, vem de variavel de ambiente do Windows)
# TODO: confirmar com o time se o Epico 5 vai reusar o MESMO usuario/senha do AGI ja usado na
# Receita (RPA_DETRAF_RECEITA_AGI_USER/PASSWORD) ou se a Despesa tera credencial propria.
USUARIO_AGI = os.environ.get("RPA_DETRAF_DESPESA_AGI_USER")
SENHA_AGI = os.environ.get("RPA_DETRAF_DESPESA_AGI_PASSWORD")
DIRETORIO_AGI = os.getenv("DIRETORIO_AGI")
# Host/IP do AGI que aparece no titulo das janelas de upload/download (ver README).
AGI_JANELA_HOST = os.getenv("AGI_JANELA_HOST")

# Banco (mesmo padrao do exemplo: reaproveita a classe Banco de conexao.py)
USUARIO_BD = os.environ.get("RPA_DETRAF_DESPESA_DB_USER")
SENHA_BD = os.environ.get("RPA_DETRAF_DESPESA_DB_PASSWORD")
CONFIG_WEBFAT = {
    'host': os.getenv("HOST_BD_WEBFAT"),
    'port': os.getenv("PORT_BD_WEBFAT"),
    'user': USUARIO_BD,
    'password': SENHA_BD,
    'database': os.getenv("DATABASE_WEBFAT"),
}
# TODO: confirmar as tabelas novas de log da despesa citadas no To Be MVP2 (paragrafo 5.4.5.9):
#   tbl_rpa_log_detraf_despesa_arquivos
#   tbl_rpa_log_detraf_despesa_contestacao
# Ainda nao existe metodo em conexao.py para gravar nelas - ver README, secao "Precisa ser feito".

# ---- Pastas de imagens (templates pyautogui) ----
DIRETORIO_IMGS_AGI_CONFIG = os.getenv("DIRETORIO_IMGS_AGI_CONFIG")            # REAPROVEITADO (copiado)
DIRETORIO_IMGS_UPLOAD_DETRAF = os.getenv("DIRETORIO_IMGS_UPLOAD_DETRAF")      # REAPROVEITADO (copiado, validar resolucao)
DIRETORIO_IMGS_UPLOAD_CONTESTACAO = os.getenv("DIRETORIO_IMGS_UPLOAD_CONTESTACAO")  # NOVO - pasta vazia, ver MANIFESTO_IMAGENS.md

# ---- Pastas de dados (arquivos gerados no Epico 4, consumidos aqui no Epico 5) ----
DIRETORIO_PASTA_EXT = os.getenv("DIRETORIO_PASTA_EXT")   # arquivos DE_AGI_D_<AAAAMM>_TBRA_X_<OPERADORA>_EXT
DIRETORIO_PASTA_INT = os.getenv("DIRETORIO_PASTA_INT")   # arquivos DE_AGI_D_<AAAAMM>_TBRA_X_<OPERADORA>_INT (so cenario com retencao)
DIRETORIO_PASTA_CONTESTACAO = os.getenv("DIRETORIO_PASTA_CONTESTACAO")  # arquivos CONT_PROC_MASCARA_<OPERADORA>_<AAAAMM>
DIRETORIO_EXPORT_ERRO = os.getenv("DIRETORIO_EXPORT_ERRO")
DIRETORIO_TEMP = os.getenv("DIRETORIO_TEMP")
DIRETORIO_EVIDENCIAS = os.getenv("DIRETORIO_EVIDENCIAS")  # NOVO - print automatico de sucesso do upload (nao existia no exemplo)

DIRETORIO_REMESSA_BAIXADA = os.getenv("DIRETORIO_REMESSA_BAIXADA")
DIRETORIO_RELATORIO_BAIXADO = DIRETORIO_REMESSA_BAIXADA  # alias - nome usado pelo AGI_config.py copiado do Epico 6/HU-20

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