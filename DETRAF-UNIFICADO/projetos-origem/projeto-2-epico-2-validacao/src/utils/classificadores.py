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
