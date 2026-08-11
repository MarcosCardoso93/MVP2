"""Integração com o AGI (Portal Triad) por automação de interface.

Origem: `projeto-7-epico-5-carga-agi/src/services/AGI/AGI_config.py`, que por sua
vez veio sem alteração do `RPA_DETRAF_RECEITA` (MVP1). Ver
`trabalho/inventarios/inventario-projeto-7.md` §5.

O AGI não tem API: tudo é feito abrindo o executável, procurando botões na tela
por comparação de imagem (`pyautogui`) e conversando com os diálogos nativos do
Windows (`pywinauto`). As imagens de referência ficam em `comum/view/imagens/`.

## Promovido para `comum/` em 2026-08-10

Ficou no RPA 3 até aqui por ser ocorrência **única** — falhava o critério C1, que
exige duas ocorrências reais em RPAs diferentes. O gatilho anotado na ficha era
"quando o Projeto 6 chegar"; ele chegou, o RPA 4 (HU-21) nasceu, e a HU-21 usa
este mesmo Portal noutra tela (`Contestação > Gerenciar`, ¶713).

A alternativa era copiar — e a segunda cópia de uma classificação é exatamente o
defeito **A4**, que este repositório já pagou duas vezes.

O que o RPA 4 acrescentou aqui está agrupado ao final da classe, sob o comentário
"Telas da HU-21": ele reusa `_click`, `_localizar`, `_wait_appear` e
`janela_salvar` sem duplicar nada.

## ⚠️ As imagens não foram validadas nesta VM

Os PNGs de `AGI_CONFIG/` e `AGI_Upload_Detraf/` vieram da máquina de **Receita**.
Resolução de tela, escala de DPI e tema do Windows mudam o pixel, e o
`locateOnScreen` compara pixel. Recaptura pode ser necessária na VM de Despesa —
ver `comum/view/imagens/AGI_Upload_Detraf/LEIA-ME_VALIDACAO.md`.

## O que mudou na migração

- `print()` → `logger`, para que a falha típica ("não achei o botão") apareça no
  arquivo de log com o nome da imagem procurada;
- caminhos das imagens deixam de vir de variáveis de ambiente e passam a ser
  resolvidos **relativos a este pacote** — são artefatos versionados junto com o
  código, não configuração de ambiente;
- `_click` devolve `bool` em vez da string `"Não encontrou a imagem"`, que os
  chamadores comparavam por igualdade de texto;
- `import easygui` e `import pandas` removidos: nenhum dos dois era usado (o
  único `easygui.msgbox` já estava comentado, para execução desassistida).

## Produção deixou de ser o único ambiente (2026-08-06)

`acessar_producao`/`login_producao` viraram `acessar_ambiente`/`login`, e o
ambiente passou a sair de `AGI_AMBIENTE`.

O aplicativo do AGI é o **Portal AIR da Triad**, e ao instalá-lo em
`unificado/aplicacao_agi/` apareceu o que o projeto não sabia: o portal abre
**dois** ambientes, produção e homologação, em hosts diferentes. Isso toca a
pendência **Q20**, registrada em vários pontos do repositório como *"não existe
ambiente de teste do AGI"* — existe um AGI de homologação; o que continua em
aberto é se ele tem dado de Despesa utilizável e se a credencial vale nele.

A imagem `bnt_homo_ini.png` já estava capturada em `AGI_CONFIG/`, sem nenhum
código que a usasse.

## O ciclo de vida do aplicativo estava errado (2026-08-06)

Achado ao rodar `ensaiar_portal_agi.py` contra o aplicativo de verdade — nenhum
teste alcançava isso, porque depende do comportamento do Adobe AIR.

O `portal_air_vivo.exe` é um **lançador**: sobe o `adl.exe`, que fica com a
janela, e sai com código 1. Daí duas correções, em `inicializar` e `fechar`:
o laço de espera não terminava nunca, e o lançador sobrevivia a cada execução.
Ver `tests/test_agi_ciclo_de_vida.py`.
"""

from __future__ import annotations

import os
import stat
import subprocess
import time
from pathlib import Path

import psutil
import pyautogui
import pygetwindow as gw
from pywinauto import Desktop

from comum.config import configuration
from comum.config.logger_config import logger

#: Raiz das imagens de referência, dentro do próprio pacote `comum`.
#:
#: `parents[1]` é `comum/` — a expressão não mudou na promoção de 2026-08-10
#: porque as imagens vieram junto, de `rpa3/src/view/` para `comum/view/`. Elas
#: são artefato versionado com o código, não configuração de ambiente.
RAIZ_IMAGENS = Path(__file__).resolve().parents[1] / "view" / "imagens"

_IMAGENS_CONFIG = RAIZ_IMAGENS / "AGI_CONFIG"

