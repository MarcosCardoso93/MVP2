"""Utilitários para operações e manipulações com o sistema de arquivos."""

from datetime import datetime
from pathlib import Path

from dateutil.relativedelta import relativedelta

_UNIDADES = ("B", "KB", "MB", "GB", "TB")
_BASE_BYTES: int = 1024


def formatar_tamanho(tamanho_bytes: int) -> str:
    """
    Formata um tamanho em bytes para uma representação legível.

    Args:
        tamanho_bytes: Tamanho em bytes a ser formatado.

    Returns:
        String formatada com a unidade mais adequada.

    Examples:
        >>> formatar_tamanho(1024)
        '1.00 KB'
        >>> formatar_tamanho(1_048_576)
        '1.00 MB'
    """
    tamanho = float(tamanho_bytes)
    for unidade in _UNIDADES[:-1]:
        if abs(tamanho) < _BASE_BYTES:
            return f"{tamanho:.2f} {unidade}"
        tamanho /= _BASE_BYTES
    return f"{tamanho:.2f} {_UNIDADES[-1]}"


def obter_tamanho_arquivo(caminho: Path) -> str:
    """
    Retorna o tamanho de um arquivo em formato legível por humanos.

    Args:
        caminho: Caminho do arquivo.

    Returns:
        Tamanho formatado do arquivo.

    Raises:
        FileNotFoundError: Se o arquivo não existir.
    """
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    return formatar_tamanho(caminho.stat().st_size)


def construir_caminho_saida(
    raiz: Path,
    operadora: str,
    ano: str,
    competencia: str,
) -> Path:
    """
    Constrói o caminho de saída seguindo a estrutura padrão do projeto.

    Estrutura gerada: {raiz}/{OPERADORA}/{YYYY}/{YYYYMM}/

    Args:
        raiz: Diretório raiz de saída.
        operadora: Nome da operadora (usado como subdiretório).
        ano: Ano no formato YYYY.
        competencia: Competência no formato YYYYMM.

    Returns:
        Caminho completo de saída construído como objeto Path.

    Examples:
        >>> construir_caminho_saida(Path("Saida"), "ALGAR", "2026", "202605")
        PosixPath('Saida/ALGAR/2026/202605')
    """
    return raiz / operadora / ano / competencia


def mes_anterior(competencia: str) -> str:
    """
    Retorna a competência (YYYYMM) do mês civil anterior à informada.

    Args:
        competencia: Competência no formato YYYYMM.

    Returns:
        Competência do mês anterior, no formato YYYYMM.

    Examples:
        >>> mes_anterior("202506")
        '202505'
        >>> mes_anterior("202601")
        '202512'
    """
    data = datetime(int(competencia[:4]), int(competencia[4:6]), 1)
    return (data - relativedelta(months=1)).strftime("%Y%m")
