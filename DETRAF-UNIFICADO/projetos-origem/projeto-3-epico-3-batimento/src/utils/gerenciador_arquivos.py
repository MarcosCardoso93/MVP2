import re
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Tuple
from typing import Optional

from src.config.configuration import (
    EXTENSOES_PERMITIDAS,
    EXTENSOES_CSV,
    EXTENSOES_EXCEL,
)


def _validar_extensao(extensao: str) -> None:
    """
    Função interna para validar se a extensão do arquivo é suportada pela biblioteca.
    """
    if extensao.lower() not in EXTENSOES_PERMITIDAS:
        raise ValueError(
            f"Formato de arquivo não suportado: '{extensao}'. "
            f"Os formatos permitidos são: {', '.join(EXTENSOES_PERMITIDAS)}"
        )


def _validar_indice_coluna(df: pd.DataFrame, indice_coluna: int) -> None:
    """
    Função interna para garantir que o índice da coluna solicitado existe no DataFrame.
    """
    total_colunas = df.shape[1]
    if not (0 <= indice_coluna < total_colunas):
        raise IndexError(
            f"Índice de coluna inválido: {indice_coluna}. "
            f"O DataFrame possui apenas {total_colunas} colunas (índices de 0 a {total_colunas - 1})."
        )


def carregar_dados(
    caminho_arquivo: Path, mostrar_cabecalho: bool = False
) -> pd.DataFrame:
    """
    Carrega um arquivo CSV ou planilha Excel em um DataFrame do Pandas.
    Detecta dinamicamente a presença de cabeçalho baseado nas 3 primeiras colunas.

    Args:
        caminho_arquivo (Path): Objeto Path representando o caminho do arquivo.
        mostrar_cabecalho (bool): Se False (default), remove a linha de cabeçalho caso
                                  ela seja detectada, mantendo apenas dados brutos.

    Returns:
        pd.DataFrame: DataFrame contendo os dados do arquivo carregado.

    Raises:
        FileNotFoundError: Se o arquivo não for encontrado no caminho especificado.
        RuntimeError: Para erros inesperados na leitura do arquivo.
    """
    if not caminho_arquivo.exists():
        raise FileNotFoundError(f"O arquivo não foi encontrado: {caminho_arquivo}")

    extensao = caminho_arquivo.suffix
    _validar_extensao(extensao)

    # Função auxiliar interna para detectar o separador por heurística de contagem
    def _detectar_separador_csv(caminho: Path, linhas_amostra: int = 20) -> str:
        separadores_alvo = [";", ",", "\t"]
        pontuacao = {sep: 0 for sep in separadores_alvo}
        try:
            with open(caminho, mode="r", encoding="utf-8", errors="ignore") as arquivo:
                linhas_analisadas = 0
                for linha in arquivo:
                    linha_limpa = linha.strip()
                    if not linha_limpa or len(linha_limpa) < 10:
                        continue
                    for sep in separadores_alvo:
                        pontuacao[sep] += linha_limpa.count(sep)
                    linhas_analisadas += 1
                    if linhas_analisadas >= linhas_amostra:
                        break
            vencedor = max(pontuacao, key=pontuacao.get)  # type: ignore
            return vencedor if pontuacao[vencedor] > 0 else ";"
        except Exception:
            return ";"

    try:
        extensao_lower = extensao.lower()

        # Carrega o arquivo SEMPRE com header=None para trazer a primeira linha para o corpo (índice 0)
        if extensao_lower in EXTENSOES_CSV:
            separador_detectado = _detectar_separador_csv(caminho_arquivo)
            df = pd.read_csv(
                caminho_arquivo,
                engine="c",
                header=None,
                sep=separador_detectado,
                dtype=str,  # Lê tudo como string para evitar problemas de formatação automática
            )
        elif extensao_lower in EXTENSOES_EXCEL:
            df = pd.read_excel(
                caminho_arquivo, engine="openpyxl", header=None, dtype=str
            )
        else:
            raise ValueError(f"Extensão '{extensao}' não é suportada para leitura.")

        # Se o DataFrame veio vazio, retorna imediatamente
        if df.shape[0] == 0:
            return df

        # --- LÓGICA DE DETECÇÃO DO CABEÇALHO ---
        # Extrai os valores das 3 primeiras colunas da primeira linha (índice 0)
        tres_primeiras_celulas = df.iloc[0, 0:3].astype(str).str.strip().tolist()

        # Regex para validar se a célula é texto puro (contém apenas letras, acentos ou espaços)
        # Impede que números guardados como texto (ex: "123") passem como cabeçalho
        padrao_texto = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ\s_\-]+$")

        # Verifica se todas as 3 primeiras células casam com a regra de texto puro
        eh_cabecalho = all(
            bool(padrao_texto.match(celula)) for celula in tres_primeiras_celulas
        )

        # Se detectou que a primeira linha é um cabeçalho e o usuário não quer mostrá-lo
        if eh_cabecalho and not mostrar_cabecalho:
            # Remove a linha 0 de títulos e reseta os índices das linhas de dados para começar do 0
            df = df.iloc[1:].reset_index(drop=True)

        return df

    except Exception as erro:
        raise RuntimeError(
            f"Erro ao processar a leitura do arquivo {caminho_arquivo}: {erro}"
        )