img_bnt_prod_ini = str(_IMAGENS_CONFIG / "bnt_producao_ini.png")
img_bnt_homo_ini = str(_IMAGENS_CONFIG / "bnt_homo_ini.png")
img_windows_login = str(_IMAGENS_CONFIG / "windows_login.png")
img_bnt_user = str(_IMAGENS_CONFIG / "bnt_user.png")
img_bnt_entrar = str(_IMAGENS_CONFIG / "bnt_entrar.png")
#: A **logo** do card do AGI — não o botão ACESSAR.
#:
#: Os sete cards da página do ambiente têm o mesmo botão `ACESSAR`, e o card
#: vizinho é o do **AGI Garliavo**, com a mesma moldura e uma logo parecida.
#: Medido em 2026-08-06: um recorte do card inteiro casa nos **dois** a partir de
#: 0.95, porque a logo é uma fração pequena de uma área quase toda uniforme.
#: Fechando o recorte na logo, o que distingue passa a dominar — e aí ela é
#: única em 0.95.
#:
#: O botão é alcançado por deslocamento a partir daqui; ver
#: `DESLOCAMENTO_LOGO_ATE_ACESSAR`.
img_card_agi = str(_IMAGENS_CONFIG / "card_agi.png")
img_bnt_menu_relatorio = str(_IMAGENS_CONFIG / "bnt_menu_relatorio.png")
img_bnt_submenu_detraf = str(_IMAGENS_CONFIG / "bnt_submenu_detraf.png")
img_bnt_submenu_receita_despesas = str(
    _IMAGENS_CONFIG / "bnt_submenu_receita_despesas.png"
)
img_bnt_filtro = str(_IMAGENS_CONFIG / "bnt_filtro.png")
img_bnt_periodo_referencia = str(_IMAGENS_CONFIG / "bnt_periodo_referencia.png")
img_drop_box_export = str(_IMAGENS_CONFIG / "drop_box_export.png")
img_submenu_export_para_csv = str(_IMAGENS_CONFIG / "submenu_export_para_csv.png")
img_bnt_ok_export = str(_IMAGENS_CONFIG / "bnt_ok_upload.png")
img_bnt_filtrar = str(_IMAGENS_CONFIG / "bnt_filtrar.png")

# ---------------------------------------------------------------------------
# Contestação > Gerenciar — a tela da HU-21 (RPA 4), ¶713
#
# ⚠️ Estes PNGs são **recortes de um print de documentação**, não capturas ao
# vivo na VM. O `locateOnScreen` compara pixel: escala de DPI, tema e resolução
# mudam o resultado. Ver `AGI_Contestacao_Gerenciar/MANIFESTO_IMAGENS.md`, que
# traz o status de cada um e o histórico das três viradas de estratégia.
# ---------------------------------------------------------------------------
_IMAGENS_CONTESTACAO = RAIZ_IMAGENS / "AGI_Contestacao_Gerenciar"

img_bnt_contestacao = str(_IMAGENS_CONTESTACAO / "bnt_contestacao.png")
img_bnt_submenu_gerenciar = str(_IMAGENS_CONTESTACAO / "bnt_submenu_gerenciar.png")
img_campo_periodo = str(_IMAGENS_CONTESTACAO / "campo_periodo.png")
img_bnt_buscar_contestacao = str(_IMAGENS_CONTESTACAO / "bnt_buscar_contestacao.png")
img_bnt_pesquisar = str(_IMAGENS_CONTESTACAO / "bnt_pesquisar.png")
img_cabecalho_id_processo = str(_IMAGENS_CONTESTACAO / "cabecalho_id_processo.png")
img_bnt_mais_adicionar = str(_IMAGENS_CONTESTACAO / "bnt_mais_adicionar.png")
img_campo_tipo_evento = str(_IMAGENS_CONTESTACAO / "campo_tipo_evento.png")
img_bnt_salvar_evento = str(_IMAGENS_CONTESTACAO / "bnt_salvar_evento.png")

#: Quantos pixels abaixo do **cabeçalho** da coluna "ID Processo" fica a 1ª linha
#: de dado.
#:
#: O cabeçalho é texto fixo, então serve de âncora estável; a linha de dado muda
#: a cada busca. Substituiu um recorte de 25×24px quase todo de cor sólida, que
#: casava em qualquer lugar da grid.
#:
#: ⚠️ **Não calibrado nesta VM.** O código de origem usa 72 e o manifesto dele
#: diz 68 — a divergência é de lá. Confirmar na primeira execução assistida.
OFFSET_CABECALHO_ATE_PRIMEIRA_LINHA: int = 72

#: Quantas vezes descer no dropdown "Tipo Evento" até "Recuperação".
#:
#: ⚠️ **Contado ao vivo em 2026-08-06, na origem, e não reconferido aqui.** É
#: acoplamento à ordem da lista: se o AGI acrescentar um tipo antes de
#: "Recuperação", o robô lança o evento errado — e o evento é irreversível.
#: A imagem `opcao_recuperacao.png` existe e seria o caminho robusto; a origem a
#: capturou e não chegou a usar.
DESCIDAS_ATE_RECUPERACAO: int = 12


