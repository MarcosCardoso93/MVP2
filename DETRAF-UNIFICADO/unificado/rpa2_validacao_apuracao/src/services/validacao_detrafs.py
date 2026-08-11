from comum.config.logger_config import logger
from src.services.expectativa import acusar_expectativa_ausente
from comum.arquivos.recusa import registrar_recusa
from comum.utils.decoradores import log_execucao
from pathlib import Path
import pandas as pd
from comum.config.configuration import (
    CAMINHO_DETRAF_RECEBIDO,
    CAMINHO_EXPECTATIVA_DETRAF,
    ANO_MES_REFERENCIA,
    EXTENSOES_PERMITIDAS,
    PASTAS_EXPECTATIVAS,
    EXPECTATIVA_SUBSTRING,
    IGNORAR_ARQUIVOS,
    SUBPASTA_DETRAFS_RECEBIDOS,
    DIRETORIO_TEMP,
    DIRETORIO_SAIDA_VALIDACAO,
)
from comum.arquivos.area_de_trabalho import AreaDeTrabalho
from comum.dados.repositorio_tabelas import bd_tabelas
from comum.dominio.validacao_colunas import ValidadorColunas
from src.services.validacao_inicial.limpeza_trafegos import LimpadorTrafegos
from comum.arquivos.gerenciador import (
    carregar_dados,
    manter_linhas_por_lista_valores,
    separar_e_salvar_por_mascara,
    salvar_dados,
)
from comum.arquivos import estrutura_pastas as ep
from comum.arquivos.historico import ValidadorHistoricoRPA
from comum.dominio.layout_detraf import validar_layout
from comum.utils.debug import salvar_debug_log
from src.services.resultado_validacao import TransformadorRelatorioRPA
from comum.arquivos.gerenciador import renomear_arquivo_com_sufixo


