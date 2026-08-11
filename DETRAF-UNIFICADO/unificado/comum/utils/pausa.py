"""Parada interativa entre etapas — só no modo dev.

Escrito em 2026-08-06, para a homologação manual.

## Para que serve

As etapas de cada robô têm nome e fronteira (ver o `FLUXO.md` de cada um). A
homologação, porém, era cega: o RPA 3 rodava os quatro passos sem parar, e só no
fim dava para conferir o que saiu — quando o AGI já tinha sido tocado e o e-mail
já estava montado.

A parada entre etapas faz duas coisas ao mesmo tempo: **mostra o que a etapa
acabou de produzir** e **dá o poder de não continuar**.

## 🔴 O risco desta funcionalidade é ela escapar para produção

Um robô desassistido que abre uma caixa de diálogo **trava para sempre** — e a
escolha de desenho foi justamente essa: a caixa espera indefinidamente, porque na
homologação conduzida a pessoa está ali.

Por isso este módulo começa pelos travamentos, não pela caixa.
:func:`esta_habilitada` exige **quatro** condições simultâneas, e qualquer uma
que falhe faz o robô seguir sem parar, com o motivo no log:

1. **`ENV == "dev"`** — em produção nunca para. Regra dura;
2. **`PAUSA_ENTRE_ETAPAS=true`** — explícito, default `false`. Estar em dev não
   basta;
3. **sessão gráfica utilizável** — tenta criar a janela e desistir. É o que
   protege a tarefa agendada em sessão 0, que não tem desktop: ela **falha
   continuando**, não travando;
4. **fora do pytest** — uma suíte que abre diálogo trava o CI para sempre.

A terceira é a que realmente segura o caso perigoso, porque não depende de
ninguém ter configurado nada certo.

## Por que tkinter

É **stdlib** — nenhuma dependência nova. O `pyautogui.confirm` existiria e faria
o mesmo, mas ele é do RPA 3 e traz a automação de tela junto; a base comum não
tem por que depender disso.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Optional

from comum.config.logger_config import logger

#: Rótulo dos botões, num lugar só — eles aparecem na caixa e no log.
BOTAO_OK = "Continuar"
BOTAO_CANCELAR = "Cancelar execução"
BOTAO_ABRIR = "Abrir pasta"


class ExecucaoCanceladaPeloOperador(RuntimeError):
    """
    O operador escolheu não continuar.

    **Não é erro** — é decisão humana, e os `main.py` a tratam à parte: log em
    `WARNING`, código de saída **2** (distinto de 0 e de 1) e sem traceback.

    O que já foi feito **fica feito**. É o comportamento certo: as etapas são
    pontos de retomada, e a seguinte pode ser rodada depois com `--etapa`.
    """


def _sob_pytest() -> bool:
    """
    `True` quando o processo está rodando uma suíte de testes.

    Função própria, e não um `if` embutido, por dois motivos: fica ao lado da
    guarda irmã (`_sem_sessao_grafica`), e o pytest **redefine**
    `PYTEST_CURRENT_TEST` a cada fase do teste — apagá-la numa fixture não
    funciona, então testar as outras guardas exige poder substituir esta.
    """
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def _sem_sessao_grafica() -> bool:
    """
    `True` quando não há desktop utilizável para abrir a janela.

    Cria a raiz do tkinter e a destrói. É o único jeito honesto de saber — no
    Windows, uma tarefa agendada com "executar estando o usuário conectado ou
    não" roda em sessão 0, sem desktop, e o `TclError` acontece exatamente aqui.

    Falha ao criar → **segue sem parar**. Esta função existe para o robô nunca
    travar por causa de uma caixa que não tinha como aparecer.
    """
    try:
        import tkinter

        raiz = tkinter.Tk()
        raiz.withdraw()
        raiz.destroy()
        return False
    except Exception:
        return True


def esta_habilitada() -> tuple[bool, str]:
    """
    Se a pausa deve acontecer, e o motivo quando não.

    Returns:
        ``(habilitada, motivo)``. O motivo é vazio quando habilitada, e é o que
        vai para o log quando não — para ninguém ficar procurando por que a caixa
        não apareceu.
    """
    from comum.config import configuration

    if _sob_pytest():
        return False, "rodando sob pytest"

    if configuration.ENV != "dev":
        return False, f"ENV={configuration.ENV} (a pausa só existe em dev)"

    if not configuration.PAUSA_ENTRE_ETAPAS:
        return False, "PAUSA_ENTRE_ETAPAS desligado"

    if _sem_sessao_grafica():
        return False, "sem sessão gráfica para abrir a janela"

    return True, ""


def _abrir(caminho: Path) -> None:
    """Abre a pasta no explorador. Falhar aqui nunca derruba a execução."""
    try:
        if sys.platform == "win32":
            os.startfile(str(caminho))  # type: ignore[attr-defined]
        else:
            import subprocess

            subprocess.Popen(["xdg-open", str(caminho)])
    except Exception as erro:
        logger.warning(f"[PAUSA] Não foi possível abrir [{caminho}]: {erro}")


def _mostrar_caixa(
    titulo: str, texto: str, caminho: Optional[Path]
) -> bool:
    """
    Abre a caixa e devolve `True` para continuar, `False` para cancelar.

    A janela sobe **em primeiro plano** (`-topmost`): sem isso ela nasce atrás
    do terminal e o robô parece travado — que é o oposto do que a pausa existe
    para fazer.

    Fechar no X é tratado como **cancelar**. Quem fecha a janela não está
    dizendo "pode seguir".
    """
    import tkinter
    from tkinter import scrolledtext

    janela = tkinter.Tk()
    janela.title(titulo)
    janela.attributes("-topmost", True)
    janela.geometry("760x480")

    decisao = {"continuar": False}

    area = scrolledtext.ScrolledText(
        janela, wrap="none", font=("Consolas", 10), padx=12, pady=12
    )
    area.insert("1.0", texto)
    area.configure(state="disabled")
    area.pack(fill="both", expand=True)

    barra = tkinter.Frame(janela, pady=8)
    barra.pack(fill="x")

    def _continuar() -> None:
        decisao["continuar"] = True
        janela.destroy()

    def _cancelar() -> None:
        decisao["continuar"] = False
        janela.destroy()

    if caminho is not None and Path(caminho).exists():
        tkinter.Button(
            barra, text=BOTAO_ABRIR, width=16, command=lambda: _abrir(Path(caminho))
        ).pack(side="left", padx=12)

    tkinter.Button(barra, text=BOTAO_OK, width=18, command=_continuar).pack(
        side="right", padx=12
    )
    tkinter.Button(barra, text=BOTAO_CANCELAR, width=18, command=_cancelar).pack(
        side="right"
    )

    janela.protocol("WM_DELETE_WINDOW", _cancelar)
    janela.mainloop()

    return decisao["continuar"]


def montar_texto(
    linhas: list[str], proxima_etapa: str | None, caminho: Path | None
) -> str:
    """Monta o corpo da caixa. Separado para poder ser testado sem abrir janela."""

    partes = list(linhas) if linhas else ["(nada a relatar)"]

    if caminho is not None:
        partes += ["", f"Pasta: {caminho}"]

    if proxima_etapa:
        partes += ["", "─" * 60, f"PRÓXIMA ETAPA: {proxima_etapa}"]
    else:
        partes += ["", "─" * 60, "Esta é a última etapa da execução."]

    return "\n".join(partes)


def pausar(
    titulo: str,
    linhas: list[str],
    proxima_etapa: str | None = None,
    caminho: Path | None = None,
    _mostrar: Callable[[str, str, Optional[Path]], bool] | None = None,
) -> None:
    """
    Mostra o que a etapa produziu e espera a decisão de continuar.

    Args:
        titulo: Cabeçalho da janela — ``"RPA 3 — etapa 1/4: artefatos"``.
        linhas: O que mostrar. Vai **também para o log**, para a rodada ficar
            auditável depois de a janela fechar.
        proxima_etapa: Descrição do que vem a seguir. É a informação mais útil
            da caixa quando a próxima etapa escreve para fora.
        caminho: Pasta a oferecer no botão "Abrir pasta". `None` esconde o botão.
        _mostrar: Costura de teste — substitui a caixa por uma função que
            devolve a decisão. Existe para testar o texto e o cancelamento sem
            abrir janela nenhuma.

    Raises:
        ExecucaoCanceladaPeloOperador: Quando o operador cancela ou fecha a
            janela.
    """

    habilitada, motivo = esta_habilitada()
    texto = montar_texto(linhas, proxima_etapa, caminho)

    # O conteúdo vai para o log SEMPRE — inclusive com a pausa desligada. É o
    # resumo por etapa, e ele é útil de qualquer forma.
    for linha in texto.splitlines():
        if linha.strip():
            logger.info(f"[{titulo}] {linha}")

    if not habilitada:
        if _mostrar is None:
            logger.debug(f"[PAUSA] Não pausei em '{titulo}': {motivo}.")
        return

    mostrar = _mostrar or _mostrar_caixa

    if not mostrar(titulo, texto, caminho):
        raise ExecucaoCanceladaPeloOperador(
            f"Execução cancelada pelo operador em '{titulo}'."
        )

    logger.info(f"[PAUSA] '{titulo}' confirmada pelo operador — seguindo.")
