"""Confere se as imagens do AGI batem com esta tela, sem operar nada.

Escrito em 2026-08-06, ao fechar a pendência **Q20**.

## O problema que isto resolve

A automação do AGI é por **reconhecimento de imagem**: `pyautogui.locateOnScreen`
compara pixel. As 30 capturas em `comum/view/imagens/` foram feitas nas máquinas de
quem escreveu cada projeto de origem — **nunca na VM onde isto vai rodar**.
Resolução, escala de fonte, tema do Windows e versão do AGI mudam pixel, e pixel
diferente é imagem não encontrada.

Sem esta ferramenta, descobrir isso custava uma execução inteira: abrir o AGI,
logar em produção, navegar — e falhar no meio, uma imagem por vez, porque cada
`_wait_appear` espera até **180 segundos** antes de desistir. Sete imagens
quebradas eram sete rodadas.

Aqui é o contrário: com a tela certa aberta, o comando diz de uma vez **quais
imagens são encontradas e quais não**, com o grau de confiança de cada uma.

## O que ele NÃO faz

**Não clica, não digita, não abre o AGI, não navega.** Só procura. Pode rodar com
o AGI aberto em produção sem risco de tocar em nada — é `locateOnScreen`, uma
leitura da tela.

## Como usar

O AGI tem várias telas, e cada imagem só existe na sua. Rode **uma vez por
grupo**, com a tela correspondente aberta::

    python verificar_imagens_agi.py --listar          # que grupos existem
    python verificar_imagens_agi.py --grupo AGI_CONFIG
    python verificar_imagens_agi.py                   # todos, de uma vez

Imagem "não encontrada" **só é problema se a tela dela estiver aberta**. Rodar
tudo de uma vez sempre vai acusar a maioria — o resultado útil é por grupo.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# Desde a promoção de 2026-08-10 as imagens são de `comum/`, não do RPA 3 — os
# dois robôs que operam o AGI as compartilham. A raiz vem do próprio módulo, e
# não repetida aqui, para não haver dois caminhos para a mesma pasta.
from comum.integracoes.agi import RAIZ_IMAGENS  # noqa: E402

#: Confianças testadas, da mais estrita para a mais frouxa.
#:
#: O código usa 0.8 por padrão e 0.9 no `bnt_acessar_agi`. Testar uma escala
#: mostra **o quanto** a imagem está diferente, não só se está: uma que só casa
#: em 0.6 vai falhar de forma intermitente em produção, e é melhor recapturar
#: agora do que descobrir no meio de uma carga.
CONFIANCAS = (0.95, 0.9, 0.8, 0.7, 0.6)

#: Abaixo disto, casar é coincidência: o `locateOnScreen` acha "qualquer coisa
#: parecida", e o robô clica no lugar errado. Nunca baixe o `confidence` do
#: código para fazer um passo passar.
CONFIANCA_MINIMA_ACEITAVEL = 0.8


def _grupos() -> dict[str, list[Path]]:
    """As imagens, agrupadas pela subpasta — que corresponde à tela do AGI."""

    if not RAIZ_IMAGENS.is_dir():
        return {}

    grupos: dict[str, list[Path]] = {}
    for imagem in sorted(RAIZ_IMAGENS.rglob("*.png")):
        grupos.setdefault(imagem.parent.name, []).append(imagem)
    return grupos


def _procurar(caminho: Path) -> float | None:
    """
    Maior confiança em que a imagem é encontrada nesta tela.

    Returns:
        A confiança, ou `None` se não for encontrada nem na mais frouxa.
    """
    import pyautogui

    for confianca in CONFIANCAS:
        try:
            if pyautogui.locateOnScreen(str(caminho), confidence=confianca):
                return confianca
        except Exception:
            # `locateOnScreen` levanta quando não acha, e o tipo da exceção varia
            # com a versão do pyautogui/opencv. Não achar não é erro aqui.
            continue
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verificar_imagens_agi.py",
        description=(
            "Procura na tela atual cada imagem de referência do AGI e diz quais "
            "são encontradas. NÃO clica, não digita e não abre o AGI."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Cada grupo corresponde a uma tela do AGI. Rode uma vez por grupo,\n"
            "com a tela correspondente aberta — imagem não encontrada só é\n"
            "problema se a tela dela estiver na frente."
        ),
    )
    parser.add_argument("--grupo", help="Só as imagens deste grupo (subpasta).")
    parser.add_argument(
        "--listar", action="store_true", help="Lista os grupos e sai."
    )
    args = parser.parse_args(argv)

    grupos = _grupos()
    if not grupos:
        print(f"ERRO: nenhuma imagem em [{RAIZ_IMAGENS}].")
        return 2

    if args.listar:
        print("Grupos de imagem (cada um é uma tela do AGI):\n")
        for nome, imagens in grupos.items():
            print(f"  {nome:28s} {len(imagens)} imagem(ns)")
        print("\nRode com --grupo NOME, com a tela correspondente aberta.")
        return 0

    if args.grupo:
        if args.grupo not in grupos:
            print(f"ERRO: grupo '{args.grupo}' não existe. Use --listar.")
            return 2
        grupos = {args.grupo: grupos[args.grupo]}

    try:
        import pyautogui

        largura, altura = pyautogui.size()
    except Exception as erro:
        print(f"ERRO: não foi possível acessar a tela: {erro}")
        print("Este comando precisa de sessão gráfica — não roda por SSH nem serviço.")
        return 2

    print("=" * 70)
    print("  IMAGENS DO AGI — conferência contra a tela atual")
    print("=" * 70)
    print(f"  Resolução desta tela: {largura} x {altura}")
    print("  Nada é clicado: só leitura da tela.\n")

    encontradas, fracas, ausentes = [], [], []

    for nome_grupo, imagens in grupos.items():
        print(f"── {nome_grupo} " + "─" * max(0, 66 - len(nome_grupo)))
        for imagem in imagens:
            confianca = _procurar(imagem)
            if confianca is None:
                print(f"  [ ausente ] {imagem.name}")
                ausentes.append(imagem)
            elif confianca < CONFIANCA_MINIMA_ACEITAVEL:
                print(f"  [ FRACA {confianca:.2f} ] {imagem.name}")
                fracas.append((imagem, confianca))
            else:
                print(f"  [ ok {confianca:.2f}   ] {imagem.name}")
                encontradas.append(imagem)
        print()

    print("=" * 70)
    print(
        f"  {len(encontradas)} encontrada(s), {len(fracas)} fraca(s), "
        f"{len(ausentes)} ausente(s)"
    )

    if fracas:
        print("\n  ⚠️  IMAGENS FRACAS — casam, mas abaixo do que o código usa (0.8).")
        print("     Vão falhar de forma INTERMITENTE em produção. Recapture-as")
        print("     nesta VM antes de rodar o fluxo:")
        for imagem, confianca in fracas:
            print(f"       {confianca:.2f}  {imagem.relative_to(RAIZ_IMAGENS)}")
        print("\n     ⛔ NÃO baixe o `confidence` no código para fazer passar —")
        print("        confiança baixa casa o botão errado, e o robô clica nele.")

    if ausentes:
        print("\n  Não encontradas nesta tela:")
        for imagem in ausentes:
            print(f"       {imagem.relative_to(RAIZ_IMAGENS)}")
        print(
            "\n     Isto só é problema se a tela correspondente estiver aberta.\n"
            "     Rode com --grupo, uma tela de cada vez."
        )

    print(
        "\n  Para recapturar: recorte o MESMO elemento nesta VM e substitua o\n"
        "  arquivo, mantendo o nome. Ver docs/03-checklists/checklist-validacao-agi.md."
    )

    # Só as fracas derrubam o código de saída: ausente pode ser só a tela errada.
    return 1 if fracas else 0


if __name__ == "__main__":
    raise SystemExit(main())
