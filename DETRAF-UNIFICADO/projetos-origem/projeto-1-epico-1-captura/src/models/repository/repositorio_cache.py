from __future__ import annotations

from typing import Optional

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.config.configuration import (
    CAMINHO_SQLITE,
    DATABASE_RPA,
    ENV,
    HOST_BD_RPA,
    PORT_BD_RPA,
    SENHA_BD,
    USUARIO_BD,
)
from src.config.logger_config import logger

TABELAS_CACHE: list[str] = [
    "tbl_anexo5_processado",
]


class RepositorioCache:
    """
    Classe responsável por:

    - Gerenciar conexão com banco
    - Carregar tabelas em memória
    - Disponibilizar DataFrames cacheados
    - Reutilizar cache durante toda execução

    As tabelas são carregadas apenas uma vez.
    """

    _instance: Optional["RepositorioCache"] = None
    _engine: Optional[Engine] = None

    def __new__(cls) -> "RepositorioCache":
        """
        Implementa padrão Singleton.
        """

        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self) -> None:
        """
        Inicializa o repositório de cache.
        """

        if hasattr(self, "_inicializado"):
            return

        self._inicializado = True

        self.engine: Engine = self._obter_engine()

        self.tabelas: dict[str, pd.DataFrame] = {}

        self._carregar_tabelas()

    @classmethod
    def _obter_engine(cls) -> Engine:
        """
        Cria e reutiliza a engine do banco.
        """

        if cls._engine is not None:
            return cls._engine

        logger.info(f"Inicializando conexão banco ambiente [{ENV}]")

        if ENV == "dev":

            logger.info(f"Utilizando SQLite local [{CAMINHO_SQLITE}]")

            cls._engine = create_engine(f"sqlite:///{CAMINHO_SQLITE}")

            return cls._engine

        logger.info((f"Conectando MySQL " f"[{HOST_BD_RPA}:{PORT_BD_RPA}]"))

        cls._engine = create_engine(
            (
                f"mysql+pymysql://"
                f"{USUARIO_BD}:{SENHA_BD}"
                f"@{HOST_BD_RPA}:{PORT_BD_RPA}"
                f"/{DATABASE_RPA}"
            ),
            pool_pre_ping=True,
        )

        return cls._engine

    def _carregar_tabelas(self) -> None:
        """
        Carrega todas as tabelas configuradas
        em memória.

        Levanta exceção caso alguma tabela
        não possa ser carregada.
        """

        logger.info("Iniciando carregamento tabelas em memória")

        for nome_tabela in TABELAS_CACHE:

            self.tabelas[nome_tabela] = self._carregar_tabela(nome_tabela=nome_tabela)

        logger.info("Todas as tabelas foram carregadas com sucesso")

    def _carregar_tabela(self, nome_tabela: str) -> pd.DataFrame:
        """
        Carrega uma tabela completa para memória.

        Args:
            nome_tabela:
                Nome da tabela no banco.

        Returns:
            DataFrame contendo toda tabela.

        Raises:
            RuntimeError:
                Caso ocorra erro ao carregar.
        """

        logger.info(f"Carregando tabela [{nome_tabela}]")

        try:

            df: pd.DataFrame = pd.read_sql(
                sql=f"SELECT * FROM {nome_tabela}", con=self.engine
            )

            logger.info(
                (
                    f"Tabela [{nome_tabela}] carregada "
                    f"com sucesso | "
                    f"Linhas: {len(df)} | "
                    f"Colunas: {len(df.columns)}"
                )
            )

            return df

        except Exception as erro:

            mensagem_erro: str = f"Erro ao carregar tabela " f"[{nome_tabela}]: {erro}"

            logger.error(mensagem_erro)

            raise RuntimeError(mensagem_erro) from erro

    def obter_tabela(self, nome_tabela: str) -> pd.DataFrame:
        """
        Retorna uma tabela carregada em memória.

        Args:
            nome_tabela:
                Nome da tabela desejada.

        Returns:
            DataFrame da tabela.

        Raises:
            KeyError:
                Caso tabela não exista no cache.
        """

        if nome_tabela not in self.tabelas:

            raise KeyError((f"Tabela [{nome_tabela}] " f"não encontrada no cache"))

        return self.tabelas[nome_tabela]

    def salvar_dados_tabela_despesa(self, df_consolidado: pd.DataFrame) -> None:
        """
        Insere o DataFrame consolidado de resultados diretamente na tabela
        'tbl_detraf_despesa_arquivos' utilizando a conexão ativa da Engine.

        Garante alta performance em lotes e proteção contra falhas de I/O.
        """
        # 1. Validação de segurança: Impede chamadas desnecessárias se não houver dados
        if df_consolidado is None or df_consolidado.empty:
            logger.info(
                "Nenhum registro encontrado para inserção na tabela [tbl_detraf_despesa_arquivos]."
            )
            return

        nome_tabela = "tbl_detraf_despesa_arquivos"
        total_linhas = len(df_consolidado)

        logger.info(
            f"Iniciando a inserção de {total_linhas} registro(s) na tabela [{nome_tabela}]."
        )

        try:
            # 2. Execução da escrita blindada em banco de dados
            df_consolidado.to_sql(
                name=nome_tabela,
                con=self.engine,
                if_exists="append",  # Mantém o histórico e adiciona os novos dados ao final
                index=False,  # Ignora o índice do Pandas (permite que o 'id' PK auto-increment do banco funcione)
                chunksize=1000,  # Fraciona em blocos de 1000 para mitigar estouro de memória/timeout
            )

            logger.info(
                f"Sucesso: {total_linhas} registro(s) foram persistidos com êxito na "
                f"tabela original [{nome_tabela}]."
            )

        except Exception as erro:
            mensagem_erro = (
                f"Falha crítica ao tentar inserir o lote de dados na tabela [{nome_tabela}]. "
                f"Motivo do banco: {erro}"
            )
            logger.error(mensagem_erro)

            # Levanta uma exceção tratada para interromper a esteira do RPA de forma segura
            raise RuntimeError(mensagem_erro) from erro
