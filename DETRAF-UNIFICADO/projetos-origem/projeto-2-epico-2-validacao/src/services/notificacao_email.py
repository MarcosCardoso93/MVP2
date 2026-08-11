"""
Responde o e-mail (Outlook) de onde um arquivo foi baixado, a partir do nome
do arquivo e do arquivo de rastreamento JSON gerado pelo robô do Épico 1
(RASTREAMENTO_ARQUIVO_PATH).

Porta de DOCS/email/responder_email_por_arquivo.py para dentro de src/, sem a
CLI (não é necessária no fluxo do robô).

Pré-requisitos: Windows, com Outlook Desktop Classic instalado e com perfil
configurado (não funciona com o "Novo Outlook" do Windows 11); pywin32.
"""

import json
from pathlib import Path
from typing import Optional

from src.config.logger_config import logger


class _PlaceholderAusente(dict):
    """Usado com str.format_map para não lançar exceção em placeholder desconhecido."""

    def __missing__(self, chave):
        return "{" + chave + "}"


def buscar_registro_por_arquivo(
    nome_arquivo: str, caminho_rastreamento: Path
) -> Optional[dict]:
    """
    Procura, no arquivo de rastreamento, o registro do e-mail de origem de
    `nome_arquivo` (comparação por nome de arquivo, case-insensitive — não
    pelo caminho completo).

    Se houver mais de um registro com o mesmo nome de arquivo, retorna o mais
    recente por `received_at` e loga um aviso sobre a ambiguidade.
    """
    if not caminho_rastreamento.exists():
        logger.error(
            f"Arquivo de rastreamento não encontrado: '{caminho_rastreamento}'."
        )
        return None

    try:
        registros = json.loads(caminho_rastreamento.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error(f"Falha ao ler rastreamento '{caminho_rastreamento}': {exc}")
        return None

    candidatos = [
        registro
        for registro in registros
        if Path(registro.get("caminho_arquivo", "")).name.lower()
        == nome_arquivo.lower()
    ]

    if not candidatos:
        logger.warning(
            f"Nenhum e-mail de origem encontrado para o arquivo '{nome_arquivo}'."
        )
        return None

    if len(candidatos) > 1:
        logger.warning(
            f"{len(candidatos)} registros encontrados para '{nome_arquivo}' — "
            "usando o mais recente por 'received_at'."
        )
        candidatos.sort(key=lambda r: r.get("received_at") or "", reverse=True)

    return candidatos[0]


def renderizar_template(template: str, registro: dict, nome_arquivo: str) -> str:
    """Substitui os placeholders do template pelos dados do registro de rastreamento."""
    dados = {
        "nome_arquivo": nome_arquivo,
        "assunto_original": registro.get("subject") or "",
        "remetente": registro.get("sender_email") or "",
        "data_recebimento": registro.get("received_at") or "",
    }
    return template.format_map(_PlaceholderAusente(dados))


def _criar_resposta_outlook(entry_id: str, corpo: str, enviar: bool) -> None:
    """Conecta ao Outlook via COM e cria/envia a resposta ao e-mail `entry_id`."""
    # Import isolado aqui (não no topo do módulo) para que este arquivo possa
    # ser importado em ambientes sem pywin32/Outlook (ex.: dev fora do Windows)
    # sem quebrar o pipeline — só falha se de fato precisar criar a resposta.
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    app = win32com.client.Dispatch("Outlook.Application")
    namespace = app.GetNamespace("MAPI")

    item = namespace.GetItemFromID(entry_id)
    reply = item.Reply()
    reply.Subject = f"RES: {item.Subject}"
    reply.Body = corpo

    if enviar:
        reply.Send()
    else:
        reply.Save()


def responder_email_por_arquivo(
    nome_arquivo: str,
    template: str,
    caminho_rastreamento: Path,
    enviar: bool = False,
) -> bool:
    """
    Localiza o e-mail de origem de `nome_arquivo` (via arquivo de
    rastreamento) e cria uma resposta a esse e-mail no Outlook, usando
    `template` (com placeholders substituídos pelos dados do e-mail).

    Nunca lança exceção — todo erro é logado e retorna False, para o
    chamador não precisar tratar exceções COM.
    """
    registro = buscar_registro_por_arquivo(nome_arquivo, caminho_rastreamento)
    if registro is None:
        return False

    corpo = renderizar_template(template, registro, nome_arquivo)

    try:
        _criar_resposta_outlook(registro["entry_id"], corpo, enviar)
    except Exception as exc:
        logger.error(
            f"Falha ao {'enviar' if enviar else 'criar rascunho de'} resposta para "
            f"o e-mail de '{nome_arquivo}' (entry_id='{registro['entry_id']}'): {exc}"
        )
        return False

    logger.info(
        f"Resposta {'enviada' if enviar else 'criada como rascunho'} para o e-mail "
        f"de origem de '{nome_arquivo}' (assunto original: '{registro.get('subject')}')."
    )
    return True
