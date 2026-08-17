"""Conexão com o banco WebFat e cache das tabelas de consulta.

Singleton: a engine é criada uma vez e as tabelas de consulta são carregadas em
memória uma única vez por execução, evitando ida ao banco por linha.

Origem: unificação das quatro versões de ``repositorio_cache.py`` (duplicação
D-06). O corpo era o mesmo nos quatro; a única diferença real era a lista de
tabelas a carregar — que aqui passa a ser **parâmetro**.

Alterações intencionais registradas na unificação:

1. ``TABELAS_CACHE`` deixa de ser constante do módulo e vira parâmetro do
   construtor. Cada RPA declara o seu conjunto (ver ``tabelas.py``).
2. O caminho do SQLite vem apenas de ``CAMINHO_SQLITE``. O Projeto 2 tinha um
   caminho absoluto da máquina do desenvolvedor embutido como fallback
   (``repositorio_cache.py:82``); quando vazio, resolve-se um arquivo relativo
   ao projeto.
3. ``salvar_dados_tabela_despesa`` e ``salvar_dados_tabela_contestacao`` passam
   a delegar a um ``inserir`` genérico — eram duas cópias do mesmo corpo com o
   nome da tabela trocado.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from comum.config.configuration import (
    CAMINHO_SQLITE,
    DATABASE_RPA,
    ENV,
    HOST_BD_RPA,
    PORT_BD_RPA,
    SENHA_BD,
    USUARIO_BD,
)
from comum.config.logger_config import logger
from comum.dados import tabelas

#: Usado quando ENV=dev e CAMINHO_SQLITE está vazio.
_SQLITE_PADRAO = Path("banco_de_dados") / "TABELAS_DETRAF.db"

#: Linhas por bloco na escrita em lote.
_TAMANHO_BLOCO = 1000


class RepositorioCache:
    """Conexão única com o banco e cache das tabelas de consulta."""

    _instance: Optional["RepositorioCache"] = None
    _engine: Optional[Engine] = None

    def __new__(cls, tabelas_cache: Sequence[str] | None = None) -> "RepositorioCache":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, tabelas_cache: Sequence[str] | None = None) -> None:
        """
        Args:
            tabelas_cache: Tabelas a carregar em memória. Se ``None``, nenhuma
                é pré-carregada — útil para quem só escreve. Cada RPA passa o
                seu conjunto de ``comum.dados.tabelas``.
        """
        if hasattr(self, "_inicializado"):
            # Singleton já construído. Carrega o que ainda faltar, para o caso
            # de um segundo consumidor precisar de mais tabelas.
            if tabelas_cache:
                self.carregar(tabelas_cache)
            return

        self._inicializado = True
        self.engine: Engine = self._obter_engine()
        self.tabelas: dict[str, pd.DataFrame] = {}

        if tabelas_cache:
            self.carregar(tabelas_cache)

    # ------------------------------------------------------------------
    # Conexão
    # ------------------------------------------------------------------
    @classmethod
    def _obter_engine(cls) -> Engine:
        """
        Cria a engine na primeira chamada e a reutiliza depois.

        **Conecta de verdade aqui** (2026-08-06). `create_engine` é preguiçoso:
        até esta mudança, credencial errada, host inacessível e base inexistente
        só apareciam na primeira leitura de tabela, dentro de `_carregar_tabela`,
        como a mensagem crua do driver embrulhada num `RuntimeError` — e as três
        chegavam com a mesma cara, pedindo correções diferentes.

        Falhar aqui custa um segundo e diz o que fazer.
        """
        if cls._engine is not None:
            return cls._engine

        logger.info(f"Inicializando conexão com o banco no ambiente [{ENV}]")

        if ENV == "dev":
            caminho_banco = CAMINHO_SQLITE or str(_SQLITE_PADRAO)
            logger.info(f"Utilizando SQLite local [{caminho_banco}]")

            if not Path(caminho_banco).is_file():
                raise RuntimeError(
                    f"[BANCO] O SQLite [{caminho_banco}] não existe.\n"
                    f"  -> Gere-o com `python preparar_banco_dev.py` (dados dos "
                    f"projetos de origem) ou `python espelhar_banco.py` (cópia "
                    f"do banco real).\n"
                    f"  -> Se o caminho está errado, corrija CAMINHO_SQLITE no .env."
                )

            cls._engine = create_engine(f"sqlite:///{caminho_banco}")
            return cls._engine

        logger.info(f"Conectando ao MySQL [{HOST_BD_RPA}:{PORT_BD_RPA}]")

        engine = create_engine(
            f"mysql+pymysql://{USUARIO_BD}:{SENHA_BD}"
            f"@{HOST_BD_RPA}:{PORT_BD_RPA}/{DATABASE_RPA}",
            pool_pre_ping=True,
        )

        try:
            with engine.connect():
                pass
        except Exception as erro:
            # Import tardio: `diagnostico` importa a configuração, e trazê-lo no
            # topo criaria um ciclo com quem já importa este módulo.
            from comum.config.diagnostico import explicar_erro_de_banco

            causa, correcao = explicar_erro_de_banco(erro)
            engine.dispose()
            raise RuntimeError(
                f"[BANCO] Não foi possível conectar ao MySQL "
                f"[{HOST_BD_RPA}:{PORT_BD_RPA}/{DATABASE_RPA}]: {causa}.\n"
                f"  -> {correcao}\n"
                f"  -> Para conferir o ambiente inteiro de uma vez: "
                f"`python verificar_ambiente.py`."
            ) from erro

        cls._engine = engine
        return cls._engine

    @classmethod
    def resetar(cls) -> None:
        """Descarta o singleton e a engine. Existe para isolar testes."""
        cls._instance = None
        cls._engine = None

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------
    def carregar(self, nomes_tabelas: Sequence[str]) -> None:
        """
        Carrega em memória as tabelas ainda não cacheadas.

        Args:
            nomes_tabelas: Nomes das tabelas a carregar.

        Raises:
            RuntimeError: Se alguma tabela não puder ser lida.
        """
        pendentes = [nome for nome in nomes_tabelas if nome not in self.tabelas]

        if not pendentes:
            return

        logger.info(f"Carregando {len(pendentes)} tabela(s) em memória")

        for nome_tabela in pendentes:
            self.tabelas[nome_tabela] = self._carregar_tabela(nome_tabela)

        logger.info("Tabelas carregadas com sucesso")

    def _carregar_tabela(self, nome_tabela: str) -> pd.DataFrame:
        """Lê uma tabela inteira para memória."""
        logger.info(f"Carregando tabela [{nome_tabela}]")

        try:
            df = pd.read_sql(sql=f"SELECT * FROM {nome_tabela}", con=self.engine)
        except Exception as erro:
            from comum.config.diagnostico import explicar_erro_de_banco

            causa, correcao = explicar_erro_de_banco(erro)
            mensagem = (
                f"[BANCO] Não foi possível ler a tabela [{nome_tabela}]: {causa}.\n"
                f"  -> {correcao}"
            )
            logger.error(mensagem)
            raise RuntimeError(mensagem) from erro

        logger.info(
            f"Tabela [{nome_tabela}] carregada | "
            f"Linhas: {len(df)} | Colunas: {len(df.columns)}"
        )
        return df

    def obter_tabela(self, nome_tabela: str) -> pd.DataFrame:
        """
        Devolve uma tabela do cache, carregando-a se ainda não estiver lá.

        Args:
            nome_tabela: Nome da tabela.

        Returns:
            DataFrame com o conteúdo da tabela.
        """
        if nome_tabela not in self.tabelas:
            self.tabelas[nome_tabela] = self._carregar_tabela(nome_tabela)

        return self.tabelas[nome_tabela]

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------
    def inserir(self, nome_tabela: str, df: pd.DataFrame) -> None:
        """
        Acrescenta linhas a uma tabela, em blocos.

        O índice do pandas é descartado para que a PK auto-incremento do banco
        funcione.

        Args:
            nome_tabela: Tabela de destino.
            df: Linhas a inserir. Vazio ou ``None`` não faz nada.

        Raises:
            RuntimeError: Se a escrita falhar — interrompe a esteira do RPA.
        """
        if df is None or df.empty:
            logger.info(f"Nenhum registro para inserir em [{nome_tabela}].")
            return

        total = len(df)
        logger.info(f"Inserindo {total} registro(s) em [{nome_tabela}].")

        try:
            df.to_sql(
                name=nome_tabela,
                con=self.engine,
                if_exists="append",
                index=False,
                chunksize=_TAMANHO_BLOCO,
            )
        except Exception as erro:
            mensagem = (
                f"Falha ao inserir o lote em [{nome_tabela}]. Motivo: {erro}"
            )
            logger.error(mensagem)
            raise RuntimeError(mensagem) from erro

        logger.info(f"{total} registro(s) persistidos em [{nome_tabela}].")
        self._atualizar_cache_local(nome_tabela, df)

    def salvar_dados_tabela_despesa(self, df_consolidado: pd.DataFrame) -> None:
        """Insere o consolidado de validação no log de arquivos."""
        self.inserir(tabelas.LOG_DESPESA_ARQUIVOS, df_consolidado)

    def salvar_dados_tabela_contestacao(self, df_contestacao: pd.DataFrame) -> None:
        """Insere a análise de contestação no log de contestação."""
        self.inserir(tabelas.LOG_DESPESA_CONTESTACAO, df_contestacao)

    @staticmethod
    def _validar_tabela_escrita(nome_tabela: str) -> None:
        """
        Garante que a escrita só ocorra em tabelas conhecidas do domínio.

        Origem: Projeto 4, que validava contra a sua ``TABELAS_CACHE``. Como a
        lista de cache aqui é por RPA, a validação usa ``tabelas.TODAS``.

        Raises:
            KeyError: Caso ``nome_tabela`` não seja conhecida.
        """
        if nome_tabela not in tabelas.TODAS:
            raise KeyError(
                f"Tabela [{nome_tabela}] não é uma tabela de escrita conhecida "
                f"(esperado uma de {sorted(tabelas.TODAS)})"
            )

    def inserir_dados(self, nome_tabela: str, dados: pd.DataFrame) -> None:
        """
        Insere linhas e sincroniza o cache. Alias validado de :meth:`inserir`.

        Origem: Projeto 4. Mantido porque os services e testes daquele projeto
        o chamam por este nome.

        Args:
            nome_tabela: Tabela de destino, que precisa ser conhecida.
            dados: Linhas a inserir. Nada é feito se vazio.

        Raises:
            KeyError: Caso ``nome_tabela`` não seja conhecida.
        """
        self._validar_tabela_escrita(nome_tabela=nome_tabela)
        self.inserir(nome_tabela, dados)

    def atualizar_dados(
        self,
        nome_tabela: str,
        valores: dict,
        chave: dict,
        sincronizar_cache: bool = True,
    ) -> int:
        """
        Atualiza (``UPDATE``) as linhas que casam com ``chave``.

        Origem: Projeto 4. Contrapartida de :meth:`inserir_dados` para os fluxos
        em que a linha já existe: a HU-19 preenche a despesa apresentada pela
        operadora e a HU-16 regrava ``tipo_contestacao``. Em ambos, a linha-base
        é inserida pelo RPA 2.

        A SQL é parametrizada e roda em transação. O cache é recarregado do
        banco ao final, porque um ``UPDATE`` não é reproduzível por concatenação.

        Args:
            nome_tabela: Tabela de destino, que precisa ser conhecida.
            valores: Colunas a atualizar -> novo valor. Nada é feito se vazio.
            chave: Colunas do filtro -> valor esperado. Obrigatório — um
                ``UPDATE`` sem ``WHERE`` atingiria a tabela inteira.
            sincronizar_cache: Se ``False``, não relê a tabela; quem chama fica
                responsável por ressincronizar. Usado em lotes, para não pagar
                um ``SELECT *`` por linha.

        Returns:
            Número de linhas atualizadas (0 = chave inexistente).

        Raises:
            KeyError: Caso ``nome_tabela`` não seja conhecida.
            ValueError: Caso ``chave`` esteja vazia.
        """
        self._validar_tabela_escrita(nome_tabela=nome_tabela)

        if not chave:
            raise ValueError(
                f"UPDATE em [{nome_tabela}] exige uma chave — "
                f"atualização sem WHERE não é permitida"
            )

        if not valores:
            logger.info(f"Nada a atualizar em [{nome_tabela}] (vazio).")
            return 0

        # Prefixos distintos evitam colisão quando a mesma coluna aparece nos
        # dois lados.
        atribuicoes = ", ".join(f"{coluna} = :set_{coluna}" for coluna in valores)
        filtros = " AND ".join(f"{coluna} = :key_{coluna}" for coluna in chave)

        parametros = {f"set_{coluna}": valor for coluna, valor in valores.items()}
        parametros.update({f"key_{coluna}": valor for coluna, valor in chave.items()})

        sql = text(f"UPDATE {nome_tabela} SET {atribuicoes} WHERE {filtros}")

        with self.engine.begin() as conexao:
            resultado = conexao.execute(sql, parametros)
            linhas_afetadas = int(resultado.rowcount or 0)

        logger.info(f"{linhas_afetadas} linha(s) atualizada(s) em [{nome_tabela}].")

        if linhas_afetadas and sincronizar_cache:
            self.recarregar_cache_local(nome_tabela=nome_tabela)

        return linhas_afetadas

    def recarregar_cache_local(self, nome_tabela: str) -> None:
        """
        Relê a tabela do banco e substitui a versão em memória.

        Usado após ``UPDATE``, onde não há como sincronizar por concatenação.
        """
        self.tabelas[nome_tabela] = self._carregar_tabela(nome_tabela=nome_tabela)

    def _atualizar_cache_local(
        self, nome_tabela: str, df_novos_dados: pd.DataFrame
    ) -> None:
        """
        Sincroniza o cache em memória com o que acabou de ser inserido, para
        evitar um novo ``SELECT``. Só age se a tabela já estiver cacheada.
        """
        if df_novos_dados is None or df_novos_dados.empty:
            return

        if nome_tabela not in self.tabelas:
            return

        self.tabelas[nome_tabela] = pd.concat(
            [self.tabelas[nome_tabela], df_novos_dados], ignore_index=True
        )

        logger.info(
            f"Cache de [{nome_tabela}] sincronizado. "
            f"Total em memória: {len(self.tabelas[nome_tabela])} linhas."
        )
