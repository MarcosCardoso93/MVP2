"""Parada interativa entre etapas (2026-08-06).

O risco desta funcionalidade não é ela não funcionar — é ela **escapar para
produção**. Um robô desassistido que abre caixa de diálogo trava para sempre, e a
caixa foi desenhada para esperar indefinidamente.

Por isso a maior parte destes testes é sobre os **travamentos**: as quatro
condições que precisam valer ao mesmo tempo para a pausa acontecer. Cada uma tem
o seu teste, porque cada uma sozinha é suficiente para evitar o desastre.

Nenhum teste abre janela — a exibição é injetada (`_mostrar`), e o próprio
`esta_habilitada` recusa parar sob pytest.
"""

from pathlib import Path

import pytest

from comum.utils import pausa


@pytest.fixture()
def sem_pytest(monkeypatch):
    """
    Finge que não estamos sob pytest, para testar as outras três guardas.

    Sem isto a guarda do pytest curto-circuita todas as demais, e elas nunca
    seriam exercitadas. Substitui a função, e não a variável de ambiente: o
    pytest **redefine** `PYTEST_CURRENT_TEST` a cada fase do teste, então apagar
    a variável numa fixture não tem efeito no corpo do teste.
    """
    monkeypatch.setattr(pausa, "_sob_pytest", lambda: False)


@pytest.fixture()
def com_sessao_grafica(monkeypatch):
    """A guarda de sessão gráfica sai do caminho — ela tem teste próprio."""
    monkeypatch.setattr(pausa, "_sem_sessao_grafica", lambda: False)


def _configurar(monkeypatch, env="dev", ligada=True):
    from comum.config import configuration

    monkeypatch.setattr(configuration, "ENV", env)
    monkeypatch.setattr(configuration, "PAUSA_ENTRE_ETAPAS", ligada)


class TestOsQuatroTravamentos:
    def test_sob_pytest_nunca_para(self, monkeypatch):
        """
        A guarda mais importante para o dia a dia: uma suíte que abre diálogo
        **trava o CI para sempre**. Ela vem antes de todas as outras.
        """
        _configurar(monkeypatch)
        monkeypatch.setattr(pausa, "_sem_sessao_grafica", lambda: False)

        habilitada, motivo = pausa.esta_habilitada()

        assert habilitada is False
        assert "pytest" in motivo

    def test_em_producao_nunca_para(self, monkeypatch, sem_pytest, com_sessao_grafica):
        """Regra dura: em `prod` não há caixa, nem com a flag ligada."""
        _configurar(monkeypatch, env="prod", ligada=True)

        habilitada, motivo = pausa.esta_habilitada()

        assert habilitada is False
        assert "prod" in motivo

    def test_dev_sozinho_nao_basta(self, monkeypatch, sem_pytest, com_sessao_grafica):
        """Estar em dev é comum; parar precisa ser pedido explicitamente."""
        _configurar(monkeypatch, env="dev", ligada=False)

        habilitada, motivo = pausa.esta_habilitada()

        assert habilitada is False
        assert "PAUSA_ENTRE_ETAPAS" in motivo

    def test_sem_sessao_grafica_nao_para(self, monkeypatch, sem_pytest):
        """
        É a guarda que protege o caso perigoso de verdade: tarefa agendada em
        sessão 0, sem desktop. Ela **falha continuando**, não travando — e não
        depende de ninguém ter configurado nada certo.
        """
        _configurar(monkeypatch)
        monkeypatch.setattr(pausa, "_sem_sessao_grafica", lambda: True)

        habilitada, motivo = pausa.esta_habilitada()

        assert habilitada is False
        assert "gráfica" in motivo

    def test_com_as_quatro_condicoes_para(
        self, monkeypatch, sem_pytest, com_sessao_grafica
    ):
        _configurar(monkeypatch)

        assert pausa.esta_habilitada() == (True, "")


class TestComportamento:
    def _pausar(self, monkeypatch, decisao, **kwargs):
        _configurar(monkeypatch)
        monkeypatch.setattr(pausa, "_sem_sessao_grafica", lambda: False)
        monkeypatch.setattr(pausa, "_sob_pytest", lambda: False)

        visto = {}

        def _mostrar(titulo, texto, caminho):
            visto["titulo"] = titulo
            visto["texto"] = texto
            visto["caminho"] = caminho
            return decisao

        pausa.pausar(_mostrar=_mostrar, **kwargs)
        return visto

    def test_continuar_deixa_a_execucao_seguir(self, monkeypatch):
        visto = self._pausar(
            monkeypatch, True, titulo="t", linhas=["linha"]
        )

        assert visto["titulo"] == "t"

    def test_cancelar_levanta_a_excecao(self, monkeypatch):
        """
        Cancelar tem que **interromper**, não só registrar. É o que faz a caixa
        valer: sem isso ela seria um aviso que ninguém pode acatar.
        """
        with pytest.raises(pausa.ExecucaoCanceladaPeloOperador, match="etapa 1"):
            self._pausar(monkeypatch, False, titulo="etapa 1", linhas=["x"])

    def test_desligada_nao_chama_a_caixa(self, monkeypatch):
        """Com a pausa desligada, o caminho de produção não muda em nada."""
        _configurar(monkeypatch, ligada=False)
        chamou = []

        pausa.pausar(
            titulo="t",
            linhas=["x"],
            _mostrar=lambda *a: chamou.append(True) or True,
        )

        assert chamou == []

    def test_o_conteudo_vai_para_o_log_mesmo_desligada(self, monkeypatch, caplog):
        """
        O resumo por etapa é útil de qualquer forma. Ele existir só quando
        alguém está olhando seria desperdiçar a informação.
        """
        _configurar(monkeypatch, ligada=False)

        with caplog.at_level("INFO"):
            pausa.pausar(titulo="etapa 1", linhas=["3 operadoras", "2 ok"])

        assert "3 operadoras" in caplog.text
        assert "etapa 1" in caplog.text


class TestTextoDaCaixa:
    def test_traz_a_proxima_etapa(self):
        """
        É a informação que decide o clique — sobretudo quando a próxima escreve
        para fora.
        """
        texto = pausa.montar_texto(
            ["ok"], proxima_etapa="carga no AGI — ESCREVE NO AGI", caminho=None
        )

        assert "PRÓXIMA ETAPA: carga no AGI — ESCREVE NO AGI" in texto

    def test_sem_proxima_diz_que_e_a_ultima(self):
        texto = pausa.montar_texto(["ok"], proxima_etapa=None, caminho=None)

        assert "última etapa" in texto

    def test_mostra_a_pasta_quando_ha_uma(self):
        texto = pausa.montar_texto(["ok"], None, Path("C:/operadoras"))

        assert "C:/operadoras" in texto or "C:\\operadoras" in texto

    def test_lista_vazia_nao_produz_caixa_vazia(self):
        assert "nada a relatar" in pausa.montar_texto([], None, None)


class TestBotaoAbrirPasta:
    def test_pasta_inexistente_nao_derruba(self, tmp_path, caplog):
        """Abrir a pasta é conveniência; falhar nisso não pode parar a rodada."""
        with caplog.at_level("WARNING"):
            pausa._abrir(tmp_path / "nao-existe")

        # Não levantou. No Windows o `startfile` falha e vira aviso; em outros
        # sistemas o `Popen` pode nem existir — os dois caminhos são tolerados.
        assert True
