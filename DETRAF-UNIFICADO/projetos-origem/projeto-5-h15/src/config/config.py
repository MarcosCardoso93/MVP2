import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Caminho explicito (raiz do projeto, 2 niveis acima de src/config) - evita que o load_dotenv()
# "sem endereco" suba pastas e ache o .env errado de outro projeto/pasta compartilhada.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# ==========================================================================
# Mesmo padrao de leitura de env do RPA_DETRAF_RECEITA, adaptado para a HU-15
# (Envio automatico do e-mail de contestacao) + config do outlook_standalone.py.
# ==========================================================================


def _flag(nome, padrao="False"):
    return str(os.getenv(nome, padrao)).strip().lower() in ("1", "true", "sim", "yes", "on")


# Kill-switch (mesmo padrao do resto do projeto): False = so identifica o que precisa ser
# enviado e monta o e-mail em memoria, mas NAO chama mail.Send(). Util pra testar sem
# disparar e-mail de verdade pra operadora.
PERMITIR_ENVIO_EMAIL = _flag("PERMITIR_ENVIO_EMAIL")

PERIODO = os.getenv("PERIODO_REF") or datetime.now().strftime("%Y%m")
PERIODO_REF = PERIODO

# ---- Banco (mesmo padrao do resto do projeto) ----
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

# ---- Outlook (usado para montar o OutlookConfig do modulo reaproveitado) ----
OUTLOOK_ACCOUNT = os.getenv("OUTLOOK_ACCOUNT", "")  # TODO: confirmar se e a mesma caixa
                                                     # ja usada no MVP2 para RECEBER Detraf
                                                     # (tbr00848.br@telefonica.com, ver To Be)
                                                     # ou uma caixa dedicada a ENVIO.

# ---- Pastas de dados ----
# Onde ficam a carta de contestacao ja gerada e o arquivo "..._ENV" (saida do Epico 4,
# etapas anteriores a esta HU - geracao do arquivo de contestacao e carta).
DIRETORIO_CONTESTACOES = os.getenv("DIRETORIO_CONTESTACOES")
DIRETORIO_TEMP = os.getenv("DIRETORIO_TEMP")
