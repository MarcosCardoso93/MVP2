"""Serviço da HU-16 — arquivo CONT_PROC para carga AGI (SEM e COM retenção).

**Escopo atual: T-100, T-101 e T-102 — HU-16 completa.**

- T-100: colunas `ID_OPERADORA_JV`, `ID_OPERADORA_PREST`, `ID_PERIODO_REF`,
  `ID_PERIODO_TRAF`, `DEBIT_CREDIT`, `FLAG_PAG_REC`.
- T-101: `DURACAO`/`VLR_BRUTO` (negativos, a partir da diferença já calculada pelo
  `Contest` — **as duas recebem minutagem**, ver abaixo), `REMUNERACAO_FIXA` (já resolvida pelo `Contest` via D-5) e `ID_MODALIDADE`
  (**D-4 RESOLVIDA, 2026-07-23** — usuário confirmou valor fixo
  `constantes_epico4.ID_MODALIDADE_PADRAO = "00"`, a partir dos 2 exemplos reais da
  máscara `CONT_PROC_MASCARA_OPERADORA_202510_TESTE.xls`, ambos com `ID_MODALIDADE="00"`
  apesar de remunerações diferentes).
- T-102: grava o arquivo em `.xlsx` (**D-7 resolvida** — o AGI aceita `.xlsx`).

**Nota sobre os índices reais de coluna (arquivo real inspecionado, 2026-07-23):** a
ordem documentada em AI/09 §5 (C,D,E,F,G,H,I,W,AB,AG) **não bate** com o arquivo real —
lá as mesmas colunas aparecem em B,C,D,E,F,G,H,Y,AD,AI (a máscara real tem ~15 colunas
extras entre `DURACAO` e `VLR_BRUTO` que a doc não previa: `ST_ENCERRAMENTO`,
`DT_APRES_PROC`, `DS_OBS`, `TP_MERCADO`, impostos etc.). Como este service ainda produz
apenas um DataFrame com colunas **nomeadas** (não escreve posicionalmente no template
real), isso não afeta a implementação atual — registrado para quando a escrita
posicional no template for implementada.

## ⚠️ A coluna W (`VLR_BRUTO`) recebe MINUTAGEM

**Decisão do PO, 2026-08-06 — fecha a pendência Q11.**

A V2 (¶643) diz, literalmente:

    "Coluna W: 'VLR_BRUTO' - preencher com a **minutagem** total da linha."

O texto é **idêntico ao da coluna I** (`DURACAO`), o que levava a ler como erro
de redação — uma coluna chamada `VLR_BRUTO` recebendo minutos parece copy-paste.
Até 2026-08-06 o código gravava `vb_diferenca` (valor), com a divergência
registrada como pendência **justamente por ser dado financeiro carregado no AGI**,
onde errar não é reversível e ninguém confere linha a linha.

**Perguntado e respondido: não é o valor bruto.** As duas colunas recebem a
mesma minutagem, e é isso que o AGI espera.

Se algum dia isto se mostrar equivocado, a correção é uma linha — trocar
`minutos_diferenca` por `vb_diferenca` em `COL_VLR_BRUTO`, no
`montar_linhas_cont_proc`.

Fonte de regra: `AI/09-Regras-Negocio-Epico4.md` §5.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from comum.config import constantes as const
from comum.config.logger_config import logger
from comum.dados import tabelas
from src.services.geracao_ext import eh_com_retencao
from comum.arquivos import estrutura_pastas as ep
from comum.arquivos import gerenciador as ga
from comum.arquivos import nomenclatura as nom
from comum.utils.decoradores import log_execucao

# Nomes das colunas do CONT_PROC (AI/09 §5; posições reais — ver nota no docstring).
COL_ID_OPERADORA_JV = "ID_OPERADORA_JV"
COL_ID_OPERADORA_PREST = "ID_OPERADORA_PREST"
COL_ID_PERIODO_REF = "ID_PERIODO_REF"
COL_ID_PERIODO_TRAF = "ID_PERIODO_TRAF"
COL_DEBIT_CREDIT = "DEBIT_CREDIT"
COL_FLAG_PAG_REC = "FLAG_PAG_REC"
COL_DURACAO = "DURACAO"
COL_VLR_BRUTO = "VLR_BRUTO"
COL_ID_MODALIDADE = "ID_MODALIDADE"
COL_REMUNERACAO_FIXA = "REMUNERACAO_FIXA"


@log_execucao
def selecionar_linhas_contestadas(
    df_contest: pd.DataFrame,
    referencia: str,
    obter_tipo_contestacao: Callable[[str, str, str, str, str], Optional[str]],
) -> pd.DataFrame:
    """
    Aplica o **gate de "linha contestada"** (D-14, AI/09 §0) sobre o `Contest`.

    Uma linha só é considerada contestada se **ambos** os sinais forem verdadeiros:

    1. `contestacao_a_enviar == "S"` — variação de `R$_Bruto` acima do limiar, calculada
       pelo `Contest` (T-023);
    2. o sinal do analista (`obter_tipo_contestacao`) não é nulo — ou seja, o cenário é
       realmente SEM ou COM retenção, e não "sem contestação".

    Uma linha com variação alta mas sem decisão do analista **não** é contestada: o
    CONT_PROC (e o writeback da D-19) só existem nos cenários SEM/COM retenção.

    Ponto único de verdade do gate: consumido por :func:`montar_linhas_cont_proc`
    (arquivo da HU-16) e pelo writeback de `tipo_contestacao` (D-19). O sinal é
    resolvido **uma vez por chave única**, como já fazem EXT e INT.

    Args:
        df_contest: Saída de `consolidacao_contestacao.montar_contest` (T-023).
        referencia: Mês de referência do Detraf da contestação (`AAAAMM`).
        obter_tipo_contestacao: Callable injetada (repository via controller — o service
            não acessa banco, AI/01 §1) que resolve o sinal por
            `(eot_operadora, eot_tbra, referencia, trafego, remuneracao)` (T-024/D-6).

    Returns:
        DataFrame com as colunas de chave (`eot_operadora`, `eot_tbra`, `referencia`,
        `trafego`, `remuneracao`) mais `tipo_contestacao`, **preservando o índice de
        `df_contest`** (para que o chamador recupere as demais colunas por `.loc`).
        Vazio se nada for contestado.
    """

    colunas_saida = const.COLUNAS_CHAVE_DESPESA_CONTESTACAO + ["tipo_contestacao"]

    if df_contest.empty:
        return pd.DataFrame(columns=colunas_saida)

    candidatas = df_contest[df_contest["contestacao_a_enviar"] == "S"]

    if candidatas.empty:
        logger.info("[HU-16 CONT_PROC] Nenhuma combinação com 'contestacao_a_enviar'=S.")
        return pd.DataFrame(columns=colunas_saida)

    # Nomes de COLUNA DO BANCO — a ordem tem que bater com
    # `COLUNAS_CHAVE_DESPESA_CONTESTACAO`, porque a chamada abaixo é posicional.
    chaves = pd.DataFrame(
        {
            "eot_operadora": candidatas["eot_credora"].astype(str),
            "eot_tbra": candidatas["eot_devedora"].astype(str),
            "referencia": str(referencia),
            "trafego": candidatas["trafego"].astype(str),
            # Plural à esquerda (banco), singular à direita (frame de domínio).
            tabelas.COL_CONTESTACAO_REMUNERACOES: candidatas["remuneracao"].astype(
                str
            ),
        }
    )

    # Uma consulta por combinação única, não por linha. O splat é POSICIONAL:
    # `obter_tipo_contestacao` recebe parâmetros de domínio (`remuneracao`, no
    # singular), e é a ordem das colunas acima que os alimenta — não o nome.
    sinal_por_chave = {
        chave: obter_tipo_contestacao(*chave)
        for chave in dict.fromkeys(chaves.itertuples(index=False, name=None))
    }

    chaves["tipo_contestacao"] = [
        sinal_por_chave[chave] for chave in chaves.itertuples(index=False, name=None)
    ]

    contestadas = chaves[chaves["tipo_contestacao"].notna()]

    if contestadas.empty:
        logger.info(
            "[HU-16 CONT_PROC] Nenhuma combinação com sinal do analista (todas 'sem "
            "contestação' apesar da variação)."
        )
        return pd.DataFrame(columns=colunas_saida)

    logger.info(f"[HU-16 CONT_PROC] {contestadas.shape[0]} linha(s) contestada(s).")
    return contestadas


@log_execucao
def montar_linhas_cont_proc(
    df_contest: pd.DataFrame,
    referencia: str,
    obter_tipo_contestacao: Callable[[str, str, str, str, str], Optional[str]],
) -> pd.DataFrame:
    """
    Monta as colunas C-H do CONT_PROC (T-100), uma linha por combinação já produzida
    pelo `Contest` (T-023) — (EOT credora × EOT devedora × remuneração × tráfego).

    **Filtro (AI/09 §0/§5 — "SEM e COM retenção", exclui "sem contestação"):** apenas
    linhas com `contestacao_a_enviar == "S"` entram (a mesma flag de variação que decide
    "deve ser contestado" na aba `Contest`).

    `referencia` (mês do Detraf da contestação, coluna E) é recebida como **parâmetro
    único do lote** — o `Base_Contestação` é escopado a um único mês de referência por
    nome de arquivo (`Base_Contestação_{operadora}_{mês}`), então não há necessidade de
    uma coluna por linha (o `Contest`, T-023, não a carrega — seu agrupamento documentado
    é só EOT × tarifação × tráfego).

    **T-101:** também preenche `DURACAO`/`VLR_BRUTO` (negativos, a partir da diferença já
    calculada pelo `Contest`), `REMUNERACAO_FIXA` (já resolvida pelo `Contest`, D-5) e
    `ID_MODALIDADE` (valor fixo `constantes_epico4.ID_MODALIDADE_PADRAO`, D-4 resolvida).

    **Gate de "linha contestada" (D-14):** delegado a
    :func:`selecionar_linhas_contestadas`, compartilhado com o writeback de
    `tipo_contestacao` (D-19).

    Args:
        df_contest: Saída de `consolidacao_contestacao.montar_contest` (T-023), com as
            colunas `eot_credora`, `eot_devedora`, `remuneracao`, `trafego`,
            `contestacao_a_enviar`, `minutos_diferenca`, `vb_diferenca`.
        referencia: Mês de referência do Detraf da contestação (`AAAAMM`).
        obter_tipo_contestacao: Callable injetada (repository via controller) que resolve
            o sinal COM/SEM retenção por
            `(eot_operadora, eot_tbra, referencia, trafego, remuneracao)` (T-024/D-6; a
            remuneração entra na chave desde 2026-07-28) — usada para `FLAG_PAG_REC` e
            para o gate acima.

    Returns:
        DataFrame com as colunas `ID_OPERADORA_JV`, `ID_OPERADORA_PREST`,
        `ID_PERIODO_REF`, `ID_PERIODO_TRAF`, `DEBIT_CREDIT`, `FLAG_PAG_REC`, `DURACAO`,
        `VLR_BRUTO`, `ID_MODALIDADE` (fixo, D-4), `REMUNERACAO_FIXA` — uma linha por
        combinação contestada (ver gate acima). Vazio se nada a contestar.
    """

    colunas_saida = [
        COL_ID_OPERADORA_JV,
        COL_ID_OPERADORA_PREST,
        COL_ID_PERIODO_REF,
        COL_ID_PERIODO_TRAF,
        COL_DEBIT_CREDIT,
        COL_FLAG_PAG_REC,
        COL_DURACAO,
        COL_VLR_BRUTO,
        COL_ID_MODALIDADE,
        COL_REMUNERACAO_FIXA,
    ]

    selecionadas = selecionar_linhas_contestadas(
        df_contest=df_contest,
        referencia=referencia,
        obter_tipo_contestacao=obter_tipo_contestacao,
    )

    if selecionadas.empty:
        return pd.DataFrame(columns=colunas_saida)

    # O gate preserva o índice do `Contest`, então as demais colunas voltam por `.loc`.
    contestadas = df_contest.loc[selecionadas.index]

    flag_pag_rec = selecionadas["tipo_contestacao"].map(
        lambda sinal: (
            const.FLAG_PAG_REC_COM_RETENCAO
            if eh_com_retencao(sinal)
            else const.FLAG_PAG_REC_SEM_RETENCAO
        )
    )

    resultado = pd.DataFrame(
        {
            COL_ID_OPERADORA_JV: contestadas["eot_devedora"],
            COL_ID_OPERADORA_PREST: contestadas["eot_credora"],
            COL_ID_PERIODO_REF: referencia,
            COL_ID_PERIODO_TRAF: contestadas["trafego"],
            COL_DEBIT_CREDIT: const.DEBIT_CREDIT_DESPESA,
            COL_FLAG_PAG_REC: flag_pag_rec,
            COL_DURACAO: -contestadas["minutos_diferenca"],
            # ⚠️ MINUTAGEM, não valor — decisão do PO em 2026-08-06 (pendência
            # Q11). Ver a seção "A coluna W" no docstring do módulo.
            COL_VLR_BRUTO: -contestadas["minutos_diferenca"],
            COL_ID_MODALIDADE: const.ID_MODALIDADE_PADRAO,
            COL_REMUNERACAO_FIXA: contestadas["remuneracao"],
        }
    ).reset_index(drop=True)

    logger.info(f"[HU-16 CONT_PROC] {resultado.shape[0]} linha(s) montada(s) (T-100+T-101 completos).")
    return resultado


@log_execucao
def gerar_arquivo_cont_proc(
    linhas_cont_proc: pd.DataFrame,
    operadora: str,
    aaaamm: str,
    raiz_operadoras: Path | None = None,
) -> Optional[Path]:
    """
    Grava o arquivo CONT_PROC (T-102) — **só se houver linhas** a contestar.

    D-7 resolvida (2026-07-23): grava em **`.xlsx`** (o AGI aceita), sem depender de
    `xlwt`. Destino: pasta `AGI` (AI/10 §2: "(pasta AGI/carga)"), mesma usada pelo
    EXT/INT — decisão de design não questionada pelo usuário; ajustar se confirmado
    destino diferente no futuro.

    Args:
        linhas_cont_proc: DataFrame já montado por :func:`montar_linhas_cont_proc`.
        operadora: Nome da operadora (usado no nome do arquivo e na pasta).
        aaaamm: Período de referência (`AAAAMM`).
        raiz_operadoras: Raiz `...\\Operadoras`. Default: `CAMINHO_OPERADORAS` (config).

    Returns:
        Caminho do arquivo `.xlsx` gravado, ou ``None`` se não houver linhas a contestar.
    """

    if linhas_cont_proc.empty:
        logger.info("[HU-16 CONT_PROC] Nada a gravar (nenhuma linha a contestar).")
        return None

    pasta_agi = ep.caminho_agi(operadora, aaaamm, raiz_operadoras=raiz_operadoras, criar=True)
    nome_arquivo = nom.nome_cont_proc(operadora, aaaamm)
    caminho = pasta_agi / nome_arquivo

    ga.salvar_dados(linhas_cont_proc, caminho, incluir_cabecalho=True)

    logger.info(f"[HU-16 CONT_PROC] Arquivo gravado em [{caminho}].")
    return caminho
