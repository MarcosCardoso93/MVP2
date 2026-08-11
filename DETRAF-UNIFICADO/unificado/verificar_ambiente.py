"""Confere o ambiente antes de rodar qualquer robô.

Escrito em 2026-08-06, para a homologação manual.

Roda em segundos e responde, de uma vez, o que hoje só se descobre falhando:
as credenciais estão lá? as pastas existem e são graváveis? o banco conecta e
tem as colunas que o código usa? quais efeitos externos estão ligados?

Cada linha traz a correção ao lado. Código de saída não-zero quando há falha,
para poder entrar numa agenda antes do robô.

Uso::

    python verificar_ambiente.py                 # tudo
    python verificar_ambiente.py --rpa rpa3      # com o modo do RPA 3
    python verificar_ambiente.py --so-falhas     # só o que precisa de ação
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# 🔴 O console do Windows abre em cp1252, e o relatório usa `─`, `✅` e `🔴`. Sem
# isto o script levanta `UnicodeEncodeError` ao imprimir o primeiro cabeçalho de
# grupo — depois de já ter feito todas as verificações. O gate que existe para
# dizer se o ambiente está bom morria antes de dizer qualquer coisa.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: `NOME_RPA` de cada robô, para o `--rpa` reproduzir o modo em que ele roda.
ROBOS = {
    "rpa1": "rpa1_captura",
    "rpa2": "rpa2_validacao_apuracao",
    "rpa3": "rpa3_contestacao_agi_ec",
    "rpa4": "rpa4_retificacao",
}

#: Que grupos de verificação cada robô de fato depende.
#:
#: Sem isto, quem vai homologar o RPA 1 recebe uma falha de `DIRETORIO_AGI` e um
#: código de saída não-zero por causa de um sistema que aquele robô nunca abre. E
#: uma lista de falhas com item irrelevante dentro é uma lista que se aprende a
#: ignorar — que é como uma falha real passa despercebida.
#:
#: O provisionamento segue esta mesma ordem (docs/03-checklists/credenciais-e-acessos.md):
#: banco e pastas destravam o RPA 1 e o RPA 2 inteiros, sem nada do AGI.
GRUPOS_POR_ROBO = {
    # O RPA 1 ganhou "Validação" em 2026-08-06: ele passou a validar o arquivo
    # antes de salvá-lo, e a regra da EOT da Vivo depende de NOME_FANTASIA_VIVO.
    "rpa1": {"Configuração", "Pastas", "Validação", "Banco", "Outlook"},
    # E o RPA 2 perdeu "Outlook" na mesma mudança: ele deixou de responder à
    # operadora, e não sobrou nenhuma linha de código dele que fale com o
    # Outlook. Quem acusou a inconsistência foi o próprio teste de escopo.
    # O RPA 2 ganhou "SFTP" em 2026-08-10: a etapa `expectativa` baixa os
    # arquivos `_D` do ClickHub. É o único robô que fala com aquele host.
    "rpa2": {"Configuração", "Pastas", "Validação", "Filtros", "Banco", "SFTP"},
    # O RPA 3 usa tudo: além do AGI, ele manda o e-mail de contestação
    # (`envio_email_contestacao.py`) — o Outlook não é só do RPA 1 e do RPA 2.
    "rpa3": {
        "Configuração", "Pastas", "Validação", "Filtros", "Banco", "Outlook", "AGI",
    },
    # O RPA 4 lê a contestação no banco e opera o AGI. Não manda e-mail (a HU-21
    # não tem passo de notificação) e não processa arquivo de Detraf, então nem
    # "Outlook" nem "Filtros" dizem respeito a ele.
    "rpa4": {"Configuração", "Pastas", "Banco", "AGI"},
}

#: Por que cada grupo fica de fora — dito na tela, para a omissão não parecer
#: esquecimento de quem escreveu o verificador.
MOTIVO_FORA_DE_ESCOPO = {
    "AGI": "este robô não abre o AGI",
    "Filtros": "estas listas filtram arquivos que este robô não processa",
    "Outlook": "este robô não lê nem envia e-mail",
    "Validação": "este robô não abre arquivo de Detraf — lê a apuração no banco",
    "SFTP": "este robô não baixa a expectativa — ela já está em disco quando ele roda",
}


def _verificar_pastas(diag, cfg) -> list:
    """As pastas que cada robô lê e escreve, com quem precisa de escrita."""

    return [
        diag.verificar_pasta(
            "Pastas", "CAMINHO_OPERADORAS", cfg.CAMINHO_OPERADORAS,
            precisa_escrever=True,
        ),
        diag.verificar_pasta(
            "Pastas", "DIRETORIO_ENTRADA", cfg.DIRETORIO_ENTRADA,
            precisa_escrever=True,
        ),
        diag.verificar_pasta(
            "Pastas", "DIRETORIO_NAO_IDENTIFICADOS", cfg.DIRETORIO_NAO_IDENTIFICADOS,
            obrigatoria=False, precisa_escrever=True,
        ),
        # Onde o RPA 1 põe o que reprovou na validação. Sem escrita aqui, a
        # recusa não deixa evidência — e a evidência é o que a operadora vai
        # contestar quando receber a resposta.
        diag.verificar_pasta(
            "Pastas", "DIRETORIO_QUARENTENA", cfg.DIRETORIO_QUARENTENA,
            obrigatoria=False, precisa_escrever=True,
        ),
        # Onde o RPA 2 escreve TUDO desde 2026-08-10. Sem escrita aqui a etapa
        # de validação não copia um arquivo sequer — e a alternativa que ela
        # recusa, escrever no insumo, é o defeito que a área existe para fechar.
        diag.verificar_pasta(
            "Pastas", "DIRETORIO_TEMP", cfg.DIRETORIO_TEMP,
            obrigatoria=False, precisa_escrever=True,
        ),
        # A saída da validação é a ENTRADA do batimento. Sem escrita aqui a
        # etapa 1 termina "com sucesso" e a etapa 2 não acha nada — a falha só
        # apareceria como contestação zerada, dias depois.
        diag.verificar_pasta(
            "Pastas", "DIRETORIO_SAIDA_VALIDACAO", cfg.DIRETORIO_SAIDA_VALIDACAO,
            obrigatoria=False, precisa_escrever=True,
        ),
        diag.verificar_pasta(
            "Pastas", "CAMINHO_EXPECTATIVA_DETRAF", cfg.CAMINHO_EXPECTATIVA_DETRAF,
        ),
        diag.verificar_pasta(
            "Pastas", "CAMINHO_CONTROLE_CT", cfg.CAMINHO_CONTROLE_CT,
            obrigatoria=False, precisa_escrever=True,
        ),
        diag.verificar_pasta(
            "Pastas", "DIRETORIO_HISTORICO_ARQUIVOS", cfg.DIRETORIO_HISTORICO_ARQUIVOS,
            precisa_escrever=True,
        ),
        diag.verificar_pasta("Pastas", "RAIZ_LOGS", cfg.RAIZ_LOGS, precisa_escrever=True),
    ]


def _verificar_sftp(diag, cfg) -> list:
    """
    O SFTP de onde a expectativa vem (RPA 2, etapa `expectativa`).

    A credencial só é **exigida** quando o download está ligado — mesma regra do
    AGI. Com o kill-switch desligado a etapa não conecta, e cobrar credencial
    seria a falha irrelevante que o recorte por robô existe para tirar.
    """
    obrigatoria = cfg.PERMITIR_DOWNLOAD_SFTP

    resultados = [
        diag.verificar_credencial(
            "SFTP", "CLICKHUB_SFTP_HOST", cfg.SFTP_HOST,
            obrigatoria=obrigatoria,
        ),
        diag.verificar_credencial(
            "SFTP", "CLICKHUB_SFTP_USER", cfg.SFTP_USUARIO,
            obrigatoria=obrigatoria,
        ),
        diag.verificar_credencial(
            "SFTP", "CLICKHUB_SFTP_PASSWORD", cfg.SFTP_SENHA,
            obrigatoria=obrigatoria,
        ),
    ]

    # A pasta de destino precisa ser gravável — é a única do projeto que era
    # somente leitura até a captação existir.
    resultados.append(
        diag.verificar_pasta(
            "SFTP", "CAMINHO_EXPECTATIVA_DETRAF (destino do download)",
            cfg.CAMINHO_EXPECTATIVA_DETRAF,
            obrigatoria=False, precisa_escrever=True,
        )
    )

    # 🔴 Baixar para uma pasta que o RPA 2 não lê é trabalho jogado fora, e o
    # sintoma seria "a expectativa não apareceu" — sem erro em lugar nenhum.
    # Esta conferência só existe em execução real: sob pytest o `.env` não é
    # lido, e `PASTAS_EXPECTATIVAS` vem vazia por design.
    from comum.integracoes.sftp import MAPA_PASTAS

    lidas = {pasta.strip().upper() for pasta in cfg.PASTAS_EXPECTATIVAS}
    orfas = sorted(
        {destino for destino in MAPA_PASTAS.values()}
        - {destino for destino in MAPA_PASTAS.values() if destino.upper() in lidas}
    )
    resultados.append(
        diag.Resultado(
            "SFTP",
            "destinos do download",
            "ok" if not orfas else "falha",
            (
                f"as {len(set(MAPA_PASTAS.values()))} pastas baixadas estão em "
                f"PASTAS_EXPECTATIVAS"
                if not orfas
                else f"baixadas e NÃO lidas: {', '.join(orfas)}"
            ),
            (
                None
                if not orfas
                else "Acrescente-as a PASTAS_EXPECTATIVAS no .env, ou tire-as de "
                     "MAPA_PASTAS — hoje o robô baixaria e ninguém leria."
            ),
        )
    )
    return resultados


def _verificar_filtros(diag, cfg) -> list:
    """
    As listas que, vazias, fazem o robô processar nada e terminar bem.

    São o oposto de uma falha barulhenta: elas não quebram, elas **esvaziam**.
    Um mês inteiro pode passar antes de alguém notar que o batimento nunca leu
    um arquivo.
    """
    return [
        diag.verificar_lista_de_filtro(
            "Filtros", "ARQUIVOS_VALIDADOS", cfg.ARQUIVOS_VALIDADOS,
            "É o que o BATIMENTO do RPA 2 usa para achar os arquivos que a "
            "validação aprovou (ela os renomeia acrescentando `_ENV`).",
        ),
        diag.verificar_lista_de_filtro(
            "Filtros", "EXPECTATIVA_SUBSTRING", cfg.EXPECTATIVA_SUBSTRING,
            "É o que identifica um arquivo de expectativa Vivo pelo nome.",
        ),
        diag.verificar_lista_de_filtro(
            "Filtros", "PASTAS_EXPECTATIVAS", cfg.PASTAS_EXPECTATIVAS,
            "São as pastas varridas em busca da expectativa Vivo.",
        ),
    ]


def _verificar_validacao(diag, cfg) -> list:
    """
    O que a validação de conteúdo precisa — e que os três robôs usam.

    Grupo separado de "Filtros" desde 2026-08-06. Quando o RPA 1 passou a
    validar, ele passou a depender de UMA das quatro variáveis daquele grupo; dar
    o grupo inteiro a ele traria de volta o ruído que o `GRUPOS_POR_ROBO` existe
    para tirar — três listas de arquivos que o RPA 1 nunca lê.
    """
    return [
        diag.verificar_lista_de_filtro(
            "Validação", "NOME_FANTASIA_VIVO", cfg.NOME_FANTASIA_VIVO,
            "É a lista contra a qual a 2ª coluna do Detraf (EOT da Vivo) é "
            "validada.",
        ),
    ]


def _origem(cfg, *nomes: str) -> str:
    """
    Qual variável do `.env` respondeu, entre sinônimos.

    Mesma ideia da `origem()` de `configuration.resumo_de_arranque`: "o RPA 3
    está em homologação" é metade da informação; a outra metade é **qual linha
    do `.env` mandou nisso**, que é o que se procura quando o robô rodou no
    ambiente errado.
    """
    for nome in nomes:
        registrada = cfg.ORIGEM_DAS_VARIAVEIS.get(nome, "")
        if registrada and not registrada.startswith("("):
            return registrada
    return "(default do código)"


def _verificar_agi(diag, cfg) -> list:
    """Executável, credenciais e as imagens da automação por reconhecimento."""

    resultados = [
        diag.verificar_credencial(
            "AGI", "RPA_DETRAF_DESPESA_AGI_USER", cfg.USUARIO_AGI,
            obrigatoria=cfg.PERMITIR_ACESSO_AGI or cfg.PERMITIR_UPLOAD_AGI,
        ),
        diag.verificar_credencial(
            "AGI", "RPA_DETRAF_DESPESA_AGI_PASSWORD", cfg.SENHA_AGI,
            obrigatoria=cfg.PERMITIR_ACESSO_AGI or cfg.PERMITIR_UPLOAD_AGI,
        ),
    ]

    if cfg.DIRETORIO_AGI is None:
        resultados.append(
            diag.Resultado(
                "AGI", "DIRETORIO_AGI", "aviso", "não configurado",
                "Só é necessário se algum kill-switch do AGI for ligado.",
            )
        )
    elif not Path(cfg.DIRETORIO_AGI).is_file():
        resultados.append(
            diag.Resultado(
                "AGI", "DIRETORIO_AGI", "falha",
                f"executável não encontrado: [{cfg.DIRETORIO_AGI}]",
                "Aponte para o `portal_air_vivo.exe` do Portal AIR — em "
                "`aplicacao_agi/Portal AIR/portal_air_vivo.exe`, relativo a "
                "`unificado/`. Não é o `adl.exe`, que fica no `runtime/` ao lado.",
            )
        )
    else:
        resultados.append(
            diag.Resultado("AGI", "DIRETORIO_AGI", "ok", f"[{cfg.DIRETORIO_AGI}]")
        )

    # Ambiente inválido é falha silenciosa no pior lugar: o robô só descobre ao
    # tentar clicar, com o aplicativo já aberto.
    if cfg.AGI_AMBIENTE not in cfg.AMBIENTES_AGI:
        resultados.append(
            diag.Resultado(
                "AGI", "AGI_AMBIENTE", "falha",
                f"valor inválido: [{cfg.AGI_AMBIENTE}]",
                f"Use um de {list(cfg.AMBIENTES_AGI)}.",
            )
        )
    else:
        resultados.append(
            diag.Resultado(
                "AGI", "AGI_AMBIENTE", "ok",
                f"{cfg.AGI_AMBIENTE} (de {_origem(cfg, 'AGI_AMBIENTE')})",
            )
        )

    # Entra na REGEX do título do diálogo de download. Sem ele, a HU-20 falha
    # DEPOIS de abrir o AGI, logar e baixar — o pedaço caro do fluxo.
    #
    # O host é derivado do ambiente, então a mensagem diz qual variável está
    # faltando de fato — `AGI_JANELA_HOST` genérico não é mais o nome usual.
    variavel_host = f"AGI_JANELA_HOST_{cfg.AGI_AMBIENTE.upper()}"
    if not cfg.AGI_JANELA_HOST:
        exigido = cfg.PERMITIR_ACESSO_AGI or cfg.PERMITIR_UPLOAD_AGI
        resultados.append(
            diag.Resultado(
                "AGI", variavel_host,
                "falha" if exigido else "aviso",
                "não configurado",
                "Ele entra na regex do título do diálogo de download. Sem ele a "
                "HU-20 falha DEPOIS de abrir o AGI e logar. O que o portal "
                "aponta: produção 10.238.6.120, homologação 10.129.178.159.",
            )
        )
    else:
        resultados.append(
            diag.Resultado(
                "AGI", variavel_host, "ok",
                f"{cfg.AGI_JANELA_HOST} "
                f"(de {_origem(cfg, variavel_host, 'AGI_JANELA_HOST')})",
            )
        )

    # As imagens são comparadas pixel a pixel; faltar uma é falha certa no meio
    # do fluxo, depois de o AGI já ter sido aberto e logado.
    #
    # A raiz vem do próprio módulo do AGI, e não repetida aqui: quando as imagens
    # subiram para `comum/` (2026-08-10), este caminho ficou apontando para a
    # pasta antiga e o gate passou a acusar "pasta não encontrada" — uma falha
    # inventada por um caminho duplicado.
    from comum.integracoes.agi import RAIZ_IMAGENS

    pasta_imagens = RAIZ_IMAGENS
    if not pasta_imagens.is_dir():
        resultados.append(
            diag.Resultado(
                "AGI", "imagens", "falha", f"pasta não encontrada: [{pasta_imagens}]",
                "A automação do AGI é por reconhecimento de imagem e não roda sem elas.",
            )
        )
    else:
        total = len(list(pasta_imagens.rglob("*.png")))
        resultados.append(
            diag.Resultado(
                "AGI", "imagens", "ok" if total else "falha",
                f"{total} imagem(ns) em [{pasta_imagens.name}]",
                "" if total else "Nenhuma imagem — a automação do AGI não funciona.",
            )
        )
        resultados.append(
            diag.Resultado(
                "AGI", "resolução", "aviso",
                "27 das 30 imagens vieram de outra máquina",
                "Elas são comparadas pixel a pixel. As 3 do portal já foram "
                "recapturadas aqui — `python ensaiar_portal_agi.py` as confere "
                "sozinho. As 27 restantes são telas de dentro do AGI e só dá "
                "para conferi-las com acesso a ele. Se um passo falhar por "
                "imagem não encontrada, recapture NESTA VM — ver "
                "docs/03-checklists/checklist-validacao-agi.md.",
            )
        )

    return resultados


def _verificar_outlook(diag, cfg) -> list:
    """Conta e pastas do Outlook — sem abrir a conexão COM."""

    resultados = []

    if not cfg.OUTLOOK_ACCOUNT:
        resultados.append(
            diag.Resultado(
                "Outlook", "OUTLOOK_ACCOUNT", "falha", "não configurada",
                "O RPA 1 precisa dela para achar a caixa. Para homologar sem "
                "Outlook, use `main.py --pasta-entrada CAMINHO`.",
            )
        )
    else:
        resultados.append(
            diag.Resultado(
                "Outlook", "OUTLOOK_ACCOUNT", "ok", cfg.OUTLOOK_ACCOUNT
            )
        )

    resultados.append(
        diag.Resultado(
            "Outlook", "pastas", "ok",
            f"origem [{cfg.OUTLOOK_DETRAF_DESPESAS_FOLDER}], "
            f"destino [{cfg.OUTLOOK_PROCESSADOS_FOLDER}]",
        )
    )

    # O template da resposta à operadora. Nunca foi conferido em lugar nenhum:
    # a ausência dele só aparecia como uma linha de log no fim da execução, e o
    # robô reportava sucesso tendo recusado arquivos sem avisar ninguém.
    template = cfg.CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO
    if template is None:
        resultados.append(
            diag.Resultado(
                "Outlook", "CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO", "aviso",
                "não configurado",
                "Sem ele, o arquivo reprovado vai para a quarentena mas a "
                "operadora NÃO é avisada.",
            )
        )
    elif not Path(template).is_file():
        resultados.append(
            diag.Resultado(
                "Outlook", "CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO", "falha",
                f"arquivo não encontrado: [{template}]",
                "É o corpo do e-mail de recusa. Placeholders aceitos: "
                "{nome_arquivo} {assunto_original} {remetente} "
                "{data_recebimento} {motivos}.",
            )
        )
    else:
        resultados.append(
            diag.Resultado(
                "Outlook", "CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO", "ok",
                f"[{Path(template).name}]",
            )
        )

    return resultados


def _imprimir(resultados, so_falhas: bool) -> None:
    grupo_atual = None

    for resultado in resultados:
        if so_falhas and resultado.situacao == "ok":
            continue

        if resultado.grupo != grupo_atual:
            grupo_atual = resultado.grupo
            print(f"\n── {grupo_atual} " + "─" * max(0, 66 - len(grupo_atual)))

        print(f"  [{resultado.simbolo}] {resultado.item:34s} {resultado.detalhe}")
        if resultado.correcao:
            for linha in _quebrar(resultado.correcao, 62):
                print(f"           -> {linha}")


def _quebrar(texto: str, largura: int) -> list[str]:
    """Quebra o texto em linhas, para a correção não sair de qualquer jeito."""
    linhas, atual = [], ""
    for palavra in texto.split():
        if len(atual) + len(palavra) + 1 > largura:
            linhas.append(atual)
            atual = palavra
        else:
            atual = f"{atual} {palavra}".strip()
    if atual:
        linhas.append(atual)
    return linhas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verificar_ambiente.py",
        description=(
            "Confere credenciais, pastas, permissões de escrita, banco e "
            "kill-switches. Cada falha vem com o que fazer."
        ),
    )
    parser.add_argument(
        "--rpa",
        choices=sorted(ROBOS),
        help=(
            "Confere com o modo deste robô. Importa porque as variáveis aceitam "
            "sufixo por robô (ENV_RPA3 vence ENV) — sem isto, você confere o "
            "modo geral, que pode não ser o que o robô vai usar."
        ),
    )
    parser.add_argument(
        "--so-falhas",
        action="store_true",
        help="Esconde o que está OK. Útil na segunda passada.",
    )
    args = parser.parse_args(argv)

    if args.rpa:
        os.environ["NOME_RPA"] = ROBOS[args.rpa]

    from comum.config import configuration as cfg
    from comum.config import diagnostico as diag

    print("=" * 70)
    print("  VERIFICAÇÃO DE AMBIENTE — RPAs do Detraf")
    print("=" * 70)
    for linha in cfg.resumo_do_ambiente():
        print(f"  {linha}")

    resultados: list = []
    resultados += diag.verificar_variaveis(RAIZ / ".env.example")
    resultados += _verificar_pastas(diag, cfg)
    resultados += _verificar_validacao(diag, cfg)
    resultados += _verificar_filtros(diag, cfg)
    resultados += diag.verificar_banco()
    resultados += _verificar_sftp(diag, cfg)
    resultados += _verificar_outlook(diag, cfg)
    resultados += _verificar_agi(diag, cfg)

    if args.rpa:
        no_escopo = GRUPOS_POR_ROBO[args.rpa]
        fora = sorted({r.grupo for r in resultados} - no_escopo)
        resultados = [r for r in resultados if r.grupo in no_escopo]
        if fora:
            print(f"\n  Fora do escopo de {args.rpa}, não conferido:")
            for grupo in fora:
                motivo = MOTIVO_FORA_DE_ESCOPO.get(grupo, "não é usado por este robô")
                print(f"    {grupo} — {motivo}")

    _imprimir(resultados, args.so_falhas)

    falhas = [r for r in resultados if r.situacao == "falha"]
    avisos = [r for r in resultados if r.situacao == "aviso"]

    print("\n" + "=" * 70)
    print(
        f"  {len(resultados) - len(falhas) - len(avisos)} OK, "
        f"{len(avisos)} aviso(s), {len(falhas)} falha(s)"
    )

    if falhas:
        print("\n  🔴 Corrija as falhas antes de rodar os robôs:")
        for resultado in falhas:
            print(f"     - {resultado.grupo}/{resultado.item}: {resultado.detalhe}")
    else:
        print("\n  ✅ Nenhuma falha. O ambiente comporta uma execução.")

    # A linha final é a que decide se a rodada escreve para fora — e é a que
    # alguém vai procurar depois, se algo sair sem querer.
    ligados = [
        nome
        for nome, ligado in (
            ("PERMITIR_ENVIO_EMAIL", cfg.PERMITIR_ENVIO_EMAIL),
            ("PERMITIR_UPLOAD_AGI", cfg.PERMITIR_UPLOAD_AGI),
            ("PERMITIR_ACESSO_AGI", cfg.PERMITIR_ACESSO_AGI),
            ("NOTIFICAR_OPERADORA_ENVIAR", cfg.NOTIFICAR_OPERADORA_ENVIAR),
        )
        if ligado
    ]
    if ligados:
        print(f"\n  ⚠️  EFEITOS EXTERNOS LIGADOS: {', '.join(ligados)}")
        print("     Esta configuração AGE PARA FORA da máquina.")
    else:
        print("\n  🔒 Nenhum efeito externo ligado — nada sai desta máquina.")

    # A pausa entre etapas é da mesma natureza dos kill-switches: muda o que a
    # execução faz, e esquecê-la ligada numa agenda travaria o robô.
    from comum.utils import pausa as _pausa

    pausa_ligada, motivo_pausa = _pausa.esta_habilitada()
    if pausa_ligada:
        print(
            "\n  ⏸️  PAUSA ENTRE ETAPAS LIGADA: a execução vai parar ao fim de cada"
            "\n     etapa e esperar confirmação. Não use isto numa agenda."
        )
    elif cfg.PAUSA_ENTRE_ETAPAS:
        print(f"\n  ⏸️  PAUSA_ENTRE_ETAPAS ligada, mas NÃO vai agir: {motivo_pausa}.")

    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
