"""Resolver de remuneração — **reexporta a base comum**.

O conteúdo foi promovido para `comum/dominio/mapa_remuneracao.py` em 2026-08-06,
ao corrigir o defeito **A4**: o RPA 2 gravava a remuneração por uma regra e o
RPA 3 a lia por outra, e a coluna é parte da chave do sinal do analista.

Este módulo continua existindo para que os imports do RPA 3 sigam valendo —
`from src.services import mapa_remuneracao as mr` aparece na orquestração e nos
services de EXT, INT e consolidação.
"""

from comum.dominio.mapa_remuneracao import (  # noqa: F401
    COLUNAS_MAPA_DESCRITORES,
    PRODUTO_DETRAF,
    carregar_mapa_descritores,
    construir_indice_remuneracao,
    resolver_remuneracao,
    resolver_series,
)
