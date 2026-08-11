"""Serviço da HU-15 — envio do e-mail de contestação à operadora.

Origem: `projeto-5-h15/src/services/Contestacao/Envio_Email_Contestacao.py`.
Ver `trabalho/inventarios/inventario-projeto-5.md`.

Critérios de aceite (V2):

- destinatários vindos da tabela de contatos do WebFat;
- assunto ``CONTESTAÇÃO_TBRA|{operadora}_{mês}``;
- anexos: as cartas CT e o arquivo ``_ENV`` — produzidos pela HU-14
  (`geracao_env_carta.py`), na pasta ``Contestações`` da operadora;
- disparo automático após a sinalização do analista, **sem** aprovação manual.

## O que mudou na migração

O original varria ``DIRETORIO_CONTESTACOES`` como pasta **plana**, filtrando por
substring do nome. Aqui os anexos vêm de `comum/arquivos/estrutura_pastas.py`
(`{operadora}/{ano}/{aaaamm}/Contestações/`) e o ``_ENV`` é localizado pelo nome
exato que a HU-14 grava (`nomenclatura.nome_env`), não por heurística. Era a
terceira ocorrência do mesmo desvio de caminho — as anteriores foram o contrato
RPA 1 → RPA 2 e o P7.

O envio em si é da camada comum (`comum/integracoes/outlook.py`), que absorveu o
``outlook_standalone_original.py`` de 1.191 linhas do P5.

## O que continua pendente

Duas pontas dependem do banco e **não executam**:

- `buscar_destinatarios` — a "tabela de contatos do WebFat" é citada na V2 sem
  nome de tabela nem de coluna. É a pendência **Q16**, ainda aberta com o cliente.
  Desde 2026-08-05 há uma **ponte**: os contatos podem vir de um CSV apontado por
  ``CAMINHO_CONTATOS_OPERADORAS``. ⚠️ Com esse arquivo preenchido **e**
  ``PERMITIR_ENVIO_EMAIL=true``, o robô passa a enviar de verdade — o kill-switch
  é a única proteção que sobra.
- `buscar_contestacoes_sinalizadas` — falta a coluna que marca "e-mail já
  enviado", para não reenviar.

⚠️ O TODO do original dizia que *"não existe hoje nenhuma tabela/coluna mapeada"*
para o gatilho do analista. **Isso está desatualizado:** o gatilho é
``tipo_contestacao`` de ``tbl_rpa_log_detraf_despesa_contestacao``, e
`comum/dados/repositorio_tabelas.py::obter_tipo_contestacao` já o lê. O que falta
é só o controle de reenvio.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from comum.arquivos import estrutura_pastas as ep
from comum.arquivos import nomenclatura as nom
from comum.config import configuration
from comum.config import constantes as const
from comum.config.logger_config import logger
from comum.utils.decoradores import log_execucao

# Texto exato da V2 (parágrafos 278-283).
CORPO_EMAIL_TEMPLATE = """Prezados,

Segue a contestação para a sua análise e validação, referente ao mês {mes}

