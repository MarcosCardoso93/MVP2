"""Argumentos de linha de comando — base comum dos RPAs do Detraf.

Acrescentado em 2026-08-06, para a homologação manual.

## O problema que isto resolve

Até aqui **não havia um único argumento** nos três `main.py`: o RPA 3 chamava
``GeracaoAgiController().gerar_artefatos()`` sem parâmetro algum, embora o
controller já aceitasse ``operadoras``, ``referencia``, ``raiz_operadoras`` e
``raiz_controle_ct``. Os parâmetros existiam e eram inalcançáveis.

Na prática, testar **uma** operadora ou repetir **um** mês exigia editar `.py` ou
reescrever o `.env` a cada rodada — e reescrever o `.env` durante a homologação é
como se esquece um kill-switch ligado.

## O contrato com o agendador não muda

``python main.py`` **sem argumento** continua fazendo exatamente o que fazia. As
agendas de produção não mudam. Tudo aqui é opcional, e existe para a pessoa que
está conduzindo o teste.

## Por que os argumentos são traduzidos para o ambiente

`comum.config.configuration` lê tudo no import e expõe constantes. Reler não é
opção — metade do repositório importa as constantes diretamente. Então os
argumentos que correspondem a variáveis são escritos em ``os.environ`` **antes**
de a configuração ser importada, e o resto do código não precisa saber que uma
linha de comando existiu.

É o mesmo mecanismo que os `main.py` já usavam para o ``NOME_RPA``.
"""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass, field

#: Kill-switches desligados pelo `--dry-run`. São todos os efeitos que saem da
#: máquina: e-mail à operadora (HU-15), e-mail de arquivo inválido (RPA 2),
#: carga no AGI (HU-17/18) e abertura do AGI (HU-20).
_KILL_SWITCHES = (
    "PERMITIR_ENVIO_EMAIL",
    "PERMITIR_UPLOAD_AGI",
    "PERMITIR_ACESSO_AGI",
    "NOTIFICAR_OPERADORA_ENVIAR",
    # Download da expectativa (RPA 2). Desligado, a etapa `expectativa` não
    # conecta e segue com o que já está na pasta — que é o modo de teste.
    "PERMITIR_DOWNLOAD_SFTP",
)

_PADRAO_REFERENCIA = re.compile(r"^\d{6}$")


@dataclass
class Argumentos:
    """O que a linha de comando pediu, já normalizado."""

    referencia: str | None = None
    operadoras: list[str] = field(default_factory=list)
    etapa: str | None = None
    pasta_entrada: str | None = None
    de_pasta: str | None = None
    dry_run: bool = False
    pausar: bool = False

    @property
    def houve_recorte(self) -> bool:
        """Se algo restringiu a execução — o que precisa constar do relatório."""
        return any(
            (self.referencia, self.operadoras, self.etapa, self.pasta_entrada,
             self.de_pasta, self.dry_run, self.pausar)
        )

    def descrever(self) -> list[str]:
        """Linhas legíveis para o log de arranque e o relatório de execução."""
        if not self.houve_recorte:
            return ["parâmetros: nenhum — execução completa, como na agenda"]

        partes = []
        if self.referencia:
            partes.append(f"referência forçada: {self.referencia}")
        if self.operadoras:
            partes.append(f"apenas as operadoras: {', '.join(self.operadoras)}")
        if self.etapa:
            partes.append(f"apenas a etapa: {self.etapa}")
        if self.pasta_entrada:
            partes.append(f"lendo da pasta: {self.pasta_entrada}")
        if self.de_pasta:
            partes.append(f"origem simulada em disco: {self.de_pasta}")
        if self.dry_run:
            partes.append("DRY-RUN: todos os efeitos externos desligados")
        if self.pausar:
            partes.append("PAUSA entre etapas ligada")
        return ["parâmetros: " + "; ".join(partes)]


