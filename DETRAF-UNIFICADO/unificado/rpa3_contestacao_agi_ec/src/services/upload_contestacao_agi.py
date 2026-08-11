"""Serviço da HU-18 — upload do CONT_PROC no AGI (Contestação > Gerenciar).

Origem: `projeto-7-epico-5-carga-agi/src/services/AGI/Upload_Contestacao.py`. Ver
`trabalho/inventarios/inventario-projeto-7.md` §4.

Sobe no AGI os arquivos ``CONT_PROC_MASCARA_{operadora}_{aaaamm}`` que a HU-16
(`geracao_cont_proc.py`) deixou na subpasta ``AGI`` de cada operadora.

Diferente da HU-17, esta tela tem um passo a mais: depois que o AGI carrega o
arquivo, é preciso clicar em **Salvar** (V2, parágrafo 322).

## ⚠️ Nunca foi executado

A tela "Contestação > Gerenciar" **não existia** no fluxo de Receita — não há
código validado do qual copiar. O original declarava, no próprio cabeçalho:
*"TUDO abaixo é ESQUELETO/TODO"*, e os dois métodos de interface eram corpos
comentados.

O que mudou desde então: **as 4 imagens já foram capturadas**
(`comum/view/imagens/AGI_Upload_Contestacao/`), o que permitiu escrever a
navegação de verdade. Ela segue o mesmo padrão da HU-17, que é validado — mas
esta sequência específica nunca rodou contra o AGI.

Falta confirmar na VM o **título do diálogo nativo de upload nesta tela**. Aqui
está o mesmo título da HU-17; pode ser outro. É a primeira coisa a checar quando
houver acesso.
"""

from __future__ import annotations

import time
from pathlib import Path

import pyautogui

from comum.arquivos import estrutura_pastas as ep
from comum.config import configuration
from comum.config.logger_config import logger
from comum.dados.repositorio_tabelas import RepositorioTabelas
from comum.utils.decoradores import log_execucao
from comum.integracoes.agi import AGI, AGIError, RAIZ_IMAGENS
from src.services.upload_detraf_agi import capturar_evidencia_sucesso

#: Valores da coluna ``carga_agi``. O ``"não carregado"`` é o que o RPA 2 grava
#: ao criar a linha (`criacao_arquivo_contestacao.py`); os outros dois são o
#: desfecho que a V2 pede que o robô registre.
CARGA_AGI_CARREGADO = "carregado"
CARGA_AGI_ERRO = "erro na carga"

_IMAGENS = RAIZ_IMAGENS / "AGI_Upload_Contestacao"

img_bnt_contestacao = str(_IMAGENS / "bnt_contestacao.png")
img_bnt_submenu_gerenciar = str(_IMAGENS / "bnt_submenu_gerenciar.png")
img_bnt_upload_contestacao = str(_IMAGENS / "bnt_upload_contestacao.png")
img_bnt_salvar_contestacao = str(_IMAGENS / "bnt_salvar_contestacao.png")

#: Prefixo do arquivo produzido pela HU-16 (`nomenclatura.nome_cont_proc`).
PREFIXO_CONT_PROC = "CONT_PROC_MASCARA"


def listar_arquivos_contestacao(
    operadoras: list[str],
    aaaamm: str,
    raiz_operadoras: Path | None = None,
) -> list[tuple[str, Path]]:
    """
    Lista os ``CONT_PROC`` do mês, por operadora.

    Como na HU-17, a busca deixou de varrer uma pasta plana e passa por
    `estrutura_pastas`.

    ⚠️ A pasta é a **AGI**, não a ``Contestações``. Quem manda é o gerador: a
    HU-16 grava em `caminho_agi` (`geracao_cont_proc.py:263`, seguindo AI/10 §2).
    Esta função apontava para `caminho_contestacoes` e nunca teria encontrado o
    arquivo — o defeito passou despercebido porque nada encadeava as duas HUs.
    """

    pendencias: list[tuple[str, Path]] = []

    for operadora in operadoras:
        pasta = ep.caminho_agi(operadora, aaaamm, raiz_operadoras)
        if not pasta.is_dir():
            logger.info(
                f"[HU-18] Sem pasta AGI para {operadora}/{aaaamm}: [{pasta}]."
            )
            continue

        encontrados = sorted(
            caminho
            for caminho in pasta.glob(f"{PREFIXO_CONT_PROC}*")
            if caminho.is_file()
        )
        if not encontrados:
            logger.info(f"[HU-18] Nenhum {PREFIXO_CONT_PROC} em [{pasta}].")

        pendencias.extend((operadora, caminho) for caminho in encontrados)

    return pendencias


