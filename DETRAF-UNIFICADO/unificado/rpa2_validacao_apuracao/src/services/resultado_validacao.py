from datetime import datetime
from pathlib import Path
from typing import Optional
import pandas as pd

from comum.dominio.classificadores import classificar_descritor_remuneracao
from comum.config.configuration import ANO_MES_REFERENCIA
from comum.config.logger_config import logger
from comum.arquivos.gerenciador import carregar_dados
from comum.dados import tabelas
from comum.dados.repositorio_tabelas import bd_tabelas

# Códigos de erro gravados na coluna `codigo_erro`.
#
# ⚠️ **Provisórios.** O de-para oficial de códigos de erro nunca foi informado
# pelo cliente — a V2 não traz nenhuma tabela de códigos. Até 2026-08-04 existia
# um único valor fixo para toda e qualquer falha, o que tornava a coluna inútil
# para diagnóstico. Estes distinguem as categorias que o código **já** conhece;
# quando o de-para real chegar, é aqui que ele entra.
COD_ERRO_VALIDACAO = "ERR_VALIDACAO_PROCESSAMENTO"
COD_ERRO_LEITURA = "ERR_LEITURA_ARQUIVO"


class LeituraDetrafFalhou(RuntimeError):
    """O arquivo não pôde ser lido — distinto de "lido e sem tráfego"."""


def _arredondar(valor) -> Optional[float]:
    """Arredonda para 2 casas, preservando `None` (leitura falhou)."""
    return None if valor is None else round(float(valor), 2)


def obter_codigo_erro(path_arquivo: Path) -> str:
    """
    Código de erro de um arquivo que caiu no fluxo `_ERRO`.

    Ainda não há de-para oficial (ver o bloco de constantes acima), então a
    categoria vem do que o chamador sabe: este é o caso "arquivo validado e
    reprovado", distinto de "arquivo não pôde ser lido".
    """
    return COD_ERRO_VALIDACAO


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
        """Busca o Tipo de Serviço no Anexo 5 a partir do Nome Fantasia.

        As colunas vêm de ``tabelas.COL_ANEXO5_*``: no banco real elas **não têm
        acento**, e até 2026-08-06 esta linha procurava ``"Tipo de Serviço"``
        acentuado — ``KeyError`` em toda execução contra o MySQL de verdade.
        """
        if not nome_fantasia:
            return None

        # Filtra a tabela em memória para capturar o Tipo de Serviço correspondente
        resultado = self.tbl_anexo5[
            self.tbl_anexo5[tabelas.COL_ANEXO5_NOME_FANTASIA] == nome_fantasia
        ]
        if resultado.empty:
            return None

        return resultado.iloc[0][tabelas.COL_ANEXO5_TIPO_SERVICO]

    def _extrair_dados_internos(self, path_arquivo: Path) -> dict:
        """
        Abre o arquivo, remove as linhas de totais e extrai volumetria e chaves.

        Raises:
            LeituraDetrafFalhou: Se o arquivo não puder ser lido ou interpretado.

        ⚠️ **Zero não é o mesmo que "não consegui ler".** Até 2026-08-04 uma falha
        de I/O caía nos `dados_padrao` — o registro ia para o banco com minutos e
        valor bruto zerados e o arquivo era marcado como processado. Zero é um
        resultado **legítimo** (operadora sem tráfego no mês), então ninguém
        conseguiria distinguir os dois casos depois.

        Os `dados_padrao` continuam valendo para o arquivo que foi **lido com
        sucesso** e não tem linha de tráfego — aí o zero é a resposta correta.
        """
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

        except Exception as erro:
            raise LeituraDetrafFalhou(
                f"Não foi possível ler o arquivo [{path_arquivo.name}]: {erro}"
            ) from erro

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
                codigo_erro = obter_codigo_erro(path_obj)
            else:
                logger.warning(
                    f"Tipo de lote desconhecido: {tipo_lote}. Ignorando arquivo."
                )
                continue

            # A falha de leitura não zera o registro: ela o marca como não
            # validado, com código próprio. Zero é resultado legítimo de uma
            # operadora sem tráfego, e confundir os dois apaga a diferença.
            try:
                dados_internos = self._extrair_dados_internos(path_obj)
            except LeituraDetrafFalhou as erro:
                logger.error(
                    f"[{tipo_lote}] {erro} — registrando como não validado "
                    f"({COD_ERRO_LEITURA}), sem volumetria."
                )
                dados_internos = {
                    "empresa": None,
                    "tipo_servico_operadora": None,
                    "tipo_servico_vivo": None,
                    "remuneracoes": None,
                    "minuto_desp": None,
                    "valor_bruto_desp": None,
                }
                status = "Não validado"
                codigo_erro = COD_ERRO_LEITURA

            linha_tabela = {
                "tipo_registro": tipo_registro,
                "nome_arquivo": path_obj.name,
                "periodo": self.periodo,
                "empresa": dados_internos["empresa"],
                "tipo_servico_operadora": dados_internos["tipo_servico_operadora"],
                "tipo_servico_vivo": dados_internos["tipo_servico_vivo"],
                "remuneracoes": dados_internos["remuneracoes"],
                # `None` quando a leitura falhou — distinto do 0.0 de quem foi
                # lido e não tem tráfego.
                "minuto_desp": _arredondar(dados_internos["minuto_desp"]),
                "valor_bruto_desp": _arredondar(dados_internos["valor_bruto_desp"]),
                "status": status,
                "codigo_erro": codigo_erro,
                "created_at": agora_formatado,
            }

            registros_processados.append(linha_tabela)

        # Retorna o lote consolidado em formato estruturado pronto para a Engine do Banco
        return pd.DataFrame(registros_processados)
