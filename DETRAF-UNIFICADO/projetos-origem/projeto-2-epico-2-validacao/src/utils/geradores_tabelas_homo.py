import sqlite3
from pathlib import Path
import pandas as pd
import os
import sys

# Sobe dois níveis para chegar na raiz 'DETRAF-2-FULL'
raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(raiz)

from src.config.configuration import (
    EXTENSOES_CSV,
    EXTENSOES_EXCEL,
    EXTENSOES_PERMITIDAS,
)


def converter_tabela_para_sqlite(
    caminho_arquivo: Path,
    caminho_destino_sqlite: Path,
    nome_tabela: str,
    linha_cabecalho: int = 0,
) -> None:
    """
    Lê um arquivo (CSV ou Excel) a partir de uma linha de cabeçalho específica,
    limpa colunas vazias ou sem nome e despeja os dados em um banco SQLite (.db).

    Args:
        caminho_arquivo (Path): Objeto Path para o arquivo de origem (CSV ou Excel).
        caminho_destino_sqlite (Path): Objeto Path completo de onde o banco .db será salvo.
        nome_tabela (str): Nome da tabela que será criada dentro do banco SQLite.
        linha_cabecalho (int): O índice da linha (baseado em zero) onde se encontra o cabeçalho.
    """
    if not caminho_arquivo.exists():
        raise FileNotFoundError(
            f"O arquivo de origem não foi encontrado: {caminho_arquivo}"
        )

    try:
        # 1. Garante que as pastas de destino do SQLite existem
        caminho_destino_sqlite.parent.mkdir(parents=True, exist_ok=True)

        # 2. Identifica a extensão para usar o leitor correto
        extensao = caminho_arquivo.suffix.lower()

        # 3. Leitura condicional performática baseado no formato
        if extensao in EXTENSOES_CSV:
            # Para CSV, skiprows pula as linhas físicas e o header=0 define a primeira linha restante como cabeçalho
            df = pd.read_csv(
                caminho_arquivo, header=0, skiprows=linha_cabecalho, engine="c", sep=";"
            )
        elif extensao in EXTENSOES_EXCEL:
            df = pd.read_excel(
                caminho_arquivo, header=0, skiprows=linha_cabecalho, engine="openpyxl"
            )
        else:
            raise ValueError(
                f"Formato '{extensao}' não suportado. "
                f"Formatos permitidos: {', '.join(EXTENSOES_PERMITIDAS)}"
            )

        # 4. LIMPEZA DE COLUNAS VAZIAS E FANTASMAS
        # Remove colunas onde TODOS os valores estão vazios (NaN)
        df = df.dropna(how="all", axis=1)

        # Remove colunas sem nome (geradas pelo Pandas como 'Unnamed:')
        colunas_validas = [
            col
            for col in df.columns
            if pd.notna(col) and not str(col).strip().startswith("Unnamed:")
        ]
        df = df[colunas_validas]

        # 5. Cria a conexão com o SQLite e grava os dados filtrados em lote (Bulk Insert)
        with sqlite3.connect(caminho_destino_sqlite) as conexao:
            df.to_sql(
                name=nome_tabela,
                con=conexao,
                index=False,
                if_exists="replace",
                chunksize=50000,
            )

    except Exception as erro:
        raise RuntimeError(
            f"Falha na conversão do arquivo '{caminho_arquivo.name}' para SQLite: {erro}"
        )


# ==============================================================================
# EXECUÇÃO DO PROCESSO
# ==============================================================================

CAMINHO_BANCOS_SALVOS = r"C:\Users\btime\Desktop\Projetos\detraf 2 - Completo\DETRAF-2-FULL\MOCK\banco de dados"

pasta_banco = Path(CAMINHO_BANCOS_SALVOS)
arquivo_sqlite_final = pasta_banco / "TABELAS_DETRAF.db"

# converter_tabela_para_sqlite(
#     caminho_destino_sqlite=arquivo_sqlite_final,
#     caminho_arquivo=Path(
#         r"C:\Users\btime\Desktop\Projetos\detraf 2 - Completo\DETRAF-2-FULL\MOCK\Anexo5.xlsx"
#     ),
#     nome_tabela="tbl_anexo5_processado",
#     linha_cabecalho=7,
# )

# converter_tabela_para_sqlite(
#     caminho_destino_sqlite=arquivo_sqlite_final,
#     caminho_arquivo=Path(
#         r"C:\Users\btime\Desktop\Projetos\detraf 2 - Completo\DETRAF-2-FULL\MOCK\tabela_tarifa.csv"
#     ),
#     nome_tabela="tbl_detraf_tarifas",
#     linha_cabecalho=0,
# )

# converter_tabela_para_sqlite(
#     caminho_destino_sqlite=arquivo_sqlite_final,
#     caminho_arquivo=Path(
#         r"C:\Users\btime\Desktop\Projetos\detraf 2 - Completo\DETRAF-2-FULL\MOCK\Mapeamento_Descritores.xlsx"
#     ),
#     nome_tabela="tbl_detraf_mapeamento_descritores",
#     linha_cabecalho=0,
# )
converter_tabela_para_sqlite(
    caminho_destino_sqlite=arquivo_sqlite_final,
    caminho_arquivo=Path(
        r"C:\Users\btime\Desktop\Projetos\detraf 2 - Completo\DETRAF-2-FULL\MOCK\tabela_arquivos.csv"
    ),
    nome_tabela="tbl_detraf_despesa_arquivos",
    linha_cabecalho=0,
)