def remover_linhas_por_valor(
    df: pd.DataFrame, indice_coluna: int, valor: Any
) -> pd.DataFrame:
    """
    Remove do DataFrame todas as linhas onde a coluna no índice especificado possui o valor indicado.

    Args:
        df (pd.DataFrame): O DataFrame original.
        indice_coluna (int): O índice numérico da coluna (começando em 0).
        valor (Any): Valor que define quais linhas serão removidas.

    Returns:
        pd.DataFrame: Um novo DataFrame sem as linhas removidas.
    """
    _validar_indice_coluna(df, indice_coluna)

    # .iloc[:, indice_coluna] acessa a coluna de forma posicional e ultra veloz
    filtro_linhas_manter = df.iloc[:, indice_coluna] != valor
    return df[filtro_linhas_manter].copy()


def obter_linhas_por_valor(
    df: pd.DataFrame, indice_coluna: int, valor: Any
) -> List[Dict[Any, Any]]:
    """
    Filtra o DataFrame por índice de coluna e retorna uma lista de dicionários
    representando as linhas que possuem o valor especificado.

    Args:
        df (pd.DataFrame): O DataFrame original.
        indice_coluna (int): O índice numérico da coluna (começando em 0).
        valor (Any): Valor a ser buscado.

    Returns:
        List[Dict[Any, Any]]: Lista onde cada item é um mapeamento {coluna: valor} da linha.
    """
    _validar_indice_coluna(df, indice_coluna)

    filtro_linhas = df.iloc[:, indice_coluna] == valor
    df_filtrado = df[filtro_linhas]

    return df_filtrado.to_dict(orient="records")


