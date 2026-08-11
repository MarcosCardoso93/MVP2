"""Orquestração do RPA 3 — do Detraf recebido à carga no AGI.

Segue o padrão de "orquestração fina" (AI/01 §1): o controller **instancia e
dispara** os services, sem regra de negócio nem manipulação de DataFrame. Quem
sabe comparar minutagem é o service; aqui só se decide a ordem, o que fazer com
falha e o que fica de fora.

## A ordem vem da V2

Seção *Contestação e criação dos arquivos para o AGI*:

    "1) geração do arquivo com o tráfego da operadora para carga no AGI - todos
    os cenários; 2) geração do arquivo interno com a expectativa da Vivo, apenas
    para o tráfego contestado com retenção; 3) geração do arquivo de contestação
    e carta para envio à operadora [...]; 4) geração do arquivo com o consolidado
    da contestação para carga no AGI"

Seção *Carga no AGI*: primeiro ``Detraf > Importar Dados`` (EXT e INT, um de cada
vez), depois ``Contestação > Gerenciar`` (CONT_PROC) → Salvar → gravar
``carga_agi``.

E, depois da carga, a V2 (¶690) pede a conferência: *"Este relatório é gerado
para conferir os valores carregados no AGI e no EC"* — a HU-20.

Daí as cinco fases: **A** gera os artefatos por operadora, **B** carrega no AGI
(fora do laço — os uploaders abrem o AGI uma vez só, para o lote inteiro), **C**
envia o e-mail da HU-15, **D** confere o relatório (HU-20) e **E** consolida o
resumo.

## Diante de etapa bloqueada: pular com aviso

O mês tem dezenas de operadoras. Abortar tudo faz uma pasta ausente bloquear o
mês inteiro; seguir cego produz artefato errado. Então: falta de insumo e
pendência conhecida viram aviso nomeado e seguem; erro inesperado numa operadora
não impede a seguinte.

**Duas exceções, que abortam a etapa para a execução inteira:**

- ``NumeracaoCartaIndeterminada`` — a numeração CT é global e serial. Se falha
  para a primeira operadora, falha para todas, e insistir arrisca **duplicar
  número**, o que a decisão do cliente de 2026-07-31 proíbe. A etapa "carta" é
  desabilitada e o resto continua saindo.
- Falha ao montar o índice de remuneração — é pré-condição de tudo; aborta antes
  do laço começar.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from comum.arquivos import estrutura_pastas as ep
from comum.config import configuration
from comum.config import constantes as const
from comum.config import relatorio_execucao as rel
from comum.config.diagnostico_execucao import DiagnosticoInativo
from comum.config.logger_config import logger
from comum.dados.repositorio_tabelas import RepositorioTabelas
from comum.dominio.competencia import obter_competencia
from comum.utils import pausa
from comum.utils.decoradores import log_execucao
from src.services import consolidacao_contestacao as cc
from src.services import encontro_contas as ec
from src.services import envio_email_contestacao as email
from src.services import geracao_cont_proc as gcp
from src.services import geracao_env_carta as gec
from src.services import geracao_ext as gext
from src.services import geracao_int as gint
from src.services import mapa_remuneracao as mr


@dataclass
class ResultadoOperadora:
    """O que saiu (ou não) para uma operadora no mês."""

    operadora: str
    ext: Optional[Path] = None
    int_: Optional[Path] = None
    env: Optional[Path] = None
    #: **Lista** desde a Q25 (2026-08-05): uma carta por cenário de contestação.
    #: A mesma operadora pode ter linhas COM e SEM retenção no mesmo mês, e cada
    #: uma vira um documento com o seu próprio número CT.
    cartas: list[Path] = field(default_factory=list)
    cont_proc: Optional[Path] = None
    despesa: dict = field(default_factory=dict)
    pulos: list[str] = field(default_factory=list)
    erro: Optional[str] = None

    @property
    def gerou_algo(self) -> bool:
        return any((self.ext, self.int_, self.env, self.cont_proc)) or bool(self.cartas)


class GeracaoAgiController:
    """Orquestra a geração dos artefatos e a carga no AGI."""

    def __init__(
        self,
        repositorio: RepositorioTabelas | None = None,
        uploader_detraf=None,
        uploader_contestacao=None,
        servico_outlook=None,
        hoje: date | None = None,
        provedor_assinatura=None,
    ) -> None:
        """
        Args:
            repositorio: Acesso às tabelas do WebFat.
            uploader_detraf: `UploadDetrafAGI`. **Injetado**, não construído aqui:
                o construtor dele resolve o executável do AGI, o que tornaria a
                orquestração intestável sem a VM.
            uploader_contestacao: `UploadContestacaoAGI`, pelo mesmo motivo.
            servico_outlook: `OutlookService`. Construído **preguiçosamente** — a
                conexão COM custa e falha em máquina sem perfil, e não faz sentido
                pagar por ela quando não há e-mail a enviar.
            hoje: Data da carta. Injetada para a renderização ser determinística.
            provedor_assinatura: Assinatura da carta (default: a padrão da HU-14).
        """
        self.repositorio = repositorio or RepositorioTabelas()
        self._uploader_detraf = uploader_detraf
        self._uploader_contestacao = uploader_contestacao
        self._servico_outlook = servico_outlook
        self.hoje = hoje or date.today()
        self.provedor_assinatura = provedor_assinatura

        self._indice_remuneracao: dict[str, list[str]] | None = None
        #: Desabilitada para a execução inteira quando a numeração CT falha.
        self._carta_habilitada = True

    # ------------------------------------------------------------------
    # Recursos resolvidos uma vez por execução
    # ------------------------------------------------------------------

    @property
    def indice_remuneracao(self) -> dict[str, list[str]]:
        """
        Índice ``remuneração -> descritores`` (D-5), do banco.

        Preguiçoso e memorizado: é uma leitura de tabela inteira, e as três HUs
        que o consomem rodam por operadora — montá-lo a cada uma multiplicaria o
        custo pelo número de operadoras sem mudar o resultado.
        """
        if self._indice_remuneracao is None:
            mapa = mr.carregar_mapa_descritores(self.repositorio.obter_mapa_descritores())
            self._indice_remuneracao = mr.construir_indice_remuneracao(mapa)
        return self._indice_remuneracao

    @property
    def uploader_detraf(self):
        if self._uploader_detraf is None:
            # Import tardio: `upload_detraf_agi` traz `pyautogui` junto, que só
            # faz sentido na máquina que opera o AGI.
            from src.services.upload_detraf_agi import UploadDetrafAGI

            self._uploader_detraf = UploadDetrafAGI()
        return self._uploader_detraf

    @property
    def uploader_contestacao(self):
        if self._uploader_contestacao is None:
            from src.services.upload_contestacao_agi import UploadContestacaoAGI

            self._uploader_contestacao = UploadContestacaoAGI(
                repositorio=self.repositorio
            )
        return self._uploader_contestacao

    @property
    def servico_outlook(self):
        if self._servico_outlook is None:
            from comum.integracoes.outlook import OutlookService

            self._servico_outlook = OutlookService(configuration.OUTLOOK_ACCOUNT)
        return self._servico_outlook

    # ------------------------------------------------------------------
    # Ponto de entrada
    # ------------------------------------------------------------------

    @log_execucao
    def gerar_artefatos(
        self,
        operadoras: list[str] | None = None,
        referencia: str | None = None,
        raiz_operadoras: Path | None = None,
        raiz_controle_ct: Path | None = None,
        indice_descritor: int = const.COL_DESCRITOR,
        etapa: str | None = None,
        diagnostico=None,
    ) -> list[ResultadoOperadora]:
        """
        Executa o fluxo do RPA 3 para o mês.

        Args:
            operadoras: Quais processar. `None` varre a raiz — é o comportamento
                normal; a lista existe para reprocessar uma operadora só.
            referencia: Mês ``AAAAMM``. `None` usa a competência corrente.
            raiz_operadoras: Raiz alternativa, para teste.
            raiz_controle_ct: Pasta de numeração CT, para teste.
            indice_descritor: Índice 0-based da coluna DESC.
            etapa: Uma de ``artefatos``, ``carga``, ``email`` ou ``verificacao``.
                `None` (o normal) executa as quatro na ordem. Existe para a
                homologação repetir a etapa que falhou sem refazer as anteriores
                — as três últimas leem o disco e o banco, não o resultado da
                primeira, então repetir a carga sem regerar os artefatos é
                legítimo.

        Returns:
            Um `ResultadoOperadora` por operadora processada.
        """

        registro = diagnostico or DiagnosticoInativo()
        inicio = time.time()
        referencia = referencia or obter_competencia().competencia

        if operadoras is None:
            operadoras = ep.listar_operadoras_do_mes(
                referencia,
                raiz_operadoras,
                subpasta=configuration.SUBPASTA_DETRAFS_RECEBIDOS,
            )

        if not operadoras:
            logger.warning(
                f"[RPA 3] Nenhuma operadora com Detraf recebido em {referencia}. "
                f"Nada a fazer."
            )
            return []

        logger.info(
            f"[RPA 3] {len(operadoras)} operadora(s) em {referencia}: "
            f"{', '.join(operadoras)}."
        )

        # Pré-condição de tudo: sem o índice de remuneração nenhuma HU classifica
        # linha nenhuma. Falhar aqui é melhor do que falhar N vezes no laço.
        try:
            self.indice_remuneracao
        except Exception as erro:
            logger.excecao(
                f"[RPA 3] Não foi possível montar o índice de remuneração: {erro}. "
                f"É pré-condição de todas as HUs — execução abortada."
            )
            raise

        def roda(nome_etapa: str) -> bool:
            """Sem `--etapa`, roda tudo; com, só a pedida (homologação)."""
            if etapa is None or etapa == nome_etapa:
                return True
            logger.info(f"[RPA 3] Etapa '{nome_etapa}' pulada por --etapa={etapa}.")
            registro.pular(nome_etapa, f"pulada por --etapa={etapa}")
            return False

        # --- Fase A: artefatos, por operadora ---------------------------
        def _gerar_todos() -> list[ResultadoOperadora]:
            with registro.etapa(
                "artefatos",
                {
                    "operadoras": ", ".join(operadoras),
                    "referencia": referencia,
                },
            ) as atual:
                gerados = [
                    self._gerar_para_operadora(
                        operadora=operadora,
                        referencia=referencia,
                        raiz_operadoras=raiz_operadoras,
                        raiz_controle_ct=raiz_controle_ct,
                        indice_descritor=indice_descritor,
                    )
                    for operadora in operadoras
                ]
                atual.produzido = [
                    f"{r.operadora}: "
                    + (f"ERRO {r.erro}" if r.erro
                       else "gerou artefato" if r.gerou_algo
                       else "nada gerado")
                    + (f" | pulos: {'; '.join(r.pulos)}" if r.pulos else "")
                    for r in gerados
                ]
                return gerados

        resultados = (
            _gerar_todos()
            if roda("artefatos")
            # As etapas seguintes leem o disco, não este resultado — dá para
            # repetir a carga sem refazer os artefatos, que é o caso de uso.
            else [ResultadoOperadora(operadora=operadora) for operadora in operadoras]
        )

        com_artefato = (
            [r.operadora for r in resultados if r.gerou_algo]
            if etapa is None
            else self._operadoras_com_artefato_em_disco(
                operadoras, referencia, raiz_operadoras
            )
        )

        if roda("artefatos"):
            # ⚠️ A parada mais valiosa das quatro: é a **última antes de o AGI
            # ser tocado**. O que vier depois escreve para fora.
            self._pausar_apos_artefatos(resultados, referencia, raiz_operadoras, etapa)

        # --- Fase B: carga no AGI ---------------------------------------
        # Fora do laço: os uploaders recebem a lista e abrem o AGI **uma vez**
        # para o lote todo. Abrir e logar no AGI custa minutos.
        if roda("carga"):
            with registro.etapa(
                "carga",
                {
                    "operadoras com artefato": ", ".join(com_artefato) or "(nenhuma)",
                    "PERMITIR_UPLOAD_AGI": str(configuration.PERMITIR_UPLOAD_AGI),
                    "DIRETORIO_AGI": str(configuration.DIRETORIO_AGI),
                },
            ) as atual:
                self._carregar_no_agi(
                    com_artefato, referencia, raiz_operadoras, inicio
                )
                atual.produzido = [
                    f"{len(com_artefato)} operadora(s) na lista de carga",
                    "upload " + (
                        "LIGADO — enviado ao AGI"
                        if configuration.PERMITIR_UPLOAD_AGI
                        else "desligado — nada enviado"
                    ),
                ]
            pausa.pausar(
                titulo="RPA 3 — etapa 2/4: carga no AGI",
                linhas=[
                    f"{len(com_artefato)} operadora(s) na lista de carga.",
                    "",
                    "Upload no AGI: "
                    + ("LIGADO — os arquivos FORAM enviados."
                       if configuration.PERMITIR_UPLOAD_AGI
                       else "desligado — nada foi enviado, só registrado no log."),
                    "",
                    "Confira no AGI se a carga entrou, e o campo `carga_agi` na "
                    "tabela de contestação.",
                ],
                proxima_etapa=self._descrever_proxima("email", etapa),
                caminho=configuration.DIRETORIO_EVIDENCIAS,
            )

        # --- Fase C: e-mail de contestação (HU-15) ----------------------
        if roda("email"):
            with registro.etapa(
                "email",
                {
                    "PERMITIR_ENVIO_EMAIL": str(configuration.PERMITIR_ENVIO_EMAIL),
                    "CAMINHO_CONTATOS_OPERADORAS": str(
                        configuration.CAMINHO_CONTATOS_OPERADORAS
                    ),
                },
            ) as atual:
                self._enviar_emails(resultados, referencia, raiz_operadoras)
                atual.produzido = [
                    "envio " + (
                        "LIGADO — e-mails enviados"
                        if configuration.PERMITIR_ENVIO_EMAIL
                        else "desligado — montado e não enviado"
                    ),
                ]
            pausa.pausar(
                titulo="RPA 3 — etapa 3/4: e-mail de contestação",
                linhas=[
                    "Envio de e-mail: "
                    + ("LIGADO — os e-mails FORAM enviados às operadoras."
                       if configuration.PERMITIR_ENVIO_EMAIL
                       else "desligado — o e-mail foi montado e registrado, "
                            "não enviado."),
                    "",
                    "Contatos: "
                    + (
                        str(configuration.CAMINHO_CONTATOS_OPERADORAS)
                        if configuration.CAMINHO_CONTATOS_OPERADORAS
                        else "não configurados (pendência Q16) — nada é enviado"
                    ),
                ],
                proxima_etapa=self._descrever_proxima("verificacao", etapa),
            )

        # --- Fase D: verificação do relatório (HU-20) -------------------
        if roda("verificacao"):
            with registro.etapa(
                "verificacao",
                {
                    "PERMITIR_ACESSO_AGI": str(configuration.PERMITIR_ACESSO_AGI),
                    "DIRETORIO_INCONSISTENCIAS": str(
                        configuration.DIRETORIO_INCONSISTENCIAS
                    ),
                },
            ) as atual:
                self._verificar_relatorio(referencia)
                atual.produzido = [
                    "a planilha de inconsistências só sai quando há divergência",
                ]
            pausa.pausar(
                titulo="RPA 3 — etapa 4/4: conferência do relatório",
                linhas=[
                    "A conferência compara o relatório do AGI com o Encontro de "
                    "Contas do banco.",
                    "",
                    "A planilha de inconsistências só é gravada quando há "
                    "divergência — nenhum arquivo significa nenhuma divergência.",
                ],
                caminho=configuration.DIRETORIO_INCONSISTENCIAS,
            )

        # --- Fase E: resumo ---------------------------------------------
        self._registrar_resumo(resultados, referencia)
        self._gravar_relatorio(resultados, referencia, etapa)
        return resultados

    # ------------------------------------------------------------------
    # Paradas entre etapas (só em dev, e só com PAUSA_ENTRE_ETAPAS)
    # ------------------------------------------------------------------

    #: O que cada etapa faz, para a caixa dizer o que vem a seguir. As duas
    #: primeiras trazem o aviso em caixa alta de propósito: são as que agem
    #: para fora, e é essa a informação que decide o clique.
    _DESCRICAO_DAS_ETAPAS = {
        "carga": "carga no AGI (HU-17/HU-18) — ESCREVE NO AGI",
        "email": "e-mail de contestação à operadora (HU-15) — SAI DA EMPRESA",
        "verificacao": "conferência do relatório contra o EC (HU-20)",
    }

    @classmethod
    def _descrever_proxima(cls, etapa_seguinte: str, etapa: str | None) -> str | None:
        """
        Descreve a próxima etapa — ou avisa que ela não vai rodar.

        Com `--etapa` a execução para depois da etapa pedida, e a caixa precisa
        dizer isso. Senão quem clica "Continuar" espera a carga acontecer, e ela
        não acontece — e a pausa passa a enganar em vez de informar.
        """
        if etapa is not None:
            return f"nenhuma — a execução termina aqui (--etapa={etapa})"
        return cls._DESCRICAO_DAS_ETAPAS.get(etapa_seguinte)

    def _operadoras_com_artefato_em_disco(
        self,
        operadoras: list[str],
        referencia: str,
        raiz_operadoras: Path | None,
    ) -> list[str]:
        """
        Quais operadoras têm de fato artefato na pasta AGI do mês.

        🔴 Corrige um defeito de 2026-08-07. Com `--etapa carga`, a fase de
        artefatos não roda e devolve `ResultadoOperadora` **vazios**; o código
        antigo caía em `list(operadoras)` e mandava para o AGI **todas** as
        operadoras do mês, inclusive as que nunca geraram nada.

        A pergunta certa é a mesma que o `--etapa` quer permitir — *"o que já
        está pronto em disco?"* —, e a resposta está lá: o `_EXT` e o `_INT` da
        HU-12/13 ficam na subpasta AGI da operadora.
        """
        prontas = []
        for operadora in operadoras:
            try:
                pasta = ep.caminho_agi(
                    operadora=operadora,
                    aaaamm=referencia,
                    raiz_operadoras=raiz_operadoras,
                )
            except (OSError, ValueError) as erro:
                logger.warning(
                    f"[RPA 3] Não foi possível olhar a pasta AGI de "
                    f"'{operadora}': {erro}. Ela fica fora da carga."
                )
                continue

            if pasta.is_dir() and any(pasta.iterdir()):
                prontas.append(operadora)
            else:
                logger.info(
                    f"[RPA 3] '{operadora}' não tem artefato em [{pasta}] — "
                    f"fora da carga. Rode --etapa artefatos antes."
                )

        return prontas

    def _pausar_apos_artefatos(
        self,
        resultados: list[ResultadoOperadora],
        referencia: str,
        raiz_operadoras: Path | None,
        etapa: str | None,
    ) -> None:
        """
        Mostra o que saiu por operadora, **antes de o AGI ser tocado**.

        É a parada que mais importa das quatro: tudo o que vem depois escreve
        para fora — o AGI e a caixa de e-mail da operadora. Aqui ainda dá para
        parar sem consequência externa nenhuma.

        A tabela por operadora usa o mesmo recorte do relatório de execução
        (`comum/config/relatorio_execucao.py`), para quem homologa comparar as
        duas coisas sem precisar traduzir de uma para a outra.
        """
        linhas = [f"{len(resultados)} operadora(s) em {referencia}:", ""]

        for resultado in resultados:
            produzidos = [
                nome
                for nome, saiu in (
                    ("EXT", resultado.ext),
                    ("INT", resultado.int_),
                    ("_EXP", resultado.env),
                    (f"{len(resultado.cartas)} carta(s)", resultado.cartas),
                    ("CONT_PROC", resultado.cont_proc),
                )
                if saiu
            ]
            linhas.append(
                f"  {resultado.operadora:20s} "
                f"{' · '.join(produzidos) if produzidos else 'nada gerado'}"
            )

            if resultado.erro:
                linhas.append(f"  {'':20s} ERRO: {resultado.erro}")
            for pulo in resultado.pulos:
                linhas.append(f"  {'':20s} pulado: {pulo}")

        pausa.pausar(
            titulo="RPA 3 — etapa 1/4: artefatos",
            linhas=linhas,
            proxima_etapa=self._descrever_proxima("carga", etapa),
            caminho=(
                Path(raiz_operadoras)
                if raiz_operadoras
                else configuration.CAMINHO_OPERADORAS
            ),
        )

    # ------------------------------------------------------------------
    # Fase A — uma operadora
    # ------------------------------------------------------------------

    def _gerar_para_operadora(
        self,
        operadora: str,
        referencia: str,
        raiz_operadoras: Path | None,
        raiz_controle_ct: Path | None,
        indice_descritor: int,
    ) -> ResultadoOperadora:
        """Gera os artefatos de uma operadora, na ordem da V2."""

        resultado = ResultadoOperadora(operadora=operadora)

        try:
            df_operadora = cc.consolidar_detrafs_operadora(
                ep.caminho_detrafs_recebidos(operadora, referencia, raiz_operadoras)
            )

            if df_operadora.empty:
                # Sem Detraf não há o que gerar. E o short-circuit importa:
                # `gerar_arquivo_ext` não tem guarda de vazio (ao contrário do
                # INT/_EXP/CONT_PROC), então gravaria um .xlsx vazio que a HU-17
                # tentaria subir no AGI.
                logger.warning(
                    f"[RPA 3] {operadora}: nenhum Detraf em {referencia} — "
                    f"operadora pulada."
                )
                resultado.pulos.append("sem Detraf recebido")
                return resultado

            df_tbra = cc.consolidar_expectativa_vivo(
                ep.caminho_detrafs_enviados(operadora, referencia, raiz_operadoras)
            )
            if df_tbra.empty:
                # O Contest trata o par ausente como 100% de variação, então o
                # EXT ainda sai — mas INT e _EXP ficarão vazios.
                logger.warning(
                    f"[RPA 3] {operadora}: sem expectativa Vivo em {referencia}; "
                    f"a comparação sairá com o lado da Vivo zerado."
                )
                resultado.pulos.append("sem expectativa Vivo")

            df_contest = cc.montar_contest(
                df_operadora=df_operadora,
                df_tbra=df_tbra,
                indice_descritor=indice_descritor,
                indice_remuneracao=self.indice_remuneracao,
            )

            # HU-19 antes dos artefatos: é UPDATE idempotente, e garante o
            # panorama no WebFat mesmo se a geração falhar adiante.
            resultado.despesa = self.atualizar_despesa_contestacao(
                df_contest, referencia
            )

            resultado.ext = self._gerar_ext(
                df_operadora, operadora, referencia, raiz_operadoras, indice_descritor
            )
            resultado.int_ = self._gerar_int(
                df_tbra, operadora, referencia, raiz_operadoras, indice_descritor
            )

            resultado.env, resultado.cartas = self._gerar_env_e_carta(
                df_contest=df_contest,
                df_tbra=df_tbra,
                operadora=operadora,
                referencia=referencia,
                raiz_operadoras=raiz_operadoras,
                raiz_controle_ct=raiz_controle_ct,
                indice_descritor=indice_descritor,
                pulos=resultado.pulos,
            )

            resultado.cont_proc = self.gerar_cont_proc(
                df_contest, operadora, referencia, raiz_operadoras
            )

        except Exception as erro:
            # Uma operadora com problema não bloqueia as demais — o mês tem
            # dezenas, e o resumo final e o código de saída denunciam a falha.
            logger.excecao(f"[RPA 3] {operadora}: falha ao gerar artefatos: {erro}")
            resultado.erro = str(erro)

        return resultado

    def _gerar_ext(
        self, df_operadora, operadora, referencia, raiz_operadoras, indice_descritor
    ) -> Path:
        """HU-12 — sai em **todos** os cenários (V2)."""
        linhas = gext.montar_linhas_ext(
            df_operadora=df_operadora,
            indice_descritor=indice_descritor,
            indice_remuneracao=self.indice_remuneracao,
            obter_tipo_contestacao=self.repositorio.obter_tipo_contestacao,
        )
        return gext.gerar_arquivo_ext(linhas, operadora, referencia, raiz_operadoras)

    def _gerar_int(
        self, df_tbra, operadora, referencia, raiz_operadoras, indice_descritor
    ) -> Optional[Path]:
        """HU-13 — só existe no cenário COM retenção; `None` nos demais."""
        if df_tbra.empty:
            return None

        linhas = gint.montar_linhas_int(
            df_tbra=df_tbra,
            indice_descritor=indice_descritor,
            indice_remuneracao=self.indice_remuneracao,
            obter_tipo_contestacao=self.repositorio.obter_tipo_contestacao,
        )
        return gint.gerar_arquivo_int(linhas, operadora, referencia, raiz_operadoras)

    def _gerar_env_e_carta(
        self,
        df_contest,
        df_tbra,
        operadora: str,
        referencia: str,
        raiz_operadoras: Path | None,
        raiz_controle_ct: Path | None,
        indice_descritor: int,
        pulos: list[str],
    ) -> tuple[Optional[Path], list[Path]]:
        """HU-14 — o `_EXP` e a carta. Sem linha contestada, nenhum dos dois sai."""

        if df_tbra.empty:
            # `montar_abas_env` monta a aba TBRA a partir da expectativa bruta e
            # indexa por posição — sem ela, estoura em vez de degradar. O EXT já
            # saiu (ele só depende do lado da operadora), e o CONT_PROC ainda sai;
            # o que não dá para montar é a comparação lado a lado que o _EXP é.
            logger.warning(
                f"[RPA 3] {operadora}: sem expectativa Vivo — _EXP e carta não "
                f"serão gerados. Confira a pasta "
                f"'{configuration.SUBPASTA_DETRAFS_ENVIADOS}' da operadora."
            )
            pulos.append("_EXP e carta sem expectativa Vivo")
            return None, []

        abas = gec.montar_abas_env(
            df_contest=df_contest,
            df_tbra_bruta=df_tbra,
            referencia=referencia,
            indice_descritor=indice_descritor,
            indice_remuneracao=self.indice_remuneracao,
            obter_tipo_contestacao=self.repositorio.obter_tipo_contestacao,
        )
        caminho_env = gec.gerar_arquivo_env(abas, operadora, referencia, raiz_operadoras)

        if caminho_env is None:
            # Nada contestado: não há contestação a enviar, então não há carta.
            return None, []

        if not self._carta_habilitada:
            pulos.append("carta desabilitada nesta execução (numeração CT)")
            return caminho_env, []

        por_cenario = gec.separar_por_cenario(
            df_contest, referencia, self.repositorio.obter_tipo_contestacao
        )
        if len(por_cenario) > 1:
            logger.info(
                f"[RPA 3] {operadora}: linhas COM e SEM retenção no mesmo mês — "
                f"sairão {len(por_cenario)} cartas, uma por cenário (decisão Q25)."
            )

        try:
            cartas = self._emitir_cartas(
                por_cenario=por_cenario,
                operadora=operadora,
                referencia=referencia,
                raiz_operadoras=raiz_operadoras,
                raiz_controle_ct=raiz_controle_ct,
            )
        except (gec.NumeracaoCartaIndeterminada, ValueError) as erro:
            # A numeração é global e serial: se falhou aqui, falha para todas.
            # Insistir a cada operadora arriscaria emitir números duplicados.
            self._carta_habilitada = False
            logger.error(
                f"[RPA 3] Numeração CT indisponível: {erro} "
                f"A geração de CARTA fica desabilitada para toda esta execução — "
                f"os demais artefatos continuam sendo gerados."
            )
            pulos.append("carta desabilitada nesta execução (numeração CT)")
            return caminho_env, []

        return caminho_env, cartas

    def _emitir_cartas(
        self,
        por_cenario: dict,
        operadora: str,
        referencia: str,
        raiz_operadoras: Path | None,
        raiz_controle_ct: Path | None,
    ) -> list[Path]:
        """
        Emite **uma carta por cenário**, cada uma com o seu número CT (Q25).

        O sinal do analista é por chave — a mesma operadora pode ter linhas COM e
        SEM retenção no mesmo mês, e a carta é um documento com **um** texto de
        cenário. Decisão do cliente (2026-08-05): duas cartas, dois números.

        Tudo acontece **dentro de uma única trava** (Q18): o número sai do maior
        encontrado na pasta e só passa a existir ali quando a carta é gravada.
        Resolver o segundo número antes de gravar o primeiro daria o mesmo valor
        duas vezes — e agora é a própria execução que consome dois seguidos.
        """
        pasta_controle = ep.caminho_controle_ct(referencia, raiz_controle_ct)
        cartas: list[Path] = []

        with gec.travar_numeracao(pasta_controle):
            for cenario, linhas in por_cenario.items():
                numero_ct = gec.obter_proximo_numero_carta(pasta_controle)

                documento = gec.renderizar_carta(
                    numero_ct=numero_ct,
                    data_carta=self.hoje,
                    aaaamm=referencia,
                    operadora=operadora,
                    tipo_contestacao=cenario,
                    tabelas_por_remuneracao=gec.montar_tabelas_carta(linhas),
                    provedor_assinatura=self.provedor_assinatura,
                )
                cartas.append(
                    gec.gerar_arquivo_carta(
                        documento=documento,
                        operadora=operadora,
                        numero_ct=numero_ct,
                        aaaamm=referencia,
                        raiz_operadoras=raiz_operadoras,
                        raiz_controle_ct=raiz_controle_ct,
                    )
                )
                logger.info(
                    f"[RPA 3] {operadora}: carta CT {numero_ct} — {cenario}."
                )

        return cartas

    # ------------------------------------------------------------------
    # Fase B — carga no AGI
    # ------------------------------------------------------------------

    def _carregar_no_agi(
        self,
        operadoras: list[str],
        referencia: str,
        raiz_operadoras: Path | None,
        inicio_da_execucao: float,
    ) -> None:
        """
        Sobe EXT/INT e depois o CONT_PROC, na ordem da V2.

        O controller **não relê** `PERMITIR_UPLOAD_AGI`: os uploaders já o checam,
        e duplicar a decisão é como ela acaba divergindo. `inicio_da_execucao`
        descarta sobra de rodada anterior na pasta.
        """
        if not operadoras:
            logger.info("[RPA 3] Nenhum artefato gerado — nada a carregar no AGI.")
            return

        self.uploader_detraf.executar(
            operadoras, referencia, raiz_operadoras, desde=inicio_da_execucao
        )
        self.uploader_contestacao.executar(operadoras, referencia, raiz_operadoras)

    # ------------------------------------------------------------------
    # Fase C — HU-15
    # ------------------------------------------------------------------

    def _enviar_emails(
        self,
        resultados: list[ResultadoOperadora],
        referencia: str,
        raiz_operadoras: Path | None,
    ) -> None:
        """
        Envia a contestação de quem tem `_EXP` **e** carta.

        Hoje isto sempre termina em `pulos`: `buscar_destinatarios` devolve lista
        vazia porque a tabela de contatos do WebFat não foi informada (Q16). A
        chamada fica aqui, e não comentada, para que o dia em que a resposta
        chegar seja só preencher a função — e para que o log diga, a cada
        execução, que a contestação ficou sem enviar.
        """
        candidatas = [r for r in resultados if r.env and r.cartas]
        if not candidatas:
            return

        # O Outlook só é construído quando existe pelo menos um destinatário.
        #
        # 🐛 Antes, `self.servico_outlook` era avaliado no argumento da chamada —
        # ou seja, **antes** de `enviar_contestacao` olhar os destinatários. Numa
        # máquina sem perfil Outlook a conexão COM estourava e caía no `except`
        # genérico, e a operadora era reportada como "e-mail falhou" em vez de
        # "não enviado", escondendo que a causa real é a Q16.
        if not any(email.buscar_destinatarios(r.operadora) for r in candidatas):
            logger.warning(
                f"[RPA 3] Nenhum destinatário para as {len(candidatas)} contestação(ões) "
                f"do mês — o Outlook nem chega a ser aberto. Pendência Q16."
            )
            for resultado in candidatas:
                resultado.pulos.append("e-mail de contestação não enviado")
            return

        for resultado in candidatas:
            try:
                email.enviar_contestacao(
                    operadora=resultado.operadora,
                    aaaamm=referencia,
                    servico_outlook=self.servico_outlook,
                    raiz_operadoras=raiz_operadoras,
                )
            except email.EnvioEmailContestacaoIncompleto as erro:
                logger.warning(f"[RPA 3] {erro}")
                resultado.pulos.append("e-mail de contestação não enviado")
            except Exception as erro:
                logger.excecao(
                    f"[RPA 3] {resultado.operadora}: falha ao enviar a contestação: {erro}"
                )
                resultado.pulos.append("e-mail de contestação falhou")

    # ------------------------------------------------------------------
    # Fase D — HU-20
    # ------------------------------------------------------------------

    def _verificar_relatorio(self, referencia: str) -> None:
        """
        Confere o relatório do AGI contra o Encontro de Contas (HU-20).

        Vem **depois** da carga, porque é ela que confere o que foi carregado
        (V2 ¶690: *"Este relatório é gerado para conferir os valores carregados no
        AGI e no EC"*).

        A V2 (¶706) mandava confirmar se esta HU deveria existir. **O GP/dev
        confirmou em 2026-08-05: fica no escopo** — a Q7 está fechada.

        O `PERMITIR_ACESSO_AGI` continua desligado por padrão, mas por outro
        motivo: a HU-20 **abre o AGI e faz login em produção**, e não há ambiente
        de teste (Q20). É proteção de ambiente, não dúvida de escopo.

        Uma falha aqui **não derruba a execução**: os artefatos já foram gerados e
        carregados, e esta é uma conferência posterior. Derrubar o mês por causa
        dela seria desproporcional.
        """
        from src.services.verificacao_relatorio import (
            RelatorioAgiIndisponivel,
            VerificacaoRelatorio,
        )

        try:
            VerificacaoRelatorio(repositorio=self.repositorio).executar(referencia)
        except RelatorioAgiIndisponivel as erro:
            logger.warning(f"[RPA 3] HU-20 não executada: {erro}")
        except Exception as erro:
            logger.excecao(f"[RPA 3] Falha na verificação do relatório (HU-20): {erro}")

    # ------------------------------------------------------------------
    # Fase E — resumo
    # ------------------------------------------------------------------

    def _gravar_relatorio(
        self,
        resultados: list[ResultadoOperadora],
        referencia: str,
        etapa: str | None,
    ) -> None:
        """
        Grava a tabela esperado × obtido que a homologação compara.

        O `_registrar_resumo` abaixo escreve o mesmo no log, mas o log é
        cronológico e mistura os passos de todas as operadoras. Aqui é uma linha
        por operadora, e a coluna mais consultada é a última: **por que não
        saiu**.
        """
        relatorio = rel.RelatorioExecucao(
            robo="rpa3_contestacao_agi_ec",
            referencia=referencia,
            parametros=[f"etapa: {etapa}"] if etapa else [],
        )

        for resultado in resultados:
            produzidos = {
                "EXT": "sim" if resultado.ext else "-",
                "INT": "sim" if resultado.int_ else "-",
                "_EXP": "sim" if resultado.env else "-",
                "cartas": str(len(resultado.cartas)) if resultado.cartas else "-",
                "CONT_PROC": "sim" if resultado.cont_proc else "-",
            }
            relatorio.acrescentar(
                rel.LinhaDeRelatorio(
                    item=resultado.operadora,
                    produzidos=produzidos,
                    pulos=list(resultado.pulos),
                    erro=resultado.erro,
                )
            )

        ausentes = sum(len(r.despesa.get("ausentes", [])) for r in resultados)
        if ausentes:
            relatorio.observar(
                f"{ausentes} chave(s) da HU-19 sem linha-base no banco. É "
                f"esperado quando o RPA 3 roda isolado — a linha-base é inserida "
                f"pelo RPA 2 (bloqueio B-D20). **Não é defeito deste robô.**"
            )

        if not configuration.CAMINHO_CONTATOS_OPERADORAS:
            relatorio.observar(
                "CAMINHO_CONTATOS_OPERADORAS não configurado: a HU-15 não "
                "envia e-mail (pendência Q16)."
            )

        relatorio.gravar()

    @staticmethod
    def _registrar_resumo(
        resultados: list[ResultadoOperadora], referencia: str
    ) -> None:
        """Resumo do lote, para quem lê o log sem acompanhar a execução."""

        def _quantos(atributo: str) -> int:
            return sum(1 for r in resultados if getattr(r, atributo))

        com_erro = [r for r in resultados if r.erro]
        ausentes = sum(len(r.despesa.get("ausentes", [])) for r in resultados)

        logger.info(
            f"[RPA 3] Resumo de {referencia} — {len(resultados)} operadora(s): "
            f"EXT {_quantos('ext')}, INT {_quantos('int_')}, "
            f"_EXP {_quantos('env')}, "
            f"carta {sum(len(r.cartas) for r in resultados)}, "
            f"CONT_PROC {_quantos('cont_proc')}."
        )

        for resultado in resultados:
            if resultado.pulos:
                logger.info(
                    f"[RPA 3]   {resultado.operadora}: "
                    f"{'; '.join(resultado.pulos)}."
                )

        if ausentes:
            logger.warning(
                f"[RPA 3] {ausentes} chave(s) da HU-19 sem linha-base no banco. "
                f"É esperado quando o RPA 3 roda isolado — a linha é inserida pelo "
                f"RPA 2 (bloqueio B-D20), não é defeito deste robô."
            )

        if com_erro:
            logger.error(
                f"[RPA 3] {len(com_erro)} operadora(s) com erro: "
                f"{', '.join(r.operadora for r in com_erro)}."
            )

        if not configuration.CAMINHO_CONTATOS_OPERADORAS:
            logger.warning(
                "[RPA 3] HU-15 sem destinatários: a tabela de contatos do WebFat "
                "continua sem resposta do cliente (pendência Q16). A ponte é "
                "apontar CAMINHO_CONTATOS_OPERADORAS para um CSV "
                "`operadora;emails`."
            )

    # ------------------------------------------------------------------
    # HUs com writeback próprio (chamáveis isoladamente)
    # ------------------------------------------------------------------

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
            df_contest=df_contest,
            referencia=referencia,
            # Q24 (¶942): `vb_contestacao` só sai nas linhas COM retenção, e o
            # cenário é o sinal do analista — que mora no banco.
            obter_tipo_contestacao=self.repositorio.obter_tipo_contestacao,
        )
        return self.repositorio.atualizar_despesa_contestacao(atualizacoes)
