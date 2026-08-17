import pandas as pd
from pathlib import Path
from src.config.logger_config import logger
from src.utils.gerenciador_arquivos import carregar_dados, exportar_dataframe_para_excel
from src.config.configuration import (
    ANO_MES_REFERENCIA,
    DIRETORIO_BASE_CONTESTACAO,
    CABECARIO_PLANILHA,
)
from src.models.repository.repositorio_tabelas import bd_tabelas


class CriacaoArquivoContestacao:

    @staticmethod
    def _gerar_nome_planilha(
        pasta_base: Path,
        operadora: str,
    ) -> dict[str, Path | str]:
        """
        Gera o caminho e o nome da planilha de contestação.

        Args:
            pasta_base: Caminho base onde as planilhas serão armazenadas.
            operadora: Nome da operadora.

        Returns:
            Dicionário contendo:
                - caminho_planilha: Path no formato <pasta_base>/YYYY/YYYYMM
                - nome_planilha: Nome da planilha no formato
                "Base_Contestação_<OPERADORA>_<YYYYMM>"
        """

        ano = ANO_MES_REFERENCIA[:4]

        return {
            "caminho_planilha": pasta_base / ano / ANO_MES_REFERENCIA,
            "nome_planilha": (
                f"Base_Contestação_{operadora.upper()}_{ANO_MES_REFERENCIA}"
            ),
        }

    def _exportar_planilha_operadora(
        self,
        df: pd.DataFrame,
        operadora: str,
        nome_aba: str,
    ) -> None:
        """
        Exporta um DataFrame para a planilha da operadora.
        """

        info_planilha = self._gerar_nome_planilha(
            pasta_base=DIRETORIO_BASE_CONTESTACAO,
            operadora=operadora,
        )

        exportar_dataframe_para_excel(
            df=df,
            pasta_destino=info_planilha["caminho_planilha"],  # type: ignore
            nome_arquivo=info_planilha["nome_planilha"],  # type: ignore
            cabecalho=CABECARIO_PLANILHA,
            nome_aba=nome_aba,
        )

    def _carregar_dataframe_filtrado(
        self,
        arquivo: Path,
        operadora: str,
        debug: bool = False,
    ) -> pd.DataFrame | None:
        """
        Carrega um arquivo e remove linhas de totais.
        """

        df = carregar_dados(arquivo)

        if df is None or df.empty:
            return None

        df_filtrado = df[
            df.iloc[:, 5].isin(["00", "0", 0])
        ].copy()

        if debug:
            logger.info(
                "[DEBUG] Operadora=%s | Arquivo=%s | Linhas originais=%s | Linhas após filtro=%s",
                operadora,
                arquivo.name,
                len(df),
                len(df_filtrado),
            )

        return df_filtrado

    def _consolidar_arquivos(
        self,
        arquivos: list[Path],
        operadora: str,
        debug: bool = False,
    ) -> pd.DataFrame:
        """
        Carrega, filtra e consolida arquivos de uma operadora.
        """

        dfs_validos: list[pd.DataFrame] = []

        for arquivo in arquivos:
            df = self._carregar_dataframe_filtrado(
                arquivo=arquivo,
                operadora=operadora,
                debug=debug,
            )

            if df is not None and not df.empty:
                dfs_validos.append(df)

        df_consolidado = (
            pd.concat(dfs_validos, ignore_index=True)
            if dfs_validos
            else pd.DataFrame()
        )

        if debug:
            logger.info(
                "[DEBUG] Operadora=%s | Arquivos válidos=%s | Linhas consolidadas=%s",
                operadora,
                len(dfs_validos),
                len(df_consolidado),
            )

        return df_consolidado

    def _obter_operadoras(
        self,
        arquivos_detraf: dict[str, list[Path]],
        arquivos_expectativa: dict[str, list[Path]],
    ) -> set[str]:
        """
        Retorna a união das operadoras encontradas nos dois dicionários.
        """

        chave_ignorada = "OPERADORA_NAO_IDENTIFICADA"

        detraf_normalizado = {
            chave.upper(): arquivos
            for chave, arquivos in arquivos_detraf.items()
        }

        expectativa_normalizado = {
            chave.upper(): arquivos
            for chave, arquivos in arquivos_expectativa.items()
        }

        arquivos_detraf.clear()
        arquivos_detraf.update(detraf_normalizado)

        arquivos_expectativa.clear()
        arquivos_expectativa.update(expectativa_normalizado)

        chaves_detraf = {
            chave
            for chave in detraf_normalizado
            if chave != chave_ignorada
        }

        chaves_expectativa = {
            chave
            for chave in expectativa_normalizado
            if chave != chave_ignorada
        }

        return chaves_detraf | chaves_expectativa

    @staticmethod
    def _converter_coluna_numerica(serie: pd.Series) -> pd.Series:
        """
        Converte uma Series string com formato brasileiro (vírgula decimal)
        para float. Retorna 0 onde a conversão falhar.
        """
        return pd.to_numeric(
            serie.astype(str).str.replace(",", ".", regex=False),
            errors="coerce",
        ).fillna(0)

    def _gerar_aba_resumo(
        self,
        df: pd.DataFrame,
        operadora: str,
        nome_aba: str,
    ) -> None:
        """
        Agrupa os dados por Trafego + Referencia, soma Minutos e R$_Bruto,
        e exporta o resultado como aba de resumo na planilha da operadora.

        Índices de coluna usados:
            3 → Trafego | 2 → Referencia | 9 → Minutos | 14 → R$_Bruto
        """
        if df.empty:
            logger.warning(
                "DataFrame vazio — aba '%s' da operadora '%s' não será gerada.",
                nome_aba,
                operadora,
            )
            return

        df_trabalho = df.iloc[:, [3, 2, 9, 14]].copy()
        df_trabalho.columns = pd.Index(["Trafego", "Referencia", "Minutos", "R$_Bruto"])

        df_trabalho["Minutos"] = self._converter_coluna_numerica(df_trabalho["Minutos"])
        df_trabalho["R$_Bruto"] = self._converter_coluna_numerica(df_trabalho["R$_Bruto"])

        df_resumo = (
            df_trabalho
            .groupby(["Trafego", "Referencia"], dropna=False)[["Minutos", "R$_Bruto"]]
            .sum()
            .reset_index()
        )

        info_planilha = self._gerar_nome_planilha(
            pasta_base=DIRETORIO_BASE_CONTESTACAO,
            operadora=operadora,
        )

        exportar_dataframe_para_excel(
            df=df_resumo,
            pasta_destino=info_planilha["caminho_planilha"],  # type: ignore
            nome_arquivo=info_planilha["nome_planilha"],  # type: ignore
            cabecalho=None,
            nome_aba=nome_aba,
        )

        logger.info(
            "Aba '%s' exportada para operadora '%s' | Linhas: %s",
            nome_aba,
            operadora,
            len(df_resumo),
        )

    def _enriquecer_com_tipo(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adiciona as colunas tipo_operacao e tipo_produto ao DataFrame.

        tipo_operacao: derivado da Credora (col 0) via tbl_anexo5_processado.
        tipo_produto:  derivado do POI (col 4) via tbl_detraf_mapeamento_descritores.

        Usa dicionários pré-computados com .map() para evitar chamadas
        por linha ao banco de dados.
        """
        if df.empty:
            return df.copy()

        df = df.copy()

        credoras_unicas = df.iloc[:, 0].astype(str).str.strip().unique()
        mapa_tipo_op = {
            eot: bd_tabelas.obter_tipo_servico_por_eot(eot)
            for eot in credoras_unicas
        }
        df["tipo_operacao"] = df.iloc[:, 0].astype(str).str.strip().map(mapa_tipo_op)

        pois_unicos = df.iloc[:, 4].astype(str).str.strip().unique()
        mapa_tipo_prod = {
            poi: bd_tabelas.obter_tipo_produto_por_poi(poi)
            for poi in pois_unicos
        }
        df["tipo_produto"] = df.iloc[:, 4].astype(str).str.strip().map(mapa_tipo_prod)

        return df

    def _aplicar_analise_contestacao(self, df_contest: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica a camada analítica H10 sobre o df_contest montado na H9.

        Adiciona:
        - flag_contestacao: "S" se variacao_pct >= 1 %, "N" caso contrário.
        - modalidade_tarifa: somente para linhas VU-M em GH Reduzido (R).
          Depende do tipo de serviço da EOT Devedora (operadora), não da Credora.
          STFC → "NR" (não reduzido); SMP → "R" (reduzido).
        """
        df = df_contest.copy()

        df["flag_contestacao"] = df["variacao_pct"].apply(
            lambda v: "S" if pd.notna(v) and v >= 1.0 else "N"
        )

        mapa_tipo_serv = {
            eot: bd_tabelas.obter_tipo_servico_por_eot(eot)
            for eot in df["Devedora"].unique()
        }
        tipo_serv_devedora = df["Devedora"].map(mapa_tipo_serv)

        mascara_vum_r = (
            (df["tipo_produto"] == "VU-M") &
            (df["GH"].str.upper() == "R")
        )
        df["modalidade_tarifa"] = None
        df.loc[mascara_vum_r & (tipo_serv_devedora == "STFC"), "modalidade_tarifa"] = "NR"
        df.loc[mascara_vum_r & (tipo_serv_devedora == "SMP"),  "modalidade_tarifa"] = "R"

        return df

    @staticmethod
    def _preparar_dados_persistencia_contestacao(
        df_contest: pd.DataFrame, operadora: str
    ) -> pd.DataFrame:
        """
        Monta o DataFrame no formato de colunas da tabela
        'tbl_rpa_log_detraf_despesa_contestacao' — schema confirmado em
        'DOCS/Outros arquivos auxiliares/Tabelas para o RPA alimentar o
        Webfat - despesa.xlsx' (aba 'Contestação'). Colunas 'id' (AI PK) e
        'created_at' (default do banco) não são preenchidas aqui.

        ATENÇÃO — mapeamento sujeito a confirmação de negócio (ver
        PENDENCIAS.md P2/P3): o schema descreve 'eot_tbra' como "campo
        devedora dos arquivos" e 'eot_operadora' como "campo credora dos
        arquivos". Pela convenção já adotada neste serviço (Credora = EOT
        Vivo, Devedora = EOT da operadora — ver `_enriquecer_com_tipo` e
        `_aplicar_analise_contestacao`), o mapeamento literal fica:
        eot_tbra -> Devedora (operadora) e eot_operadora -> Credora (Vivo).
        Validar se essa é de fato a intenção antes de considerar definitivo.
        'carga_agi' e 'tipo_contestacao' ficam com valores iniciais, pois
        são preenchidos/atualizados posteriormente pelo WebFat (P2).
        """
        if df_contest.empty:
            return pd.DataFrame()

        minutos_diferenca = df_contest["Minutos_op"] - df_contest["Minutos_tbra"]
        minutos_variacao_perc = (
            minutos_diferenca / df_contest["Minutos_tbra"].replace(0, pd.NA) * 100
        )

        return pd.DataFrame({
            "tipo_servico_vivo": df_contest["tipo_operacao"],
            "eot_tbra": df_contest["Devedora"],
            "eot_operadora": df_contest["Credora"],
            "empresa": operadora,
            "referencia": df_contest["Referencia"],
            "trafego": df_contest["Trafego"],
            "minutos_tbra": df_contest["Minutos_tbra"],
            "vb_tbra": df_contest["RS_tbra"],
            "minutos_operadora": df_contest["Minutos_op"],
            "vb_operadora": df_contest["RS_op"],
            "minutos_diferenca": minutos_diferenca,
            "vb_diferenca": df_contest["variacao_rs"],
            "minutos_variacao_perc": minutos_variacao_perc,
            "vb_variacao_perc": df_contest["variacao_pct"],
            "carga_agi": "não carregado",
            "tipo_contestacao": None,
        })

    def _gerar_aba_contest(
        self,
        df_detraf: pd.DataFrame,
        df_expectativa: pd.DataFrame,
        operadora: str,
    ) -> None:
        """
        Constrói a aba Contest comparando os dados da operadora (detraf)
        com a expectativa Vivo (TBRA).

        Dimensões do agrupamento: Devedora, tipo_operacao, tipo_produto, Trafego, GH
        Métricas: Minutos e R$_Bruto (somados por dimensão)
        Colunas de saída adicionais: variacao_rs (absoluta) e variacao_pct (percentual)

        Índices de coluna usados:
            1 → Devedora | 3 → Trafego | 7 → GH | 9 → Minutos | 14 → R$_Bruto
        """
        DIMS = ["Devedora", "tipo_operacao", "tipo_produto", "Trafego", "GH"]

        def _preparar_agregado(df_enr: pd.DataFrame, sufixo: str) -> pd.DataFrame:
            if df_enr.empty:
                return pd.DataFrame(
                    columns=DIMS
                    + ["Credora", "Referencia", f"Minutos_{sufixo}", f"RS_{sufixo}"]
                )

            df_work = df_enr.copy()
            df_work["Credora"] = df_work.iloc[:, 0].astype(str).str.strip()
            df_work["Devedora"] = df_work.iloc[:, 1].astype(str).str.strip()
            df_work["Referencia"] = df_work.iloc[:, 2].astype(str).str.strip()
            df_work["Trafego"] = df_work.iloc[:, 3].astype(str).str.strip()
            df_work["GH"] = df_work.iloc[:, 7].astype(str).str.strip()
            df_work["Minutos"] = self._converter_coluna_numerica(df_work.iloc[:, 9])
            df_work["R$_Bruto"] = self._converter_coluna_numerica(df_work.iloc[:, 14])

            return (
                df_work
                .groupby(DIMS, dropna=False)
                .agg(
                    Credora=("Credora", "first"),
                    Referencia=("Referencia", "first"),
                    **{
                        f"Minutos_{sufixo}": ("Minutos", "sum"),
                        f"RS_{sufixo}": ("R$_Bruto", "sum"),
                    },
                )
                .reset_index()
            )

        df_det_enr = self._enriquecer_com_tipo(df_detraf)
        df_exp_enr = self._enriquecer_com_tipo(df_expectativa)

        df_agg_det = _preparar_agregado(df_det_enr, "op")
        df_agg_exp = _preparar_agregado(df_exp_enr, "tbra")

        if df_agg_det.empty and df_agg_exp.empty:
            logger.warning(
                "Nenhum dado para gerar aba Contest da operadora '%s'.", operadora
            )
            return

        df_contest = df_agg_det.merge(
            df_agg_exp, on=DIMS, how="outer", suffixes=("_op", "_tbra")
        )

        # Credora e Referencia não fazem parte das dimensões de agrupamento
        # (assumidas constantes por lado), mas são necessárias para a
        # persistência em tbl_rpa_log_detraf_despesa_contestacao.
        df_contest["Credora"] = df_contest["Credora_op"].fillna(
            df_contest["Credora_tbra"]
        )
        df_contest["Referencia"] = df_contest["Referencia_op"].fillna(
            df_contest["Referencia_tbra"]
        )
        df_contest = df_contest.drop(
            columns=["Credora_op", "Credora_tbra", "Referencia_op", "Referencia_tbra"]
        )

        colunas_numericas = ["Minutos_op", "RS_op", "Minutos_tbra", "RS_tbra"]
        df_contest[colunas_numericas] = df_contest[colunas_numericas].fillna(0)

        df_contest["variacao_rs"] = df_contest["RS_op"] - df_contest["RS_tbra"]
        df_contest["variacao_pct"] = (
            df_contest["variacao_rs"]
            / df_contest["RS_tbra"].replace(0, pd.NA)
            * 100
        )

        # H10 — flag de contestação e modalidade de tarifa VU-M
        df_contest = self._aplicar_analise_contestacao(df_contest)

        info_planilha = self._gerar_nome_planilha(
            pasta_base=DIRETORIO_BASE_CONTESTACAO,
            operadora=operadora,
        )

        # A aba "Contest" mantém o layout já validado (sem Credora/Referencia,
        # usadas apenas internamente para a persistência abaixo).
        df_contest_excel = df_contest.drop(columns=["Credora", "Referencia"])

        exportar_dataframe_para_excel(
            df=df_contest_excel,
            pasta_destino=info_planilha["caminho_planilha"],  # type: ignore
            nome_arquivo=info_planilha["nome_planilha"],  # type: ignore
            cabecalho=None,
            nome_aba="Contest",
        )

        logger.info(
            "Aba 'Contest' exportada para operadora '%s' | Linhas: %s",
            operadora,
            len(df_contest_excel),
        )

        # H9 Passo 7 — persiste o resultado da análise de contestação
        df_persistencia = self._preparar_dados_persistencia_contestacao(
            df_contest, operadora
        )
        bd_tabelas.salvar_dados_tabela_contestacao(df_persistencia)

    def _organizar_arquivos_por_operadora(
        self,
        arquivos_detraf: dict[str, list[Path]],
        arquivos_expectativa: dict[str, list[Path]],
        debug: bool = False,
    ) -> None:
        """
        Consolida arquivos DETRAF e EXPECTATIVA por operadora e exporta
        os resultados para planilhas Excel.
        """

        operadoras = self._obter_operadoras(
            arquivos_detraf,
            arquivos_expectativa,
        )

        for operadora in operadoras:
            df_detraf = self._consolidar_arquivos(
                arquivos=arquivos_detraf.get(operadora, []),
                operadora=operadora,
                debug=debug,
            )

            if not df_detraf.empty:
                self._exportar_planilha_operadora(
                    df=df_detraf,
                    operadora=operadora,
                    nome_aba=operadora,
                )
                self._gerar_aba_resumo(df_detraf, operadora, f"RESUMO {operadora}")

            df_expectativa = self._consolidar_arquivos(
                arquivos=arquivos_expectativa.get(operadora, []),
                operadora=operadora,
                debug=debug,
            )

            if not df_expectativa.empty:
                self._exportar_planilha_operadora(
                    df=df_expectativa,
                    operadora=operadora,
                    nome_aba="TBRA",
                )
                self._gerar_aba_resumo(df_expectativa, operadora, "RESUMO TBRA")

            self._gerar_aba_contest(df_detraf, df_expectativa, operadora)

    def criar_arquivo_contestacao(
        self,
        arquivos_detraf: dict[str, list[Path]],
        arquivos_expectativa: dict[str, list[Path]],
        caminho_base_contestacao: Path,
    ) -> None:
        logger.info("Iniciando o processo de criação dos arquivos de contestação.")
        self._organizar_arquivos_por_operadora(
            arquivos_detraf, arquivos_expectativa, debug=True
        )
