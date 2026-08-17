"""Resolver de remuneração a partir do descritor.

**Fonte (D-21, 2026-07-30 — adequação à V2 pág. 7):** a tabela
``tbl_detraf_mapeamento_descritores`` do banco Webfat — *"a relação entre descritores e
remuneração está disponível para consulta na tabela 'tbl_detraf_mapeamento_descritores'
do banco de dados webfat"*. Até 2026-07-30 a fonte era a planilha
`Mapeamento_Descritores.xlsx` (D-5); o CSV em `tests/fixtures/mapeamento_descritores.csv`
passou a ser apenas o **seed do SQLite de teste**, não mais fonte de produção.

Colunas esperadas (schema presumido pela D-21, a confirmar — bloqueio B-D21): ``id``,
``final_descritor``, ``remuneracao_fixa``, ``observacao``, ``produto``.

A chave de mapeamento é o **último caractere do descritor** (AI/09 §7: "Mapeamento pelo
caractere inicial e final do descritor"). Alimenta a coluna ``REMUNERACAO``/``REMUNERACAO_FIXA``
do EXT (T-042), INT (T-061), CONT_PROC (T-101) e o "tipo de tarifação" do Contest (T-023).

**Colisões de caractere final — RESOLVIDO (D-5, 2026-07-27):** o mapa real tem caracteres
finais repetidos com remunerações diferentes (``T``, ``M``, ``U``, ``W``, ``5``). Regra de
desambiguação confirmada pelo usuário: (1) filtrar apenas linhas com
``produto == "DETRAF"``; (2) se ainda houver mais de uma linha para o mesmo caractere
final após o filtro, usar a **primeira ocorrência** (ordem do arquivo/`id`). Ver
:func:`construir_indice_remuneracao`. Descritor cujo caractere final não está mapeado é
**ignorado** (retorna ``None``), conforme AI/09 §7 ("descritor não mapeado ⇒ ignorado").
"""

from __future__ import annotations

import pandas as pd

from src.config.logger_config import logger

PRODUTO_DETRAF = "DETRAF"

COLUNAS_MAPA_DESCRITORES = [
    "id",
    "final_descritor",
    "remuneracao_fixa",
    "observacao",
    "produto",
]


