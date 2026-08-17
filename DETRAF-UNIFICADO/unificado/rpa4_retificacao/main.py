"""RPA 4 — retificação de contestação (HU-21).

Quando a Vivo recupera tráfego que havia sido contestado no mês anterior, o
evento **"Recuperação"** precisa ser lançado no AGI, em `Contestação > Gerenciar`
(V2 ¶713). Este robô faz isso.

Origem: `projetos-origem/projeto-6-h20-h21/H21/`, migrado em 2026-08-10. A HU-20
do mesmo projeto ficou no RPA 3 (é conferência de relatório, não retificação).

## O gatilho não é uma agenda

É **condição de negócio**: só há trabalho quando existe linha com variação
negativa na contestação do mês anterior. Rodar num mês sem recuperação termina
com sucesso e zero processos — e isso é o resultado certo, não uma falha muda.

## Este robô mexe em coisa que não volta atrás

O evento de Recuperação no AGI é **irreversível**, e o AGI não devolve
confirmação de que salvou. Daí três coisas:

- `--dry-run` calcula tudo, mostra o que faria e **não abre o AGI**;
- `PERMITIR_ACESSO_AGI` continua sendo o interruptor, como nos outros robôs;
- antes de lançar, o robô confere na tela que o processo aberto é o esperado, e
  **aborta** se não for (`AGI.validar_processo_selecionado`).

⚠️ Boa parte da automação de tela veio da origem **sem calibração na VM** —
contagens de TAB, deslocamento em pixels e posição no dropdown. A primeira
execução real precisa de alguém olhando.

Uso::

    python rpa4_retificacao/main.py --referencia 202603 --dry-run
    python rpa4_retificacao/main.py --referencia 202603
    python rpa4_retificacao/main.py --etapa deteccao
"""

from __future__ import annotations

import sys
from pathlib import Path

# A base comum (`comum.*`) vive na raiz de `unificado/`; o código do robô
# (`src.*`) vive nesta pasta.
_RAIZ_RPA = Path(__file__).resolve().parent
_RAIZ_UNIFICADO = _RAIZ_RPA.parent

for _caminho in (str(_RAIZ_UNIFICADO), str(_RAIZ_RPA)):
    if _caminho not in sys.path:
        sys.path.insert(0, _caminho)

#: Nome deste robô. Define o arquivo de log e o sufixo das variáveis por robô
#: (`ENV_RPA4` vence `ENV`). Aplicado ao ambiente **antes** de
#: `comum.config.configuration` ser importado — a configuração lê o ambiente uma
#: vez, no import.
NOME_RPA = "rpa4_retificacao"

#: `deteccao` responde "há o que retificar?" sem tocar no AGI; `retificacao`
#: executa. Separadas porque a primeira é conferível a qualquer momento, e a
#: segunda não se desfaz.
ETAPAS = ("deteccao", "retificacao")


def main(argv: list[str] | None = None) -> int:
    """
    Executa o robô e devolve o código de saída do processo.

    Não-zero quando algum processo falhou: uma execução em que metade das
    recuperações não foi lançada não pode reportar sucesso ao agendador.
    """
    from comum.config import linha_de_comando as cli

    parser = cli.construir_parser(
        robo="RPA 4",
        descricao=(
            "Identifica o tráfego recuperado da contestação do mês anterior e "
            "lança o evento de Recuperação no AGI."
        ),
        etapas=ETAPAS,
        aceita_operadoras=False,
    )
    recorte = cli.aplicar(parser.parse_args(argv), NOME_RPA)

    # Só agora — depois de os argumentos terem virado ambiente.
    from comum.config.configuration import resumo_do_ambiente
    from comum.config.diagnostico_execucao import DiagnosticoDeExecucao
    from comum.config.logger_config import logger

    for linha in resumo_do_ambiente() + recorte.descrever():
        logger.info(f"[RPA 4] {linha}")

    diagnostico = DiagnosticoDeExecucao(
        robo=NOME_RPA,
        referencia=recorte.referencia or "",
        parametros=recorte.descrever(),
    )

    try:
        # Import tardio, pelo mesmo motivo do RPA 3: ele puxa o controller, que
        # puxa `bd_tabelas`, que resolve o banco no import. Banco fora do ar
        # matava o processo antes do `try`, e nenhum diagnóstico saía.
        with diagnostico.etapa("arranque") as _arranque:
            from src.main.process_handle import run

            _arranque.produzido = ["módulos carregados, banco resolvido"]

        processos_com_erro = run(
            referencia=recorte.referencia,
            etapa=recorte.etapa,
            diagnostico=diagnostico,
        )
    except Exception:
        logger.excecao(
            f"[RPA 4] Execução interrompida por erro não tratado — "
            f"{diagnostico.desfecho}"
        )
        return 1
    finally:
        destino = diagnostico.gravar()
        if destino:
            logger.info(f"[RPA 4] Diagnóstico das etapas em [{destino}]")

    if processos_com_erro:
        logger.error(
            f"[RPA 4] Execução concluída com {processos_com_erro} processo(s) em "
            f"erro — ver o log acima."
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