def _validar_referencia(valor: str) -> str:
    if not _PADRAO_REFERENCIA.match(valor):
        raise argparse.ArgumentTypeError(
            f"'{valor}' não é uma referência válida. Use AAAAMM — por exemplo, "
            f"202507 para julho de 2025."
        )
    return valor


def construir_parser(
    robo: str,
    descricao: str,
    etapas: tuple[str, ...] = (),
    aceita_operadoras: bool = False,
    aceita_pasta_entrada: bool = False,
    aceita_de_pasta: bool = False,
) -> argparse.ArgumentParser:
    """
    Monta o parser de um robô, com os argumentos comuns mais os dele.

    O ``--help`` resultante é a documentação de invocação do robô — é o que
    alguém sem acesso a nada mais vai ler para saber o que dá para fazer.

    Args:
        robo: Nome exibido no `--help` (ex.: ``"RPA 3"``).
        descricao: Uma linha sobre o que o robô faz.
        etapas: Valores aceitos por ``--etapa``. Vazio omite o argumento.
        aceita_operadoras: Se o robô sabe filtrar por operadora.
        aceita_pasta_entrada: Se o robô sabe ler de uma pasta em vez do Outlook.
        aceita_de_pasta: Se o robô sabe simular a origem externa a partir de um
            diretório local — hoje só o RPA 2, para o SFTP da expectativa.
    """

    parser = argparse.ArgumentParser(
        prog=f"main.py ({robo})",
        description=(
            f"{descricao}\n\n"
            f"Sem argumento nenhum, roda exatamente como na agenda de produção. "
            f"Os argumentos abaixo existem para a homologação manual."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Antes da primeira execução, rode:\n"
            "    python verificar_ambiente.py\n"
            "Ele confere credenciais, pastas, permissões e banco, e diz o que "
            "corrigir em cada falha."
        ),
    )

    parser.add_argument(
        "--referencia",
        type=_validar_referencia,
        metavar="AAAAMM",
        help=(
            "Mês de tráfego a processar. Sem isto, usa o mês anterior ao "
            "corrente. Use para repetir um mês já fechado."
        ),
    )

    if aceita_operadoras:
        parser.add_argument(
            "--operadoras",
            metavar="NOME[,NOME...]",
            help=(
                "Processa somente estas operadoras, separadas por vírgula. "
                "O nome é o da pasta na árvore de operadoras."
            ),
        )

    if etapas:
        parser.add_argument(
            "--etapa",
            choices=etapas,
            help=(
                "Executa somente esta etapa. Sem isto, executa todas na ordem. "
                "Use para repetir a etapa que falhou sem refazer as anteriores."
            ),
        )

    if aceita_pasta_entrada:
        parser.add_argument(
            "--pasta-entrada",
            metavar="CAMINHO",
            help=(
                "Lê os arquivos desta pasta em vez de buscá-los no Outlook. "
                "Permite exercitar a identificação da operadora e o salvamento "
                "sem depender de perfil de e-mail configurado."
            ),
        )

    if aceita_de_pasta:
        parser.add_argument(
            "--de-pasta",
            metavar="CAMINHO",
            help=(
                "Lê os arquivos deste diretório como se viessem do SFTP, com os "
                "mesmos filtros e o mesmo destino. Permite exercitar a etapa "
                "inteira sem rede e sem credencial."
            ),
        )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Desliga TODOS os efeitos externos nesta execução, "
            "independentemente do .env: nenhum e-mail é enviado e o AGI não é "
            "tocado. Os arquivos locais continuam sendo gerados."
        ),
    )

    parser.add_argument(
        "--pausar",
        action="store_true",
        help=(
            "Abre uma caixa de diálogo ao fim de cada etapa, mostrando o que ela "
            "produziu, e espera a confirmação para seguir. SÓ funciona com "
            "ENV=dev e em sessão gráfica — em produção é ignorado."
        ),
    )

    parser.add_argument(
        "--log-nivel",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        metavar="NÍVEL",
        help=(
            "Nível do log só nesta execução (DEBUG, INFO, WARNING, ERROR). "
            "DEBUG registra cada imagem procurada no AGI e cada arquivo "
            "avaliado — é o que se liga quando algo falha sem explicação."
        ),
    )

    return parser


