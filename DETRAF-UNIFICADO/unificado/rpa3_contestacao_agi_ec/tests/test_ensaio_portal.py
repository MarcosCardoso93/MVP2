"""O limite do `ensaiar_portal_agi.py` — provado, não prometido.

O ensaio existe para exercitar a metade do fluxo que **não** fala com o AGI:
abrir o Portal AIR e navegar até a tela do ambiente. A promessa dele é parar
**antes** do botão ACESSAR e nunca fazer login.

Promessa em docstring não impede ninguém de acrescentar um passo a mais depois.
Estes testes impedem.

Os testes de `etapa_processo` são de lógica pura, com o `Popen` e a listagem de
processos substituídos: o que se cobre é o **diagnóstico** — "o processo saiu,
logo `inicializar()` travaria" e "o processo vivo não é o que `fechar()` mata" —,
não o comportamento do Adobe AIR, que só a execução real mostra.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import ensaiar_portal_agi as ensaio
from comum.integracoes.agi import _TELA_POR_AMBIENTE, img_card_agi

#: Tudo que toca o AGI de verdade. Se um destes for chamado, o ensaio deixou de
#: ser offline — e passou a poder logar em produção sem ninguém ter pedido.
METODOS_PROIBIDOS = {
    "login",
    "janela_salvar",
    "baixar_remessa",
    "acessar_ambiente",  # ele inclui o clique no ACESSAR; o ensaio para antes
}


class _CaixaFalsa:
    """O que o `locateOnScreen` devolveria: uma caixa na tela."""

    def __init__(self, left=100, top=200, width=140, height=139):
        self.left, self.top = left, top
        self.width, self.height = width, height


class _PortalProibido:
    """Dublê do `AGI`: só o que o ensaio pode usar existe; o resto levanta."""

    def __init__(self, achou: bool = True):
        self._achou = achou
        self.cliques: list[str] = []
        self.localizados: list[str] = []
        self.janelas: list[str] = []
        self.fechou = False

    def _click(self, img, **kwargs) -> bool:
        self.cliques.append(img)
        return self._achou

    def _localizar(self, img, **kwargs):
        """Localizar **não** é clicar — é a distinção que mantém o ensaio seguro."""
        self.localizados.append(img)
        return _CaixaFalsa() if self._achou else None

    def aguardar_janela(self, nome_janela: str, **kwargs) -> None:
        self.janelas.append(nome_janela)

    def fechar(self) -> None:
        self.fechou = True

    def __getattr__(self, nome):
        def _explodir(*args, **kwargs):
            raise AssertionError(f"O ensaio tocou no AGI: chamou '{nome}'.")

        return _explodir


class TestOLimiteDoEnsaio:
    """A parte que não pode regredir: o ensaio não toca no AGI."""

    def test_nenhum_metodo_que_toca_o_agi_e_chamado(self):
        """
        Varre o módulo pela árvore sintática, não por texto.

        A docstring do ensaio fala de `login()` e dos diálogos o tempo todo —
        procurar por texto acusaria a própria documentação.
        """
        arvore = ast.parse(
            Path(ensaio.__file__).read_text(encoding="utf-8")
        )
        chamados = {
            no.func.attr
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
        }

        assert not (chamados & METODOS_PROIBIDOS), (
            f"O ensaio passou a chamar {sorted(chamados & METODOS_PROIBIDOS)}. "
            f"Ele precisa continuar parando antes do ACESSAR."
        )

    @pytest.mark.parametrize("ambiente", sorted(_TELA_POR_AMBIENTE))
    def test_o_card_do_agi_e_procurado_mas_nunca_clicado(self, ambiente, monkeypatch):
        """
        A distinção que mantém o ensaio offline.

        Clicar no ACESSAR abriria o AGI de verdade — e, sem acesso de rede, uma
        página que não carrega, onde qualquer clique seguinte cai às cegas.
        """
        monkeypatch.setattr(ensaio, "esperar_a_pagina_pintar", lambda *a, **k: True)

        agi = _PortalProibido()
        procurados: list[Path] = []

        def _procurar(caminho: Path):
            procurados.append(caminho)
            return 0.95

        resultado = ensaio.etapa_navegacao(agi, ambiente, _procurar)

        assert Path(img_card_agi) in procurados, "não chegou a procurá-lo"
        assert img_card_agi not in agi.cliques, "CLICOU no card do AGI"
        assert img_card_agi in agi.localizados, "não mediu onde o clique cairia"
        assert resultado["acessar"] == 0.95

    def test_calcula_onde_o_acessar_seria_clicado(self, monkeypatch):
        """
        O ensaio precisa medir o ponto — é o que prova que o deslocamento até o
        `ACESSAR` não caiu no vazio, sem clicar para descobrir.
        """
        from comum.integracoes.agi import DESLOCAMENTO_LOGO_ATE_ACESSAR

        monkeypatch.setattr(ensaio, "esperar_a_pagina_pintar", lambda *a, **k: True)

        caixa = _CaixaFalsa()
        resultado = ensaio.etapa_navegacao(_PortalProibido(), "producao", lambda _: 0.9)

        assert resultado["alvo_do_clique"] == (
            caixa.left + caixa.width // 2,
            caixa.top + caixa.height // 2 + DESLOCAMENTO_LOGO_ATE_ACESSAR,
        )

    def test_clica_no_botao_do_ambiente_e_espera_a_janela_dele(self, monkeypatch):
        monkeypatch.setattr(ensaio, "esperar_a_pagina_pintar", lambda *a, **k: True)

        agi = _PortalProibido()
        botao, titulo = _TELA_POR_AMBIENTE["homologacao"]

        resultado = ensaio.etapa_navegacao(agi, "homologacao", lambda _: 0.9)

        assert agi.cliques == [botao]
        assert agi.janelas == [titulo]
        assert resultado["abriu"] is True

    def test_botao_nao_encontrado_nao_procura_o_card(self, monkeypatch):
        """Sem o clique não há tela nova — procurar ali seria olhar a errada."""
        monkeypatch.setattr(ensaio, "esperar_a_pagina_pintar", lambda *a, **k: True)

        agi = _PortalProibido(achou=False)
        procurados = []

        resultado = ensaio.etapa_navegacao(
            agi, "producao", lambda c: procurados.append(c)
        )

        assert resultado["clicou"] is False
        assert resultado["acessar"] is None
        assert resultado["alvo_do_clique"] is None
        assert procurados == []
        assert agi.janelas == [], "esperou uma janela que não foi aberta"


class TestDiagnosticoDoProcesso:
    """O que a etapa 1 conclui a partir do que observa."""

    @staticmethod
    def _observar(monkeypatch, *, codigo, vivos):
        class _PopenFalso:
            def poll(self):
                return codigo

        monkeypatch.setattr(
            ensaio.subprocess, "Popen", lambda *a, **k: _PopenFalso()
        )
        monkeypatch.setattr(ensaio, "_processos_do_portal", lambda: vivos)
        return ensaio.etapa_processo(Path("qualquer.exe"), segundos=0)

    def test_processo_vivo_significa_que_inicializar_nao_trava(self, monkeypatch):
        """`poll()` devolve `None` enquanto vive — o laço não chega a rodar."""
        resultado = self._observar(
            monkeypatch, codigo=None, vivos=["adl.exe", "portal_air_vivo.exe"]
        )

        assert resultado["codigo_de_saida"] is None

    def test_processo_que_saiu_denuncia_o_laco_de_inicializar(self, monkeypatch):
        """
        `while processo.poll() is not None` só roda depois que o processo morre
        — e, morto, ele nunca mais devolve `None`. O laço não termina.
        """
        resultado = self._observar(monkeypatch, codigo=0, vivos=["adl.exe"])

        assert resultado["codigo_de_saida"] == 0

    def test_fechar_cobre_os_dois_processos_do_portal(self, monkeypatch):
        resultado = self._observar(
            monkeypatch, codigo=None, vivos=["adl.exe", "portal_air_vivo.exe"]
        )

        assert resultado["fechar_funciona"] is True
        assert resultado["nao_cobertos"] == []

    def test_processo_desconhecido_e_denunciado(self, monkeypatch):
        """
        A razão de o ensaio varrer por fragmento, e não pela lista do código.

        Foi assim que o `portal_air_vivo.exe` apareceu em 2026-08-06: `fechar()`
        só conhecia o `adl.exe`. Se o aplicativo mudar de novo, é este teste que
        garante que o ensaio vai notar em vez de repetir a crença do código.
        """
        resultado = self._observar(
            monkeypatch, codigo=None, vivos=["adl.exe", "adl_outro_qualquer.exe"]
        )

        assert resultado["fechar_funciona"] is False
        assert resultado["nao_cobertos"] == ["adl_outro_qualquer.exe"]
