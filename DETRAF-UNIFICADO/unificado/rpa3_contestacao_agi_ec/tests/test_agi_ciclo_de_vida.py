"""Abrir e fechar o Portal AIR — `AGI.inicializar` e `AGI.fechar`.

Escrito em 2026-08-06, depois de o `ensaiar_portal_agi.py` mostrar, contra o
aplicativo de verdade, duas coisas que nenhum teste cobria:

1. o `portal_air_vivo.exe` é um **lançador**: ele sobe o `adl.exe`, que fica com
   a janela, e sai com código 1 em menos de seis segundos;
2. `fechar()` só matava o `adl.exe`, então o lançador sobrevivia a cada
   execução.

O primeiro era grave: com um lançador que sai, o laço original de
`inicializar()` — ``while processo.poll() is not None`` — **não termina nunca**.
O RPA 3 travaria em silêncio no instante em que um kill-switch do AGI fosse
ligado. Estes testes fixam o comportamento corrigido.

Nada aqui abre processo de verdade: o `psutil` e o `subprocess` são
substituídos. O que se cobre é a **espera**, não o Adobe AIR.
"""

from __future__ import annotations

import pytest

from comum.config import configuration
from comum.integracoes import agi as agi_mod
from comum.integracoes.agi import AGI, AGIError


class _ProcessoFalso:
    def __init__(self, nome: str, pid: int = 1):
        self.info = {"name": nome}
        self.pid = pid


class TestNaoEntrarNoAmbienteErrado:
    """
    As duas proteções contra abrir produção achando que é homologação.

    Em 2026-08-06, com o cursor parado sobre o botão `PRODUÇÃO` — que o CSS do
    portal pinta de roxo no `:hover` —, a busca por `bnt_producao_ini.png` casou
    no botão `HOMOLOGAÇÃO`, e o robô abriu o ambiente errado sem nada acusar.
    """

    def test_o_cursor_e_afastado_antes_de_cada_busca(self, monkeypatch):
        """
        Um botão sob o mouse fica com a aparência de hover e não casa com a
        imagem — que foi capturada sem hover. Procurar sem afastar o cursor é
        procurar por algo que o próprio robô escondeu.
        """
        ordem: list[str] = []

        monkeypatch.setattr(agi_mod.pyautogui, "size", lambda: (1920, 1080))
        monkeypatch.setattr(
            agi_mod.pyautogui, "moveTo", lambda *a, **k: ordem.append("afastou")
        )
        monkeypatch.setattr(
            agi_mod.pyautogui,
            "locateOnScreen",
            lambda *a, **k: ordem.append("procurou") or "alvo",
        )
        monkeypatch.setattr(agi_mod.pyautogui, "click", lambda *a, **k: None)

        AGI()._click("qualquer.png")

        assert ordem[:2] == ["afastou", "procurou"]

    def test_o_botao_do_ambiente_usa_confianca_mais_alta_que_o_padrao(self):
        """
        Os dois botões só diferem na palavra. No 0.8 padrão, um casa no outro.

        ⛔ Subir a confiança é o oposto de baixá-la para o passo passar: é
        impedir que ele passe pelo lugar errado.
        """
        assert agi_mod.CONFIANCA_AMBIENTE > 0.8

    def test_janela_de_outro_ambiente_aborta_antes_de_tocar_no_agi(
        self, monkeypatch
    ):
        """
        A rede de segurança: o título da janela não é ambíguo.

        Se a navegação foi parar noutro ambiente, o robô para aqui — antes do
        ACESSAR, portanto antes de qualquer contato com o AGI.
        """
        monkeypatch.setattr(configuration, "AGI_AMBIENTE", "homologacao")
        monkeypatch.setattr(AGI, "_wait_appear", lambda *a, **k: True)
        monkeypatch.setattr(AGI, "_click", lambda *a, **k: True)
        monkeypatch.setattr(agi_mod.time, "sleep", lambda _: None)

        vistas = []

        def _aguardar(self, nome_janela, timeout=180):
            vistas.append(nome_janela)
            if nome_janela == "Portal Triad: Vivo":
                return
            raise AGIError(f"Janela '{nome_janela}' não apareceu.")

        monkeypatch.setattr(AGI, "aguardar_janela", _aguardar)

        with pytest.raises(AGIError, match="ambiente errado"):
            AGI().acessar_ambiente()

        assert vistas == ["Portal Triad: Vivo", "Portal Triad: Vivo - Homologação"]