class ValidacaoDetrafsService:
    def __init__(self):
        self.repositorio_tabelas = bd_tabelas
        self.operadoras_sem_detraf: list[str] = []
        self.validador_colunas = ValidadorColunas()
        self.validador_separar_trafegos = LimpadorTrafegos()
        self.arquivos_invalidos: set[Path] = set()
        self.historico_rpa = ValidadorHistoricoRPA()
        self.resultado_validacao = TransformadorRelatorioRPA()
        #: Resumo da última execução, para a parada entre etapas mostrar.
        self.resumo: list[str] = []
        #: Onde esta etapa escreve, e para onde ela entrega. O insumo original
        #: não é tocado, e os artefatos vão para `DIRETORIO_SAIDA_VALIDACAO` — não para a
        #: pasta de entrada. Quem lê do outro lado é o batimento, pela MESMA
        #: função `caminho_de_saida`.
        self.area = AreaDeTrabalho(
            DIRETORIO_TEMP,
            ANO_MES_REFERENCIA,
            destino_de=lambda pasta: ep.caminho_de_saida(
                pasta, ANO_MES_REFERENCIA, raiz_saida=DIRETORIO_SAIDA_VALIDACAO
            ),
        )

    @log_execucao
    def _preparar_arquivos_detrafs(self) -> list[Path]:
        """
        Varre o diretório raiz buscando arquivos (CSV ou Planilhas) dentro da estrutura
        de pastas de cada operadora para o ano e mês de referência informados.

        Returns:
            list[Path]: Lista contendo os caminhos completos (Path) de todos os arquivos válidos encontrados.
        """
        logger.info("Preparando os detrafs para validação...")

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
            # A varredura de `{operadora}/{ano}/{aaaamm}` vem de `comum`: ela
            # estava duplicada aqui e em `batimento_detraf`, e o RPA 3 precisava
            # da mesma coisa. A subpasta é exigida pela V2 (HU-03) e é onde o
            # RPA 1 grava — os dois lados usam a mesma constante para não
            # divergirem.
            com_detraf = ep.listar_operadoras_do_mes(
                ano_mes,
                raiz_operadoras=CAMINHO_DETRAF_RECEBIDO,
                subpasta=SUBPASTA_DETRAFS_RECEBIDOS,
            )

            # "Sem Detraf no mês" é o complemento das pastas de operadora que
            # existem na raiz — inclusive as que só têm meses anteriores. É esta
            # lista que denuncia a operadora que simplesmente não enviou.
            todas = sorted(
                pasta.name
                for pasta in CAMINHO_DETRAF_RECEBIDO.iterdir()
                if pasta.is_dir()
            )
            self.operadoras_sem_detraf.extend(
                operadora for operadora in todas if operadora not in com_detraf
            )

            for nome_operadora in com_detraf:
                logger.info(f"Varrendo arquivos da operadora: [{nome_operadora}]")
                arquivos_por_operadora[nome_operadora] = 0

                pasta_alvo = ep.caminho_detrafs_recebidos(
                    nome_operadora, ano_mes, raiz_operadoras=CAMINHO_DETRAF_RECEBIDO
                )

                for arquivo in pasta_alvo.iterdir():
                    if not arquivo.is_file():
                        continue

                    # Ignora arquivos contendo substrings proibidas
                    if any(sub in arquivo.name for sub in IGNORAR_ARQUIVOS):
                        continue

                    if arquivo.suffix.lower() not in extensoes_validas:
                        continue

                    caminhos_encontrados.append(arquivo)
                    arquivos_por_operadora[nome_operadora] += 1

        except Exception as erro:
            logger.excecao(
                f"Erro inesperado durante a varredura dos diretórios: {erro}"
            )
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

        # Validação de segurança do diretório raiz de expectativa.
        #
        # A variável agora é `None` quando não configurada. Antes era `Path(".")`,
        # e esta guarda passava — o diretório atual existe e é um diretório —,
        # fazendo o robô varrer o CWD e concluir "nenhum arquivo" sem erro.
        if CAMINHO_EXPECTATIVA_DETRAF is None:
            raise FileNotFoundError(
                "CAMINHO_EXPECTATIVA_DETRAF não está configurado. É a raiz da "
                "expectativa Vivo (Detrafs Enviados); sem ela não há com o que "
                "comparar os arquivos das operadoras."
            )

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

                    if arquivos_validos_pasta == 0:
                        acusar_expectativa_ausente(
                            pasta_operadora,
                            f"existe, mas nenhum dos {arquivos_invalidos_pasta} "
                            f"arquivo(s) passou nos filtros",
                        )
                else:
                    acusar_expectativa_ausente(pasta_operadora, "não existe")

        except Exception as erro:
            logger.error(
                f"Erro inesperado durante a varredura das expectativas: {erro}"
            )
            raise RuntimeError(f"Falha ao mapear arquivos de expectativa: {erro}")

        logger.info(
            f"Mapeamento de expectativa concluído. Total geral de arquivos válidos: {len(caminhos_encontrados)}"
        )
        return self.historico_rpa.filtrar_arquivos_novos(caminhos_encontrados)

    def _validar_layout_arquivos(self, arquivos: list[Path]) -> None:
        """
        Confere se cada arquivo tem o layout documentado na V2, **antes** de
        qualquer validação linha a linha.

        É a diferença entre "este arquivo tem uma linha ruim" e "este arquivo
        não é o arquivo que eu esperava". Sem esta camada, um arquivo com layout
        diferente passa direto e é lido por posição — o código pega o índice 14
        achando que é `R$_Bruto` e recebe minutos, sem nada indicar o problema.

        A regra vale para os DOIS tipos de arquivo, operadora e expectativa,
        porque a V2 diz que as regras de validação valem para ambos (decisão do
        cliente, 2026-07-31).

        ⚠️ Consequência conhecida: os arquivos de expectativa Vivo atuais NÃO
        conformam com a V2 e passam a ser rejeitados. É o comportamento pedido —
        falhar alto é melhor que comparar coluna errada em silêncio —, mas
        significa que não haverá comparação até a geração ser corrigida no ICT.
        O diagnóstico no log identifica esse caso pelo nome.
        """
        for arquivo in arquivos:
            try:
                df = carregar_dados(arquivo)
                resultado = validar_layout(df)

                if not resultado.conforme:
                    logger.error(resultado.mensagem(arquivo))
                    self.arquivos_invalidos.add(arquivo)
                    registrar_recusa(arquivo, resultado, df)

            except Exception as erro:
                logger.excecao(
                    f"Erro ao validar o layout do arquivo [{arquivo}]: {erro}"
                )
                self.arquivos_invalidos.add(arquivo)

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
                logger.excecao(f"Erro ao verificar col 5 do arquivo [{arquivo}]: {e}")
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
                    # `error`, e nao `warning`: desde 2026-08-06 o RPA 1 valida
                    # ANTES de salvar, e nada reprovado deveria chegar ate aqui.
                    # Um arquivo reprovado neste ponto e uma ANOMALIA — ou o
                    # portao da captura falhou, ou alguem pos o arquivo na pasta
                    # a mao. Nos dois casos, alguem precisa olhar.
                    logger.error(
                        f"Arquivo [{arquivo}] falhou em uma ou mais validações "
                        "APÓS ter passado pelo portão do RPA 1 — investigar por "
                        "que ele chegou à pasta da operadora."
                    )
                    self.arquivos_invalidos.add(arquivo)
            except Exception as erro:
                logger.excecao(f"Erro ao validar o arquivo [{arquivo}]: {erro}")
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
                logger.excecao(
                    f"Erro ao validar o fluxo {tipo_fluxo} do arquivo [{arquivo}]: {erro}"
                )
                self.arquivos_invalidos.add(arquivo)

    def _salvar_historico_arquivos_processados(self, todos_arquivos: set[Path]):
        """
        Registra o resultado por arquivo, sempre pelo caminho do **insumo**.

        `todos_arquivos` já chega traduzido; `self.arquivos_invalidos` guarda
        cópias de trabalho e precisa ser traduzido aqui — sem isso a subtração
        não casaria nenhum caminho e todo arquivo entraria como válido.
        """
        invalidos = set(self.area.origens(self.arquivos_invalidos))
        arquivos_validos = todos_arquivos - invalidos
        self.historico_rpa.registrar_arquivos(
            lista_caminhos=list(arquivos_validos), status_valido=True
        )
        self.historico_rpa.registrar_arquivos(
            lista_caminhos=list(invalidos), status_valido=False
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
                f"Renomeando {len(arquivos_validos)} arquivos validados adicionando _EXP"
            )
            for arquivo in arquivos_validos:
                renomear_arquivo_com_sufixo(arquivo, sufixo="_EXP")

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

        # A partir daqui, TUDO opera sobre a cópia. A troca acontece num ponto
        # só, e de propósito: as validações não sabem — e não precisam saber —
        # que estão escrevendo na área de trabalho, porque cada uma escreve ao
        # lado do arquivo que recebeu. É o que mantém a proteção do insumo sem
        # espalhar o assunto por dez funções.
        arquivos_detraf = self.area.acolher(arquivos_detraf)
        arquivos_expectativa = self.area.acolher(arquivos_expectativa)

        # Validação de LAYOUT — vem antes de tudo. Um arquivo com layout errado
        # é lido por posição e produz números sem sentido silenciosamente; não
        # faz sentido aplicar as demais regras sobre ele.
        self._validar_layout_arquivos(arquivos_detraf + arquivos_expectativa)

        # Fluxo _BK — vale para os DOIS tipos de arquivo (corrigido 2026-08-10).
        #
        # Rodava só na expectativa. A V2 é explícita na HU-06: o tráfego L→V de
        # EOTs SMP não-PMS é separado numa cópia com `_BK`, e *"vale tanto para o
        # arquivo da operadora quanto para o de expectativa Vivo"*. Enquanto só a
        # expectativa era tratada, o mesmo tráfego ficava separado de um lado e
        # inteiro do outro — e a comparação da HU-10 passava a somar coisas
        # diferentes sem nada indicar.
        self._validar_fluxo(
            arquivos_expectativa + arquivos_detraf, tipo_fluxo="BK", sufixo="_BK"
        )

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

        # Renomear os arquivos processados para evitar reprocessamentos futuros
        arquivos_validos = todos_arquivos - self.arquivos_invalidos
        self.renomear_arquivos_processados(
            arquivos_validos=arquivos_validos,
            arquivos_invalidos=self.arquivos_invalidos,
        )

        # Devolver os artefatos às pastas de origem. Vem DEPOIS da renomeação,
        # senão o que sobe é a cópia de trabalho crua, sem o `_EXP`/`_ERRO` que
        # diz o que aconteceu com ela.
        self.area.promover()

        # O histórico é indexado pelo caminho ABSOLUTO, e quem precisa constar
        # nele é o insumo — não a cópia. Registrar a cópia deixaria o original
        # invisível ao filtro anti-reprocessamento, e ele voltaria inteiro na
        # execução seguinte.
        self._salvar_historico_arquivos_processados(
            set(self.area.origens(todos_arquivos))
        )

        # Resumo estruturado para a parada entre etapas. Montado aqui, junto da
        # categorização, para não existirem duas versões da mesma contagem.
        self.resumo = [
            f"Detraf válidos:           {len(arquivos_processados['detraf_validos'])}",
            f"Detraf inválidos:         {len(arquivos_processados['detraf_invalidos'])}",
            f"Expectativa válidos:      {len(arquivos_processados['expectativa_validos'])}",
            f"Expectativa inválidos:    {len(arquivos_processados['expectativa_invalidos'])}",
        ]
        if self.operadoras_sem_detraf:
            self.resumo += [
                "",
                f"Operadoras sem Detraf no mês ({len(self.operadoras_sem_detraf)}):",
                "  " + ", ".join(sorted(self.operadoras_sem_detraf)),
            ]
        if self.arquivos_invalidos:
            self.resumo += [
                "",
                "Recusados (cada um tem um *_RECUSADO.md ao lado):",
            ]
            self.resumo += [f"  {caminho.name}" for caminho in sorted(self.arquivos_invalidos)]

        ...
