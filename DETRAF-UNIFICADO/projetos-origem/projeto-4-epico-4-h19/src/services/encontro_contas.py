"""Serviço da HU-19 — despesa da contestação (Épico 6, escopo ampliado por D-15).

**Reformulado em 2026-07-28 (D-16 revisada):** a abordagem original de gerar uma
planilha "Encontro de Contas" foi **substituída** — o robô passa a escrever em
``tbl_rpa_log_detraf_despesa_contestacao`` (a mesma tabela do sinal COM/SEM retenção,
D-6), com uma coluna ``remuneracao`` adicionada ao schema.

**Revisto em 2026-07-30 (D-20, adequação à V2):** a V2 (pág. 38) diz que o robô
*"atualiza a tabela do banco webfat ... Atualiza os campos `minutos_operadora`,
`vb_operadora`, `minutos_diferenca`, `vb_diferenca`, `minutos_variacao_perc`,
`vb_variacao_perc`"*. A escrita da HU-19 deixa portanto de ser um **INSERT** da linha
inteira e passa a ser um **UPDATE** desses seis campos: a linha-base (chave + lado
TBRA/expectativa) é inserida pelo Épico 3 (V2 pág. 19), **fora do escopo deste
projeto** — ver bloqueio B-D20.

Este módulo só **prepara** o DataFrame de atualizações (regra pura, sem acesso a banco
— AI/01 §1); a gravação é feita por
:func:`src.models.repository.repositorio_tabelas.RepositorioTabelas.atualizar_despesa_contestacao`.

**Regra (decisões do usuário, 2026-07-28 e 2026-07-30):**
- **Todas** as linhas do `Contest` (T-023) são atualizadas — não só as
  `contestacao_a_enviar == "S"` (o analista precisa ver o panorama completo para decidir).
- `vb_operadora` e `vb_diferenca` são gravados **sempre negativos** (despesa).
- `tipo_contestacao` **não** é escrito aqui: é o sinal do analista, regravado pela HU-16
  após o CONT_PROC (D-19). `carga_agi` é da HU-18 (Épico 5, fora de escopo).
"""

from __future__ import annotations

import pandas as pd

from src.config.constantes_epico4 import (
    COLUNAS_ATUALIZADAS_DESPESA_CONTESTACAO,
    COLUNAS_CHAVE_DESPESA_CONTESTACAO,
)
from src.config.logger_config import logger
from src.utils.decoradores import log_execucao

# Ordem das colunas do DataFrame de atualizações (chave + campos gravados).
COLUNAS_DESPESA_CONTESTACAO = (
    COLUNAS_CHAVE_DESPESA_CONTESTACAO + COLUNAS_ATUALIZADAS_DESPESA_CONTESTACAO
)


@log_execucao
def preparar_atualizacoes_despesa_contestacao(
    df_contest: pd.DataFrame,
    referencia: str,
) -> pd.DataFrame:
    """
    Monta as atualizações da despesa da contestação (HU-19), prontas para
    `RepositorioTabelas.atualizar_despesa_contestacao`.

    Args:
        df_contest: Saída de `consolidacao_contestacao.montar_contest` (T-023) — colunas
            `eot_credora`, `eot_devedora`, `remuneracao`, `trafego`, `minutos_operadora`,
            `vb_operadora`, `minutos_diferenca`, `vb_diferenca`, `minutos_variacao_perc`,
            `vb_variacao_perc`.
        referencia: Mês de referência do Detraf (`AAAAMM`) — mesmo parâmetro único de
            lote usado por `geracao_cont_proc.montar_linhas_cont_proc`.

    Returns:
        DataFrame com as colunas de `COLUNAS_DESPESA_CONTESTACAO` (chave + os seis
        campos da V2 pág. 38), uma linha por combinação do `Contest` (**todas**, não só
        as contestadas — o analista decide via Webfat). `vb_operadora`/`vb_diferenca`
        sempre negativos. Vazio se `df_contest` for vazio.
    """

    if df_contest.empty:
        return pd.DataFrame(columns=COLUNAS_DESPESA_CONTESTACAO)

    linhas = pd.DataFrame(
        {
            "eot_operadora": df_contest["eot_credora"],
            "eot_tbra": df_contest["eot_devedora"],
            "referencia": referencia,
            "trafego": df_contest["trafego"],
            "remuneracao": df_contest["remuneracao"],
            "minutos_operadora": df_contest["minutos_operadora"],
            "vb_operadora": -df_contest["vb_operadora"].abs(),
            "minutos_diferenca": df_contest["minutos_diferenca"],
            "vb_diferenca": -df_contest["vb_diferenca"].abs(),
            "minutos_variacao_perc": df_contest["minutos_variacao_perc"],
            "vb_variacao_perc": df_contest["vb_variacao_perc"],
        }
    ).reset_index(drop=True)

    logger.info(
        f"[HU-19 Despesa Contestação] {linhas.shape[0]} atualização(ões) preparada(s)."
    )
    return linhas
