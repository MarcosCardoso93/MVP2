from __future__ import annotations

from typing import Optional

import pandas as pd

from src.config.logger_config import logger
from src.models.repository.repositorio_cache import RepositorioCache


class RepositorioTabelas:
    """
    Classe responsável por centralizar
    consultas nas tabelas carregadas em cache.
    """

    def __init__(self) -> None:
        """
        Inicializa acesso às tabelas em memória.
        """

        self.cache = RepositorioCache()

        self.tbl_anexo5_processado: pd.DataFrame = self.cache.obter_tabela(
            "tbl_anexo5_processado"
        )

    def buscar_nome_fantasia(self, texto: str) -> Optional[str]:
        """
        Verifica se `texto` está contido (substring, case-insensitive)
        em algum valor da coluna 'Nome Fantasia' da tabela
        tbl_anexo5_processado.

        Args:
            texto:
                Texto a ser pesquisado dentro da coluna 'Nome Fantasia'.

        Returns:
            Nome Fantasia real cadastrado caso encontre.

            None caso não encontre.
        """

        texto_tratado: str = str(texto).strip().upper()

        coluna: pd.Series = self.tbl_anexo5_processado["Nome Fantasia"].astype(
            str
        ).str.strip()

        mascara = coluna.str.upper().str.contains(texto_tratado, na=False, regex=False)

        resultado: pd.DataFrame = self.tbl_anexo5_processado[mascara]

        if resultado.empty:

            logger.info(f"Nome Fantasia não encontrado para o texto [{texto}]")

            return None

        nome_fantasia: str = resultado.iloc[0]["Nome Fantasia"]

        return nome_fantasia

    def buscar_nome_fantasia_por_eot(self, eot: str) -> Optional[str]:
        """
        Busca o Nome Fantasia por correspondência exata do código EOT
        (Entidade Operadora de Telecomunicações, coluna 'EOT' do Anexo 5).

        Args:
            eot:
                Código EOT a pesquisar (ex.: "112").

        Returns:
            Nome Fantasia cadastrado para esse EOT, ou None caso não encontre.
        """

        resultado: pd.DataFrame = self.tbl_anexo5_processado[
            self.tbl_anexo5_processado["EOT"].astype(str).str.strip() == str(eot).strip()
        ]

        if resultado.empty:

            logger.info(f"Nome Fantasia não encontrado para o EOT [{eot}]")

            return None

        return resultado.iloc[0]["Nome Fantasia"]

    def salvar_dados_tabela_despesa(self, df_despesa: pd.DataFrame) -> None:
        """
        Salva os dados de despesa validados na tabela de despesas do banco.

        Args:
            df_despesa (pd.DataFrame): DataFrame contendo os dados de despesa a serem salvos.
        """

        self.cache.salvar_dados_tabela_despesa(df_despesa)


bd_tabelas = RepositorioTabelas()
