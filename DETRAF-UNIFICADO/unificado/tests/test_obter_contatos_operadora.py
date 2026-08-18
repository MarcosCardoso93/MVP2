"""`RepositorioTabelas.obter_contatos_operadora` — Q16 resolvida em 2026-08-18.

Cobre a leitura de `tbl_detraf_destinatarios`: separação Para/Cc por
`tipo_destinatario`, o split por vírgula de múltiplos apelidos na coluna
`operadora`, o filtro por `produto`, e a normalização de nome (case/espaço).

Banco próprio e isolado — não depende do SQLite de dev/espelho nem do seed
compartilhado de `tests_apoio.banco` (nenhum dos dois tem esta tabela ainda).
Cria só o necessário, com `sqlite3` puro.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

_DIR_TEMP = Path(tempfile.mkdtemp(prefix="detraf_destinatarios_teste_"))
_CAMINHO_DB = _DIR_TEMP / "destinatarios.db"


def _popular(caminho: Path) -> None:
    conexao = sqlite3.connect(caminho)
    conexao.execute(
        """
        CREATE TABLE tbl_detraf_destinatarios (
            id INTEGER PRIMARY KEY,
            email TEXT,
            nome TEXT,
            tipo_destinatario TEXT,
            operadora TEXT,
            produto TEXT
        )
        """
    )
    conexao.executemany(
        "INSERT INTO tbl_detraf_destinatarios "
        "(email, nome, tipo_destinatario, operadora, produto) VALUES (?, ?, ?, ?, ?)",
        [
            ("contestacao@claro.com.br", "Contestação", "PARA", "CLARO", "Detraf"),
            ("fiscal@claro.com.br", "Fiscal", "PARA", "CLARO", "Detraf"),
            ("gestor@claro.com.br", "Gestor", "CC", "CLARO", "Detraf"),
            (
                "financeiro@advance.com.br",
                "Financeiro",
                "PARA",
                "ADVANCE_TELECOM, ADVANCE_TELECOMUNICACOES_LTDA",
                "Detraf",
            ),
            ("outro-produto@x.com.br", "Outro", "PARA", "CLARO", "OutroProduto"),
        ],
    )
    conexao.commit()
    conexao.close()


_popular(_CAMINHO_DB)


@pytest.fixture()
def repositorio(monkeypatch):
    """`RepositorioTabelas` isolado, apontado para o SQLite desta suíte."""
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.setenv("CAMINHO_SQLITE", str(_CAMINHO_DB))

    import comum.config.configuration as cfg
    import comum.dados.repositorio_cache as mod_cache
    from comum.dados.repositorio_cache import RepositorioCache
    from comum.dados.repositorio_tabelas import RepositorioTabelas

    # A configuração é lida no import; para o teste, aponta direto (mesmo
    # padrão de `tests/test_repositorio_tabelas.py`).
    monkeypatch.setattr(cfg, "CAMINHO_SQLITE", str(_CAMINHO_DB))
    monkeypatch.setattr(cfg, "ENV", "dev")
    monkeypatch.setattr(mod_cache, "CAMINHO_SQLITE", str(_CAMINHO_DB))
    monkeypatch.setattr(mod_cache, "ENV", "dev")

    RepositorioCache.resetar()
    yield RepositorioTabelas()
    RepositorioCache.resetar()


def test_separa_para_e_cc(repositorio):
    contatos = repositorio.obter_contatos_operadora("CLARO")

    assert contatos["para"] == ["contestacao@claro.com.br", "fiscal@claro.com.br"]
    assert contatos["copia"] == ["gestor@claro.com.br"]


def test_grafia_nao_precisa_bater(repositorio):
    """Case e espaço não importam — o nome vem da pasta no compartilhamento."""
    assert repositorio.obter_contatos_operadora("  claro ")["para"] == [
        "contestacao@claro.com.br",
        "fiscal@claro.com.br",
    ]


def test_um_alias_entre_varios_na_mesma_linha(repositorio):
    """A coluna `operadora` pode listar mais de um nome fantasia, por vírgula."""
    contatos = repositorio.obter_contatos_operadora("ADVANCE_TELECOMUNICACOES_LTDA")

    assert contatos["para"] == ["financeiro@advance.com.br"]


def test_operadora_ausente_devolve_vazio(repositorio):
    assert repositorio.obter_contatos_operadora("ALGAR") == {"para": [], "copia": []}


def test_filtra_por_produto(repositorio):
    """A linha de 'OutroProduto' não vaza para a busca do Detraf."""
    contatos = repositorio.obter_contatos_operadora("CLARO", produto="Detraf")

    assert "outro-produto@x.com.br" not in contatos["para"]
