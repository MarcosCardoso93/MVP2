"""Orquestra a captura de e-mails da pasta 'Detraf Despesas' (HU-01)."""

import re
from datetime import datetime
from pathlib import Path

from src.config.logger_config import logger
from src.config.outlook_config import OutlookConfig
from src.models.dto.arquivo_para_processar import ArquivoParaProcessar
from src.models.dto.registro_rastreamento import RegistroRastreamento
from src.models.repository.rastreamento_repository import RastreamentoRepository
from src.services.email_filter_service import DetrafEmailFilterService
from src.services.outlook_service import OutlookError, OutlookService

_INVALID_DIR_CHARS = re.compile(r'[\\/:*?"<>|]')


def _safe_dir_name(entry_id: str) -> str:
    """Converte entry_id em nome de diretório seguro (últimos 80 chars)."""
    safe = _INVALID_DIR_CHARS.sub("_", entry_id)
    return safe[-80:] if len(safe) > 80 else safe


class OutlookController:
    """
    Lê a pasta 'Detraf Despesas' (alimentada por fora do robô), filtra os
    e-mails relevantes, baixa os anexos e move cada e-mail capturado para a
    subpasta 'PROCESSADOS' — garantindo que não seja capturado de novo.
    """

    def __init__(self) -> None:
        self._config = OutlookConfig.from_configuration()
        self._rastreamento = RastreamentoRepository()

    def deve_processar_hoje(self) -> bool:
        """Só processa a partir do dia configurado (DETRAF_DIA_LIBERACAO)."""
        return datetime.now().day >= self._config.dia_liberacao

    def capturar_arquivos(self) -> list[ArquivoParaProcessar]:
        """
        Executa o fluxo de captura: lê 'Detraf Despesas', filtra, baixa
        anexos, registra rastreamento e move e-mails capturados para
        'PROCESSADOS'.

        Returns:
            Lista de arquivos baixados, prontos para o pipeline de
            processamento/salvamento (HU-02/HU-03).
        """
        if not self.deve_processar_hoje():
            logger.info(
                f"Dia atual anterior ao dia de liberação ({self._config.dia_liberacao}) — "
                f"captura de e-mails não executada."
            )
            return []

        outlook = OutlookService(self._config.account)
        emails = outlook.fetch_emails_from_folder(self._config.detraf_despesas_folder)
        logger.info(f"{len(emails)} e-mail(s) em '{self._config.detraf_despesas_folder}'")

        arquivos: list[ArquivoParaProcessar] = []
        total_filtrados = 0
        total_ja_rastreados = 0
        total_falha_download = 0
        total_falha_mover = 0

        for email in emails:
            if not DetrafEmailFilterService.deve_processar(email):
                total_filtrados += 1
                logger.debug(
                    f"E-mail '{email.entry_id}' (assunto: '{email.subject}', "
                    f"remetente: '{email.sender_email}') não passou no filtro de negócio "
                    "(contém 'CONTESTAÇÃO' e/ou não tem anexo excel/csv) — ignorado."
                )
                continue

            if self._rastreamento.existe_entry_id(email.entry_id):
                total_ja_rastreados += 1
                logger.debug(
                    f"E-mail '{email.entry_id}' (assunto: '{email.subject}') já rastreado — pulando."
                )
                continue

            dest_folder = self._config.dest_root / _safe_dir_name(email.entry_id)
            try:
                caminhos = outlook.download_attachments(email.entry_id, dest_folder)
            except OutlookError as exc:
                total_falha_download += 1
                logger.error(f"Falha ao baixar anexos de '{email.entry_id}': {exc}")
                continue

            for caminho in caminhos:
                self._rastreamento.registrar(RegistroRastreamento(
                    caminho_arquivo=str(caminho),
                    entry_id=email.entry_id,
                    subject=email.subject,
                    sender_email=email.sender_email,
                    received_at=email.received_at.isoformat() if email.received_at else None,
                ))
                arquivos.append(ArquivoParaProcessar(
                    caminho=caminho,
                    sender_email=email.sender_email,
                    entry_id=email.entry_id,
                ))

            try:
                outlook.move_to_subfolder(
                    email.entry_id,
                    self._config.detraf_despesas_folder,
                    self._config.processados_folder,
                )
                logger.info(
                    f"E-mail '{email.entry_id}' capturado e movido para "
                    f"'{self._config.processados_folder}'."
                )
            except OutlookError as exc:
                total_falha_mover += 1
                logger.error(
                    f"E-mail '{email.entry_id}' capturado mas não movido para "
                    f"'{self._config.processados_folder}': {exc}"
                )

        logger.info(
            "Resumo da captura — "
            f"lidos: {len(emails)} | "
            f"filtrados (ignorados): {total_filtrados} | "
            f"já rastreados (ignorados): {total_ja_rastreados} | "
            f"falha no download: {total_falha_download} | "
            f"falha ao mover p/ PROCESSADOS: {total_falha_mover} | "
            f"arquivos capturados: {len(arquivos)}"
        )
        return arquivos

    def responder_por_arquivo(self, caminho_arquivo: Path, corpo: str) -> None:
        """
        Cria um rascunho de resposta ao e-mail que originou `caminho_arquivo`.

        Args:
            caminho_arquivo: Caminho do arquivo baixado (usado para localizar
                o e-mail de origem via rastreamento).
            corpo: Corpo do rascunho de resposta.
        """
        registro = self._rastreamento.buscar_por_arquivo(caminho_arquivo)
        if registro is None:
            logger.warning(
                f"Não foi possível localizar o e-mail de origem para '{caminho_arquivo}'."
            )
            return

        outlook = OutlookService(self._config.account)
        outlook.create_reply_draft(registro.entry_id, corpo)
