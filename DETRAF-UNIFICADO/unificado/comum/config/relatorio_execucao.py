"""Relatório do que aconteceu numa execução (2026-08-06).

## Por que existe

Homologar é comparar **esperado × obtido**. O obtido estava só no log — que é
cronológico, tem centenas de linhas por rodada e mistura os passos de todas as
operadoras. Responder "a CLARO gerou o quê?" era filtrar texto.

Este módulo grava, ao fim de cada execução, um `.md` com uma tabela: uma linha
por operadora, o que saiu, o que foi pulado **e por quê**, o que deu erro. Mais o
cabeçalho que diz em que modo a rodada correu e quais efeitos externos estavam
ligados — porque a primeira pergunta sobre qualquer resultado estranho é essa.

## O log não sai

Isto é adicional. O log continua sendo a testemunha completa; o relatório é o
resumo que cabe numa tela.

## Falhar aqui não derruba a execução

O relatório é gravado depois de o trabalho estar feito. Perdê-lo por falta de
permissão numa pasta seria trocar um inconveniente por um prejuízo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from comum.config import configuration
from comum.config.logger_config import logger


@dataclass
class LinhaDeRelatorio:
    """O que aconteceu com um item — normalmente uma operadora."""

    item: str
    #: O que foi produzido: ``{"EXT": "sim", "cartas": "2"}``.
    produzidos: dict[str, str] = field(default_factory=dict)
    #: Etapas puladas, **com o motivo**. É a coluna mais consultada: quase toda
    #: dúvida de homologação é "por que isto não saiu?".
    pulos: list[str] = field(default_factory=list)
    erro: str | None = None

    @property
    def situacao(self) -> str:
        if self.erro:
            return "ERRO"
        if self.pulos and not self.produzidos:
            return "nada gerado"
        if self.pulos:
            return "parcial"
        return "ok"


class RelatorioExecucao:
    """Acumula o que aconteceu e grava o `.md` ao final."""

    def __init__(self, robo: str, referencia: str, parametros: list[str] | None = None):
        self.robo = robo
        self.referencia = referencia
        self.parametros = parametros or []
        self.inicio = datetime.now()
        self.linhas: list[LinhaDeRelatorio] = []
        self.observacoes: list[str] = []

    def acrescentar(self, linha: LinhaDeRelatorio) -> None:
        self.linhas.append(linha)

    def observar(self, texto: str) -> None:
        """Nota que vale para a execução inteira, não para um item."""
        self.observacoes.append(texto)

    # ------------------------------------------------------------------

    def caminho(self) -> Path:
        """
        ``logs/{host}/{robo}/execucoes/{carimbo}.md``.

        Fica sob `RAIZ_LOGS` porque é da mesma natureza do log — registro do que
        o robô fez — e herda a organização por host que já existe. Um `.md` por
        execução, e não um arquivo acumulado: a comparação da homologação é
        rodada a rodada.
        """
        import socket

        return (
            configuration.RAIZ_LOGS
            / socket.gethostname()
            / (self.robo or "comum")
            / "execucoes"
            / f"{self.inicio:%Y-%m-%d_%H-%M-%S}.md"
        )

    def gravar(self) -> Path | None:
        """Grava o relatório. Devolve `None` se não foi possível — nunca levanta."""
        destino = self.caminho()

        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(self._montar(), encoding="utf-8")
        except OSError as erro:
            logger.warning(
                f"[Relatório] Não foi possível gravar [{destino}]: {erro}. "
                f"O log completo da execução continua disponível."
            )
            return None

        logger.info(f"[Relatório] Resumo da execução em [{destino}].")
        return destino

    # ------------------------------------------------------------------

    def _montar(self) -> str:
        duracao = (datetime.now() - self.inicio).total_seconds()

        texto = [
            f"# {self.robo} — execução de {self.inicio:%Y-%m-%d %H:%M:%S}",
            "",
            f"**Referência:** {self.referencia}",
            f"**Duração:** {duracao:.0f}s",
            "",
            "## Ambiente",
            "",
        ]
        texto += [f"- {linha}" for linha in configuration.resumo_do_ambiente()]
        texto += [f"- {linha}" for linha in self.parametros]
        texto += ["", "## Resultado por operadora", ""]

        if not self.linhas:
            texto += ["Nenhuma operadora processada.", ""]
        else:
            colunas = sorted({chave for l in self.linhas for chave in l.produzidos})
            cabecalho = ["Operadora", "Situação"] + colunas + ["Pulos e erros"]
            texto += [
                "| " + " | ".join(cabecalho) + " |",
                "|" + "---|" * len(cabecalho),
            ]
            for linha in self.linhas:
                observacao = "; ".join(linha.pulos)
                if linha.erro:
                    observacao = f"**ERRO:** {linha.erro}" + (
                        f" — {observacao}" if observacao else ""
                    )
                texto.append(
                    "| "
                    + " | ".join(
                        [linha.item, linha.situacao]
                        + [linha.produzidos.get(coluna, "-") for coluna in colunas]
                        + [observacao or "-"]
                    )
                    + " |"
                )
            texto.append("")

        totais = {
            situacao: sum(1 for l in self.linhas if l.situacao == situacao)
            for situacao in ("ok", "parcial", "nada gerado", "ERRO")
        }
        texto += [
            "## Totais",
            "",
            "| Situação | Quantidade |",
            "|---|---|",
        ]
        texto += [f"| {nome} | {qtd} |" for nome, qtd in totais.items() if qtd]
        texto.append("")

        if self.observacoes:
            texto += ["## Observações", ""]
            texto += [f"- {obs}" for obs in self.observacoes]
            texto.append("")

        texto += [
            "---",
            "",
            "O log completo desta execução está em "
            f"`{configuration.RAIZ_LOGS}` — este relatório é o resumo.",
        ]
        return "\n".join(texto) + "\n"
