"""O que aconteceu em cada etapa, num `.txt` por execução (2026-08-07).

## Por que existe

Os três `main.py` tinham o mesmo `except Exception` cego: ele registrava
*"Execução interrompida por erro não tratado"* e devolvia 1, **sem saber em qual
etapa estava**. O que sobrava era o `.log` cronológico, com centenas de linhas
por rodada, misturando os passos de todas as operadoras.

Numa homologação manual — sem IA no ambiente, que é o caso — responder *"onde
parou, e por quê?"* virava leitura de log.

## O formato é para ser lido depois, por gente ou por máquina

Texto puro, seções delimitadas por `===`, sem depender de renderização. É o
arquivo que se manda para análise: ele carrega o ambiente, a sequência das
etapas, o que cada uma produziu e o erro **com traceback**.

## Grava sempre, inclusive quando dá tudo certo

A etapa que passou é contexto: sem ela não dá para saber se o erro é do passo ou
de algo que veio antes. E o modo de falha mais comum aqui é *"terminou bem sem
fazer nada"* — que não deixaria arquivo nenhum se só gravasse em erro.

## Não substitui o log, e não é o `relatorio_execucao.py`

O log continua sendo a testemunha completa. E o relatório de execução tem **uma
linha por operadora** e é do RPA 3; este tem **uma seção por etapa** e é dos
três. Eixos diferentes, arquivos diferentes.

## Falhar ao gravar não derruba a execução

Ele é gravado depois de o trabalho estar feito. Perdê-lo por falta de permissão
numa pasta seria trocar um inconveniente por um prejuízo.
"""

from __future__ import annotations

import socket
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from comum.config import configuration
from comum.config.logger_config import logger

#: Largura das réguas. Coincide com a do `verificar_ambiente.py`.
_REGUA = 70


@dataclass
class Etapa:
    """Uma etapa da execução, do começo ao desfecho."""

    nome: str
    #: O que a etapa recebeu — caminhos, parâmetros. É a primeira coisa que se
    #: quer conferir quando o resultado surpreende.
    entrada: dict[str, str] = field(default_factory=dict)
    #: O resumo que o próprio serviço monta (`ValidacaoDetrafsService.resumo` e
    #: irmãos) — as mesmas linhas que a pausa entre etapas mostra.
    produzido: list[str] = field(default_factory=list)
    situacao: str = "ok"
    duracao: float = 0.0
    motivo_do_pulo: str = ""
    erro: str = ""
    causa_provavel: str = ""
    correcao: str = ""
    traceback_completo: str = ""

    @property
    def falhou(self) -> bool:
        return self.situacao == "ERRO"


