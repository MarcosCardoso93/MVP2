"""Conferência de schema e espelhamento do banco (2026-08-06).

O `espelhar_banco.py` só roda inteiro contra um MySQL, que não existe na suíte.
O que se cobre aqui são as partes que **decidem** alguma coisa e que erram em
silêncio se alguém mexer:

- `conferir_colunas`, que diz se o código consegue operar sobre uma tabela real;
- a tradução de tipos MySQL → SQLite e os avisos de perda;
- a criação da tabela espelhada, incluindo os nomes com espaço e acento do
  `tbl_anexo5_processado` — que sem aspas viram erro de sintaxe.

A conferência importa porque é ela que transforma "o robô falhou no meio do
teste" em "falta a coluna X, e ela está no encaminhamento ao DBA".
"""

import re
import sqlite3
from pathlib import Path

import pytest

import espelhar_banco
from comum.dados import tabelas as tbl


class TestConferenciaDeColunas:
    def test_tabela_completa_nao_acusa_nada(self):
        completa = tbl.COLUNAS_ESPERADAS[tbl.LOG_DESPESA_CONTESTACAO]

        assert tbl.conferir_colunas(tbl.LOG_DESPESA_CONTESTACAO, completa) == []

    def test_coluna_faltando_e_nomeada(self):
        sem_a_nova = [
            coluna
            for coluna in tbl.COLUNAS_ESPERADAS[tbl.LOG_DESPESA_CONTESTACAO]
            if coluna != "vb_contestacao"
        ]

        faltando = tbl.conferir_colunas(tbl.LOG_DESPESA_CONTESTACAO, sem_a_nova)

        assert faltando == ["vb_contestacao"]

    def test_coluna_a_mais_no_banco_e_irrelevante(self):
        """Uma coluna que o código não usa não atrapalha ninguém."""
        com_extra = list(tbl.COLUNAS_ESPERADAS[tbl.TARIFAS]) + ["coluna_do_dba"]

        assert tbl.conferir_colunas(tbl.TARIFAS, com_extra) == []

    def test_espaco_nas_pontas_nao_conta_como_diferenca(self):
        com_espaco = [f"  {c} " for c in tbl.COLUNAS_ESPERADAS[tbl.TARIFAS]]

        assert tbl.conferir_colunas(tbl.TARIFAS, com_espaco) == []

    def test_a_caixa_conta(self):
        """
        O MySQL distingue, e uma tabela com `FINAL_DO_DESCRITOR` onde o código
        procura `final_descritor` falha igual a se a coluna não existisse — foi
        exatamente o caso do SQLite de 2025 do Projeto 2.
        """
        em_caixa_alta = [c.upper() for c in tbl.COLUNAS_ESPERADAS[tbl.TARIFAS]]

        assert tbl.conferir_colunas(tbl.TARIFAS, em_caixa_alta) != []

    def test_a_coluna_pendente_no_dba_esta_declarada(self):
        """
        `vb_contestacao` é a **única** ausente do banco real (Q24). Se sair
        daqui, a conferência para de destacá-la e o `verificar_ambiente.py`
        volta a tratá-la como quebra desconhecida.

        Até 2026-08-06 este teste afirmava que eram DUAS — `remuneracao` e
        `vb_contestacao` — e que as duas estavam confirmadas no MySQL real.
        As duas metades eram falsas: `remuneracao` nunca foi coluna nova (é
        `remuneracoes`), e nenhuma das duas tinha sido conferida contra o banco.
        """
        pendentes = tbl.COLUNAS_PENDENTES_NO_BANCO[tbl.LOG_DESPESA_CONTESTACAO]
        esperadas = tbl.COLUNAS_ESPERADAS[tbl.LOG_DESPESA_CONTESTACAO]

        assert set(pendentes) == {"vb_contestacao"}
        assert set(pendentes) <= set(esperadas)

    def test_a_coluna_da_remuneracao_e_plural(self):
        """
        Regressão de 2026-08-06. O código gravava `remuneracao` (singular), que
        não existe: o banco tem `remuneracoes`, como a tabela irmã de arquivos.
        Sendo coluna-CHAVE, o singular derrubava o INSERT do RPA 2 e o UPDATE do
        RPA 3 — e nada disso aparecia na suíte, porque o fixture também estava
        no singular.
        """
        esperadas = tbl.COLUNAS_ESPERADAS[tbl.LOG_DESPESA_CONTESTACAO]

        assert tbl.COL_CONTESTACAO_REMUNERACOES == "remuneracoes"
        assert "remuneracoes" in esperadas
        assert "remuneracao" not in esperadas

    def test_toda_tabela_conhecida_tem_colunas_declaradas(self):
        """Uma tabela sem lista passaria na conferência sem conferir nada."""
        assert set(tbl.COLUNAS_ESPERADAS) == set(tbl.TODAS)


