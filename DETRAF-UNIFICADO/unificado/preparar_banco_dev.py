"""Prepara o SQLite de desenvolvimento a partir dos bancos dos projetos de origem.

Os projetos vieram com um SQLite de homologação cada um, mas nenhum deles tem a
tabela de log com o nome que a V2 documenta — e que foi adotado
(``tbl_rpa_log_detraf_despesa_arquivos``, decisão de 2026-07-31). Este script
gera o banco de dev com o nome certo.

``projetos-origem/`` é somente leitura: o banco é **copiado** para
``unificado/banco_de_dados/`` e renomeado lá.

## O modo ``--do-schema-real`` (2026-08-10)

O modo padrão adapta o banco de 2025 coluna a coluna, e cada adaptação é uma
suposição sobre como o banco real é. Desde 2026-08-06 não é preciso supor: o
``espelhar_banco.py`` gravou o DDL de verdade em
``banco_de_dados/schema-real-AAAAMMDD.sql``.

Com ``--do-schema-real``, o espelho nasce **desse arquivo** — estrutura idêntica
à do MySQL, sem precisar alcançar o MySQL — e é carregado com os dados que
existem localmente, traduzindo os nomes divergentes (Anexo 5 acentuado,
``remuneracao`` no singular).

⚠️ **Estrutura real, dados de 2025.** Serve para exercitar o fluxo inteiro sem
VPN. Número de homologação continua exigindo ``espelhar_banco.py`` contra o
MySQL.

Uso:
    .venv\\Scripts\\python preparar_banco_dev.py
    .venv\\Scripts\\python preparar_banco_dev.py --do-schema-real
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# O console do Windows abre em cp1252, e um `print` com acento ou emoji levanta
# `UnicodeEncodeError` DEPOIS de o banco já ter sido gravado — o script parece
# ter falhado quando na verdade terminou. Trocar o encoding é mais barato do que
# policiar cada mensagem.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from comum.dados import schema_mysql
from comum.dados import tabelas as tbl
from tests_apoio.banco import ddl_sqlite

#: Banco de origem. O do Projeto 2 é o mais completo — tem as quatro tabelas de
#: consulta e a de log.
ORIGEM = (
    RAIZ.parent
    / "projetos-origem"
    / "projeto-2-epico-2-validacao"
    / "banco de dados"
    / "TABELAS_DETRAF.db"
)

DESTINO = RAIZ / "banco_de_dados" / "TABELAS_DETRAF.db"

#: Destino do ``--do-schema-real``. É o mesmo nome que o ``espelhar_banco.py``
#: usa, e o mesmo que o `.env` já aponta — os dois produzem a mesma coisa, um
#: lendo o MySQL e outro lendo o DDL que aquele gravou.
ESPELHO = RAIZ / "banco_de_dados" / "TABELAS_DETRAF_espelho.db"

#: Saída dos robôs, não insumo. Nascem vazias no espelho: aproveitar as linhas
#: de uma rodada anterior faria a conferência do teste seguinte contar registro
#: que ele não produziu.
TABELAS_DE_SAIDA = (tbl.LOG_DESPESA_ARQUIVOS, tbl.LOG_DESPESA_CONTESTACAO)

#: Renomeações a aplicar: nome no banco de origem -> nome adotado.
RENOMEAR = {
    "tbl_detraf_despesa_arquivos": "tbl_rpa_log_detraf_despesa_arquivos",
}

#: Tabelas que o código escreve mas que podem não existir no banco de origem.
#: Criadas vazias, com o schema **do banco real** — derivado de
#: `tabelas.DDL_CONFIRMADO` por `tests_apoio.banco.ddl_sqlite`, a mesma função
#: que monta os `fixtures` de teste.
#:
#: Escrever o `CREATE TABLE` aqui à mão foi o que fez este arquivo virar a
#: quarta declaração independente do schema — e ele declarava `remuneracao`
#: (singular) e `vb_contestacao`, nenhuma das duas existente no MySQL.
CRIAR_SE_FALTAR = (tbl.LOG_DESPESA_CONTESTACAO,)


#: Colunas que os bancos de origem, de 2025, não têm. Só valem para uma tabela
#: que **já existe** — as criadas por `CRIAR_SE_FALTAR` já nascem com elas.
#:
#: O `CRIAR_SE_FALTAR` só age quando a tabela **falta**; se ela veio no banco de
#: origem, ficava sem as colunas novas e a escrita da HU-19 falhava — descoberto
#: em 2026-08-06, ao conferir o banco de dev contra `COLUNAS_ESPERADAS`.
#:
#: ⚠️ `vb_contestacao` **não entra aqui**, embora o código a grave. O banco real
#: não a tem (Q24), e um banco de dev que a tivesse esconderia o caminho
#: degradado de `RepositorioTabelas._atualizar_contestacao_em_lote` — que é o que
#: roda em produção hoje. O banco de dev modela o real, inclusive no que falta.
ACRESCENTAR_SE_FALTAR = {
    tbl.LOG_DESPESA_CONTESTACAO: {
        # Decisão de 2026-07-28. ⚠️ Chamava-se `remuneracao` aqui até 2026-08-06,
        # e com isso o banco de dev ganhava uma coluna que o MySQL não tem,
        # enquanto lhe faltava a que ele tem. Ver `obter_tipo_contestacao`.
        tbl.COL_CONTESTACAO_REMUNERACOES: "TEXT",
    },
}


#: Adaptação do `tbl_anexo5_processado` de 2025 aos nomes do banco real.
#:
#: 🔴 Os SQLite de origem são a **fonte dos literais acentuados** que quebravam
#: os três RPAs contra o MySQL — foi de lá que `Região` e companhia vieram para o
#: código. Sem esta renomeação, o banco de dev continuaria acentuado e o código
#: corrigido não conseguiria lê-lo: a correção do defeito quebraria o ambiente de
#: desenvolvimento.
#:
#: ⚠️ Não foi possível verificar contra `projetos-origem/` (a pasta é ignorada e
#: não está em todo checkout). O mapa cobre as duas grafias possíveis; renomear é
#: no-op quando a coluna antiga não existe.
_RENOMEAR_ANEXO5 = {
    "Região": tbl.COL_ANEXO5_REGIAO,
    "Tipo de Serviço": tbl.COL_ANEXO5_TIPO_SERVICO,
    "Concessão": tbl.COL_ANEXO5_CONCESSAO,
    "Endereço de Correspondência": tbl.COL_ANEXO5_ENDERECO_CORRESP,
    "Razão Social": "Razao Social",
    "Área de Prestação": "Area de Prestacao",
    "Inscrição Estadual": "Inscricao Estadual",
    "Endereço de Emissão Nota Fiscal": "Endereco de Emissao Nota Fiscal",
}


#: Adaptação do `tbl_detraf_mapeamento_descritores` de 2025 ao formato presumido.
#:
#: 🔴 **Divergência achada em 2026-08-06.** O SQLite do Projeto 2 tem a tabela com
#: **três** colunas — ``FINAL_DO_DESCRITOR``, ``REMUNERACAO_FIXA``, ``DS_OBS`` —,
#: enquanto `mapa_remuneracao.carregar_mapa_descritores` exige cinco em caixa
#: baixa (``id``, ``final_descritor``, ``remuneracao_fixa``, ``observacao``,
#: ``produto``) e levanta `ValueError` sem elas.
#:
#: Como esse mapa é **pré-condição de todo o RPA 3** ("aborta antes do laço
#: começar"), o robô não daria um passo contra este banco.
#:
#: ⚠️ **Isto adapta o banco de DEV, e não decide nada sobre produção.** Qual das
#: duas formas o MySQL real tem é parte da pendência Q22 — e o
#: `espelhar_banco.py` responde a isso lendo o schema de verdade.
_RENOMEAR_DESCRITORES = {
    "FINAL_DO_DESCRITOR": "final_descritor",
    "REMUNERACAO_FIXA": "remuneracao_fixa",
    "DS_OBS": "observacao",
}


def _adaptar_mapeamento_descritores(conexao: sqlite3.Connection) -> None:
    """Põe o mapa de descritores de 2025 no formato que o código espera."""

    tabela = "tbl_detraf_mapeamento_descritores"
    presentes = [linha[1] for linha in conexao.execute(f'PRAGMA table_info("{tabela}")')]
    if not presentes:
        return

    for antigo, novo in _RENOMEAR_DESCRITORES.items():
        if antigo in presentes and novo not in presentes:
            conexao.execute(f'ALTER TABLE "{tabela}" RENAME COLUMN "{antigo}" TO "{novo}"')
            print(f"  coluna renomeada: {tabela}.{antigo} -> {novo}")

    presentes = [linha[1] for linha in conexao.execute(f'PRAGMA table_info("{tabela}")')]

    if "produto" not in presentes:
        # O código filtra `produto == "DETRAF"`. A tabela de 2025 é inteira do
        # Detraf — não havia outro produto —, então preencher com o literal
        # preserva o comportamento em vez de zerar o mapa.
        conexao.execute(f'ALTER TABLE "{tabela}" ADD COLUMN "produto" TEXT')
        conexao.execute(f'UPDATE "{tabela}" SET "produto" = \'DETRAF\'')
        print(f"  coluna acrescentada: {tabela}.produto (= 'DETRAF')")

    if "id" not in presentes:
        # Só a presença importa: o `id` é lido junto com as demais e nunca
        # usado como chave neste mapa.
        conexao.execute(f'ALTER TABLE "{tabela}" ADD COLUMN "id" INTEGER')
        conexao.execute(f'UPDATE "{tabela}" SET "id" = rowid')
        print(f"  coluna acrescentada: {tabela}.id (= rowid)")


def _adaptar_anexo5(conexao: sqlite3.Connection) -> None:
    """Tira os acentos dos nomes de coluna do Anexo 5, como no banco real."""

    tabela = tbl.ANEXO5
    presentes = [linha[1] for linha in conexao.execute(f'PRAGMA table_info("{tabela}")')]
    if not presentes:
        return

    for antigo, novo in _RENOMEAR_ANEXO5.items():
        if antigo in presentes and novo not in presentes:
            conexao.execute(
                f'ALTER TABLE "{tabela}" RENAME COLUMN "{antigo}" TO "{novo}"'
            )
            print(f"  coluna renomeada: {tabela}.{antigo} -> {novo}")


def _acrescentar_colunas_da_unificacao(conexao: sqlite3.Connection) -> None:
    """Aplica `ACRESCENTAR_SE_FALTAR` nas tabelas que já vieram do banco de origem."""

    for tabela, colunas in ACRESCENTAR_SE_FALTAR.items():
        try:
            presentes = {
                linha[1] for linha in conexao.execute(f'PRAGMA table_info("{tabela}")')
            }
        except sqlite3.Error as erro:
            print(f"  AVISO: não foi possível ler [{tabela}]: {erro}")
            continue

        if not presentes:
            continue  # tabela não existe; o CRIAR_SE_FALTAR cuidou dela

        for coluna, tipo in colunas.items():
            if coluna in presentes:
                continue
            conexao.execute(f'ALTER TABLE "{tabela}" ADD COLUMN "{coluna}" {tipo}')
            print(f"  coluna acrescentada: {tabela}.{coluna} ({tipo})")


def _renomeacao_de(tabela_real: str) -> dict[str, str]:
    """Coluna como está no banco local -> coluna como está no banco real."""
    if tabela_real == tbl.ANEXO5:
        return dict(_RENOMEAR_ANEXO5)
    if tabela_real == tbl.MAPEAMENTO_DESCRITORES:
        return dict(_RENOMEAR_DESCRITORES)
    if tabela_real == tbl.LOG_DESPESA_CONTESTACAO:
        # A descoberta de 2026-08-06: é o mesmo campo com outro nome. Ver
        # `tbl.COL_CONTESTACAO_REMUNERACOES`.
        return {"remuneracao": tbl.COL_CONTESTACAO_REMUNERACOES}
    return {}


def _tabela_local(tabela_real: str, existentes: set[str]) -> str | None:
    """Como a tabela se chama no banco local — pode ser o nome antigo."""
    if tabela_real in existentes:
        return tabela_real
    for antigo, novo in RENOMEAR.items():
        if novo == tabela_real and antigo in existentes:
            return antigo
    return None


def _preencher_obrigatoria(tipo_sqlite: str):
    """
    Valor para uma coluna ``NOT NULL`` que o banco local não tem.

    Manter o ``NOT NULL`` do banco real e inventar um valor neutro é melhor do
    que relaxar a restrição no espelho: assim o espelho recusa o que o MySQL
    recusaria, e a coluna inventada aparece no relatório do fim.
    """
    return 0 if tipo_sqlite in ("INTEGER", "REAL") else ""


def _carregar_do_banco_local(
    origem: sqlite3.Connection,
    destino: sqlite3.Connection,
    tabela_real: str,
    colunas_reais: list[tuple[str, str, bool, bool]],
) -> tuple[int, list[str]]:
    """
    Copia uma tabela do banco local para o espelho, traduzindo os nomes.

    Returns:
        ``(linhas_copiadas, colunas_que_ficaram_sem_dado)``.
    """
    existentes = {
        linha[0]
        for linha in origem.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    fonte = _tabela_local(tabela_real, existentes)
    if fonte is None:
        return 0, [nome for nome, _, _ in colunas_reais]

    presentes = [linha[1] for linha in origem.execute(f'PRAGMA table_info("{fonte}")')]
    renomear = _renomeacao_de(tabela_real)

    # Nome real -> nome local. O `get` cobre a coluna que já vem com o nome
    # certo; o mapa cobre a que veio acentuada ou no singular.
    onde_esta = {renomear.get(coluna, coluna): coluna for coluna in presentes}

    alvos, valores_fixos, sem_dado = [], {}, []
    for coluna in colunas_reais:
        nome, tipo_mysql, aceita_nulo = coluna[0], coluna[1], coluna[2]
        auto_incremento = coluna[3] if len(coluna) > 3 else False

        if nome in onde_esta:
            alvos.append(nome)
            continue

        sem_dado.append(nome)

        # A coluna `AUTO_INCREMENT` ausente fica de fora: o SQLite a preenche
        # sozinha. Inventar valor aqui daria o mesmo `id` a todas as linhas e
        # esbarraria na chave primária.
        if not aceita_nulo and not auto_incremento:
            alvos.append(nome)
            valores_fixos[nome] = _preencher_obrigatoria(schema_mysql.tipo_sqlite(tipo_mysql)[0])

    lidas = [nome for nome in alvos if nome not in valores_fixos]
    if not lidas:
        return 0, sem_dado

    selecao = ", ".join(f'"{onde_esta[nome]}"' for nome in lidas)
    linhas = origem.execute(f'SELECT {selecao} FROM "{fonte}"').fetchall()
    if not linhas:
        return 0, sem_dado

    montadas = [
        tuple(
            valores_fixos[nome] if nome in valores_fixos else linha[lidas.index(nome)]
            for nome in alvos
        )
        for linha in linhas
    ]
    colunas_sql = ", ".join(f'"{nome}"' for nome in alvos)
    marcadores = ", ".join("?" * len(alvos))
    destino.executemany(
        f'INSERT INTO "{tabela_real}" ({colunas_sql}) VALUES ({marcadores})', montadas
    )
    return len(montadas), sem_dado


def montar_do_schema_real(destino_arquivo: Path, dados: Path) -> int:
    """Cria o espelho com o schema do `schema-real-*.sql` e os dados locais."""
    ddl = schema_mysql.ddl_mais_recente(RAIZ / "banco_de_dados")
    if ddl is None:
        print("ERRO: não há banco_de_dados/schema-real-*.sql.")
        print("Rode `python espelhar_banco.py --somente-schema` com acesso ao MySQL.")
        return 1

    if not dados.is_file():
        print(f"ERRO: banco local com os dados não encontrado em {dados}")
        print("Rode `python preparar_banco_dev.py` (sem argumentos) antes.")
        return 1

    tabelas = schema_mysql.tabelas_do_arquivo_ddl(ddl.read_text(encoding="utf-8"))
    if not tabelas:
        print(f"ERRO: nenhum CREATE TABLE reconhecido em {ddl.name}")
        return 1

    print(f"Schema real: {ddl.name} ({len(tabelas)} tabela(s))")
    print(f"Dados:       {dados.name}")

    destino_arquivo.parent.mkdir(parents=True, exist_ok=True)
    if destino_arquivo.exists():
        print(f"Sobrescrevendo o espelho anterior: {destino_arquivo}")

    origem = sqlite3.connect(dados)
    espelho = sqlite3.connect(destino_arquivo)
    avisos: list[str] = []
    faltando: dict[str, list[str]] = {}

    try:
        for tabela, colunas in tabelas.items():
            print(f"\n{tabela}")
            print(f"  {len(colunas)} coluna(s) — schema real")
            avisos += schema_mysql.criar_tabela_sqlite(espelho, tabela, colunas)

            if tabela in TABELAS_DE_SAIDA:
                print("  vazia — é saída do robô, não insumo")
                continue

            linhas, sem_dado = _carregar_do_banco_local(origem, espelho, tabela, colunas)
            print(f"  {linhas} linha(s) carregada(s) do banco local")
            if sem_dado:
                faltando[tabela] = sem_dado

        espelho.commit()
    finally:
        espelho.close()
        origem.close()

    print("\n" + "=" * 70)

    if avisos:
        print("\nTraduções de tipo que perdem informação:")
        for aviso in avisos:
            print(f"  - {aviso}")

    if faltando:
        print("\nColunas do banco real que o banco local não tem — ficaram sem dado:")
        for tabela, colunas in faltando.items():
            print(f"  - {tabela}: {', '.join(colunas)}")

    print(
        "\n⚠️ Este espelho tem a ESTRUTURA do banco real e DADOS de 2025.\n"
        "   Serve para exercitar o fluxo inteiro sem acesso ao MySQL.\n"
        "   Homologação com número certo continua exigindo `espelhar_banco.py`."
    )
    print(f"\nEspelho: {destino_arquivo}")
    print("Para usá-lo, aponte no .env:")
    print("    ENV=dev")
    print(f"    CAMINHO_SQLITE={destino_arquivo}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="preparar_banco_dev.py",
        description=(
            "Prepara um SQLite local. Sem argumentos, adapta o banco dos "
            "projetos de origem; com --do-schema-real, monta o espelho a partir "
            "do DDL real já extraído."
        ),
    )
    parser.add_argument(
        "--do-schema-real",
        action="store_true",
        help=(
            "Monta o espelho com a estrutura de banco_de_dados/schema-real-*.sql "
            "e os dados do banco local. Não precisa de MySQL."
        ),
    )
    parser.add_argument(
        "--destino",
        type=Path,
        help=f"Só com --do-schema-real. Padrão: {ESPELHO.name}",
    )
    parser.add_argument(
        "--dados",
        type=Path,
        help=f"Só com --do-schema-real. Banco local de onde ler. Padrão: {DESTINO.name}",
    )
    args = parser.parse_args(argv)

    if args.do_schema_real:
        return montar_do_schema_real(args.destino or ESPELHO, args.dados or DESTINO)

    return _preparar_do_banco_de_origem()


def _preparar_do_banco_de_origem() -> int:
    if not ORIGEM.is_file():
        print(f"ERRO: banco de origem não encontrado em {ORIGEM}")
        print("Os projetos de origem foram inseridos em projetos-origem/?")
        return 1

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ORIGEM, DESTINO)
    print(f"Copiado: {ORIGEM.name} -> {DESTINO}")

    conexao = sqlite3.connect(DESTINO)
    try:
        existentes = {
            linha[0]
            for linha in conexao.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

        for antigo, novo in RENOMEAR.items():
            if novo in existentes:
                print(f"  já renomeada: {novo}")
                continue
            if antigo not in existentes:
                print(f"  AVISO: [{antigo}] não existe no banco de origem")
                continue
            conexao.execute(f'ALTER TABLE "{antigo}" RENAME TO "{novo}"')
            print(f"  renomeada: {antigo} -> {novo}")

        for nome in CRIAR_SE_FALTAR:
            if nome in existentes:
                print(f"  já existe: {nome}")
                continue
            conexao.execute(ddl_sqlite(nome))
            print(f"  criada vazia: {nome} (schema do banco real)")

        _adaptar_anexo5(conexao)
        _adaptar_mapeamento_descritores(conexao)
        _acrescentar_colunas_da_unificacao(conexao)

        conexao.commit()

        print("\nTabelas no banco de dev:")
        for (nome,) in conexao.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ):
            total = conexao.execute(f'SELECT COUNT(*) FROM "{nome}"').fetchone()[0]
            print(f"  {nome:45s} {total:6d} linhas")

    finally:
        conexao.close()

    print(f"\nPronto. Aponte CAMINHO_SQLITE para:\n  {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
