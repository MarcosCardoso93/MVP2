"""Apoio comum às quatro suítes de teste.

Vive na raiz de `unificado/` porque **cada suíte roda numa invocação separada do
pytest** — os três RPAs têm um pacote chamado `src` e não coexistem num mesmo
processo. Um `conftest.py` compartilhado não alcançaria as quatro; um módulo
importável, sim, já que todos os conftests põem a raiz de `unificado/` no path.

Virou pacote em 2026-08-06, quando a validação subiu para o RPA 1: as duas suítes
passaram a precisar do **mesmo** seed de banco e das **mesmas** linhas de Detraf.
Antes disso, cada conftest montava o seu — e as duas versões já divergiam (a do
RPA 1 tinha duas colunas onde a validação lê seis). Um seed por suíte é o padrão
de defeito que este repositório já pagou duas vezes.

Não é código de produção: nada em `comum/` ou `rpa*/src/` deve importar daqui.
"""

from __future__ import annotations

from tests_apoio.banco import (
    OPERADORAS_PADRAO,
    TARIFAS_PADRAO,
    criar_banco_de_teste,
)
from tests_apoio.detraf import LINHA_VALIDA, POSICOES, linha
from tests_apoio.log import loguru_para_caplog, silenciar_diagnose_do_log

__all__ = [
    "LINHA_VALIDA",
    "OPERADORAS_PADRAO",
    "POSICOES",
    "TARIFAS_PADRAO",
    "criar_banco_de_teste",
    "linha",
    "loguru_para_caplog",
    "silenciar_diagnose_do_log",
]
