"""O encadeamento do RPA 4, com o AGI dublado.

O que se trava aqui é a ordem em que as coisas acontecem — e ela importa porque o
passo do meio é irreversível: só se marca a linha **depois** de lançar, e não se
abre o AGI quando o kill-switch está desligado.
"""

from __future__ import annotations

import pytest

from src.controllers.retificacao_controller import RetificacaoController
from src.services.retificacao_agi import ResultadoRetificacao


class AgiDublado:
    """Registra o que foi pedido, sem tocar em tela nenhuma."""

    def __init__(self, falhar_em: set[int] | None = None):
        self.falhar_em = falhar_em or set()
        self.sessoes_abertas = 0
        self.sessoes_fechadas = 0
        self.lancados: list[int] = []

    def abrir_sessao(self):
        self.sessoes_abertas += 1

    def fechar_sessao(self):
        self.sessoes_fechadas += 1

    def retificar(self, recuperacao):
        if recuperacao.id_contestacao in self.falhar_em:
            return ResultadoRetificacao(
                recuperacao=recuperacao, erro="processo não encontrado no CSV"
            )
        self.lancados.append(recuperacao.id_contestacao)
        return ResultadoRetificacao(
            recuperacao=recuperacao, id_processo="590969", lancado=True
        )


@pytest.fixture
def ligar_agi(monkeypatch):
    """Liga `PERMITIR_ACESSO_AGI` só para o teste que precisa dele."""
    from comum.config import configuration

    monkeypatch.setattr(configuration, "PERMITIR_ACESSO_AGI", True)
    # O controller lê o módulo de configuração importado por ele.
    import src.controllers.retificacao_controller as controlador

    monkeypatch.setattr(controlador.configuration, "PERMITIR_ACESSO_AGI", True)


class TestKillSwitch:
    def test_desligado_nao_abre_o_agi(self, repo_tabelas, monkeypatch):
        """
        🔴 O que está atrás do interruptor é irreversível. Desligado, o robô
        calcula e mostra — e não toca no AGI.
        """
        import src.controllers.retificacao_controller as controlador

        monkeypatch.setattr(controlador.configuration, "PERMITIR_ACESSO_AGI", False)
        agi = AgiDublado()

        resultados = RetificacaoController(
            repositorio=repo_tabelas, servico_agi=agi
        ).retificar(referencia="202507")

        assert resultados == []
        assert agi.sessoes_abertas == 0
        assert agi.lancados == []

    def test_desligado_diz_no_log_quantas_deixou_de_lancar(
        self, repo_tabelas, monkeypatch, caplog
    ):
        import src.controllers.retificacao_controller as controlador

        monkeypatch.setattr(controlador.configuration, "PERMITIR_ACESSO_AGI", False)

        RetificacaoController(
            repositorio=repo_tabelas, servico_agi=AgiDublado()
        ).retificar(referencia="202507")

        assert "PERMITIR_ACESSO_AGI" in caplog.text


class TestFluxoCompleto:
    def test_lanca_e_marca_cada_recuperacao(self, repo_tabelas, ligar_agi):
        agi = AgiDublado()

        resultados = RetificacaoController(
            repositorio=repo_tabelas, servico_agi=agi
        ).retificar(referencia="202507")

        assert sorted(agi.lancados) == [1, 2]
        assert all(item.lancado for item in resultados)
        # Marcadas: a segunda detecção não as traz mais.
        from src.services import deteccao_recuperacao as deteccao

        assert deteccao.detectar(repo_tabelas, referencia="202507") == []

    def test_o_que_falha_nao_e_marcado(self, repo_tabelas, ligar_agi):
        """
        Uma recuperação que não foi lançada precisa voltar na próxima execução —
        marcá-la seria perdê-la em silêncio.
        """
        from src.services import deteccao_recuperacao as deteccao

        agi = AgiDublado(falhar_em={2})

        RetificacaoController(repositorio=repo_tabelas, servico_agi=agi).retificar(
            referencia="202507"
        )

        pendentes = {
            item.id_contestacao
            for item in deteccao.detectar(repo_tabelas, referencia="202507")
        }
        assert pendentes == {2}

    def test_uma_falha_nao_derruba_as_demais(self, repo_tabelas, ligar_agi):
        agi = AgiDublado(falhar_em={1})

        resultados = RetificacaoController(
            repositorio=repo_tabelas, servico_agi=agi
        ).retificar(referencia="202507")

        assert agi.lancados == [2]
        assert len(resultados) == 2

    def test_a_sessao_do_agi_e_fechada_mesmo_com_erro(self, repo_tabelas, ligar_agi):
        agi = AgiDublado(falhar_em={1, 2})

        RetificacaoController(repositorio=repo_tabelas, servico_agi=agi).retificar(
            referencia="202507"
        )

        assert agi.sessoes_abertas == 1
        assert agi.sessoes_fechadas == 1

    def test_mes_sem_recuperacao_nao_abre_o_agi(self, repo_tabelas, ligar_agi):
        """Abrir o Portal para descobrir que não há nada é custo e risco à toa."""
        agi = AgiDublado()

        resultados = RetificacaoController(
            repositorio=repo_tabelas, servico_agi=agi
        ).retificar(referencia="209912")

        assert resultados == []
        assert agi.sessoes_abertas == 0


class TestRecorteDeEtapa:
    def test_so_deteccao_nao_abre_o_agi(self, repo_tabelas, ligar_agi):
        agi = AgiDublado()

        resultados = RetificacaoController(
            repositorio=repo_tabelas, servico_agi=agi
        ).retificar(referencia="202507", etapa="deteccao")

        assert resultados == []
        assert agi.sessoes_abertas == 0

    def test_so_retificacao_nao_tem_o_que_lancar(self, repo_tabelas, ligar_agi):
        """
        A retificação depende da detecção: pular a primeira deixa a segunda sem
        entrada. Termina limpo, sem abrir o AGI.
        """
        agi = AgiDublado()

        resultados = RetificacaoController(
            repositorio=repo_tabelas, servico_agi=agi
        ).retificar(referencia="202507", etapa="retificacao")

        assert resultados == []
        assert agi.sessoes_abertas == 0
