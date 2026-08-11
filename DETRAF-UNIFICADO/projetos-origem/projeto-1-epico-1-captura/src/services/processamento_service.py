from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from src.config import configuration
from src.config.logger_config import logger
from src.models.dto.arquivo_para_processar import ArquivoParaProcessar
from src.models.dto.operadora_resultado import OperadoraResultado
from src.models.repository.repositorio_arquivos import RepositorioArquivos
from src.models.repository.repositorio_tabelas import bd_tabelas
from src.services.competencia_service import Competencia, CompetenciaService
from src.services.operadora_service import OperadoraService
from src.utils.filesystem import construir_caminho_saida, mes_anterior

_SEPARADOR: str = "=" * 50
_PASTA_NAO_IDENTIFICADOS: str = "_NAO_IDENTIFICADOS"


class ProcessamentoService:
    """
    Serviço que orquestra o fluxo completo de processamento de arquivos.

    Responsabilidades:
        - Calcular a competência do processamento.
        - Listar e filtrar arquivos válidos no diretório de entrada.
        - Aplicar regras de negócio a cada arquivo.
        - Determinar a operadora e construir o caminho de saída.
        - Copiar arquivos para a estrutura de destino organizada,
          clonando a estrutura do mês anterior quando necessário.
        - Registrar cada arquivo salvo com sucesso na tabela de despesas.
        - Isolar erros individuais sem interromper o lote.
        - Exibir resumo final de sucesso, falhas e não identificados.

    Preparado para futura paralelização com ThreadPoolExecutor:
    o método _processar_arquivo é autocontido e thread-safe.
    """

    def __init__(self) -> None:
        self._repositorio = RepositorioArquivos()
        self._servico_competencia = CompetenciaService()
        self._sucessos: int = 0
        self._nao_identificados: List[Dict[str, str]] = []
        self._erros: List[Dict[str, str]] = []

    def executar(self, arquivos: Optional[List[ArquivoParaProcessar]] = None) -> None:
        """
        Executa o fluxo principal de processamento.

        Args:
            arquivos: Lista de arquivos a processar, com metadados do e-mail
                de origem (normalmente produzida pelo OutlookController).
                Se None, lista diretamente DIRETORIO_ENTRADA (uso standalone,
                sem informação de remetente — operadora ficará sempre como
                não identificada nesse modo).

        Returns:
            None.
        """
        logger.info("Iniciando fluxo de processamento")

        competencia = self._servico_competencia.obter_competencia()
        logger.info(
            f"Competência: {competencia.competencia} | Ano: {competencia.ano}"
        )

        if arquivos is None:
            arquivos = [
                ArquivoParaProcessar(caminho=caminho)
                for caminho in self._repositorio.listar_arquivos(
                    configuration.DIRETORIO_ENTRADA
                )
            ]
        logger.info(f"Total de arquivos a processar: {len(arquivos)}")

        for pacote in arquivos:
            self._processar_arquivo(pacote, competencia)

        self._exibir_resumo()

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
            arquivo_resultante = self._aplicar_regra_negocio(pacote.caminho)
            resultado_operadora = OperadoraService.obter_operadora(pacote.caminho, pacote.sender_email)

            if not resultado_operadora.identificada:
                self._salvar_nao_identificado(arquivo_resultante, pacote, competencia)
                return

            diretorio_destino = construir_caminho_saida(
                raiz=configuration.DIRETORIO_SAIDA,
                operadora=resultado_operadora.nome,
                ano=competencia.ano,
                competencia=competencia.competencia,
            )

            if not diretorio_destino.exists():
                diretorio_mes_anterior = construir_caminho_saida(
                    raiz=configuration.DIRETORIO_SAIDA,
                    operadora=resultado_operadora.nome,
                    ano=competencia.ano,
                    competencia=mes_anterior(competencia.competencia),
                )
                self._repositorio.clonar_estrutura_mes_anterior(
                    origem=diretorio_mes_anterior,
                    destino=diretorio_destino,
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

            self._registrar_log_despesa(pacote, competencia, resultado_operadora)

        except Exception as excecao:
            self._erros.append({
                "arquivo": pacote.caminho.name,
                "erro": str(excecao),
            })
            logger.error(
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

        Copia o arquivo para uma subpasta de exceção (dentro de
        DIRETORIO_SAIDA) para intervenção manual, sem travar o pipeline
        e sem registrar na tabela de log oficial (não foi "salvo" na
        estrutura definitiva).
        """
        diretorio_destino = (
            configuration.DIRETORIO_SAIDA / _PASTA_NAO_IDENTIFICADOS / competencia.competencia
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

    @staticmethod
    def _registrar_log_despesa(
        pacote: ArquivoParaProcessar,
        competencia: Competencia,
        resultado_operadora: OperadoraResultado,
    ) -> None:
        """Registra o arquivo salvo com sucesso na tabela tbl_detraf_despesa_arquivos."""
        df_despesa = pd.DataFrame([{
            "tipo_registro": "DETRAF",
            "nome_arquivo": pacote.caminho.name,
            "periodo": int(competencia.competencia),
            "empresa": resultado_operadora.nome,
            "tipo_servico_operadora": None,
            "tipo_servico_vivo": None,
            "remuneracoes": None,
            "minuto_desp": 0.0,
            "valor_bruto_desp": 0.0,
            "status": "Validado",
            "codigo_erro": None,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }])
        bd_tabelas.salvar_dados_tabela_despesa(df_despesa)

    @staticmethod
    def _aplicar_regra_negocio(caminho_arquivo: Path) -> Path:
        """
        Aplica a regra de negócio ao arquivo e retorna o caminho resultante.

        # PLACEHOLDER: Implementação temporária — retorna o próprio arquivo.
        # Substituir pela transformação/validação real do arquivo.
        # O retorno deve ser o caminho do arquivo após o processamento,
        # podendo ser o original ou um arquivo gerado no processo.

        Args:
            caminho_arquivo: Caminho do arquivo de entrada.

        Returns:
            Caminho do arquivo resultante após aplicação da regra de negócio.
        """
        return caminho_arquivo

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
        print(f"Arquivos não identificados: {len(self._nao_identificados)}")
        print(f"Arquivos com erro: {len(self._erros)}")

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
            f"Não identificados: {len(self._nao_identificados)} | "
            f"Erros: {len(self._erros)}"
        )
