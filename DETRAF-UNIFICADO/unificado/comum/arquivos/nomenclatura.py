"""Montagem centralizada dos nomes de artefatos do Épico 4.

**Único** lugar onde os nomes de arquivo são construídos (AI/02 §7). Nunca monte
nomes de artefato espalhados pelo código — chame estas funções.

Padrões (AI/02 §7, AI/09, AI/10 §2):

| Artefato                | Nome                                             |
|-------------------------|--------------------------------------------------|
| EXT (HU-12)             | ``DE_AGI_D_{aaaamm}_TBRA_X_{OPERADORA}_EXT``      |
| INT (HU-13)             | ``DE_AGI_D_{aaaamm}_TBRA_X_{OPERADORA}_INT``      |
| Base Contestação (dep.) | ``Base_Contestação_{operadora}_{mes}``           |
| ``_ENV`` (HU-14)        | ``Base Contestação_{operadora}_{mes}_ENV``       |
| CONT_PROC (HU-16)       | ``CONT_PROC_MASCARA_{operadora}_{aaaamm}.xls``   |
| Carta (HU-14)           | ``CT - {n}`` (numeração sequencial)              |

Nota (D-8/validar em campo): a grafia exata da operadora nos nomes AGI (caixa,
espaços) deve ser conferida contra exemplos reais. Aqui a normalização remove
acentos e colapsa espaços; o EXT/INT usam a forma em CAIXA ALTA.
"""

from __future__ import annotations

import re
import unicodedata

from comum.config import constantes as const


def normalizar_operadora(nome: str, maiuscula: bool = False) -> str:
    """
    Normaliza o nome de uma operadora para uso em nomes de arquivo.

    Remove acentos/diacríticos, apara as pontas e colapsa espaços internos
    repetidos em um único espaço.

    Args:
        nome: Nome bruto da operadora (pode conter acentos e espaços extras).
        maiuscula: Se ``True``, retorna em CAIXA ALTA (usado nos nomes AGI).

    Returns:
        O nome normalizado.

    Raises:
        ValueError: Se ``nome`` for vazio após a normalização.
    """

    if nome is None:
        raise ValueError("Nome de operadora não pode ser None.")

    # Remove acentos: decompõe (NFKD) e descarta os caracteres combinantes.
    sem_acento = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", str(nome))
        if not unicodedata.combining(caractere)
    )

    # Colapsa qualquer sequência de espaços em branco em um único espaço.
    normalizado = re.sub(r"\s+", " ", sem_acento).strip()

    if not normalizado:
        raise ValueError(f"Nome de operadora inválido/vazio: [{nome!r}]")

    return normalizado.upper() if maiuscula else normalizado


def _validar_aaaamm(aaaamm: str) -> str:
    """Valida o período no formato ``AAAAMM`` e o retorna como string."""

    periodo = str(aaaamm).strip()
    if not (periodo.isdigit() and len(periodo) == 6):
        raise ValueError(
            f"Período deve estar no formato 'AAAAMM' (ex.: '202606'). Recebido: [{aaaamm!r}]"
        )
    return periodo


def _nome_agi(aaaamm: str, operadora: str, sufixo: str) -> str:
    """Monta o nome-base (sem extensão) dos artefatos AGI (EXT/INT)."""

    periodo = _validar_aaaamm(aaaamm)
    op = normalizar_operadora(operadora, maiuscula=True)
    return f"{const.PREFIXO_AGI}_{periodo}_{const.INFIXO_AGI}_{op}_{sufixo}"


def nome_ext(aaaamm: str, operadora: str) -> str:
    """Nome-base do arquivo EXT (HU-12): ``DE_AGI_D_{aaaamm}_TBRA_X_{OP}_EXT``."""

    return _nome_agi(aaaamm, operadora, const.SUFIXO_EXT)


def nome_int(aaaamm: str, operadora: str) -> str:
    """Nome-base do arquivo INT (HU-13): ``DE_AGI_D_{aaaamm}_TBRA_X_{OP}_INT``."""

    return _nome_agi(aaaamm, operadora, const.SUFIXO_INT)


# `nome_base_contestacao` e `nome_modelo_base_contestacao` foram REMOVIDAS
# (2026-08-04): nomeavam o arquivo `Base_Contestação_{OP}_{mes}[.xlsx]` e o seu
# modelo `_M`. A base de contestação é uma **tabela** — decisão do cliente, e o
# que a V2 já pedia ("Não é necessário gerar o arquivo, mas usar a lógica e
# popular a tabela"). O `_ENV` (abaixo) continua sendo arquivo e mantém a grafia
# herdada daquele nome.


def nome_env(operadora: str, mes: str) -> str:
    """
    Nome-base do arquivo ``_ENV`` (HU-14).

    Segue a grafia literal da documentação (AI/09 §4.1, AI/10 §2), com **espaço**
    entre "Base" e "Contestação": ``Base Contestação_{operadora}_{mes}_ENV``.
    """

    op = normalizar_operadora(operadora)
    return f"Base Contestação_{op}_{mes}_{const.SUFIXO_ENV}"


def nome_cont_proc(
    operadora: str, aaaamm: str, extensao: str = const.EXTENSAO_EXCEL
) -> str:
    """
    Nome do arquivo CONT_PROC (HU-16), **com extensão**.

    ``CONT_PROC_MASCARA_{operadora}_{aaaamm}{extensao}``

    D-7 resolvida (2026-07-23): o AGI aceita ``.xlsx`` — default deixou de ser ``.xls``
    (que exigiria a dependência `xlwt`, `openpyxl` não grava `.xls` — L-003). Parâmetro
    `extensao` mantido caso a decisão mude no futuro.
    """

    periodo = _validar_aaaamm(aaaamm)
    op = normalizar_operadora(operadora)
    return f"{const.PREFIXO_CONT_PROC}_{op}_{periodo}{extensao}"


def nome_carta(numero: int) -> str:
    """
    Nome-base da carta CT a partir do número sequencial (HU-14).

    ``CT - {numero}`` (ex.: ``CT - 363``). A numeração é resolvida em outra
    tarefa (T-081) lendo o último número da pasta de controle.
    """

    if int(numero) <= 0:
        raise ValueError(f"Número de carta deve ser positivo. Recebido: [{numero!r}]")
    return f"{const.PREFIXO_CARTA} - {int(numero)}"