class UploadContestacaoAGI:
    """Sobe os CONT_PROC do mês no AGI."""

    def __init__(
        self, agi: AGI | None = None, repositorio: RepositorioTabelas | None = None
    ) -> None:
        self.agi = agi or AGI()
        self.repositorio = repositorio or RepositorioTabelas()

    @log_execucao
    def executar(
        self,
        operadoras: list[str],
        aaaamm: str,
        raiz_operadoras: Path | None = None,
    ) -> None:
        """
        Fluxo completo. Respeita `PERMITIR_UPLOAD_AGI` — ver `upload_detraf_agi`.

        A navegação até a tela é feita **uma vez**; depois todos os arquivos sobem
        pela mesma tela, sem refazer o caminho pelo menu a cada um.
        """

        pendencias = listar_arquivos_contestacao(operadoras, aaaamm, raiz_operadoras)
        if not pendencias:
            logger.info(f"[HU-18] Nenhum {PREFIXO_CONT_PROC} pendente; nada a fazer.")
            return

        if not configuration.PERMITIR_UPLOAD_AGI:
            logger.info(
                f"[MODO SEGURO] PERMITIR_UPLOAD_AGI=false — {len(pendencias)} arquivo(s) "
                "de contestação pendente(s), nada enviado ao AGI:"
            )
            for operadora, caminho in pendencias:
                logger.info(f"  {operadora}: {caminho.name}")
            return

        self.agi.inicializar()
        try:
            self.agi.acessar_ambiente()
            self.agi.login()
            self.navegar_contestacao_gerenciar()

            for operadora, caminho in pendencias:
                try:
                    self.upload_um_arquivo(caminho)
                    capturar_evidencia_sucesso(caminho.stem, prefixo="evidencia_contestacao")
                    logger.info(f"[HU-18] Upload concluído: {operadora} / {caminho.name}.")
                    status = CARGA_AGI_CARREGADO
                except Exception as exc:
                    logger.excecao(
                        f"[HU-18] Falha no upload de {operadora} / {caminho.name}: {exc}"
                    )
                    status = CARGA_AGI_ERRO

                # A V2 pede este registro logo após o Salvar da tela: é a
                # confirmação de carga que o WebFat espera. Gravar também no
                # fracasso é deliberado — "erro na carga" é informação; deixar
                # "não carregado" faria a falha parecer uma execução que nunca
                # aconteceu.
                self._registrar_carga(operadora, aaaamm, status)
                time.sleep(1)
        finally:
            self.agi.fechar()

    def _registrar_carga(self, operadora: str, aaaamm: str, status: str) -> None:
        """
        Grava `carga_agi` no banco, sem deixar a falha derrubar o lote.

        O upload no AGI já aconteceu e não se desfaz. Se o banco estiver fora, o
        certo é gritar no log e seguir para a próxima operadora — abortar aqui
        deixaria arquivos carregados no AGI e nenhum registro de quais foram.
        """
        try:
            self.repositorio.atualizar_carga_agi(operadora, aaaamm, status)
        except Exception as exc:
            logger.excecao(
                f"[HU-18] Upload de {operadora}/{aaaamm} terminou como '{status}', "
                f"mas o registro em carga_agi FALHOU: {exc}. O AGI e o WebFat "
                f"ficaram fora de sincronia para esta operadora."
            )

    def navegar_contestacao_gerenciar(self, tentativas: int = 10) -> None:
        """Menu ``Contestação > Gerenciar``."""

        for _ in range(tentativas):
            if not self.agi._wait_appear(img_bnt_contestacao, timeout=30):
                continue
            if not self.agi._click(img_bnt_contestacao):
                continue
            pyautogui.moveRel(0, 70)
            if not self.agi._wait_appear(img_bnt_submenu_gerenciar, timeout=15):
                continue
            if self.agi._click(img_bnt_submenu_gerenciar):
                return

        raise AGIError(
            f"Não foi possível chegar a 'Contestação > Gerenciar' em {tentativas} tentativas."
        )

    def upload_um_arquivo(self, caminho: Path) -> None:
        """Upload + o clique em **Salvar**, que só existe nesta tela."""

        if not self.agi._wait_appear(img_bnt_upload_contestacao, timeout=40):
            raise AGIError(f"Botão de upload não apareceu para [{caminho.name}].")
        self.agi._click(img_bnt_upload_contestacao)

        # ⚠️ Título não confirmado nesta tela — ver o cabeçalho do módulo.
        self.agi.janela_salvar(
            caminho,
            nome_janela=(
                "(Select location for download by|Selecionar local para download de) "
                f"{configuration.AGI_JANELA_HOST}"
            ),
        )

        if not self.agi._wait_appear(img_bnt_salvar_contestacao, timeout=60):
            raise AGIError(f"Botão 'Salvar' não apareceu após o upload de [{caminho.name}].")
        self.agi._click(img_bnt_salvar_contestacao)
