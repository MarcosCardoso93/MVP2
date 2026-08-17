"""Derivação da árvore de pastas de I/O do Épico 4 (AI/09 §9, AI/10).

Estrutura por operadora/mês::

    {raiz_operadoras}\\{operadora}\\{ano}\\{aaaamm}\\
        ├── Detrafs Recebidos   (entrada — arquivos da operadora)
        ├── Detrafs Enviados    (entrada — expectativa Vivo `_D_`)
        ├── AGI                 (saída — EXT/INT, HU-12/13)
        └── Contestações        (saída — _EXP, carta, Base_Contestação, HU-14)

Nota: a HU-19 (Épico 6, D-15) não usa pasta/planilha — grava direto no banco
(`tbl_rpa_log_detraf_despesa_contestacao`, D-16 revisada 2026-07-28).

Fora da árvore da operadora::

    {raiz_controle_ct}\\{ano}   (controle de numeração CT + cópia da carta)

Os nomes das subpastas são configuráveis (``configuration.py``). As funções são
puras: recebem as raízes como argumento (default = variáveis de ambiente), o que
as torna testáveis contra ``tmp_path``. ``criar=True`` cria a árvore no disco.
"""

from __future__ import annotations

from pathlib import Path

from comum.config import configuration as cfg


def ano_de(aaaamm: str) -> str:
    """
    Extrai o ano (``AAAA``) de um período ``AAAAMM``.

    Raises:
        ValueError: Se ``aaaamm`` não estiver no formato ``AAAAMM``.
    """

    periodo = str(aaaamm).strip()
    if not (periodo.isdigit() and len(periodo) == 6):
        raise ValueError(
            f"Período deve estar no formato 'AAAAMM' (ex.: '202606'). Recebido: [{aaaamm!r}]"
        )
    return periodo[:4]


def listar_operadoras_do_mes(
    aaaamm: str,
    raiz_operadoras: Path | None = None,
    subpasta: str | None = None,
) -> list[str]:
    """
    Nomes das operadoras que têm árvore para o mês.

    Uma "operadora" é uma pasta de primeiro nível sob a raiz que tenha
    ``{operadora}/{ano}/{aaaamm}`` — e, se ``subpasta`` for dada, também ela.
    Nenhuma normalização de caixa: o nome da pasta física é a fonte de verdade,
    porque é ele que `caminho_mes_operadora` remonta depois.

    Esta varredura estava **duplicada** no RPA 2 (`batimento_detraf` e
    `validacao_detrafs`), e o RPA 3 precisava dela para saber o que processar.

    Args:
        aaaamm: Período de referência.
        raiz_operadoras: Raiz "...\\Operadoras". Default: ``CAMINHO_OPERADORAS``.
        subpasta: Exige também esta subpasta (ex.: ``SUBPASTA_DETRAFS_RECEBIDOS``).

    Returns:
        Nomes ordenados. Lista vazia se a raiz não existir — quem chama decide se
        isso é erro; aqui não é, porque um mês sem nenhuma operadora é um estado
        possível.
    """

    raiz = Path(raiz_operadoras) if raiz_operadoras is not None else cfg.CAMINHO_OPERADORAS

    if not raiz.is_dir():
        return []

    ano = ano_de(aaaamm)
    encontradas: list[str] = []

    for pasta_operadora in sorted(raiz.iterdir()):
        if not pasta_operadora.is_dir():
            continue

        alvo = pasta_operadora / ano / str(aaaamm)
        if subpasta:
            alvo = alvo / subpasta

        if alvo.is_dir():
            encontradas.append(pasta_operadora.name)

    return encontradas


def caminho_mes_operadora(
    operadora: str,
    aaaamm: str,
    raiz_operadoras: Path | None = None,
    criar: bool = False,
) -> Path:
    """
    Caminho da pasta do mês de uma operadora: ``{raiz}\\{op}\\{ano}\\{aaaamm}``.

    Args:
        operadora: Nome da operadora (usado como nome de pasta, sem normalização
            de caixa — a pasta física preserva o nome tal como no repositório).
        aaaamm: Período de referência ``AAAAMM``.
        raiz_operadoras: Raiz "...\\Operadoras". Default: ``CAMINHO_OPERADORAS``.
        criar: Se ``True``, cria a pasta (e as pais) no disco.

    Returns:
        O :class:`~pathlib.Path` da pasta do mês.
    """

    raiz = Path(raiz_operadoras) if raiz_operadoras is not None else cfg.CAMINHO_OPERADORAS
    ano = ano_de(aaaamm)
    caminho = raiz / str(operadora).strip() / ano / str(aaaamm).strip()

    if criar:
        caminho.mkdir(parents=True, exist_ok=True)

    return caminho


