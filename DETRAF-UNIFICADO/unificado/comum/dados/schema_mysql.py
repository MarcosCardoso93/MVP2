"""Tradução de schema MySQL -> SQLite, e leitura do DDL real em texto.

Extraído de ``espelhar_banco.py`` em 2026-08-10, quando o
``preparar_banco_dev.py`` passou a precisar da mesma tradução para montar o
espelho a partir do ``banco_de_dados/schema-real-*.sql``, sem MySQL.

Copiar as tabelas de tipos para o segundo script teria criado uma segunda
declaração do que o SQLite deve receber — exatamente o problema que
``comum.dados.tabelas`` existe para não ter. Aqui há **uma**.

Duas entradas, o mesmo destino:

- ``colunas_do_ddl`` / ``tabelas_do_arquivo_ddl`` — a partir do texto do
  ``SHOW CREATE TABLE`` já gravado em arquivo.
- as tuplas ``(nome, tipo, aceita_nulo)`` que ``espelhar_banco`` monta lendo
  ``SHOW COLUMNS`` da conexão.

Ambas alimentam ``criar_tabela_sqlite``.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

#: Uma coluna do DDL: ``(nome, tipo_mysql, aceita_nulo, auto_incremento)``.
#:
#: O quarto item é opcional na entrada — ``criar_tabela_sqlite`` aceita tuplas de
#: três, que é o que as chamadas antigas passam.
Coluna = tuple[str, str, bool, bool]

#: MySQL -> SQLite. O SQLite tem tipagem dinâmica, então a tradução é mais uma
#: declaração de intenção do que uma restrição — mas ela importa para o
#: `read_sql` do pandas devolver o mesmo tipo dos dois lados.
TIPOS = {
    "int": "INTEGER",
    "bigint": "INTEGER",
    "smallint": "INTEGER",
    "tinyint": "INTEGER",
    "mediumint": "INTEGER",
    "float": "REAL",
    "double": "REAL",
    # `REAL` e não `TEXT`: o código faz `.astype(float)` sobre estas colunas, e
    # um espelho que devolvesse texto quebraria de um jeito que o banco real não
    # quebra — o espelho estaria testando a si mesmo. A perda de precisão é real
    # e vira aviso, logo abaixo.
    "decimal": "REAL",
    "numeric": "REAL",
    "date": "TEXT",
    "datetime": "TEXT",
    "timestamp": "TEXT",
    "time": "TEXT",
}

#: Tipos cuja tradução **perde informação**. Cada um vira aviso nomeando a
#: coluna: um `DECIMAL(18,6)` de valor financeiro virando `REAL` é exatamente o
#: tipo de detalhe que explica uma diferença de centavos meses depois.
TRADUCAO_IMPRECISA = {
    "decimal": "REAL — ponto flutuante binário não representa decimal exato",
    "numeric": "REAL — ponto flutuante binário não representa decimal exato",
    "datetime": "TEXT — deixa de ser comparável como data pelo banco",
    "timestamp": "TEXT — deixa de ser comparável como data pelo banco",
    "date": "TEXT — deixa de ser comparável como data pelo banco",
}

#: Linhas do ``SHOW CREATE TABLE`` que encerram o bloco de colunas.
_FIM_DAS_COLUNAS = re.compile(r"^(PRIMARY KEY|KEY|UNIQUE|CONSTRAINT|FULLTEXT|SPATIAL|\))")

#: ``\`nome\` tipo`` — o tipo leva junto o parêntese quando tem um
#: (``decimal(18,6)``, ``enum('DETRAF','EXPECTATIVA','ERRO')``). Não há
#: parêntese aninhado em declaração de coluna, então ``[^)]*`` basta.
_COLUNA = re.compile(r"^`([^`]+)`\s+(\w+(?:\([^)]*\))?)")

_INICIO_TABELA = re.compile(r"CREATE TABLE `([^`]+)`")


def tipo_sqlite(tipo_mysql: str) -> tuple[str, str | None]:
    """
    Traduz um tipo do MySQL, devolvendo também o aviso quando a tradução perde.

    Returns:
        ``(tipo_sqlite, aviso_ou_None)``.
    """
    # O MySQL devolve `bigint(20) unsigned`, `int unsigned zerofill`, `decimal
    # (18,6)`. O tipo é a primeira palavra antes do parêntese; o resto é
    # modificador e não muda a tradução.
    base = tipo_mysql.split("(")[0].strip().lower().split()[0] if tipo_mysql.strip() else ""
    return TIPOS.get(base, "TEXT"), TRADUCAO_IMPRECISA.get(base)


def criar_tabela_sqlite(
    destino: sqlite3.Connection, tabela: str, colunas
) -> list[str]:
    """
    Recria a tabela no SQLite. Devolve os avisos de tradução imprecisa.

    ⚠️ A coluna ``AUTO_INCREMENT`` vira ``INTEGER PRIMARY KEY``, e não
    ``INTEGER NOT NULL``. No SQLite, só essa forma exata é apelido do ``rowid`` e
    se preenche sozinha; sem ela, todo ``INSERT`` que omite o ``id`` — que é o
    que o código faz, porque no MySQL o banco resolve — morre com
    ``NOT NULL constraint failed``. Descoberto em 2026-08-10, na primeira
    execução que **escreveu** no espelho: até então ele só era lido.
    """
    avisos: list[str] = []
    definicoes = []

    for coluna in colunas:
        nome, tipo_mysql, aceita_nulo = coluna[0], coluna[1], coluna[2]
        auto_incremento = coluna[3] if len(coluna) > 3 else False

        tipo, aviso = tipo_sqlite(tipo_mysql)
        if aviso:
            avisos.append(f"{tabela}.{nome}: {tipo_mysql} -> {aviso}")

        if auto_incremento:
            definicoes.append(f'"{nome}" INTEGER PRIMARY KEY')
            continue

        # As aspas duplas preservam nomes com espaço e acento — o
        # `tbl_anexo5_processado` tem "Nome Fantasia" e "Endereco de
        # Correspondencia", que sem elas viram erro de sintaxe.
        definicoes.append(f'"{nome}" {tipo}' + ("" if aceita_nulo else " NOT NULL"))

    destino.execute(f'DROP TABLE IF EXISTS "{tabela}"')
    destino.execute(f'CREATE TABLE "{tabela}" ({", ".join(definicoes)})')
    return avisos


def _coluna_da_linha(achado: re.Match, linha: str) -> Coluna:
    """Monta a tupla da coluna a partir da linha já casada por ``_COLUNA``."""
    em_caixa_alta = linha.upper()
    return (
        achado.group(1),
        achado.group(2),
        # `NOT NULL` é o único jeito de o MySQL declarar obrigatoriedade nesta
        # posição; ausência significa que aceita nulo.
        "NOT NULL" not in em_caixa_alta,
        "AUTO_INCREMENT" in em_caixa_alta,
    )


def colunas_do_ddl(ddl: str) -> list[Coluna]:
    """
    Colunas de **um** ``CREATE TABLE``, na ordem em que aparecem.

    A saída de ``SHOW CREATE TABLE`` é gerada por máquina e estável: uma coluna
    por linha, o nome entre crases, e o bloco de colunas termina na primeira
    linha que começa com ``PRIMARY KEY``, ``KEY``, ``UNIQUE`` ou ``)``.
    """
    colunas: list[Coluna] = []
    dentro = False

    for linha in ddl.splitlines():
        despida = linha.strip()

        if _INICIO_TABELA.match(despida):
            dentro = True
            continue

        if not dentro:
            continue

        if _FIM_DAS_COLUNAS.match(despida):
            break

        achado = _COLUNA.match(despida)
        if achado:
            colunas.append(_coluna_da_linha(achado, despida))

    return colunas


def tabelas_do_arquivo_ddl(texto: str) -> dict[str, list[Coluna]]:
    """Todas as tabelas de um ``schema-real-*.sql``, na ordem do arquivo."""
    tabelas: dict[str, list[Coluna]] = {}
    atual: str | None = None

    for linha in texto.splitlines():
        despida = linha.strip()

        inicio = _INICIO_TABELA.match(despida)
        if inicio:
            atual = inicio.group(1)
            tabelas[atual] = []
            continue

        if atual is None:
            continue

        if _FIM_DAS_COLUNAS.match(despida):
            atual = None
            continue

        achado = _COLUNA.match(despida)
        if achado:
            tabelas[atual].append(_coluna_da_linha(achado, despida))

    return tabelas


def ddl_mais_recente(diretorio: Path) -> Path | None:
    """
    O ``schema-real-*.sql`` mais novo do diretório, ou ``None``.

    A ordem alfabética serve porque o carimbo no nome é ``AAAAMMDD``.
    """
    arquivos = sorted(diretorio.glob("schema-real-*.sql"))
    return arquivos[-1] if arquivos else None
