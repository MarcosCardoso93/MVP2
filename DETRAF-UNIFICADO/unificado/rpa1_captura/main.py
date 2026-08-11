"""RPA 1 — Captura de Arquivos das Operadoras.

Ponto de entrada do robô. Nenhum dos projetos de origem tinha um ``main.py``:
todos paravam em ``src/main/process_handle.py::run()``, sem nada que o chamasse.

Gatilho: chegada de e-mail na caixa de Detraf, a partir da data de corte do mês —
**dia 5 por decisão do GP/dev em 2026-08-05**, que é o que a V1 registrava
("varredura diária após o dia 05"); a V2 removeu a regra e não pôs nada no lugar.
Configurável em ``DETRAF_DIA_LIBERACAO``.

Cobre HU-01 (captura no Outlook), HU-02 (identificação da operadora pela EOT
credora lida dentro do arquivo) e HU-03 (salvamento na árvore de pastas). Ver
``docs/01-entendimento/responsabilidades-dos-rpas.md``.

⚠️ **A captura depende do Outlook; a identificação e o salvamento, não.** Com
``--pasta-entrada`` o robô pula a HU-01 e processa arquivos já em disco — é como
se homologa dois terços dele numa máquina sem perfil de e-mail configurado.

Uso::

    python main.py                                   # como na agenda
    python main.py --help                            # todos os argumentos
    python main.py --pasta-entrada C:\\temp\\detrafs   # sem Outlook
    python main.py --referencia 202507 --dry-run     # repete julho, sem efeito
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
#: (`ENV_RPA1` vence `ENV`). É aplicado ao ambiente **antes** de
#: `comum.config.configuration` ser importado — a configuração lê o ambiente uma
#: vez, no import, e depois disso mexer em `os.environ` não tem efeito.
NOME_RPA = "rpa1_captura"

#: As duas etapas do robô — ver `FLUXO.md`.
ETAPAS = ("captura", "processamento")


def main(argv: list[str] | None = None) -> int:
    """Executa o robô e devolve o código de saída do processo."""
    from comum.config import linha_de_comando as cli

    parser = cli.construir_parser(
        robo="RPA 1",
        descricao=(
            "Captura os anexos da caixa de Detraf, identifica a operadora pela "
            "EOT credora e salva na árvore de pastas do mês."
        ),
        etapas=ETAPAS,
        aceita_pasta_entrada=True,
    )
    recorte = cli.aplicar(parser.parse_args(argv), NOME_RPA)

    # Só agora — depois de os argumentos terem virado ambiente.
    from comum.config.configuration import resumo_do_ambiente
    from comum.config.diagnostico_execucao import DiagnosticoDeExecucao
    from comum.config.logger_config import logger
    from comum.utils import pausa

    for linha in resumo_do_ambiente() + recorte.descrever():
        logger.info(f"[RPA 1] {linha}")

    # Um `.txt` por execução, com uma seção por etapa: o que ela recebeu, o que
    # produziu, e o erro COM traceback quando houver. Sem isto, o `except`
    # abaixo sabia que algo falhou e não sabia ONDE.
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

        run(pasta_entrada=recorte.pasta_entrada, etapa=recorte.etapa, diagnostico=diagnostico)
    except pausa.ExecucaoCanceladaPeloOperador as cancelamento:
        # Não é erro: é decisão humana. Sai com 2 — distinto de 0 (sucesso) e
        # de 1 (falha) —, sem traceback, e dizendo onde parou. O que já foi
        # feito fica feito; as etapas são pontos de retomada.
        logger.warning(f"[RPA 1] {cancelamento} Nada além disto foi executado.")
        return 2
    except Exception:
        logger.excecao(
            f"[RPA 1] Execução interrompida por erro não tratado — "
            f"{diagnostico.desfecho}"
        )
        return 1
    finally:
        # No `finally`: o diagnóstico do que falhou é o mais útil de todos, e
        # ele só existe se for gravado também no caminho de erro.
        destino = diagnostico.gravar()
        if destino:
            logger.info(f"[RPA 1] Diagnóstico das etapas em [{destino}]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
