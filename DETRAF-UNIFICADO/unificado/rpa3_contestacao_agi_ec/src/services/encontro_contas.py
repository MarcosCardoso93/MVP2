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

**Q24 (2026-08-05):** entra a sétima coluna, `vb_contestacao` — a regra do ¶942, que
existe no bloco antigo da V2 e na V1, mas não no texto vigente. Ver
:func:`_valor_contestado`. É **acréscimo da unificação ao schema presumido**, como a
`remuneracao` de 2026-07-28, e vai ao DBA no encaminhamento.
"""

from __future__ import annotations

from typing import Callable, Optional

import pandas as pd

from comum.config import constantes as const
from comum.config.constantes import (
    COLUNAS_ATUALIZADAS_DESPESA_CONTESTACAO,
    COLUNAS_CHAVE_DESPESA_CONTESTACAO,
)
from comum.config.logger_config import logger
from comum.dados import tabelas
from comum.utils.decoradores import log_execucao

# Ordem das colunas do DataFrame de atualizações (chave + campos gravados).
COLUNAS_DESPESA_CONTESTACAO = (
    COLUNAS_CHAVE_DESPESA_CONTESTACAO + COLUNAS_ATUALIZADAS_DESPESA_CONTESTACAO
)


@log_execucao
def preparar_atualizacoes_despesa_contestacao(
    df_contest: pd.DataFrame,
    referencia: str,
    obter_tipo_contestacao: Optional[
        Callable[[str, str, str, str, str], Optional[str]]
    ] = None,
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
        obter_tipo_contestacao: Leitura do sinal do analista, usada só para a regra
            do ¶942 (Q24). **Opcional**: sem ela `vb_contestacao` sai vazio em todas
            as linhas, e as demais colunas continuam idênticas — é o que mantém
            testável a parte da HU-19 que não depende de banco.

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
            # Chave do banco (plural) à esquerda, coluna do frame de domínio
            # (singular) à direita. As duas grafias estão certas — ver
            # `tabelas.COL_CONTESTACAO_REMUNERACOES`.
            tabelas.COL_CONTESTACAO_REMUNERACOES: df_contest["remuneracao"],
            "minutos_operadora": df_contest["minutos_operadora"],
            "vb_operadora": -df_contest["vb_operadora"].abs(),
            "minutos_diferenca": df_contest["minutos_diferenca"],
            "vb_diferenca": -df_contest["vb_diferenca"].abs(),
            "minutos_variacao_perc": df_contest["minutos_variacao_perc"],
            "vb_variacao_perc": df_contest["vb_variacao_perc"],
            "vb_contestacao": _valor_contestado(
                df_contest, referencia, obter_tipo_contestacao
            ),
        }
    ).reset_index(drop=True)

    logger.info(
        f"[HU-19 Despesa Contestação] {linhas.shape[0]} atualização(ões) preparada(s)."
    )
    return linhas


def _valor_contestado(
    df_contest: pd.DataFrame,
    referencia: str,
    obter_tipo_contestacao: Optional[Callable[..., Optional[str]]],
) -> pd.Series:
    """
    A coluna do ¶942 — o valor bruto da diferença, **só nas linhas COM retenção**.

    > *"Quando acontece a contestação com retenção, o robô também preenche a
    > coluna de contestação da remuneração no EC para a EOT da Vivo atrelada à
    > contestação com o valor bruto da Diferença apresentada aba Contest."*
    > — V2 ¶942 (bloco antigo) / V1 HU-19

    A regra **não está no texto vigente da V2** — está no bloco antigo e na V1. A
    decisão de 2026-08-05 foi implementá-la mesmo assim: as duas versões
    concordam, e a informação que ela carrega ("quanto da diferença está retido")
    não existe em nenhuma outra coluna.

    O sinal segue a convenção de despesa do resto da tabela: **negativo**, igual
    ao `vb_diferenca` ao lado. Linha SEM retenção fica `None`, não zero — zero
    diria "nada retido apurado", e o que se quer dizer é "não se aplica".

    Returns:
        Série `object` alinhada ao índice de `df_contest`. Toda `None` quando a
        leitura do sinal não foi injetada.
    """

    if obter_tipo_contestacao is None:
        return pd.Series([None] * len(df_contest), index=df_contest.index, dtype=object)

    def _da_linha(linha) -> Optional[float]:
        sinal = obter_tipo_contestacao(
            linha["eot_credora"],
            linha["eot_devedora"],
            referencia,
            linha["trafego"],
            linha["remuneracao"],
        )
        if sinal != const.CENARIO_COM_RETENCAO:
            return None
        return -abs(float(linha["vb_diferenca"]))

    valores = df_contest.apply(_da_linha, axis=1)
    # Misturar `float` e `None` faz o pandas inferir `float64` e virar os `None`
    # em `NaN` — que o driver grava como o **texto** "nan", não como NULL. O
    # `where` sobre `object` devolve o `None` de verdade.
    return valores.astype(object).where(valores.notna(), None)
