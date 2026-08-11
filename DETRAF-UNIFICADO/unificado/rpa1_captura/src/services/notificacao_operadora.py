"""A resposta à operadora sobre Detrafs recusados (HU-04) — 2026-08-06.

Quem respondia era o RPA 2, uma execução depois. Agora responde o RPA 1, na
mesma execução em que recusa: o arquivo nunca chega à pasta da operadora, e a
operadora sabe disso no mesmo dia.

**Uma resposta por e-mail de origem, não por arquivo.** Um e-mail pode trazer
vários anexos, e vários deles podem ser reprovados; três mensagens sobre o mesmo
envio fariam a operadora agir só na primeira. O agrupamento é feito em
`ProcessamentoService._notificar_reprovados`, que só sabe o total depois de
processar tudo.

O que este módulo faz é montar o corpo. Quem sabe falar com o Outlook é o
`OutlookController`, e ele chega aqui como parâmetro — ver a nota sobre a
preguiça do controller em `ProcessamentoService.__init__`.

Nada aqui levanta exceção. Quando esta função é chamada, as recusas **já estão
consumadas**: os arquivos estão na quarentena e os diagnósticos estão gravados ao
lado. Falhar em avisar é ruim; desfazer a recusa por causa disso seria pior.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, List

from comum.config import configuration
from comum.config.logger_config import logger
from comum.integracoes.corpo_email import renderizar
from src.models.dto.arquivo_para_processar import ArquivoParaProcessar
from src.models.dto.arquivo_recusado import ArquivoRecusado

#: Assinatura de quem sabe responder: `(pacote, corpo, enviar) -> conseguiu`.
Responder = Callable[[ArquivoParaProcessar, str, bool], bool]


def notificar_arquivos_recusados(
    responder: Responder,
    pacote: ArquivoParaProcessar,
    recusas: List[ArquivoRecusado],
) -> bool:
    """
    Responde ao e-mail de origem listando os arquivos recusados e os motivos.

    Args:
        responder: Normalmente `OutlookController.responder`.
        pacote: Um arquivo daquele e-mail — dele saem o `entry_id`, o assunto e
            o remetente, que valem para o envio inteiro.
        recusas: Todos os arquivos reprovados **daquele mesmo e-mail**.

    Returns:
        Se a resposta foi criada. `False` também quando falta o template — e,
        nesse caso, os arquivos continuam na quarentena. **A ausência de template
        nunca impede a recusa**; ela só impede o aviso.
    """
    if not recusas:
        return False

    template = _ler_template()
    if template is None:
        return False

    corpo = renderizar(
        template,
        {
            "assunto_original": pacote.subject or "",
            "remetente": pacote.sender_email or "",
            "data_recebimento": formatar_data(pacote.received_at),
            "quantidade": str(len(recusas)),
            "arquivos": formatar_arquivos(recusas),
        },
    )

    return bool(responder(pacote, corpo, configuration.NOTIFICAR_OPERADORA_ENVIAR))


def formatar_arquivos(recusas: List[ArquivoRecusado]) -> str:
    """
    Os arquivos recusados e seus motivos, em texto puro.

    Texto puro porque `OutlookService.responder_email` faz `reply.Body = corpo` —
    é o corpo em texto do Outlook, não HTML.

    Com **um** arquivo, sai sem numeração: um "1)" solitário parece um fragmento
    de lista, e um anexo por e-mail é o caso comum. Com vários, a numeração é o
    que permite a operadora conferir item a item.
    """
    if not recusas:
        return "(o detalhamento não pôde ser gerado; consulte o remetente)"

    numerar = len(recusas) > 1
    blocos = []

    for indice, recusa in enumerate(recusas, start=1):
        titulo = f"{indice}) {recusa.nome}" if numerar else recusa.nome
        linhas = [titulo]
        if recusa.motivos:
            linhas += [f"   - {motivo}" for motivo in recusa.motivos]
        else:
            linhas.append("   - (motivo não registrado; consulte o remetente)")
        blocos.append("\n".join(linhas))

    return "\n\n".join(blocos)


def formatar_data(iso: str) -> str:
    """
    `2026-08-03T09:14:00` -> `03/08/2026 09:14`.

    O valor vem de `received_at.isoformat()`, que é ótimo para guardar e ruim
    para ler — e este é o único texto do projeto que a operadora vê.

    Formato incompreensível ou vazio volta como veio: melhor uma data estranha
    do que uma data errada, ou um campo em branco no e-mail.
    """
    if not iso:
        return ""

    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return iso


def _ler_template() -> str | None:
    """O template do corpo, ou `None` com o motivo em log."""
    caminho = configuration.CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO

    if caminho is None:
        logger.error(
            "CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO não está configurada — a "
            "operadora NÃO será avisada dos arquivos recusados. Eles continuam "
            "na quarentena, com o diagnóstico ao lado."
        )
        return None

    if not caminho.is_file():
        logger.error(
            f"Template do e-mail não encontrado em [{caminho}] — a operadora NÃO "
            "será avisada dos arquivos recusados."
        )
        return None

    try:
        return caminho.read_text(encoding="utf-8")
    except OSError as erro:
        logger.error(f"Não foi possível ler o template [{caminho}]: {erro}")
        return None
