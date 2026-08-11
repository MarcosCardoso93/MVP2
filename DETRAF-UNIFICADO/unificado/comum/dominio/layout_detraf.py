"""Validação do layout dos arquivos de Detraf — base comum dos RPAs.

Confere se um arquivo tem a **forma** que a V2 documenta, antes de qualquer
validação linha a linha. É a diferença entre "este arquivo tem uma linha ruim" e
"este arquivo não é o arquivo que eu esperava".

---

## Por que existe

Sem esta camada, um arquivo com layout diferente passa direto e é lido por
posição: o código pega o índice 14 achando que é ``R$_Bruto`` e recebe minutos,
sem nada indicar o problema. Foi o que se descobriu comparando o arquivo de
expectativa Vivo com o da operadora — ver
``trabalho/inventarios/inventario-projeto-3.md`` §4.

## A regra

Decidida com o cliente (2026-07-31):

- **posicional**, ignorando os nomes das colunas. Os nomes reais
  (``cd_eot_bil``, ``mes_ref``) não batem com os da V2 (``Credora``,
  ``Referencia``) e variam por operadora;
- **mínimo de 15 colunas**, usando as 15 primeiras. A ALGAR entrega 18 — as 15
  documentadas mais 3 extras no fim — e isso é aceito;
- **cabeçalho descartado** — ``carregar_dados`` já o remove;
- vale para os **dois** tipos de arquivo, operadora e expectativa Vivo, porque a
  V2 diz que as regras valem para ambos.

## Tolerância a linha ruim

Um arquivo pode ter algumas linhas ruins sem estar no layout errado — essas
linhas são separadas depois, pela validação por coluna, e vão para o ``_ERRO``.
Por isso uma posição só é considerada divergente quando a **maioria** dos valores
amostrados falha. Assim se distingue "arquivo errado" de "arquivo com sujeira".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pandas as pd

from comum.config import constantes as const
from comum.dominio.diagnostico_de_recusa import Diagnostico

#: Quantas linhas amostrar para decidir se uma posição está certa.
LINHAS_AMOSTRADAS = 200

#: Fração mínima de valores válidos para a posição ser aceita.
FRACAO_MINIMA_VALIDA = 0.5

#: Quantos exemplos de valor divergente mostrar no diagnóstico.
_EXEMPLOS_NO_DIAGNOSTICO = 3

_PADRAO_AAAAMM = re.compile(r"^\d{6}$")
_PADRAO_INTEIRO = re.compile(r"^-?\d+$")
#: Aceita vírgula como separador decimal (`0,00631`) e a parte inteira ausente
#: (`.00787`) — os dois formatos aparecem nos arquivos reais.
_PADRAO_NUMERO = re.compile(r"^-?(\d+([.,]\d*)?|[.,]\d+)$")
_GRUPOS_HORARIOS_VALIDOS = {"S", "R", "N", "D"}


# ---------------------------------------------------------------------------
# Verificadores por tipo de campo
# ---------------------------------------------------------------------------
def _limpo(valor) -> str:
    return "" if valor is None else str(valor).strip()


def _eh_eot(valor) -> bool:
    """EOT: só dígitos. Aceita `11.0`, que é como o Excel devolve um número."""
    texto = _limpo(valor)
    if not texto:
        return False
    if "." in texto:
        texto = texto.split(".")[0]
    return texto.isdigit()


def _eh_aaaamm(valor) -> bool:
    return bool(_PADRAO_AAAAMM.match(_limpo(valor)))


def _eh_rel(valor) -> bool:
    """Rel: 0 nas linhas de tráfego, 1 nos totais. Pode estar vazia."""
    texto = _limpo(valor)
    if not texto:
        return True
    if "." in texto:
        texto = texto.split(".")[0]
    return texto in {"0", "1", "00"}


def _eh_descritor(valor) -> bool:
    """
    Descritor: precisa conter letra.

    É o que separa um descritor (``_NSN5``, ``LENL``, ``2NENI``) de um valor
    numérico que caiu nessa posição por o layout estar deslocado.
    """
    texto = _limpo(valor)
    return bool(texto) and any(caractere.isalpha() for caractere in texto)


def _eh_grupo_horario(valor) -> bool:
    texto = _limpo(valor).upper()
    return texto in _GRUPOS_HORARIOS_VALIDOS


def _eh_inteiro(valor) -> bool:
    texto = _limpo(valor)
    if not texto:
        return True
    if "." in texto and texto.split(".")[1].strip("0") == "":
        texto = texto.split(".")[0]
    return bool(_PADRAO_INTEIRO.match(texto))


def _eh_numero(valor) -> bool:
    """Número, aceitando vírgula como separador decimal (formato brasileiro)."""
    texto = _limpo(valor)
    if not texto:
        return True
    return bool(_PADRAO_NUMERO.match(texto))


# ---------------------------------------------------------------------------
# Especificação do layout (V2, item 3.2)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ColunaEsperada:
    indice: int
    nome: str
    descricao_do_esperado: str
    verificar: Callable[[object], bool] | None


#: A coluna 5 (POI) é de escrita livre e não obrigatória — sem verificação.
LAYOUT_V2: tuple[ColunaEsperada, ...] = (
    ColunaEsperada(const.COL_CREDORA, "Credora", "EOT numérica", _eh_eot),
    ColunaEsperada(const.COL_DEVEDORA, "Devedora", "EOT numérica", _eh_eot),
    ColunaEsperada(const.COL_REFERENCIA, "Referencia", "AAAAMM", _eh_aaaamm),
    ColunaEsperada(const.COL_TRAFEGO, "Tráfego", "AAAAMM", _eh_aaaamm),
    ColunaEsperada(const.COL_POI, "POI", "escrita livre", None),
    ColunaEsperada(const.COL_REL, "Rel", "0, 1 ou vazio", _eh_rel),
    ColunaEsperada(const.COL_DESCRITOR, "DESC", "descritor (contém letra)", _eh_descritor),
    ColunaEsperada(const.COL_GH, "GH", "S, R, N ou D", _eh_grupo_horario),
    ColunaEsperada(const.COL_CHAMADAS, "Chamadas", "número inteiro", _eh_inteiro),
    ColunaEsperada(const.COL_MINUTOS, "Minutos", "número", _eh_numero),
    ColunaEsperada(const.COL_TARIFA, "Tarifa", "número", _eh_numero),
    ColunaEsperada(const.COL_R_LIQ, "R$_Liq", "número", _eh_numero),
    ColunaEsperada(const.COL_PIS_COFINS, "PIS_Cofins", "número", _eh_numero),
    ColunaEsperada(const.COL_ICMS, "ICMS", "número", _eh_numero),
    ColunaEsperada(const.COL_R_BRUTO, "R$_Bruto", "número", _eh_numero),
)

#: Quantidade mínima de colunas. Extras à direita são aceitas.
COLUNAS_MINIMAS = len(LAYOUT_V2)


# ---------------------------------------------------------------------------
# ✅ O layout completo chegou (2026-08-06, pendência Q6)
#
# As colunas 16 a 21 são `CN_RELACIONAMENTO`, `CBS`, `IBS_Municipal`,
# `IBS_Estadual`, `EOT_Ponta` e `Corredor` — ver `constantes.py`.
#
# **As 15 primeiras não se mexem**, e é o que importa aqui: CBS e IBS entram
# DEPOIS do `R$_Bruto`, não no bloco de impostos. A leitura posicional dos
# índices 0 a 14 continua correta, e o `R$_Bruto` segue no índice 14.
#
# Isso encerra a preocupação registrada em 2026-08-05 sobre o item 7 da V2
# ("mais um imposto deslocando as colunas"): o deslocamento que se temia não
# acontece neste layout.
#
# As posições 16-21 **não são validadas** — os arquivos reais de hoje têm outra
# coisa ali (a ALGAR entrega `valor_total_real`, `OPERATOR_TYPE`, `cd_eot`), e
# validá-las rejeitaria arquivos que estão certos. Ver a nota em `constantes.py`.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Diagnóstico do arquivo de expectativa Vivo
#
# O layout que mais aparece fora do padrão. Reconhecê-lo poupa quem opera de
# investigar do zero um arquivo rejeitado.
# ---------------------------------------------------------------------------
_ASSINATURA_EXPECTATIVA_VIVO = {
    const.COL_REFERENCIA,  # traz a EOT devedora
    const.COL_DESCRITOR,  # traz o Rel
    const.COL_GH,  # traz PARTE_TARIFADA
    const.COL_CHAMADAS,  # traz o descritor
}

_DIAGNOSTICO_EXPECTATIVA_VIVO = (
    "Diagnóstico provável: layout de expectativa Vivo. Ele tem uma coluna a mais "
    "no início (GROUP_CREDORA) e outra no meio (PARTE_TARIFADA), o que desloca "
    "todos os campos, e NÃO possui coluna de R$_Bruto — termina em VALOR_LIQUIDO. "
    "Como a comparação da HU-10 é sobre R$_Bruto, a geração do arquivo precisa "
    "ser corrigida na origem (ICT)."
)


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------
@dataclass
class Divergencia:
    indice: int
    nome: str
    esperado: str
    exemplos_encontrados: list[str]
    valores_validos: int
    valores_avaliados: int

    def __str__(self) -> str:
        exemplos = ", ".join(f'"{valor}"' for valor in self.exemplos_encontrados)
        return (
            f"posição {self.indice} ({self.nome}): esperado {self.esperado}, "
            f"encontrado {exemplos or '(vazio)'} "
            f"[{self.valores_validos}/{self.valores_avaliados} válidos]"
        )


@dataclass
class ResultadoLayout:
    conforme: bool
    total_colunas: int
    divergencias: list[Divergencia] = field(default_factory=list)
    motivo: str = ""

    def mensagem(self, caminho_arquivo: Path | str | None = None) -> str:
        """Monta o diagnóstico legível — é o que vai para o log."""
        if self.conforme:
            return "Layout conforme o padrão da V2."

        rotulo = f"Arquivo [{Path(caminho_arquivo).name}]" if caminho_arquivo else "Arquivo"
        linhas = [f"{rotulo} rejeitado: layout fora do padrão da V2."]

        if self.motivo:
            linhas.append(f"  {self.motivo}")

        for divergencia in self.divergencias:
            linhas.append(f"  {divergencia}")

        if self._parece_expectativa_vivo():
            linhas.append(f"  {_DIAGNOSTICO_EXPECTATIVA_VIVO}")

        return "\n".join(linhas)

    def _parece_expectativa_vivo(self) -> bool:
        indices = {divergencia.indice for divergencia in self.divergencias}
        return _ASSINATURA_EXPECTATIVA_VIVO.issubset(indices)

    def diagnostico(self) -> Diagnostico:
        """A recusa na forma comum — ver `comum/dominio/diagnostico_de_recusa.py`."""
        return Diagnostico(
            total_colunas=self.total_colunas,
            motivo=self.motivo,
            divergencias=list(self.divergencias),
        )


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------
def validar_layout(
    df: pd.DataFrame,
    linhas_amostradas: int = LINHAS_AMOSTRADAS,
    fracao_minima_valida: float = FRACAO_MINIMA_VALIDA,
) -> ResultadoLayout:
    """
    Confere se o DataFrame tem o layout documentado na V2.

    Espera o DataFrame como ``carregar_dados`` o devolve: colunas posicionais,
    valores como texto, cabeçalho já removido.

    Args:
        df: Conteúdo do arquivo.
        linhas_amostradas: Quantas linhas avaliar por posição.
        fracao_minima_valida: Fração mínima de valores válidos para aceitar a
            posição. O default de 0,5 tolera linhas ruins isoladas sem tolerar
            um layout trocado.

    Returns:
        ``ResultadoLayout``. Use ``.mensagem(caminho)`` para o diagnóstico.
    """
    total_colunas = 0 if df is None else int(df.shape[1])

    if df is None or df.empty:
        return ResultadoLayout(
            conforme=False,
            total_colunas=total_colunas,
            motivo="arquivo vazio ou sem linhas de dados.",
        )

    if total_colunas < COLUNAS_MINIMAS:
        return ResultadoLayout(
            conforme=False,
            total_colunas=total_colunas,
            motivo=(
                f"esperadas ao menos {COLUNAS_MINIMAS} colunas, "
                f"encontradas {total_colunas}."
            ),
        )

    amostra = df.head(linhas_amostradas)
    divergencias: list[Divergencia] = []

    for coluna in LAYOUT_V2:
        if coluna.verificar is None:
            continue

        valores = amostra.iloc[:, coluna.indice]
        avaliados = 0
        validos = 0
        invalidos: list[str] = []

        for valor in valores:
            avaliados += 1
            if coluna.verificar(valor):
                validos += 1
            elif len(invalidos) < _EXEMPLOS_NO_DIAGNOSTICO:
                invalidos.append(_limpo(valor))

        if avaliados and (validos / avaliados) < fracao_minima_valida:
            divergencias.append(
                Divergencia(
                    indice=coluna.indice,
                    nome=coluna.nome,
                    esperado=coluna.descricao_do_esperado,
                    exemplos_encontrados=invalidos,
                    valores_validos=validos,
                    valores_avaliados=avaliados,
                )
            )

    return ResultadoLayout(
        conforme=not divergencias,
        total_colunas=total_colunas,
        divergencias=divergencias,
    )
