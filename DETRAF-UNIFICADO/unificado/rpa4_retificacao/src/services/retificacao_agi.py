"""Passo 2 da HU-21 — lançar o evento de Recuperação no AGI.

Estratégia decidida com a cliente em 2026-08-03, e não a óbvia: **não** se filtra
por operadora no modal (o dropdown dela não é alcançável por UIA — a origem tentou
e registrou o timeout). Filtra-se por período, exporta-se a grid para CSV, e a
linha certa é achada no CSV cruzando EOT + Referência + Tráfego + Valor.

Por processo, a sequência é sempre a mesma:

    filtrar → exportar → achar no CSV → pesquisar → abrir → **validar** → lançar

A validação é o passo que não pode ser pulado: o que vem depois dela é
irreversível, e o duplo-clique que abre a linha usa um deslocamento em pixels que
não foi calibrado nesta VM.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from comum.config import configuration
from comum.config.logger_config import logger
from comum.dominio.retificacao import ProcessoNaoIdentificado, achar_id_processo
from comum.integracoes.agi import AGI, AGIError

#: Nome do CSV que a grid exporta a cada iteração.
NOME_CSV_EXPORTADO = "contestacao_exportada.csv"


@dataclass
class ResultadoRetificacao:
    """O que aconteceu com uma recuperação."""

    recuperacao: object
    id_processo: str | None = None
    erro: str | None = None
    lancado: bool = False


def pasta_de_trabalho() -> Path:
    """
    Onde o CSV exportado do AGI é gravado.

    Subpasta própria dentro de `DIRETORIO_TEMP`: aquela variável já é a área de
    trabalho da validação do RPA 2, e dois robôs gravando `contestacao_exportada.csv`
    no mesmo lugar é colisão esperando acontecer.
    """
    destino = Path(configuration.DIRETORIO_TEMP) / "rpa4_retificacao"
    destino.mkdir(parents=True, exist_ok=True)
    return destino


class RetificacaoAgiService:
    """Lança as recuperações no AGI, uma por uma."""

    def __init__(self, agi: AGI | None = None):
        self.agi = agi or AGI()
        self._sessao_aberta = False

    # ------------------------------------------------------------------

    def abrir_sessao(self) -> None:
        """Sobe o AGI, entra no ambiente e vai para Contestação > Gerenciar."""
        self.agi.inicializar()
        self.agi.acessar_ambiente()
        self.agi.login()
        self.agi.abrir_contestacao_gerenciar()
        self._sessao_aberta = True

    def fechar_sessao(self) -> None:
        if self._sessao_aberta:
            self.agi.fechar()
            self._sessao_aberta = False

    # ------------------------------------------------------------------

    def retificar(self, recuperacao) -> ResultadoRetificacao:
        """
        Lança uma recuperação. Não levanta: devolve o erro no resultado.

        Uma operadora que falha não pode derrubar as demais — o laço do
        controller segue, e o que falhou fica sem a marca, para ser tentado de
        novo na próxima execução.
        """
        resultado = ResultadoRetificacao(recuperacao=recuperacao)
        caminho_csv = pasta_de_trabalho() / NOME_CSV_EXPORTADO

        try:
            self.agi.filtrar_por_periodo()
            self.agi.exportar_grid_csv(caminho_csv)

            resultado.id_processo = achar_id_processo(
                caminho_csv=caminho_csv,
                eot_operadora=recuperacao.eot_operadora,
                periodo_referencia=recuperacao.periodo,
                periodo_trafego=recuperacao.periodo_trafego,
                valor_bruto=recuperacao.valor_bruto,
            )

            self.agi.selecionar_processo(resultado.id_processo)
            self.agi.abrir_processo_selecionado()
            # 🔴 Daqui para baixo é irreversível. Esta linha é o último ponto em
            # que dá para desistir sem consequência.
            self.agi.validar_processo_selecionado(resultado.id_processo)

            self.agi.lancar_evento_recuperacao(recuperacao.valores_evento)
            resultado.lancado = True

        except (AGIError, ProcessoNaoIdentificado) as erro:
            resultado.erro = str(erro)
            logger.error(
                f"[HU-21] {recuperacao.descrever()} — não retificada: {erro}"
            )
        except Exception as erro:  # noqa: BLE001 - um processo não derruba os outros
            resultado.erro = str(erro)
            logger.excecao(
                f"[HU-21] {recuperacao.descrever()} — erro inesperado: {erro}"
            )

        return resultado
