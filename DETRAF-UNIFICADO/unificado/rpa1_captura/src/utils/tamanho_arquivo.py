"""Formatação de tamanho de arquivo — exclusivo do RPA 1.

Origem: ``utils/filesystem.py`` do Projeto 1. As demais funções daquele arquivo
foram para a base comum (``construir_caminho_saida`` em
``comum.arquivos.estrutura_pastas``, ``mes_anterior`` em
``comum.dominio.competencia``); estas duas ficaram aqui por terem **uma única
ocorrência** — falham o critério C1 de compartilhamento. Promovem-se se um
segundo RPA precisar delas.
"""

from pathlib import Path

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
