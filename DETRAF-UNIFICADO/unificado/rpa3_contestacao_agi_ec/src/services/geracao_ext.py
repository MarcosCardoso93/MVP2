"""Serviço da HU-12 — geração do arquivo EXT para carga AGI (todos os cenários).

Fonte de regra: `AI/09-Regras-Negocio-Epico4.md` §2. Objetivo: montar
`DE_AGI_D_{aaaamm}_TBRA_X_{OPERADORA}_EXT` a partir do Detraf consolidado da operadora
(T-020), preenchendo `ORIGEM`, `EXPECTATIVA`, `INSERÇÃO`, `AJUSTE`, `OBS` e `REMUNERACAO`,
e gravando na pasta `AGI` da operadora.

**Gap registrado (não bloqueia — ver `TODO/decisoes.md`):** não existe no repositório um
arquivo-modelo EXT real para "abrir e colar a partir de A2" (AI/09 §2 passo 1-2). O
conteúdo e a nomenclatura são 100% documentados; a tarefa grava um `.xlsx` novo (com
cabeçalho) em vez de popular um template pré-existente. Formatação/estilo do template real
ficam para quando o modelo chegar.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from comum.config import constantes as const
from comum.config.logger_config import logger
from src.services import mapa_remuneracao as mr
from comum.arquivos import estrutura_pastas as ep
from comum.arquivos import gerenciador as ga
from comum.arquivos import nomenclatura as nom
from comum.utils.decoradores import log_execucao

# Nomes das colunas extras preenchidas pelo robô (AI/09 §2 passo 3), na ordem documentada.
COL_ORIGEM = "ORIGEM"
COL_EXPECTATIVA = "EXPECTATIVA"
COL_INSERCAO = "INSERÇÃO"
COL_AJUSTE = "AJUSTE"
COL_OBS = "OBS"
COL_REMUNERACAO = "REMUNERACAO"


def eh_com_retencao(valor_contestacao: Optional[str]) -> bool:
    """
    Indica se o sinal de contestação (T-024/D-6) representa **COM retenção**.

    Comparação case-insensitive; qualquer valor que não contenha "retenção" sem também
    conter "sem" (`None`, `"sem retenção"`, texto inesperado) retorna `False`. Reutilizada
    por `geracao_ext` (EXPECTATIVA) e `geracao_int` (filtro de linhas — HU-13 só existe
    neste cenário).
    """

    if not valor_contestacao:
        return False

    normalizado = str(valor_contestacao).strip().lower()
    return "retenção" in normalizado and "sem" not in normalizado


def _resolver_expectativa(valor_contestacao: Optional[str]) -> str:
    """
    Traduz o sinal de contestação (T-024/D-6) para `EXPECTATIVA` do EXT.

    `"S"` apenas quando o valor indica **COM retenção**; qualquer outro caso — `None`
    (sem contestação), `"sem retenção"` ou valor inesperado — vira `"N"` (AI/09 §2: "S para
    linhas contestadas COM retenção; N para as não contestadas ou contestadas SEM retenção").
    """

    if eh_com_retencao(valor_contestacao):
        return const.EXPECTATIVA_SIM

    return const.EXPECTATIVA_NAO


@log_execucao
def montar_linhas_ext(
    df_operadora: pd.DataFrame,
    indice_descritor: int,
    indice_remuneracao: dict[str, list[str]],
    obter_tipo_contestacao: Callable[[str, str, str, str, str], Optional[str]],
    indice_credora: int = const.COL_CREDORA,
    indice_devedora: int = const.COL_DEVEDORA,
    indice_referencia: int = const.COL_REFERENCIA,
    indice_trafego: int = const.COL_TRAFEGO,
) -> pd.DataFrame:
    """
    Monta o conteúdo do EXT (T-040/T-041/T-042): consolidado + colunas extras.

    **Todas as linhas são preservadas** (ao contrário do `Contest`, T-023) — o EXT cobre
    todos os cenários, inclusive "sem contestação". Descritor não mapeado/ambíguo resulta
    em `REMUNERACAO` vazia para aquela linha, nunca em descarte.

    Args:
        df_operadora: Consolidado da operadora (T-020), até `R$_Bruto`, sem linhas de total.
        indice_descritor: Índice (0-based) da coluna de descritor — sem posição fixa na
            documentação, deve ser informado pelo chamador (mesma razão de `montar_contest`).
        indice_remuneracao: Índice `descritor final -> [remunerações]` (D-5).
        obter_tipo_contestacao: Callable injetada (via repository/controller — o service
            não acessa banco, AI/01 §1) que resolve o sinal COM/SEM retenção por
            `(eot_operadora, eot_tbra, referencia, trafego, remuneracao)` (T-024/D-6; a
            remuneração entra na chave desde 2026-07-28 — o sinal pode variar por
            remuneração dentro do mesmo par de EOT). Retorna `None` quando não há
            sinalização (sem contestação).
        indice_credora, indice_devedora, indice_referencia, indice_trafego: Índices
            documentados (D-8) usados para consultar o sinal de contestação por linha.

    Returns:
        Cópia de `df_operadora` com as colunas extras `REMUNERACAO`, `ORIGEM`,
        `EXPECTATIVA`, `INSERÇÃO`, `AJUSTE`, `OBS` anexadas ao final, na ordem documentada.
    """

    if df_operadora.empty:
        return df_operadora.copy()

    linhas = df_operadora.copy()

    linhas[COL_REMUNERACAO] = mr.resolver_series(
        linhas.iloc[:, indice_descritor], indice_remuneracao
    )

    # Resolve o sinal de contestação uma vez por combinação única (evita repetir a
    # consulta para cada linha do mesmo grupo EOT/referência/tráfego/remuneração).
    chaves = pd.concat(
        [
            linhas.iloc[:, [indice_credora, indice_devedora, indice_referencia, indice_trafego]]
            .astype(str)
            .reset_index(drop=True),
            linhas[COL_REMUNERACAO].astype(str).reset_index(drop=True),
        ],
        axis=1,
    )
    combinacoes_unicas = chaves.drop_duplicates()

    mapa_expectativa: dict[tuple, str] = {}
    for _, linha_chave in combinacoes_unicas.iterrows():
        credora, devedora, referencia, trafego, remuneracao = linha_chave.tolist()
        sinal = obter_tipo_contestacao(credora, devedora, referencia, trafego, remuneracao)
        mapa_expectativa[(credora, devedora, referencia, trafego, remuneracao)] = (
            _resolver_expectativa(sinal)
        )

    chaves_tuplas = list(chaves.itertuples(index=False, name=None))
    linhas[COL_EXPECTATIVA] = [mapa_expectativa[chave] for chave in chaves_tuplas]

    linhas[COL_ORIGEM] = const.ORIGEM
    linhas[COL_INSERCAO] = const.INSERCAO
    linhas[COL_AJUSTE] = ""
    linhas[COL_OBS] = ""

    logger.info(f"[HU-12 EXT] {linhas.shape[0]} linha(s) montada(s).")
    return linhas


@log_execucao
def gerar_arquivo_ext(
    linhas_ext: pd.DataFrame,
    operadora: str,
    aaaamm: str,
    raiz_operadoras: Path | None = None,
) -> Path:
    """
    Grava o arquivo EXT na pasta `AGI` da operadora (T-043).

    Args:
        linhas_ext: DataFrame já montado por :func:`montar_linhas_ext`.
        operadora: Nome da operadora (usado no nome do arquivo e na pasta).
        aaaamm: Período de referência (`AAAAMM`).
        raiz_operadoras: Raiz `...\\Operadoras`. Default: `CAMINHO_OPERADORAS` (config).

    Returns:
        Caminho completo do arquivo `.xlsx` gravado.
    """

    pasta_agi = ep.caminho_agi(operadora, aaaamm, raiz_operadoras=raiz_operadoras, criar=True)
    nome_arquivo = nom.nome_ext(aaaamm, operadora)
    caminho = pasta_agi / f"{nome_arquivo}{const.EXTENSAO_EXCEL}"

    ga.salvar_dados(linhas_ext, caminho, incluir_cabecalho=True)

    logger.info(f"[HU-12 EXT] Arquivo gravado em [{caminho}].")
    return caminho