class DiagnosticoDeExecucao:
    """Acumula o que cada etapa fez e grava o `.txt` ao final."""

    def __init__(
        self,
        robo: str,
        referencia: str = "",
        parametros: list[str] | None = None,
    ) -> None:
        self.robo = robo
        self.referencia = referencia
        self.parametros = parametros or []
        self.inicio = datetime.now()
        self.etapas: list[Etapa] = []

    # ------------------------------------------------------------------

    @contextmanager
    def etapa(self, nome: str, entrada: dict[str, str] | None = None):
        """
        Envolve uma etapa: cronometra, e **captura a exceção com o nome dela**.

        É isto que resolve o `except` cego do `main.py`. A exceção é re-levantada
        — o fluxo de erro não muda —, mas antes fica registrado onde ela
        aconteceu, com o traceback e, quando é erro de banco, a tradução que o
        `diagnostico.explicar_erro_de_banco` já sabe fazer.

        Uso::

            with diagnostico.etapa("validacao", {"pasta": str(cfg.X)}) as etapa:
                etapa.produzido = Controller().validar()
        """
        atual = Etapa(nome=nome, entrada=dict(entrada or {}))
        self.etapas.append(atual)
        comecou = datetime.now()

        try:
            yield atual
        except Exception as erro:
            atual.situacao = "ERRO"
            atual.erro = f"{type(erro).__name__}: {erro}"
            atual.traceback_completo = traceback.format_exc()
            atual.causa_provavel, atual.correcao = self._traduzir(erro)
            raise
        finally:
            atual.duracao = (datetime.now() - comecou).total_seconds()

    def pular(self, nome: str, motivo: str) -> None:
        """
        Registra uma etapa que não rodou, **com o motivo**.

        Uma etapa ausente do diagnóstico é indistinguível de uma etapa que
        ninguém pensou em registrar. "Pulada por --etapa=validacao" é resposta;
        o silêncio não é.
        """
        self.etapas.append(
            Etapa(nome=nome, situacao="pulada", motivo_do_pulo=motivo)
        )

    @staticmethod
    def _traduzir(erro: Exception) -> tuple[str, str]:
        """
        Causa provável e correção, quando o erro é reconhecível.

        Reusa `diagnostico.explicar_erro_de_banco`, que já traduz os cinco erros
        do driver MySQL em causa + o que fazer — e que até aqui só o
        `verificar_ambiente.py` consumia.
        """
        try:
            from comum.config.diagnostico import explicar_erro_de_banco

            texto = str(erro).lower()
            pistas = ("mysql", "1045", "1049", "1146", "1054", "connect", "column")
            if any(pista in texto for pista in pistas):
                return explicar_erro_de_banco(erro)
        except Exception:  # pragma: no cover - a tradução é um extra
            pass
        return "", ""

    # ------------------------------------------------------------------

    @property
    def desfecho(self) -> str:
        falhas = [etapa for etapa in self.etapas if etapa.falhou]
        if falhas:
            indice = self.etapas.index(falhas[0]) + 1
            return f"ERRO na etapa {indice}/{len(self.etapas)} ({falhas[0].nome})"
        if not self.etapas:
            return "nenhuma etapa executada"
        if all(etapa.situacao == "pulada" for etapa in self.etapas):
            return "todas as etapas puladas"
        return "OK"

    def caminho(self) -> Path:
        """``logs/{host}/{robo}/diagnosticos/{carimbo}.txt``.

        Sob `RAIZ_LOGS` porque é da mesma natureza do log, e herda a organização
        por host que já existe. Um arquivo por execução: a comparação da
        homologação é rodada a rodada.
        """
        return (
            configuration.RAIZ_LOGS
            / socket.gethostname()
            / (self.robo or "comum")
            / "diagnosticos"
            / f"{self.inicio:%Y-%m-%d_%H-%M-%S}.txt"
        )

    def gravar(self) -> Path | None:
        """Grava o diagnóstico. Devolve `None` se não deu — nunca levanta."""
        destino = self.caminho()

        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(self.montar(), encoding="utf-8")
        except OSError as erro:
            logger.warning(
                f"[Diagnóstico] Não foi possível gravar [{destino}]: {erro}. "
                f"O log completo da execução continua disponível."
            )
            return None

        logger.info(f"[Diagnóstico] Etapas desta execução em [{destino}].")
        return destino

    # ------------------------------------------------------------------

    def montar(self) -> str:
        duracao = (datetime.now() - self.inicio).total_seconds()
        total = len(self.etapas)

        linhas = [
            "=" * _REGUA,
            "EXECUÇÃO",
            "=" * _REGUA,
            f"robô:       {self.robo}",
            f"referência: {self.referencia or '(mês corrente -1)'}",
            f"início:     {self.inicio:%Y-%m-%d %H:%M:%S}",
            f"duração:    {duracao:.1f}s",
            f"desfecho:   {self.desfecho}",
        ]
        linhas += [f"parâmetro:  {p}" for p in self.parametros]

        linhas += ["", "=" * _REGUA, "AMBIENTE", "=" * _REGUA]
        try:
            linhas += list(configuration.resumo_do_ambiente())
        except Exception as erro:  # pragma: no cover - o resumo é informativo
            linhas.append(f"(não foi possível montar o resumo: {erro})")

        for indice, etapa in enumerate(self.etapas, start=1):
            linhas += ["", "=" * _REGUA]
            linhas.append(
                f"ETAPA {indice}/{total}: {etapa.nome}"
                f"   [{etapa.situacao}]   {etapa.duracao:.1f}s"
            )
            linhas.append("=" * _REGUA)

            if etapa.motivo_do_pulo:
                linhas.append(f"motivo: {etapa.motivo_do_pulo}")

            if etapa.entrada:
                linhas.append("entrada:")
                linhas += [
                    f"  {chave} = {valor}" for chave, valor in etapa.entrada.items()
                ]

            if etapa.produzido:
                linhas.append("produziu:")
                linhas += [f"  {texto}" for texto in etapa.produzido]
            elif etapa.situacao == "ok":
                # Distingue "rodou e não produziu nada" de "não rodou". A
                # primeira é o modo de falha silencioso mais comum do projeto.
                linhas.append("produziu: (nada — a etapa rodou sem gerar resultado)")

            if etapa.falhou:
                linhas.append(f"erro: {etapa.erro}")
                if etapa.causa_provavel:
                    linhas.append(f"causa provável: {etapa.causa_provavel}")
                if etapa.correcao:
                    linhas.append(f"o que fazer: {etapa.correcao}")
                linhas.append("traceback:")
                linhas += [
                    f"  {linha}"
                    for linha in etapa.traceback_completo.rstrip().splitlines()
                ]

        linhas += [
            "",
            "=" * _REGUA,
            "LOG COMPLETO",
            "=" * _REGUA,
            str(configuration.RAIZ_LOGS),
            "",
            "Este arquivo é o resumo por etapa. O log tem a sequência completa,",
            "linha a linha, de tudo o que a execução fez.",
        ]
        return "\n".join(linhas) + "\n"


class DiagnosticoInativo:
    """
    Faz nada, com a mesma interface. Para quando não há diagnóstico.

    Evita espalhar `if diagnostico is not None` pelos três dispatchers — e, com
    isso, evita o caso em que alguém acrescenta uma etapa e esquece o `if`,
    deixando-a fora do arquivo sem ninguém notar.

    Serve também aos testes que exercitam o `run` sem querer arquivo nenhum.
    """

    @contextmanager
    def etapa(self, nome: str, entrada: dict[str, str] | None = None):
        yield Etapa(nome=nome)

    def pular(self, nome: str, motivo: str) -> None:
        return None

    def gravar(self) -> None:
        return None

    @property
    def desfecho(self) -> str:
        return "(sem diagnóstico)"
