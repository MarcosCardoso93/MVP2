"""Copia o banco WebFat real para um SQLite local — schema, tipos e conteúdo.

Escrito em 2026-08-06, para a homologação manual.

## Para que serve

A homologação precisa exercitar o fluxo **inteiro**, inclusive as escritas
(`carga_agi`, `tipo_contestacao`, a despesa da contestação). Fazer isso contra o
WebFat de produção não é opção, e o `preparar_banco_dev.py` copia dos SQLite que
vieram em ``projetos-origem/`` — que são de 2025 e **não são o banco real**.

Este utilitário fecha a lacuna: lê o MySQL de verdade e produz um SQLite com o
mesmo schema e o mesmo conteúdo, contra o qual se pode escrever à vontade.

## E serve a uma segunda coisa, talvez mais importante

O DDL das tabelas **nunca foi publicado** — é a pendência Q22, a de maior
alavancagem da lista. Toda execução deste script grava
``banco_de_dados/schema-real-AAAAMMDD.sql`` com o ``SHOW CREATE TABLE`` de cada
tabela. **Esse arquivo é a resposta da Q22**, e vale guardar mesmo quando o
espelho não for usado.

E confere o schema real contra o que o código presume
(``comum.dados.tabelas.COLUNAS_ESPERADAS``), acusando **por nome** cada coluna
faltando.

Foi essa conferência que, na primeira execução contra o banco real (2026-08-06),
derrubou três suposições de uma vez: as colunas do Anexo 5 não têm acento, a
coluna da remuneração na contestação é ``remuneracoes`` (plural), e
``vb_contestacao`` não existe. As duas primeiras foram corrigidas no código; a
terceira aparece em destaque como **pendente no DBA**
(``COLUNAS_PENDENTES_NO_BANCO``) — o robô grava as demais colunas e avisa.

## Segurança

**Nunca escreve no MySQL.** Só ``SELECT`` e ``SHOW CREATE TABLE``. A conexão é
aberta com o usuário do `.env`; se ele tiver permissão de escrita, nada aqui a
usa.

Uso::

    python espelhar_banco.py                          # tudo, para o espelho padrão
    python espelhar_banco.py --somente-schema         # só o DDL, sem copiar linha
    python espelhar_banco.py --limite 500             # amostra por tabela
    python espelhar_banco.py --tabelas tbl_detraf_tarifas
    python espelhar_banco.py --destino ./teste.db
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from comum.dados.schema_mysql import TIPOS as _TIPOS
from comum.dados.schema_mysql import TRADUCAO_IMPRECISA as _TRADUCAO_IMPRECISA
from comum.dados.schema_mysql import criar_tabela_sqlite as _criar_tabela_sqlite
from comum.dados.schema_mysql import tipo_sqlite as _tipo_sqlite

#: Nome padrão do espelho. Deliberadamente **diferente** do banco de dev
#: (`TABELAS_DETRAF.db`): sobrescrever aquele apagaria os dados de origem sem
#: aviso, e os dois têm propósitos distintos.
DESTINO_PADRAO = RAIZ / "banco_de_dados" / "TABELAS_DETRAF_espelho.db"

# A tradução MySQL -> SQLite mora em `comum.dados.schema_mysql` desde 2026-08-10:
# o `preparar_banco_dev.py --do-schema-real` monta o mesmo espelho a partir do
# `schema-real-*.sql`, sem MySQL, e precisa das mesmas regras. Os nomes privados
# seguem apontando para lá porque são o que a suíte exercita.


def _conectar_mysql(engine_url_visivel: bool = False):
    """
    Abre a conexão com o MySQL a partir do `.env`, **ignorando o `ENV`**.

    O `ENV` decide para onde os robôs escrevem; aqui a intenção é sempre ler o
    banco real, e fazer o script obedecer ao `ENV` significaria que rodá-lo com
    `ENV=dev` copiaria o SQLite sobre ele mesmo, em silêncio.
    """
    from sqlalchemy import create_engine

    from comum.config import configuration as cfg

    faltando = [
        nome
        for nome, valor in (
            ("HOST_BD_RPA", cfg.HOST_BD_RPA),
            ("PORT_BD_RPA", cfg.PORT_BD_RPA),
            ("DATABASE_RPA", cfg.DATABASE_RPA),
            ("USUARIO_BD", cfg.USUARIO_BD),
            ("SENHA_BD", cfg.SENHA_BD),
        )
        if not valor
    ]
    if faltando:
        raise SystemExit(
            "ERRO: faltam credenciais do banco no .env: "
            + ", ".join(faltando)
            + "\n\nEste utilitário lê o MySQL real — não há como espelhar sem elas."
        )

    url = (
        f"mysql+pymysql://{cfg.USUARIO_BD}:{cfg.SENHA_BD}"
        f"@{cfg.HOST_BD_RPA}:{cfg.PORT_BD_RPA}/{cfg.DATABASE_RPA}"
    )
    if engine_url_visivel:
        # Sem a senha. O host e a base ajudam a confirmar que se está lendo o
        # banco certo; a senha não ajuda em nada e vaza para o terminal.
        print(
            f"Conectando em mysql://{cfg.USUARIO_BD}@{cfg.HOST_BD_RPA}:"
            f"{cfg.PORT_BD_RPA}/{cfg.DATABASE_RPA}"
        )

    return create_engine(url, pool_pre_ping=True)


def _ler_ddl(conexao, tabela: str) -> str | None:
    """``SHOW CREATE TABLE`` — o texto que responde a Q22."""
    from sqlalchemy import text

    try:
        linha = conexao.execute(text(f"SHOW CREATE TABLE `{tabela}`")).fetchone()
    except Exception as erro:
        print(f"  ! não foi possível ler o DDL de {tabela}: {erro}")
        return None
    return linha[1] if linha else None


def _ler_colunas(conexao, tabela: str) -> list[tuple[str, str, bool, bool]]:
    """
    ``(nome, tipo, aceita_nulo, auto_incremento)`` de cada coluna.

    O ``SHOW COLUMNS`` devolve ``Field, Type, Null, Key, Default, Extra``, e o
    ``auto_increment`` vive no ``Extra``. Sem ele o espelho recria o `id` como
    coluna comum ``NOT NULL``, e toda escrita falha — ver
    `schema_mysql.criar_tabela_sqlite`.
    """
    from sqlalchemy import text

    resultado = conexao.execute(text(f"SHOW COLUMNS FROM `{tabela}`"))
    return [
        (
            linha[0],
            linha[1],
            str(linha[2]).upper() == "YES",
            "AUTO_INCREMENT" in str(linha[5]).upper() if len(linha) > 5 else False,
        )
        for linha in resultado
    ]


def _copiar_conteudo(engine, destino: sqlite3.Connection, tabela: str, limite: int | None) -> int:
    """Copia as linhas em blocos. Devolve quantas foram."""
    import pandas as pd

    sql = f"SELECT * FROM `{tabela}`" + (f" LIMIT {int(limite)}" if limite else "")
    total = 0

    # Em blocos porque `tbl_rpa_log_detraf_despesa_contestacao` cresce a cada
    # mês, e carregar a tabela inteira em memória só para copiá-la é gasto sem
    # motivo — o `to_sql` já grava por bloco.
    for bloco in pd.read_sql(sql, con=engine, chunksize=5_000):
        bloco.to_sql(tabela, destino, if_exists="append", index=False)
        total += len(bloco)

    return total


def main(argv: list[str] | None = None) -> int:
    from comum.dados import tabelas as tbl

    parser = argparse.ArgumentParser(
        prog="espelhar_banco.py",
        description=(
            "Copia o banco WebFat real para um SQLite local (schema, tipos e "
            "conteúdo) e grava o DDL real em arquivo. Nunca escreve no MySQL."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "O arquivo schema-real-*.sql gerado é a resposta da pendência Q22 "
            "(DDL das tabelas) — guarde-o mesmo que não use o espelho."
        ),
    )
    parser.add_argument(
        "--destino",
        type=Path,
        default=DESTINO_PADRAO,
        help=f"Arquivo SQLite a gerar. Padrão: {DESTINO_PADRAO.name}",
    )
    parser.add_argument(
        "--tabelas",
        help=(
            "Somente estas tabelas, separadas por vírgula. Padrão: as cinco que "
            "o código usa."
        ),
    )
    parser.add_argument(
        "--limite",
        type=int,
        help=(
            "Copia no máximo N linhas por tabela. Use para uma amostra rápida; "
            "sem isto, copia tudo."
        ),
    )
    parser.add_argument(
        "--somente-schema",
        action="store_true",
        help="Cria as tabelas vazias e grava o DDL, sem copiar linha nenhuma.",
    )
    args = parser.parse_args(argv)

    tabelas = (
        [nome.strip() for nome in args.tabelas.split(",") if nome.strip()]
        if args.tabelas
        else sorted(tbl.TODAS)
    )

    engine = _conectar_mysql(engine_url_visivel=True)

    args.destino.parent.mkdir(parents=True, exist_ok=True)
    if args.destino.exists():
        print(f"Sobrescrevendo o espelho anterior: {args.destino}")
    destino = sqlite3.connect(args.destino)

    ddl_completo: list[str] = []
    avisos_traducao: list[str] = []
    colunas_faltando: dict[str, list[str]] = {}
    ausentes: list[str] = []

    try:
        with engine.connect() as conexao:
            for tabela in tabelas:
                print(f"\n{tabela}")

                try:
                    colunas = _ler_colunas(conexao, tabela)
                except Exception as erro:
                    print(f"  ! tabela não encontrada ou inacessível: {erro}")
                    ausentes.append(tabela)
                    continue

                print(f"  {len(colunas)} coluna(s)")

                ddl = _ler_ddl(conexao, tabela)
                if ddl:
                    ddl_completo.append(f"-- {tabela}\n{ddl};\n")

                faltando = tbl.conferir_colunas(tabela, [coluna[0] for coluna in colunas])
                if faltando:
                    colunas_faltando[tabela] = faltando

                avisos_traducao += _criar_tabela_sqlite(destino, tabela, colunas)

                if args.somente_schema:
                    print("  conteúdo não copiado (--somente-schema)")
                    continue

                linhas = _copiar_conteudo(engine, destino, tabela, args.limite)
                print(f"  {linhas} linha(s) copiada(s)")

        destino.commit()
    finally:
        destino.close()
        engine.dispose()

    # --- O DDL, que é o entregável da Q22 -------------------------------
    if ddl_completo:
        carimbo = datetime.now().strftime("%Y%m%d")
        caminho_ddl = args.destino.parent / f"schema-real-{carimbo}.sql"
        caminho_ddl.write_text(
            "-- DDL real do banco WebFat, lido por espelhar_banco.py\n"
            f"-- Gerado em {datetime.now():%Y-%m-%d %H:%M}\n"
            "-- Responde à pendência Q22 (o DDL nunca foi publicado pela V2).\n\n"
            + "\n".join(ddl_completo),
            encoding="utf-8",
        )
        print(f"\nDDL real gravado em: {caminho_ddl}")

    # --- O que precisa de atenção ---------------------------------------
    print("\n" + "=" * 70)

    if avisos_traducao:
        print("\nTraduções de tipo que perdem informação:")
        for aviso in avisos_traducao:
            print(f"  - {aviso}")
        print(
            "\n  Isto vale para o ESPELHO, não para o banco real. Se a "
            "homologação\n  comparar centavos, confira contra o MySQL antes de "
            "abrir defeito."
        )

    if ausentes:
        print(f"\n🔴 TABELAS NÃO ENCONTRADAS NO BANCO REAL: {', '.join(ausentes)}")
        print("  O código as usa. Confirme os nomes com o DBA (pendências Q22/N1).")

    # Uma ausência prevista (`vb_contestacao`) não é a mesma coisa que uma
    # inesperada: a primeira já é tratada em código e tem ALTER pedido ao DBA; a
    # segunda é regressão, e é o que este relatório existe para pegar.
    inesperadas: dict[str, list[str]] = {}
    for tabela, faltando in colunas_faltando.items():
        pendentes = set(tbl.COLUNAS_PENDENTES_NO_BANCO.get(tabela, ()))
        novas = [coluna for coluna in faltando if coluna not in pendentes]
        if novas:
            inesperadas[tabela] = novas

    if colunas_faltando:
        print("\n🔴 COLUNAS QUE O CÓDIGO USA E O BANCO REAL NÃO TEM:")
        for tabela, faltando in colunas_faltando.items():
            pendentes = set(tbl.COLUNAS_PENDENTES_NO_BANCO.get(tabela, ()))
            for coluna in faltando:
                marca = (
                    "  (pendente no DBA — tratada: o robô grava as demais e avisa)"
                    if coluna in pendentes
                    else "  ⚠️ NÃO PREVISTA"
                )
                print(f"  - {tabela}.{coluna}{marca}")
        if inesperadas:
            print(
                "\n  As marcadas NÃO PREVISTAS são divergência nova entre o código\n"
                "  e o banco. Compare com `tabelas.DDL_CONFIRMADO`."
            )
        else:
            print(
                "\n  Todas as ausências são conhecidas e tratadas.\n"
                "  Ver docs/04-relatorios/pendencias-para-o-cliente.md (Q24)."
            )

    if not (ausentes or colunas_faltando):
        print("\n✅ O schema real tem tudo o que o código usa.")

    print(f"\nEspelho: {args.destino}")
    print("Para usá-lo, aponte no .env:")
    print(f"    ENV=dev")
    print(f"    CAMINHO_SQLITE={args.destino}")
    print("Ou só para um robô, com o sufixo — por exemplo, CAMINHO_SQLITE_RPA3=...")

    # Uma pendência conhecida e tratada não é motivo de saída diferente de zero:
    # ela seria permanente até o DBA agir, e um código de erro que nunca zera
    # deixa de significar alguma coisa. Sai 1 só no que é regressão.
    return 1 if (ausentes or inesperadas) else 0


if __name__ == "__main__":
    raise SystemExit(main())
