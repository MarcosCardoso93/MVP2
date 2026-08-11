"""Fixtures da suíte da base comum.

Duas coisas que os testes precisam e o pytest não dá de graça:

1. **Capturar o que o loguru escreve.** O `caplog` do pytest lê o `logging` da
   biblioteca padrão; o loguru não passa por lá. Sem a ponte abaixo, um teste que
   afirma "isto foi registrado no log" passa em silêncio mesmo quando nada foi.
   Isso importa aqui mais que o normal: boa parte do que esta suíte cobre é
   *justamente* "passar a registrar o que era engolido".

2. **Carregar um módulo de RPA por caminho.** Os três RPAs têm um pacote chamado
   `src` e não coexistem num processo Python. Esta suíte roda sozinha, então dá
   para pôr a raiz de um RPA no path sob demanda — mas só de um por vez.
"""

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

_RAIZ_UNIFICADO = Path(__file__).resolve().parents[1]
if str(_RAIZ_UNIFICADO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_UNIFICADO))

from tests_apoio import LINHA_VALIDA, criar_banco_de_teste, linha, silenciar_diagnose_do_log

silenciar_diagnose_do_log()

# ---------------------------------------------------------------------------
# Banco de teste — antes de qualquer import que resolva `RepositorioCache`
#
# Entrou aqui em 2026-08-06, quando `ValidadorColunas` subiu para `comum/` e
# trouxe o seu teste junto. É o MESMO seed das outras suítes, do
# `tests_apoio.banco` — o schema não pode divergir entre elas, e já divergiu.
# ---------------------------------------------------------------------------
_DIR_TEMP = Path(tempfile.mkdtemp(prefix="detraf_comum_teste_"))
#: Exposto para o teste que precisa mexer no seed em tempo de execução.
CAMINHO_DB = _DIR_TEMP / "TABELAS_DETRAF_TESTE.db"

os.environ.setdefault("ENV", "dev")
# Referência fixa => ANO_MES_REFERENCIA = 202507 (mês anterior a 202508).
os.environ.setdefault("DEBUG_ANO_MES_ATUAL", "202508")
os.environ["CAMINHO_SQLITE"] = str(CAMINHO_DB)

criar_banco_de_teste(CAMINHO_DB)

# A ponte loguru -> caplog vem do módulo de apoio, compartilhada com as suítes
# dos três RPAs (cada uma roda num processo separado, então não dá para
# compartilhar um `conftest.py`).
from tests_apoio import loguru_para_caplog  # noqa: F401 — fixture autouse


def carregar_modulo_de_rpa(caminho_relativo: str, nome_modulo: str):
    """
    Importa um módulo de um RPA pelo caminho, sem colisão de pacote `src`.

    A raiz do RPA entra no `sys.path` para que os imports internos (`from src...`)
    resolvam. Só funciona para **um** RPA por processo — o que basta aqui, já que
    apenas o RPA 2 é exercitado por esta suíte.

    Args:
        caminho_relativo: Caminho a partir de `unificado/`.
        nome_modulo: Nome sob o qual registrar em `sys.modules`.
    """
    caminho = _RAIZ_UNIFICADO / caminho_relativo
    raiz_rpa = _RAIZ_UNIFICADO / Path(caminho_relativo).parts[0]

    for entrada in (str(_RAIZ_UNIFICADO), str(raiz_rpa)):
        if entrada not in sys.path:
            sys.path.insert(0, entrada)

    if nome_modulo in sys.modules:
        return sys.modules[nome_modulo]

    spec = importlib.util.spec_from_file_location(nome_modulo, caminho)
    assert spec and spec.loader, f"não foi possível carregar [{caminho}]"
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome_modulo] = modulo
    spec.loader.exec_module(modulo)
    return modulo


# ---------------------------------------------------------------------------
# Linhas de Detraf — as mesmas das outras suítes, vindas de `tests_apoio.detraf`
# ---------------------------------------------------------------------------
@pytest.fixture()
def df_valido() -> pd.DataFrame:
    """DataFrame de uma linha, aprovada em todas as regras."""
    return pd.DataFrame([LINHA_VALIDA])


@pytest.fixture()
def df_com():
    """Fábrica: ``df_com(gh="X")`` -> DataFrame de uma linha com aquele desvio."""

    def _construir(**alteracoes) -> pd.DataFrame:
        return pd.DataFrame([linha(**alteracoes)])

    return _construir


@pytest.fixture()
def repo_cache():
    """Instância limpa do cache apontando para o SQLite de teste."""
    from comum.dados.repositorio_cache import RepositorioCache

    RepositorioCache.resetar()
    cache = RepositorioCache()
    yield cache
    RepositorioCache.resetar()
