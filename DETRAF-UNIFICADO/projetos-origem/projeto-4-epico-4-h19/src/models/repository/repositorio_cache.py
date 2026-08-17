from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config.configuration import (
    CAMINHO_SQLITE,
    DATABASE_RPA,
    HOST_BD_RPA,
    PORT_BD_RPA,
    SENHA_BD,
    USUARIO_BD,
)

# Tabelas de referência carregadas em RAM uma única vez (AI/01 §6).
TABELAS_CACHE: list[str] = [
    "tbl_anexo5_processado",
    "tbl_detraf_tarifas",
    "tbl_detraf_mapeamento_descritores",
    "tbl_rpa_log_detraf_despesa_contestacao",
]

# Caminho default do SQLite de dev quando CAMINHO_SQLITE não é informado.
# Fica dentro do projeto (não mais hardcoded para outra máquina — T-003).
_SQLITE_DEV_DEFAULT: Path = (
    Path(__file__).resolve().parents[3] / "data" / "dev" / "TABELAS_DETRAF.db"
)


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
    def resetar(cls) -> None:
        """
        Descarta a instância e a engine cacheadas.

        Uso exclusivo de testes: garante que cada teste possa reconstruir o
        Singleton apontando para um SQLite temporário diferente. A engine é
        **descartada** (``dispose``) para não deixar conexões abertas segurando o
        arquivo do banco.
        """

        if cls._engine is not None:
            cls._engine.dispose()

        cls._instance = None
        cls._engine = None

    @classmethod
    def _obter_engine(cls) -> Engine:
        """
        Cria e reutiliza a engine do banco.
        """

        if cls._engine is not None:
            return cls._engine

        env: str = os.getenv("ENV", "dev").lower()

        logger.info(f"Inicializando conexão banco ambiente [{env}]")

        if env == "dev":

            caminho_banco: Path = (
                Path(CAMINHO_SQLITE) if CAMINHO_SQLITE else _SQLITE_DEV_DEFAULT
            )

            logger.info(f"Utilizando SQLite local [{caminho_banco}]")

            cls._engine = create_engine(f"sqlite:///{caminho_banco}")

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

    @staticmethod
    def _validar_tabela_escrita(nome_tabela: str) -> None:
        """
        Garante que a escrita só ocorra em tabelas conhecidas (``TABELAS_CACHE``).

        Raises:
            KeyError: Caso ``nome_tabela`` não esteja em ``TABELAS_CACHE``.
        """

        if nome_tabela not in TABELAS_CACHE:

            raise KeyError(
                f"Tabela [{nome_tabela}] não é uma tabela de escrita conhecida "
                f"(esperado uma de {TABELAS_CACHE})"
            )

    def inserir_dados(self, nome_tabela: str, dados: pd.DataFrame) -> None:
        """
        Insere novas linhas em ``nome_tabela`` (banco) e sincroniza o cache em RAM.

        Método de escrita do repositório (AI/01 §1: só o `RepositorioCache` fala com o
        banco). Para atualizar linhas já existentes, use ``atualizar_dados``.

        Args:
            nome_tabela: Nome da tabela de destino (deve estar em ``TABELAS_CACHE``).
            dados: Linhas a inserir. Nada é feito se vazio.

        Raises:
            KeyError: Caso ``nome_tabela`` não esteja em ``TABELAS_CACHE``.
        """

        self._validar_tabela_escrita(nome_tabela=nome_tabela)

        if dados is None or dados.empty:
            logger.info(f"[RepositorioCache] Nada a inserir em [{nome_tabela}] (vazio).")
            return

        dados.to_sql(nome_tabela, con=self.engine, if_exists="append", index=False)
        logger.info(f"[RepositorioCache] {len(dados)} linha(s) inserida(s) em [{nome_tabela}].")

        self._atualizar_cache_local(nome_tabela, dados)

    def atualizar_dados(
        self,
        nome_tabela: str,
        valores: dict,
        chave: dict,
        sincronizar_cache: bool = True,
    ) -> int:
        """
        Atualiza (``UPDATE``) as linhas de ``nome_tabela`` que casam com ``chave``.

        Contrapartida de ``inserir_dados`` para os fluxos em que a linha já existe no
        banco: a HU-19 (D-20) preenche a despesa apresentada pela operadora e a HU-16
        (D-19) regrava `tipo_contestacao`. Em ambos os casos a linha-base é inserida
        pelo Épico 3, fora deste projeto.

        A SQL é parametrizada (`sqlalchemy.text` + bind params) e roda dentro de uma
        transação (`engine.begin`). O cache em RAM é recarregado do banco ao final,
        pois um ``UPDATE`` não é reproduzível por concatenação.

        Args:
            nome_tabela: Tabela de destino (deve estar em ``TABELAS_CACHE``).
            valores: Colunas a atualizar → novo valor. Nada é feito se vazio.
            chave: Colunas do filtro → valor esperado. Obrigatório (um ``UPDATE`` sem
                ``WHERE`` atingiria a tabela inteira).
            sincronizar_cache: Se ``False``, não relê a tabela após o ``UPDATE`` — quem
                chama fica responsável por ressincronizar. Usado em lotes, para não
                pagar um ``SELECT *`` por linha atualizada.

        Returns:
            Número de linhas efetivamente atualizadas (0 = chave inexistente).

        Raises:
            KeyError: Caso ``nome_tabela`` não esteja em ``TABELAS_CACHE``.
            ValueError: Caso ``chave`` esteja vazia.
        """

        self._validar_tabela_escrita(nome_tabela=nome_tabela)

        if not chave:

            raise ValueError(
                f"UPDATE em [{nome_tabela}] exige uma chave — "
                f"atualização sem WHERE não é permitida"
            )

        if not valores:
            logger.info(f"[RepositorioCache] Nada a atualizar em [{nome_tabela}] (vazio).")
            return 0

        # Prefixos distintos evitam colisão quando a mesma coluna aparece nos dois lados.
        atribuicoes: str = ", ".join(f"{coluna} = :set_{coluna}" for coluna in valores)
        filtros: str = " AND ".join(f"{coluna} = :key_{coluna}" for coluna in chave)

        parametros: dict = {f"set_{coluna}": valor for coluna, valor in valores.items()}
        parametros.update({f"key_{coluna}": valor for coluna, valor in chave.items()})

        sql = text(f"UPDATE {nome_tabela} SET {atribuicoes} WHERE {filtros}")

        with self.engine.begin() as conexao:
            resultado = conexao.execute(sql, parametros)
            linhas_afetadas: int = int(resultado.rowcount or 0)

        logger.info(
            f"[RepositorioCache] {linhas_afetadas} linha(s) atualizada(s) "
            f"em [{nome_tabela}]."
        )

        if linhas_afetadas and sincronizar_cache:
            self.recarregar_cache_local(nome_tabela=nome_tabela)

        return linhas_afetadas

    def recarregar_cache_local(self, nome_tabela: str) -> None:
        """
        Relê a tabela do banco e substitui a versão em RAM.

        Usado após ``UPDATE``, onde não há como sincronizar o cache por concatenação.
        """

        self.tabelas[nome_tabela] = self._carregar_tabela(nome_tabela=nome_tabela)

    def _atualizar_cache_local(
        self, nome_tabela: str, df_novos_dados: pd.DataFrame
    ) -> None:
        """
        Atualiza o cache em memória RAM concatenando os novos dados inseridos
        ao DataFrame já existente, evitando um novo SELECT no banco de dados.
        """
        if df_novos_dados is None or df_novos_dados.empty:
            return

        logger.info(f"Sincronizando cache em memória para a tabela [{nome_tabela}].")

        if nome_tabela in self.tabelas:
            self.tabelas[nome_tabela] = pd.concat(
                [self.tabelas[nome_tabela], df_novos_dados], ignore_index=True
            )
        else:
            self.tabelas[nome_tabela] = df_novos_dados.copy()

        logger.info(
            f"Cache da tabela [{nome_tabela}] atualizado com sucesso. "
            f"Total atual em memória: {len(self.tabelas[nome_tabela])} linhas."
        )
