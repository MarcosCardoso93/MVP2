"""Monta a árvore de pastas que os robôs leem e escrevem (2026-08-07).

## Por que existe

Não havia nada que criasse essas pastas. O `resetar_homologacao.py` só apaga
artefatos; a estrutura em si era montada à mão, e por isso a primeira execução
sempre esbarrava numa pasta faltando — quase sempre no meio do fluxo, depois de
o robô já ter aberto o Outlook ou o AGI.

## Ele lê a configuração, não uma lista de nomes

As pastas saem das variáveis de `comum/config/configuration.py`, e não de nomes
fixos aqui dentro. Assim o script acompanha o `.env`: quem apontar
`CAMINHO_OPERADORAS` para um compartilhamento de rede vê o script preparar aquele
compartilhamento, e não uma segunda árvore local.

## É idempotente

Rodar de novo não duplica nem apaga nada — só relata o que já existia. Isso
importa porque o uso normal é rodar antes de cada rodada de homologação, sem
lembrar se já rodou.

Uso::

    python preparar_ambiente.py
    python preparar_ambiente.py --operadora CLARO --referencia 202507
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def _pastas_da_configuracao(cfg) -> list[tuple[str, Path]]:
    """
    As pastas que o robô precisa encontrar prontas, na ordem do fluxo.

    Só entram as que o código **não** cria sozinho, ou cuja ausência produz
    falha silenciosa. As que o robô cria (`_NAO_IDENTIFICADOS`, `_QUARENTENA`,
    evidências) entram assim mesmo: vê-las vazias na árvore é o que diz a quem
    homologa que elas existem e onde procurar.
    """
    candidatas = [
        ("CAMINHO_OPERADORAS", cfg.CAMINHO_OPERADORAS),
        ("DIRETORIO_ENTRADA", cfg.DIRETORIO_ENTRADA),
        ("CAMINHO_EXPECTATIVA_DETRAF", cfg.CAMINHO_EXPECTATIVA_DETRAF),
        ("DIRETORIO_NAO_IDENTIFICADOS", cfg.DIRETORIO_NAO_IDENTIFICADOS),
        ("DIRETORIO_QUARENTENA", cfg.DIRETORIO_QUARENTENA),
        ("DIRETORIO_TEMP", cfg.DIRETORIO_TEMP),
        ("DIRETORIO_SAIDA_VALIDACAO", cfg.DIRETORIO_SAIDA_VALIDACAO),
        ("DIRETORIO_HISTORICO_ARQUIVOS", cfg.DIRETORIO_HISTORICO_ARQUIVOS),
        ("CAMINHO_CONTROLE_CT", cfg.CAMINHO_CONTROLE_CT),
        ("DIRETORIO_EVIDENCIAS", cfg.DIRETORIO_EVIDENCIAS),
        ("RAIZ_LOGS", cfg.RAIZ_LOGS),
    ]
    return [(nome, caminho) for nome, caminho in candidatas if caminho is not None]


def _criar(caminho: Path) -> str:
    """`criada`, `já existia` ou a mensagem do erro."""
    if caminho.is_dir():
        return "já existia"
    try:
        caminho.mkdir(parents=True, exist_ok=True)
    except OSError as erro:
        return f"ERRO: {erro}"
    return "criada"


def _preparar_mes_da_operadora(cfg, operadora: str, referencia: str) -> list[str]:
    """
    As quatro subpastas de `{operadora}/{ano}/{aaaamm}/`.

    Reusa `comum/arquivos/estrutura_pastas.py`, que já as monta com `criar=True`
    — repetir os nomes aqui abriria espaço para eles divergirem do que o robô
    procura, que é exatamente o defeito que a árvore de pastas existe para
    evitar.
    """
    from comum.arquivos import estrutura_pastas as ep

    montadores = [
        ("Detrafs Recebidos", ep.caminho_detrafs_recebidos),
        ("Detrafs Enviados", ep.caminho_detrafs_enviados),
        ("AGI", ep.caminho_agi),
        ("Contestações", ep.caminho_contestacoes),
    ]

    linhas = []
    for rotulo, montar in montadores:
        caminho = montar(
            operadora=operadora,
            aaaamm=referencia,
            raiz_operadoras=cfg.CAMINHO_OPERADORAS,
            criar=True,
        )
        linhas.append(f"  {rotulo:22s} {caminho}")
    return linhas


def _copiar(origem: Path, destino: Path) -> str:
    """`copiado`, `já estava lá` ou a mensagem do erro."""
    if destino.exists():
        return "já estava lá"
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)
    except OSError as erro:
        return f"ERRO: {erro}"
    return "copiado"


def _pasta_de_expectativa(nome_arquivo: str, pastas: list[str]) -> str | None:
    """
    Em qual subpasta de `PASTAS_EXPECTATIVAS` este arquivo entra.

    A heurística morava aqui, com o comentário "o robô não usa isto". Deixou de
    ser verdade em 2026-08-10: a captação por SFTP precisa dela no modo
    `--de-pasta`, quando a origem é um diretório plano. Subiu para
    `comum/dominio/expectativa.py`, e esta função ficou como o apelido que os
    testes deste script já usavam.
    """
    from comum.dominio.expectativa import pasta_por_nome

    return pasta_por_nome(nome_arquivo, pastas)


def _semear(
    cfg,
    origem: Path,
    para_operadora: str | None = None,
    referencia: str | None = None,
) -> list[str]:
    """
    Copia os insumos reais para onde os robôs os procuram.

    ## Os Detrafs vão para a ENTRADA, não para a árvore da operadora

    Poderia parecer mais direto pôr cada arquivo em
    ``{operadora}/{ano}/{aaaamm}/Detrafs Recebidos/``. Seria preciso descobrir a
    operadora — lendo a EOT credora de dentro do arquivo e consultando o Anexo 5.

    Isso é **exatamente a HU-02**, e já existe em
    `rpa1_captura/src/services/operadora_service.py`. Uma segunda implementação
    aqui seria uma segunda fonte de verdade para a mesma pergunta, que é o
    defeito que este repositório já pagou duas vezes (A4, e as duas cópias do
    classificador de descritores).

    Então o script põe os arquivos em `DIRETORIO_ENTRADA` e o **RPA 1 os arquiva**
    — o que, de quebra, exercita a HU-02 e a HU-03 com arquivo real, que é o
    ponto da homologação.

    ## `para_operadora` — o atalho para testar o RPA 2 sozinho

    Quando se quer exercitar **só** o RPA 2, passar pelo RPA 1 é um passo a mais
    que pode falhar por motivo próprio, e aí não se sabe qual robô se está
    testando. Com `--semear --para-operadora ALGAR --referencia 202603` os
    Detrafs vão direto para `Detrafs Recebidos/`.

    ⚠️ Isto **não** é uma segunda implementação da HU-02: a operadora não é
    descoberta, é dita na linha de comando. Se ela estiver errada, os arquivos
    ficam na pasta errada e o teste mente — por isso não é o padrão.

    A expectativa é diferente: ela não é por operadora na árvore, vai direto para
    `CAMINHO_EXPECTATIVA_DETRAF/{pasta}/`.
    """
    linhas: list[str] = []

    if para_operadora:
        from comum.arquivos import estrutura_pastas as ep

        destino_detrafs = ep.caminho_detrafs_recebidos(
            operadora=para_operadora,
            aaaamm=referencia,
            raiz_operadoras=cfg.CAMINHO_OPERADORAS,
            criar=True,
        )
    else:
        destino_detrafs = cfg.DIRETORIO_ENTRADA

    detrafs = origem / "Detrafs recebidos"
    if detrafs.is_dir():
        linhas.append(f"  Detrafs -> {destino_detrafs}")
        if para_operadora:
            linhas.append(
                "    (direto na árvore da operadora, a pedido — o RPA 1 não vai "
                "arquivar estes)"
            )
        for arquivo in sorted(p for p in detrafs.iterdir() if p.is_file()):
            situacao = _copiar(arquivo, destino_detrafs / arquivo.name)
            linhas.append(f"    [{situacao:13s}] {arquivo.name}")
    else:
        linhas.append(f"  (sem pasta 'Detrafs recebidos' em {origem})")

    expectativa = origem / "Expectativa"
    if not expectativa.is_dir():
        linhas.append(f"  (sem pasta 'Expectativa' em {origem})")
        return linhas

    if cfg.CAMINHO_EXPECTATIVA_DETRAF is None:
        linhas.append("  CAMINHO_EXPECTATIVA_DETRAF não configurado — pulado")
        return linhas

    linhas.append(f"  Expectativa -> {cfg.CAMINHO_EXPECTATIVA_DETRAF}")
    for arquivo in sorted(p for p in expectativa.iterdir() if p.is_file()):
        pasta = _pasta_de_expectativa(arquivo.name, cfg.PASTAS_EXPECTATIVAS)
        if pasta is None:
            linhas.append(
                f"    [não roteado ] {arquivo.name}"
                f"  (nenhuma de {cfg.PASTAS_EXPECTATIVAS} aparece no nome)"
            )
            continue
        situacao = _copiar(
            arquivo, cfg.CAMINHO_EXPECTATIVA_DETRAF / pasta / arquivo.name
        )
        linhas.append(f"    [{situacao:13s}] {pasta}/{arquivo.name}")

    # A armadilha que este script não pode deixar passar em silêncio: o filtro
    # vazio ou errado faz o robô achar ZERO arquivos e terminar com sucesso.
    nomes = [p.name for p in expectativa.iterdir() if p.is_file()]
    casam = [
        nome
        for nome in nomes
        if any(sub in nome for sub in cfg.EXPECTATIVA_SUBSTRING)
    ]
    if nomes and not casam:
        linhas += [
            "",
            "  🔴 NENHUM arquivo de expectativa casa com "
            f"EXPECTATIVA_SUBSTRING={cfg.EXPECTATIVA_SUBSTRING}.",
            "     O RPA 2 vai encontrar zero arquivos e TERMINAR COM SUCESSO —",
            "     a falha é muda. Corrija a variável no .env.",
        ]
    elif nomes:
        linhas.append(f"    ({len(casam)}/{len(nomes)} casam com o filtro do RPA 2)")

    return linhas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="preparar_ambiente.py",
        description=(
            "Cria as pastas que os robôs leem e escrevem, a partir do que está "
            "no .env. Idempotente: rodar de novo não duplica nem apaga nada."
        ),
    )
    parser.add_argument(
        "--operadora",
        metavar="NOME",
        help=(
            "Também monta {operadora}/{ano}/{aaaamm}/ com as quatro subpastas. "
            "Exige --referencia."
        ),
    )
    parser.add_argument(
        "--referencia",
        metavar="AAAAMM",
        help="Mês de tráfego, para o --operadora.",
    )
    parser.add_argument(
        "--semear",
        action="store_true",
        help=(
            "Copia os insumos reais para onde os robôs os procuram: os Detrafs "
            "para DIRETORIO_ENTRADA (quem os arquiva é o RPA 1) e a expectativa "
            "para CAMINHO_EXPECTATIVA_DETRAF. Não sobrescreve o que já existe."
        ),
    )
    parser.add_argument(
        "--para-operadora",
        metavar="NOME",
        help=(
            "Só com --semear: põe os Detrafs direto em "
            "{operadora}/{ano}/{aaaamm}/Detrafs Recebidos/ em vez da entrada, "
            "para testar o RPA 2 sem passar pelo RPA 1. Exige --referencia."
        ),
    )
    parser.add_argument(
        "--de",
        metavar="PASTA",
        default="Insumos",
        help=(
            "Onde estão os insumos, com as subpastas 'Detrafs recebidos' e "
            "'Expectativa'. Relativa a unificado/. Default: Insumos"
        ),
    )
    args = parser.parse_args(argv)

    if args.operadora and not args.referencia:
        print("ERRO: --operadora exige --referencia AAAAMM.")
        return 2

    if args.para_operadora and not args.referencia:
        print("ERRO: --para-operadora exige --referencia AAAAMM.")
        return 2

    if args.para_operadora and not args.semear:
        print("ERRO: --para-operadora só faz sentido junto de --semear.")
        return 2

    if args.referencia and not (
        len(args.referencia) == 6 and args.referencia.isdigit()
    ):
        print(f"ERRO: '{args.referencia}' não é AAAAMM.")
        return 2

    from comum.config import configuration as cfg

    # Mesma recusa do `resetar_homologacao.py`. Aqui o risco é menor — criar
    # pasta não apaga nada —, mas apontar um compartilhamento de produção e sair
    # criando diretório é o tipo de coisa que ninguém quer descobrir depois.
    if cfg.ENV == "prod":
        print("=" * 70)
        print("  RECUSADO: o ambiente está em ENV=prod.")
        print("=" * 70)
        print(
            "\n  Este script cria pastas a partir do .env. Em produção elas\n"
            "  apontam para o compartilhamento de rede, e a estrutura de lá é\n"
            "  responsabilidade da operação — não de um script de homologação.\n\n"
            "  Ponha ENV=dev antes de rodar."
        )
        return 2

    print("=" * 70)
    print("  PREPARAÇÃO DO AMBIENTE")
    print("=" * 70)
    print(f"  raiz do projeto: {cfg.RAIZ_UNIFICADO}")
    print(f"  modo: {cfg.ENV}")
    print()

    erros = 0
    for nome, caminho in _pastas_da_configuracao(cfg):
        situacao = _criar(caminho)
        if situacao.startswith("ERRO"):
            erros += 1
        print(f"  [{situacao:11s}] {nome:30s} {caminho}")

    nao_configuradas = [
        nome
        for nome, valor in (
            ("CAMINHO_EXPECTATIVA_DETRAF", cfg.CAMINHO_EXPECTATIVA_DETRAF),
            ("CAMINHO_CONTROLE_CT", cfg.CAMINHO_CONTROLE_CT),
            ("DIRETORIO_EVIDENCIAS", cfg.DIRETORIO_EVIDENCIAS),
        )
        if valor is None
    ]
    if nao_configuradas:
        print("\n  Não configuradas no .env, portanto não criadas:")
        for nome in nao_configuradas:
            print(f"    {nome}")

    if args.operadora:
        print(f"\n  Mês da operadora {args.operadora} em {args.referencia}:")
        try:
            for linha in _preparar_mes_da_operadora(
                cfg, args.operadora, args.referencia
            ):
                print(linha)
        except (OSError, ValueError) as erro:
            print(f"    ERRO: {erro}")
            erros += 1

    if args.semear:
        origem = Path(args.de)
        if not origem.is_absolute():
            origem = cfg.RAIZ_UNIFICADO / origem

        print(f"\n  Semeando a partir de {origem}:")
        if not origem.is_dir():
            print(f"    ERRO: a pasta não existe.")
            erros += 1
        else:
            for linha in _semear(
                cfg, origem, args.para_operadora, args.referencia
            ):
                print(linha)

    print("\n" + "=" * 70)
    if erros:
        print(f"  {erros} problema(s) — ver acima.")
        return 1

    print("  Ambiente pronto.")
    print("\n  Próximos passos:")
    print("     python verificar_ambiente.py")
    print("       confere credenciais, banco e permissão de escrita de verdade")
    if args.semear and args.para_operadora:
        print()
        print("     python rpa2_validacao_apuracao/main.py --etapa validacao")
        print("       os Detrafs já estão na árvore — o RPA 1 foi pulado a pedido")
    elif args.semear:
        print()
        print("     python rpa1_captura/main.py --etapa processamento \\")
        print("            --referencia AAAAMM --dry-run")
        print("       arquiva os Detrafs na árvore — é ele quem identifica a")
        print("       operadora (HU-02), lendo a EOT credora de dentro do arquivo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