#: Botão do portal e título da janela que ele abre, por ambiente.
#:
#: Os dois andam **juntos** de propósito. O título é o que `aguardar_janela`
#: espera depois do clique; separados, dá para clicar em Homologação e ficar
#: esperando a janela de Produção — que nunca vem, e o robô só descobre no
#: timeout.
#:
#: O terceiro item é o host que aparece no título do diálogo nativo de upload,
#: que **não** mora aqui: vem do `.env` (`AGI_JANELA_HOST_PRODUCAO` e
#: `AGI_JANELA_HOST_HOMOLOGACAO`), porque IP é dado de infraestrutura e muda sem
#: que o código mude. Para referência, o que o portal aponta hoje:
#: produção `10.238.6.120:7010/Agi/`, homologação `10.129.178.159:7010/Agi/`.
#: Confiança exigida para o botão do ambiente — acima do 0.8 padrão.
#:
#: Não é zelo: os dois botões do portal são a **mesma** moldura, do mesmo
#: tamanho, com o mesmo fundo, e diferem só na palavra. Medido em 2026-08-06,
#: cada imagem casa no seu botão com 0.99, e o botão errado só entra em 0.8 ou
#: menos. O 0.9 fica no meio dessa folga.
#:
#: ⛔ Isto é o oposto de "baixar o confidence para o passo passar" — é subi-lo
#: para que ele não passe pelo lugar errado.
CONFIANCA_AMBIENTE: float = 0.9

#: Confiança exigida para a logo do card do AGI. Abaixo disto ela casa também no
#: card do **AGI Garliavo**, que é outro sistema — medido em 2026-08-06: única em
#: 0.95 e em 0.99; em 0.90 já aparecem as duas.
CONFIANCA_CARD_AGI: float = 0.95

#: Quantos pixels abaixo do **centro da logo** fica o centro do botão `ACESSAR`.
#:
#: Medido na tela: logo em y 396..534 (centro 465), botão em y 605..648 (centro
#: 627). Daí os 162.
#:
#: Substituiu um `moveRel(0, 75)` cego, que descia 75px a partir de onde o clique
#: anterior tivesse caído. Aqui o ponto é calculado a partir da **caixa
#: localizada**, então ou a logo foi encontrada e o clique é derivado dela, ou
#: nada é clicado.
DESLOCAMENTO_LOGO_ATE_ACESSAR: int = 162

_TELA_POR_AMBIENTE: dict[str, tuple[str, str]] = {
    "producao": (img_bnt_prod_ini, "Portal Triad: Vivo - Produção"),
    "homologacao": (img_bnt_homo_ini, "Portal Triad: Vivo - Homologação"),
}


#: Os processos que compõem o Portal AIR, em minúsculas.
#:
#: São **dois**, e a distinção custou uma correção: o `portal_air_vivo.exe` é só
#: um lançador — ele sobe o runtime do Adobe AIR (`adl.exe`), que é quem fica com
#: a janela, e sai. Ver `inicializar` e `fechar`.
NOMES_DE_PROCESSO_AGI: tuple[str, ...] = ("adl.exe", "portal_air_vivo.exe")


def processos_do_agi() -> list[str]:
    """Nomes dos processos do Portal AIR vivos agora."""
    vivos = []
    for proc in psutil.process_iter(["name"]):
        nome = (proc.info["name"] or "").lower()
        if nome in NOMES_DE_PROCESSO_AGI:
            vivos.append(nome)
    return sorted(set(vivos))


