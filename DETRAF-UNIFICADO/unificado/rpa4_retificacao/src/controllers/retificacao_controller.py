"""Orquestração do RPA 4: detectar, e então retificar.

Mesma forma do controller do RPA 3 — o gate `roda(etapa)` para o `--etapa`, uma
seção de diagnóstico por etapa, e "pular com aviso" em vez de abortar.
"""

from __future__ import annotations

from comum.config import configuration
from comum.config.diagnostico_execucao import DiagnosticoInativo
from comum.config.logger_config import logger
from comum.dados.repositorio_tabelas import bd_tabelas
from comum.utils.decoradores import log_execucao
from src.services import deteccao_recuperacao as deteccao
from src.services.retificacao_agi import RetificacaoAgiService, ResultadoRetificacao


class RetificacaoController:
    """Do sinal no banco até o evento no AGI."""

    def __init__(self, repositorio=None, servico_agi=None):
        # Injetáveis para o teste poder exercitar o encadeamento sem AGI.
        self.repositorio = repositorio or bd_tabelas
        self._servico_agi = servico_agi

    @log_execucao
    def retificar(
        self, referencia=None, etapa=None, diagnostico=None
    ) -> list[ResultadoRetificacao]:
        """
        Executa as etapas pedidas e devolve um resultado por recuperação.

        Returns:
            Lista vazia quando não há recuperação no mês — que é o caso comum, e
            não é falha.
        """
        registro = diagnostico or DiagnosticoInativo()

        def roda(nome_etapa: str) -> bool:
            if etapa is None or etapa == nome_etapa:
                return True
            logger.info(f"[RPA 4] Etapa '{nome_etapa}' pulada por --etapa={etapa}.")
            registro.pular(nome_etapa, f"pulada por --etapa={etapa}")
            return False

        recuperacoes: list = []

        if roda("deteccao"):
            with registro.etapa("deteccao", {"referencia": referencia or "(ambiente)"}) as atual:
                recuperacoes = deteccao.detectar(self.repositorio, referencia)
                atual.produzido = [
                    f"{len(recuperacoes)} recuperação(ões) identificada(s)"
                ] + [item.descrever() for item in recuperacoes]

        if not recuperacoes:
            logger.info(
                "[RPA 4] Nada a retificar. Num mês sem recuperação este é o "
                "resultado certo, e não uma falha."
            )
            return []

        if not roda("retificacao"):
            return []

        # O kill-switch é conferido AQUI, e não dentro do laço: a decisão de não
        # tocar no AGI vale para a execução inteira, e o operador precisa vê-la
        # uma vez, não uma por processo.
        if not configuration.PERMITIR_ACESSO_AGI:
            logger.warning(
                f"[RPA 4] PERMITIR_ACESSO_AGI está desligado — as "
                f"{len(recuperacoes)} recuperação(ões) acima foram calculadas e "
                f"NÃO foram lançadas. É o modo de conferência."
            )
            registro.pular("retificacao", "PERMITIR_ACESSO_AGI desligado")
            return []

        return self._lancar(recuperacoes, registro)

    def _lancar(self, recuperacoes: list, registro) -> list[ResultadoRetificacao]:
        """Abre uma sessão do AGI e lança as recuperações, uma a uma."""
        servico = self._servico_agi or RetificacaoAgiService()
        resultados: list[ResultadoRetificacao] = []

        with registro.etapa("retificacao", {"processos": len(recuperacoes)}) as atual:
            servico.abrir_sessao()
            try:
                for recuperacao in recuperacoes:
                    resultado = servico.retificar(recuperacao)
                    resultados.append(resultado)

                    if not resultado.lancado:
                        continue

                    # Só depois do lançamento — e mesmo assim sem confirmação do
                    # AGI, que não devolve nenhuma. Ver `marcar_retificacao_no_agi`.
                    self.repositorio.marcar_retificacao_no_agi(
                        recuperacao.id_contestacao
                    )
            finally:
                servico.fechar_sessao()

            lancados = [item for item in resultados if item.lancado]
            atual.produzido = [
                f"{len(lancados)} de {len(recuperacoes)} recuperação(ões) lançada(s)"
            ] + [
                f"{item.recuperacao.descrever()} -> processo {item.id_processo}"
                for item in lancados
            ]

        return resultados
