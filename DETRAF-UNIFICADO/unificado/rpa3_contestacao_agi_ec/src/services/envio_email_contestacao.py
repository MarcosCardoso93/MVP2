"""Serviço da HU-15 — envio do e-mail de contestação à operadora.

Origem: `projeto-5-h15/src/services/Contestacao/Envio_Email_Contestacao.py`.
Ver `trabalho/inventarios/inventario-projeto-5.md`.

Critérios de aceite (V2):

- destinatários vindos da tabela de contatos do WebFat;
- assunto ``CONTESTAÇÃO_TBRA|{operadora}_{mês}``;
- anexos: as cartas CT e o arquivo ``_EXP`` — produzidos pela HU-14
  (`geracao_env_carta.py`), na pasta ``Contestações`` da operadora;
- disparo automático após a sinalização do analista, **sem** aprovação manual.

## O que mudou na migração

O original varria ``DIRETORIO_CONTESTACOES`` como pasta **plana**, filtrando por
substring do nome. Aqui os anexos vêm de `comum/arquivos/estrutura_pastas.py`
(`{operadora}/{ano}/{aaaamm}/Contestações/`) e o ``_EXP`` é localizado pelo nome
exato que a HU-14 grava (`nomenclatura.nome_env`), não por heurística. Era a
terceira ocorrência do mesmo desvio de caminho — as anteriores foram o contrato
RPA 1 → RPA 2 e o P7.

O envio em si é da camada comum (`comum/integracoes/outlook.py`), que absorveu o
``outlook_standalone_original.py`` de 1.191 linhas do P5.

## O que continua pendente

Uma ponta depende do banco e **não executa**:

- `buscar_contestacoes_sinalizadas` — falta a coluna que marca "e-mail já
  enviado", para não reenviar.

`buscar_destinatarios` **não é mais pendência**: a Q16 foi resolvida pelo
cliente em 2026-08-18 — a "tabela de contatos do WebFat" citada na V2 é
``tbl_detraf_destinatarios``. Os contatos por operadora vêm de lá agora
(`comum.dados.repositorio_tabelas.bd_tabelas.obter_contatos_operadora`). O CSV
que servia de ponte (``CAMINHO_CONTATOS_OPERADORAS``) continua opcional só para
a **cópia fixa** — ver `_copia_fixa`, abaixo.

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
from comum.dados.repositorio_tabelas import bd_tabelas
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
    """Faltou algo para enviar: destinatário, carta ou `_EXP`."""


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
    Localiza a carta CT e o ``_EXP`` da operadora no mês, na pasta ``Contestações``.

    O ``_EXP`` tem nome determinístico (`nomenclatura.nome_env`). O das cartas
    depende do número CT sequencial, que só é conhecido depois da HU-14 — por isso
    são procuradas por prefixo (``CT - ...``).

    **Mais de uma carta é normal desde a Q25 (2026-08-05):** a operadora com
    linhas COM e SEM retenção no mesmo mês recebe uma carta por cenário, cada uma
    com o seu número CT, e **todas** vão anexadas. Antes disso o código pegava só
    a mais recente e avisava que "a HU-14 rodou duas vezes" — o que passou a ser
    falso.

    O ``_EXP`` **continua único** (decisão de desenho registrada junto com a
    Q25): o nome dele não tem cenário, e ele é o anexo de dados da contestação
    inteira.

    Returns:
        ``(cartas, caminho_env)`` — lista possivelmente vazia e `None` se o `_EXP`
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
        logger.warning(f"[HU-15] Arquivo _EXP não encontrado: [{caminho_env}].")
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

    **Q16 resolvida em 2026-08-18.** A V2 (parágrafo 136) cita "a tabela de
    contatos do WebFat" sem dar nome — o cliente confirmou que é
    ``tbl_detraf_destinatarios``, filtrada por ``produto = 'Detraf'`` (a tabela
    serve outros produtos do WebFat também). A consulta mora em
    `comum.dados.repositorio_tabelas.RepositorioTabelas.obter_contatos_operadora`,
    reaproveitável por qualquer RPA — esta função só traduz o resultado para
    `Destinatarios` e soma a cópia fixa.

    ## Cópia fixa — o que a tabela não modela

    Um print do e-mail de contestação em composição, embutido no `.docx`
    normativo, mostrou um endereço em Cc que **não é da operadora** e se repete
    em todos os envios — cópia fixa do processo. `tbl_detraf_destinatarios` não
    tem uma linha equivalente (ela é só ``{operadora, email, tipo}``), então essa
    parte **continua** vindo do CSV opcional de ``CAMINHO_CONTATOS_OPERADORAS``,
    linha ``*`` — ver `_copia_fixa`. Sem o arquivo configurado, o e-mail sai
    normalmente, só sem essa cópia extra.

    Sem destinatário em `Para` (operadora ausente da tabela, ou só com linhas
    `CC`), `enviar_contestacao` recusa o envio em vez de mandar e-mail para
    lugar nenhum.
    """

    contatos = bd_tabelas.obter_contatos_operadora(operadora)
    para = contatos["para"]

    if not para:
        logger.warning(
            f"[HU-15] '{operadora}' não tem destinatário em Para em "
            f"tbl_detraf_destinatarios (produto Detraf). O e-mail da "
            f"contestação não será enviado."
        )
        return Destinatarios()

    copia = _sem_repetir(contatos["copia"] + _copia_fixa(), exceto=para)

    logger.info(
        f"[HU-15] {operadora}: {len(para)} destinatário(s), {len(copia)} em cópia."
    )
    return Destinatarios(para=list(para), copia=copia)


def _copia_fixa() -> list[str]:
    """
    Endereço(s) que entram em Cc de **todo** envio — não modelado em
    ``tbl_detraf_destinatarios`` (ver docstring de `buscar_destinatarios`).

    Opcional: só existe se ``CAMINHO_CONTATOS_OPERADORAS`` continuar apontando
    para um CSV com a linha ``*;;email`` (formato de `_ler_contatos`). Sem o
    arquivo configurado, devolve lista vazia sem erro — a cópia fixa é um
    extra, não um requisito para o envio principal funcionar.
    """
    caminho = configuration.CAMINHO_CONTATOS_OPERADORAS
    if caminho is None:
        return []

    if not Path(caminho).is_file():
        logger.warning(
            f"[HU-15] CAMINHO_CONTATOS_OPERADORAS aponta para [{caminho}], que "
            f"não existe — cópia fixa não aplicada nesta execução."
        )
        return []

    try:
        contatos = _ler_contatos(Path(caminho))
    except OSError as erro:
        logger.warning(f"[HU-15] Falha ao ler a cópia fixa em [{caminho}]: {erro}")
        return []

    fixa = contatos.get(COPIA_FIXA, Destinatarios())
    return list(fixa.para) + list(fixa.copia)


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
        EnvioEmailContestacaoIncompleto: Sem destinatário, sem carta ou sem `_EXP`.
    """

    destinatarios = buscar_destinatarios(operadora)
    cartas, caminho_env = localizar_anexos(operadora, aaaamm, raiz_operadoras)

    faltando = []
    if not destinatarios:
        faltando.append("destinatários")
    if not cartas:
        faltando.append("carta CT")
    if caminho_env is None:
        faltando.append("arquivo _EXP")
    if faltando:
        raise EnvioEmailContestacaoIncompleto(
            f"E-mail de contestação de {operadora}/{aaaamm} não enviado — "
            f"faltou: {', '.join(faltando)}."
        )

    assunto = montar_assunto(operadora, aaaamm)
    # As cartas primeiro, o `_EXP` por último — é a ordem em que a operadora lê:
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
