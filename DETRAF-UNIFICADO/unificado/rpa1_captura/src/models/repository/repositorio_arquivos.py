import shutil
from pathlib import Path
from typing import List

from comum.config import configuration
from comum.config.logger_config import logger


class RepositorioArquivos:
    """
    Repositório para leitura, criação de diretórios e cópia de arquivos.

    Implementa o padrão Repository para abstrair o acesso ao sistema
    de arquivos, facilitando testes e manutenção.
    """

    def listar_arquivos(self, diretorio: Path) -> List[Path]:
        """
        Lista os arquivos válidos na raiz do diretório informado.

        Não realiza busca recursiva em subdiretórios.
        Filtra pelos tipos definidos em EXTENSOES_PERMITIDAS.

        Args:
            diretorio: Caminho do diretório a ser lido.

        Returns:
            Lista de caminhos de arquivos com extensão permitida.

        Raises:
            FileNotFoundError: Se o diretório não existir.
            NotADirectoryError: Se o caminho não for um diretório.
        """
        if not diretorio.exists():
            raise FileNotFoundError(
                f"Diretório de entrada não encontrado: {diretorio}"
            )

        if not diretorio.is_dir():
            raise NotADirectoryError(
                f"O caminho informado não é um diretório: {diretorio}"
            )

        arquivos_validos = [
            arquivo
            for arquivo in diretorio.iterdir()
            if arquivo.is_file()
            and arquivo.suffix.lower() in configuration.EXTENSOES_PERMITIDAS
        ]

        logger.debug(
            f"{len(arquivos_validos)} arquivo(s) válido(s) encontrado(s) "
            f"em '{diretorio}'"
        )
        return arquivos_validos

    def criar_diretorio(self, diretorio: Path) -> None:
        """
        Cria o diretório informado, incluindo todos os intermediários.

        Opera de forma idempotente: não gera erro se o diretório já existir.

        Args:
            diretorio: Caminho do diretório a ser criado.

        Returns:
            None.
        """
        diretorio.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Diretório garantido: {diretorio}")

    def copiar_arquivo(self, origem: Path, destino: Path) -> None:
        """
        Copia um arquivo preservando seus metadados originais.

        Utiliza shutil.copy2 para preservar datas de acesso,
        modificação e permissões do arquivo de origem.

        Args:
            origem: Caminho do arquivo de origem.
            destino: Caminho completo de destino (incluindo nome do arquivo).

        Returns:
            None.

        Raises:
            FileNotFoundError: Se o arquivo de origem não existir.
            PermissionError: Se não houver permissão de escrita no destino.
        """
        shutil.copy2(origem, destino)
        logger.debug(f"Copiado: '{origem.name}' → '{destino.parent}'")

    def clonar_estrutura_mes_anterior(self, origem: Path, destino: Path) -> None:
        """
        Cria `destino` clonando apenas a estrutura de subdiretórios de `origem`.

        Usado quando a pasta do mês atual ainda não existe: em vez de criá-la
        vazia, replica as subpastas do mês anterior (sem copiar arquivos).
        Se `origem` não existir, degrada graciosamente criando apenas
        `destino` vazio.

        Args:
            origem: Diretório do mês anterior (referência de estrutura).
            destino: Diretório do mês atual a ser criado.

        Returns:
            None.
        """
        destino.mkdir(parents=True, exist_ok=True)

        if not origem.exists():
            logger.warning(
                f"Estrutura do mês anterior não encontrada em '{origem}' — "
                f"criando '{destino}' vazio."
            )
            return

        subdiretorios = [caminho for caminho in origem.rglob("*") if caminho.is_dir()]
        for subdiretorio in subdiretorios:
            relativo = subdiretorio.relative_to(origem)
            (destino / relativo).mkdir(parents=True, exist_ok=True)

        logger.debug(
            f"Estrutura clonada de '{origem}' para '{destino}' "
            f"({len(subdiretorios)} subpasta(s))"
        )
