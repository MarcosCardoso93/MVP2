from datetime import datetime
from pathlib import Path
from typing import Optional
import pandas as pd
from loguru import logger

from src.utils.classificadores import classificar_descritor_remuneracao
from src.config.configuration import ANO_MES_REFERENCIA
from src.utils.gerenciador_arquivos import carregar_dados
from src.models.repository.repositorio_tabelas import bd_tabelas


# Placeholder para a função futura de captura do código de erro
def obter_codigo_erro_placeholder(path_arquivo: Path) -> str:
    """
    Placeholder para futura implementação do de-para de códigos de erro.
    Retorna uma string padrão provisória.
    """
    return "ERR_VALIDACAO_PROCESSAMENTO"


class TransformadorRelatorioRPA:
    def __init__(self):
        """
        Inicializa o transformador de relatórios para o banco de dados.

        :param repositorio_cache: Instância da classe RepositorioCache (contém o método validar_eot e o anexo 5)
        :param periodo_fixo: String de período vinda do config.py (Ex: "202604")
        :param carregar_dados_funcao: Referência para a sua função existente 'carregar_dados'
        """
        self.repositorio_tabelas = bd_tabelas
        self.periodo = ANO_MES_REFERENCIA

        # Garante o acesso direto à tabela do anexo 5 tratada em memória
        self.tbl_anexo5 = self.repositorio_tabelas.tbl_anexo5_processado

    def _obter_tipo_servico(self, nome_fantasia: Optional[str]) -> Optional[str]:
        """Busca a coluna 'Tipo de Serviço' no Anexo 5 baseado no Nome Fantasia."""
        if not nome_fantasia:
            return None

        # Filtra a tabela em memória para capturar o Tipo de Serviço correspondente
        resultado = self.tbl_anexo5[self.tbl_anexo5["Nome Fantasia"] == nome_fantasia]
        if resultado.empty:
            return None

        return resultado.iloc[0]["Tipo de Serviço"]

    def _extrair_dados_internos(self, path_arquivo: Path) -> dict:
        """
        Abre o arquivo usando a função padrão, limpa as linhas de totais
        e extrai as volumetrias e chaves de cruzamento do Anexo 5.
        """
        # Inicialização com valores default caso o arquivo não possa ser aberto (Regra 1 e 4)
        dados_padrao = {
            "empresa": None,
            "tipo_servico_operadora": None,
            "tipo_servico_vivo": None,
            "remuneracoes": None,
            "minuto_desp": 0.0,
            "valor_bruto_desp": 0.0,
        }

        try:
            # Uso obrigatório da função existente do projeto (Regra 2)
            df = carregar_dados(path_arquivo)

            if df is None or df.empty:
                return dados_padrao

            # REGRA DE NEGÓCIO: Remover linhas de totais baseando-se na coluna de índice 5
            # Mantém apenas registros puros cujo indicador seja '00', '0' ou 0 numérico
            valores_manter = ["00", "0", 0]
            df_filtrado = df[df.iloc[:, 5].isin(valores_manter)].copy()

            if df_filtrado.empty:
                return dados_padrao

            # Captura da primeira linha de dados purificados para extração de chaves de metadados
            primeira_linha = df_filtrado.iloc[0]

            # 1. Tratamento da Operadora Credora (Coluna Índice 0) -> Empresa e Serviço Operadora
            eot_credora = str(primeira_linha.iloc[0]).strip()
            nome_fantasia_credora = self.repositorio_tabelas.validar_eot(eot_credora)

            # 2. Tratamento da Operadora Devedora (Coluna Índice 1) -> Serviço Vivo
            eot_devedora = str(primeira_linha.iloc[1]).strip()
            nome_fantasia_devedora = self.repositorio_tabelas.validar_eot(eot_devedora)

            # 3. Classificação de Remuneração (Coluna Índice 6)
            descritor_remun = str(primeira_linha.iloc[6]).strip()
            remuneracao_classificada = classificar_descritor_remuneracao(
                descritor_remun
            )

            # 4. Volumetria Financeira e de Tráfego (Somas das colunas de Índice 9 e 14)
            total_minutos = pd.to_numeric(
                df_filtrado.iloc[:, 9].astype(str).str.replace(",", ".", regex=False),
                errors="coerce",
            ).sum()

            total_valor_bruto = pd.to_numeric(
                df_filtrado.iloc[:, 14].astype(str).str.replace(",", ".", regex=False),
                errors="coerce",
            ).sum()

            return {
                "empresa": nome_fantasia_credora,
                "tipo_servico_operadora": self._obter_tipo_servico(
                    nome_fantasia_credora
                ),
                "tipo_servico_vivo": self._obter_tipo_servico(nome_fantasia_devedora),
                "remuneracoes": remuneracao_classificada,
                "minuto_desp": total_minutos,
                "valor_bruto_desp": total_valor_bruto,
            }

        except Exception as e:
            # Tratamento caso o arquivo falhe ao abrir (Regra de Negócio 1)
            logger.error(
                f"Falha crítica de I/O ao ler o arquivo {path_arquivo.name}. Registrando com dados zerados. Erro: {e}"
            )
            return dados_padrao

    def preparar_lote(self, lista_arquivos: list[Path], tipo_lote: str) -> pd.DataFrame:
        """
        Método principal: Recebe a lista de Paths e o tipo de lote mapeado pelo RPA,
        retornando o DataFrame estruturado pronto para inserção direta no banco.

        :param tipo_lote: Pode ser 'DETRAF_SUCESSO', 'DETRAF_ERRO', 'EXPECTATIVA_SUCESSO', 'EXPECTATIVA_ERRO'
        """
        registros_processados = []

        agora_formatado = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.info(
            f"Iniciando transformação de lote tipo [{tipo_lote}] com {len(lista_arquivos)} arquivo(s)."
        )

        for path_obj in lista_arquivos:
            # DETERMINAÇÃO DE MATRIZ DE STATUS E ENUMS CONFORME REGRA DE NEGÓCIO
            if tipo_lote == "DETRAF_SUCESSO":
                tipo_registro = "DETRAF"
                status = "Validado"
                codigo_erro = None
            elif tipo_lote == "DETRAF_ERRO":
                tipo_registro = "DETRAF"
                status = "Não validado"
                codigo_erro = None
            elif tipo_lote == "EXPECTATIVA_SUCESSO":
                tipo_registro = "EXPECTATIVA"
                status = "Validado"
                codigo_erro = None
            elif tipo_lote == "EXPECTATIVA_ERRO":
                tipo_registro = "ERRO"
                status = "Não validado"
                # Uso da função de Placeholder para regras futuras (Regra 3)
                codigo_erro = obter_codigo_erro_placeholder(path_obj)
            else:
                logger.warning(
                    f"Tipo de lote desconhecido: {tipo_lote}. Ignorando arquivo."
                )
                continue

            # Extração ou zeramento dos dados dependendo da natureza do lote
            dados_internos = self._extrair_dados_internos(path_obj)

            linha_tabela = {
                "tipo_registro": tipo_registro,
                "nome_arquivo": path_obj.name,
                "periodo": self.periodo,
                "empresa": dados_internos["empresa"],
                "tipo_servico_operadora": dados_internos["tipo_servico_operadora"],
                "tipo_servico_vivo": dados_internos["tipo_servico_vivo"],
                "remuneracoes": dados_internos["remuneracoes"],
                "minuto_desp": round(float(dados_internos["minuto_desp"]), 2),
                "valor_bruto_desp": round(float(dados_internos["valor_bruto_desp"]), 2),
                "status": status,
                "codigo_erro": codigo_erro,
                "created_at": agora_formatado,
            }

            registros_processados.append(linha_tabela)

        # Retorna o lote consolidado em formato estruturado pronto para a Engine do Banco
        return pd.DataFrame(registros_processados)
