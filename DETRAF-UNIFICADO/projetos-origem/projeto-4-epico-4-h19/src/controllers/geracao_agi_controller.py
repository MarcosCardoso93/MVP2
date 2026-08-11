"""Controller de orquestração da geração dos artefatos do Épico 4.

Segue o padrão de "orquestração fina" da referência: o controller **apenas
instancia e dispara** os services, sem lógica de negócio nem manipulação de
DataFrame (AI/01 §1).

Neste Bootstrap os services ainda não existem — os passos são *stubs* que serão
substituídos pelas HUs (Consolidação → EXT → INT → _ENV/carta → CONT_PROC).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from src.config.logger_config import logger
from src.models.repository.repositorio_tabelas import RepositorioTabelas
from src.services import encontro_contas as ec
from src.services import geracao_cont_proc as gcp
from src.utils.decoradores import log_execucao


class GeracaoAgiController:
    """Orquestra a geração dos arquivos de contestação/carga AGI do Épico 4."""

    def __init__(self, repositorio: RepositorioTabelas | None = None) -> None:
        # Os demais services serão injetados/instanciados aqui conforme a orquestração
        # completa for montada (T-120): consolidacao_contestacao, geracao_ext,
        # geracao_int, geracao_env_carta.
        self.repositorio = repositorio or RepositorioTabelas()

    @log_execucao
    def gerar_cont_proc(
        self,
        df_contest: pd.DataFrame,
        operadora: str,
        referencia: str,
        raiz_operadoras: Path | None = None,
    ) -> Optional[Path]:
        """
        HU-16: gera o CONT_PROC e, **só se o arquivo for gravado**, regrava
        ``tipo_contestacao`` no banco (D-19, V2 pág. 34).

        A ordem importa: a V2 descreve o writeback *depois* de "o robô copia as linhas
        alteradas e salva em um arquivo". Nos cenários "sem contestação" o arquivo não
        é gerado e, portanto, nada é regravado.

        Returns:
            Caminho do CONT_PROC gravado, ou ``None`` se não houver o que contestar.
        """

        linhas = gcp.montar_linhas_cont_proc(
            df_contest=df_contest,
            referencia=referencia,
            obter_tipo_contestacao=self.repositorio.obter_tipo_contestacao,
        )

        caminho = gcp.gerar_arquivo_cont_proc(
            linhas_cont_proc=linhas,
            operadora=operadora,
            aaaamm=referencia,
            raiz_operadoras=raiz_operadoras,
        )

        if caminho is None:
            return None

        contestadas = gcp.selecionar_linhas_contestadas(
            df_contest=df_contest,
            referencia=referencia,
            obter_tipo_contestacao=self.repositorio.obter_tipo_contestacao,
        )
        self.repositorio.atualizar_tipo_contestacao(contestadas)

        return caminho

    @log_execucao
    def atualizar_despesa_contestacao(
        self, df_contest: pd.DataFrame, referencia: str
    ) -> dict:
        """
        HU-19: atualiza a despesa apresentada pela operadora (D-20, V2 pág. 38).

        Returns:
            Resumo do lote: ``{"atualizadas": int, "ausentes": list[dict]}``.
        """

        atualizacoes = ec.preparar_atualizacoes_despesa_contestacao(
            df_contest=df_contest, referencia=referencia
        )
        return self.repositorio.atualizar_despesa_contestacao(atualizacoes)

    @log_execucao
    def gerar_artefatos(self) -> None:
        """
        Ponto de entrada da orquestração do Épico 4.

        STUB de Bootstrap (T-009): registra a sequência-alvo. Cada passo será
        preenchido pela HU correspondente, sempre delegando ao service.
        """

        logger.info("[Épico 4] Orquestração iniciada (stub de Bootstrap).")
        logger.info("[Épico 4] Etapa pendente: Consolidação (Base_Contestação).")
        logger.info("[Épico 4] Etapa pendente: HU-12 EXT.")
        logger.info("[Épico 4] Etapa pendente: HU-13 INT.")
        logger.info("[Épico 4] Etapa pendente: HU-14 _ENV + carta.")
        logger.info(
            "[Épico 4] Etapa pendente: HU-16 CONT_PROC (ver `gerar_cont_proc`)."
        )
        logger.info(
            "[Épico 4] Etapa pendente: HU-19 despesa "
            "(ver `atualizar_despesa_contestacao`)."
        )
        logger.info("[Épico 4] Orquestração finalizada (nenhum artefato gerado ainda).")
