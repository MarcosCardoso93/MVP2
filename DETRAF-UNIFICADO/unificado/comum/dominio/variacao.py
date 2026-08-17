"""Regra de variação e decisão de contestar — base comum dos RPAs do Detraf.

Esta é **a** regra de decisão do processo: define, por combinação de operadora ×
EOT × remuneração × mês de tráfego, se há contestação formal a uma operadora.
Tem consequência financeira direta, e por isso existe num único lugar.

---

## Por que este módulo existe

Os Projetos 3 e 4 implementaram a regra de formas **incompatíveis**, cada um
lendo a mesma V2:

| Aspecto            | Projeto 3                  | Projeto 4              |
|--------------------|----------------------------|------------------------|
| Base do percentual | expectativa (``RS_tbra``)  | operadora              |
| Sinal              | com sinal                  | ``abs()``              |
| Par ausente        | ``NA`` -> ``"N"``          | 100% -> ``"S"``        |
| Limiar             | ``>= 1.0``                 | ``>= 0.01`` (fração)   |

Ver ``trabalho/inventarios/duplicacoes.md`` D-13.

## A regra decidida, e sua fundamentação na V2

**Base = lado operadora.** A V2: *"A origem dos dados é o Detraf 'oficial'
enviado para a Vivo pela operadora, já com a informação se está divergente da
expectativa e quanto."* O documento oficial da operadora é a referência.

**Par ausente contesta.** A V2: *"Caso tenha arquivo de detraf de uma operadora
mas não o de expectativa, deve-se preencher a tabela normalmente e apresentar os
valores zerados de expectativas. Os dados da operadora são considerados."*
Usar a expectativa como base (Projeto 3) faz esse caso virar divisão por zero e
**deixar de contestar** justamente o cenário mais contestável — a operadora
cobra algo que a Vivo não esperava.

**O sinal importa.** A V2: *"se a variação for maior que **+1%** ele marca com
'S'"*. E a variação **negativa** tem destino próprio: a retificação da HU-21
(*"houve recuperação de tráfego pela Vivo apresentando variação negativa"*).
Contestar uma cobrança **menor** que a esperada não teria sentido econômico numa
contestação de despesa.

**Limiar ``>=``.** Projeto 3, Projeto 4 e o PDF de histórias usam ``>=``.

⚠️ **Pendência residual (Q2, não bloqueante):** a V2 também diz *"se for
**superior**"*, que literalmente seria ``> 1%``. A diferença só aparece em
exatamente 1,000000%. Adotado ``>=``; confirmar com o PO.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from comum.config.constantes import LIMIAR_VARIACAO_CONTESTACAO

FLAG_CONTESTAR = "S"
FLAG_NAO_CONTESTAR = "N"

#: Valor de variação atribuído quando não há par do lado da base.
VARIACAO_PAR_AUSENTE = 100.0


def calcular_variacao(
    valor_operadora: pd.Series,
    valor_expectativa: pd.Series,
) -> pd.Series:
    """
    Calcula a variação percentual **com sinal**, na escala 0-100.

    Positiva significa que a operadora apresentou mais do que a expectativa da
    Vivo — o caso que gera contestação.

    A base é o **lado operadora**. Quando ela é zero mas há valor de
    expectativa, a variação é ``-100`` (a Vivo esperava algo que a operadora não
    cobrou). Quando ambos são zero, a variação é ``0``.

    Args:
        valor_operadora: Valores apresentados pela operadora.
        valor_expectativa: Valores da expectativa gerada pelo ICT.

    Returns:
        Série de variações percentuais com sinal, alinhada ao índice de entrada.
    """
    operadora = pd.to_numeric(valor_operadora, errors="coerce").fillna(0).to_numpy()
    expectativa = pd.to_numeric(valor_expectativa, errors="coerce").fillna(0).to_numpy()

    diferenca = operadora - expectativa

    tem_base = operadora != 0
    tem_alternativa = expectativa != 0

    base_segura = np.where(tem_base, operadora, 1.0)
    variacao_com_base = diferenca / base_segura * 100.0

    # Sem base (operadora == 0) mas com expectativa: a Vivo esperava e a
    # operadora não cobrou. Variação -100% — não contesta, pelo sinal.
    resultado = np.where(
        tem_base,
        variacao_com_base,
        np.where(tem_alternativa, -VARIACAO_PAR_AUSENTE, 0.0),
    )

    return pd.Series(resultado, index=valor_operadora.index, dtype="float64")


def deve_contestar(
    variacao_percentual: pd.Series,
    limiar: float = LIMIAR_VARIACAO_CONTESTACAO,
) -> pd.Series:
    """
    Aplica a regra de corte sobre a variação e devolve a flag ``S``/``N``.

    Contesta quando a variação é **positiva** e atinge o limiar — ou seja, a
    operadora apresentou pelo menos ``limiar`` a mais que a expectativa.

    Args:
        variacao_percentual: Variação com sinal, na escala 0-100.
        limiar: Fração mínima para contestar. Default ``0.01`` (1%).

    Returns:
        Série de ``"S"`` / ``"N"``.
    """
    limiar_percentual = limiar * 100.0
    variacao = pd.to_numeric(variacao_percentual, errors="coerce")

    contesta = variacao.notna() & (variacao >= limiar_percentual)

    return pd.Series(
        np.where(contesta, FLAG_CONTESTAR, FLAG_NAO_CONTESTAR),
        index=variacao_percentual.index,
        dtype="object",
    )


def aplicar(
    df: pd.DataFrame,
    coluna_operadora: str,
    coluna_expectativa: str,
    coluna_variacao: str,
    coluna_flag: str | None = None,
    limiar: float = LIMIAR_VARIACAO_CONTESTACAO,
) -> pd.DataFrame:
    """
    Acrescenta ao DataFrame a coluna de variação e, opcionalmente, a flag.

    Conveniência para os dois consumidores (a consolidação do RPA 2 e a do
    RPA 3), que precisam do mesmo par de colunas com nomes diferentes.

    Args:
        df: DataFrame já agregado pelas dimensões de comparação.
        coluna_operadora: Nome da coluna com o valor da operadora.
        coluna_expectativa: Nome da coluna com o valor da expectativa.
        coluna_variacao: Nome da coluna de variação a criar.
        coluna_flag: Nome da coluna de flag a criar. Se ``None``, não cria.
        limiar: Fração mínima para contestar.

    Returns:
        Cópia do DataFrame com as colunas acrescentadas.
    """
    resultado = df.copy()

    resultado[coluna_variacao] = calcular_variacao(
        resultado[coluna_operadora], resultado[coluna_expectativa]
    )

    if coluna_flag is not None:
        resultado[coluna_flag] = deve_contestar(
            resultado[coluna_variacao], limiar=limiar
        )

    return resultado
