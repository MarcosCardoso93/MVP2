"""Derivação da árvore de pastas de I/O do Épico 4 (AI/09 §9, AI/10).

Estrutura por operadora/mês::

    {raiz_operadoras}\\{operadora}\\{ano}\\{aaaamm}\\
        ├── Detrafs Recebidos   (entrada — arquivos da operadora)
        ├── Detrafs Enviados    (entrada — expectativa Vivo `_D_`)
        ├── AGI                 (saída — EXT/INT, HU-12/13)
        └── Contestações        (saída — _ENV, carta, Base_Contestação, HU-14)

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

from src.config import configuration as cfg


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
    """Subpasta de saída Contestações (_ENV, carta, Base_Contestação — HU-14)."""

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
    """

    raiz = (
        Path(raiz_controle_ct)
        if raiz_controle_ct is not None
        else cfg.CAMINHO_CONTROLE_CT
    )
    caminho = raiz / ano_de(aaaamm)

    if criar:
        caminho.mkdir(parents=True, exist_ok=True)

    return caminho
