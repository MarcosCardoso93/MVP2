"""Serviço da HU-13 — geração do arquivo INT para carga AGI (apenas COM retenção).

Fonte de regra: `AI/09-Regras-Negocio-Epico4.md` §3. Objetivo: montar
`DE_AGI_D_{aaaamm}_TBRA_X_{OPERADORA}_INT` a partir da aba `TBRA` (T-021) — **apenas o
tráfego contestado COM retenção**. Nos demais cenários (sem contestação, SEM retenção), o
arquivo **não é criado** (critério de aceite explícito, AI/09 §0/§3).

Molde direto de `src/services/geracao_ext.py` — mesma estrutura de
`montar_linhas_*`/`gerar_arquivo_*`, reaproveitando `eh_com_retencao` para o filtro.

**Gap D-12** (mesmo do EXT): sem modelo INT real no repositório, grava-se um `.xlsx` novo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from src.config import constantes_epico4 as const
from src.config.logger_config import logger
from src.services import mapa_remuneracao as mr
from src.services.geracao_ext import COL_REMUNERACAO, eh_com_retencao
from src.utils import estrutura_pastas as ep
from src.utils import gerenciador_arquivos as ga
from src.utils import nomenclatura as nom
from src.utils.decoradores import log_execucao

# Nomes das colunas extras preenchidas pelo robô (AI/09 §3), na ordem documentada.
COL_ORIGEM = "ORIGEM"
COL_EXPECTATIVA = "EXPECTATIVA"
COL_INSERCAO = "INSERÇÃO"
COL_AJUSTE = "AJUSTE"
COL_OBS = "OBS"


@log_execucao
def montar_linhas_int(
    df_tbra: pd.DataFrame,
    indice_descritor: int,
    indice_remuneracao: dict[str, list[str]],
    obter_tipo_contestacao: Callable[[str, str, str, str, str], Optional[str]],
    indice_credora: int = const.COL_CREDORA,
    indice_devedora: int = const.COL_DEVEDORA,
    indice_referencia: int = const.COL_REFERENCIA,
    indice_trafego: int = const.COL_TRAFEGO,
) -> pd.DataFrame:
    """
    Monta o conteúdo do INT (T-060/T-061): apenas linhas COM retenção.

    Diferente do EXT, aqui a linha é **descartada** se a combinação (EOT credora × EOT
    devedora × referência × tráfego × remuneração) não estiver sinalizada como COM
    retenção — o INT "só existe" nesse cenário (AI/09 §3). `EXPECTATIVA` é **fixa `"N"`**
    (não calculada), conforme documentado.

    Args:
        df_tbra: Aba `TBRA` consolidada (T-021), até `R$_Bruto`, sem linhas de total.
        indice_descritor: Índice (0-based) da coluna de descritor — sem posição fixa na
            documentação, informado pelo chamador (mesma razão de `montar_contest`/EXT).
        indice_remuneracao: Índice `descritor final -> [remunerações]` (D-5).
        obter_tipo_contestacao: Callable injetada (repository via controller) que resolve
            o sinal COM/SEM retenção por
            `(eot_operadora, eot_tbra, referencia, trafego, remuneracao)` (T-024/D-6; a
            remuneração entra na chave desde 2026-07-28 — o sinal pode variar por
            remuneração dentro do mesmo par de EOT).
        indice_credora, indice_devedora, indice_referencia, indice_trafego: Índices
            documentados (D-8) usados para consultar o sinal de contestação por linha.

    Returns:
        DataFrame só com as linhas COM retenção, com as colunas extras `REMUNERACAO`,
        `ORIGEM`, `EXPECTATIVA` (fixo `"N"`), `INSERÇÃO`, `AJUSTE`, `OBS` anexadas. **Vazio**
        se nenhuma linha for COM retenção (nenhum cenário aplicável).
    """

    if df_tbra.empty:
        return df_tbra.copy()

    remuneracao_serie = mr.resolver_series(
        df_tbra.iloc[:, indice_descritor], indice_remuneracao
    )
    chaves = pd.concat(
        [
            df_tbra.iloc[:, [indice_credora, indice_devedora, indice_referencia, indice_trafego]]
            .astype(str)
            .reset_index(drop=True),
            remuneracao_serie.astype(str).reset_index(drop=True),
        ],
        axis=1,
    )
    combinacoes_unicas = chaves.drop_duplicates()

    com_retencao_por_chave: dict[tuple, bool] = {}
    for _, linha_chave in combinacoes_unicas.iterrows():
        credora, devedora, referencia, trafego, remuneracao = linha_chave.tolist()
        sinal = obter_tipo_contestacao(credora, devedora, referencia, trafego, remuneracao)
        com_retencao_por_chave[(credora, devedora, referencia, trafego, remuneracao)] = (
            eh_com_retencao(sinal)
        )

    chaves_tuplas = list(chaves.itertuples(index=False, name=None))
    mascara_com_retencao = pd.Series(
        [com_retencao_por_chave[chave] for chave in chaves_tuplas], index=df_tbra.index
    )

    linhas = df_tbra[mascara_com_retencao].copy()

    if linhas.empty:
        logger.info(
            "[HU-13 INT] Nenhuma linha COM retenção — INT não se aplica a este cenário."
        )
        return linhas

    linhas[COL_REMUNERACAO] = remuneracao_serie[mascara_com_retencao]
    linhas[COL_ORIGEM] = const.ORIGEM
    linhas[COL_EXPECTATIVA] = const.EXPECTATIVA_NAO
    linhas[COL_INSERCAO] = const.INSERCAO
    linhas[COL_AJUSTE] = ""
    linhas[COL_OBS] = ""

    logger.info(f"[HU-13 INT] {linhas.shape[0]} linha(s) montada(s) (COM retenção).")
    return linhas


@log_execucao
def gerar_arquivo_int(
    linhas_int: pd.DataFrame,
    operadora: str,
    aaaamm: str,
    raiz_operadoras: Path | None = None,
) -> Optional[Path]:
    """
    Grava o arquivo INT na pasta `AGI` da operadora (T-062) — **só se houver linhas**.

    Se `linhas_int` estiver vazio (cenário sem contestação ou SEM retenção), **nenhum
    arquivo é criado** — critério de aceite explícito da HU-13 (AI/09 §3, matriz §0).

    Args:
        linhas_int: DataFrame já montado por :func:`montar_linhas_int`.
        operadora: Nome da operadora (usado no nome do arquivo e na pasta).
        aaaamm: Período de referência (`AAAAMM`).
        raiz_operadoras: Raiz `...\\Operadoras`. Default: `CAMINHO_OPERADORAS` (config).

    Returns:
        Caminho do arquivo `.xlsx` gravado, ou ``None`` se o INT não se aplica ao cenário.
    """

    if linhas_int.empty:
        logger.info(
            "[HU-13 INT] Nada a gravar (sem linhas COM retenção) — arquivo não criado."
        )
        return None

    pasta_agi = ep.caminho_agi(operadora, aaaamm, raiz_operadoras=raiz_operadoras, criar=True)
    nome_arquivo = nom.nome_int(aaaamm, operadora)
    caminho = pasta_agi / f"{nome_arquivo}{const.EXTENSAO_EXCEL}"

    ga.salvar_dados(linhas_int, caminho, incluir_cabecalho=True)

    logger.info(f"[HU-13 INT] Arquivo gravado em [{caminho}].")
    return caminho