def dividir_por_valor(
    df: pd.DataFrame, indice_coluna: int, valor: Any
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Divide o DataFrame original em dois novos DataFrames com base no valor de uma coluna (por índice).

    Args:
        df (pd.DataFrame): O DataFrame original.
        indice_coluna (int): O índice numérico da coluna (começando em 0).
        valor (Any): Valor de referência para a divisão.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (DataFrame com o valor, DataFrame com o restante).
    """
    _validar_indice_coluna(df, indice_coluna)

    condicao = df.iloc[:, indice_coluna] == valor

    df_igual = df[condicao].copy()
    df_restante = df[~condicao].copy()

    return df_igual, df_restante


def adicionar_linha(df: pd.DataFrame, valores_linha: List[Any]) -> pd.DataFrame:
    """
    Adiciona uma nova linha ao final do DataFrame baseando-se na ordem posicional dos elementos.

    Args:
        df (pd.DataFrame): O DataFrame original.
        valores_linha (List[Any]): Lista com os valores da nova linha, na mesma ordem das colunas.

    Returns:
        pd.DataFrame: Um novo DataFrame contendo a linha adicionada.
    """
    if len(valores_linha) != df.shape[1]:
        raise ValueError(
            f"Quantidade de valores fornecida ({len(valores_linha)}) "
            f"não corresponde ao número de colunas do DataFrame ({df.shape[1]})."
        )

    # Criamos o DataFrame da nova linha mapeando os valores diretamente para as colunas existentes do df
    nova_linha_df = pd.DataFrame([valores_linha], columns=df.columns)

    return pd.concat([df, nova_linha_df], ignore_index=True)


def salvar_dados(
    df: pd.DataFrame, caminho_salvamento: Path, incluir_cabecalho: bool = False
) -> Path:
    """
    Salva o DataFrame no caminho completo especificado, identificando o formato (CSV ou Planilha).

    Cria os diretórios da pasta pai caso eles não existam no sistema.

    Args:
        df (pd.DataFrame): O DataFrame a ser salvo.
        caminho_salvamento (Path): Objeto Path representando o caminho completo de destino
                                   (ex: Path("dados/saida/resultado.xlsx")).
        incluir_cabecalho (bool): Se False, salva o arquivo sem a linha de títulos/nomes de colunas.

    Returns:
        Path: O objeto Path completo de onde o arquivo foi salvo.

    """
    # .suffix pega a extensão direto do arquivo (ex: '.csv')
    extensao = caminho_salvamento.suffix
    _validar_extensao(extensao)

    try:
        # .parent pega o diretório onde o arquivo vai ficar e o .mkdir cria a estrutura se não existir
        caminho_salvamento.parent.mkdir(parents=True, exist_ok=True)

        extensao_lower = extensao.lower()
        if extensao_lower in EXTENSOES_CSV:
            df.to_csv(
                caminho_salvamento,
                index=False,
                header=incluir_cabecalho,
                encoding="utf-8",
            )
        else:
            df.to_excel(
                caminho_salvamento,
                index=False,
                header=incluir_cabecalho,
                engine="openpyxl",
            )

        return caminho_salvamento

    except Exception as erro:
        raise IOError(f"Falha ao gravar o arquivo em '{caminho_salvamento}': {erro}")


def validar_quantidade_colunas(df: pd.DataFrame, numero_esperado: int) -> bool:
    """
    Valida se o DataFrame possui exatamente a quantidade de colunas esperada.

    Útil para fail-fast (interromper o processo cedo) ao processar arquivos inválidos.

    Args:
        df (pd.DataFrame): O DataFrame a ser validado.
        numero_esperado (int): O número exato de colunas que o DF deve ter.

    Returns:
        bool: True se a quantidade for igual à esperada, False caso contrário.
    """
    # df.shape[1] obtém o número de colunas instantaneamente (complexidade O(1))
    return df.shape[1] == numero_esperado


def validar_quantidade_minima_colunas(df: pd.DataFrame, numero_minimo: int) -> bool:
    """
    Valida se o DataFrame possui pelo menos a quantidade mínima de colunas esperada.

    Útil para garantir que as colunas posicionais necessárias para o processamento
    existam no arquivo antes de iniciar as operações.

    Args:
        df (pd.DataFrame): O DataFrame a ser validado.
        numero_minimo (int): O número mínimo de colunas que o DF deve conter.

    Returns:
        bool: True se a quantidade de colunas for maior ou igual ao mínimo, False caso contrário.
    """
    # df.shape[1] obtém o número de colunas instantaneamente em O(1)
    return df.shape[1] >= numero_minimo


def obter_coluna_por_indice(df: pd.DataFrame, indice_coluna: int) -> pd.Series:
    """
    Retorna uma única coluna específica do DataFrame com base no seu índice numérico.

    Args:
        df (pd.DataFrame): O DataFrame original.
        indice_coluna (int): O índice da coluna desejada (começando em 0).

    Returns:
        pd.Series: A coluna extraída em formato de Series do Pandas.
    """
    # Reutiliza a lógica de validação de índice para evitar erros silenciosos
    total_colunas = df.shape[1]
    if not (0 <= indice_coluna < total_colunas):
        raise IndexError(
            f"Índice {indice_coluna} fora dos limites. O DF possui {total_colunas} colunas."
        )

    return df.iloc[:, indice_coluna]


def obter_lista_colunas_por_indices(
    df: pd.DataFrame, indices_colunas: List[int]
) -> pd.DataFrame:
    """
    Retorna um novo DataFrame contendo apenas as colunas especificadas na lista de índices.

    Args:
        df (pd.DataFrame): O DataFrame original.
        indices_colunas (List[int]): Lista de inteiros com os índices das colunas desejadas.

    Returns:
        pd.DataFrame: Um novo DataFrame apenas com as colunas selecionadas.
    """
    total_colunas = df.shape[1]
    # Valida todos os índices de uma vez de forma performática
    for ind in indices_colunas:
        if not (0 <= ind < total_colunas):
            raise IndexError(
                f"Índice {ind} da lista está fora dos limites (0 a {total_colunas - 1})."
            )

    # O iloc aceita uma lista de inteiros diretamente, fazendo a extração vetorizada na memória
    return df.iloc[:, indices_colunas].copy()


def obter_linha_por_indice(df: pd.DataFrame, indice_linha: int) -> pd.Series:
    """
    Retorna uma única linha específica do DataFrame com base no seu índice numérico.

    Args:
        df (pd.DataFrame): O DataFrame original.
        indice_linha (int): O índice da linha desejada (começando em 0).

    Returns:
        pd.Series: A linha extraída em formato de Series do Pandas.
    """
    total_linhas = df.shape[0]
    if not (0 <= indice_linha < total_linhas):
        raise IndexError(
            f"Índice de linha {indice_linha} fora dos limites (0 a {total_linhas - 1})."
        )

    return df.iloc[indice_linha]


def obter_lista_linhas_por_indices(
    df: pd.DataFrame, indices_linhas: List[int]
) -> pd.DataFrame:
    """
    Retorna um novo DataFrame contendo apenas as linhas especificadas na lista de índices.

    Args:
        df (pd.DataFrame): O DataFrame original.
        indices_linhas (List[int]): Lista de inteiros com os índices das linhas desejadas.

    Returns:
        pd.DataFrame: Um novo DataFrame apenas com as linhas selecionadas.
    """
    total_linhas = df.shape[0]
    for ind in indices_linhas:
        if not (0 <= ind < total_linhas):
            raise IndexError(
                f"Índice de linha {ind} fora dos limites (0 a {total_linhas - 1})."
            )

    return df.iloc[indices_linhas].copy()


def extrair_nome_arquivo(caminho_arquivo: Path, incluir_extensao: bool = True) -> str:
    """
    Recebe o objeto Path de um arquivo e retorna apenas o seu nome.

    Exemplo: Path('/dados/entrada/planilha.xlsx') -> 'planilha.xlsx' ou 'planilha'

    Args:
        caminho_arquivo (Path): Objeto Path representando o caminho do arquivo.
        incluir_extensao (bool): Se False, retorna o nome sem a extensão.

    Returns:
        str: Apenas o nome do arquivo.
    """

    return caminho_arquivo.name if incluir_extensao else caminho_arquivo.stem


def manter_linhas_por_lista_valores(
    df: pd.DataFrame, indice_coluna: int, valores_manter: List[Any]
) -> pd.DataFrame:
    """
    Mantém no DataFrame apenas as linhas onde a coluna no índice especificado
    possui valores contidos na lista informada, removendo todas as outras.

    Args:
        df (pd.DataFrame): O DataFrame original.
        indice_coluna (int): O índice numérico da coluna (zero-based).
        valores_manter (List[Any]): Lista de valores permitidos que devem ser mantidos.

    Returns:
        pd.DataFrame: Um novo DataFrame contendo apenas as linhas cujos valores
                      da coluna alvo estão na lista.
    """
    _validar_indice_coluna(df, indice_coluna)

    # Converter a lista para conjunto (set) otimiza a busca interna do Pandas para complexidade O(1)
    conjunto_valores = set(valores_manter)

    # .isin() mapeia o lote na velocidade do C. O operador '~' inverte a lógica,
    # garantindo que selecionemos apenas quem NÃO está fora da lista (ou seja, quem deve ficar).
    filtro_linhas_manter = df.iloc[:, indice_coluna].isin(conjunto_valores)

    # Retorna a cópia profunda isolada para evitar mutabilidade compartilhada no pipeline
    return df[filtro_linhas_manter].copy()


def renomear_arquivo_com_sufixo(
    caminho_arquivo: Path,
    sufixo: str,
) -> Path:
    """
    Renomeia um arquivo adicionando um sufixo ao final do nome,
    preservando a extensão original.

    Caso já exista um arquivo com o nome de destino, ele será
    sobrescrito.

    Exemplo:
        relatorio.xlsx + "_processado"
        -> relatorio_processado.xlsx

    Args:
        caminho_arquivo: Caminho do arquivo que será renomeado.
        sufixo: Texto que será acrescentado ao final do nome do arquivo.

    Returns:
        Path: Caminho do arquivo renomeado.

    Raises:
        FileNotFoundError: Caso o arquivo informado não exista.
    """
    if not caminho_arquivo.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_arquivo}")

    novo_caminho = caminho_arquivo.with_name(
        f"{caminho_arquivo.stem}{sufixo}{caminho_arquivo.suffix}"
    )

    return caminho_arquivo.replace(novo_caminho)


def exportar_dataframe_para_excel(
    df: pd.DataFrame,
    cabecalho: Optional[list[str]],
    pasta_destino: Path,
    nome_arquivo: str,
    ignorar_colunas_extras: bool = False,
    nome_aba: str = "Sheet1",
    adicionar_como_nova_aba: bool = True,
) -> Path:
    """
    Gera uma planilha Excel a partir de um DataFrame.

    Regras:
    - Se cabecalho for None, exporta o DataFrame exatamente como está.
    - Se cabecalho for informado:
        * escreve o cabeçalho informado na primeira linha;
        * escreve os dados a partir da segunda linha;
        * se ignorar_colunas_extras=True, exporta apenas as primeiras
          len(cabecalho) colunas do DataFrame;
        * se ignorar_colunas_extras=False, mantém as colunas extras
          preenchendo seus cabeçalhos com "COLUNA NAO IDENTIFICADA".
    - Se adicionar_como_nova_aba=False, sobrescreve o arquivo completo.
    - Se adicionar_como_nova_aba=True e o arquivo já existir, adiciona
      uma nova aba ao arquivo existente.
    - Se adicionar_como_nova_aba=True e a aba já existir, uma exceção é lançada.

    :param df: DataFrame com os dados.
    :param cabecalho: Cabeçalho customizado ou None.
    :param pasta_destino: Pasta onde o arquivo será salvo.
    :param nome_arquivo: Nome do arquivo, com ou sem extensão .xlsx.
    :param ignorar_colunas_extras: Define se colunas além do cabeçalho
        devem ser descartadas.
    :param nome_aba: Nome da aba da planilha.
    :param adicionar_como_nova_aba: Se True, adiciona uma nova aba ao
        arquivo existente.
    :return: Caminho completo do arquivo gerado.
    """
    if df is None or df.empty:
        raise ValueError("DataFrame vazio ou nulo.")

    pasta_destino.mkdir(parents=True, exist_ok=True)

    if not nome_arquivo.lower().endswith(".xlsx"):
        nome_arquivo += ".xlsx"

    caminho_final = pasta_destino / nome_arquivo

    try:
        if caminho_final.exists() and adicionar_como_nova_aba:
            writer = pd.ExcelWriter(
                caminho_final,
                engine="openpyxl",
                mode="a",
                if_sheet_exists="replace",
            )
        else:
            writer = pd.ExcelWriter(
                caminho_final,
                engine="openpyxl",
                mode="w",
            )

        with writer:
            if cabecalho is None:
                df.to_excel(
                    writer,
                    sheet_name=nome_aba,
                    index=False,
                )
            else:
                quantidade_colunas_cabecalho = len(cabecalho)

                if ignorar_colunas_extras:
                    df_exportacao = df.iloc[:, :quantidade_colunas_cabecalho].copy()

                    cabecalho_final = cabecalho

                else:
                    df_exportacao = df.copy()

                    quantidade_colunas_extras = max(
                        0,
                        len(df.columns) - quantidade_colunas_cabecalho,
                    )

                    cabecalho_final = (
                        cabecalho
                        + ["COLUNA NAO IDENTIFICADA"] * quantidade_colunas_extras
                    )

                df_exportacao.to_excel(
                    writer,
                    sheet_name=nome_aba,
                    index=False,
                    header=False,
                    startrow=1,
                )

                worksheet = writer.sheets[nome_aba]

                for indice_coluna, nome_coluna in enumerate(
                    cabecalho_final,
                    start=1,
                ):
                    worksheet.cell(
                        row=1,
                        column=indice_coluna,
                        value=nome_coluna,
                    )

        return caminho_final

    except Exception as e:
        raise RuntimeError(
            f"Falha ao exportar dados para a planilha Excel " f"[{nome_arquivo}]: {e}"
        ) from e