class TestTraducaoDeTipos:
    @pytest.mark.parametrize(
        "mysql, esperado",
        [
            ("int(11)", "INTEGER"),
            ("bigint unsigned", "INTEGER"),
            ("double", "REAL"),
            ("varchar(255)", "TEXT"),
            ("datetime", "TEXT"),
            ("tipo_que_nao_existe", "TEXT"),
        ],
    )
    def test_traduz_os_tipos_comuns(self, mysql, esperado):
        assert espelhar_banco._tipo_sqlite(mysql)[0] == esperado

    def test_decimal_avisa_que_perde_precisao(self):
        """
        `DECIMAL(18,6)` de valor financeiro virando `REAL` explica diferença de
        centavos — e é melhor avisar do que deixar alguém abrir defeito por isso.
        """
        tipo, aviso = espelhar_banco._tipo_sqlite("decimal(18,6)")

        assert tipo == "REAL"
        assert aviso and "decimal exato" in aviso

    def test_varchar_nao_gera_aviso(self):
        assert espelhar_banco._tipo_sqlite("varchar(50)")[1] is None


class TestCriacaoDaTabelaEspelhada:
    @pytest.fixture()
    def destino(self):
        conexao = sqlite3.connect(":memory:")
        yield conexao
        conexao.close()

    def test_cria_a_tabela_com_as_colunas_na_ordem(self, destino):
        colunas = [("id", "int(11)", False), ("nome", "varchar(80)", True)]

        espelhar_banco._criar_tabela_sqlite(destino, "t", colunas)

        assert [linha[1] for linha in destino.execute("PRAGMA table_info(t)")] == [
            "id",
            "nome",
        ]

    def test_nome_com_espaco_e_acento_sobrevive(self, destino):
        """
        `tbl_anexo5_processado` tem nomes com espaço — "Nome Fantasia",
        "Endereco de Correspondencia". Sem as aspas duplas no DDL, o CREATE TABLE
        nem compila.

        O acento continua coberto por uma coluna **sintética**: o espelho tem que
        aguentar um nome acentuado se o DBA criar um algum dia. Mas as amostras
        reais vêm sem acento, porque é assim que o banco as tem — até 2026-08-06
        este teste usava "Endereço de Correspondência" acentuado e dava a impressão
        de que aquele era o nome verdadeiro.
        """
        colunas = [
            ("EOT", "varchar(10)", True),
            ("Nome Fantasia", "varchar(120)", True),
            ("Endereco de Correspondencia", "varchar(255)", True),
            ("Coluna Acentuada Sintética", "varchar(10)", True),
        ]

        espelhar_banco._criar_tabela_sqlite(destino, "anexo", colunas)

        nomes = [linha[1] for linha in destino.execute("PRAGMA table_info(anexo)")]
        assert "Nome Fantasia" in nomes
        assert "Endereco de Correspondencia" in nomes
        assert "Coluna Acentuada Sintética" in nomes

    def test_not_null_e_preservado(self, destino):
        colunas = [("obrigatoria", "varchar(10)", False)]

        espelhar_banco._criar_tabela_sqlite(destino, "t", colunas)

        with pytest.raises(sqlite3.IntegrityError):
            destino.execute("INSERT INTO t (obrigatoria) VALUES (NULL)")

    def test_recriar_descarta_o_espelho_anterior(self, destino):
        """Espelhar de novo tem que dar o banco novo, não os dois misturados."""
        espelhar_banco._criar_tabela_sqlite(destino, "t", [("a", "int", True)])
        destino.execute("INSERT INTO t (a) VALUES (1)")

        espelhar_banco._criar_tabela_sqlite(destino, "t", [("a", "int", True)])

        assert destino.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 0

    def test_devolve_os_avisos_de_traducao(self, destino):
        colunas = [("valor", "decimal(18,6)", True), ("nome", "varchar(10)", True)]

        avisos = espelhar_banco._criar_tabela_sqlite(destino, "t", colunas)

        assert len(avisos) == 1
        assert "t.valor" in avisos[0]


# ---------------------------------------------------------------------------
# Os testes-guarda (2026-08-06)
#
# 🔴 Este bloco existe porque a suíte inteira passava enquanto o código estava
# quebrado contra o banco real. Os `fixtures` declaravam o schema que o código
# supunha, então os testes validavam a suposição — três defeitos (nomes do Anexo 5
# com acento, `remuneracao` no singular, `vb_contestacao` inexistente) viveram
# meses sem uma única falha.
#
# O que fecha o buraco é comparar `COLUNAS_ESPERADAS` com o DDL REAL, e não com
# outra coisa escrita pela mesma pessoa que escreveu o código.
# ---------------------------------------------------------------------------

_DIRETORIO_BANCO = Path(espelhar_banco.__file__).resolve().parent / "banco_de_dados"


