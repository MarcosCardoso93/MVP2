from src.config.logger_config import logger
from src.utils.decoradores import log_execucao
from pathlib import Path
import pandas as pd
from src.config.configuration import (
    CAMINHO_DETRAF_RECEBIDO,
    CAMINHO_EXPECTATIVA_DETRAF,
    ANO_MES_REFERENCIA,
    EXTENSOES_PERMITIDAS,
    PASTAS_EXPECTATIVAS,
    EXPECTATIVA_SUBSTRING,
    IGNORAR_ARQUIVOS,
    RASTREAMENTO_ARQUIVO_PATH,
    CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO,
)
from src.services.notificacao_email import responder_email_por_arquivo
from src.models.repository.repositorio_tabelas import bd_tabelas
from src.services.validacao_inicial.validacao_colunas import ValidadorColunas
from src.services.validacao_inicial.limpeza_trafegos import LimpadorTrafegos
from src.utils.gerenciador_arquivos import (
    carregar_dados,
    manter_linhas_por_lista_valores,
    separar_e_salvar_por_mascara,
    salvar_dados,
)
from src.utils.historico_arquivos import ValidadorHistoricoRPA
from src.utils.utils import salvar_debug_log
from src.services.resultado_validacao import TransformadorRelatorioRPA
from src.utils.gerenciador_arquivos import renomear_arquivo_com_sufixo


