"""Serviço de Consolidação — produção do Base_Contestação (dependência D-2).

Escopo atual:

- **T-020** — aba `{operadora}`: concatena os "Detrafs Recebidos" da operadora,
  removendo as linhas de total (`Rel = 1`).
- **T-021** — aba `TBRA`: concatena os arquivos de expectativa Vivo (nome com
  ``_D_``/``_D``), até a coluna `R$_Bruto` (truncamento opcional — D-8), também
  removendo `Rel = 1`.
- **T-022** — aba `RESUMO`: totais de `Minutos`/`R$_Bruto` por `Referência`/`Tráfego`
  (tabela dinâmica — AI/09 §1, confirmado pelos screenshots do ToBe, D-11).
- **T-023** — aba `Contest`: comparação operadora × expectativa por EOT/remuneração/
  mês de tráfego, com a flag de variação (D-11, D-5, D-6 resolvidas). Produz apenas o
  **conteúdo** (DataFrame); a escrita do `.xlsx` multi-aba fica para tarefa futura
  (falta o modelo `_M` real — resíduo de D-11).

Regra de negócio deliberadamente **não inventada** além do que está documentado/confirmado
por evidência real (ToBe, planilhas auxiliares). O índice da coluna de total varia por
layout (**D-8**; decisão do usuário: usar os índices documentados como default) e o índice
da coluna de **descritor** não tem posição fixa na documentação — por isso é recebido
como parâmetro explícito, nunca hardcoded.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.config import constantes_epico4 as const
from src.config.configuration import EXTENSOES_PERMITIDAS
from src.config.logger_config import logger
from src.services import mapa_remuneracao as mr
from src.utils import gerenciador_arquivos as ga
from src.utils.decoradores import log_execucao


def _valor_numerico(serie: pd.Series) -> pd.Series:
    """
    Converte uma coluna de valores Detraf (string, vírgula decimal — L-006) para float.

    Valores não conversíveis viram ``0.0`` (célula vazia/malformada não deve derrubar
    a soma; ver AI/02 §5 "falha esperada ⇒ log e segue").
    """

    convertido = pd.to_numeric(
        serie.astype(str).str.strip().str.replace(",", ".", regex=False),
        errors="coerce",
    )
    return convertido.fillna(0.0)


def listar_arquivos_detraf(pasta: Path) -> list[Path]:
    """
    Lista os arquivos com extensão permitida dentro de ``pasta`` (não recursivo).

    Args:
        pasta: Diretório de Detrafs (recebidos ou enviados) da operadora.

    Returns:
        Lista ordenada de :class:`~pathlib.Path`. Vazia se a pasta não existir.
    """

    pasta = Path(pasta)
    if not pasta.is_dir():
        logger.warning(f"Pasta de Detrafs inexistente: [{pasta}]")
        return []

    arquivos = sorted(
        caminho
        for caminho in pasta.iterdir()
        if caminho.is_file() and caminho.suffix.lower() in EXTENSOES_PERMITIDAS
    )
    logger.info(f"[Consolidação] {len(arquivos)} arquivo(s) encontrado(s) em [{pasta}].")
    return arquivos


def eh_arquivo_expectativa(caminho: Path) -> bool:
    """
    Indica se o arquivo é de expectativa Vivo (nome contém ``_D_`` ou termina em ``_D``).

    Regra AI/09 §1 / AI/10 §1.2: apenas os arquivos com ``_D_`` no nome entram na
    aba ``TBRA``.
    """

    stem = caminho.stem.upper()
    return "_D_" in stem or stem.endswith("_D")


def _concatenar_arquivos(
    arquivos: list[Path],
    indice_total: int,
    valor_total: str,
    min_colunas: int,
    indice_ultima_coluna: int | None = None,
) -> pd.DataFrame:
    """
    Núcleo comum de consolidação: carrega, valida, remove totais, (trunca) e concatena.

    Args:
        arquivos: Arquivos a consolidar.
        indice_total: Índice (0-based) da coluna que marca a linha de total (D-8).
        valor_total: Valor textual que identifica a linha de total.
        min_colunas: Nº mínimo de colunas esperado (fail-fast).
        indice_ultima_coluna: Se informado, mantém apenas as colunas ``0..N`` (corte
            "até `R$_Bruto`"). ``None`` mantém todas.

    Returns:
        DataFrame consolidado (sem linhas de total). Vazio se nada a consolidar.

    Raises:
        ValueError: Se algum arquivo tiver menos colunas que ``min_colunas``.
    """

    partes: list[pd.DataFrame] = []

    for caminho in arquivos:
        df = ga.carregar_dados(caminho)

        if df.empty:
            logger.warning(f"[Consolidação] Arquivo vazio ignorado: [{caminho.name}].")
            continue

        if not ga.validar_quantidade_minima_colunas(df, min_colunas):
            raise ValueError(
                f"Arquivo [{caminho.name}] tem {df.shape[1]} coluna(s); "
                f"esperado no mínimo {min_colunas}. Layout inesperado (ver D-8)."
            )

        sem_total = ga.remover_linhas_por_valor(df, indice_total, valor_total)

        if indice_ultima_coluna is not None:
            indices = list(range(indice_ultima_coluna + 1))
            sem_total = ga.obter_lista_colunas_por_indices(sem_total, indices)

        logger.info(
            f"[Consolidação] [{caminho.name}]: {df.shape[0]} linha(s) -> "
            f"{sem_total.shape[0]} após remover totais."
        )
        partes.append(sem_total)

    if not partes:
        return pd.DataFrame()

    consolidado = pd.concat(partes, ignore_index=True)
    logger.info(
        f"[Consolidação] Consolidado: {consolidado.shape[0]} linha(s) "
        f"de {len(partes)} arquivo(s)."
    )
    return consolidado


@log_execucao
def consolidar_detrafs_operadora(
    pasta: Path,
    indice_total: int = const.COL_REL,
    valor_total: str = const.VALOR_REL_TOTAL,
    min_colunas: int = const.COL_R_BRUTO + 1,
) -> pd.DataFrame:
    """
    Monta a aba ``{operadora}``: concatena os Detrafs da operadora removendo os totais.

    Args:
        pasta: Pasta de "Detrafs Recebidos" da operadora.
        indice_total: Índice (0-based) da coluna de total. Varia por layout (**D-8**).
        valor_total: Valor textual que identifica a linha de total.
        min_colunas: Nº mínimo de colunas esperado (fail-fast).

    Returns:
        DataFrame consolidado (sem linhas de total). Vazio se não houver arquivos.
    """

    arquivos = listar_arquivos_detraf(pasta)
    if not arquivos:
        return pd.DataFrame()
    return _concatenar_arquivos(arquivos, indice_total, valor_total, min_colunas)


@log_execucao
def consolidar_expectativa_vivo(
    pasta: Path,
    indice_total: int = const.COL_REL,
    valor_total: str = const.VALOR_REL_TOTAL,
    min_colunas: int = const.COL_R_BRUTO + 1,
    indice_ultima_coluna: int | None = None,
) -> pd.DataFrame:
    """
    Monta a aba ``TBRA``: concatena a expectativa Vivo (arquivos ``_D_``), sem totais.

    Somente arquivos cujo nome contém ``_D_``/``_D`` entram (AI/09 §1). O corte
    "até `R$_Bruto`" é aplicado via ``indice_ultima_coluna`` quando informado — o
    índice exato do layout de expectativa depende de **D-8**, por isso é parâmetro
    (default ``None`` = mantém todas as colunas).

    Args:
        pasta: Pasta de "Detrafs Enviados" (expectativa Vivo).
        indice_total: Índice (0-based) da coluna de total (D-8; Vivo observado = 6).
        valor_total: Valor textual que identifica a linha de total.
        min_colunas: Nº mínimo de colunas esperado (fail-fast).
        indice_ultima_coluna: Corte "até `R$_Bruto`" (mantém colunas ``0..N``).

    Returns:
        DataFrame consolidado (sem linhas de total). Vazio se não houver arquivos ``_D_``.
    """

    arquivos = [a for a in listar_arquivos_detraf(pasta) if eh_arquivo_expectativa(a)]
    if not arquivos:
        logger.warning(f"[Consolidação] Nenhum arquivo de expectativa (_D_) em [{pasta}].")
        return pd.DataFrame()
    return _concatenar_arquivos(
        arquivos, indice_total, valor_total, min_colunas, indice_ultima_coluna
    )


@log_execucao
def montar_resumo(
    df: pd.DataFrame,
    indice_referencia: int = const.COL_REFERENCIA,
    indice_trafego: int = const.COL_TRAFEGO,
    indice_minutos: int = const.COL_MINUTOS,
    indice_r_bruto: int = const.COL_R_BRUTO,
) -> pd.DataFrame:
    """
    Monta a aba ``RESUMO`` (T-022): totais de `Minutos`/`R$_Bruto` por `Referência`/`Tráfego`.

    Reproduz a tabela dinâmica confirmada pelos screenshots do ToBe (D-11): "totais das
    colunas 'Minutos' e 'R$ Bruto'... inserir também as colunas 'Tráfego', 'Referência'"
    (AI/09 §1). É **intermediária** — não é renderizada em nenhum artefato final; alimenta
    apenas a montagem do `Contest` (T-023).

    Args:
        df: DataFrame já consolidado (aba `{operadora}` ou `TBRA`, sem linhas de total).
        indice_referencia: Índice da coluna `Referência` (default documentado — D-8).
        indice_trafego: Índice da coluna `Tráfego` (default documentado — D-8).
        indice_minutos: Índice da coluna `Minutos` (default documentado — D-8).
        indice_r_bruto: Índice da coluna `R$_Bruto` (default documentado — D-8).

    Returns:
        DataFrame com colunas ``Referência``, ``Tráfego``, ``Minutos``, ``R$_Bruto``
        (uma linha por combinação, com os totais somados).
    """

    colunas_saida = ["Referência", "Tráfego", "Minutos", "R$_Bruto"]

    if df.empty:
        return pd.DataFrame(columns=colunas_saida)

    tabela = pd.DataFrame(
        {
            "Referência": df.iloc[:, indice_referencia].astype(str).str.strip(),
            "Tráfego": df.iloc[:, indice_trafego].astype(str).str.strip(),
            "Minutos": _valor_numerico(df.iloc[:, indice_minutos]),
            "R$_Bruto": _valor_numerico(df.iloc[:, indice_r_bruto]),
        }
    )

    resumo = tabela.groupby(["Referência", "Tráfego"], as_index=False)[
        ["Minutos", "R$_Bruto"]
    ].sum()

    logger.info(f"[Consolidação] RESUMO: {resumo.shape[0]} combinação(ões) Referência/Tráfego.")
    return resumo


def _agregar_por_chave(
    df: pd.DataFrame,
    indice_descritor: int,
    indice_remuneracao: dict[str, list[str]],
    indice_credora: int,
    indice_devedora: int,
    indice_trafego: int,
    indice_minutos: int,
    indice_r_bruto: int,
    rotulo_minutos: str,
    rotulo_vb: str,
) -> pd.DataFrame:
    """
    Agrega um lado (operadora OU TBRA) por (EOT credora, EOT devedora, remuneração, tráfego).

    Descritores cujo caractere final não está mapeado são **ignorados** (AI/09 §7).
    Colisões de caractere final já são resolvidas deterministicamente por
    `mapa_remuneracao.construir_indice_remuneracao` (D-5, filtro `produto` + primeira
    ocorrência) — o log de WARNING abaixo é só defensivo (não deve disparar na prática).
    """

    if df.empty:
        return pd.DataFrame(
            columns=["eot_credora", "eot_devedora", "remuneracao", "trafego", rotulo_minutos, rotulo_vb]
        )

    df = df.copy()
    df["_remuneracao"] = mr.resolver_series(df.iloc[:, indice_descritor], indice_remuneracao)
    nao_mapeados = int(df["_remuneracao"].isna().sum())
    if nao_mapeados:
        logger.info(
            f"[Consolidação] {nao_mapeados} linha(s) com descritor não mapeado — ignoradas "
            f"na aba Contest (AI/09 §7)."
        )
    df_validos = df[df["_remuneracao"].notna()]

    if df_validos.empty:
        return pd.DataFrame(
            columns=["eot_credora", "eot_devedora", "remuneracao", "trafego", rotulo_minutos, rotulo_vb]
        )

    tabela = pd.DataFrame(
        {
            "eot_credora": df_validos.iloc[:, indice_credora].astype(str).str.strip(),
            "eot_devedora": df_validos.iloc[:, indice_devedora].astype(str).str.strip(),
            "remuneracao": df_validos["_remuneracao"],
            "trafego": df_validos.iloc[:, indice_trafego].astype(str).str.strip(),
            rotulo_minutos: _valor_numerico(df_validos.iloc[:, indice_minutos]),
            rotulo_vb: _valor_numerico(df_validos.iloc[:, indice_r_bruto]),
        }
    )

    return tabela.groupby(
        ["eot_credora", "eot_devedora", "remuneracao", "trafego"], as_index=False
    )[[rotulo_minutos, rotulo_vb]].sum()


@log_execucao
def montar_contest(
    df_operadora: pd.DataFrame,
    df_tbra: pd.DataFrame,
    indice_descritor: int,
    indice_remuneracao: dict[str, list[str]],
    mapa_tipo_operacao: dict[str, str] | None = None,
    limiar_variacao: float = const.LIMIAR_VARIACAO_CONTESTACAO,
    indice_credora: int = const.COL_CREDORA,
    indice_devedora: int = const.COL_DEVEDORA,
    indice_trafego: int = const.COL_TRAFEGO,
    indice_minutos: int = const.COL_MINUTOS,
    indice_r_bruto: int = const.COL_R_BRUTO,
) -> pd.DataFrame:
    """
    Monta a aba ``Contest`` (T-023): comparação operadora × expectativa (TBRA).

    Agrupa por (EOT credora × EOT devedora × remuneração × mês de tráfego) e calcula a
    diferença/variação de `Minutos` e `R$_Bruto` (**base = lado operadora**, confirmado
    contra o exemplo real da carta — ToBe screenshot: EOT 11/200, TBRA 4.790,2/29,18,
    AMPERNET 53.106,7/324,41, Diferença 48.316,5/295,23, Variação 91,0%/91,0% — e contra o
    arquivo real `Base Contestação_GT GROUP..._ROBO.xlsx`, aba `Contest`: **`EOT TBRA`
    e `EOT OPERADORA` são colunas separadas**, não uma coluna combinada — por isso este
    service não gera nenhuma coluna `eot` combinada).

    **Nota de formato (não é bug):** no arquivo real, "Variação Perc." é armazenada como
    **fração** (ex. `0.192`), não como número já multiplicado por 100. Este service
    mantém `*_variacao_perc` na escala `0-100` (mais legível para teste/log); ao escrever
    o `.xlsx` real no futuro, converter para fração e aplicar formatação de porcentagem.

    A última coluna (**"Contestação a enviar"**, AI/09 §1 e ToBe HU-10 §474) é `"S"` quando
    a variação de `R$_Bruto` é `>= limiar_variacao` (1% por padrão), senão `"N"`. **Par
    ausente** (só um dos lados tem tráfego) é preenchido com **zero** no lado ausente
    (AI/09 §1) — a variação nesse caso é tratada como 100% (o lado presente é integralmente
    "diferença").

    Descritores não mapeados são ignorados (AI/09 §7); colisões de caractere final já são
    resolvidas deterministicamente (D-5, filtro `produto` + primeira ocorrência).

    Args:
        df_operadora: Aba `{operadora}` consolidada (T-020), sem linhas de total.
        df_tbra: Aba `TBRA` consolidada (T-021), sem linhas de total.
        indice_descritor: Índice (0-based) da coluna de descritor. **Sem posição fixa na
            documentação** — não hardcoded, deve ser informado pelo chamador.
        indice_remuneracao: Índice `descritor final -> [remunerações]` (ver
            :func:`src.services.mapa_remuneracao.construir_indice_remuneracao`).
        mapa_tipo_operacao: Opcional, ``{eot_devedora: "SMP"/"STFC"}`` para rotular a linha
            (AI/09 §0/§1: Tipo de Operação baseado na EOT Vivo/tipo de serviço). ``None``
            omite a coluna.
        limiar_variacao: Fração mínima de variação de `R$_Bruto` para contestar (AI/09 §1:
            `< 1% => N`, `>= 1% => S`). Default = `constantes_epico4.LIMIAR_VARIACAO_CONTESTACAO`.
        indice_credora, indice_devedora, indice_trafego, indice_minutos, indice_r_bruto:
            Índices documentados (D-8) das demais colunas usadas na chave/soma.

    Returns:
        DataFrame com uma linha por combinação, colunas: ``eot_devedora``,
        ``eot_credora``, ``remuneracao``, ``trafego``, ``minutos_tbra``, ``vb_tbra``,
        ``minutos_operadora``, ``vb_operadora``, ``minutos_diferenca``, ``vb_diferenca``,
        ``minutos_variacao_perc``, ``vb_variacao_perc``, ``contestacao_a_enviar`` (e
        ``tipo_operacao`` se ``mapa_tipo_operacao`` for informado).
    """

    agg_operadora = _agregar_por_chave(
        df_operadora, indice_descritor, indice_remuneracao, indice_credora, indice_devedora,
        indice_trafego, indice_minutos, indice_r_bruto, "minutos_operadora", "vb_operadora",
    )
    agg_tbra = _agregar_por_chave(
        df_tbra, indice_descritor, indice_remuneracao, indice_credora, indice_devedora,
        indice_trafego, indice_minutos, indice_r_bruto, "minutos_tbra", "vb_tbra",
    )

    chave = ["eot_credora", "eot_devedora", "remuneracao", "trafego"]
    contest = pd.merge(agg_operadora, agg_tbra, on=chave, how="outer")

    for coluna in ["minutos_operadora", "vb_operadora", "minutos_tbra", "vb_tbra"]:
        contest[coluna] = contest[coluna].fillna(0.0)

    contest["minutos_diferenca"] = contest["minutos_operadora"] - contest["minutos_tbra"]
    contest["vb_diferenca"] = contest["vb_operadora"] - contest["vb_tbra"]

    def _variacao(diferenca: pd.Series, base: pd.Series, alternativa: pd.Series) -> pd.Series:
        # Par ausente no lado "base" (base == 0): a variação é 100% se o outro lado tiver
        # valor; 0% se ambos os lados forem zero (nada a comparar).
        com_base = base.to_numpy() != 0
        com_alternativa = alternativa.to_numpy() != 0
        # Evita divisão por zero: usa 1.0 como base "segura" onde base==0 (resultado
        # descartado pelo np.where logo em seguida).
        base_segura = np.where(com_base, base.to_numpy(), 1.0)
        variacao_com_base = np.abs(diferenca.to_numpy() / base_segura) * 100
        resultado = np.where(com_base, variacao_com_base, np.where(com_alternativa, 100.0, 0.0))
        return pd.Series(resultado, index=diferenca.index)

    contest["minutos_variacao_perc"] = _variacao(
        contest["minutos_diferenca"], contest["minutos_operadora"], contest["minutos_tbra"]
    )
    contest["vb_variacao_perc"] = _variacao(
        contest["vb_diferenca"], contest["vb_operadora"], contest["vb_tbra"]
    )

    contest["contestacao_a_enviar"] = (
        (contest["vb_variacao_perc"] / 100.0) >= limiar_variacao
    ).map({True: "S", False: "N"})

    if mapa_tipo_operacao is not None:
        contest["tipo_operacao"] = contest["eot_devedora"].map(mapa_tipo_operacao)

    logger.info(f"[Consolidação] Contest: {contest.shape[0]} combinação(ões) analisada(s).")
    return contest