def _colunas_do_ddl_real() -> dict[str, set[str]]:
    """
    Nomes de coluna por tabela, lidos do `schema-real-*.sql` mais recente.

    A saída de ``SHOW CREATE TABLE`` é gerada por máquina e estável: uma coluna
    por linha, o nome entre crases, e o bloco termina na primeira linha que
    começa com ``PRIMARY KEY``, ``KEY``, ``UNIQUE`` ou ``)``.
    """
    arquivos = sorted(_DIRETORIO_BANCO.glob("schema-real-*.sql"))
    if not arquivos:
        return {}

    tabelas_encontradas: dict[str, set[str]] = {}
    tabela_atual: str | None = None

    for linha in arquivos[-1].read_text(encoding="utf-8").splitlines():
        despida = linha.strip()

        inicio = re.match(r"CREATE TABLE `([^`]+)`", despida)
        if inicio:
            tabela_atual = inicio.group(1)
            tabelas_encontradas[tabela_atual] = set()
            continue

        if tabela_atual is None:
            continue

        if re.match(r"^(PRIMARY KEY|KEY|UNIQUE|CONSTRAINT|\))", despida):
            tabela_atual = None
            continue

        coluna = re.match(r"^`([^`]+)`", despida)
        if coluna:
            tabelas_encontradas[tabela_atual].add(coluna.group(1))

    return tabelas_encontradas


class TestGuardaContraODDLReal:
    """
    ⚠️ O `.sql` é um **retrato**, tirado quando alguém rodou `espelhar_banco.py`.
    Verde aqui não é o mesmo que verde em produção: se o DBA mexer no schema, este
    teste só descobre na próxima extração. Quem confere ao vivo é o
    `verificar_ambiente.py`.
    """

    @pytest.fixture(scope="class")
    def ddl_real(self) -> dict[str, set[str]]:
        colunas = _colunas_do_ddl_real()
        if not colunas:
            pytest.skip(
                "sem banco_de_dados/schema-real-*.sql — rode "
                "`python espelhar_banco.py --somente-schema`"
            )
        return colunas

    def test_toda_coluna_esperada_existe_no_banco_real(self, ddl_real):
        """
        O teste que teria pego D1, D2 e D3 no dia em que nasceram.

        A única exceção admitida é `COLUNAS_PENDENTES_NO_BANCO` — ausência
        conhecida, com `ALTER TABLE` pedido e degradação implementada.
        """
        divergencias: dict[str, list[str]] = {}

        for tabela, esperadas in tbl.COLUNAS_ESPERADAS.items():
            if tabela not in ddl_real:
                continue

            pendentes = set(tbl.COLUNAS_PENDENTES_NO_BANCO.get(tabela, ()))
            faltando = sorted(set(esperadas) - ddl_real[tabela] - pendentes)
            if faltando:
                divergencias[tabela] = faltando

        assert not divergencias, (
            f"colunas que o código usa e o DDL real não tem: {divergencias}. "
            f"Ou o nome está errado no código, ou a coluna precisa entrar em "
            f"COLUNAS_PENDENTES_NO_BANCO com pedido ao DBA."
        )

    def test_o_ddl_confirmado_bate_com_o_ddl_real(self, ddl_real):
        """`DDL_CONFIRMADO` alimenta os fixtures — se ele mentir, eles mentem junto."""
        divergencias: dict[str, list[str]] = {}

        for tabela, colunas in tbl.DDL_CONFIRMADO.items():
            if tabela not in ddl_real:
                continue

            inventadas = sorted(set(colunas) - ddl_real[tabela])
            if inventadas:
                divergencias[tabela] = inventadas

        assert not divergencias, (
            f"DDL_CONFIRMADO declara coluna(s) que não existem no banco: "
            f"{divergencias}"
        )

    def test_as_cinco_tabelas_estao_no_ddl_real(self, ddl_real):
        assert set(tbl.TODAS) <= set(ddl_real)


class TestGuardaEmProcesso:
    """A mesma classe de erro, sem depender de arquivo — roda em checkout limpo."""

    def test_esperadas_sao_subconjunto_das_confirmadas(self):
        for tabela, esperadas in tbl.COLUNAS_ESPERADAS.items():
            confirmadas = set(tbl.DDL_CONFIRMADO.get(tabela, {}))
            if not confirmadas:
                continue

            pendentes = set(tbl.COLUNAS_PENDENTES_NO_BANCO.get(tabela, ()))
            faltando = set(esperadas) - confirmadas - pendentes

            assert not faltando, f"{tabela}: {sorted(faltando)} fora do DDL_CONFIRMADO"

    def test_toda_tabela_tem_ddl_confirmado(self):
        """Sem DDL confirmado, `tests_apoio.banco.ddl_sqlite` não sabe criá-la."""
        assert set(tbl.DDL_CONFIRMADO) == set(tbl.TODAS)
