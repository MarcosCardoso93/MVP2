"""RPA 3 — Contestação, Carga no AGI e Encontro de Contas.

Ponto de entrada do robô. Nenhum dos projetos de origem tinha um ``main.py``:
todos paravam em ``src/main/process_handle.py::run()``, sem nada que o chamasse.

Gatilho: sinalização do analista no WebFat, informando a decisão de contestação
(com ou sem retenção) para a operadora/remuneração.

O fluxo, na ordem da V2, para cada operadora do mês: consolida o Detraf recebido
contra a expectativa Vivo → HU-19 (despesa) → HU-12 (`_EXT`) → HU-13 (`_INT`) →
HU-14 (`_EXP` e cartas) → HU-16 (`CONT_PROC`). Depois, para o lote inteiro:
HU-17/HU-18 (carga no AGI), HU-15 (e-mail de contestação) e HU-20 (conferência do
relatório contra o Encontro de Contas).

A HU-14 pode emitir **mais de uma carta**: a operadora com linhas COM e SEM
retenção no mesmo mês recebe uma por cenário, cada uma com o seu número CT
(decisão Q25, de 2026-08-05). O `_EXP` continua único, e a HU-15 anexa os três.

---

⚠️ **O que depende de configuração para acontecer**

======================================  ==============================================
O quê                                   Do que depende
======================================  ==============================================
HU-15 — envio do e-mail                 ``CAMINHO_CONTATOS_OPERADORAS`` apontando para
                                        um CSV ``operadora;emails``, mais
                                        ``PERMITIR_ENVIO_EMAIL=true``. A tabela de
                                        contatos do WebFat não existe na V2 (Q16); o
                                        CSV é a ponte.
HU-14 — as cartas                       ``CAMINHO_CONTROLE_CT``. Sem ela a carta não é
                                        gerada, porque emitir arriscaria duplicar a
                                        numeração — os demais artefatos continuam
                                        saindo.
HU-17/18 — carga no AGI                 ``PERMITIR_UPLOAD_AGI=true``.
HU-20 — baixar o relatório              ``PERMITIR_ACESSO_AGI=true``. Desligado, a
                                        conferência roda sobre um relatório já
                                        baixado.
======================================  ==============================================

Os kill-switches são **desligados por padrão**: o fluxo roda inteiro, gera todos
os arquivos e registra o que faria — só não age para fora.

---

Uso::

    python main.py                                    # como na agenda
    python main.py --help                             # todos os argumentos
    python main.py --referencia 202507 --dry-run      # repete julho, sem efeito
    python main.py --operadoras CLARO --etapa carga   # repete só a carga da CLARO
"""

import sys
from pathlib import Path

# A base comum (`comum.*`) vive na raiz de `unificado/`; o código do robô
# (`src.*`) vive nesta pasta. Ambas entram no path para que os imports dos
# projetos de origem continuem valendo sem alteração.
_RAIZ_RPA = Path(__file__).resolve().parent
_RAIZ_UNIFICADO = _RAIZ_RPA.parent

for _caminho in (str(_RAIZ_UNIFICADO), str(_RAIZ_RPA)):
    if _caminho not in sys.path:
        sys.path.insert(0, _caminho)

#: Nome deste robô. Define o arquivo de log e o sufixo das variáveis por robô
#: (`ENV_RPA3` vence `ENV`). É aplicado ao ambiente **antes** de
#: `comum.config.configuration` ser importado — a configuração lê o ambiente uma
#: vez, no import, e depois disso mexer em `os.environ` não tem efeito.
NOME_RPA = "rpa3_contestacao_agi_ec"

ETAPAS = ("artefatos", "carga", "email", "verificacao")


def main(argv: list[str] | None = None) -> int:
    """
    Executa o robô e devolve o código de saída do processo.

    Não-zero quando alguma operadora falhou. Uma execução em que metade das
    operadoras não gerou artefato não pode reportar sucesso ao agendador — foi
    justamente esse tipo de silêncio que escondeu falhas antes.
    """
    from comum.config import linha_de_comando as cli

    parser = cli.construir_parser(
        robo="RPA 3",
        descricao=(
            "Gera os artefatos de contestação, carrega no AGI, envia o e-mail à "
            "operadora e confere o relatório contra o Encontro de Contas."
        ),
        etapas=ETAPAS,
        aceita_operadoras=True,
    )
    recorte = cli.aplicar(parser.parse_args(argv), NOME_RPA)

    # Só agora — depois de os argumentos terem virado ambiente.
    from comum.config.configuration import resumo_do_ambiente
    from comum.config.diagnostico_execucao import DiagnosticoDeExecucao
    from comum.config.logger_config import logger
    from comum.utils import pausa

    for linha in resumo_do_ambiente() + recorte.descrever():
        logger.info(f"[RPA 3] {linha}")

    # Um `.txt` por execução, com uma seção por etapa: o que ela recebeu, o que
    # produziu, e o erro COM traceback quando houver. Sem isto, o `except`
    # abaixo sabia que algo falhou e não sabia ONDE — e este robô tem quatro
    # etapas, três delas mexendo com sistema externo.
    diagnostico = DiagnosticoDeExecucao(
        robo=NOME_RPA,
        referencia=recorte.referencia or "",
        parametros=recorte.descrever(),
    )

    try:
        # O import entra AQUI, e não junto dos outros: ele puxa os
        # controllers, que puxam `bd_tabelas`, que resolve o banco no
        # import. SQLite faltando ou WebFat fora do ar matavam o
        # processo antes do `try` — e nenhum diagnóstico saía. É
        # justamente a falha que uma homologação encontra primeiro.
        with diagnostico.etapa("arranque") as _arranque:
            from src.main.process_handle import run

            _arranque.produzido = ["módulos carregados, banco resolvido"]

        operadoras_com_erro = run(
            operadoras=recorte.operadoras,
            referencia=recorte.referencia,
            etapa=recorte.etapa,
            diagnostico=diagnostico,
        )
    except pausa.ExecucaoCanceladaPeloOperador as cancelamento:
        # Não é erro: é decisão humana. Sai com 2 — distinto de 0 (sucesso) e
        # de 1 (falha) —, sem traceback, e dizendo onde parou. O que já foi
        # feito fica feito; as etapas são pontos de retomada, e a seguinte pode
        # ser rodada depois com --etapa.
        logger.warning(f"[RPA 3] {cancelamento} Nada além disto foi executado.")
        return 2
    except Exception:
        logger.excecao(
            f"[RPA 3] Execução interrompida por erro não tratado — "
            f"{diagnostico.desfecho}"
        )
        return 1
    finally:
        # No `finally`: o diagnóstico do que falhou é o mais útil de todos, e
        # ele só existe se for gravado também no caminho de erro.
        destino = diagnostico.gravar()
        if destino:
            logger.info(f"[RPA 3] Diagnóstico das etapas em [{destino}]")

    if operadoras_com_erro:
        logger.error(
            f"[RPA 3] Execução concluída com {operadoras_com_erro} operadora(s) "
            f"em erro — ver o log acima."
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
