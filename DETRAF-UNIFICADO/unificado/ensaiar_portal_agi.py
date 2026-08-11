"""Ensaia a metade do fluxo do AGI que **não depende de rede** (2026-08-06).

## Por que existe

O fluxo do RPA 3 contra o AGI tem duas metades, e só a segunda precisa de rede::

    inicializar() ──► acessar_ambiente() ──┊──► login() ──► menus ──► upload
    └──── Portal AIR, HTML LOCAL ─────────┘┊    └──── AGI no navegador ────┘
                                    (botão ACESSAR)

O Portal AIR é um aplicativo **local**: abrir o executável, esperar a janela e
clicar em Produção/Homologação não fala com servidor nenhum. Só o clique em
ACESSAR é que abre o AGI no navegador.

Enquanto o acesso ao AGI não existe — hoje `10.238.6.120:7010` e
`10.129.178.159:7010` não respondem desta máquina —, esta metade dá para
exercitar de verdade. É o que este comando faz.

## 🔒 O limite, que é a razão de ele existir

**Ele para ANTES do botão ACESSAR, e nunca chama `login()`.**

O `bnt_acessar_agi.png` é apenas **procurado**, nunca clicado. Clicá-lo abriria o
navegador num host que não responde — e logo depois viria o `moveRel(0, 75)` +
`click()` às cegas de `acessar_ambiente()`, que numa página que não carregou
acerta qualquer coisa que esteja ali.

`tests/test_ensaio_portal.py` prova esse limite com um dublê que levanta ao
primeiro toque no que é proibido.

## O que ele responde

Três coisas que nenhum teste automatizado alcança, porque dependem do
comportamento real do aplicativo nesta máquina:

1. **Quais processos o aplicativo deixa vivos**, e se `AGI.fechar()` cobre todos.
   Foi assim que se descobriu, em 2026-08-06, que o `portal_air_vivo.exe` é só um
   **lançador**: ele sobe o `adl.exe`, que fica com a janela, e sai com código 1.
   `fechar()` só matava o `adl.exe`, e o lançador se acumulava a cada execução.
2. **Que o `inicializar()` corrigido continua correto.** O laço original
   (``while processo.poll() is not None``) nunca terminava com um lançador que
   sai — o RPA 3 travaria em silêncio. Hoje ele espera pelo processo que
   *aparece*; o ensaio confirma que algum aparece.

   A observação é feita **por fora** do `inicializar()`, com amostragem por
   tempo: assim o ensaio diagnostica a espera sem depender dela.
3. **Se as três imagens do portal casam nesta tela** — `bnt_producao_ini`,
   `bnt_homo_ini` e `bnt_acessar_agi`. As outras 27 estão dentro do AGI e
   continuam sem como ser conferidas.

⚠️ `bnt_homo_ini.png` nunca foi exercitada por código nenhum: estava capturada em
`AGI_CONFIG/` e sem uso até `AGI_AMBIENTE` existir.

## ⚠️ O Bootstrap vem de um CDN externo

As três páginas do portal carregam o CSS de `stackpath.bootstrapcdn.com`. Com o
CDN fora do ar ou bloqueado, elas renderizam só com o `portal.css` local — com
aparência **diferente** daquela em que as imagens foram capturadas. Por isso o
ensaio registra se o CDN respondeu: se as imagens casarem aqui e falharem na VM,
é a primeira hipótese a testar.

Uso::

    python ensaiar_portal_agi.py                        # usa AGI_AMBIENTE do .env
    python ensaiar_portal_agi.py --ambiente homologacao # força o outro
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
_RAIZ_RPA3 = RAIZ / "rpa3_contestacao_agi_ec"
for _caminho in (str(RAIZ), str(_RAIZ_RPA3)):
    if _caminho not in sys.path:
        sys.path.insert(0, _caminho)

#: Segundos de observação do processo recém-lançado. Seis é o bastante para o
#: lançador sair, se for esse o caso, e curto o bastante para não cansar quem
#: está olhando.
SEGUNDOS_DE_OBSERVACAO = 6

#: Fragmentos de nome que identificam um processo do Portal AIR.
#:
#: Deliberadamente **mais largo** do que a lista que `AGI.fechar()` usa: é assim
#: que se descobre um processo que o código ainda não conhece. Foi exatamente o
#: que aconteceu em 2026-08-06 — `fechar()` só sabia do `adl.exe`, e o
#: `portal_air_vivo.exe` sobrevivia a cada execução.
NOMES_DE_PROCESSO = ("portal_air", "adl")

_CDN_DO_PORTAL = ("stackpath.bootstrapcdn.com", 443)


def _processos_do_portal() -> list[str]:
    """Nomes dos processos do Portal AIR vivos agora."""
    import psutil

    vivos = []
    for proc in psutil.process_iter(["name"]):
        nome = (proc.info["name"] or "").lower()
        if any(fragmento in nome for fragmento in NOMES_DE_PROCESSO):
            vivos.append(nome)
    return sorted(set(vivos))


def _cdn_responde(timeout: float = 3.0) -> bool:
    """O CDN do Bootstrap está alcançável? Muda como o portal renderiza."""
    try:
        with socket.create_connection(_CDN_DO_PORTAL, timeout=timeout):
            return True
    except OSError:
        return False


def etapa_processo(executavel: Path, segundos: int = SEGUNDOS_DE_OBSERVACAO) -> dict:
    """
    Sobe o executável e observa o que acontece com ele.

    Não usa `AGI.inicializar()` de propósito: é justamente o laço dele que está
    sob suspeita, e entrar nele para diagnosticá-lo seria travar.

    Returns:
        Dicionário com `processo` (o `Popen`, para quem quiser encerrar),
        `codigo_de_saida` (`None` se continua vivo), `vivos` (nomes de processo)
        e `fechar_funciona` (se `AGI.fechar()` teria o que matar).
    """
    from comum.integracoes.agi import NOMES_DE_PROCESSO_AGI

    caminho = str(executavel)
    processo = subprocess.Popen([caminho], cwd=os.path.dirname(caminho))

    for _ in range(segundos):
        time.sleep(1)

    codigo = processo.poll()
    vivos = _processos_do_portal()

    # O veredito compara o que está vivo com o que `fechar()` de fato mata — não
    # com uma lista escrita aqui. Assim o ensaio acusa a divergência no dia em
    # que o aplicativo mudar, em vez de repetir a crença do código.
    return {
        "processo": processo,
        "codigo_de_saida": codigo,
        "vivos": vivos,
        "nao_cobertos": [n for n in vivos if n not in NOMES_DE_PROCESSO_AGI],
        "fechar_funciona": bool(vivos)
        and all(nome in NOMES_DE_PROCESSO_AGI for nome in vivos),
    }


def etapa_navegacao(agi, ambiente: str, procurar) -> dict:
    """
    Clica no botão do ambiente e confere que a tela dele abriu.

    **Para antes do ACESSAR.** O `bnt_acessar_agi.png` é procurado, e o resultado
    entra no relatório; o clique não acontece.

    Args:
        agi: Uma `AGI` (ou dublê, nos testes).
        ambiente: `producao` ou `homologacao`.
        procurar: Função que recebe o caminho de uma imagem e devolve a maior
            confiança em que ela está na tela, ou `None`.
    """
    from comum.integracoes.agi import (
        CONFIANCA_AMBIENTE,
        CONFIANCA_CARD_AGI,
        DESLOCAMENTO_LOGO_ATE_ACESSAR,
        _TELA_POR_AMBIENTE,
        img_card_agi,
    )

    botao, titulo = _TELA_POR_AMBIENTE[ambiente]

    # Mesma confiança que o `acessar_ambiente()` real usa: um ensaio que procura
    # com critério mais frouxo aprova o que o robô vai reprovar.
    clicou = agi._click(botao, confidence=CONFIANCA_AMBIENTE)
    if not clicou:
        return {
            "clicou": False, "titulo": titulo, "abriu": False,
            "acessar": None, "alvo_do_clique": None,
        }

    try:
        agi.aguardar_janela(titulo)
        abriu = True
    except Exception:
        abriu = False

    esperar_a_pagina_pintar()

    # A logo é procurada, NUNCA clicada — ver o cabeçalho do módulo. O que se
    # confere aqui é ONDE o clique cairia: o `acessar_ambiente()` calcula esse
    # ponto a partir da caixa da logo, e um deslocamento errado só apareceria em
    # produção, clicando no card do lado.
    caixa = agi._localizar(img_card_agi, confidence=CONFIANCA_CARD_AGI)
    alvo_do_clique = None
    if caixa is not None:
        alvo_do_clique = (
            int(caixa.left + caixa.width // 2),
            int(caixa.top + caixa.height // 2 + DESLOCAMENTO_LOGO_ATE_ACESSAR),
        )

    return {
        "clicou": True,
        "titulo": titulo,
        "abriu": abriu,
        "acessar": procurar(Path(img_card_agi)),
        "alvo_do_clique": alvo_do_clique,
    }


def esperar_a_pagina_pintar(timeout: int = 20) -> bool:
    """
    Espera a tela parar de mudar. Devolve `False` se ela não se aquietar.

    ⚠️ **O título da janela muda antes de a página repintar.** O Adobe AIR o lê
    do documento assim que ele carrega, e a pintura vem depois. Quem procurar uma
    imagem nesse intervalo mede a tela ANTERIOR: foi o que fez o card do AGI
    parecer vazio e os botões do portal parecerem fracos, em 2026-08-06.

    O robô não sofre com isso porque o `_wait_appear` insiste por até 180s. Este
    ensaio mede uma vez cada imagem — então precisa esperar de propósito, ou
    reprova imagem boa.
    """
    import pyautogui
    import pygetwindow as gw

    # Só a janela do portal. A tela inteira nunca se aquieta — o relógio da
    # barra de tarefas muda sozinho, e a espera expiraria sempre.
    janelas = gw.getWindowsWithTitle("Portal Triad: Vivo")
    if janelas:
        j = janelas[0]
        regiao = (max(j.left, 0), max(j.top, 0), j.width, j.height)
    else:
        regiao = None

    anterior = None
    for _ in range(timeout):
        atual = pyautogui.screenshot(region=regiao).tobytes()
        if atual == anterior:
            return True
        anterior = atual
        time.sleep(1)
    return False


#: Altura aceitável para o retângulo claro do botão, em pixels. Medido: 43.
_ALTURA_DO_BOTAO = (30, 60)


def _e_um_botao(ponto: tuple[int, int]) -> bool:
    """
    O ponto está dentro de um botão do portal?

    Prova que o deslocamento até o `ACESSAR` não caiu no vazio — sem clicar para
    descobrir, que em produção abriria um sistema.

    ⚠️ Não basta "o pixel é claro". O centro do botão é justamente onde fica o
    texto `ACESSAR`, em roxo escuro; a primeira versão desta função exigia pixels
    claros e reprovou um deslocamento **correto**.

    O que se mede é a **faixa clara**: numa janela estreita ao redor do ponto, os
    pixels claros formam o interior do botão, e o que está fora dele (o card,
    lavanda) não é claro. Se a altura dessa faixa é a de um botão e o ponto está
    no meio dela, o ponto está no botão — o texto escuro no meio não atrapalha,
    porque não muda os limites da faixa.
    """
    import pyautogui

    x, y = ponto
    largura, altura = 120, 80
    regiao = pyautogui.screenshot(
        region=(x - largura // 2, y - altura // 2, largura, altura)
    ).convert("RGB")

    linhas_claras = [
        linha
        for linha in range(altura)
        if sum(
            1
            for coluna in range(largura)
            if min(regiao.getpixel((coluna, linha))) > 200
        )
        > largura * 0.5
    ]
    if not linhas_claras:
        return False

    alto, baixo = min(linhas_claras), max(linhas_claras)
    if not _ALTURA_DO_BOTAO[0] <= baixo - alto + 1 <= _ALTURA_DO_BOTAO[1]:
        return False

    # O ponto (no centro da janela) tem de estar no meio da faixa, não na borda.
    return abs((alto + baixo) // 2 - altura // 2) <= 8


def _imprimir_veredito_de_imagem(rotulo: str, confianca, minima: float) -> str:
    """Imprime uma linha de imagem e devolve o veredito (`ok`/`fraca`/`ausente`)."""
    if confianca is None:
        print(f"      {rotulo:26s} ausente")
        return "ausente"
    if confianca < minima:
        print(f"      {rotulo:26s} FRACA ({confianca:.2f})")
        return "fraca"
    print(f"      {rotulo:26s} ok ({confianca:.2f})")
    return "ok"


def main(argv: list[str] | None = None) -> int:
    from comum.config import configuration as cfg
    from verificar_imagens_agi import CONFIANCA_MINIMA_ACEITAVEL, _procurar

    parser = argparse.ArgumentParser(
        prog="ensaiar_portal_agi.py",
        description=(
            "Abre o Portal AIR e navega até a tela do ambiente. NÃO faz login, "
            "NÃO clica em ACESSAR e NÃO toca no AGI."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Precisa de sessão gráfica e da área de trabalho livre: o pyautogui\n"
            "move o mouse de verdade, e uma janela por cima muda o que ele vê."
        ),
    )
    parser.add_argument(
        "--ambiente",
        choices=list(cfg.AMBIENTES_AGI),
        help="Sobrepõe o AGI_AMBIENTE do .env, só nesta execução.",
    )
    args = parser.parse_args(argv)

    ambiente = args.ambiente or cfg.AGI_AMBIENTE
    if ambiente not in cfg.AMBIENTES_AGI:
        print(f"ERRO: AGI_AMBIENTE inválido: [{ambiente}].")
        return 2

    if cfg.DIRETORIO_AGI is None or not Path(cfg.DIRETORIO_AGI).is_file():
        print(f"ERRO: executável do AGI não encontrado: [{cfg.DIRETORIO_AGI}].")
        print("Confira DIRETORIO_AGI — `python verificar_ambiente.py --rpa rpa3`.")
        return 2

    try:
        import pyautogui

        largura, altura = pyautogui.size()
    except Exception as erro:
        print(f"ERRO: não foi possível acessar a tela: {erro}")
        print("Este comando precisa de sessão gráfica — não roda por SSH nem serviço.")
        return 2

    from comum.integracoes.agi import AGI, img_bnt_homo_ini, img_bnt_prod_ini

    cdn = _cdn_responde()

    print("=" * 70)
    print("  ENSAIO DO PORTAL AIR — a metade do fluxo que não precisa de rede")
    print("=" * 70)
    print(f"  ambiente: {ambiente}")
    print(f"  executável: [{cfg.DIRETORIO_AGI}]")
    print(f"  tela: {largura} x {altura}")
    print(f"  CDN do Bootstrap: {'responde' if cdn else 'NÃO responde'}")
    if not cdn:
        print("      ⚠️  Sem ele o portal renderiza só com o CSS local, e a")
        print("          aparência muda. Se as imagens falharem, é a 1ª hipótese.")
        print("          Registre em qual condição este ensaio rodou.")
    print("  🔒 Não faz login, não clica em ACESSAR, não toca no AGI.\n")

    agi = AGI()
    problemas: list[str] = []

    # ── 1. Ciclo de vida do processo ───────────────────────────────────────
    print("[1/4] Ciclo de vida do processo")
    diagnostico = etapa_processo(Path(cfg.DIRETORIO_AGI))
    codigo = diagnostico["codigo_de_saida"]
    vivos = diagnostico["vivos"]

    print(f"      processos do Portal AIR vivos: {', '.join(vivos) or '(nenhum)'}")

    if codigo is None:
        print(f"      poll() após {SEGUNDOS_DE_OBSERVACAO}s: None — o lançado vive")
    else:
        print(f"      poll() após {SEGUNDOS_DE_OBSERVACAO}s: {codigo} — ele SAIU")
        print("      >> é um lançador; quem fica com a janela é outro processo.")
        print("         `inicializar()` espera pelo processo que APARECE, não por")
        print("         este — foi a correção de 2026-08-06.")

    if not vivos:
        print("      >> 🔴 nenhum processo do Portal AIR ficou vivo.")
        print("         `inicializar()` levantaria AGIError ao fim do timeout.")
        problemas.append(
            "nada subiu: o executável foi lançado e nenhum processo do Portal "
            "AIR restou"
        )

    if diagnostico["fechar_funciona"]:
        print("      >> fechar() cobre todos os processos vivos acima. OK.")
    else:
        nao_cobertos = diagnostico["nao_cobertos"]
        print(f"      >> 🔴 fechar() NÃO conhece: {', '.join(nao_cobertos) or '—'}")
        print("         Eles sobreviveriam a cada execução, acumulando.")
        problemas.append(
            "fechar() não cobre "
            f"{', '.join(nao_cobertos) or 'nenhum processo (nada subiu)'}"
        )

    # ── 2. Janela ──────────────────────────────────────────────────────────
    print("\n[2/4] Janela do portal")
    try:
        agi.aguardar_janela("Portal Triad: Vivo")
        print("      'Portal Triad: Vivo' apareceu e está em primeiro plano.")
    except Exception as erro:
        print(f"      🔴 {erro}")
        problemas.append(f"a janela do portal não apareceu: {erro}")
        agi.fechar()
        return _encerrar(problemas)

    # ── 3. Imagens da tela inicial ─────────────────────────────────────────
    print("\n[3/4] Imagens desta tela")
    if not esperar_a_pagina_pintar():
        print("      ⚠️  a tela não parou de mudar; as medidas abaixo podem")
        print("          ter pegado a página no meio da pintura.")
    for rotulo, imagem in (
        ("bnt_producao_ini.png", img_bnt_prod_ini),
        ("bnt_homo_ini.png", img_bnt_homo_ini),
    ):
        veredito = _imprimir_veredito_de_imagem(
            rotulo, _procurar(Path(imagem)), CONFIANCA_MINIMA_ACEITAVEL
        )
        if veredito != "ok":
            problemas.append(f"{rotulo}: {veredito} na tela inicial do portal")

    # ── 4. Navegação até o ambiente ────────────────────────────────────────
    print(f"\n[4/4] Navegação → {ambiente}")
    resultado = etapa_navegacao(agi, ambiente, _procurar)

    if not resultado["clicou"]:
        print("      🔴 não achou o botão do ambiente para clicar.")
        problemas.append(f"o botão do ambiente '{ambiente}' não foi encontrado")
    else:
        if resultado["abriu"]:
            print(f"      título agora: '{resultado['titulo']}'")
        else:
            print(f"      🔴 a janela '{resultado['titulo']}' não apareceu.")
            problemas.append(f"a tela de {ambiente} não abriu após o clique")

        veredito = _imprimir_veredito_de_imagem(
            "card_agi.png", resultado["acessar"], CONFIANCA_MINIMA_ACEITAVEL
        )
        if veredito != "ok":
            problemas.append(f"card_agi.png: {veredito} na tela de {ambiente}")

        alvo = resultado["alvo_do_clique"]
        if alvo is None:
            print("      onde o ACESSAR seria clicado: (logo não localizada)")
        else:
            print(f"      o ACESSAR seria clicado em {alvo}")
            if _e_um_botao(alvo):
                print("      >> o ponto cai sobre um botão claro. OK.")
            else:
                print("      >> 🔴 o ponto NÃO cai sobre um botão.")
                problemas.append(
                    f"o clique no ACESSAR cairia em {alvo}, que não é botão — "
                    f"conferir DESLOCAMENTO_LOGO_ATE_ACESSAR"
                )

    print("\n      PAROU AQUI. O clique em ACESSAR não foi dado.")

    # ── Encerramento: e `fechar()` de verdade ──────────────────────────────
    print("\n  Encerrando com AGI.fechar()...")
    agi.fechar()
    time.sleep(2)
    restantes = _processos_do_portal()
    if restantes:
        print(f"      🔴 sobraram processos: {', '.join(restantes)}")
        problemas.append(f"fechar() deixou processos vivos: {', '.join(restantes)}")
    else:
        print("      nenhum processo do Portal AIR restou. OK.")

    return _encerrar(problemas)


def _encerrar(problemas: list[str]) -> int:
    print("\n" + "=" * 70)
    if not problemas:
        print("  ✅ Ensaio completo, sem problema.")
        print()
        print("  Fica sem cobertura, até haver acesso ao AGI: login, os menus,")
        print("  os dois uploads, o download do relatório e os diálogos nativos")
        print("  — 27 das 30 imagens.")
        return 0

    print(f"  🔴 {len(problemas)} problema(s):")
    for problema in problemas:
        print(f"     - {problema}")
    print()
    print("  Imagem fraca ou ausente: recapture NESTA máquina — ver")
    print("  docs/03-checklists/checklist-validacao-agi.md.")
    print("  ⛔ Nunca baixe o `confidence` no código para fazer um passo passar.")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
