import re
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pandas as pd

from comum.config import configuration
from comum.config import constantes as const
from comum.config.logger_config import logger
from src.models.dto.arquivo_para_processar import ArquivoParaProcessar
from src.models.dto.arquivo_recusado import ArquivoRecusado
from src.models.dto.operadora_resultado import OperadoraResultado
from src.models.repository.rastreamento_repository import RastreamentoRepository
from src.models.repository.repositorio_arquivos import RepositorioArquivos
from comum.dados.repositorio_tabelas import bd_tabelas
from src.services.competencia_service import Competencia, CompetenciaService
from src.services.operadora_service import OperadoraService
from comum.arquivos.estrutura_pastas import (
    caminho_detrafs_recebidos,
    caminho_mes_operadora,
)
from comum.arquivos.gerenciador import carregar_dados, manter_linhas_por_lista_valores
from comum.arquivos.recusa import registrar_recusa
from comum.dominio.competencia import mes_anterior
from comum.dominio.diagnostico_de_recusa import Diagnostico
from comum.dominio.layout_detraf import validar_layout
from comum.dominio.validacao_colunas import ValidacaoIndisponivel, ValidadorColunas

_SEPARADOR: str = "=" * 50
# O nome da pasta de exceção passou a vir de `configuration.
# DIRETORIO_NAO_IDENTIFICADOS`, porque ela precisou sair de dentro da raiz das
# operadoras — ver `_salvar_nao_identificado`.

_CARACTERES_INVALIDOS = re.compile(r'[<>:"/\\|?*]')


def _pasta_da_evidencia(pacote: ArquivoParaProcessar) -> str:
    """
    Subpasta de quarentena de um arquivo, dentro do mês.

    Existe porque duas operadoras que mandem `DETRAF.csv` no mesmo mês se
    sobrescreveriam — e a evidência de uma delas sumiria, junto com o `.md` que
    explicava a recusa. O `entry_id` é único por e-mail; sem ele (pasta preparada
    à mão) o nome do arquivo serve.
    """
    bruto = pacote.entry_id or pacote.caminho.stem
    seguro = _CARACTERES_INVALIDOS.sub("_", bruto)
    return seguro[-80:] if len(seguro) > 80 else seguro