Att,
"""


#: Linha do CSV de contatos cujo conteúdo entra em cópia em **todos** os envios.
#:
#: Existe porque o e-mail real do processo (print embutido no `.docx`) tem em Cc
#: um endereço que **não é da operadora** e se repete em todos os envios.
COPIA_FIXA = "*"


class EnvioEmailContestacaoIncompleto(RuntimeError):
    """Faltou algo para enviar: destinatário, carta ou `_ENV`."""


def montar_assunto(operadora: str, mes: str) -> str:
    """``CONTESTAÇÃO_TBRA|{operadora}_{mês}`` — critério de aceite da HU-15."""

    return f"CONTESTAÇÃO_TBRA|{operadora}_{mes}"


def montar_corpo(mes: str) -> str:
    """Corpo do e-mail, com o texto literal da V2."""

    return CORPO_EMAIL_TEMPLATE.format(mes=mes)


def localizar_anexos(
    operadora: str,
    aaaamm: str,
    raiz_operadoras: Path | None = None,
) -> tuple[list[Path], Optional[Path]]:
    """
    Localiza a carta CT e o ``_ENV`` da operadora no mês, na pasta ``Contestações``.

    O ``_ENV`` tem nome determinístico (`nomenclatura.nome_env`). O das cartas
    depende do número CT sequencial, que só é conhecido depois da HU-14 — por isso
    são procuradas por prefixo (``CT - ...``).

    **Mais de uma carta é normal desde a Q25 (2026-08-05):** a operadora com
    linhas COM e SEM retenção no mesmo mês recebe uma carta por cenário, cada uma
    com o seu número CT, e **todas** vão anexadas. Antes disso o código pegava só
    a mais recente e avisava que "a HU-14 rodou duas vezes" — o que passou a ser
    falso.

    O ``_ENV`` **continua único** (decisão de desenho registrada junto com a
    Q25): o nome dele não tem cenário, e ele é o anexo de dados da contestação
    inteira.

    Returns:
        ``(cartas, caminho_env)`` — lista possivelmente vazia e `None` se o `_ENV`
        não for encontrado. As cartas saem ordenadas por número CT.
    """

    pasta = ep.caminho_contestacoes(operadora, aaaamm, raiz_operadoras)
    if not pasta.is_dir():
        logger.warning(
            f"[HU-15] Pasta de contestações não encontrada para "
            f"{operadora}/{aaaamm}: [{pasta}]."
        )
        return [], None

    caminho_env = pasta / f"{nom.nome_env(operadora, aaaamm)}{const.EXTENSAO_EXCEL}"
    if not caminho_env.is_file():
        logger.warning(f"[HU-15] Arquivo _ENV não encontrado: [{caminho_env}].")
        caminho_env = None

    cartas = sorted(pasta.glob(f"{const.PREFIXO_CARTA}*{const.EXTENSAO_DOCX}"))
    if not cartas:
        logger.warning(f"[HU-15] Carta CT não encontrada em [{pasta}].")
    elif len(cartas) > 1:
        logger.info(
            f"[HU-15] {len(cartas)} cartas para {operadora}/{aaaamm} — uma por "
            f"cenário de contestação (Q25). Todas vão anexadas: "
            f"{[carta.name for carta in cartas]}."
        )

    return cartas, caminho_env


@dataclass(frozen=True)
class Destinatarios:
    """Para quem o e-mail vai — separando **Para** de **Cc**."""

    para: list[str] = field(default_factory=list)
    copia: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        """Sem ninguém em `Para`, não há e-mail a enviar. Só Cc não basta."""
        return bool(self.para)


def buscar_destinatarios(operadora: str) -> Destinatarios:
    """
    Contatos da operadora para o envio da contestação.

    **Ponte decidida em 2026-08-05 (Q16).** A V2 (parágrafo 136) cita "a tabela de
    contatos do WebFat" sem dar nome de tabela nem de coluna, e nenhum dos sete
    projetos de origem chegou a consultá-la — a pergunta continua aberta com o
    cliente. Até a tabela existir, os contatos vêm de um arquivo apontado por
    ``CAMINHO_CONTATOS_OPERADORAS``.

    ## O formato veio do processo real (2026-08-05)

    Um print do e-mail de contestação em composição, embutido no `.docx`
    normativo, mostrou como isso é feito hoje à mão — e que a primeira versão
    desta ponte não daria conta:

    - **dois ou mais destinatários** por operadora;
    - **Cc além do Para**, e não a mesma coisa;
    - **um endereço em cópia que não é da operadora**, repetido em todos os
      envios — cópia fixa do processo.

    Formato (CSV, ``;``, uma operadora por linha, cabeçalho opcional)::

        operadora;para;cc
        CLARO;contestacao@claro.com.br,fiscal@claro.com.br;gestor@claro.com.br
        TIM;interconexao@tim.com.br;
        *;;atacado@exemplo.com.br

    A linha ``*`` é a **cópia fixa**: o que estiver nela entra em Cc de **todos**
    os envios. É a forma de expressar o endereço interno que aparece em cópia em
    todo e-mail do processo.

    ⚠️ **Compatível com o formato anterior** (``operadora;emails``): uma linha
    com uma coluna só de e-mails continua sendo lida como `Para`.

    A busca é **case-insensitive** e ignora espaços — o nome da operadora vem da
    pasta no compartilhamento, e a grafia varia.

    Sem o arquivo configurado, sem a operadora nele ou sem endereço em `Para`, o
    comportamento anterior se mantém: `enviar_contestacao` recusa o envio em vez
    de mandar e-mail para lugar nenhum.

    Quando a tabela do WebFat for informada, o que muda é **o corpo desta
    função** — por isso a leitura fica isolada aqui.
    """

    caminho = configuration.CAMINHO_CONTATOS_OPERADORAS

    if caminho is None:
        logger.warning(
            f"[HU-15] Contatos de '{operadora}' indisponíveis: a tabela de contatos "
            f"do WebFat ainda não foi informada pelo cliente (pendência Q16), e "
            f"CAMINHO_CONTATOS_OPERADORAS não está configurado."
        )
        return Destinatarios()

    if not Path(caminho).is_file():
        logger.error(
            f"[HU-15] Arquivo de contatos não encontrado em [{caminho}]. Nenhum "
            f"e-mail será enviado — confira CAMINHO_CONTATOS_OPERADORAS."
        )
        return Destinatarios()

    try:
        contatos = _ler_contatos(Path(caminho))
    except OSError as erro:
        logger.excecao(f"[HU-15] Falha ao ler o arquivo de contatos [{caminho}]: {erro}")
        return Destinatarios()

    da_operadora = contatos.get(operadora.strip().casefold(), Destinatarios())
    copia_fixa = contatos.get(COPIA_FIXA, Destinatarios())

    # A cópia fixa entra em Cc mesmo quando ela foi escrita na coluna `para` —
    # quem edita o arquivo à mão vai pôr o endereço onde parecer natural, e o
    # sentido dela é sempre "em cópia".
    copia = _sem_repetir(
        da_operadora.copia + copia_fixa.para + copia_fixa.copia, exceto=da_operadora.para
    )

    if not da_operadora.para:
        logger.warning(
            f"[HU-15] '{operadora}' não tem destinatário em [{caminho}]. O e-mail "
            f"da contestação não será enviado (pendência Q16)."
        )
        return Destinatarios()

    logger.info(
        f"[HU-15] {operadora}: {len(da_operadora.para)} destinatário(s), "
        f"{len(copia)} em cópia."
    )
    return Destinatarios(para=list(da_operadora.para), copia=copia)


def _sem_repetir(emails: list[str], exceto: list[str]) -> list[str]:
    """Remove duplicatas e quem já está em `Para`, preservando a ordem."""

    ja_vistos = {email.casefold() for email in exceto}
    resultado = []
    for email in emails:
        if email.casefold() not in ja_vistos:
            ja_vistos.add(email.casefold())
            resultado.append(email)
    return resultado


def _ler_contatos(caminho: Path) -> dict[str, Destinatarios]:
    """
    Lê o CSV de contatos como ``{operadora normalizada: Destinatarios}``.

    Linha em branco, comentário (``#``) e o cabeçalho são ignorados — o arquivo é
    editado à mão por quem opera, e é o tipo de coisa que ganha comentário.
    """

    contatos: dict[str, Destinatarios] = {}

    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        for linha in csv.reader(arquivo, delimiter=";"):
            if not linha or not linha[0].strip() or linha[0].lstrip().startswith("#"):
                continue

            nome = linha[0].strip()
            if nome.casefold() == "operadora":
                continue

            para = _separar(linha[1] if len(linha) > 1 else "")
            # Tudo depois da terceira coluna também é Cc: quem edita à mão pode
            # separar endereços com `;` em vez de `,`, e engolir isso em silêncio
            # perderia destinatário.
            copia = _separar(",".join(linha[2:])) if len(linha) > 2 else []

            chave = COPIA_FIXA if nome == COPIA_FIXA else nome.casefold()
            anterior = contatos.get(chave, Destinatarios())
            contatos[chave] = Destinatarios(
                para=list(anterior.para) + para,
                copia=list(anterior.copia) + copia,
            )

    return contatos


def _separar(campo: str) -> list[str]:
    """Divide um campo de e-mails separados por vírgula."""

    return [email.strip() for email in campo.split(",") if email.strip()]


def buscar_contestacoes_sinalizadas() -> list[dict]:
    """
    Contestações que o analista já sinalizou e que ainda não tiveram e-mail enviado.

    ⛔ **Parcialmente bloqueado.** O gatilho existe e já é legível — é
    ``tipo_contestacao`` em ``tbl_rpa_log_detraf_despesa_contestacao``, via
    `bd_tabelas.obter_tipo_contestacao`. O que falta é a **coluna de controle de
    reenvio**: sem ela, uma segunda execução reenviaria tudo o que já foi enviado.
    Por isso devolve lista vazia — reenviar é pior do que não enviar.

    Returns:
        Lista de dicts ``{"operadora", "mes"}``.
    """

    logger.warning(
        "[HU-15] Busca de contestações sinalizadas ainda não ligada: falta a coluna "
        "que marca o e-mail como enviado, sem a qual não há proteção contra reenvio."
    )
    return []


@log_execucao
def enviar_contestacao(
    operadora: str,
    aaaamm: str,
    servico_outlook,
    raiz_operadoras: Path | None = None,
) -> None:
    """
    Monta e envia o e-mail de contestação de uma operadora no mês.

    Respeita `configuration.PERMITIR_ENVIO_EMAIL`: com o kill-switch desligado
    (o default), tudo é montado e registrado no log, e nada é enviado. É o que
    permite exercitar o fluxo sem disparar e-mail para a operadora.

    Args:
        operadora: Nome da operadora.
        aaaamm: Mês de referência.
        servico_outlook: `comum.integracoes.outlook.OutlookService` já conectado.
        raiz_operadoras: Raiz alternativa, para teste.

    Raises:
        EnvioEmailContestacaoIncompleto: Sem destinatário, sem carta ou sem `_ENV`.
    """

    destinatarios = buscar_destinatarios(operadora)
    cartas, caminho_env = localizar_anexos(operadora, aaaamm, raiz_operadoras)

    faltando = []
    if not destinatarios:
        faltando.append("destinatários")
    if not cartas:
        faltando.append("carta CT")
    if caminho_env is None:
        faltando.append("arquivo _ENV")
    if faltando:
        raise EnvioEmailContestacaoIncompleto(
            f"E-mail de contestação de {operadora}/{aaaamm} não enviado — "
            f"faltou: {', '.join(faltando)}."
        )

    assunto = montar_assunto(operadora, aaaamm)
    # As cartas primeiro, o `_ENV` por último — é a ordem em que a operadora lê:
    # o documento que explica a contestação, depois os dados que a sustentam.
    anexos = [*cartas, caminho_env]

    if not configuration.PERMITIR_ENVIO_EMAIL:
        logger.info(
            f"[MODO SEGURO] PERMITIR_ENVIO_EMAIL=false — e-mail montado e não enviado: "
            f"'{assunto}' para {destinatarios.para}"
            + (f", em cópia {destinatarios.copia}" if destinatarios.copia else "")
            + f", anexos {[anexo.name for anexo in anexos]}."
        )
        return

    servico_outlook.send_email_com_anexos(
        to=destinatarios.para,
        subject=assunto,
        body=montar_corpo(aaaamm),
        anexos=anexos,
        cc=destinatarios.copia or None,
    )
    logger.info(
        f"[HU-15] Contestação de {operadora}/{aaaamm} enviada para "
        f"{destinatarios.para}"
        + (f", em cópia {destinatarios.copia}" if destinatarios.copia else "")
        + "."
    )
