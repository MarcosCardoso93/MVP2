from typing import Set
import pandas as pd

# Importações oficiais do seu projeto
from src.config.configuration import ANO_MES_REFERENCIA
from src.config.logger_config import logger
from src.models.repository.repositorio_tabelas import bd_tabelas
from src.utils.classificadores import (
    classificar_descritor_remuneracao,
    classificar_regra_inicio_fim_desc,
)
from src.utils.utils import salvar_debug_log


class ValidadorColunas:
    """
    Classe especialista em validação de integridade e regras de negócio para DataFrames DETRAF.
    Os métodos internos realizam a conversão automática de One-Based para Zero-Based.
    """

    def __init__(self) -> None:
        """
        Inicializa a classe sem estado.
        """
        self.ref_mes_menos_1: str = ""
        self.valores_validos_trafego: Set[str] = set()
        self.valores_validos_gh: Set[str] = {"S", "R", "N", "D"}

    def _preparar_datas_referencia(self) -> None:
        """
        Calcula e prepara os períodos retroativos com base na constante global.
        """
        try:
            periodo_referencia = pd.Period(ANO_MES_REFERENCIA, freq="M")
        except Exception as erro:
            raise ValueError(
                f"A constante ANO_MES_REFERENCIA ('{ANO_MES_REFERENCIA}') "
                f"não está no formato válido 'AAAAMM'. Erro: {erro}"
            )

        self.ref_mes_menos_1 = (periodo_referencia - 1).strftime("%Y%m")
        ref_mes_menos_2: str = (periodo_referencia - 2).strftime("%Y%m")

        self.valores_validos_trafego = {
            ANO_MES_REFERENCIA,
            self.ref_mes_menos_1,
            ref_mes_menos_2,
        }

    def validar_tudo(
        self, df: pd.DataFrame, tipo_arquivo: str, debug: bool = False
    ) -> bool:
        """
        Executa todas as validações de regras de negócio no DataFrame fornecido.
        Garante que todas as regras sejam testadas, exibindo no log todas as falhas ocorridas.
        """

        self._preparar_datas_referencia()
        df_trabalho = df.copy()

        # Execução das validações mantendo o mapeamento One-Based original no fluxo
        v_col1_2 = self._validar_col_1_2_eot(df_trabalho)
        v_col2_vivo = self._validar_col_2_eot_vivo(
            df_trabalho,
            nomes_fantasia_vivo=[
                "Vivo",
                "Telefônica",
            ],  # Adicionar aqui caso haja outros
        )
        v_col3 = self._validar_col_3_referencia(df_trabalho)
        v_col4 = self._validar_col_4_trafego(df_trabalho)
        v_col8 = self._validar_col_8_gh(df_trabalho)
        v_col9 = self._validar_col_9_chamadas(df_trabalho)
        v_col10 = self._validar_col_10_minutos(df_trabalho)
        v_col11 = self._validar_col_11_tarifa(df_trabalho)
        v_col12_15 = self._validar_cols_financeiras_12_15(df_trabalho)

        v_tarifas_remuneradas = self._validar_tarifas_remuneradas(
            df_trabalho, debug_em_arquivo=False
        )

        validacoes = {
            "v_col1_2": v_col1_2,
            "v_col2_vivo": v_col2_vivo,
            "v_col3": v_col3,
            "v_col4": v_col4,
            "v_col8": v_col8,
            "v_col9": v_col9,
            "v_col10": v_col10,
            "v_col11": v_col11,
            "v_col12_15": v_col12_15,
            "v_tarifas_remuneradas": v_tarifas_remuneradas,
        }
        logger.info(
            f"Resultado das validações para o arquivo do tipo '{tipo_arquivo}': {validacoes}"
        )

        return all(validacoes.values())

    def validar_tudo_mascara(
        self, df: pd.DataFrame, tipo_arquivo: str, debug: bool = False
    ) -> pd.Series:
        """
        Igual a validar_tudo, mas em vez de reprovar o DataFrame inteiro,
        retorna uma Series[bool] alinhada a df.index: True = linha passou em
        TODAS as regras de negócio, False = linha falhou em pelo menos uma.
        """
        self._preparar_datas_referencia()
        df_trabalho = df.copy()

        mascaras = {
            "col1_2": self._mascara_col_1_2_eot(df_trabalho),
            "col2_vivo": self._mascara_col_2_eot_vivo(
                df_trabalho,
                nomes_fantasia_vivo=["Vivo", "Telefônica"],
            ),
            "col3": self._mascara_col_3_referencia(df_trabalho),
            "col4": self._mascara_col_4_trafego(df_trabalho),
            "col8": self._mascara_col_8_gh(df_trabalho),
            "col9": self._mascara_col_9_chamadas(df_trabalho),
            "col10": self._mascara_col_10_minutos(df_trabalho),
            "col11": self._mascara_col_11_tarifa(df_trabalho),
            "col12_15": self._mascara_cols_financeiras_12_15(df_trabalho),
            "tarifas_remuneradas": self._mascara_tarifas_remuneradas(df_trabalho),
        }

        mascara_final = pd.concat(mascaras, axis=1).all(axis=1)
        mascara_final.index = df.index

        if debug:
            logger.debug(
                f"Resumo por critério (linhas OK) para '{tipo_arquivo}': "
                f"{ {chave: int(mascara.sum()) for chave, mascara in mascaras.items()} }"
            )

        return mascara_final

    def _mascara_col_3_referencia(self, df: pd.DataFrame) -> pd.Series:
        """Regra: Col 3 (Referência) -> Mês corrente -1 no formato AAAAMM."""
        # Col 3 = Índice 2 no iloc (3 - 1)
        coluna = df.iloc[:, 2].astype(str).str.strip()
        return coluna == ANO_MES_REFERENCIA

    def _validar_col_3_referencia(self, df: pd.DataFrame) -> bool:
        valido = bool(self._mascara_col_3_referencia(df).all())

        if not valido:
            logger.info(
                f"DataFrame reprovado na validação da Coluna 3 (Referência). Esperado apenas: {self.ref_mes_menos_1}"
            )
        return valido

    def _mascara_col_4_trafego(self, df: pd.DataFrame) -> pd.Series:
        """Regra: Col 4 (Tráfego) -> Mês -1, -2 ou -3 no formato AAAAMM."""
        # Col 4 = Índice 3 no iloc (4 - 1)
        coluna = df.iloc[:, 3].astype(str).str.strip()
        return coluna.isin(self.valores_validos_trafego)

    def _validar_col_4_trafego(self, df: pd.DataFrame) -> bool:
        valido = bool(self._mascara_col_4_trafego(df).all())

        if not valido:
            logger.info(
                f"DataFrame reprovado na validação da Coluna 4 (Tráfego). Valores permitidos: {self.valores_validos_trafego}"
            )
        return valido

    def _mascara_col_8_gh(self, df: pd.DataFrame) -> pd.Series:
        """Regra: Col 8 (GH) -> Deve estar preenchida com as opções (S, R, N, D)."""
        # Col 8 = Índice 7 no iloc (8 - 1)
        coluna = df.iloc[:, 7].astype(str).str.strip()
        return coluna.isin(self.valores_validos_gh)

    def _validar_col_8_gh(self, df: pd.DataFrame) -> bool:
        valido = bool(self._mascara_col_8_gh(df).all())

        if not valido:
            logger.info(
                f"DataFrame reprovado na validação da Coluna 8 (GH). Valores fora das opções {self.valores_validos_gh} detectados."
            )
        return valido

    def _mascara_col_9_chamadas(self, df: pd.DataFrame) -> pd.Series:
        """Regra: Col 9 (Chamadas) -> Somente inteiros."""
        # Col 9 = Índice 8 no iloc (9 - 1)
        coluna_numerica = pd.to_numeric(df.iloc[:, 8], errors="coerce")
        mascara_numerico = coluna_numerica.notna()
        mascara_inteiro = (coluna_numerica % 1 == 0).fillna(False)
        return mascara_numerico & mascara_inteiro

    def _validar_col_9_chamadas(self, df: pd.DataFrame) -> bool:
        coluna_numerica = pd.to_numeric(df.iloc[:, 8], errors="coerce")

        if bool(coluna_numerica.isna().any()):
            logger.info(
                "DataFrame reprovado na validação da Coluna 9 (Chamadas). Encontrados valores não numéricos ou vazios."
            )
            return False

        valido = bool((coluna_numerica % 1 == 0).all())

        if not valido:
            logger.info(
                "DataFrame reprovado na validação da Coluna 9 (Chamadas). Encontrados números decimais onde deveriam ser apenas inteiros."
            )
        return valido

    def _mascara_col_10_minutos(self, df: pd.DataFrame) -> pd.Series:
        """Regra: Col 10 (Minutos) -> Até 1 casa decimal."""
        # Col 10 = Índice 9 no iloc (10 - 1)
        coluna_tratada = df.iloc[:, 9].astype(str).str.replace(",", ".", regex=False)
        coluna_numerica = pd.to_numeric(coluna_tratada, errors="coerce")
        mascara_numerico = coluna_numerica.notna()
        mascara_uma_casa = ((coluna_numerica * 10) % 1 == 0).fillna(False)
        return mascara_numerico & mascara_uma_casa

    def _validar_col_10_minutos(self, df: pd.DataFrame) -> bool:
        coluna_tratada = df.iloc[:, 9].astype(str).str.replace(",", ".", regex=False)
        coluna_numerica = pd.to_numeric(coluna_tratada, errors="coerce")

        if bool(coluna_numerica.isna().any()):
            logger.info(
                "DataFrame reprovado na validação da Coluna 10 (Minutos). Valores nulos ou não numéricos detectados."
            )
            return False

        valido = bool(((coluna_numerica * 10) % 1 == 0).all())

        if not valido:
            logger.info(
                "DataFrame reprovado na validação da Coluna 10 (Minutos). Encontrados valores com mais de 1 casa decimal."
            )
        return valido

    def _mascara_col_11_tarifa(self, df: pd.DataFrame) -> pd.Series:
        """Regra: Col 11 (Tarifa) -> Até 5 casas decimais, sem conter valor zero."""
        # Col 11 Tarifa = Índice 10 no iloc (11 - 1)
        coluna_crua = df.iloc[:, 10]
        coluna_tratada = coluna_crua.astype(str).str.replace(",", ".", regex=False)
        coluna_numerica = pd.to_numeric(coluna_tratada, errors="coerce")

        mascara_numerico = coluna_numerica.notna()
        mascara_nao_zero = (coluna_numerica != 0).fillna(False)

        valor_multiplicado = coluna_numerica * 100000
        valor_estabilizado = valor_multiplicado.round(9)
        mascara_decimais = (valor_estabilizado % 1 == 0).fillna(False)

        return mascara_numerico & mascara_nao_zero & mascara_decimais

    def _validar_col_11_tarifa(self, df: pd.DataFrame) -> bool:
        # Col 11 Tarifa = Índice 10 no iloc (11 - 1)
        coluna_crua = df.iloc[:, 10]

        coluna_tratada = coluna_crua.astype(str).str.replace(",", ".", regex=False)
        coluna_numerica = pd.to_numeric(coluna_tratada, errors="coerce")

        # 1. Validação de nulos ou falhas de conversão de texto
        if bool(coluna_numerica.isna().any()):
            logger.info(
                "DataFrame reprovado na validação da Coluna 11 (Tarifa). Valores inválidos ou não numéricos detectados."
            )
            return False

        # 2. Validação: Sem conter valor zero (0)
        if bool((coluna_numerica == 0).any()):
            logger.info(
                "DataFrame reprovado na validação da Coluna 11 (Tarifa). Encontrada tarifa zerada (0), o que não é permitido."
            )
            return False

        # 3. Validação de precisão decimal utilizando proteção contra erro de ponto flutuante
        valor_multiplicado = coluna_numerica * 100000
        valor_estabilizado = valor_multiplicado.round(
            9
        )  # Elimina resíduos binários do hardware

        valido_decimais = bool((valor_estabilizado % 1 == 0).all())

        if not valido_decimais:
            logger.info(
                "DataFrame reprovado na validação da Coluna 11 (Tarifa). Encontrados valores com mais de 5 casas decimais."
            )

        return valido_decimais

    def _mascara_cols_financeiras_12_15(self, df: pd.DataFrame) -> pd.Series:
        """Regra: Cols 12–15 (valores financeiros) -> Até 2 casas decimais."""
        # Cols 12 a 15 Humanas = Índices de 11 a 14 no fatiamento do Python
        bloco_financeiro = df.iloc[:, 11:15]

        bloco_tratado = bloco_financeiro.astype(str).map(lambda x: x.replace(",", "."))
        bloco_numerico = bloco_tratado.apply(pd.to_numeric, errors="coerce")

        mascara_numerico = ~bloco_numerico.isna().any(axis=1)

        valor_multiplicado = bloco_numerico * 100
        valor_estabilizado = valor_multiplicado.round(9)
        mascara_decimais = (valor_estabilizado % 1 == 0).all(axis=1)

        return mascara_numerico & mascara_decimais

    def _validar_cols_financeiras_12_15(self, df: pd.DataFrame) -> bool:
        # Cols 12 a 15 Humanas = Índices de 11 a 14 no fatiamento do Python
        bloco_financeiro = df.iloc[:, 11:15]

        bloco_tratado = bloco_financeiro.astype(str).map(lambda x: x.replace(",", "."))

        bloco_numerico = bloco_tratado.apply(pd.to_numeric, errors="coerce")

        # 1. Validação de nulos ou falhas de conversão de texto no bloco
        if bool(bloco_numerico.isna().any().any()):
            logger.info(
                "DataFrame reprovado na validação das Colunas Financeiras (12-15). Valores nulos ou não numéricos encontrados."
            )
            return False

        # 2. Validação de precisão decimal com proteção contra erro de ponto flutuante na matriz
        valor_multiplicado = bloco_numerico * 100
        valor_estabilizado = valor_multiplicado.round(
            9
        )  # Elimina resíduos binários do hardware

        valido = bool((valor_estabilizado % 1 == 0).all().all())

        if not valido:
            logger.info(
                "DataFrame reprovado na validação das Colunas Financeiras (12-15). Encontrados valores monetários com mais de 2 casas decimais."
            )

        return valido

    def _mascara_col_1_2_eot(self, df: pd.DataFrame) -> pd.Series:
        """Regra: Col 1 e 2 (EOT) -> Devem existir na tabela de EOTs do Anexo 5 Processado."""
        mascara_col_1 = bd_tabelas.validar_coluna_eot_df_mascara(df, indice_coluna=0)
        mascara_col_2 = bd_tabelas.validar_coluna_eot_df_mascara(df, indice_coluna=1)
        return mascara_col_1 & mascara_col_2

    def _validar_col_1_2_eot(self, df: pd.DataFrame) -> bool:
        """Regra: Col 1 e 2 (EOT) -> Devem existir na tabela de EOTs do Anexo 5 Processado."""
        # Col 1 = Índice 0 no iloc (1 - 1)
        # Col 2 = Índice 1 no iloc (2 - 1)

        valido_col_1 = bd_tabelas.validar_coluna_eot_df(df, indice_coluna=0)
        valido_col_2 = bd_tabelas.validar_coluna_eot_df(df, indice_coluna=1)

        if not valido_col_1:
            logger.info(
                "DataFrame reprovado na validação da Coluna 1 (EOT). Encontrados códigos de operadoras que não existem no Anexo 5 cadastrado."
            )

        if not valido_col_2:
            logger.info(
                "DataFrame reprovado na validação da Coluna 2 (EOT). Encontrados códigos de operadoras que não existem no Anexo 5 cadastrado."
            )

        if not (valido_col_1 and valido_col_2):
            return False

        return True

    def _mascara_col_2_eot_vivo(
        self, df: pd.DataFrame, nomes_fantasia_vivo: list[str]
    ) -> pd.Series:
        """Regra: Col 2 (EOT Vivo) -> Deve conter apenas EOTs correspondentes aos nomes fantasia da Vivo."""
        return bd_tabelas.validar_eots_por_nomes_fantasia_mascara(
            df, indice_coluna=1, nomes_fantasia=nomes_fantasia_vivo
        )

    def _validar_col_2_eot_vivo(
        self, df: pd.DataFrame, nomes_fantasia_vivo: list[str]
    ) -> bool:
        """Regra: Col 2 (EOT Vivo) -> Deve conter apenas EOTs correspondentes aos nomes fantasia da Vivo."""

        valido_col_2_vivo = bd_tabelas.validar_eots_por_nomes_fantasia(
            df, indice_coluna=1, nomes_fantasia=nomes_fantasia_vivo
        )
        if not valido_col_2_vivo:
            logger.info(
                "DataFrame reprovado na validação da Coluna 2 (EOT Vivo). Encontrados códigos de operadoras que não correspondem aos nomes fantasia da Vivo."
            )
            return False

        return True

    def __filtrar_tarifas_remuneradas(
        self,
        df: pd.DataFrame,
        debug: bool = False,
    ) -> pd.DataFrame:
        """
        Filtra apenas tarifas remuneradas e adiciona a coluna Remuneração.

        O mapeamento é realizado utilizando a coluna 7
        e a função `classificar_descritor_remuneracao`.
        """

        total_linhas_original = len(df)

        df = df.copy()

        # Coluna 7 = índice 6
        coluna = df.iloc[:, 6].astype(str).str.strip()

        # Mapeia a remuneração
        df["remuneracao"] = coluna.apply(classificar_descritor_remuneracao)

        # Mantém apenas linhas remuneradas
        df_remunerado = df[df["remuneracao"].notna()].copy()

        total_linhas_removidas = total_linhas_original - len(df_remunerado)
        total_linhas_restantes = len(df_remunerado)

        if debug:
            logger.info(
                "Filtro de remuneração aplicado -> "
                f"Original: {total_linhas_original} | "
                f"Tarifas não remuneradas: {total_linhas_removidas} | "
                f"Tarifas remuneradas: {total_linhas_restantes}"
            )

        return df_remunerado

    def _calcular_validacao_tarifas_remuneradas(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.Series] | None:
        """
        Núcleo de cálculo compartilhado entre `_validar_tarifas_remuneradas`
        (bool) e `_mascara_tarifas_remuneradas` (Series por linha). Retorna
        (df_final, validacao) indexados apenas pelo subconjunto de linhas
        remuneradas, ou None se não houver nenhuma linha remunerada.
        """
        df = df.fillna(0)
        df_remunerado = self.__filtrar_tarifas_remuneradas(df)

        if df_remunerado.empty:
            return None

        df_tarifas = bd_tabelas.validar_regiao(df_remunerado)

        # Preparar mes de trafego no formato da tabela de tarifas
        coluna_ano_mes = df_tarifas.iloc[:, 3].astype(str).str.strip()

        # O parâmetro errors="coerce" garante que se houver alguma linha com texto inválido, ela vire NaN em vez de quebrar o script.
        coluna_ano_mes = coluna_ano_mes.str.split(".").str[0]

        df_tarifas["mes_trafego_formatado"] = pd.to_datetime(
            coluna_ano_mes,
            format="%Y%m",
            errors="coerce",
        )
        df_tarifas["regra_desc"] = df_tarifas.iloc[:, 6].apply(
            classificar_regra_inicio_fim_desc
        )

        df_final = bd_tabelas.validar_tarifas_na_tabela(df=df_tarifas)

        # Verifica se o valor da coluna índice 10 (Tarifa) está contido na lista da coluna tarifa_tabela
        validacao = pd.Series(
            [
                (
                    (
                        float(str(tarifa_linha).replace(",", "."))
                        in [
                            float(str(valor).replace(",", "."))
                            for valor in tarifa_tabela
                        ]
                    )
                    if isinstance(tarifa_tabela, list)
                    else False
                )
                for tarifa_linha, tarifa_tabela in zip(
                    df_final.iloc[:, 10], df_final["tarifa_tabela"]
                )
            ],
            index=df_final.index,
        )

        return df_final, validacao

    def _validar_tarifas_remuneradas(
        self, df: pd.DataFrame, debug_em_arquivo: bool = False
    ) -> bool:
        resultado = self._calcular_validacao_tarifas_remuneradas(df)
        if resultado is None:
            return True

        df_final, validacao = resultado

        total_linhas = len(df_final)
        linhas_validas = int(validacao.sum())
        linhas_invalidas = total_linhas - linhas_validas

        valido = linhas_invalidas == 0

        if not valido:
            logger.info(
                f"Validação de tarifas concluída | "
                f"Total: {total_linhas} | "
                f"Válidas: {linhas_validas} | "
                f"Inválidas: {linhas_invalidas} | "
                f"Resultado final: {valido}"
            )

            if debug_em_arquivo:

                linhas_invalidas_df = df_final.loc[~validacao]

                conteudo_log = []

                conteudo_log.append("=" * 120)
                conteudo_log.append("LOG DE TARIFAS INVÁLIDAS")
                conteudo_log.append("=" * 120)
                conteudo_log.append(f"Total de linhas inválidas: {linhas_invalidas}")
                conteudo_log.append("")

                for indice, linha in linhas_invalidas_df.iterrows():

                    conteudo_log.append("#" * 120)
                    conteudo_log.append(f"LINHA INVALIDA | INDEX DF: {indice}")
                    conteudo_log.append("#" * 120)
                    tarifas_invalidas = ""

                    for coluna, valor in linha.items():

                        conteudo_log.append(f"{coluna}: {valor}")
                        if coluna == 10:
                            tarifas_invalidas = f"Tarifa inválida encontrada: {valor} |Valores válidos na tabela: {linha['tarifa_tabela']}"

                    conteudo_log.append("")
                    conteudo_log.append(f"RESULTADO: {tarifas_invalidas}")
                    conteudo_log.append("-" * 120)
                    conteudo_log.append("")

                salvar_debug_log(
                    nome_arquivo="LOG_TARIFAS_INVALIDAS_",
                    conteudo="\n".join(conteudo_log),
                )
        return valido

    def _mascara_tarifas_remuneradas(self, df: pd.DataFrame) -> pd.Series:
        """
        Regra: tarifa da linha deve corresponder a uma tarifa válida na
        tabela para a região/GH/regra/mês daquela linha. Linhas não
        remuneradas (fora do escopo desta regra) ficam implicitamente
        True — não reprovam por essa validação.
        """
        mascara_completa = pd.Series(True, index=df.index)

        resultado = self._calcular_validacao_tarifas_remuneradas(df)
        if resultado is None:
            return mascara_completa

        _, validacao = resultado
        mascara_completa.loc[validacao.index] = validacao
        return mascara_completa
