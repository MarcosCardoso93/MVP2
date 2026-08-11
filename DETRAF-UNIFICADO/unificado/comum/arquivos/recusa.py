"""Registro em arquivo da recusa de um Detraf por layout (2026-08-06).

O diagnóstico do layout já era bom — posição, o que se esperava, o que se
encontrou e a proporção de valores válidos. O problema é **onde** ele ficava: só
no log, misturado a tudo o que o robô registrou naquele dia.

Numa homologação manual, a pergunta é sempre a mesma: *por que este arquivo foi
recusado?* Respondê-la exigia abrir o `.log` do dia e procurar pelo nome do
arquivo. Agora o diagnóstico fica **ao lado do próprio arquivo**, num `.md` com o
mesmo nome — e com duas linhas de exemplo do conteúdo, que é o que permite
decidir, sem abrir nada mais, se o errado é o arquivo ou o código.

O log continua recebendo tudo. Este arquivo é adicional, e a falha ao gravá-lo
nunca derruba a validação: um diagnóstico que não pôde ser salvo é menos grave do
que a apuração inteira parar.

Subiu para `comum/` em 2026-08-06, quando o RPA 1 passou a recusar arquivos na
captura — e, com ele, a recusa deixou de vir só do layout: as regras de coluna
também a produzem. Daí o `Diagnostico`, que é a forma comum das duas.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from comum.config.logger_config import logger
from comum.dominio.diagnostico_de_recusa import Diagnostico

#: Sufixo do arquivo de diagnóstico. Fica junto do arquivo recusado, e não numa
#: pasta de relatórios: quem está olhando o arquivo já está na pasta certa.
SUFIXO_RECUSA = "_RECUSADO.md"

#: Quantas linhas do arquivo entram no diagnóstico. Duas bastam para reconhecer
#: um layout, e mais do que isso arriscaria copiar dado da operadora para um
#: arquivo que ninguém sabe que existe.
LINHAS_DE_EXEMPLO = 2


def registrar_recusa(
    caminho_arquivo: Path, resultado, df: pd.DataFrame | None
) -> Path | None:
    """
    Grava o diagnóstico da recusa ao lado do arquivo.

    Args:
        caminho_arquivo: O arquivo recusado.
        resultado: Um `Diagnostico`, ou qualquer resultado que saiba produzir um
            (`ResultadoLayout`, `ResultadoColunas`) pelo método `.diagnostico()`.
        df: O conteúdo lido, para as linhas de exemplo. Pode ser `None`.

    Returns:
        O caminho gravado, ou `None` se não foi possível gravar — nunca levanta.
    """

    diagnostico = resultado if isinstance(resultado, Diagnostico) else resultado.diagnostico()
    destino = caminho_arquivo.with_name(caminho_arquivo.stem + SUFIXO_RECUSA)

    try:
        destino.write_text(_montar(caminho_arquivo, diagnostico, df), encoding="utf-8")
    except OSError as erro:
        # Não derruba a validação. Perder o diagnóstico é menos grave do que
        # parar a apuração do mês por falta de permissão numa pasta.
        logger.warning(
            f"[Layout] Não foi possível gravar o diagnóstico da recusa em "
            f"[{destino}]: {erro}. O motivo continua no log."
        )
        return None

    logger.info(f"[Layout] Motivo da recusa gravado em [{destino.name}].")
    return destino


def _montar(caminho_arquivo: Path, resultado: Diagnostico, df: pd.DataFrame | None) -> str:
    linhas = [
        f"# Arquivo recusado — {caminho_arquivo.name}",
        "",
        f"**Pasta:** `{caminho_arquivo.parent}`",
        f"**Colunas encontradas:** {resultado.total_colunas}",
        "",
        "## Por que foi recusado",
        "",
    ]

    if resultado.motivo:
        linhas += [resultado.motivo, ""]

    # Recusa por regra de coluna: o arquivo tem a forma certa, mas há valor fora
    # da regra. A tabela de posições abaixo não se aplica — ela descreve layout.
    if resultado.motivos_por_regra:
        linhas += [f"- {motivo}" for motivo in resultado.motivos_por_regra]
        linhas.append("")

    if resultado.divergencias:
        linhas += [
            "| Posição | Campo | Esperado | Encontrado | Válidos |",
            "|---|---|---|---|---|",
        ]
        for divergencia in resultado.divergencias:
            exemplos = ", ".join(
                f"`{valor}`" for valor in divergencia.exemplos_encontrados
            )
            linhas.append(
                f"| {divergencia.indice} | {divergencia.nome} | "
                f"{divergencia.esperado} | {exemplos or '(vazio)'} | "
                f"{divergencia.valores_validos}/{divergencia.valores_avaliados} |"
            )
        linhas.append("")

    linhas += _amostra(df)
    linhas += [
        "## O que fazer",
        "",
        "1. Compare a tabela acima com o arquivo. Se as posições estiverem",
        "   deslocadas, o arquivo veio noutro layout — é a operadora que precisa",
        "   reenviar.",
        "2. Se as posições batem e mesmo assim foi recusado, o problema é de",
        "   **formato de valor** (decimal, data, zero à esquerda). Guarde este",
        "   arquivo: ele é a evidência.",
        "3. A validação é **posicional** e ignora os nomes das colunas — os nomes",
        "   reais variam por operadora e não servem de critério (decisão do",
        "   cliente, 2026-07-31).",
        "",
        "> ⚠️ **Se este for um arquivo de expectativa Vivo**, a recusa pode ser a",
        "> pendência **N3**: a V2 manda o layout valer para os dois tipos de",
        "> arquivo (¶149) e exige a coluna `R$ Bruto` (¶443), mas o arquivo real",
        "> termina em `VALOR_LIQUIDO`. É contradição entre a especificação e o",
        "> arquivo, não defeito do robô — ver `pendencias-para-o-cliente.md`.",
    ]

    return "\n".join(linhas) + "\n"


def _amostra(df: pd.DataFrame | None) -> list[str]:
    """As primeiras linhas do arquivo, para reconhecer o layout de relance."""

    if df is None or df.empty:
        return ["## Conteúdo", "", "O arquivo está vazio ou não pôde ser lido.", ""]

    linhas = ["## Primeiras linhas do arquivo", "", "```"]
    for _, linha in df.head(LINHAS_DE_EXEMPLO).iterrows():
        linhas.append(";".join(str(valor) for valor in linha.tolist()))
    linhas += ["```", ""]
    return linhas
