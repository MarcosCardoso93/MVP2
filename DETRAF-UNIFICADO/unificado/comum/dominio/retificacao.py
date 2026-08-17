"""Regra da retificação/recuperação (HU-21) — a parte que não depende de tela.

Origem: `projeto-6-h20-h21/H21/src/services/AGI/Retificacao_Contestacao.py`, onde
estas funções viviam como métodos estáticos de uma classe de 563 linhas que abria
o AGI no construtor. Separadas aqui porque são **puras** — e porque, na origem,
nenhuma delas tinha um único teste, apesar de serem exatamente o que decide
quanto vai ser lançado num evento irreversível.

## O que a HU-21 faz

Quando a Vivo recupera tráfego que havia sido contestado no mês anterior, alguém
precisa lançar o evento "Recuperação" no AGI, em `Contestação > Gerenciar`
(V2 ¶713). A recuperação é reconhecida pela **variação negativa** — ver
`comum.dominio.variacao`, que já apontava para cá.

⚠️ **A regra de detecção não foi validada com o negócio.** A origem filtra só por
`vb_variacao_perc < 0`, e o próprio código pergunta se não deveria ser
`minutos_variacao_perc`, ou as duas — havia uma única linha de teste na tabela
quando aquilo foi escrito. Ver `docs/04-relatorios/duvidas-pendentes.md`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from comum.config.constantes import FATOR_LIQUIDO_PIS_COFINS

#: Colunas do CSV exportado da grid de contestações que o cruzamento usa.
#:
#: Confirmadas em 2026-08-03 contra um export real: `Ope. Prest.` traz a EOT pura
#: (`"076"`), não `EOT-Nome`, e `Valor Bruto` vem no formato BR (`"852.618,97"`).
COL_CSV_ID_PROCESSO = "ID Processo"
COL_CSV_EOT_PRESTADORA = "Ope. Prest."
COL_CSV_PERIODO_REFERENCIA = "Per. Ref."
COL_CSV_PERIODO_TRAFEGO = "Per. Traf."
COL_CSV_VALOR_BRUTO = "Valor Bruto"

#: Folga na comparação de valor, em reais. Existe por arredondamento, não por
#: tolerância a divergência: o valor é uma das quatro chaves que identificam o
#: processo.
TOLERANCIA_VALOR: float = 0.01


class ProcessoNaoIdentificado(RuntimeError):
    """O cruzamento no CSV não achou exatamente um processo."""


def calcular_valores_evento(minutos: float, valor_bruto: float) -> dict[str, float]:
    """
    Os campos do evento de Recuperação, a partir da diferença apurada.

    Regra do To Be MVP2, ¶369-372: o valor líquido é o bruto menos PIS/Cofins, e
    o PIS/Cofins é o que sobra da subtração — não é recalculado, para que os três
    fechem entre si mesmo com arredondamento.

    Args:
        minutos: Minutos recuperados (valor absoluto da diferença).
        valor_bruto: Valor bruto recuperado (valor absoluto da diferença).

    Returns:
        ``duracao``, ``valor_liquido``, ``valor_pis_cofins`` e
        ``valor_bruto_negociado``, na ordem em que o AGI os pede.
    """
    valor_liquido = round(valor_bruto * FATOR_LIQUIDO_PIS_COFINS, 2)

    return {
        "duracao": minutos,
        "valor_liquido": valor_liquido,
        # Subtração, e não `valor_bruto * (1 - FATOR)`: assim líquido +
        # PIS/Cofins dá exatamente o bruto, sem sobrar centavo de arredondamento.
        "valor_pis_cofins": round(valor_bruto - valor_liquido, 2),
        "valor_bruto_negociado": valor_bruto,
    }


def converter_valor_br(texto: str | float) -> float:
    """
    ``"852.618,97"`` → ``852618.97``.

    O CSV do AGI vem em formato brasileiro, com ponto de milhar e vírgula
    decimal. `float()` direto sobre isso ou levanta ou devolve o número errado
    (``"852.618"`` viraria ``852.618``).
    """
    return float(str(texto).strip().replace(".", "").replace(",", "."))


def achar_id_processo(
    caminho_csv: Path,
    eot_operadora: str,
    periodo_referencia: str,
    periodo_trafego: str,
    valor_bruto: float,
    tolerancia: float = TOLERANCIA_VALOR,
) -> str:
    """
    Acha o ID do processo no CSV exportado da grid, cruzando quatro chaves.

    🔴 **EOT + Referência + Tráfego não bastam.** Confirmado no export real de
    2026-08-03: as linhas 590969 e 590971 têm os três iguais e diferem só no
    valor. Por isso o valor entra no cruzamento — sem ele, o robô escolheria uma
    das duas e lançaria a Recuperação no processo errado, que é irreversível.

    ✅ **O valor comparado é o `vb_diferenca`, e isso foi confirmado pelo GP em
    2026-08-10** (pendência Q28). A origem tinha registrado a dúvida de que a
    coluna "Valor Bruto" do CSV pudesse ser o valor da contestação original, e
    não a diferença recuperada; não é.

    Raises:
        ProcessoNaoIdentificado: Se não achar **exatamente** um. Zero e vários
            são erro pelo mesmo motivo: nos dois casos não se sabe qual é, e
            escolher seria pior do que parar.
    """
    dados = pd.read_csv(caminho_csv, sep=";", encoding="utf-8", dtype=str)

    faltando = [
        coluna
        for coluna in (
            COL_CSV_ID_PROCESSO,
            COL_CSV_EOT_PRESTADORA,
            COL_CSV_PERIODO_REFERENCIA,
            COL_CSV_PERIODO_TRAFEGO,
            COL_CSV_VALOR_BRUTO,
        )
        if coluna not in dados.columns
    ]
    if faltando:
        raise ProcessoNaoIdentificado(
            f"O CSV exportado não tem a(s) coluna(s) {faltando}. O layout da "
            f"grid do AGI mudou, ou o arquivo não é o que se espera."
        )

    def igual(coluna: str, esperado) -> pd.Series:
        return dados[coluna].astype(str).str.strip() == str(esperado).strip()

    candidatas = dados[
        igual(COL_CSV_EOT_PRESTADORA, eot_operadora)
        & igual(COL_CSV_PERIODO_REFERENCIA, periodo_referencia)
        & igual(COL_CSV_PERIODO_TRAFEGO, periodo_trafego)
    ]

    # A diferença é arredondada a centavos ANTES de comparar. Sem isso,
    # `abs(586631.59 - 586631.58)` sai como 0.010000000005 em ponto flutuante e
    # não cabe numa tolerância de 0.01 — a linha certa é descartada por um erro
    # de representação, e o robô diz que não achou o processo.
    diferenca = (
        candidatas[COL_CSV_VALOR_BRUTO]
        .apply(converter_valor_br)
        .sub(valor_bruto)
        .abs()
        .round(2)
    )
    candidatas = candidatas[diferenca <= round(tolerancia, 2)]

    if len(candidatas) != 1:
        raise ProcessoNaoIdentificado(
            f"Esperava 1 processo no CSV para EOT [{eot_operadora}], referência "
            f"[{periodo_referencia}], tráfego [{periodo_trafego}] e valor bruto "
            f"[{valor_bruto}] — encontrei {len(candidatas)}. Nada foi retificado."
        )

    return str(candidatas.iloc[0][COL_CSV_ID_PROCESSO]).strip()