def afastar_o_mouse() -> None:
    """
    Tira o cursor de cima de qualquer botão, antes de procurar imagens.

    🔴 **Sem isto o robô entra no ambiente errado.** O CSS do portal tem::

        .homo:hover { background: rgba(102,0,153,.75); color: #ffffff; }

    O botão sob o mouse fica **roxo com texto branco** — o inverso exato do que
    as imagens capturam (fundo claro, texto roxo). E a automação **deixa o
    cursor onde clicou**: o botão que ela acabou de usar fica irreconhecível.

    O que isso causou, observado em 2026-08-06: com o `PRODUÇÃO` escondido pelo
    hover, a busca por `bnt_producao_ini.png` casou no botão **`HOMOLOGAÇÃO`** —
    os dois têm a mesma moldura, o mesmo tamanho e o mesmo fundo, e só o texto
    difere. O robô pediu produção e abriu homologação. Na direção contrária, o
    estrago é maior.

    A borda esquerda da tela não tem canto quente do Windows nem janela do
    portal, que nasce a partir de x=130.
    """
    largura, altura = pyautogui.size()
    pyautogui.moveTo(1, altura // 2, duration=0)


class AGIError(RuntimeError):
    """Falha ao operar o AGI."""


class AGI:
    """Sessão do AGI: abre o executável, faz login e navega."""

    # ------------------------------------------------------------------
    # Primitivas de automação por imagem
    # ------------------------------------------------------------------

    def _click(self, img: str, tentativa: int = 3, confidence: float = 0.8) -> bool:
        """
        Procura `img` na tela e clica. Devolve `False` se não encontrar.

        O original devolvia a string ``"Não encontrou a imagem"``, e os chamadores
        comparavam por igualdade de texto — um `!=` escrito errado passava
        despercebido e o robô seguia clicando no lugar errado.

        O cursor é afastado antes da busca — ver `afastar_o_mouse`, que explica
        por que isso não é zelo, e sim a diferença entre abrir produção e abrir
        homologação.
        """
        alvo = self._localizar(img, tentativa, confidence)
        if alvo is None:
            return False

        pyautogui.click(alvo)
        return True

    def _localizar(self, img: str, tentativa: int = 3, confidence: float = 0.8):
        """
        Devolve a caixa em que `img` está na tela, ou `None`.

        Separado do `_click` para quem precisa da **geometria**, e não do
        clique: é assim que o card do AGI leva ao seu botão `ACESSAR` sem
        deslocamento cego — ver `acessar_ambiente`.
        """
        afastar_o_mouse()

        for _ in range(tentativa):
            try:
                alvo = pyautogui.locateOnScreen(img, confidence=confidence)
                if alvo is not None:
                    return alvo
            except Exception:
                pass
            time.sleep(1)

        logger.warning(f"[AGI] Imagem não encontrada na tela: [{img}].")
        return None

    def _wait_appear(self, img: str, timeout: int = 180, confidence: float = 0.8) -> bool:
        """
        Espera `img` aparecer na tela, por até `timeout` segundos.

        Afasta o cursor a cada tentativa: um botão sob o mouse fica com a
        aparência de hover e nunca aparece — ver `afastar_o_mouse`.
        """
        for segundo in range(timeout):
            afastar_o_mouse()
            try:
                if pyautogui.locateOnScreen(img, confidence=confidence):
                    return True
            except Exception:
                pass
            time.sleep(1)
            if segundo and segundo % 30 == 0:
                logger.debug(f"[AGI] Aguardando [{img}] há {segundo}s...")

        logger.warning(f"[AGI] Imagem [{img}] não apareceu em {timeout}s.")
        return False

    # ------------------------------------------------------------------
    # Ciclo de vida do aplicativo
    # ------------------------------------------------------------------

    def inicializar(self, timeout: int = 60) -> None:
        """
        Fecha instâncias abertas e sobe o AGI a partir de `DIRETORIO_AGI`.

        ## O executável é um LANÇADOR, e isso muda a espera

        Observado em 2026-08-06 com `ensaiar_portal_agi.py`: o
        `portal_air_vivo.exe` sobe o runtime do Adobe AIR (`adl.exe`) e **sai**,
        com código 1, em menos de seis segundos. Quem fica com a janela é o
        `adl.exe`.

        O código original esperava assim::

            while processo.poll() is not None:
                time.sleep(1)

        `poll()` devolve `None` enquanto o processo vive, então esse laço só
        **começa** a rodar depois que o processo morre — e um processo morto
        nunca volta a devolver `None`. Com um lançador que sai, ele **não termina
        nunca**: o RPA 3 travaria, sem erro e sem log, no instante em que algum
        kill-switch do AGI fosse ligado.

        Esperar pelo processo certo — o que aparece — resolve os dois lados: não
        trava, e ainda dá erro explícito se o aplicativo não subir.
        """
        self.fechar()

        if not configuration.DIRETORIO_AGI:
            raise AGIError("DIRETORIO_AGI não configurado — não há executável do AGI.")

        caminho = str(configuration.DIRETORIO_AGI)
        try:
            # O `cwd` importa: o executável do AGI procura arquivos ao lado de si.
            subprocess.Popen([caminho], cwd=os.path.dirname(caminho))
        except OSError as exc:
            raise AGIError(f"Falha ao abrir o AGI em [{caminho}]: {exc}") from exc

        for _ in range(timeout):
            if processos_do_agi():
                break
            time.sleep(1)
        else:
            raise AGIError(
                f"O AGI foi lançado de [{caminho}], mas nenhum processo "
                f"{list(NOMES_DE_PROCESSO_AGI)} apareceu em {timeout}s."
            )

        logger.info(f"[AGI] Aplicativo aberto a partir de [{caminho}].")
        time.sleep(2)

    def fechar(self, timeout: int = 10) -> None:
        """
        Encerra os processos do Portal AIR em execução.

        ⚠️ Mata **os dois**. Até 2026-08-06 matava só o `adl.exe`, herdado do
        código de Receita — e o `ensaiar_portal_agi.py` mostrou que o
        `portal_air_vivo.exe` sobrevivia a cada execução, acumulando processos.
        """
        encerrados = []
        for proc in psutil.process_iter(["name"]):
            nome = (proc.info["name"] or "").lower()
            if nome in NOMES_DE_PROCESSO_AGI:
                logger.info(f"[AGI] Encerrando processo em execução: {nome} (pid {proc.pid}).")
                try:
                    subprocess.run(["taskkill", "/f", "/im", nome], check=False)
                    encerrados.append(nome)
                except OSError as exc:
                    logger.warning(f"[AGI] Falha ao encerrar '{nome}': {exc}")

        if not encerrados:
            return

        # O `taskkill` devolve antes de o Windows soltar o processo. Sem esta
        # espera, o `inicializar()` que vem logo em seguida vê o processo ANTIGO
        # ainda na lista, conclui que o AGI subiu e segue para uma janela que
        # está fechando.
        for _ in range(timeout):
            if not processos_do_agi():
                return
            time.sleep(1)

        logger.warning(
            f"[AGI] Processos do Portal AIR ainda vivos após {timeout}s: "
            f"{', '.join(processos_do_agi())}."
        )

    def aguardar_janela(self, nome_janela: str, timeout: int = 180) -> None:
        """Espera a janela existir e a traz para frente, maximizada."""
        for _ in range(timeout):
            janelas = gw.getWindowsWithTitle(nome_janela)
            if janelas:
                break
            time.sleep(1)
        else:
            raise AGIError(f"Janela '{nome_janela}' não apareceu em {timeout}s.")

        janela = janelas[0]
        if not janela.isActive:
            # A dança restore/minimize/restore é herdada do original: no Windows,
            # `activate()` sozinho falha quando a janela nasce em segundo plano.
            janela.restore()
            time.sleep(1)
            janela.minimize()
            time.sleep(0.5)
            janela.restore()
            time.sleep(0.5)
            janela.activate()
            janela.maximize()

    # ------------------------------------------------------------------
    # Acesso e login
    # ------------------------------------------------------------------

    def _tela(self) -> tuple[str, str]:
        """Botão e título do ambiente configurado, ou `AGIError` se inválido."""
        try:
            return _TELA_POR_AMBIENTE[configuration.AGI_AMBIENTE]
        except KeyError:
            raise AGIError(
                f"AGI_AMBIENTE inválido: [{configuration.AGI_AMBIENTE}]. "
                f"Use um de {sorted(_TELA_POR_AMBIENTE)}."
            ) from None

    def acessar_ambiente(self) -> None:
        """
        Do portal inicial até a tela do AGI do ambiente configurado.

        Era `acessar_producao`, e clicava sempre no botão de produção. O portal
        oferece os dois ambientes, e a imagem do de homologação já estava
        capturada e sem uso — ver `_TELA_POR_AMBIENTE`.
        """
        botao, titulo = self._tela()

        self.aguardar_janela("Portal Triad: Vivo")
        time.sleep(1)

        self._wait_appear(botao, confidence=CONFIANCA_AMBIENTE)
        self._click(botao, confidence=CONFIANCA_AMBIENTE)

        # 🔴 Confere em QUAL ambiente entrou, antes de seguir.
        #
        # Os dois botões do portal têm a mesma moldura, o mesmo tamanho e o mesmo
        # fundo — só o texto difere. Em 2026-08-06 a busca por `PRODUÇÃO` casou no
        # `HOMOLOGAÇÃO`, e o robô abriu o ambiente errado sem nada acusar. A
        # confiança mais alta acima torna isso improvável; esta conferência torna
        # o dano impossível, porque o título da janela não é ambíguo.
        #
        # Timeout curto de propósito: a página é local e troca em um piscar. Se
        # não trocou, foi para outro lugar — esperar mais não conserta.
        try:
            self.aguardar_janela(titulo, timeout=30)
        except AGIError as exc:
            raise AGIError(
                f"Pedi o ambiente '{configuration.AGI_AMBIENTE}' e a janela "
                f"'{titulo}' não apareceu — o robô pode ter entrado no ambiente "
                f"errado. Nada foi feito no AGI. ({exc})"
            ) from exc

        # O card do AGI ocupa a mesma posição (`box-3`) e usa a mesma logo nas
        # duas páginas do portal, então a imagem serve para ambas.
        self._wait_appear(img_card_agi, confidence=CONFIANCA_CARD_AGI)
        alvo = self._localizar(img_card_agi, confidence=CONFIANCA_CARD_AGI)
        if alvo is None:
            raise AGIError(
                "O card do AGI não foi encontrado na tela do ambiente "
                f"'{configuration.AGI_AMBIENTE}'. Nada foi clicado."
            )

        # O `ACESSAR` fica abaixo da logo, a uma distância fixa pelo CSS. Como o
        # ponto sai da caixa localizada, ou a logo do AGI foi reconhecida e o
        # clique cai no botão dela, ou não há clique nenhum — nunca no `ACESSAR`
        # do card ao lado, que abre o AGI Garliavo.
        pyautogui.click(
            alvo.left + alvo.width // 2,
            alvo.top + alvo.height // 2 + DESLOCAMENTO_LOGO_ATE_ACESSAR,
        )

    def login(self) -> None:
        """Preenche usuário e senha na janela de login do Windows."""
        if not configuration.USUARIO_AGI or not configuration.SENHA_AGI:
            raise AGIError(
                "Credencial do AGI ausente — defina RPA_DETRAF_DESPESA_AGI_USER e "
                "RPA_DETRAF_DESPESA_AGI_PASSWORD no ambiente."
            )

        _, titulo = self._tela()
        self.aguardar_janela(titulo)

        self._wait_appear(img_windows_login)
        self._click(img_windows_login)
        self._wait_appear(img_bnt_user)
        self._click(img_bnt_user)
        pyautogui.typewrite(configuration.USUARIO_AGI)

        self._wait_appear(img_windows_login)
        self._click(img_windows_login)
        pyautogui.moveRel(175, 50)
        pyautogui.click()
        pyautogui.typewrite(configuration.SENHA_AGI)

        self._click(img_bnt_entrar)
        logger.info("[AGI] Login enviado.")

    # ------------------------------------------------------------------
    # Diálogos nativos do Windows
    # ------------------------------------------------------------------

    def janela_salvar(self, caminho: str | Path, nome_janela: str) -> None:
        """
        Preenche o diálogo nativo de arquivo (salvar/abrir) com `caminho`.

        `nome_janela` é uma **regex** de título: o AGI traduz o título conforme o
        idioma da VM, e a de Despesa está em inglês
        (``"Select file for upload by {host}"``).
        """
        dialogo = Desktop(backend="win32").window(title_re=nome_janela)
        dialogo.wait("visible", timeout=220)
        dialogo.Edit.type_keys(str(caminho), with_spaces=True)
        pyautogui.press("Enter")

        confirmacao = Desktop(backend="win32").window(
            title_re="(Confirm Save As|Confirmar Salvar como)"
        )
        if confirmacao.exists(timeout=2):
            logger.info(f"[AGI] Arquivo já existia, será substituído: [{caminho}].")
            confirmacao.type_keys("%s")  # Alt+S = Sim/Save

    # ------------------------------------------------------------------
    # Relatórios
    # ------------------------------------------------------------------

    def _selecionar_periodo(self) -> None:
        """Navega o filtro de período de referência só pelo teclado."""
        pyautogui.click()
        for tecla in ("down", "tab", "down", "tab"):
            pyautogui.press(tecla)
        for _ in range(3):
            pyautogui.hotkey("Shift", "TAB")
        pyautogui.press("SPACE")

    def baixar_remessa(self, destino: Path) -> Path:
        """
        Exporta o relatório Detraf de Receita/Despesas para CSV em `destino`.

        É a primeira metade da **HU-20**, no próprio RPA 3 — a V2 (¶691) diz *"O
        robô entra no AGI e acessa Relatórios >> Detraf >> Receitas e Despesas"*, e
        o ¶698 completa: *"é possível extrair os dados da tela"*.

        ⚠️ Este docstring dizia *"quem vai usá-lo é o RPA 4"*. Estava errado: a
        HU-21, que é do RPA 4, usa `Contestação > Gerenciar` (¶713), não esta tela.
        O método ficou órfão até o Projeto 6 chegar — agora
        `verificacao_relatorio.py` o chama.
        """
        while True:
            self._wait_appear(img_bnt_menu_relatorio, timeout=30)
            self._click(img_bnt_menu_relatorio)
            pyautogui.moveRel(0, 70)
            self._wait_appear(img_bnt_submenu_detraf, timeout=15)
            if self._click(img_bnt_submenu_detraf):
                break

        self._wait_appear(img_bnt_submenu_receita_despesas, timeout=30)
        self._click(img_bnt_submenu_receita_despesas)

        self._wait_appear(img_bnt_filtro)
        time.sleep(1)
        self._click(img_bnt_filtro)

        self._wait_appear(img_bnt_periodo_referencia)
        self._click(img_bnt_periodo_referencia)
        pyautogui.moveRel(10, 0)
        self._selecionar_periodo()

        while True:
            self._wait_appear(img_drop_box_export, timeout=10)
            self._click(img_drop_box_export)
            time.sleep(2)
            pyautogui.moveRel(0, -20)
            if self._click(img_submenu_export_para_csv):
                break

        destino = Path(destino)
        # O idioma do diálogo muda conforme a VM — já foi visto em inglês e em
        # português. A regex aceita as duas em vez de depender do idioma da
        # máquina. (Correção que veio do Projeto 6, de quem rodou em produção.)
        self.janela_salvar(
            destino,
            nome_janela=(
                "(Select location for download by|Selecionar local para download de) "
                f"{configuration.AGI_JANELA_HOST}"
            ),
        )

        _corrigir_aspas_impares(destino)
        logger.info(f"[AGI] Remessa baixada em [{destino}].")
        return destino

    # ------------------------------------------------------------------
    # Telas da HU-21 — Contestação > Gerenciar (RPA 4)
    #
    # A estratégia é a decidida com a cliente em 2026-08-03, e não a óbvia:
    # NÃO se filtra por operadora no modal (o dropdown dela não é alcançável por
    # UIA — ver `teste_uia_operadora.py` na origem, que falhou por timeout).
    # Filtra-se só por período, exporta-se a grid para CSV, e a linha certa é
    # achada no CSV cruzando EOT + Per. Ref. + Per. Traf. + Valor.
    # ------------------------------------------------------------------

    def _janela_uia(self):
        """
        A janela do AGI pelo backend UIA, para os dois controles que têm árvore.

        O título real termina em `": "` — com dois-pontos e espaço —, mas o resto
        do módulo trabalha com o título sem eles. A regex aceita as duas formas
        em vez de fixar uma e quebrar quando o AGI mudar o sufixo.
        """
        _, titulo = self._tela()
        return Desktop(backend="uia").window(title_re=f"{titulo}.*")

    def abrir_contestacao_gerenciar(self, timeout: int = 30) -> None:
        """
        Navega até `Contestação > Gerenciar`.

        O menu só abre o submenu depois de o mouse descer sobre ele, daí o
        `moveRel`. O laço da origem era `while True` sem saída: se a imagem nunca
        casasse — e ela é recorte de print, não captura da VM —, o robô ficava
        preso para sempre, sem log. Aqui ele desiste e diz o que procurava.
        """
        for _ in range(3):
            if not self._wait_appear(img_bnt_contestacao, timeout=timeout):
                continue
            self._click(img_bnt_contestacao)
            pyautogui.moveRel(0, 70)
            if self._wait_appear(img_bnt_submenu_gerenciar, timeout=15) and self._click(
                img_bnt_submenu_gerenciar
            ):
                logger.info("[AGI] Tela Contestação > Gerenciar aberta.")
                return

        raise AGIError(
            "Não foi possível abrir Contestação > Gerenciar: o menu não "
            f"respondeu em 3 tentativas. Confira [{img_bnt_contestacao}] e "
            f"[{img_bnt_submenu_gerenciar}] com `verificar_imagens_agi.py`."
        )

    def filtrar_por_periodo(self) -> None:
        """
        Abre o Filtro e escolhe o período de referência.

        ⚠️ **Não calibrado nesta VM.** "Período Referência" é um intervalo de/até,
        e a origem seleciona pelo teclado assumindo que o **primeiro item da
        lista é o mês anterior** — duas vezes marcado "PRECISA CONFIRMAR NA VM"
        lá. Se a ordem do dropdown for outra, o filtro traz o período errado; o
        cruzamento no CSV então não acha a linha e o robô **para**, em vez de
        retificar errado. É a rede de segurança dessa incerteza.
        """
        self._wait_appear(img_bnt_filtro)
        time.sleep(1)
        self._click(img_bnt_filtro)

        if not self._wait_appear(img_campo_periodo, timeout=30):
            raise AGIError(
                "O modal de Filtro não abriu (campo 'Período Referência' não "
                "apareceu). Nada foi filtrado."
            )
        self._click(img_campo_periodo)

        # "de": primeiro item da lista. "até": idem, no segundo campo.
        for tecla in ("down", "enter", "tab", "down", "enter"):
            pyautogui.press(tecla)

        self._wait_appear(img_bnt_buscar_contestacao, timeout=15)
        self._click(img_bnt_buscar_contestacao, confidence=0.9)
        logger.info("[AGI] Grid filtrada por período.")

    def exportar_grid_csv(self, destino: Path, timeout: int = 30) -> Path:
        """
        Exporta a grid de contestações para CSV em `destino`.

        Apaga o arquivo anterior **antes** de exportar: sem isso, uma exportação
        que falhe deixa o robô lendo o CSV da volta passada e retificando o
        processo de outra operadora. A proteção veio da origem e é mantida.
        """
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.unlink(missing_ok=True)

        for _ in range(3):
            if not self._wait_appear(img_drop_box_export, timeout=timeout):
                continue
            self._click(img_drop_box_export)
            time.sleep(2)
            pyautogui.moveRel(0, -20)
            if self._click(img_submenu_export_para_csv):
                break
        else:
            raise AGIError(
                "Não foi possível acionar a exportação da grid em 3 tentativas. "
                "Nada foi exportado."
            )

        self.janela_salvar(
            destino,
            nome_janela=(
                "(Select location for download by|Selecionar local para download de) "
                f"{configuration.AGI_JANELA_HOST}"
            ),
        )

        if not destino.exists():
            raise AGIError(
                f"A exportação terminou mas [{destino}] não existe. O diálogo de "
                f"salvar pode ter sido recusado."
            )

        _corrigir_aspas_impares(destino)
        logger.info(f"[AGI] Grid de contestações exportada em [{destino}].")
        return destino

    def selecionar_processo(self, id_processo: str | int) -> None:
        """
        Digita o número do processo e pesquisa.

        Híbrido de propósito: o campo é alcançável por UIA, o botão **não**.
        Medido na origem (`teste_botao_pesquisar.py`): `Pesquisar` não aparece na
        árvore de controles, diferente de `Filtro`, `Exportar` e `Operação Lote`.
        Por isso o campo vai por pywinauto e o botão por imagem.
        """
        campo = self._janela_uia().child_window(
            title="Número Processo : ", control_type="Edit"
        )
        campo.wait("visible", timeout=30)
        campo.set_focus()
        campo.type_keys("^a{DEL}")
        campo.type_keys(str(id_processo))

        if not self._click(img_bnt_pesquisar):
            raise AGIError(
                f"Botão 'Pesquisar' não encontrado — o processo "
                f"[{id_processo}] não foi pesquisado."
            )
        logger.info(f"[AGI] Processo [{id_processo}] pesquisado.")

    def abrir_processo_selecionado(self) -> None:
        """
        Abre a 1ª linha da grid, ancorando no cabeçalho da coluna "ID Processo".

        O duplo-clique é dado num deslocamento fixo abaixo do cabeçalho — ver
        `OFFSET_CABECALHO_ATE_PRIMEIRA_LINHA`, que **não está calibrado**.
        """
        caixa = self._localizar(img_cabecalho_id_processo, tentativa=5)
        if caixa is None:
            raise AGIError(
                "Cabeçalho 'ID Processo' não encontrado — sem âncora, não dá "
                "para saber onde está a linha de dado. Nada foi aberto."
            )

        centro = pyautogui.center(caixa)
        pyautogui.doubleClick(centro.x, centro.y + OFFSET_CABECALHO_ATE_PRIMEIRA_LINHA)
        time.sleep(1)

    def validar_processo_selecionado(self, id_processo: str | int) -> None:
        """
        Confere que o processo aberto é o esperado. **Levanta** se não for.

        🔴 É a guarda que a cliente reforçou na reunião de 2026-08-03, e a razão
        de ela existir é simples: o passo seguinte lança um evento
        **irreversível**. Sem esta conferência, um duplo-clique que caiu na linha
        errada — e o deslocamento que o leva até lá não está calibrado — lança
        Recuperação no processo de outra operadora.
        """
        campo = self._janela_uia().child_window(
            title_re=r"Processo Selecionado: .*", control_type="Text"
        )
        campo.wait("visible", timeout=30)
        encontrado = campo.window_text().strip()
        esperado = f"Processo Selecionado: {id_processo}".strip()

        if encontrado != esperado:
            raise AGIError(
                f"Processo selecionado errado: esperava [{esperado}], achei "
                f"[{encontrado}]. Abortando ANTES de lançar o evento."
            )
        logger.info(f"[AGI] Processo [{id_processo}] confirmado na tela.")

    def _clicar_botao_mais_a_direita(self, img: str, confidence: float = 0.8) -> None:
        """
        Clica na ocorrência mais à direita de `img`.

        A tela tem **dois** botões "+ Adicionar" idênticos, e o do painel de
        Eventos é o da direita. Sem este critério, o clique cai no outro painel.
        """
        afastar_o_mouse()
        posicoes = list(pyautogui.locateAllOnScreen(img, confidence=confidence))
        if not posicoes:
            raise AGIError(f"Nenhuma ocorrência de [{img}] na tela.")

        pyautogui.click(pyautogui.center(max(posicoes, key=lambda caixa: caixa.left)))

    def lancar_evento_recuperacao(self, valores: dict) -> None:
        """
        Lança o evento "Recuperação" com os valores calculados. **Irreversível.**

        `valores` vem de `comum.dominio.retificacao.calcular_valores_evento`.

        ⚠️ O preenchimento é por TAB cego, contando colunas da grid de Eventos —
        ordem real: Tipo Evento, Data, Duração, Vlr Líquido, PIS/Cofins, ICMS,
        IBS Est., IBS Mun., CBS, Vlr Bruto Negociado. A contagem veio da origem,
        marcada "PRECISA CONFIRMAR NA VM". Um campo a mais ou a menos no AGI
        desloca **todos** os valores.
        """
        self._clicar_botao_mais_a_direita(img_bnt_mais_adicionar)
        time.sleep(1)

        if not self._click(img_campo_tipo_evento):
            raise AGIError(
                "Campo 'Tipo Evento' não encontrado — a linha de evento pode "
                "não ter sido criada. Nada foi preenchido."
            )
        for _ in range(DESCIDAS_ATE_RECUPERACAO):
            pyautogui.press("down")
        pyautogui.press("enter")

        for _ in range(6):  # até "Duração"
            pyautogui.press("tab")
        pyautogui.typewrite(str(valores["duracao"]), interval=0.15)
        pyautogui.press("tab")
        pyautogui.typewrite(str(valores["valor_liquido"]), interval=0.15)
        pyautogui.press("tab")
        pyautogui.typewrite(str(valores["valor_pis_cofins"]), interval=0.15)
        for _ in range(5):  # pula ICMS, IBS Est., IBS Mun., CBS
            pyautogui.press("tab")
        pyautogui.typewrite(str(valores["valor_bruto_negociado"]), interval=0.15)

        self._clicar_botao_mais_a_direita(img_bnt_salvar_evento)
        logger.warning(
            "[AGI] Evento de Recuperação salvo — duração "
            f"{valores['duracao']}, bruto {valores['valor_bruto_negociado']}. "
            "NADA confirma a persistência: o AGI não devolve sinal, e reexecutar "
            "duplica o evento."
        )


def _corrigir_aspas_impares(caminho: Path, tentativas: int = 5) -> None:
    """
    Remove as aspas de linhas com número ímpar delas.

    O export do AGI ocasionalmente fecha uma aspa e não abre a outra, e aí o
    parser de CSV engole as linhas seguintes como se fossem continuação do campo.

    **A reescrita tem retry** porque, logo após o download, o arquivo pode estar
    retido — antivírus escaneando o arquivo novo, ou o próprio processo que salvou
    ainda sem liberar o handle. Isso derruba o `open("w")` com `PermissionError`
    de forma **transitória**: esperar dois segundos resolve.

    O `chmod` cobre o outro caso, em que o download vem marcado como somente
    leitura. Sem os dois, a HU-20 falharia depois de já ter aberto o AGI, logado e
    baixado — o pedaço caro do fluxo. Correção herdada do Projeto 6.
    """
    with open(caminho, "r", encoding="utf-8") as arquivo:
        linhas = [
            linha.replace('"', "") if linha.count('"') % 2 else linha
            for linha in arquivo
        ]

    for tentativa in range(1, tentativas + 1):
        try:
            os.chmod(caminho, stat.S_IWRITE)
            with open(caminho, "w", encoding="utf-8") as arquivo:
                arquivo.writelines(linhas)
            return
        except PermissionError as erro:
            logger.warning(
                f"[AGI] [{caminho.name}] ainda bloqueado para escrita "
                f"(tentativa {tentativa}/{tentativas}): {erro}"
            )
            time.sleep(2)

    raise AGIError(
        f"Não foi possível reescrever [{caminho}] após {tentativas} tentativas. "
        f"O arquivo foi baixado, mas continua retido por outro processo."
    )
