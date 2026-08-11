"""Desfaz o efeito de uma rodada de homologação, para poder repeti-la.

Escrito em 2026-08-06.

## A armadilha que este script evita

`ValidadorHistoricoRPA` guarda, num JSON por mês, os arquivos que já passaram —
para o robô não reprocessar o que já processou. Em produção é o comportamento
certo. Na homologação, ele produz a cena mais confusa possível:

> Rodo o cenário. Funciona. Rodo de novo para conferir. **Nada acontece.**
> O robô termina com sucesso, sem processar nada, e parece defeito.

Não é. É o histórico fazendo o trabalho dele. Este script o limpa, junto com os
artefatos que a rodada gerou, para que o mesmo cenário possa ser repetido do zero.

## Segurança

- **Recusa rodar com `ENV=prod`.** Apagar artefato de produção não é o que este
  script existe para fazer, e a confusão é fácil.
- **Lista tudo antes** e pede confirmação. `--sim` pula a pergunta, para quem já
  sabe o que está fazendo.
- **Nunca toca no banco.** Limpar `tbl_rpa_log_detraf_despesa_contestacao` seria
  destruir o sinal do analista, que é insumo, não resultado. Para partir de um
  banco limpo, gere outro espelho com `espelhar_banco.py`.

Uso::

    python resetar_homologacao.py --referencia 202507
    python resetar_homologacao.py --referencia 202507 --so-historico
    python resetar_homologacao.py --referencia 202507 --sim
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

#: Sufixos dos artefatos gerados pelos robôs. Só o que o robô **produz** — o
#: Detraf recebido e a expectativa Vivo são insumo e nunca são tocados.
_ARTEFATOS = (
    "_EXT",
    "_INT",
    "_EXP",
    "_BK",
    "_ERRO",
    "_RECUSADO",
    "CONT_PROC",
)


def _localizar_historico(referencia: str) -> list[Path]:
    from comum.config import configuration as cfg

    pasta = Path(cfg.DIRETORIO_HISTORICO_ARQUIVOS) / "historico_arquivos_processados"
    return [p for p in (pasta / f"arquivos_validados_{referencia}.json",) if p.is_file()]


def _localizar_artefatos(referencia: str) -> list[Path]:
    """
    Os artefatos do mês, na árvore de operadoras.

    A carta CT fica **de fora de propósito**: ela consome um número da sequência
    global, que é serial e compartilhada. Apagar o arquivo não devolve o número,
    e apagar a carta de controle CT afetaria a numeração de todo mundo.
    """
    from comum.arquivos import estrutura_pastas as ep
    from comum.config import configuration as cfg

    raiz = Path(cfg.CAMINHO_OPERADORAS)
    if not raiz.is_dir():
        return []

    encontrados: list[Path] = []
    ano = referencia[:4]

    for pasta_operadora in sorted(p for p in raiz.iterdir() if p.is_dir()):
        pasta_mes = pasta_operadora / ano / referencia
        if not pasta_mes.is_dir():
            continue

        for arquivo in pasta_mes.rglob("*"):
            if not arquivo.is_file():
                continue
            if any(marca in arquivo.stem.upper() for marca in _ARTEFATOS):
                encontrados.append(arquivo)

    return encontrados


def _localizar_area_de_trabalho(referencia: str) -> list[Path]:
    """
    As cópias de trabalho do mês (2026-08-10).

    A área é preservada de propósito — é evidência de homologação e o estado
    parcial de uma etapa que morreu no meio. Mas repetir um cenário do zero
    exige limpá-la junto do histórico: senão a próxima execução acha a cópia
    anterior e o `_ERRO` de linha da rodada passada, e o que se está olhando
    deixa de ser o resultado desta rodada.
    """
    from comum.config import configuration as cfg

    pasta = Path(cfg.DIRETORIO_TEMP) / referencia
    if not pasta.is_dir():
        return []

    return [caminho for caminho in sorted(pasta.rglob("*")) if caminho.is_file()]


def _localizar_saida(referencia: str) -> list[Path]:
    """
    Os artefatos entregues pela validação, na pasta de saída (2026-08-10).

    Antes eles ficavam ao lado do insumo e eram pegos por `_localizar_artefatos`.
    Agora moram em `DIRETORIO_SAIDA_VALIDACAO` — que é também a ENTRADA do batimento, e
    por isso precisa ser limpa junto: uma saída antiga faz a rodada seguinte
    bater contra o resultado da anterior.
    """
    from comum.config import configuration as cfg

    pasta = Path(cfg.DIRETORIO_SAIDA_VALIDACAO) / referencia
    if not pasta.is_dir():
        return []

    return [caminho for caminho in sorted(pasta.rglob("*")) if caminho.is_file()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="resetar_homologacao.py",
        description=(
            "Limpa o histórico anti-reprocessamento e os artefatos de um mês, "
            "para repetir um cenário de homologação do zero."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "NÃO toca no banco: o sinal do analista é insumo, não resultado. "
            "Para um banco limpo, gere outro espelho com espelhar_banco.py.\n"
            "A carta CT também não é apagada — o número dela já foi consumido "
            "da sequência global e apagar o arquivo não o devolve."
        ),
    )
    parser.add_argument(
        "--referencia",
        required=True,
        metavar="AAAAMM",
        help="Mês de tráfego a limpar.",
    )
    parser.add_argument(
        "--so-historico",
        action="store_true",
        help=(
            "Limpa só o histórico anti-reprocessamento, deixando os artefatos. "
            "Use quando quiser reprocessar por cima do que já saiu."
        ),
    )
    parser.add_argument(
        "--sim", action="store_true", help="Não pergunta antes de apagar."
    )
    args = parser.parse_args(argv)

    if not (len(args.referencia) == 6 and args.referencia.isdigit()):
        print(f"ERRO: '{args.referencia}' não é AAAAMM.")
        return 2

    from comum.config import configuration as cfg

    if cfg.ENV == "prod":
        print("=" * 70)
        print("  RECUSADO: o ambiente está em ENV=prod.")
        print("=" * 70)
        print(
            "\n  Este script apaga artefatos gerados. Em produção, isso é perda\n"
            "  de dado — os artefatos são o que foi enviado à operadora e\n"
            "  carregado no AGI.\n\n"
            "  Se a intenção é mesmo limpar um ambiente de teste, ponha\n"
            "  ENV=dev (ou ENV_RPA2=dev, para um robô só) antes de rodar."
        )
        return 2

    historico = _localizar_historico(args.referencia)
    artefatos = [] if args.so_historico else _localizar_artefatos(args.referencia)
    area = [] if args.so_historico else _localizar_area_de_trabalho(args.referencia)
    saida = [] if args.so_historico else _localizar_saida(args.referencia)

    print(f"Referência: {args.referencia}   |   modo: {cfg.ENV}")
    print("=" * 70)

    if historico:
        print(f"\nHistórico anti-reprocessamento ({len(historico)}):")
        for caminho in historico:
            print(f"  {caminho}")
    else:
        print("\nNenhum histórico deste mês — a próxima execução já processa tudo.")

    if artefatos:
        print(f"\nArtefatos gerados ({len(artefatos)}):")
        for caminho in artefatos[:20]:
            print(f"  {caminho}")
        if len(artefatos) > 20:
            print(f"  ... e mais {len(artefatos) - 20}")
    elif not args.so_historico:
        print("\nNenhum artefato deste mês na árvore de operadoras.")

    if area:
        print(f"\nÁrea de trabalho do RPA 2 ({len(area)}):")
        for caminho in area[:20]:
            print(f"  {caminho}")
        if len(area) > 20:
            print(f"  ... e mais {len(area) - 20}")

    if saida:
        print(f"\nSaída da validação ({len(saida)}):")
        for caminho in saida[:20]:
            print(f"  {caminho}")
        if len(saida) > 20:
            print(f"  ... e mais {len(saida) - 20}")

    total = len(historico) + len(artefatos) + len(area) + len(saida)
    if not total:
        print("\nNada a apagar.")
        return 0

    if not args.sim:
        print()
        resposta = input(f"Apagar os {total} arquivo(s) acima? [s/N] ").strip().lower()
        if resposta not in {"s", "sim"}:
            print("Cancelado. Nada foi apagado.")
            return 1

    apagados, falhas = 0, 0
    for caminho in historico + artefatos + area + saida:
        try:
            caminho.unlink()
            apagados += 1
        except OSError as erro:
            print(f"  ! não foi possível apagar [{caminho}]: {erro}")
            falhas += 1

    # As pastas ficariam vazias e viram ruído na próxima leitura. A da saída
    # importa mais: `listar_operadoras_com_saida` conta pasta, não arquivo, e
    # uma pasta vazia faria o batimento anunciar uma operadora que não tem nada.
    for raiz in (cfg.DIRETORIO_TEMP, cfg.DIRETORIO_SAIDA_VALIDACAO):
        for pasta in sorted(
            (p for p in (Path(raiz) / args.referencia).glob("**/*") if p.is_dir()),
            reverse=True,
        ):
            try:
                pasta.rmdir()
            except OSError:
                pass  # não está vazia — alguém pôs algo lá, e não é nosso apagar

    print(f"\n{apagados} arquivo(s) apagado(s), {falhas} falha(s).")
    print(
        "\nA carta CT e o banco NÃO foram tocados — ver o --help para o motivo."
        if not args.so_historico
        else ""
    )
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