def _subpasta(
    subpasta: str,
    operadora: str,
    aaaamm: str,
    raiz_operadoras: Path | None,
    criar: bool,
) -> Path:
    """Helper: caminho de uma subpasta do mês da operadora."""

    base = caminho_mes_operadora(
        operadora, aaaamm, raiz_operadoras=raiz_operadoras, criar=False
    )
    caminho = base / subpasta

    if criar:
        caminho.mkdir(parents=True, exist_ok=True)

    return caminho


def caminho_detrafs_recebidos(
    operadora: str,
    aaaamm: str,
    raiz_operadoras: Path | None = None,
    criar: bool = False,
) -> Path:
    """Subpasta de entrada dos Detrafs da operadora."""

    return _subpasta(
        cfg.SUBPASTA_DETRAFS_RECEBIDOS, operadora, aaaamm, raiz_operadoras, criar
    )


def caminho_detrafs_enviados(
    operadora: str,
    aaaamm: str,
    raiz_operadoras: Path | None = None,
    criar: bool = False,
) -> Path:
    """Subpasta de entrada da expectativa Vivo (``_D_``)."""

    return _subpasta(
        cfg.SUBPASTA_DETRAFS_ENVIADOS, operadora, aaaamm, raiz_operadoras, criar
    )


def caminho_agi(
    operadora: str,
    aaaamm: str,
    raiz_operadoras: Path | None = None,
    criar: bool = False,
) -> Path:
    """Subpasta de saída AGI (EXT/INT — HU-12/13)."""

    return _subpasta(cfg.SUBPASTA_AGI, operadora, aaaamm, raiz_operadoras, criar)


def caminho_contestacoes(
    operadora: str,
    aaaamm: str,
    raiz_operadoras: Path | None = None,
    criar: bool = False,
) -> Path:
    """Subpasta de saída Contestações (_EXP, carta, Base_Contestação — HU-14)."""

    return _subpasta(
        cfg.SUBPASTA_CONTESTACOES, operadora, aaaamm, raiz_operadoras, criar
    )


def caminho_controle_ct(
    aaaamm: str,
    raiz_controle_ct: Path | None = None,
    criar: bool = False,
) -> Path:
    """
    Pasta de controle de numeração CT do ano: ``{raiz_ct}\\{ano}``.

    Fica **fora** da árvore da operadora (AI/09 §9). Guarda o controle de
    numeração e a cópia da carta.

    Raises:
        ValueError: Se `CAMINHO_CONTROLE_CT` não estiver configurado. É pré-condição
            da HU-14: sem essa pasta não há como saber o último número CT emitido, e
            emitir mesmo assim arriscaria duplicar a numeração — o que a decisão do
            cliente de 2026-07-31 proíbe.
    """

    raiz = (
        Path(raiz_controle_ct)
        if raiz_controle_ct is not None
        else cfg.CAMINHO_CONTROLE_CT
    )

    if raiz is None:
        raise ValueError(
            "CAMINHO_CONTROLE_CT não está configurado. É a pasta "
            "'...\\Correspondências Enviadas\\CT', de onde sai o último número de "
            "carta emitido — sem ela a HU-14 não pode gerar carta sem arriscar "
            "duplicar a numeração."
        )

    caminho = raiz / ano_de(aaaamm)

    if criar:
        caminho.mkdir(parents=True, exist_ok=True)

    return caminho


# ---------------------------------------------------------------------------
# Saída da validação (RPA 2) — 2026-08-10
#
# Os artefatos (`_EXP`, `_ERRO`, `_BK`, `_RECUSADO.md`) saíam ao lado do insumo.
# Agora vão para uma árvore própria, que espelha a origem:
#
#     {raiz_saida}\\{aaaamm}\\Operadoras\\{operadora}\\{subpasta}
#     {raiz_saida}\\{aaaamm}\\Expectativa\\{pasta}
#
# 🔴 `Operadoras` e `Expectativa` são separados de propósito. Sem essa divisão,
# a pasta `Expectativa` ficaria irmã dos nomes de operadora, e quem varre a raiz
# tratando todo diretório como uma operadora — que é o que o batimento faz —
# processaria a expectativa como se fosse uma.
#
# ⚠️ Estas funções são o **contrato** entre quem grava e quem lê. Antes desta
# data, a validação gravava em `{operadora}/{ano}/{aaaamm}/Detrafs Recebidos` e
# o batimento procurava em `{operadora}/{ano}/{aaaamm}` — nunca achava nada, e o
# lado da operadora entrava zerado na contestação, com variação de -100%. Um
# caminho derivado em dois lugares diverge; aqui ele é derivado num só.
# ---------------------------------------------------------------------------


