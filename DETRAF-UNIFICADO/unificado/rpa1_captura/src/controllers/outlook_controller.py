"""Orquestra a captura de e-mails da pasta 'Detraf Despesas' (HU-01)."""

import re
from datetime import datetime
from pathlib import Path

from comum.config.logger_config import logger
from comum.integracoes.outlook_config import OutlookConfig
from src.models.dto.arquivo_para_processar import ArquivoParaProcessar
from src.models.dto.registro_rastreamento import RegistroRastreamento
from src.models.repository.rastreamento_repository import RastreamentoRepository
from src.services.email_filter_service import DetrafEmailFilterService
from comum.integracoes.outlook import OutlookError, OutlookService

_INVALID_DIR_CHARS = re.compile(r'[\\/:*?"<>|]')


def _safe_dir_name(entry_id: str) -> str:
    """Converte entry_id em nome de diretório seguro (últimos 80 chars)."""
    safe = _INVALID_DIR_CHARS.sub("_", entry_id)
    return safe[-80:] if len(safe) > 80 else safe


class OutlookController:
    """
    Organiza a Caixa de Entrada, lê a pasta 'Detraf Despesas' resultante,
    filtra os e-mails relevantes, baixa os anexos e move cada e-mail
    capturado para a subpasta 'PROCESSADOS' — garantindo que não seja
    capturado de novo.

    🔴 Até 2026-08-13 a organização não existia: a classe só lia 'Detraf
    Despesas', como se algo de fora a alimentasse. A V2 diz o contrário —
    quem filtra a Caixa de Entrada e organiza os e-mails ali é o próprio
    robô. Não existe (e não deveria existir) regra de Outlook fazendo isso;
    a Vivo confirmou que só criou a caixa, nada além. Ver
    `organizar_caixa_de_entrada`.
    """

    def __init__(self) -> None:
        self._config = OutlookConfig.from_configuration()
        self._rastreamento = RastreamentoRepository()
        #: Contadores da última captura, para a parada entre etapas mostrar.
        self.resumo: list[str] = []

    def deve_processar_hoje(self) -> bool:
        """Só processa a partir do dia configurado (DETRAF_DIA_LIBERACAO)."""
        return datetime.now().day >= self._config.dia_liberacao

    def organizar_caixa_de_entrada(self, outlook: OutlookService) -> None:
        """
        Move da Caixa de Entrada para 'Detraf Despesas' os e-mails que atendem
        ao filtro de negócio (HU-01) — a metade da história que faltava.

        Até 2026-08-13 o robô só lia 'Detraf Despesas', assumindo que algo de
        fora a alimentava. A V2 diz o contrário: **é o robô** quem filtra a
        Caixa de Entrada e organiza os e-mails nessa pasta — não existe (e,
        pelo espec, nunca deveria existir) regra de Outlook ou processo
        externo fazendo isso. Sem este passo, 'Detraf Despesas' fica vazia
        para sempre, mesmo com e-mails de despesa chegando na caixa.

        Usa o **mesmo** `DetrafEmailFilterService` que decide, mais adiante, o
        que é capturado — um e-mail que passaria no filtro de captura mas
        nunca chega a ser filtrado da Caixa de Entrada é o defeito que isto
        fecha.
        """
        emails = outlook.fetch_emails_from_inbox()
        movidos = 0
        for email in emails:
            if not DetrafEmailFilterService.deve_processar(email):
                continue
            try:
                outlook.move_to_top_level_folder(
                    email.entry_id, self._config.detraf_despesas_folder
                )
                movidos += 1
            except OutlookError as exc:
                logger.error(
                    f"Falha ao mover e-mail '{email.entry_id}' (assunto: "
                    f"'{email.subject}') da Caixa de Entrada para "
                    f"'{self._config.detraf_despesas_folder}': {exc}"
                )
        logger.info(
            f"Organização da Caixa de Entrada: {len(emails)} e-mail(s) lido(s), "
            f"{movidos} movido(s) para '{self._config.detraf_despesas_folder}'."
        )

    def capturar_arquivos(self) -> list[ArquivoParaProcessar]:
        """
        Executa o fluxo de captura: organiza a Caixa de Entrada, lê 'Detraf
        Despesas', filtra, baixa anexos, registra rastreamento e move e-mails
        capturados para 'PROCESSADOS'.

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
        self.organizar_caixa_de_entrada(outlook)
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
                    subject=email.subject or "",
                    received_at=(
                        email.received_at.isoformat() if email.received_at else ""
                    ),
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

        # Os mesmos números do log, agora também estruturados. A parada entre
        # etapas os mostra na caixa, e reformatá-los lá a partir do texto seria
        # duplicar a contagem em dois lugares que podem divergir.
        self.resumo = [
            f"E-mails lidos:            {len(emails)}",
            f"Ignorados pelo filtro:    {total_filtrados}",
            f"Ignorados (já capturados):{total_ja_rastreados}",
            f"Falha no download:        {total_falha_download}",
            f"Falha ao mover:           {total_falha_mover}",
            "",
            f"Arquivos baixados:        {len(arquivos)}",
        ]
        return arquivos

    def responder(
        self, pacote: ArquivoParaProcessar, corpo: str, enviar: bool = False
    ) -> bool:
        """
        Responde ao e-mail de origem de um arquivo reprovado na validação.

        Usa o `entry_id` que veio da captura — resolução exata. Quando ele está
        vazio (pasta preparada à mão, `--pasta-entrada`), cai no rastreamento
        **por caminho**, que também é exato aqui: o arquivo ainda está onde foi
        baixado. Sem nenhum dos dois, não há e-mail para responder.

        Args:
            pacote: O arquivo e os metadados do e-mail de origem.
            corpo: Corpo já renderizado.
            enviar: `True` envia; `False` (default) só cria o rascunho.

        Returns:
            Se a resposta foi criada. **Nunca levanta** — a recusa do arquivo já
            está consumada, e uma falha do Outlook não pode desfazê-la nem
            impedir a notificação do próximo arquivo.
        """
        entry_id = pacote.entry_id
        if not entry_id:
            registro = self._rastreamento.buscar_por_arquivo(pacote.caminho)
            entry_id = registro.entry_id if registro else ""

        if not entry_id:
            logger.warning(
                f"[RPA 1] '{pacote.caminho.name}' foi reprovado, mas não há "
                "e-mail de origem para responder (sem entry_id e sem "
                "rastreamento). É o esperado numa pasta preparada à mão."
            )
            return False

        try:
            OutlookService(self._config.account).responder_email(
                entry_id, corpo, enviar=enviar
            )
        except Exception as erro:
            logger.excecao(
                f"[RPA 1] Falha ao {'enviar' if enviar else 'criar rascunho de'} "
                f"resposta para '{pacote.caminho.name}': {erro}"
            )
            return False

        logger.info(
            f"[RPA 1] Resposta {'enviada' if enviar else 'criada como rascunho'} "
            f"para o e-mail de origem de '{pacote.caminho.name}'."
        )
        return True

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