@pytest.fixture()
def ambiente(monkeypatch, tmp_path):
    """Substitui processo, lançador e relógio. Devolve o controle dos três."""
    executavel = tmp_path / "portal_air_vivo.exe"
    executavel.write_text("", encoding="utf-8")
    monkeypatch.setattr(configuration, "DIRETORIO_AGI", executavel)

    estado = {"vivos": [], "lancado": 0, "mortos": []}

    monkeypatch.setattr(
        agi_mod.psutil,
        "process_iter",
        lambda *a, **k: [_ProcessoFalso(n) for n in estado["vivos"]],
    )
    monkeypatch.setattr(
        agi_mod.subprocess,
        "Popen",
        lambda *a, **k: estado.__setitem__("lancado", estado["lancado"] + 1),
    )
    monkeypatch.setattr(
        agi_mod.subprocess,
        "run",
        lambda cmd, **k: estado["mortos"].append(cmd[-1]),
    )
    # Sem isto cada teste custaria os segundos reais das esperas.
    monkeypatch.setattr(agi_mod.time, "sleep", lambda _: None)

    return estado


class TestInicializar:
    def test_nao_trava_quando_o_lancador_sai(self, ambiente):
        """
        A regressão que motivou o arquivo.

        O laço antigo esperava pelo `Popen` — que é o lançador, e morre. Este
        espera pelo processo que **aparece**. Se alguém voltar ao `poll()`, este
        teste não falha: ele **nunca termina**, e é assim que se percebe.
        """
        ambiente["vivos"] = ["adl.exe"]

        AGI().inicializar(timeout=5)

        assert ambiente["lancado"] == 1

    def test_levanta_quando_nenhum_processo_aparece(self, ambiente):
        """Aplicativo que não sobe tem de dar erro, não seguir para a janela."""
        ambiente["vivos"] = []

        with pytest.raises(AGIError, match="nenhum processo"):
            AGI().inicializar(timeout=3)

    def test_sem_diretorio_configurado_nem_lanca(self, monkeypatch, ambiente):
        monkeypatch.setattr(configuration, "DIRETORIO_AGI", None)

        with pytest.raises(AGIError, match="DIRETORIO_AGI"):
            AGI().inicializar(timeout=3)

        assert ambiente["lancado"] == 0


class TestFechar:
    def test_mata_os_dois_processos_do_portal(self, ambiente):
        """
        O lançador também tem de morrer.

        Até 2026-08-06 só o `adl.exe` era encerrado, e o `portal_air_vivo.exe`
        ficava — um a mais a cada execução do robô.
        """
        ambiente["vivos"] = ["adl.exe", "portal_air_vivo.exe"]

        # Depois do `taskkill`, a espera precisa ver a lista esvaziar.
        def _matar(cmd, **kwargs):
            ambiente["mortos"].append(cmd[-1])
            ambiente["vivos"] = [n for n in ambiente["vivos"] if n not in ambiente["mortos"]]

        agi_mod.subprocess.run = _matar

        AGI().fechar(timeout=3)

        assert sorted(ambiente["mortos"]) == ["adl.exe", "portal_air_vivo.exe"]

    def test_ignora_processo_alheio(self, ambiente):
        """`notepad.exe` não é do Portal AIR — nem se olha para ele."""
        ambiente["vivos"] = ["notepad.exe"]

        AGI().fechar(timeout=2)

        assert ambiente["mortos"] == []

    def test_avisa_quando_o_processo_sobrevive_ao_taskkill(self, ambiente, caplog):
        """
        Seguir calado seria pior: o `inicializar()` seguinte veria o processo
        antigo, concluiria que o AGI subiu, e iria para uma janela que fecha.
        """
        ambiente["vivos"] = ["adl.exe"]  # nunca sai da lista

        AGI().fechar(timeout=2)

        assert "ainda vivos" in caplog.text