class ValidacaoDetrafsService:
    def __init__(self):
        self.repositorio_tabelas = bd_tabelas
        self.operadoras_sem_detraf: list[str] = []
        self.validador_colunas = ValidadorColunas()
        self.validador_separar_trafegos = LimpadorTrafegos()
        self.arquivos_invalidos: set[Path] = set()
        self.historico_rpa = ValidadorHistoricoRPA()
        self.resultado_validacao = TransformadorRelatorioRPA()

    @log_execucao
    def _preparar_arquivos_detrafs(self) -> list[Path]:
        """
        Varre o diretório raiz buscando arquivos (CSV ou Planilhas) dentro da estrutura
        de pastas de cada operadora para o ano e mês de referência informados.

        Returns:
            list[Path]: Lista contendo os caminhos completos (Path) de todos os arquivos válidos encontrados.
        """
        logger.info("Preparando os detrafs para validação...")

        # Extrai o ano (4 primeiros dígitos) e o ano_mes para montar o caminho
        ano = ANO_MES_REFERENCIA[:4]
        ano_mes = ANO_MES_REFERENCIA

        caminhos_encontrados: list[Path] = []

        # Dicionário para rastrear a contagem de arquivos válidos por operadora
        arquivos_por_operadora: dict[str, int] = {}

        # Conjunto de extensões permitidas para validação rápida O(1)
        extensoes_validas = EXTENSOES_PERMITIDAS

        logger.info(
            f"Iniciando busca de arquivos para o período {ano_mes} no diretório: '{CAMINHO_DETRAF_RECEBIDO}'"
        )

        try:
            # Iterar sobre a pasta raiz para encontrar as pastas das operadoras
            for item_raiz in CAMINHO_DETRAF_RECEBIDO.iterdir():
                if item_raiz.is_dir():
                    nome_operadora = item_raiz.name

                    # Monta o caminho esperado: RAIZ / OPERADORA / ANO / ANOMES
                    pasta_alvo = item_raiz / ano / ano_mes

                    # 3. Verifica se a operadora possui a estrutura de pastas para este ano/mês
                    if pasta_alvo.exists() and pasta_alvo.is_dir():
                        logger.info(
                            f"Varrendo arquivos da operadora: [{nome_operadora}]"
                        )

                        # Inicializa o contador desta operadora específica
                        arquivos_por_operadora[nome_operadora] = 0

                        # Varre os arquivos específicos daquela pasta alvo
                        for arquivo in pasta_alvo.iterdir():
                            if not arquivo.is_file():
                                continue

                            nome_arquivo = arquivo.name

                            # Ignora arquivos contendo substrings proibidas
                            deve_ignorar = any(
                                sub in nome_arquivo for sub in IGNORAR_ARQUIVOS
                            )

                            if deve_ignorar:
                                continue

                            # Valida extensão permitida
                            if arquivo.suffix.lower() not in extensoes_validas:
                                continue

                            caminhos_encontrados.append(arquivo)
                            arquivos_por_operadora[nome_operadora] += 1
                    else:
                        # Log de aviso caso a operadora exista mas não tenha dados para aquele mês específico
                        logger.debug(
                            f"Operadora [{nome_operadora}] não possui dados para a referência {ano_mes}."
                        )
                        self.operadoras_sem_detraf.append(nome_operadora)

        except Exception as erro:
            logger.error(f"Erro inesperado durante a varredura dos diretórios: {erro}")
            raise RuntimeError(f"Falha ao mapear arquivos detrafs: {erro}")

        # Gera o log final com os indicadores de volumetria solicitados
        total_operadoras_encontradas = len(arquivos_por_operadora)
        logger.info(
            f"Mapeamento concluído com sucesso. "
            f"Total de operadoras processadas com dados: {total_operadoras_encontradas}. "
            f"Total geral de arquivos encontrados: {len(caminhos_encontrados)}"
        )

        # Exibe o detalhamento por operadora no log
        for operadora, qtd_arquivos in arquivos_por_operadora.items():
            logger.info(
                f"-> Operadora [{operadora}]: {qtd_arquivos} arquivo(s) encontrado(s)"
            )

        return self.historico_rpa.filtrar_arquivos_novos(caminhos_encontrados)

    @log_execucao
    def _preparar_arquivos_expectativa(
        self,
    ) -> list[Path]:
        """
        Varre pastas de operadoras específicas dentro do diretório de expectativa
        e retorna os caminhos dos arquivos válidos (CSV/Planilhas) cujo nome contenha
        ao menos uma das substrings informadas.

        Ao final, exibe um resumo com o número de arquivos válidos e inválidos por pasta.

        Args:
            operadoras_alvo (str): Strings de operadoras separadas por vírgula (ex: "Vivo,TLF").
            substrings_validas (str): Substrings de filtro separadas por vírgula (ex: "_D,_D_").

        Returns:
            list[Path]: Lista com os caminhos completos dos arquivos que passaram nos filtros.
        """
        logger.info("Preparando os arquivos de expectativa para validação...")

        caminhos_encontrados: list[Path] = []
        extensoes_validas = EXTENSOES_PERMITIDAS

        # Validação de segurança do diretório raiz de expectativa
        if (
            not CAMINHO_EXPECTATIVA_DETRAF.exists()
            or not CAMINHO_EXPECTATIVA_DETRAF.is_dir()
        ):
            raise FileNotFoundError(
                f"O caminho de expectativa não foi encontrado ou não é um diretório: '{CAMINHO_EXPECTATIVA_DETRAF}'"
            )

        try:
            # 2. Iterar apenas sobre as operadoras solicitadas na lista
            for pasta in PASTAS_EXPECTATIVAS:
                pasta_operadora = CAMINHO_EXPECTATIVA_DETRAF / pasta

                # Inicializa os contadores para o resumo final desta pasta
                arquivos_validos_pasta = 0
                arquivos_invalidos_pasta = 0

                if pasta_operadora.exists() and pasta_operadora.is_dir():

                    # Varre os arquivos diretamente na pasta da operadora
                    for arquivo in pasta_operadora.iterdir():
                        if arquivo.is_file():
                            nome_arquivo = arquivo.name
                            extensao = arquivo.suffix.lower()

                            # Critério de ignorar arquivos
                            deve_ignorar = any(
                                sub in nome_arquivo for sub in IGNORAR_ARQUIVOS
                            )

                            # Se estiver na lista de ignorados, pula imediatamente
                            if deve_ignorar:
                                arquivos_invalidos_pasta += 1
                                continue

                            # Critério 1: Validar se a extensão é permitida
                            # Critério 2: Validar se o nome do arquivo contém alguma das substrings alvo
                            possui_extensao_valida = extensao in extensoes_validas
                            possui_substring = any(
                                sub in nome_arquivo for sub in EXPECTATIVA_SUBSTRING
                            )

                            if possui_extensao_valida and possui_substring:
                                caminhos_encontrados.append(arquivo)
                                arquivos_validos_pasta += 1
                            else:
                                # Contabiliza como inválido/ignorado conforme a regra do escopo
                                arquivos_invalidos_pasta += 1

                    # Exibe o resumo consolidado por pasta conforme solicitado (apenas se a pasta existir)
                    logger.info(
                        f"Pasta [{pasta}] processada -> "
                        f"Válidos: {arquivos_validos_pasta} | Inválidos/Ignorados: {arquivos_invalidos_pasta}"
                    )

        except Exception as erro:
            logger.error(
                f"Erro inesperado durante a varredura das expectativas: {erro}"
            )
            raise RuntimeError(f"Falha ao mapear arquivos de expectativa: {erro}")

        logger.info(
            f"Mapeamento de expectativa concluído. Total geral de arquivos válidos: {len(caminhos_encontrados)}"
        )
        return self.historico_rpa.filtrar_arquivos_novos(caminhos_encontrados)

    def _verificar_formato_col5(self, arquivos: list[Path]) -> None:
        valores_manter = ["00", "0", 0]
        for arquivo in arquivos:
            try:
                df = carregar_dados(arquivo)
                if df is None or df.empty:
                    continue
                df_filtrado = df[df.iloc[:, 5].isin(valores_manter)]
                if df_filtrado.empty:
                    logger.warning(
                        f"Arquivo [{arquivo.name}] marcado como inválido: "
                        f"possuía {len(df)} linha(s) antes do filtro e 0 após — "
                        f"o filtro da coluna Rel (índice 5) zerou o arquivo, "
                        f"provavelmente porque está fora do padrão esperado."
                    )
                    self.arquivos_invalidos.add(arquivo)
            except Exception as e:
                logger.error(f"Erro ao verificar col 5 do arquivo [{arquivo}]: {e}")
                self.arquivos_invalidos.add(arquivo)

    def _validar_colunas_arquivos(
        self, arquivos: list[Path], tipo_arquivo: str, debug: bool = False
    ):
        for arquivo in arquivos:
            logger.info(f"Validando as colunas do arquivo de {tipo_arquivo}: {arquivo}")
            try:
                # Carrega o arquivo bruto
                df = carregar_dados(arquivo)

                # Remover as linhas de totais porque elas não seguem as regras de negócio e podem causar falhas na validação
                df_filtrado = manter_linhas_por_lista_valores(
                    df=df, indice_coluna=5, valores_manter=["00", "0", 0, 00]
                )

                if debug:
                    linhas_antes = df.shape[0]
                    linhas_depois = df_filtrado.shape[0]
                    linhas_removidas = linhas_antes - linhas_depois

                    # Dispara o aviso caso de fato alguma linha de faturamento/total tenha sido removida
                    if linhas_removidas > 0:
                        logger.warning(
                            f"Linhas de totais/resumos descartadas no arquivo [{arquivo.name}]. "
                            f"Total antes: {linhas_antes} | Total depois: {linhas_depois} | "
                            f"Diferença (linhas removidas): {linhas_removidas}"
                        )

                if df_filtrado is None:
                    logger.error(
                        f"Falha ao carregar o arquivo [{arquivo}]. Verifique o formato e o conteúdo."
                    )
                    self.arquivos_invalidos.add(arquivo)
                    continue

                if tipo_arquivo == "expectativa":
                    self._validar_colunas_expectativa(
                        arquivo, df, df_filtrado, debug=debug
                    )
                    continue

                valido = self.validador_colunas.validar_tudo(
                    df_filtrado, tipo_arquivo, debug=debug
                )
                if valido:
                    logger.info(
                        f"Arquivo [{arquivo}] passou em todas as validações."
                    )
                else:
                    logger.warning(
                        f"Arquivo [{arquivo}] falhou em uma ou mais validações."
                    )
                    self.arquivos_invalidos.add(arquivo)
            except Exception as erro:
                logger.error(f"Erro ao validar o arquivo [{arquivo}]: {erro}")
                self.arquivos_invalidos.add(arquivo)

    def _validar_colunas_expectativa(
        self,
        arquivo: Path,
        df: pd.DataFrame,
        df_filtrado: pd.DataFrame,
        debug: bool = False,
    ) -> None:
        """
        Para arquivos de expectativa, separa linha a linha as que falham em
        qualquer regra de validação de coluna, mantendo as linhas válidas
        (mais as linhas de totalização, removidas antes da validação) no
        arquivo original. O arquivo original NÃO é marcado inválido — só as
        linhas ruins são movidas para um arquivo `_ERRO` à parte.
        """
        if df_filtrado.empty:
            return

        mascara_valida = self.validador_colunas.validar_tudo_mascara(
            df_filtrado, "expectativa", debug=debug
        )

        df_validas, df_invalidas, caminho_erro = separar_e_salvar_por_mascara(
            df_filtrado, mascara_valida, arquivo
        )

        if df_invalidas.empty:
            logger.info(f"Arquivo [{arquivo}] passou em todas as validações.")
            return

        # Linhas de totalização removidas antes da validação nunca são
        # inválidas por essas regras — voltam para o arquivo original.
        df_linhas_totais = df.loc[df.index.difference(df_filtrado.index)]
        df_validas_final = pd.concat([df_validas, df_linhas_totais]).sort_index()
        salvar_dados(df_validas_final, arquivo)

        logger.warning(
            f"Arquivo [{arquivo}] teve {len(df_invalidas)} linha(s) movida(s) para "
            f"[{caminho_erro.name if caminho_erro else '?'}] por falha de validação de coluna."
        )

    def _validar_fluxo(
        self,
        arquivos: list[Path],
        tipo_fluxo: str,
        sufixo: str = "",
        debug: bool = False,
        gerar_arquivos: bool = True,
        sinalizar_como_invalido: bool = False,
    ):
        """
        Valida um fluxo específico para uma lista de arquivos.
        """
        for arquivo in arquivos:
            logger.info(f"Validando o fluxo {tipo_fluxo} do arquivo: {arquivo}")
            try:
                arquivo_com_fluxo_especial = self.validador_separar_trafegos.executar(
                    caminho_arquivo=arquivo,
                    tipo_fluxo=tipo_fluxo,
                    sufixo=sufixo,
                    debug=debug,
                    gerar_arquivos=gerar_arquivos,
                )
                if sinalizar_como_invalido and arquivo_com_fluxo_especial:
                    logger.warning(
                        f"Arquivo [{arquivo}] atende ao fluxo {tipo_fluxo} e foi sinalizado como inválido conforme configuração."
                    )
                    self.arquivos_invalidos.add(arquivo)

            except Exception as erro:
                logger.error(
                    f"Erro ao validar o fluxo {tipo_fluxo} do arquivo [{arquivo}]: {erro}"
                )
                self.arquivos_invalidos.add(arquivo)

    def _notificar_arquivos_invalidos(self, arquivos: list[Path] | set[Path]):
        """
        Cria um rascunho de resposta ao e-mail original de cada arquivo de
        detraf marcado como inválido (por qualquer critério de validação),
        avisando a operadora. Deve rodar antes de renomear_arquivos_processados,
        pois usa o nome original do arquivo (o mesmo do rastreamento de e-mails).
        """
        if not arquivos:
            return

        if not CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO.exists():
            logger.error(
                f"Template de e-mail de detraf inválido não encontrado em "
                f"[{CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO}]. "
                f"Notificação não enviada para {len(arquivos)} arquivo(s)."
            )
            return

        template = CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO.read_text(encoding="utf-8")

        for arquivo in arquivos:
            try:
                sucesso = responder_email_por_arquivo(
                    nome_arquivo=arquivo.name,
                    template=template,
                    caminho_rastreamento=RASTREAMENTO_ARQUIVO_PATH,
                    enviar=False,
                )
                if not sucesso:
                    logger.warning(
                        f"Não foi possível criar o rascunho de notificação de arquivo inválido para [{arquivo}]."
                    )
            except Exception as erro:
                logger.error(
                    f"Erro ao notificar por e-mail o arquivo inválido [{arquivo}]: {erro}"
                )

    def _salvar_historico_arquivos_processados(self, todos_arquivos: set[Path]):
        arquivos_validos = todos_arquivos - self.arquivos_invalidos
        self.historico_rpa.registrar_arquivos(
            lista_caminhos=list(arquivos_validos), status_valido=True
        )
        self.historico_rpa.registrar_arquivos(
            lista_caminhos=list(self.arquivos_invalidos), status_valido=False
        )

    def _eh_arquivo_expectativa(self, arquivo: Path) -> bool:
        return any(sub in arquivo.name for sub in EXPECTATIVA_SUBSTRING)

    def separar_arquivos_por_categoria(
        self,
        arquivos_detraf: list[Path],
        arquivos_expectativa: list[Path],
        debug: bool = False,
    ) -> dict[str, list[Path]]:
        """
        Separa os arquivos gerados em 4 categorias distintas cruza-referenciando
        o histórico de inválidos e a função de identificação de tipo.

        Retorna um dicionário contendo:
        {
            "detraf_validos": [...],
            "detraf_invalidos": [...],
            "expectativa_validos": [...],
            "expectativa_invalidos": [...],
        """
        todos_arquivos = set(arquivos_detraf + arquivos_expectativa)

        invalidos_do_lote = todos_arquivos.intersection(self.arquivos_invalidos)
        validos_do_lote = todos_arquivos - invalidos_do_lote

        # Separação por Tipo utilizando a sua função de identificação do projeto
        # Categoria: Detraf
        detraf_validos = [
            arq for arq in validos_do_lote if not self._eh_arquivo_expectativa(arq)
        ]
        detraf_invalidos = [
            arq for arq in invalidos_do_lote if not self._eh_arquivo_expectativa(arq)
        ]

        # Categoria: Expectativa
        expectativa_validos = [
            arq for arq in validos_do_lote if self._eh_arquivo_expectativa(arq)
        ]
        expectativa_invalidos = [
            arq for arq in invalidos_do_lote if self._eh_arquivo_expectativa(arq)
        ]

        resultado = {
            "detraf_validos": detraf_validos,
            "detraf_invalidos": detraf_invalidos,
            "expectativa_validos": expectativa_validos,
            "expectativa_invalidos": expectativa_invalidos,
        }
        if debug:
            logger.debug(
                f"Resultado da separação de arquivos por categoria: {resultado}"
            )

            linhas = [
                "RESULTADO DA VALIDAÇÃO",
                "=" * 80,
                f"TOTAL DE ARQUIVOS: {sum(len(v) for v in resultado.values())}",
                "=" * 80,
                "",
            ]

            categorias = [
                ("DETRAF VÁLIDOS", resultado["detraf_validos"]),
                ("DETRAF INVÁLIDOS", resultado["detraf_invalidos"]),
                ("EXPECTATIVA VÁLIDOS", resultado["expectativa_validos"]),
                ("EXPECTATIVA INVÁLIDOS", resultado["expectativa_invalidos"]),
            ]

            for titulo, arquivos in categorias:
                linhas.append(f"{titulo} ({len(arquivos)})")
                linhas.append("-" * 80)

                if arquivos:
                    for path in arquivos:
                        linhas.append(f"  • {path.name}")
                else:
                    linhas.append("  Nenhum arquivo")

                linhas.append("")

            linhas.append("=" * 80)

            conteudo = "\n".join(linhas)

            salvar_debug_log(
                nome_arquivo="RESULTADO_VALIDACAO",
                conteudo=conteudo,
            )

        return resultado

    @staticmethod
    def renomear_arquivos_processados(
        arquivos_validos: set[Path], arquivos_invalidos: set[Path]
    ):
        if arquivos_validos:
            logger.info(
                f"Renomeando {len(arquivos_validos)} arquivos validados adicionando _ENV"
            )
            for arquivo in arquivos_validos:
                renomear_arquivo_com_sufixo(arquivo, sufixo="_ENV")

        if arquivos_invalidos:
            logger.info(
                f"Renomeando {len(arquivos_invalidos)} arquivos inválidos adicionando _ERRO"
            )
            for arquivo in arquivos_invalidos:
                renomear_arquivo_com_sufixo(arquivo, sufixo="_ERRO")

    @log_execucao
    def executar(self):
        logger.info("Executando a validação dos detrafs...")
        arquivos_detraf = self._preparar_arquivos_detrafs()
        arquivos_expectativa = self._preparar_arquivos_expectativa()
        if not arquivos_detraf:
            logger.warning(
                "Nenhum arquivo de detraf encontrado para validação. Verifique os logs anteriores para detalhes."
            )
        if not arquivos_expectativa:
            logger.warning(
                "Nenhum arquivo de expectativa encontrado para validação. Verifique os logs anteriores para detalhes."
            )

        # Verificar se existe fluxo _BK nos arquivos de expectativa
        self._validar_fluxo(arquivos_expectativa, tipo_fluxo="BK", sufixo="_BK")

        # Verificar se existe fluxo LL nos arquivos de expectativa e de detraf
        self._validar_fluxo(arquivos_expectativa, tipo_fluxo="LL", sufixo="_ERRO")
        self._validar_fluxo(
            arquivos_detraf,
            tipo_fluxo="LL",
            gerar_arquivos=False,
            sinalizar_como_invalido=True,  # Unico caso em que é necessario sinalizar o arquivo como invalido
        )  # Não separar os trafegos nos detrafs ja que são arquivos de outras operadorsa

        # Descartar antecipadamente arquivos cujo filtro de col 5 zera todas as linhas
        self._verificar_formato_col5(arquivos_detraf + arquivos_expectativa)

        # Validar os arquivos de detraf encontrados (exclui os já marcados inválidos)
        self._validar_colunas_arquivos(
            [a for a in arquivos_detraf if a not in self.arquivos_invalidos],
            tipo_arquivo="detraf",
            debug=False,
        )

        # Validar os arquivos de expectativa encontrados (exclui os já marcados inválidos)
        self._validar_colunas_arquivos(
            [a for a in arquivos_expectativa if a not in self.arquivos_invalidos],
            tipo_arquivo="expectativa",
        )

        # Inserir no banco o resultado das validações
        arquivos_processados = self.separar_arquivos_por_categoria(
            arquivos_detraf, arquivos_expectativa, debug=True
        )

        detraf_sucesso = self.resultado_validacao.preparar_lote(
            lista_arquivos=arquivos_processados["detraf_validos"],
            tipo_lote="DETRAF_SUCESSO",
        )
        detraf_erro = self.resultado_validacao.preparar_lote(
            lista_arquivos=arquivos_processados["detraf_invalidos"],
            tipo_lote="DETRAF_ERRO",
        )
        expectativa_sucesso = self.resultado_validacao.preparar_lote(
            lista_arquivos=arquivos_processados["expectativa_validos"],
            tipo_lote="EXPECTATIVA_SUCESSO",
        )
        expectativa_erro = self.resultado_validacao.preparar_lote(
            lista_arquivos=arquivos_processados["expectativa_invalidos"],
            tipo_lote="EXPECTATIVA_ERRO",
        )

        lotes_preparados = [
            detraf_sucesso,
            detraf_erro,
            expectativa_sucesso,
            expectativa_erro,
        ]

        df_consolidado_final = pd.concat(lotes_preparados, ignore_index=True)

        if not df_consolidado_final.empty:
            self.repositorio_tabelas.salvar_dados_tabela_despesa(df_consolidado_final)  # type: ignore

        todos_arquivos = set(arquivos_detraf + arquivos_expectativa)

        # Salvar o historico localmente e na tabela
        self._salvar_historico_arquivos_processados(todos_arquivos)

        # Notificar a operadora por e-mail (rascunho) de todo detraf marcado inválido
        self._notificar_arquivos_invalidos(arquivos_processados["detraf_invalidos"])

        # Renomear os arquivos processados para evitar reprocessamentos futuros
        arquivos_validos = todos_arquivos - self.arquivos_invalidos
        self.renomear_arquivos_processados(
            arquivos_validos=arquivos_validos,
            arquivos_invalidos=self.arquivos_invalidos,
        )

        ...
