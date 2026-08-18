"""Consultas às tabelas de referência do banco WebFat — base comum dos RPAs.

Fachada sobre :class:`RepositorioCache`, que é a única camada que fala com o
banco. Reúne as consultas ao Anexo 5, às tarifas reguladas, ao mapeamento de
descritores e à tabela de contestação.

Origem: união das quatro versões de ``repositorio_tabelas.py``. Os métodos
comuns a P2 e P3 foram verificados como **byte a byte idênticos**; cada método
abaixo traz a sua origem em comentário. Ver
``trabalho/inventarios/duplicacoes.md`` D-07, D-08, D-09, D-11 e D-15.

Alterações intencionais registradas na unificação:

1. **Carregamento preguiçoso.** Os projetos carregavam todas as suas tabelas no
   ``__init__``. Como cada RPA usa um subconjunto diferente, isso faria o RPA 1
   exigir a tabela de tarifas, que ele não usa. As tabelas agora são
   propriedades resolvidas no primeiro acesso.
2. **Nomes de tabela** vêm de ``comum.dados.tabelas``, não de literais.
3. ``obter_tipo_produto_por_poi`` (Projeto 3) **não foi migrado**. O método lia
   a coluna POI e tratava o valor como descritor — ver
   ``inventario-projeto-3.md`` achado B. Seu lugar é ocupado por
   ``obter_mapa_descritores`` (Projeto 4), que resolve pelo descritor e
   desambigua pela coluna ``produto``.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from comum.config.constantes import (
    COLUNAS_ATUALIZADAS_DESPESA_CONTESTACAO,
    COLUNAS_CHAVE_DESPESA_CONTESTACAO,
)
from comum.config.logger_config import logger
from comum.dados import tabelas
from comum.dados.repositorio_cache import RepositorioCache


class RepositorioTabelas:
    """Consultas sobre as tabelas de referência carregadas em cache.

    As tabelas são carregadas no primeiro acesso, não na construção — assim
    cada RPA só paga pelo que usa.
    """

    def __init__(self, cache: RepositorioCache | None = None) -> None:
        """
        Args:
            cache: Repositório de cache a usar. Se ``None``, usa o singleton.
        """
        self.cache = cache or RepositorioCache()
        self._regioes_validas: set | None = None
        self._mapa_regiao: dict | None = None

    # ------------------------------------------------------------------
    # Tabelas (carregadas no primeiro acesso)
    # ------------------------------------------------------------------
    @property
    def tbl_anexo5_processado(self) -> pd.DataFrame:
        return self.cache.obter_tabela(tabelas.ANEXO5)

    @property
    def tbl_detraf_tarifas(self) -> pd.DataFrame:
        return self.cache.obter_tabela(tabelas.TARIFAS)

    @property
    def tbl_detraf_mapeamento_descritores(self) -> pd.DataFrame:
        return self.cache.obter_tabela(tabelas.MAPEAMENTO_DESCRITORES)

    #: Alias mantido por compatibilidade com o nome usado no Projeto 4.
    @property
    def tbl_mapeamento_descritores(self) -> pd.DataFrame:
        return self.tbl_detraf_mapeamento_descritores

    @property
    def tbl_contestacao(self) -> pd.DataFrame:
        return self.cache.obter_tabela(tabelas.LOG_DESPESA_CONTESTACAO)

    @property
    def tbl_detraf_destinatarios(self) -> pd.DataFrame:
        return self.cache.obter_tabela(tabelas.DESTINATARIOS)

    # ------------------------------------------------------------------
    # Caches derivados (idem — resolvidos no primeiro acesso)
    # ------------------------------------------------------------------
    @property
    def regioes_validas_cache(self) -> set:
        if self._regioes_validas is None:
            self._regioes_validas = self.obter_regioes_validas_db()
        return self._regioes_validas

    @property
    def _mapa_regiao_cache(self) -> dict:
        """Mapa EOT -> Região, para evitar refazer o mesmo join a cada consulta."""
        if self._mapa_regiao is None:
            self._mapa_regiao = (
                self.tbl_anexo5_processado.assign(
                    EOT=lambda tabela: tabela[tabelas.COL_ANEXO5_EOT]
                    .astype(str)
                    .str.strip()
                )
                .set_index(tabelas.COL_ANEXO5_EOT)[tabelas.COL_ANEXO5_REGIAO]
                .to_dict()
            )
        return self._mapa_regiao

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------
    def salvar_dados_tabela_despesa(self, df_despesa: pd.DataFrame) -> None:
        """Persiste o consolidado de validação no log de arquivos."""
        self.cache.salvar_dados_tabela_despesa(df_despesa)

    def salvar_dados_tabela_contestacao(self, df_contestacao: pd.DataFrame) -> None:
        """Persiste a análise de contestação no log de contestação."""
        self.cache.salvar_dados_tabela_contestacao(df_contestacao)


    # --- origem: Projeto 2 (P2/P3/P4 identicos)
    @staticmethod
    def _tratar_eot(eot: str) -> str:
        """
        Trata o valor do EOT antes da pesquisa.

        Regras:
        - Remove espaços
        - Sempre retorna string
        - Remove qualquer parte decimal sem arredondar
        - Caso seja numérico e menor que 100,
        adiciona zeros à esquerda para
        manter 3 dígitos.
        """

        eot = str(eot).strip()

        # Remove parte decimal sem arredondar
        if "." in eot:
            eot = eot.split(".")[0]

        if eot.isdigit() and int(eot) < 100:
            return eot.zfill(3)

        return eot


    # --- origem: Projeto 2 (P2/P3 identicos)
    def validar_eot(self, eot: str) -> Optional[str]:
        """
        Procura o EOT na tabela
        tbl_anexo5_processado.

        Returns:
            Nome Fantasia caso encontre.

            None caso não encontre.
        """

        eot_tratado: str = self._tratar_eot(eot)

        resultado: pd.DataFrame = self.tbl_anexo5_processado[
            self.tbl_anexo5_processado[tabelas.COL_ANEXO5_EOT].astype(str).str.strip() == eot_tratado
        ]

        if resultado.empty:

            logger.info(f"EOT não encontrado [{eot_tratado}]")

            return None

        nome_fantasia: str = resultado.iloc[0][tabelas.COL_ANEXO5_NOME_FANTASIA]
        return nome_fantasia


    # --- origem: Projeto 1 (so no P1)
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

        coluna: pd.Series = self.tbl_anexo5_processado[tabelas.COL_ANEXO5_NOME_FANTASIA].astype(
            str
        ).str.strip()

        mascara = coluna.str.upper().str.contains(texto_tratado, na=False, regex=False)

        resultado: pd.DataFrame = self.tbl_anexo5_processado[mascara]

        if resultado.empty:

            logger.info(f"Nome Fantasia não encontrado para o texto [{texto}]")

            return None

        nome_fantasia: str = resultado.iloc[0][tabelas.COL_ANEXO5_NOME_FANTASIA]

        return nome_fantasia


    # --- origem: Projeto 1 (so no P1)
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
            self.tbl_anexo5_processado[tabelas.COL_ANEXO5_EOT].astype(str).str.strip() == str(eot).strip()
        ]

        if resultado.empty:

            logger.info(f"Nome Fantasia não encontrado para o EOT [{eot}]")

            return None

        return resultado.iloc[0][tabelas.COL_ANEXO5_NOME_FANTASIA]


    # --- origem: Projeto 4 (so no P4)
    def obter_endereco_por_eot(self, eot: str) -> Optional[str]:
        """
        Procura o endereço de correspondência da operadora na tabela ``tbl_anexo5_processado``.

        Coluna confirmada pelo usuário (2026-07-23) e depois **contra o banco
        real** (2026-08-06): chama-se ``Endereco de Correspondencia``, sem
        acento — ver ``tabelas.COL_ANEXO5_ENDERECO_CORRESP``. Até aquela data o
        código a procurava acentuada e levantava ``KeyError``.
        Usada no cabeçalho da carta de contestação (HU-14, T-082 — campo "A:").

        Args:
            eot: Código EOT da operadora.

        Returns:
            O endereço correspondente, ou ``None`` se o EOT não for encontrado.
        """

        eot_tratado: str = self._tratar_eot(eot)

        resultado: pd.DataFrame = self.tbl_anexo5_processado[
            self.tbl_anexo5_processado[tabelas.COL_ANEXO5_EOT].astype(str).str.strip() == eot_tratado
        ]

        if resultado.empty:
            logger.info(f"EOT não encontrado para busca de endereço [{eot_tratado}]")
            return None

        return resultado.iloc[0][tabelas.COL_ANEXO5_ENDERECO_CORRESP]


    # --- origem: Projeto 2 (P2/P3 identicos)
    def obter_tipo_servico_por_eot(self, eot: str) -> Optional[str]:
        """
        Procura o EOT na tabela tbl_anexo5_processado e retorna o Tipo de Serviço.

        Args:
            eot (str): Código EOT a ser pesquisado.

        Returns:
            Optional[str]: O valor da coluna ``Tipo de Servico`` (sem acento no
                           banco — ver ``tabelas.COL_ANEXO5_TIPO_SERVICO``) caso
                           encontre. None caso não encontre.
        """
        eot_tratado: str = self._tratar_eot(eot)

        resultado: pd.DataFrame = self.tbl_anexo5_processado[
            self.tbl_anexo5_processado[tabelas.COL_ANEXO5_EOT].astype(str).str.strip() == eot_tratado
        ]

        if resultado.empty:
            logger.info(
                f"EOT não encontrado para busca de Tipo de Serviço [{eot_tratado}]"
            )
            return None

        tipo_servico: str = resultado.iloc[0][tabelas.COL_ANEXO5_TIPO_SERVICO]

        return tipo_servico


    # --- origem: Projeto 2 (P2/P3 identicos)
    def obter_concessao_por_eot(self, eot: str) -> Optional[str]:
        """
        Procura o EOT na tabela tbl_anexo5_processado e retorna o valor da Concessão.

        Args:
            eot (str): Código EOT a ser pesquisado.

        Returns:
            Optional[str]: O valor da coluna ``Concessao`` (sem acento no banco —
                           ver ``tabelas.COL_ANEXO5_CONCESSAO``) caso encontre.
                           None caso não encontre.
        """
        eot_tratado: str = self._tratar_eot(eot)

        resultado: pd.DataFrame = self.tbl_anexo5_processado[
            self.tbl_anexo5_processado[tabelas.COL_ANEXO5_EOT].astype(str).str.strip() == eot_tratado
        ]

        if resultado.empty:
            logger.info(f"EOT não encontrado para busca de Concessão [{eot_tratado}]")
            return None

        concessao: str = resultado.iloc[0][tabelas.COL_ANEXO5_CONCESSAO]

        return concessao


    # --- origem: Projeto 2 (P2/P3 identicos)
    def obter_regioes_validas_db(self) -> set:
        """
        Varre o atributo de tarifas da classe e retorna um conjunto (set)
        com todas as regiões únicas, limpas e válidas cadastradas.
        """
        # Acessa diretamente o dataframe original do objeto
        df_tarifas = self.tbl_detraf_tarifas
        return {
            str(reg).strip()
            for reg in df_tarifas["regiao"].unique()
            if pd.notna(reg) and str(reg).strip() != ""
        }


    # --- origem: Projeto 2 (P2/P3 identicos)
    def validar_regiao(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Mapeia a região no DataFrame com base no EOT da coluna 1.

        A região é obtida da tabela `tbl_anexo5_processado`
        através do relacionamento entre:
        - coluna 1 do df
        - coluna "EOT" da tbl_anexo5_processado

        Returns:
            pd.DataFrame: DataFrame com a coluna REGIAO adicionada.
        """

        df = df.copy()

        # Coluna 1 = índice 0
        eots = df.iloc[:, 0].astype(str).str.strip().apply(self._tratar_eot)

        df["regiao"] = eots.map(self._mapa_regiao_cache)

        return df


    # --- origem: Projeto 2 (so no P2/P3)
    def validar_coluna_eot_df(self, df: pd.DataFrame, indice_coluna: int) -> bool:
        """
        Valida se TODOS os valores da coluna informada no DataFrame existem
        na coluna 'EOT' da tabela tbl_anexo5_processado

        Args:
            df (pd.DataFrame): O DataFrame que está sendo validado (ex: dados do DETRAF).
            indice_coluna (int): Índice posicional (zero-based) da coluna de EOT no DF.

        Returns:
            bool: True se todos os EOTs do DF existirem no cache, False caso contrário.
        """
        if df.shape[0] == 0:
            return True

        mascara = self.validar_coluna_eot_df_mascara(df, indice_coluna)
        valido = bool(mascara.all())

        if not valido:
            logger.info(
                f"DataFrame reprovado na validação de EOT (Índice Coluna: {indice_coluna}). "
                f"Encontrados códigos de operadoras que não existem no Anexo 5 cadastrado."
            )

        return valido


    # --- origem: Projeto 2 (so no P2)
    def validar_coluna_eot_df_mascara(
        self, df: pd.DataFrame, indice_coluna: int
    ) -> pd.Series:
        """
        Retorna uma Series[bool] alinhada a df.index: True se o EOT da linha
        existe na coluna 'EOT' da tabela tbl_anexo5_processado.
        """
        if df.shape[0] == 0:
            return pd.Series([], dtype=bool, index=df.index)

        eots_cache_tratados = (
            self.tbl_anexo5_processado[tabelas.COL_ANEXO5_EOT].astype(str).apply(self._tratar_eot)
        )
        eots_validos_set: set[str] = set(eots_cache_tratados.unique())

        coluna_alvo_tratada = df.iloc[:, indice_coluna].astype(str).apply(
            self._tratar_eot
        )

        return coluna_alvo_tratada.isin(eots_validos_set)


    # --- origem: Projeto 2 (so no P2/P3)
    def validar_eots_por_nomes_fantasia(
        self,
        df: pd.DataFrame,
        indice_coluna: int,
        nomes_fantasia: list[str],
        debug: bool = False,
    ) -> bool:
        """
        Valida se todos os EOTs de uma coluna específica do DataFrame pertencem aos
        EOTs localizados no banco de dados para os Nomes Fantasia fornecidos.

        Aplica o método _tratar_eot tanto na tabela de cache quanto no DataFrame do arquivo.

        Args:
            df (pd.DataFrame): O DataFrame que está sendo validado (ex: dados do DETRAF).
            indice_coluna (int): Índice posicional (zero-based) da coluna de EOT no DF.
            nomes_fantasia (list[str]): Lista de nomes fantasia (ex: ["VIVO", "TELEFONICA"]).
            debug (bool): Se True, loga detalhes dos EOTs que falharam na validação.

        Returns:
            bool: True se todos os EOTs da coluna do DF forem válidos, False caso contrário.
        """
        if df.shape[0] == 0:
            return False

        if not nomes_fantasia:
            logger.info(
                "Lista de nomes fantasia fornecida está vazia. Validação de EOT reprovada."
            )
            return False

        nomes_busca_set = {str(nome).strip().upper() for nome in nomes_fantasia}
        nomes_tabela_padronizados = (
            self.tbl_anexo5_processado[tabelas.COL_ANEXO5_NOME_FANTASIA]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        if not nomes_tabela_padronizados.isin(nomes_busca_set).any():
            logger.info(
                f"Nenhum EOT localizado no banco para os nomes fornecidos: {nomes_fantasia}"
            )
            return False

        mascara_validos = self.validar_eots_por_nomes_fantasia_mascara(
            df, indice_coluna, nomes_fantasia
        )
        valido = bool(mascara_validos.all())

        if not valido and debug:
            # Captura os EOTs brutos do arquivo que falharam na validação
            coluna_df_bruta = df.iloc[:, indice_coluna].astype(str)
            eots_invalidos = coluna_df_bruta[~mascara_validos]
            amostra_erros = eots_invalidos.unique()[:10].tolist()

            logger.info(
                f"DataFrame reprovado na validação de EOT (Coluna índice {indice_coluna}). "
                f"Encontrados EOTs que não pertencem às operadoras informadas {nomes_fantasia}. "
                f"Amostra de valores inválidos no arquivo: {amostra_erros}"
            )

        return valido


    # --- origem: Projeto 2 (so no P2)
    def validar_eots_por_nomes_fantasia_mascara(
        self,
        df: pd.DataFrame,
        indice_coluna: int,
        nomes_fantasia: list[str],
    ) -> pd.Series:
        """
        Retorna uma Series[bool] alinhada a df.index: True se o EOT da linha
        pertence a algum dos nomes fantasia informados. Casos degenerados
        (df vazio, nomes_fantasia vazio, ou nenhum EOT do banco para os nomes
        informados) retornam uma Series de False do tamanho do df.
        """
        if df.shape[0] == 0 or not nomes_fantasia:
            return pd.Series(False, index=df.index, dtype=bool)

        nomes_busca_set = {str(nome).strip().upper() for nome in nomes_fantasia}
        nomes_tabela_padronizados = (
            self.tbl_anexo5_processado[tabelas.COL_ANEXO5_NOME_FANTASIA]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        mascara_banco = nomes_tabela_padronizados.isin(nomes_busca_set)
        sub_tabela_banco = self.tbl_anexo5_processado[mascara_banco]

        if sub_tabela_banco.empty:
            return pd.Series(False, index=df.index, dtype=bool)

        eots_validos_banco = set(
            sub_tabela_banco[tabelas.COL_ANEXO5_EOT]
            .astype(str)
            .apply(self._tratar_eot)
            .unique()
        )

        coluna_df_tratada = df.iloc[:, indice_coluna].astype(str).apply(
            self._tratar_eot
        )

        return coluna_df_tratada.isin(eots_validos_banco)


    # --- origem: Projeto 2 (P2/P3 identicos)
    def validar_tarifas_na_tabela(
        self, df: pd.DataFrame, debug: bool = False
    ) -> pd.DataFrame:
        """
        Busca o valor da tarifa aplicando todos os filtros simultaneamente
        (GH, Região, Regra e Datas).

        ## 🔴 A exceção por EOT existe no banco e este filtro a ignora

        O achado A1 (2026-08-05) registrava aqui que `eot_vivo` e `eot_operadora`
        **não existiam no DDL real** — a conclusão vinha de um print do MySQL
        Workbench que não as mostrava. **Estava errado.** A leitura do banco real
        (2026-08-06) achou as duas, e `eot_vivo` está preenchida em **64 das 127
        linhas**. A exceção que a V2 cita — **RII (943) × SERCOMTEL** — está lá.

        O filtro abaixo usa GH, região, regra e datas, e **não** as duas colunas.
        A consequência não é `KeyError`, é pior de enxergar: para a mesma
        região/GH/regra/vigência o banco tem uma linha genérica (`eot_vivo` nulo)
        **e** linhas por EOT com tarifas diferentes — grupos de até 13 linhas com
        6 tarifas distintas. Este método devolve **todas** como candidatas, e
        `validacao_colunas` aprova a linha do Detraf se ela bater com qualquer
        uma. A validação afrouxa em silêncio: uma tarifa de outro par de EOTs
        passa.

        **Manter a regra atual foi decisão de 2026-08-06.** Definir a precedência
        (o específico por EOT vence o genérico?) é regra de negócio, e errá-la
        aperta ou afrouxa validação de faturamento real. A pergunta está no
        encaminhamento ao DBA.
        """

        if df.shape[0] == 0:
            df_retorno = df.copy()
            df_retorno["tarifa_tabela"] = pd.Series(dtype=object)
            df_retorno["filtro_df"] = pd.Series(dtype=object)
            df_retorno["id_tabela"] = pd.Series(dtype=object)

            # NOVA COLUNA PARA O VALOR VINDO DA TABELA
            df_retorno["regra_desc_tabela"] = pd.Series(dtype=object)

            return df_retorno

        # Preserva dataframe original
        df_resultado = df.copy()

        # Banco
        tarifas_db = self.tbl_detraf_tarifas.copy()

        tarifas_db["data_inicio"] = pd.to_datetime(
            tarifas_db["data_inicio"],
            errors="coerce",
        )

        tarifas_db["data_fim"] = pd.to_datetime(
            tarifas_db["data_fim"],
            errors="coerce",
        )

        # Pré-processamentos reaproveitados no loop para reduzir custo por linha.
        gh_tratado = tarifas_db["gh"].astype(str).str.strip()
        tarifas_db["gh_aceita_qualquer"] = (
            tarifas_db["gh"].isna()  # NaN real — checado antes do astype
            | (gh_tratado == "nan")  # NaN convertido para string pelo astype
            | (gh_tratado.str.upper() == "NULL")  # string literal "NULL" vinda do banco
            | (gh_tratado == "")  # string vazia
        )

        cache_busca_tarifa: dict = {}

        # Processa linha
        def buscar_dados_tarifa_linha(linha):

            gh_atual = str(linha.iloc[7]).strip()
            regiao_atual = linha["regiao"]

            # Validação da região: Somente considera a região no filtro se for uma das regiões disponíveis no cache.
            regiao_limpa = str(regiao_atual).strip() if pd.notna(regiao_atual) else ""
            regiao_eh_valida = regiao_limpa in self.regioes_validas_cache

            regra_desc_atual = linha["regra_desc"]
            remuneracao = linha["remuneracao"]

            dicionario_filtro = {
                "gh": gh_atual,
                "regiao": regiao_atual,
                "regra_desc": regra_desc_atual,
                "mes_trafego_formatado": str(linha["mes_trafego_formatado"]),
                "remuneracao": remuneracao,
            }

            data_atual = linha["mes_trafego_formatado"]

            if pd.isna(data_atual):
                return [], dicionario_filtro, None, None

            chave_cache = (
                gh_atual,
                regiao_atual,
                regiao_eh_valida,
                regra_desc_atual,
                remuneracao,
                data_atual,
            )

            if chave_cache in cache_busca_tarifa:
                (
                    tarifas_encontradas,
                    ids_encontrados,
                    regras_encontradas,
                ) = cache_busca_tarifa[chave_cache]
                return (
                    tarifas_encontradas,
                    dicionario_filtro,
                    ids_encontrados,
                    regras_encontradas,
                )

            # FILTRO COMPLETO COM REGRA_DESC
            # Caso a data seja fevereiro, também considera 28/02 do mesmo ano
            data_fevereiro_28 = None

            if data_atual.month == 2:
                data_fevereiro_28 = pd.Timestamp(
                    year=data_atual.year,
                    month=2,
                    day=28,
                )

            filtro_data = (tarifas_db["data_inicio"] <= data_atual) & (
                data_atual <= tarifas_db["data_fim"]
            )

            # Adiciona regra extra para fevereiro
            if data_fevereiro_28 is not None:
                filtro_data = filtro_data | (
                    (tarifas_db["data_inicio"] <= data_fevereiro_28)
                    & (data_fevereiro_28 <= tarifas_db["data_fim"])
                )

            filtro = (
                (
                    # GH nulo/vazio significa que a tarifa aceita qualquer GH
                    (tarifas_db["gh"] == gh_atual)
                    | (tarifas_db["gh_aceita_qualquer"])
                )
                # Condicional do filtro de região
                & ((tarifas_db["regiao"] == regiao_atual) if regiao_eh_valida else True)
                & (tarifas_db["regra_desc"] == regra_desc_atual)
                & (tarifas_db["tipo_remuneracao"] == remuneracao)
                & filtro_data
            )

            registros_localizados = tarifas_db.loc[filtro]

            if registros_localizados.empty:
                cache_busca_tarifa[chave_cache] = ([], None, None)
                return [], dicionario_filtro, None, None

            tarifas_encontradas = registros_localizados["tarifa"].astype(float).tolist()

            ids_encontrados = ", ".join(
                registros_localizados["id"].astype(str).tolist()
            )

            regras_encontradas = ", ".join(
                registros_localizados["regra_desc"].astype(str).tolist()
            )

            cache_busca_tarifa[chave_cache] = (
                tarifas_encontradas,
                ids_encontrados,
                regras_encontradas,
            )

            return (
                tarifas_encontradas,
                dicionario_filtro,
                ids_encontrados,
                regras_encontradas,
            )

        resultados = df_resultado.apply(
            buscar_dados_tarifa_linha,
            axis=1,
        )

        (
            df_resultado["tarifa_tabela"],
            df_resultado["filtro_df"],
            df_resultado["id_tabela"],
            df_resultado["regra_desc_tabela"],
        ) = zip(*resultados)

        if debug:

            linhas_sem_tarifa = int(
                df_resultado["tarifa_tabela"].apply(lambda x: len(x) == 0).sum()
            )

            if linhas_sem_tarifa > 0:
                logger.info(
                    f"Validação de tarifas encontrou "
                    f"{linhas_sem_tarifa} linha(s) sem tarifa. "
                    f"Consulte as colunas "
                    f"'filtro_df', 'id_tabela' e "
                    f"'regra_desc_tabela'."
                )

        return df_resultado


    # --- origem: Projeto 4 (so no P4)
    def obter_mapa_descritores(self) -> pd.DataFrame:
        """
        Retorna a relação descritor → remuneração (D-21).

        Fonte: ``tbl_detraf_mapeamento_descritores`` do banco Webfat (V2 pág. 7). Antes
        de 2026-07-30 esta relação vinha de uma planilha/CSV
        (``Mapeamento_Descritores.xlsx``); o CSV em ``tests/fixtures`` passou a ser
        apenas o seed do SQLite de teste.

        Returns:
            DataFrame com as colunas ``id``, ``final_descritor``, ``remuneracao_fixa``,
            ``observacao`` e ``produto`` — insumo de
            :func:`src.services.mapa_remuneracao.construir_indice_remuneracao`.
        """

        return self.tbl_mapeamento_descritores


    # --- origem: Projeto 4 (so no P4)
    #: Colunas da chave comparadas com `_tratar_eot` dos dois lados — o Detraf e o
    #: banco divergem em zero-padding e parte decimal.
    _COLUNAS_EOT_DA_CHAVE: frozenset[str] = frozenset({"eot_operadora", "eot_tbra"})

    # --- origem: Projeto 4 (so no P4)
    def _filtrar_contestacao_por_chave(self, chave: dict) -> pd.DataFrame:
        """
        Seleciona em ``tbl_contestacao`` as linhas da chave de negócio (AI/10 §1.3).

        Args:
            chave: ``{coluna_do_banco: valor}``, tipicamente montado a partir de
                :data:`COLUNAS_CHAVE_DESPESA_CONTESTACAO`.

        Recebe um **dicionário** e não cinco parâmetros nomeados desde 2026-08-06.
        Antes, quem chamava fazia ``self._filtrar_contestacao_por_chave(**chave)``,
        e esse splat fazia a lista de **colunas do banco** valer também como lista
        de **parâmetros Python** — os dois nomes tinham que ser iguais. Quando se
        descobriu que a coluna do banco é ``remuneracoes`` (plural) e não
        ``remuneracao``, esse acoplamento obrigaria a renomear junto o parâmetro
        público de :meth:`obter_tipo_contestacao`, que é nome de domínio e está
        certo no singular. Com o dicionário, **um lado fala banco e o outro fala
        domínio**, e a tradução acontece num lugar só.

        Ponto único de verdade da chave: usado tanto pela leitura do sinal
        (:meth:`obter_tipo_contestacao`) quanto pelas escritas (D-19/D-20).
        """

        tabela = self.tbl_contestacao
        filtro = pd.Series(True, index=tabela.index)

        for coluna, valor in chave.items():
            lado_banco = tabela[coluna].astype(str)
            if coluna in self._COLUNAS_EOT_DA_CHAVE:
                filtro &= lado_banco.apply(self._tratar_eot) == self._tratar_eot(valor)
            else:
                filtro &= lado_banco.str.strip() == str(valor).strip()

        return tabela[filtro]


    # --- origem: Projeto 4 (so no P4)
    def obter_tipo_contestacao(
        self,
        eot_operadora: str,
        eot_tbra: str,
        referencia: str,
        trafego: str,
        remuneracao: str,
    ) -> Optional[str]:
        """
        Consulta o sinal COM/SEM retenção (decisão do analista, T-024/D-6).

        Fonte: ``tbl_rpa_log_detraf_despesa_contestacao``, schema confirmado contra
        o banco real em 2026-08-06 (``banco_de_dados/schema-real-*.sql``). O sinal
        é a coluna ``tipo_contestacao`` (``"com retenção"`` / ``"sem retenção"``),
        gravada pelo Webfat após ação do analista (HU-11).

        ⚠️ A coluna da remuneração chama-se ``remuneracoes`` (**plural**) no banco.
        O parâmetro abaixo é ``remuneracao``, singular, porque é nome de domínio —
        a tradução está na chamada a :meth:`_filtrar_contestacao_por_chave`. Até
        2026-08-06 dizia-se aqui que a coluna tinha sido acrescentada por decisão
        de 2026-07-28 e que o DDL precisava ser pedido ao DBA; ela sempre existiu,
        no plural, e o pedido foi retirado.

        ## Por que a chave inclui a remuneração

        ⚠️ **A justificativa mudou em 2026-08-05, e vale registrar por quê.**

        A original era *"o sinal pode variar por remuneração dentro do mesmo par
        de EOT"*. Um print da aba ``Contest`` real, embutido no `.docx`
        (achado A2), **contradiz isso**: a aba tem uma linha por par de EOT e uma
        única marca ``S``/``N`` — a decisão de contestar **não** se abre por
        remuneração.

        A coluna continua necessária, por outro motivo, que a V2 afirma em dois
        pontos distintos:

            "popular o Encontro de Contas com o valores total apresentado pela
             operadora, **aberto por tipo de remuneração e EOT Vivo**"

            "O que vai para o EC é o somatório do valor bruto **por remuneração e
             operadora**"

        Ou seja: **a granularidade muda ao longo do fluxo**. A decisão é por par
        de EOT; o registro no Encontro de Contas é por remuneração. Como esta
        tabela é o destino do registro, ela precisa da coluna — e o sinal lido
        aqui é o mesmo para todas as remunerações do par.

        A consequência prática é a mesma de antes (a chave inclui a remuneração),
        mas quem for confirmar o DDL com o DBA precisa apresentar **este**
        argumento, não o anterior.

        Args:
            eot_operadora: EOT credora (coluna ``eot_operadora``).
            eot_tbra: EOT devedora / Vivo (coluna ``eot_tbra``).
            referencia: Mês de referência do Detraf (``AAAAMM``).
            trafego: Mês de tráfego contestado (``AAAAMM``).
            remuneracao: Remuneração resolvida pelo descritor (D-5) — parte da chave.

        Returns:
            O texto de ``tipo_contestacao`` (ex.: ``"com retenção"``), ou ``None`` se
            não houver sinalização para a combinação (ainda **sem contestação**).
        """

        # Aqui é a fronteira: os parâmetros são nomes de DOMÍNIO (`remuneracao`,
        # singular) e as chaves do dicionário são nomes de COLUNA DO BANCO
        # (`remuneracoes`, plural). A tradução acontece nesta linha e em mais
        # nenhuma.
        resultado = self._filtrar_contestacao_por_chave(
            {
                "eot_operadora": eot_operadora,
                "eot_tbra": eot_tbra,
                "referencia": referencia,
                "trafego": trafego,
                tabelas.COL_CONTESTACAO_REMUNERACOES: remuneracao,
            }
        )

        if resultado.empty:
            eot_operadora_tratado = self._tratar_eot(eot_operadora)
            eot_tbra_tratado = self._tratar_eot(eot_tbra)
            logger.info(
                f"Sinal de contestação não encontrado para "
                f"[operadora={eot_operadora_tratado}, tbra={eot_tbra_tratado}, "
                f"referencia={referencia}, trafego={trafego}, remuneracao={remuneracao}] "
                f"— tratado como sem contestação."
            )
            return None

        return resultado.iloc[0]["tipo_contestacao"]


    # --- origem: Projeto 4 (so no P4)
    def _atualizar_contestacao_em_lote(
        self, linhas: pd.DataFrame, colunas_atualizadas: list[str], rotulo: str
    ) -> dict:
        """
        Aplica um lote de ``UPDATE`` em ``tbl_rpa_log_detraf_despesa_contestacao``.

        A linha alvo é localizada pela chave de negócio em memória
        (:meth:`_filtrar_contestacao_por_chave`, que normaliza os EOTs) e o ``UPDATE``
        vai por ``id``, garantindo que a semântica de casamento seja **idêntica** à da
        leitura do sinal e que a SQL use a chave primária.

        Chave ausente **não aborta o lote** (D-20): vira WARNING e entra no resumo — a
        linha-base é inserida pelo Épico 3, fora deste projeto (bloqueio B-D20).

        ## Coluna ausente também não aborta o lote

        ``atualizar_dados`` monta **um único** ``UPDATE ... SET a=:a, b=:b ...``.
        Uma coluna que não existe na tabela derruba a instrução inteira — e com
        ela os campos que existem, para **todas** as operadoras do lote. Era o que
        aconteceria com ``vb_contestacao``, que a HU-19 grava e o banco real não
        tem (2026-08-06, pendência Q24).

        Por isso as colunas são filtradas contra as que a tabela realmente tem
        antes do laço, com **um** aviso por lote — não por linha, que soterraria o
        sinal. A lista de colunas reais sai do próprio cache, que veio de um
        ``SELECT *``: sem ida ao ``information_schema`` e sem ramificar por
        dialeto. No dia do ``ALTER TABLE``, a coluna volta a ser gravada sem
        tocar em código.

        Args:
            linhas: Chave (``COLUNAS_CHAVE_DESPESA_CONTESTACAO``) + colunas a atualizar.
            colunas_atualizadas: Subconjunto de colunas de ``linhas`` a gravar.
            rotulo: Prefixo de log identificando a HU chamadora.

        Returns:
            ``{"atualizadas": int, "ausentes": list[dict], "colunas_ignoradas": list[str]}``
            — ``ausentes`` lista as chaves que não casaram com nenhuma linha do
            banco; ``colunas_ignoradas``, as colunas que a tabela não tem.
        """

        tabela = "tbl_rpa_log_detraf_despesa_contestacao"
        atualizadas: int = 0
        ausentes: list[dict] = []

        if linhas is None or linhas.empty:
            logger.info(f"{rotulo} Nada a atualizar (lote vazio).")
            return {"atualizadas": 0, "ausentes": [], "colunas_ignoradas": []}

        colunas_reais = set(self.tbl_contestacao.columns)
        ignoradas = [c for c in colunas_atualizadas if c not in colunas_reais]
        gravaveis = [c for c in colunas_atualizadas if c in colunas_reais]

        if ignoradas:
            logger.warning(
                f"{rotulo} A tabela '{tabela}' não tem a(s) coluna(s) "
                f"{', '.join(ignoradas)} — NÃO gravada(s). As demais seguem "
                f"normalmente. Um ALTER TABLE resolve; ver "
                f"pendencias-para-o-cliente.md (Q24)."
            )

        if not gravaveis:
            logger.error(
                f"{rotulo} Nenhuma das colunas a gravar existe em '{tabela}' "
                f"({', '.join(colunas_atualizadas)}) — lote abortado."
            )
            return {"atualizadas": 0, "ausentes": [], "colunas_ignoradas": ignoradas}

        for linha in linhas.to_dict(orient="records"):

            chave = {
                coluna: linha[coluna] for coluna in COLUNAS_CHAVE_DESPESA_CONTESTACAO
            }

            alvos = self._filtrar_contestacao_por_chave(chave)

            if alvos.empty:
                logger.warning(
                    f"{rotulo} Chave sem linha correspondente no banco {chave} — "
                    f"ignorada (a linha-base é inserida pelo Épico 3, B-D20)."
                )
                ausentes.append(chave)
                continue

            valores = {coluna: linha[coluna] for coluna in gravaveis}

            for id_linha in alvos["id"].tolist():
                atualizadas += self.cache.atualizar_dados(
                    nome_tabela=tabela,
                    valores=valores,
                    chave={"id": id_linha},
                    sincronizar_cache=False,
                )

        # Uma única releitura ao final do lote (em vez de um SELECT * por linha).
        self.cache.recarregar_cache_local(nome_tabela=tabela)
        # O Projeto 4 reatribuía `self.tbl_contestacao` aqui, porque a tabela era
        # um atributo fixado no __init__. Nesta versão ela é uma propriedade que
        # lê do cache a cada acesso, então a releitura acima já basta.

        logger.info(
            f"{rotulo} {atualizadas} linha(s) atualizada(s), "
            f"{len(ausentes)} chave(s) ausente(s)."
        )
        return {
            "atualizadas": atualizadas,
            "ausentes": ausentes,
            "colunas_ignoradas": ignoradas,
        }


    # --- origem: Projeto 4 (so no P4)
    def atualizar_despesa_contestacao(self, linhas: pd.DataFrame) -> dict:
        """
        Atualiza a despesa da contestação (HU-19) em
        ``tbl_rpa_log_detraf_despesa_contestacao``.

        **D-20 (2026-07-30, adequação à V2 pág. 38):** a escrita da HU-19 é um
        ``UPDATE`` dos seis campos de despesa da operadora, não mais um ``INSERT`` da
        linha inteira (D-16). A linha-base é inserida pelo Épico 3 (V2 pág. 19), fora
        do escopo deste projeto.

        Args:
            linhas: Saída de
                :func:`src.services.encontro_contas.preparar_atualizacoes_despesa_contestacao`.

        Returns:
            Resumo do lote: ``{"atualizadas": int, "ausentes": list[dict]}``.
        """

        return self._atualizar_contestacao_em_lote(
            linhas=linhas,
            colunas_atualizadas=COLUNAS_ATUALIZADAS_DESPESA_CONTESTACAO,
            rotulo="[HU-19 Despesa Contestação]",
        )


    # --- origem: Projeto 4 (so no P4)
    def atualizar_tipo_contestacao(self, linhas: pd.DataFrame) -> dict:
        """
        Regrava ``tipo_contestacao`` após a geração do CONT_PROC (HU-16).

        **D-19 (2026-07-30, adequação à V2 pág. 34):** *"O robô atualiza o campo
        'tipo_contestacao' da tabela do banco webfat – 'tbl_rpa_log_detraf_despesa_
        contestacao'"*. Semântica definida com o usuário: **eco do sinal aplicado** — o
        robô regrava, nas linhas efetivamente contestadas, o mesmo valor que usou para
        montar o CONT_PROC, confirmando no Webfat o que foi para o AGI.

        Args:
            linhas: Saída de
                :func:`src.services.geracao_cont_proc.selecionar_linhas_contestadas`
                — chave + coluna ``tipo_contestacao``.

        Returns:
            Resumo do lote: ``{"atualizadas": int, "ausentes": list[dict]}``.
        """

        return self._atualizar_contestacao_em_lote(
            linhas=linhas,
            colunas_atualizadas=["tipo_contestacao"],
            rotulo="[HU-16 Writeback tipo_contestacao]",
        )

    def obter_subtotal_despesa_por_operadora(self, referencia: str) -> dict[str, float]:
        """
        Subtotal de despesa por operadora, do Encontro de Contas (HU-20).

        É o equivalente em banco do *"Subtotal despesa (célula O87)"* que a V2
        (¶701) manda comparar com o relatório do AGI. Soma ``vb_operadora`` de
        ``tbl_rpa_log_detraf_despesa_contestacao``, agrupado por ``empresa``.

        **Por que não a planilha.** O Projeto 6 lia um `.xlsx` por `openpyxl`,
        achava a aba por substring do nome da operadora e pegava a célula fixa
        ``O87`` — três fragilidades numa linha (`"OI"` casaria com qualquer aba
        que contenha "oi"). A V2 diz que *"todas as planilhas deste processo foram
        substituídas por banco"*, e o cliente confirmou em 2026-08-05 que o EC é
        banco. A célula ``O87`` não sobrevive a isso.

        Args:
            referencia: Mês de referência (``AAAAMM``).

        Returns:
            ``{nome_da_empresa_em_maiúsculas: subtotal}``. Vazio quando não há
            linha no mês — o que a HU-20 trata como divergência, não como zero.
        """

        tabela = self.tbl_contestacao
        do_mes = tabela[
            tabela["referencia"].astype(str).str.strip() == str(referencia).strip()
        ]

        if do_mes.empty:
            logger.warning(
                f"[HU-20] Nenhuma linha em '{tabelas.LOG_DESPESA_CONTESTACAO}' para "
                f"{referencia} — não há Encontro de Contas com que comparar."
            )
            return {}

        somas = (
            do_mes.assign(
                _empresa=do_mes["empresa"].astype(str).str.strip().str.upper(),
                _vb=pd.to_numeric(do_mes["vb_operadora"], errors="coerce").fillna(0.0),
            )
            .groupby("_empresa")["_vb"]
            .sum()
        )

        return {empresa: float(valor) for empresa, valor in somas.items()}

    def atualizar_carga_agi(
        self, operadora: str, referencia: str, status: str
    ) -> int:
        """
        Grava o resultado da carga no AGI (HU-18) em ``carga_agi``.

        A V2 é explícita, na seção *Carga no AGI*: *"O robô atualiza o campo
        'carga_agi' com o o status da carga na tabela
        'tbl_rpa_log_detraf_despesa_contestacao' do banco webfat."* Até 2026-08-04
        não existia método para isso — o RPA 2 gravava ``"não carregado"`` na
        criação da linha e ninguém tocava no campo depois, então o WebFat nunca
        soube que a carga aconteceu.

        **Granularidade: operadora × referência, não a chave de negócio.** As
        demais escritas desta tabela usam a chave completa (par de EOT + tráfego +
        remuneração), mas quem chama esta aqui é o uploader, e ele só conhece o
        arquivo — que é justamente `CONT_PROC_MASCARA_{operadora}_{aaaamm}`, um por
        operadora e mês, contendo todas as linhas contestadas dela. Subir o arquivo
        carrega todas essas linhas de uma vez; marcar uma a uma seria inventar uma
        precisão que o ato não tem.

        Args:
            operadora: Nome fantasia, casado com a coluna ``empresa``.
            referencia: Mês de referência (``AAAAMM``).
            status: Texto do status, como ``"carregado"``.

        Returns:
            Quantidade de linhas atualizadas. Zero significa que a linha-base ainda
            não existe — ela é inserida pelo Épico 3 (RPA 2), bloqueio B-D20.
        """

        tabela = self.tbl_contestacao
        filtro = (
            tabela["empresa"].astype(str).str.strip().str.upper()
            == str(operadora).strip().upper()
        ) & (tabela["referencia"].astype(str).str.strip() == str(referencia).strip())

        alvos = tabela[filtro]

        if alvos.empty:
            logger.warning(
                f"[HU-18 carga_agi] Nenhuma linha de {operadora}/{referencia} em "
                f"'{tabelas.LOG_DESPESA_CONTESTACAO}' — status '{status}' não registrado. "
                f"A linha-base é inserida pelo RPA 2 (B-D20)."
            )
            return 0

        atualizadas = 0
        for id_linha in alvos["id"].tolist():
            atualizadas += self.cache.atualizar_dados(
                nome_tabela=tabelas.LOG_DESPESA_CONTESTACAO,
                valores={"carga_agi": status},
                chave={"id": id_linha},
                sincronizar_cache=False,
            )

        self.cache.recarregar_cache_local(nome_tabela=tabelas.LOG_DESPESA_CONTESTACAO)

        logger.info(
            f"[HU-18 carga_agi] {operadora}/{referencia}: {atualizadas} linha(s) "
            f"marcada(s) como '{status}'."
        )
        return atualizadas

    def obter_trafego_recuperado(self, referencia: str) -> list[dict]:
        """
        As linhas a retificar no AGI (HU-21) — variação negativa, ainda não feitas.

        `referencia` é o mês da contestação **original**: a recuperação é
        percebida no mês seguinte, então quem chama passa o mês anterior ao de
        processamento.

        🔴 **`carga_agi` tem dois donos, e este é o segundo.** Aqui ele significa
        "já retifiquei"; em `atualizar_carga_agi` significa "o CONT_PROC subiu"
        (HU-18, RPA 3). Duas consequências, ambas reais:
        toda linha que o RPA 3 já carregou fica **invisível** para a HU-21, e uma
        linha retificada passa a parecer carregada. É como a origem faz, e foi a
        decisão de manter; a alternativa é uma coluna própria
        (`retificacao_agi`), que precisa de `ALTER TABLE`. Está registrado em
        `docs/04-relatorios/duvidas-pendentes.md` como pergunta ao PO.

        ⚠️ **O critério de "recuperado" não foi validado com o negócio:** só
        `vb_variacao_perc < 0`. Pode ser que devesse considerar
        `minutos_variacao_perc`, ou as duas — a origem registra a dúvida e diz
        que havia uma única linha de teste na tabela quando aquilo foi escrito.

        Returns:
            Um dicionário por linha, com o que o fluxo de retificação precisa.
            Lista vazia quando não há o que fazer — que é o caso comum.
        """

        tabela = self.tbl_contestacao
        if tabela.empty:
            logger.info(
                f"[HU-21] '{tabelas.LOG_DESPESA_CONTESTACAO}' está vazia — "
                f"nada a retificar em {referencia}."
            )
            return []

        variacao = pd.to_numeric(tabela["vb_variacao_perc"], errors="coerce")

        alvos = tabela[
            (tabela["referencia"].astype(str).str.strip() == str(referencia).strip())
            & (
                tabela["carga_agi"].astype(str).str.strip()
                != tabelas.CARGA_AGI_CARREGADO
            )
            & (variacao < 0)
        ]

        if alvos.empty:
            logger.info(f"[HU-21] Nenhum tráfego recuperado em {referencia}.")
            return []

        recuperacoes = [
            {
                "id": linha["id"],
                "operadora": linha["empresa"],
                "eot_operadora": linha["eot_operadora"],
                "periodo": linha["referencia"],
                "periodo_trafego": linha["trafego"],
                # Absolutos: a diferença é negativa por definição (foi o que
                # caracterizou a recuperação), e o AGI recebe quanto foi
                # recuperado, não o sinal.
                "minutos": abs(float(linha["minutos_diferenca"] or 0)),
                "valor_bruto": abs(float(linha["vb_diferenca"] or 0)),
            }
            for _, linha in alvos.iterrows()
        ]

        logger.info(
            f"[HU-21] {len(recuperacoes)} linha(s) com tráfego recuperado em "
            f"{referencia}."
        )
        return recuperacoes

    def marcar_retificacao_no_agi(self, id_contestacao: int) -> int:
        """
        Fecha o ciclo de uma retificação, para não repeti-la.

        Grava `carga_agi = 'carregado'` na linha — ver o aviso dos dois donos em
        `obter_trafego_recuperado`.

        ⚠️ **Marcar não é confirmar.** O AGI não devolve sinal de que o evento foi
        persistido; isto roda logo depois do clique em Salvar. Se o AGI recusou, a
        linha fica marcada como feita e ninguém volta nela.
        """
        atualizadas = self.cache.atualizar_dados(
            nome_tabela=tabelas.LOG_DESPESA_CONTESTACAO,
            valores={"carga_agi": tabelas.CARGA_AGI_CARREGADO},
            chave={"id": id_contestacao},
        )

        if not atualizadas:
            logger.warning(
                f"[HU-21] Nenhuma linha de id {id_contestacao} foi marcada — "
                f"ela será reprocessada na próxima execução, e o evento no AGI "
                f"seria lançado de novo."
            )
        return atualizadas


    # --- Q16 (HU-15): resolvida em 2026-08-18, tbl_detraf_destinatarios
    def obter_contatos_operadora(
        self, operadora: str, produto: str = "Detraf"
    ) -> dict[str, list[str]]:
        """
        Contatos de e-mail da operadora para a HU-15, filtrados por ``produto``.

        Fonte: ``tbl_detraf_destinatarios`` (banco WebFat) — substitui o CSV que
        servia de ponte para a pendência Q16 até o cliente confirmar a tabela em
        2026-08-18. Uma linha vale para uma ou mais operadoras: a coluna
        ``operadora`` lista os nomes fantasia separados por vírgula (ex.:
        ``"ADVANCE_TELECOM, ADVANCE_TELECOMUNICACOES_LTDA"``), e cada linha traz
        **um** e-mail e um ``tipo_destinatario`` (``"PARA"`` ou ``"CC"``).

        A tabela serve outros produtos do WebFat além do Detraf — daí o filtro.

        Args:
            operadora: Nome fantasia a buscar — comparado sem diferenciar
                maiúsculas/espaços contra cada alias da coluna ``operadora``.
            produto: Filtro da coluna ``produto``.

        Returns:
            ``{"para": [...], "copia": [...]}`` — listas vazias se a operadora
            não tiver contato cadastrado para o produto informado.
        """
        tabela = self.tbl_detraf_destinatarios
        do_produto = tabela[
            tabela["produto"].astype(str).str.strip().str.casefold()
            == produto.strip().casefold()
        ]

        chave = operadora.strip().casefold()
        para: list[str] = []
        copia: list[str] = []

        for _, linha in do_produto.iterrows():
            operadora_bruta = linha["operadora"]
            if pd.isna(operadora_bruta):
                continue

            aliases = {
                alias.strip().casefold() for alias in str(operadora_bruta).split(",")
            }
            if chave not in aliases:
                continue

            email = linha["email"]
            if pd.isna(email) or not str(email).strip():
                continue
            email = str(email).strip()

            eh_para = str(linha["tipo_destinatario"]).strip().casefold() == "para"
            destino = para if eh_para else copia
            if email not in destino:
                destino.append(email)

        return {"para": para, "copia": copia}


# ---------------------------------------------------------------------------
# Instância de módulo, por compatibilidade
#
# P1, P2 e P3 expunham `bd_tabelas = RepositorioTabelas()` e o importavam
# diretamente nos services. O Projeto 4 evitava isso de propósito, porque o
# construtor original ia ao banco no import e quebrava quando ele estava fora.
#
# Com o carregamento preguiçoso desta versão, construir não toca o banco
# (SQLAlchemy só conecta no primeiro uso), então a instância de módulo voltou a
# ser segura — e mantém os imports dos três projetos funcionando sem alteração.
# ---------------------------------------------------------------------------
bd_tabelas = RepositorioTabelas()