def aplicar(args: argparse.Namespace, nome_rpa: str) -> Argumentos:
    """
    Traduz os argumentos para variáveis de ambiente e devolve o recorte.

    **Precisa ser chamado antes de `comum.config.configuration` ser importado.**
    A configuração lê o ambiente uma vez, no import; depois disso, escrever em
    ``os.environ`` não tem efeito algum.

    Args:
        args: O `Namespace` devolvido pelo parser.
        nome_rpa: Valor de ``NOME_RPA`` — define o log e o sufixo por robô.

    Returns:
        `Argumentos` com o que não vira variável de ambiente (operadoras,
        etapa, pasta de entrada), para o `run()` do robô repassar ao controller.
    """

    os.environ.setdefault("NOME_RPA", nome_rpa)

    referencia = getattr(args, "referencia", None)
    if referencia:
        # A competência é o mês de REFERÊNCIA; o robô processa o anterior. Quem
        # digita `--referencia 202507` quer processar julho, então a competência
        # correspondente é agosto. `obter_competencia` já faz essa conta a
        # partir de `COMPETENCIA`, e é ela que o resto do código consulta.
        from datetime import datetime

        from dateutil.relativedelta import relativedelta

        mes = datetime.strptime(referencia, "%Y%m") + relativedelta(months=1)
        os.environ["COMPETENCIA"] = mes.strftime("%Y%m")
        # `DEBUG_ANO_MES_ATUAL` é sinônimo e tem precedência na configuração;
        # deixá-lo para trás faria um `.env` antigo vencer o argumento.
        os.environ.pop("DEBUG_ANO_MES_ATUAL", None)

    nivel = getattr(args, "log_nivel", None)
    if nivel:
        os.environ["LOG_LEVEL"] = nivel
        # O sufixo por robô venceria o valor geral e anularia o argumento.
        os.environ.pop(f"LOG_LEVEL_{nome_rpa.split('_')[0].upper()}", None)

    pasta_entrada = getattr(args, "pasta_entrada", None)
    if pasta_entrada:
        # `ProcessamentoService.executar(None)` lê `configuration.DIRETORIO_ENTRADA`.
        # Apontá-la aqui é o que faz o modo sem Outlook ler da pasta certa.
        os.environ["DIRETORIO_ENTRADA"] = pasta_entrada
        os.environ.pop(f"DIRETORIO_ENTRADA_{nome_rpa.split('_')[0].upper()}", None)

    if getattr(args, "pausar", False):
        os.environ["PAUSA_ENTRE_ETAPAS"] = "true"
        os.environ.pop(f"PAUSA_ENTRE_ETAPAS_{nome_rpa.split('_')[0].upper()}", None)

    if getattr(args, "dry_run", False):
        sufixo = nome_rpa.split("_")[0].upper()
        for variavel in _KILL_SWITCHES:
            os.environ[variavel] = "false"
            os.environ.pop(f"{variavel}_{sufixo}", None)

    operadoras = [
        nome.strip()
        for nome in (getattr(args, "operadoras", None) or "").split(",")
        if nome.strip()
    ]

    return Argumentos(
        referencia=referencia,
        operadoras=operadoras,
        etapa=getattr(args, "etapa", None),
        pasta_entrada=getattr(args, "pasta_entrada", None),
        # Vai por argumento até o robô, e não para `os.environ` como o
        # `--pasta-entrada`: aquele reescreve `DIRETORIO_ENTRADA`, que é
        # configuração; este é um recorte da execução, e não muda config nenhuma.
        de_pasta=getattr(args, "de_pasta", None),
        dry_run=bool(getattr(args, "dry_run", False)),
        pausar=bool(getattr(args, "pausar", False)),
    )
