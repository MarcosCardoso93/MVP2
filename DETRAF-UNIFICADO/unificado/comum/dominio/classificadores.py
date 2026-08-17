"""Classificação de descritores do Detraf — base comum dos RPAs.

Duas funções puras, sem I/O: dado o descritor de uma linha, dizem qual regra de
tarifa se aplica a ela e qual é o tipo de remuneração correspondente.

Veio de ``rpa2/src/utils/`` em 2026-08-06, quando a validação por coluna subiu
para o RPA 1 e passou a ser usada pelos dois robôs. Não ficou re-export no lugar
antigo: o defeito **A4** nasceu justamente de haver duas fontes para a mesma
classificação, e um segundo nome canônico é como aquilo recomeça.
"""

from typing import Optional


def classificar_regra_inicio_fim_desc(desc: str) -> Optional[str]:
    """
    Classifica a descrição conforme o caractere inicial e final.

    Regras:
    - Final "V" → DESC final "V"
    - Final "L" → DESC final "L"
    - Início "L" e final "I" → DESC início "L" e final "I"
    - Início diferente de "L" e final "I"
      → DESC início diferente de "L" e final "I"

    Args:
        desc: Valor da descrição.

    Returns:
        Nome da regra correspondente ou None caso não exista.
    """
    desc = desc.strip().upper()

    if not desc:
        return None

    inicio = desc[0]
    final = desc[-1]

    if final == "V":
        return 'DESC final V""'

    if final == "L":
        return 'DESC final L""'

    if final == "I":
        return (
            'DESC início L" e final "I""'
            if inicio == "L"
            else 'DESC início diferente de L" e final "I""'
        )

    return None


def classificar_descritor_remuneracao(descritor: str) -> Optional[str]:
    """
    Classifica o descritor conforme caractere inicial e final.

    🔴 **ATENÇÃO — esta NÃO é a mesma remuneração que o RPA 3 usa (defeito A4,
    achado em 2026-08-06).**

    Há duas fontes de remuneração no repositório, com vocabulários diferentes:

    - **esta função** devolve ``TU-RL``, ``VU-M``, ``TUCOM``, ``TU-RIU1``,
      ``TU-RIU2`` — que é exatamente o vocabulário de
      ``tbl_detraf_tarifas.tipo_remuneracao`` (confirmado nos dados: são esses
      quatro valores, com o RIU dividido em dois porque a tarifa difere). **Para
      validação de tarifa, ela está certa.**
    - **`mapa_remuneracao` (RPA 3)** monta a remuneração a partir da tabela D-5
      ``tbl_detraf_mapeamento_descritores``, que devolve ``TU-COM``, ``TU-RIU``,
      ``VU-T``, ``PU``, ``MU`` e mais 16 — o catálogo amplo.

    As duas concordam **só em ``L`` e ``V``**. Como o RPA 2 grava o resultado
    desta função na coluna ``remuneracao`` da tabela de contestação, e o RPA 3
    procura o sinal do analista por igualdade exata dessa mesma coluna, **todo
    descritor que não termine em L ou V deixa de casar** — e o sintoma é
    indistinguível de "o analista não sinalizou".

    Ver `docs/04-relatorios/duvidas-pendentes.md`, achado **A4**.

    Regras:
    - Final "V" -> VU-M
    - Final "L" -> TU-RL
    - Final "C" -> TUCOM
    - Início "L" e final "I" -> TU-RIU1
    - Início diferente de "L" e final "I" -> TU-RIU2

    Args:
        descritor: Texto a ser classificado.

    Returns:
        Nome da classificação ou None.
    """
    descritor = descritor.strip().upper()

    if not descritor:
        return None

    inicio = descritor[0]
    final = descritor[-1]

    if final == "V":
        return "VU-M"

    if final == "L":
        return "TU-RL"

    if final == "C":
        return "TUCOM"

    if final == "I":
        return "TU-RIU1" if inicio == "L" else "TU-RIU2"

    return None