def carregar_mapa_descritores(mapa_bruto: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza o mapa `descritor final → remuneração` vindo do banco (D-21).

    Args:
        mapa_bruto: DataFrame de ``tbl_detraf_mapeamento_descritores``, tipicamente
            obtido por
            :meth:`src.models.repository.repositorio_tabelas.RepositorioTabelas.obter_mapa_descritores`.

    Returns:
        DataFrame com as colunas de :data:`COLUNAS_MAPA_DESCRITORES`, tudo como ``str``
        (consistente com L-006 — todo dado de negócio é lido como texto).

    Raises:
        ValueError: Caso alguma coluna esperada esteja ausente (schema divergente do
            presumido pela D-21 — ver bloqueio B-D21).
    """

    mapa = mapa_bruto.copy()
    mapa.columns = [str(coluna).strip() for coluna in mapa.columns]

    faltantes = [coluna for coluna in COLUNAS_MAPA_DESCRITORES if coluna not in mapa.columns]
    if faltantes:
        raise ValueError(
            f"tbl_detraf_mapeamento_descritores sem as colunas esperadas {faltantes} "
            f"(encontradas: {list(mapa.columns)}) — ver D-21/B-D21."
        )

    return mapa[COLUNAS_MAPA_DESCRITORES].astype(str)


def construir_indice_remuneracao(mapa: pd.DataFrame) -> dict[str, list[str]]:
    """
    Constrói o índice ``caractere final -> [remuneração]`` (D-5, colisões resolvidas).

    Regra de desambiguação confirmada pelo usuário (2026-07-27): considera **apenas**
    linhas com ``produto == "DETRAF"`` (comparação sem distinção de maiúsculas/espaços —
    a mesma tabela de origem cobre outros produtos além do DETRAF); dentre essas, se mais
    de uma linha ainda mapear o mesmo caractere final, **a primeira ocorrência vence**
    (ordem do arquivo). Por isso o valor do dicionário nunca tem mais de 1 item na
    prática — a lista é mantida só para compatibilidade com o contrato de
    :func:`resolver_remuneracao`.

    Args:
        mapa: DataFrame no formato de :func:`carregar_mapa_descritores`.

    Returns:
        Dicionário ``{caractere_final: [remuneracao]}`` (no máximo 1 candidato por chave).
    """

    if "produto" in mapa.columns:
        mapa = mapa[mapa["produto"].astype(str).str.strip().str.upper() == PRODUTO_DETRAF]

    indice: dict[str, list[str]] = {}
    for _, linha in mapa.iterrows():
        final = str(linha["final_descritor"]).strip()
        if final in indice:
            continue  # já resolvido pela primeira ocorrência (regra de desambiguação)
        remuneracao = str(linha["remuneracao_fixa"]).strip()
        indice[final] = [remuneracao]
    return indice


def resolver_remuneracao(
    descritor: str, indice: dict[str, list[str]]
) -> str | None:
    """
    Resolve a remuneração de um descritor pelo seu último caractere.

    Args:
        descritor: Descritor bruto do Detraf (ex.: ``"2NENI"``).
        indice: Índice produzido por :func:`construir_indice_remuneracao`.

    Returns:
        - A remuneração única, se o caractere final mapear para exatamente uma.
        - ``None`` se o caractere final não estiver mapeado (AI/09 §7: ignorado).

    Raises:
        ValueError: Guarda defensiva — não deve ocorrer na prática, já que
            :func:`construir_indice_remuneracao` sempre entrega no máximo 1 candidato
            por caractere final (colisões resolvidas via filtro `produto` + primeira
            ocorrência, D-5). Mantida para o caso de um índice construído manualmente
            ainda trazer múltiplos candidatos — nunca escolhe silenciosamente.
    """

    if not descritor:
        return None

    final = str(descritor).strip()[-1]
    candidatos = indice.get(final)

    if not candidatos:
        return None

    if len(candidatos) > 1:
        raise ValueError(
            f"Descritor com final '{final}' é ambíguo entre {candidatos} "
            f"(refino D-5: desambiguação por DS_OBS ainda não confirmada)."
        )

    return candidatos[0]


def resolver_series(
    descritores: pd.Series, indice: dict[str, list[str]]
) -> pd.Series:
    """
    Resolve a remuneração de uma coluna inteira de descritores (vetorizado por valor único).

    Reaproveitado por qualquer service que precise mapear `descritor → REMUNERACAO` em
    lote (Contest T-023, EXT T-042, INT T-061, CONT_PROC T-101) — evita duplicar a lógica
    de resolução linha a linha.

    Descritores **não mapeados** (AI/09 §7) resultam em ``None`` na posição
    correspondente — a linha nunca é descartada aqui; cabe ao chamador decidir se a
    mantém (ex.: EXT preserva todas as linhas) ou filtra (ex.: Contest ignora linhas sem
    remuneração resolvida). Colisões de caractere final já são resolvidas
    deterministicamente por :func:`construir_indice_remuneracao` (D-5) — o guard de
    ambiguidade abaixo é só defensivo (não deve disparar na prática).

    Args:
        descritores: Coluna (Series) de descritores brutos do Detraf.
        indice: Índice produzido por :func:`construir_indice_remuneracao`.

    Returns:
        Series do mesmo tamanho/índice, com a remuneração resolvida (ou ``None``).
    """

    descritores_str = descritores.astype(str)
    unicos = descritores_str.unique()

    mapa_local: dict[str, str | None] = {}
    ambiguos: list[str] = []

    for descritor in unicos:
        try:
            mapa_local[descritor] = resolver_remuneracao(descritor, indice)
        except ValueError:
            ambiguos.append(descritor)
            mapa_local[descritor] = None

    if ambiguos:
        logger.warning(
            f"[Remuneração] Descritores com índice ambíguo (inesperado após D-5, "
            f"ver construir_indice_remuneracao) ignorados: {ambiguos}"
        )

    return descritores_str.map(mapa_local)
