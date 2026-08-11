"""O que um arquivo recusado precisa dizer sobre si — forma única (2026-08-06).

Duas coisas recusam um Detraf, e elas reprovam por razões diferentes:

- ``validar_layout`` — a **forma**: "este arquivo não é o arquivo que eu
  esperava". Produz divergências por posição;
- ``ValidadorColunas`` — as **regras**: "é um Detraf, mas com valor fora da
  regra". Produz motivos por coluna.

Quem grava o `_RECUSADO.md` e quem monta o corpo do e-mail não deveriam precisar
saber de qual das duas o veredito veio. Este módulo é a forma comum.

Ele existe como conversão **explícita** e não como coincidência de atributos: até
2026-08-06 o `registrar_recusa` funcionava por *duck typing* sobre o
``ResultadoLayout``, e bastaria alguém renomear um campo lá para o diagnóstico
sumir sem nenhum teste reclamar.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Diagnostico:
    """A recusa numa forma só, venha ela do layout ou das regras de coluna."""

    #: Quantas colunas o arquivo tinha. `0` quando não deu para ler.
    total_colunas: int = 0

    #: Explicação de uma linha, quando existe ("arquivo vazio ou sem linhas").
    motivo: str = ""

    #: Divergências por posição — só o layout as produz.
    divergencias: list = field(default_factory=list)

    #: Motivos por regra de coluna, em português, prontos para leitura externa.
    motivos_por_regra: list[str] = field(default_factory=list)

    def motivos(self) -> list[str]:
        """Tudo o que se pode dizer à operadora, das duas origens juntas."""
        linhas = [str(divergencia) for divergencia in self.divergencias]
        linhas.extend(self.motivos_por_regra)
        if not linhas and self.motivo:
            linhas.append(self.motivo)
        return linhas
