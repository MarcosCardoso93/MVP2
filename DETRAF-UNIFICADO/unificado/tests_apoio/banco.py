"""O SQLite de teste, com o schema **derivado do banco real**.

Uma fonte só, quatro consumidores. O motivo de existir está no seed antigo do
RPA 1: ele criava `tbl_anexo5_processado` com **duas** colunas, e a validação lê
seis — `validar_regiao` procura a região e estouraria com `KeyError`. Enquanto o
RPA 1 não validava nada, ninguém notou.

## Por que o DDL não é escrito aqui (2026-08-06)

Até esta data o `CREATE TABLE` era digitado neste arquivo, e os nomes de coluna
viviam em **quatro** declarações independentes que concordavam só por
disciplina: aqui, no `conftest.py` do RPA 3, no `preparar_banco_dev.py` e em
`comum.dados.tabelas.COLUNAS_ESPERADAS`.

Não concordavam. A primeira leitura do MySQL real mostrou que os nomes do Anexo 5
**não têm acento** e que a coluna da remuneração na contestação é `remuneracoes`,
no plural — e a suíte passava assim mesmo, porque os `fixtures` declaravam o
schema que o código supunha. **Os testes validavam a suposição, não o banco.**

Agora o `CREATE TABLE` sai de `tabelas.DDL_CONFIRMADO`, que é transcrição do DDL
real (`banco_de_dados/schema-real-*.sql`). Pedir uma coluna que não existe lá
levanta `KeyError` na hora de montar o `fixture` — não passa mais em silêncio.

As **linhas** continuam parametrizáveis, porque cada suíte tem as suas,
referenciadas por EOT dentro dos testes. O **schema** é que não pode divergir.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Sequence

from comum.dados import tabelas as tbl

# Reaproveita a tradução MySQL -> SQLite do espelho, em vez de manter uma
# segunda. É a mesma função que gera o espelho do banco real, e já é coberta por
# `tests/test_espelho_do_banco.py`.
from espelhar_banco import _tipo_sqlite

#: `(EOT, Nome Fantasia, Regiao, Tipo de Servico, Concessao, Endereco)`
OPERADORAS_PADRAO: tuple[tuple, ...] = (
    ("011", "VIVO", "I", "STFC", "S", "Av. Berrini, 1376 - São Paulo - SP"),
    ("012", "VIVO", "I", "SMP", "S", "Av. Berrini, 1376 - São Paulo - SP"),
    ("021", "CLARO", "II", "SMP", "N", "Rua Verbo Divino, 1356 - SP"),
    ("031", "ALGAR", "II", "STFC", "N", "Rua João Naves, 100 - MG"),
)

#: `(id, regiao, gh, regra_desc, tipo_remuneracao, tarifa, data_inicio, data_fim)`
#:
#: `regra_desc` guarda a classificação do descritor no formato que
#: `classificar_regra_inicio_fim_desc` produz — inclusive as aspas
#: desbalanceadas, que vêm assim do banco real.
#:
#: ⚠️ A tarifa vai com **ponto** decimal porque
#: `repositorio_tabelas.validar_tarifas_na_tabela` faz `.astype(float)` direto na
#: coluna e estoura com vírgula. Note a inconsistência: a comparação logo abaixo,
#: no mesmo fluxo, faz `replace(",", ".")` — uma metade assume ponto e a outra
#: tolera vírgula. Coberto por `test_tarifa_com_virgula_no_banco_quebra`.
TARIFAS_PADRAO: tuple[tuple, ...] = (
    (1, "I", None, 'DESC final V""', "VU-M", "0.03000", "2025-01-01", "2025-12-31"),
    (2, "II", None, 'DESC final L""', "TU-RL", "0.01500", "2025-01-01", "2025-12-31"),
    (3, "II", None, 'DESC final V""', "VU-M", "0.03000", "2025-01-01", "2025-12-31"),
)

#: `(id, final_descritor, remuneracao_fixa, observacao, produto)`
#:
#: 🐛 A coluna `produto` já recebeu a própria remuneração ("VU-M", "TU-RL"…) em
#: vez de "DETRAF". `construir_indice_remuneracao` filtra por
#: `produto == "DETRAF"` (regra de desambiguação D-5), então o índice saía VAZIO
#: e toda remuneração virava None. Passou despercebido porque, até 2026-08-06,
#: nada no RPA 2 lia esta tabela.
DESCRITORES_PADRAO: tuple[tuple, ...] = (
    (1, "V", "VU-M", "ITX", "DETRAF"),
    (2, "L", "TU-RL", "ITX", "DETRAF"),
    (3, "I", "TU-RIU", "ITX", "DETRAF"),
    (4, "C", "TU-COM", "ITX", "DETRAF"),
)


# ---------------------------------------------------------------------------
# Subconjuntos de coluna que cada tabela de teste cria
#
# Os `fixtures` não precisam das 18 colunas do Anexo 5 — precisam das que o
# código lê. O que importa é que os NOMES venham de `DDL_CONFIRMADO`: pedir um
# que não exista lá levanta `KeyError` ao montar o banco de teste.
#
# A ordem é a das tuplas de seed acima, que são posicionais.
# ---------------------------------------------------------------------------
COLUNAS_ANEXO5: tuple[str, ...] = (
    tbl.COL_ANEXO5_EOT,
    tbl.COL_ANEXO5_NOME_FANTASIA,
    tbl.COL_ANEXO5_REGIAO,
    tbl.COL_ANEXO5_TIPO_SERVICO,
    tbl.COL_ANEXO5_CONCESSAO,
    tbl.COL_ANEXO5_ENDERECO_CORRESP,
)

COLUNAS_TARIFAS: tuple[str, ...] = (
    "id",
    "regiao",
    "gh",
    "regra_desc",
    "tipo_remuneracao",
    "tarifa",
    "data_inicio",
    "data_fim",
)

COLUNAS_DESCRITORES: tuple[str, ...] = (
    "id",
    "final_descritor",
    "remuneracao_fixa",
    "observacao",
    "produto",
)


def ddl_sqlite(nome_tabela: str, colunas: Sequence[str] | None = None) -> str:
    """
    Monta o ``CREATE TABLE`` de uma tabela a partir de :data:`DDL_CONFIRMADO`.

    Args:
        nome_tabela: Uma das tabelas de ``tabelas.TODAS``.
        colunas: Subconjunto a criar, **na ordem desejada**. ``None`` cria todas,
            na ordem do banco.

    Returns:
        O ``CREATE TABLE`` pronto, com todo nome entre aspas duplas — os do
        Anexo 5 têm espaço (``Nome Fantasia``), e sem as aspas viram erro de
        sintaxe.

    Raises:
        KeyError: Se a tabela não tiver DDL confirmado, ou se alguma coluna
            pedida não existir nela. **É esta exceção que impede um `fixture` de
            declarar coluna que o banco real não tem** — o defeito que passou
            despercebido até 2026-08-06.
    """

    if nome_tabela not in tbl.DDL_CONFIRMADO:
        raise KeyError(
            f"{nome_tabela}: sem DDL confirmado. Rode `python espelhar_banco.py "
            f"--somente-schema` e transcreva para `tabelas.DDL_CONFIRMADO`."
        )

    confirmado = tbl.DDL_CONFIRMADO[nome_tabela]
    nomes = tuple(colunas) if colunas is not None else tuple(confirmado)

    desconhecidas = [nome for nome in nomes if nome not in confirmado]
    if desconhecidas:
        raise KeyError(
            f"{nome_tabela}: coluna(s) {', '.join(desconhecidas)} não existem no "
            f"banco real. Colunas confirmadas: {', '.join(confirmado)}."
        )

    definicoes = []
    for nome in nomes:
        tipo_mysql = confirmado[nome]
        # `int AI PK` é como `DDL_CONFIRMADO` marca a chave primária
        # auto-incremento. No SQLite ela precisa ser exatamente
        # `INTEGER PRIMARY KEY AUTOINCREMENT` para o INSERT poder omitir o id.
        if "AI PK" in tipo_mysql:
            definicoes.append(f'"{nome}" INTEGER PRIMARY KEY AUTOINCREMENT')
            continue

        tipo, _ = _tipo_sqlite(tipo_mysql)
        sufixo = " NOT NULL" if "NOT NULL" in tipo_mysql.upper() else ""
        definicoes.append(f'"{nome}" {tipo}{sufixo}')

    return f'CREATE TABLE "{nome_tabela}" ({", ".join(definicoes)})'


def _inserir(cursor, nome_tabela: str, colunas: Sequence[str], linhas) -> None:
    """``INSERT`` nomeando as colunas — não por posição da tabela."""
    if not linhas:
        return

    nomes = ", ".join(f'"{coluna}"' for coluna in colunas)
    marcadores = ", ".join("?" * len(colunas))
    cursor.executemany(
        f'INSERT INTO "{nome_tabela}" ({nomes}) VALUES ({marcadores})',
        [tuple(linha) for linha in linhas],
    )


def criar_banco_de_teste(
    caminho: Path | str,
    operadoras: Sequence[Sequence] = OPERADORAS_PADRAO,
    tarifas: Sequence[Sequence] = TARIFAS_PADRAO,
    descritores: Sequence[Sequence] = DESCRITORES_PADRAO,
    contestacao: Sequence[Sequence] = (),
) -> None:
    """
    Cria o SQLite com as **cinco** tabelas que os robôs consultam.

    Args:
        caminho: Arquivo SQLite a criar.
        operadoras: Seeds do Anexo 5, na ordem de :data:`COLUNAS_ANEXO5`.
        tarifas: Seeds das tarifas, na ordem de :data:`COLUNAS_TARIFAS`.
        descritores: Seeds do mapeamento, na ordem de :data:`COLUNAS_DESCRITORES`.
        contestacao: Seeds da tabela de contestação, na ordem das colunas de
            ``DDL_CONFIRMADO[LOG_DESPESA_CONTESTACAO]``. Vazio cria a tabela sem
            linhas — que é o que as suítes base, do RPA 1 e do RPA 2 querem.

    ⚠️ **A tabela de contestação não tem `vb_contestacao`**, e é de propósito: o
    banco real não a tem (pendência Q24). Criá-la aqui faria a suíte exercitar um
    schema que não existe, e o caminho degradado de
    ``RepositorioTabelas._atualizar_contestacao_em_lote`` — que é o que roda em
    produção hoje — nunca seria testado.
    """
    conexao = sqlite3.connect(str(caminho))
    try:
        cursor = conexao.cursor()

        cursor.execute(ddl_sqlite(tbl.ANEXO5, COLUNAS_ANEXO5))
        _inserir(cursor, tbl.ANEXO5, COLUNAS_ANEXO5, operadoras)

        cursor.execute(ddl_sqlite(tbl.TARIFAS, COLUNAS_TARIFAS))
        _inserir(cursor, tbl.TARIFAS, COLUNAS_TARIFAS, tarifas)

        cursor.execute(ddl_sqlite(tbl.MAPEAMENTO_DESCRITORES, COLUNAS_DESCRITORES))
        _inserir(
            cursor, tbl.MAPEAMENTO_DESCRITORES, COLUNAS_DESCRITORES, descritores
        )

        # Estas duas vão com TODAS as colunas do banco: são as que os robôs
        # escrevem, e uma coluna a menos no teste esconderia uma escrita quebrada.
        cursor.execute(ddl_sqlite(tbl.LOG_DESPESA_ARQUIVOS))

        colunas_contestacao = tuple(tbl.DDL_CONFIRMADO[tbl.LOG_DESPESA_CONTESTACAO])
        cursor.execute(ddl_sqlite(tbl.LOG_DESPESA_CONTESTACAO))
        _inserir(
            cursor,
            tbl.LOG_DESPESA_CONTESTACAO,
            colunas_contestacao,
            contestacao,
        )

        conexao.commit()
    finally:
        conexao.close()