def _raiz_saida(raiz_saida: Path | None) -> Path:
    return Path(raiz_saida) if raiz_saida is not None else cfg.DIRETORIO_SAIDA_VALIDACAO


def caminho_saida_operadora(
    operadora: str,
    aaaamm: str,
    raiz_saida: Path | None = None,
    subpasta: str | None = None,
    criar: bool = False,
) -> Path:
    """Onde a validação entrega os artefatos do Detraf de uma operadora."""

    caminho = (
        _raiz_saida(raiz_saida)
        / str(aaaamm).strip()
        / "Operadoras"
        / str(operadora).strip()
        / (subpasta if subpasta is not None else cfg.SUBPASTA_DETRAFS_RECEBIDOS)
    )

    if criar:
        caminho.mkdir(parents=True, exist_ok=True)

    return caminho


def caminho_saida_expectativa(
    pasta: str,
    aaaamm: str,
    raiz_saida: Path | None = None,
    criar: bool = False,
) -> Path:
    """Onde a validação entrega os artefatos da expectativa (`Vivo`, `TLF`)."""

    caminho = (
        _raiz_saida(raiz_saida) / str(aaaamm).strip() / "Expectativa" / str(pasta).strip()
    )

    if criar:
        caminho.mkdir(parents=True, exist_ok=True)

    return caminho


def listar_operadoras_com_saida(
    aaaamm: str,
    raiz_saida: Path | None = None,
) -> list[str]:
    """
    Operadoras que têm artefato entregue no mês.

    O equivalente de `listar_operadoras_do_mes` do outro lado da cadeia: é por
    aqui que o batimento descobre o que a validação produziu, em vez de varrer a
    árvore de entrada.
    """

    raiz = _raiz_saida(raiz_saida) / str(aaaamm).strip() / "Operadoras"
    if not raiz.is_dir():
        return []

    return sorted(pasta.name for pasta in raiz.iterdir() if pasta.is_dir())


def caminho_de_saida(
    pasta_origem: Path,
    aaaamm: str,
    raiz_saida: Path | None = None,
    raiz_operadoras: Path | None = None,
    raiz_expectativa: Path | None = None,
    criar: bool = False,
) -> Path | None:
    """
    A pasta de saída correspondente a uma pasta de origem.

    É o que `AreaDeTrabalho.promover` usa para saber para onde devolver cada
    artefato, sem precisar saber nada sobre a estrutura das duas árvores.

    Returns:
        A pasta de saída, ou ``None`` quando a origem não está sob nenhuma das
        duas raízes conhecidas — caso em que quem chama decide o que fazer.
        Devolver um palpite seria pior: o artefato apareceria num lugar que
        ninguém lê.
    """

    origem = Path(pasta_origem).resolve()
    operadoras = Path(
        raiz_operadoras if raiz_operadoras is not None else cfg.CAMINHO_OPERADORAS
    ).resolve()
    expectativa = (
        raiz_expectativa
        if raiz_expectativa is not None
        else cfg.CAMINHO_EXPECTATIVA_DETRAF
    )

    if origem.is_relative_to(operadoras):
        # {operadora}/{ano}/{aaaamm}/{subpasta} — o ano e o mês somem, porque a
        # raiz de saída já é por mês.
        partes = origem.relative_to(operadoras).parts
        if len(partes) < 4:
            return None
        return caminho_saida_operadora(
            partes[0], aaaamm, raiz_saida, subpasta=partes[3], criar=criar
        )

    if expectativa is not None and origem.is_relative_to(Path(expectativa).resolve()):
        partes = origem.relative_to(Path(expectativa).resolve()).parts
        if not partes:
            return None
        return caminho_saida_expectativa(partes[0], aaaamm, raiz_saida, criar=criar)

    return None


def construir_caminho_saida(
    raiz: Path,
    operadora: str,
    ano: str,
    competencia: str,
) -> Path:
    """
    Monta ``{raiz}/{operadora}/{ano}/{aaaamm}``.

    Origem: ``utils/filesystem.py`` do Projeto 1. É a mesma estrutura que
    :func:`caminho_mes_operadora` monta a partir da configuração — a diferença
    é que aqui a raiz vem por parâmetro (duplicação D-18).

    Args:
        raiz: Diretório raiz de saída.
        operadora: Nome da operadora, usado como subdiretório.
        ano: Ano no formato ``YYYY``.
        competencia: Competência no formato ``YYYYMM``.

    Returns:
        Caminho completo, sem criar nada em disco.

    Examples:
        >>> construir_caminho_saida(Path("Saida"), "ALGAR", "2026", "202605").as_posix()
        'Saida/ALGAR/2026/202605'
    """
    return raiz / operadora / ano / competencia
