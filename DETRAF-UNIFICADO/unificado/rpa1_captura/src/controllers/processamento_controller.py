from comum.config import configuration
from comum.config.diagnostico_execucao import DiagnosticoInativo
from comum.config.logger_config import logger
from comum.utils import pausa
from src.controllers.outlook_controller import OutlookController
from src.services.notificacao_operadora import notificar_arquivos_recusados
from src.services.processamento_service import ProcessamentoService


class ProcessamentoController:
    """
    Controller do fluxo de processamento de arquivos.

    Atua como camada de coordenação entre o ponto de entrada da aplicação
    e a camada de serviços, sem conter qualquer lógica de negócio.
    """

    def __init__(self) -> None:
        self._outlook_instancia: OutlookController | None = None
        self._servico = ProcessamentoService(notificar=self._notificar_operadora)

    def _notificar_operadora(self, pacote, recusas) -> bool:
        """
        Responde à operadora sobre os arquivos reprovados de **um** e-mail.

        Passado ao serviço como **callable**, e não como objeto: assim a property
        `_outlook` só é tocada quando existe de fato um arquivo reprovado. Um
        `OutlookController` construído no `__init__` do serviço abriria a conexão
        COM em toda execução e desfaria a preguiça abaixo.
        """
        return notificar_arquivos_recusados(self._outlook.responder, pacote, recusas)

    @property
    def _outlook(self) -> OutlookController:
        """
        Construído **preguiçosamente** (2026-08-06).

        `OutlookController.__init__` abre a conexão COM com o Outlook. Enquanto
        ele era construído aqui, uma máquina sem perfil de e-mail configurado
        não conseguia rodar **nem as partes do RPA 1 que não dependem de
        e-mail** — a identificação da operadora (HU-02) e o salvamento na árvore
        de pastas (HU-03) morriam antes de começar.

        Com isto e o `--pasta-entrada`, dois terços do robô podem ser
        homologados sem Outlook nenhum.
        """
        if self._outlook_instancia is None:
            self._outlook_instancia = OutlookController()
        return self._outlook_instancia

    def processar(
        self,
        pasta_entrada: str | None = None,
        etapa: str | None = None,
        diagnostico=None,
    ) -> None:
        """
        Executa as duas etapas do RPA 1, na ordem.

        ==================  ====  ==========================================
        Etapa               HU    O que faz
        ==================  ====  ==========================================
        ``captura``         01    lê a caixa, filtra, baixa os anexos e move
                                  o e-mail para PROCESSADOS
        ``processamento``   02/03 identifica a operadora e salva na árvore
        ==================  ====  ==========================================

        ## Por que as duas são separáveis

        Porque a captura **deixa um rastro em disco**: os anexos em
        `DIRETORIO_ENTRADA` e o vínculo arquivo→remetente no
        `RastreamentoRepository`. A etapa `processamento` reconstrói dali tudo
        de que precisa — inclusive o remetente —, então rodar as duas em
        execuções separadas dá **o mesmo resultado** de rodar junto.

        Isso é o que faz a divisão valer a pena: na homologação, dá para
        capturar uma vez e reprocessar quantas vezes for preciso, sem voltar ao
        Outlook e sem consumir e-mail novo.

        Args:
            pasta_entrada: Pasta a processar em vez da configurada. **Implica
                `etapa="processamento"`** — apontar uma pasta e ainda assim ir
                ao Outlook não faria sentido.
            etapa: `"captura"`, `"processamento"` ou `None` para as duas.

        Returns:
            None.
        """
        registro = diagnostico or DiagnosticoInativo()

        if pasta_entrada:
            etapa = "processamento"

        if etapa in (None, "captura"):
            logger.info("[RPA 1] Etapa 1/2 — captura dos anexos no Outlook (HU-01)")
            with registro.etapa(
                "captura",
                {
                    "OUTLOOK_ACCOUNT": configuration.OUTLOOK_ACCOUNT,
                    "pasta de origem": configuration.OUTLOOK_DETRAF_DESPESAS_FOLDER,
                    "DIRETORIO_ENTRADA": str(configuration.DIRETORIO_ENTRADA),
                },
            ) as atual:
                arquivos = self._outlook.capturar_arquivos()
                atual.produzido = self._outlook.resumo
            pausa.pausar(
                titulo="RPA 1 — etapa 1/2: captura",
                linhas=self._outlook.resumo
                or ["Nada capturado (antes da data de corte, ou caixa vazia)."],
                proxima_etapa=(
                    "nenhuma — a execução termina aqui (--etapa=captura)"
                    if etapa == "captura"
                    else "identificação da operadora e salvamento na árvore"
                ),
                caminho=configuration.DIRETORIO_ENTRADA,
            )
        else:
            logger.info(
                "[RPA 1] Captura PULADA. Os arquivos serão lidos de "
                "DIRETORIO_ENTRADA, e o remetente de cada um vem do "
                "rastreamento gravado pela captura anterior."
            )
            registro.pular(
                "captura",
                "pulada — os arquivos vêm de DIRETORIO_ENTRADA, e o remetente "
                "de cada um, do rastreamento da captura anterior.",
            )
            # `None` faz o serviço varrer a pasta e recuperar o rastreamento —
            # ver `ProcessamentoService._varrer_pasta_de_entrada`.
            arquivos = None

        if etapa == "captura":
            logger.info(
                "[RPA 1] Concluído por --etapa=captura: os anexos estão em "
                "DIRETORIO_ENTRADA e ainda NÃO foram identificados nem salvos "
                "na árvore das operadoras. Rode --etapa=processamento para isso."
            )
            registro.pular("processamento", "pulada por --etapa=captura")
            return

        logger.info(
            "[RPA 1] Etapa 2/2 — identificação da operadora e salvamento "
            "(HU-02/HU-03)"
        )
        with registro.etapa(
            "processamento",
            {
                "CAMINHO_OPERADORAS": str(configuration.CAMINHO_OPERADORAS),
                "DIRETORIO_QUARENTENA": str(configuration.DIRETORIO_QUARENTENA),
                "arquivos recebidos": (
                    "da captura" if arquivos is not None else "varredura da entrada"
                ),
            },
        ) as atual:
            self._servico.executar(arquivos)
            atual.produzido = self._servico.resumo

        pausa.pausar(
            titulo="RPA 1 — etapa 2/2: identificação e salvamento",
            linhas=self._servico.resumo,
            caminho=configuration.CAMINHO_OPERADORAS,
        )
