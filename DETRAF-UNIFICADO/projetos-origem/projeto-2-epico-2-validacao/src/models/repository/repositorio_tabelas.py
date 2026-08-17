from __future__ import annotations

from typing import Optional

import pandas as pd
from loguru import logger

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
        self.tbl_detraf_tarifas: pd.DataFrame = self.cache.obter_tabela(
            "tbl_detraf_tarifas"
        )
        self.regioes_validas_cache: set = self.obter_regioes_validas_db()
        # Mapa fixo usado em toda a execução para evitar recomputar o mesmo join em memória.
        self._mapa_regiao_cache = (
            self.tbl_anexo5_processado.assign(
                EOT=lambda tabela: tabela["EOT"].astype(str).str.strip()
            )
            .set_index("EOT")["Região"]
            .to_dict()
        )

    def salvar_dados_tabela_despesa(self, df_despesa: pd.DataFrame) -> None:
        """
        Salva os dados de despesa validados na tabela de despesas do banco.

        Args:
            df_despesa (pd.DataFrame): DataFrame contendo os dados de despesa a serem salvos.
        """

        self.cache.salvar_dados_tabela_despesa(df_despesa)

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
            self.tbl_anexo5_processado["EOT"].astype(str).str.strip() == eot_tratado
        ]

        if resultado.empty:

            logger.info(f"EOT não encontrado [{eot_tratado}]")

            return None

        nome_fantasia: str = resultado.iloc[0]["Nome Fantasia"]
        return nome_fantasia

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
            self.tbl_anexo5_processado["EOT"].astype(str).apply(self._tratar_eot)
        )
        eots_validos_set: set[str] = set(eots_cache_tratados.unique())

        coluna_alvo_tratada = df.iloc[:, indice_coluna].astype(str).apply(
            self._tratar_eot
        )

        return coluna_alvo_tratada.isin(eots_validos_set)

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
            self.tbl_anexo5_processado["Nome Fantasia"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        mascara_banco = nomes_tabela_padronizados.isin(nomes_busca_set)
        sub_tabela_banco = self.tbl_anexo5_processado[mascara_banco]

        if sub_tabela_banco.empty:
            return pd.Series(False, index=df.index, dtype=bool)

        eots_validos_banco = set(
            sub_tabela_banco["EOT"].astype(str).apply(self._tratar_eot).unique()
        )

        coluna_df_tratada = df.iloc[:, indice_coluna].astype(str).apply(
            self._tratar_eot
        )

        return coluna_df_tratada.isin(eots_validos_banco)

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
            self.tbl_anexo5_processado["Nome Fantasia"]
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

    def validar_tarifas_na_tabela(
        self, df: pd.DataFrame, debug: bool = False
    ) -> pd.DataFrame:
        """
        Busca o valor da tarifa aplicando todos os filtros simultaneamente
        (GH, Região, Regra e Datas).
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

    def obter_tipo_servico_por_eot(self, eot: str) -> Optional[str]:
        """
        Procura o EOT na tabela tbl_anexo5_processado e retorna o Tipo de Serviço.

        Args:
            eot (str): Código EOT a ser pesquisado.

        Returns:
            Optional[str]: O valor da coluna 'Tipo de Serviço' caso encontre.
                           None caso não encontre.
        """
        eot_tratado: str = self._tratar_eot(eot)

        resultado: pd.DataFrame = self.tbl_anexo5_processado[
            self.tbl_anexo5_processado["EOT"].astype(str).str.strip() == eot_tratado
        ]

        if resultado.empty:
            logger.info(
                f"EOT não encontrado para busca de Tipo de Serviço [{eot_tratado}]"
            )
            return None

        tipo_servico: str = resultado.iloc[0]["Tipo de Serviço"]

        return tipo_servico

    def obter_concessao_por_eot(self, eot: str) -> Optional[str]:
        """
        Procura o EOT na tabela tbl_anexo5_processado e retorna o valor da Concessão.

        Args:
            eot (str): Código EOT a ser pesquisado.

        Returns:
            Optional[str]: O valor da coluna 'Concessão' caso encontre.
                           None caso não encontre.
        """
        eot_tratado: str = self._tratar_eot(eot)

        resultado: pd.DataFrame = self.tbl_anexo5_processado[
            self.tbl_anexo5_processado["EOT"].astype(str).str.strip() == eot_tratado
        ]

        if resultado.empty:
            logger.info(f"EOT não encontrado para busca de Concessão [{eot_tratado}]")
            return None

        concessao: str = resultado.iloc[0]["Concessão"]

        return concessao


bd_tabelas = RepositorioTabelas()