class ProcessamentoService:
    """
    Serviço que orquestra o fluxo completo de processamento de arquivos.

    Responsabilidades:
        - Calcular a competência do processamento.
        - Listar e filtrar arquivos válidos no diretório de entrada.
        - **Validar o arquivo** (layout e regras de coluna) antes de salvá-lo.
        - Recusar o que não passar: quarentena, diagnóstico e resposta à
          operadora — sem deixar o arquivo entrar na árvore das operadoras.
        - Determinar a operadora e construir o caminho de saída.
        - Copiar arquivos para a estrutura de destino organizada,
          clonando a estrutura do mês anterior quando necessário.
        - Registrar cada arquivo na tabela de despesas.
        - Isolar erros individuais sem interromper o lote.
        - Exibir resumo final de sucesso, recusas, falhas e não identificados.

    ⚠️ A promessa de paralelização com ThreadPoolExecutor que este docstring
    trazia foi retirada em 2026-08-06. `_processar_arquivo` continua autocontido,
    mas passou a carregar o arquivo **inteiro** num DataFrame para validá-lo —
    com Detrafs de centenas de milhares de linhas, N threads seriam N arquivos
    em memória ao mesmo tempo.
    """

    def __init__(
        self,
        notificar: Optional[
            Callable[[ArquivoParaProcessar, List[ArquivoRecusado]], bool]
        ] = None,
    ) -> None:
        """
        Args:
            notificar: Como responder à operadora sobre os arquivos reprovados
                de **um** e-mail. Recebe um pacote daquele e-mail (para o
                `entry_id` e os metadados) e a lista de recusas; devolve se
                conseguiu.

                É injetado, e não construído aqui, para preservar a preguiça do
                `OutlookController` — o `ProcessamentoController` só o instancia
                na primeira vez que alguém pede, de propósito, para que as etapas
                HU-02/03 rodem numa máquina **sem perfil de e-mail**. Construir o
                controller no `__init__` mataria isso.

                `None` pula a notificação com aviso — é o modo standalone.
        """
        self._repositorio = RepositorioArquivos()
        self._servico_competencia = CompetenciaService()
        self._notificar_externo = notificar
        self._sucessos: int = 0
        self._nao_identificados: List[Dict[str, str]] = []
        self._reprovados: List[Dict[str, str]] = []
        #: `entry_id` -> arquivos reprovados daquele e-mail, na ordem em que
        #: apareceram. É o que permite responder uma vez só por envio.
        self._recusas_por_email: Dict[str, List[ArquivoRecusado]] = {}
        #: O pacote de cada `entry_id`, para a resposta ter assunto e remetente.
        self._email_de: Dict[str, ArquivoParaProcessar] = {}
        self._erros: List[Dict[str, str]] = []
        #: Resumo da última execução, para a parada entre etapas mostrar.
        self.resumo: List[str] = []

    def executar(self, arquivos: Optional[List[ArquivoParaProcessar]] = None) -> None:
        """
        Executa o fluxo principal de processamento.

        Args:
            arquivos: Lista de arquivos a processar, com metadados do e-mail
                de origem (normalmente produzida pelo OutlookController).
                Se None, lista diretamente DIRETORIO_ENTRADA — é o modo
                standalone, usado pelo ``--pasta-entrada``.

                ⚠️ Este docstring dizia que nesse modo "a operadora ficará
                sempre como não identificada". **Não é verdade** desde que a V2
                mudou a HU-02: `OperadoraService.obter_operadora` identifica
                pela **EOT credora lida dentro do arquivo**, e só cai no domínio
                do remetente como fallback. Sem remetente, perde-se o fallback,
                não a identificação.

        Returns:
            None.
        """
        logger.info("Iniciando fluxo de processamento")

        competencia = self._servico_competencia.obter_competencia()
        logger.info(
            f"Competência: {competencia.competencia} | Ano: {competencia.ano}"
        )

        if arquivos is None:
            arquivos = self._varrer_pasta_de_entrada()

        logger.info(f"Total de arquivos a processar: {len(arquivos)}")

        for pacote in arquivos:
            self._processar_arquivo(pacote, competencia)

        # DEPOIS do laço, e não dentro dele: a resposta é por e-mail de origem,
        # não por arquivo. Um e-mail com três anexos reprovados gera UMA
        # mensagem listando os três — antes gerava três, sobre o mesmo envio, e
        # a operadora agiria só na primeira.
        self._notificar_reprovados()

        self._exibir_resumo()

    def _varrer_pasta_de_entrada(self) -> List[ArquivoParaProcessar]:
        """
        Monta a lista de trabalho a partir de `DIRETORIO_ENTRADA`, sem Outlook.

        É o que a etapa ``processamento`` usa quando roda sozinha — depois de uma
        ``captura`` anterior, ou sobre uma pasta preparada à mão
        (``--pasta-entrada``).

        ## Duas coisas que precisam acontecer aqui, e o motivo de cada uma

        **1. A busca é recursiva.** A captura grava cada anexo em
        ``dest_root/{entry_id}/`` — uma subpasta por e-mail. O
        `RepositorioArquivos.listar_arquivos` é deliberadamente **raso** (*"Não
        realiza busca recursiva"*), e continuou assim porque outros pontos
        dependem disso. Se esta varredura também fosse rasa, rodar
        ``--etapa captura`` e depois ``--etapa processamento`` não acharia
        **arquivo nenhum** — a divisão em etapas seria uma promessa falsa.

        **2. O remetente é recuperado do rastreamento.** Sem ele, a
        identificação da operadora perde o fallback por domínio (a EOT credora
        dentro do arquivo continua valendo, e é o caminho principal — mas o
        fallback existe justamente para quando ela falha).

        `RastreamentoRepository` já guarda ``caminho_arquivo -> sender_email``
        desde a captura, e `buscar_por_arquivo` o devolve. Com isso, a execução
        dividida produz **o mesmo resultado** da execução única — que é o que
        torna a etapa legítima.

        Arquivo sem rastreamento (pasta preparada à mão) simplesmente vem sem
        remetente, como antes.
        """
        raiz = Path(configuration.DIRETORIO_ENTRADA)

        if not raiz.exists():
            raise FileNotFoundError(
                f"[RPA 1] Pasta de entrada não encontrada: [{raiz}]. "
                f"Confira DIRETORIO_ENTRADA no .env, ou o caminho passado em "
                f"--pasta-entrada."
            )

        extensoes = {ext.lower() for ext in configuration.EXTENSOES_PERMITIDAS}
        caminhos = sorted(
            caminho
            for caminho in raiz.rglob("*")
            if caminho.is_file() and caminho.suffix.lower() in extensoes
        )

        rastreamento = RastreamentoRepository()
        pacotes: list[ArquivoParaProcessar] = []
        com_remetente = 0

        for caminho in caminhos:
            registro = rastreamento.buscar_por_arquivo(caminho)
            if registro is not None:
                com_remetente += 1
            pacotes.append(
                ArquivoParaProcessar(
                    caminho=caminho,
                    sender_email=registro.sender_email if registro else "",
                    entry_id=registro.entry_id if registro else "",
                )
            )

        logger.info(
            f"[RPA 1] {len(pacotes)} arquivo(s) em [{raiz}] (busca recursiva); "
            f"{com_remetente} com remetente recuperado do rastreamento."
        )
        if pacotes and not com_remetente:
            logger.warning(
                "[RPA 1] Nenhum arquivo tem rastreamento: a identificação vai "
                "depender só da EOT credora dentro do arquivo, sem o fallback "
                "por domínio do remetente. É o esperado numa pasta preparada à "
                "mão; se veio de uma captura, confira RASTREAMENTO_ARQUIVO_PATH."
            )

        return pacotes

    def _processar_arquivo(
        self,
        pacote: ArquivoParaProcessar,
        competencia: Competencia,
    ) -> None:
        """
        Processa um único arquivo com tratamento de erro isolado.

        Garante que a falha em um arquivo não interrompa o processamento
        dos demais. Registra erros para exibição no resumo final.

        Args:
            pacote: Arquivo a processar, com metadados do e-mail de origem.
            competencia: Competência calculada para o processamento.

        Returns:
            None.
        """
        try:
            # A captura continua não TRANSFORMANDO o arquivo — o que a operadora
            # mandou é o que vai para a pasta dela, byte a byte. O que mudou em
            # 2026-08-06 é que ela decide se o arquivo entra: valida antes de
            # salvar e, se reprovar, responde à operadora na mesma execução.
            #
            # Antes disso quem validava e respondia era o RPA 2 — o arquivo ruim
            # já estava na árvore quando alguém descobria, e a resposta saía uma
            # execução depois, que podia ser dias.
            arquivo_resultante = pacote.caminho

            df = self._ler(pacote.caminho)
            diagnostico = self._validar(pacote.caminho, df, competencia)
            if diagnostico is not None:
                self._reprovar(pacote, competencia, diagnostico, df)
                return

            # A identificação vem DEPOIS da validação, e a ordem é a decisão que
            # importa aqui. Um arquivo com layout quebrado costuma falhar também
            # na extração da EOT; se a identificação viesse primeiro, ele cairia
            # em `_NAO_IDENTIFICADOS` e **ninguém seria notificado**. Validando
            # antes, a resposta sai sempre — ela depende só do `entry_id`, que
            # veio do Outlook e não do conteúdo do arquivo.
            resultado_operadora = OperadoraService.obter_operadora(pacote.caminho, pacote.sender_email)

            if not resultado_operadora.identificada:
                # Arquivo íntegro, cadastro nosso faltando. Não gera resposta:
                # dizer "seu arquivo está inválido" a quem mandou um arquivo
                # correto ensina a operadora a ignorar o robô.
                self._salvar_nao_identificado(arquivo_resultante, pacote, competencia)
                return

            # A pasta do MÊS é o que se clona do mês anterior (ela carrega a
            # estrutura de subpastas: Detrafs Recebidos, Detrafs Enviados, AGI,
            # Contestações). O arquivo em si vai para a subpasta de entrada.
            pasta_mes = caminho_mes_operadora(
                operadora=resultado_operadora.nome,
                aaaamm=competencia.competencia,
                raiz_operadoras=configuration.CAMINHO_OPERADORAS,
            )

            if not pasta_mes.exists():
                pasta_mes_anterior = caminho_mes_operadora(
                    operadora=resultado_operadora.nome,
                    aaaamm=mes_anterior(competencia.competencia),
                    raiz_operadoras=configuration.CAMINHO_OPERADORAS,
                )
                self._repositorio.clonar_estrutura_mes_anterior(
                    origem=pasta_mes_anterior,
                    destino=pasta_mes,
                )

            # Subpasta exigida pela V2 e varrida pelo RPA 2 (HU-03).
            diretorio_destino = caminho_detrafs_recebidos(
                operadora=resultado_operadora.nome,
                aaaamm=competencia.competencia,
                raiz_operadoras=configuration.CAMINHO_OPERADORAS,
            )

            self._repositorio.criar_diretorio(diretorio_destino)
            self._repositorio.copiar_arquivo(
                origem=arquivo_resultante,
                destino=diretorio_destino / pacote.caminho.name,
            )

            self._sucessos += 1
            logger.info(
                f"Processado com sucesso: {pacote.caminho.name} "
                f"(operadora identificada via '{resultado_operadora.origem}')"
            )

            # 🔴 O RPA 1 NÃO registra o arquivo válido (decisão de 2026-08-10).
            #
            # Ele registrava, e o RPA 2 registrava de novo o mesmo arquivo —
            # duas linhas por Detraf válido, sem chave de deduplicação. A do
            # RPA 1 vinha com seis campos fixos (`tipo_servico_operadora`,
            # `tipo_servico_vivo`, `remuneracoes`, `minuto_desp`,
            # `valor_bruto_desp`, `codigo_erro`) em `None`/`0.0`, porque nesta
            # etapa eles não são conhecidos: quem os apura é a validação.
            # Somar valores não denunciava o problema (a linha daqui é zero),
            # mas contar arquivos no WebFat dava o dobro.
            #
            # A regra passou a ser: **o RPA 1 só grava o que só ele sabe** — o
            # que reprova na captura e o que fica sem operadora. Esses dois
            # nunca chegam ao RPA 2 (vão para a quarentena e para
            # `_NAO_IDENTIFICADOS`, fora da árvore que ele varre), então sem o
            # registro daqui eles desapareceriam do WebFat.

        except ValidacaoIndisponivel as excecao:
            # NÃO é reprovação, e a distinção é o ponto. O arquivo fica onde
            # está, para a próxima execução: mover para a quarentena e responder
            # à operadora seria acusá-la de um problema nosso — e, com
            # NOTIFICAR_OPERADORA_ENVIAR ligado, seria irreversível.
            self._erros.append({
                "arquivo": pacote.caminho.name,
                "erro": f"validação indisponível — {excecao}",
            })
            logger.error(
                f"[RPA 1] '{pacote.caminho.name}' NÃO foi validado: {excecao}. "
                "O arquivo continua na entrada e será retentado. Nenhuma "
                "operadora foi notificada."
            )

        except Exception as excecao:
            self._erros.append({
                "arquivo": pacote.caminho.name,
                "erro": str(excecao),
            })
            logger.excecao(
                f"Erro ao processar '{pacote.caminho.name}': {excecao}"
            )

    def _salvar_nao_identificado(
        self,
        arquivo_resultante: Path,
        pacote: ArquivoParaProcessar,
        competencia: Competencia,
    ) -> None:
        """
        Sinaliza um arquivo cuja operadora não foi identificada.

        Copia o arquivo para a pasta de exceção, para intervenção manual, sem
        travar o pipeline.

        A pasta fica **fora** da raiz das operadoras: o RPA 2 varre essa raiz
        tratando todo diretório como uma operadora, e a de exceção entraria na
        varredura como se fosse uma — poluindo o log e a lista de operadoras
        sem Detraf.

        🔴 **Passou a registrar no WebFat em 2026-08-10.** Antes não registrava,
        com o argumento de que o arquivo não fora "salvo na estrutura
        definitiva". O efeito era pior do que o argumento: o arquivo **chegou**,
        e sumia — nem verde nem vermelho, invisível para o analista. E como ele
        vai para `_NAO_IDENTIFICADOS`, fora da árvore que o RPA 2 varre, ninguém
        mais o registraria depois. É um dos dois casos que só o RPA 1 conhece.
        """
        diretorio_destino = (
            configuration.DIRETORIO_NAO_IDENTIFICADOS / competencia.competencia
        )
        self._repositorio.criar_diretorio(diretorio_destino)
        self._repositorio.copiar_arquivo(
            origem=arquivo_resultante,
            destino=diretorio_destino / pacote.caminho.name,
        )

        self._nao_identificados.append({
            "arquivo": pacote.caminho.name,
            "sender_email": pacote.sender_email,
        })
        logger.warning(
            f"Operadora não identificada para '{pacote.caminho.name}' "
            f"(remetente: '{pacote.sender_email}') — copiado para '{diretorio_destino}'"
        )

        # O arquivo chegou; o que falta é cadastro NOSSO. Sem esta linha ele
        # some do WebFat, e o analista não fica sabendo que houve um Detraf que
        # o robô não soube endereçar.
        self._registrar_log_despesa(
            pacote,
            competencia,
            empresa=None,
            status="Não validado",
            tipo_registro="ERRO",
        )

    # -----------------------------------------------------------------------
    # Validação — o portão que subiu do RPA 2 em 2026-08-06
    # -----------------------------------------------------------------------
    @staticmethod
    def _ler(caminho: Path) -> Optional[pd.DataFrame]:
        """
        Lê o arquivo uma vez, para o layout e para as regras de coluna.

        Uma leitura só, e não duas: o arquivo passou a ser lido **inteiro** aqui
        (antes só duas linhas, para achar a EOT), e ele pode ter centenas de
        milhares de linhas.

        Devolve `None` quando não deu para ler. Não levanta: um arquivo ilegível
        é uma recusa com motivo — se virasse erro, ficaria preso na entrada e
        seria retentado para sempre, sem ninguém ser avisado.
        """
        try:
            return carregar_dados(caminho)
        except Exception as erro:
            logger.warning(f"[RPA 1] Não foi possível ler [{caminho.name}]: {erro}")
            return None

    @staticmethod
    def _validar(
        caminho: Path, df: Optional[pd.DataFrame], competencia: Competencia
    ) -> Optional[Diagnostico]:
        """
        Confere layout e regras de coluna. `None` significa aprovado.

        A ordem é a mesma do RPA 2 e não é arbitrária: o layout responde "este
        arquivo não é o que eu esperava" e precisa vir antes, porque as regras de
        coluna leem por posição e não fazem sentido num arquivo deslocado.

        Raises:
            ValidacaoIndisponivel: o banco não respondeu. Não é reprovação —
                ver o tratamento em `_processar_arquivo`.
        """
        if df is None:
            return Diagnostico(
                motivo="o arquivo não pôde ser lido (formato, codificação ou "
                "conteúdo corrompido)."
            )

        resultado_layout = validar_layout(df)
        if not resultado_layout.conforme:
            logger.warning(resultado_layout.mensagem(caminho))
            return resultado_layout.diagnostico()

        # 🔴 As linhas de TOTAL saem antes das regras de coluna, exatamente como
        # o RPA 2 faz em `_validar_colunas_arquivos`.
        #
        # Elas têm `Rel = 1` e vêm com os demais campos VAZIOS — inclusive as
        # EOTs. Validá-las reprova o arquivo em "há códigos de operadora que não
        # constam do Anexo 5", e **todo Detraf real tem linha de total**.
        #
        # Foi o que aconteceu em 2026-08-07, na primeira execução do portão
        # contra arquivos reais: os dois Detrafs da ALGAR foram recusados por uma
        # única linha, a de total. Sem esta remoção o portão recusa 100% dos
        # arquivos válidos — e responde a todas as operadoras.
        df_sem_totais = manter_linhas_por_lista_valores(
            df=df, indice_coluna=const.COL_REL, valores_manter=["00", "0", 0]
        )

        # A referência vai explícita: é a MESMA competência com que o caminho de
        # destino é montado logo abaixo. Deixar o validador resolvê-la sozinho
        # abriria a possibilidade de o robô validar contra um mês e gravar noutro.
        validador = ValidadorColunas(referencia=competencia.competencia)
        resultado = validador.validar_tudo_detalhado(df_sem_totais, "detraf")
        if not resultado.conforme:
            logger.warning(resultado.mensagem(caminho))
            return resultado.diagnostico(total_colunas=int(df.shape[1]))

        return None

    def _reprovar(
        self,
        pacote: ArquivoParaProcessar,
        competencia: Competencia,
        diagnostico: Diagnostico,
        df: Optional[pd.DataFrame],
    ) -> None:
        """
        Põe o arquivo reprovado em quarentena e responde à operadora.

        **Nada é copiado para a árvore das operadoras.** É o que garante que a
        reprovação é um beco sem saída: se o arquivo chegasse lá, o RPA 2 o
        encontraria, o validaria de novo e — antes desta mudança — responderia à
        operadora uma segunda vez.
        """
        # 1. Identificação em MELHOR ESFORÇO, só para o log ter a empresa.
        #    Falhar aqui não cancela nada do que vem depois: a recusa já está
        #    decidida, e a resposta não depende de saber quem mandou.
        empresa: Optional[str] = None
        try:
            resultado_operadora = OperadoraService.obter_operadora(
                pacote.caminho, pacote.sender_email
            )
            if resultado_operadora.identificada:
                empresa = resultado_operadora.nome
        except Exception as erro:
            logger.warning(
                f"[RPA 1] Não foi possível identificar a operadora de "
                f"[{pacote.caminho.name}] para o registro da recusa: {erro}"
            )

        # 2. A cópia, numa subpasta por e-mail — ver `_pasta_da_evidencia`.
        destino_pasta = (
            configuration.DIRETORIO_QUARENTENA
            / competencia.competencia
            / _pasta_da_evidencia(pacote)
        )
        self._repositorio.criar_diretorio(destino_pasta)
        destino = destino_pasta / pacote.caminho.name
        self._repositorio.copiar_arquivo(origem=pacote.caminho, destino=destino)

        # 3. O diagnóstico ao lado da CÓPIA, não do original: o original está em
        #    DIRETORIO_ENTRADA, que é transitória e a captura repovoa. Quem for
        #    investigar está olhando o arquivo em quarentena.
        registrar_recusa(destino, diagnostico, df)

        # 4. O registro que o RPA 2 deixou de fazer. Sem ele, o lote DETRAF_ERRO
        #    do WebFat iria a zero e quem lê o relatório leria como "melhorou".
        self._registrar_log_despesa(
            pacote, competencia, empresa, status="Não validado"
        )

        # 5. A recusa fica ANOTADA; quem responde é `_notificar_reprovados`, no
        #    fim da execução. Notificar aqui mandaria uma mensagem por arquivo.
        motivos = diagnostico.motivos()
        chave = pacote.entry_id or str(pacote.caminho)
        self._recusas_por_email.setdefault(chave, []).append(
            ArquivoRecusado(nome=pacote.caminho.name, motivos=motivos)
        )
        self._email_de.setdefault(chave, pacote)

        self._reprovados.append({
            "arquivo": pacote.caminho.name,
            "empresa": empresa or "(não identificada)",
            "motivo": motivos[0] if motivos else "sem motivo registrado",
            "email": chave,
            "notificada": "pendente",
        })
        logger.warning(
            f"[RPA 1] '{pacote.caminho.name}' REPROVADO na validação — "
            f"quarentena em [{destino_pasta}]."
        )

    def _notificar_reprovados(self) -> None:
        """
        Responde **uma vez por e-mail de origem**, listando os arquivos daquele
        envio que foram recusados.

        Roda depois de todos os arquivos terem sido processados, porque só aí se
        sabe quantos anexos do mesmo e-mail caíram. Nunca levanta: quando isto
        roda, as recusas já estão consumadas — os arquivos estão na quarentena,
        com o diagnóstico ao lado. Falhar em avisar é ruim; desfazer a recusa por
        causa disso seria pior.
        """
        if not self._recusas_por_email:
            return

        if self._notificar_externo is None:
            logger.warning(
                f"[RPA 1] {len(self._reprovados)} arquivo(s) reprovado(s), mas "
                "não há como responder aos e-mails (execução sem Outlook). Eles "
                "estão na quarentena, com o diagnóstico ao lado."
            )
            self._marcar_notificados(self._recusas_por_email, notificada=False)
            return

        for chave, recusas in self._recusas_por_email.items():
            pacote = self._email_de[chave]
            try:
                sucesso = bool(self._notificar_externo(pacote, recusas))
            except Exception as erro:
                # Um erro do Outlook num e-mail não pode calar o robô nos outros.
                logger.excecao(
                    f"[RPA 1] Falha ao responder o e-mail de origem de "
                    f"'{pacote.caminho.name}': {erro}"
                )
                sucesso = False

            self._marcar_notificados({chave: recusas}, notificada=sucesso)
            logger.info(
                f"[RPA 1] E-mail de origem de '{pacote.caminho.name}': "
                f"{len(recusas)} arquivo(s) recusado(s), operadora "
                f"{'notificada' if sucesso else 'NÃO notificada'}."
            )

    def _marcar_notificados(self, grupos: Dict, notificada: bool) -> None:
        """Reflete no resumo o que a notificação conseguiu."""
        chaves = set(grupos)
        for registro in self._reprovados:
            if registro.get("email") in chaves:
                registro["notificada"] = "sim" if notificada else "NÃO"

    @staticmethod
    def _registrar_log_despesa(
        pacote: ArquivoParaProcessar,
        competencia: Competencia,
        empresa: Optional[str],
        status: str = "Validado",
        tipo_registro: str = "DETRAF",
    ) -> None:
        """Registra o arquivo na tabela de log de despesa.

        ⚠️ **Só é chamado para o que o RPA 2 nunca vai ver** (decisão de
        2026-08-10): o arquivo reprovado na captura e o que ficou sem operadora.
        Os dois vão para pastas fora da árvore que o RPA 2 varre, então este é o
        único registro que eles terão. O arquivo **válido** não passa por aqui —
        quem o registra é o RPA 2, que conhece os valores.

        Os campos de volumetria vão fixos em `None`/`0.0` e isso é correto para
        os dois casos que restaram: um arquivo recusado ou não identificado não
        tem minutagem apurada, e inventá-la seria pior.

        Args:
            empresa: Nome da operadora, ou `None` quando não identificada — o
                que acontece na recusa, onde a identificação é melhor esforço.
            status: `"Validado"` ou `"Não validado"`.
            tipo_registro: `"DETRAF"` para o recusado (é Detraf de operadora, só
                reprovado) e `"ERRO"` para o não identificado — nesse caso nem se
                sabe se é Detraf ou expectativa, porque a EOT não resolveu.
        """
        df_despesa = pd.DataFrame([{
            "tipo_registro": tipo_registro,
            "nome_arquivo": pacote.caminho.name,
            "periodo": int(competencia.competencia),
            "empresa": empresa,
            "tipo_servico_operadora": None,
            "tipo_servico_vivo": None,
            "remuneracoes": None,
            "minuto_desp": 0.0,
            "valor_bruto_desp": 0.0,
            "status": status,
            "codigo_erro": None,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }])
        bd_tabelas.salvar_dados_tabela_despesa(df_despesa)

    def _exibir_resumo(self) -> None:
        """
        Exibe o resumo final do processamento no console e no logger.

        Returns:
            None.
        """
        print(f"\n{_SEPARADOR}")
        print("PROCESSAMENTO FINALIZADO")
        print(f"{_SEPARADOR}\n")
        print(f"Arquivos processados: {self._sucessos}")
        print(f"Arquivos reprovados na validação: {len(self._reprovados)}")
        print(f"Arquivos não identificados: {len(self._nao_identificados)}")
        print(f"Arquivos com erro: {len(self._erros)}")

        if self._reprovados:
            print()
            for registro in self._reprovados:
                print(f"{registro['arquivo']} ({registro['empresa']})")
                print(f"-> {registro['motivo']}")
                print(f"-> operadora notificada: {registro['notificada']}\n")

        if self._nao_identificados:
            print()
            for registro in self._nao_identificados:
                print(f"{registro['arquivo']} -> remetente: {registro['sender_email']}")

        if self._erros:
            print()
            for registro in self._erros:
                print(registro["arquivo"])
                print(f"-> {registro['erro']}\n")

        logger.info(
            f"Resumo — Sucesso: {self._sucessos} | "
            f"Reprovados: {len(self._reprovados)} | "
            f"Não identificados: {len(self._nao_identificados)} | "
            f"Erros: {len(self._erros)}"
        )

        # Os mesmos números, estruturados para a parada entre etapas. Montados
        # aqui, junto da contagem, para não haver duas versões do resumo.
        self.resumo = [
            f"Arquivos salvos:          {self._sucessos}",
            f"Reprovados na validação:  {len(self._reprovados)}",
            f"Não identificados:        {len(self._nao_identificados)}",
            f"Com erro:                 {len(self._erros)}",
        ]
        if self._reprovados:
            self.resumo += ["", "Reprovados (vão para a quarentena, não para a operadora):"]
            for registro in self._reprovados:
                self.resumo.append(
                    f"  {registro['arquivo']} ({registro['empresa']})"
                )
                self.resumo.append(f"      {registro['motivo']}")
                self.resumo.append(
                    f"      operadora notificada: {registro['notificada']}"
                )
        if self._nao_identificados:
            self.resumo += ["", "Não identificados (vão para a pasta de exceção):"]
            self.resumo += [
                f"  {registro['arquivo']}  ← remetente: {registro['sender_email']}"
                for registro in self._nao_identificados
            ]
        if self._erros:
            self.resumo += ["", "Com erro:"]
            self.resumo += [
                f"  {registro['arquivo']}: {registro['erro']}"
                for registro in self._erros
            ]
