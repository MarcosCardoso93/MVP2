from mysql.connector import Error, connect
from datetime import datetime
from src.config.config import CONFIG_RPA  # conexao dos LOGS (banco 'rpa', host 79)

class Banco:

    def __init__(self, config_dict, config_log=None):
        # config: conexao de NEGOCIO (webfat/77) - selects, updates de enviado/enviado_agi, tbl_cancelados
        self.config = config_dict
        # config_log: conexao dos LOGS (rpa/79). Default = CONFIG_RPA (nao precisa mexer nos servicos).
        self.config_log = config_log or CONFIG_RPA

    def _obter_conexao(self, config=None):
        # Desempacota as chaves: host, user, password, database.
        # config opcional: usa a conexao passada (ex.: logs/rpa); senao, a de negocio (self.config).
        return connect(**(config or self.config))
    

    # def _obter_conexao(self):
    #     return mysql.connector.connect(
    #         host= HOST_BD,
    #         port = PORT_BD,
    #         user= USUARIO_BD,
    #         password= SENHA_BD,
    #         database= DATABASE
    #     )

    def selecionar_dados(self,sql, params=None):
        try:
            with self._obter_conexao() as conexao:
                with conexao.cursor(dictionary=True) as cursor:
                    cursor.execute(sql, params or ())
                    return cursor.fetchall()
        except Error as e:
            print(f"Erro ao ler dados: {e}")
            return []

    def _inserir_banco(self,tabela, dados_dict, config=None):
        """
        tabela: Nome da tabela (string)
        dados_dict: Dicionário onde a chave é a coluna e o valor é o dado
        Ex: {"nome": "Nota 1", "valor": 100.50}
        """
        # 1. Prepara as colunas e os placeholders (%s) de forma dinâmica
        colunas = ", ".join(dados_dict.keys())
        placeholders = ", ".join(["%s"] * len(dados_dict))
        
        # 2. Monta a estrutura da query sem os valores reais ainda
        sql = f"INSERT INTO {tabela} ({colunas}) VALUES ({placeholders})"
        
        # 3. Extrai apenas os valores na ordem correta
        valores = tuple(dados_dict.values())

        try:
            with self._obter_conexao(config) as conexao:
                with conexao.cursor() as cursor:
                    # O driver MySQL recebe o SQL e os VALORES SEPARADAMENTE
                    # Ele limpa os valores antes de fundi-los ao SQL
                    cursor.execute(sql, valores)
                    conexao.commit()
                    return cursor.lastrowid
        except Error as e:
            print(f"Tentativa de inserção negada ou erro técnico: {e}")
            return None

    def _atualizar_banco(self,tabela, novos_valores, condicao_dict):
        """
        tabela: Nome da tabela (str)
        novos_valores: {'coluna_nova': 'valor_novo'}
        condicao_dict: {'coluna_filtro': 'valor_filtro'} 
        """
        # 1. Monta a parte do SET (coluna1=%s, coluna2=%s)
        campos_set = ", ".join([f"{coluna} = %s" for coluna in novos_valores.keys()])
        
        # 2. Monta a parte do WHERE (id=%s)
        campos_where = " AND ".join([f"{coluna} = %s" for coluna in condicao_dict.keys()])
        
        sql = f"UPDATE {tabela} SET {campos_set} WHERE {campos_where}"
        
        # 3. Une os valores na ordem correta: primeiro os do SET, depois os do WHERE
        valores = tuple(novos_valores.values()) + tuple(condicao_dict.values())

        try:
            with self._obter_conexao() as conexao:
                with conexao.cursor() as cursor:
                    cursor.execute(sql, valores)
                    conexao.commit()
                    return cursor.rowcount  # Retorna quantas linhas foram alteradas
        except Error as e:
            self.log(processo="Finalizado",status="ERRO",descricao = f"Erro ao atualizar: {e}" )
            print(f"Erro ao atualizar: {e}")
            return 0

    def log(self,processo,status,descricao):
        """
        processo: "Iniciado" ou "Finalizado"; status: "Sucesso" ou "Erro" (ver PLANO_LOGS_POR_RPA.md
        do RPA_DETRAF_RECEITA - mesma estrutura, tabela dedicada por RPA/HU).
        """
        data_log = datetime.now()
        log = {
        "rpa": "Detraf Despesa - HU-15 (Envio Email Contestacao)",
        "processo": processo,
        "status": status,
        "descricao": descricao,
        "data_log": data_log
        }
        # LOGS vao para a conexao 'rpa' (host 79); o resto (negocio) fica no self.config (webfat/77).
        # TODO: confirmar nome definitivo da tabela (citado no To Be MVP2, paragrafo 5.4.5.9)
        result = self._inserir_banco("tbl_rpa_log_detraf_despesa_contestacao",log, config=self.config_log)
        return result

    def inserir_nota_cancelada(self, num_nf,operadora,tipo_produto):
        data_log = datetime.now()
        info_nota = {
        "num_nf": num_nf,
        "nota_enviada": "nao",
        "operadora": operadora,
        "data_inserido": data_log,
        "tipo_produto": tipo_produto,
        "historico": "nao" 
        }
        result = self._inserir_banco("tbl_cancelados_detraf",info_nota)
        return result

    def atualizar_envio(self,num_nf,historico):

        novos_valores = {
            "nota_enviada": "sim",
            "historico": historico
        }

        # Filtro para encontrar a nota certa
        filtro = {"num_nf": num_nf}

        tabela = "tbl_cancelados_detraf"
        # Execução
        linhas_alteradas = self._atualizar_banco(tabela, novos_valores, filtro)
        return linhas_alteradas

    def marcar_enviado_agi(self, condicao_dict, enviado_agi, arquivo_agi=None):
        """
        Marca o resultado do upload no AGI em tbl_encontro_contas:
        enviado_agi = 2 (sucesso) ou 3 (falha); arquivo_agi = nome do arquivo enviado (opcional).
        condicao_dict: filtro que identifica a linha (ex.: arquivo_detraf, periodo, empresa, remuneracoes).
        """
        novos_valores = {"enviado_agi": enviado_agi}
        if arquivo_agi is not None:
            novos_valores["arquivo_agi"] = arquivo_agi
        return self._atualizar_banco("tbl_encontro_contas", novos_valores, condicao_dict)


# # Dados que vieram de algum lugar (ex: leitura de um PDF de nota)
# nova_nota = {
#     "numero_nota": "2024-001",
#     "cliente": "Empresa X",
#     "valor": 550.00
# }

# # Chamada limpa e segura
# id_gerado = self._inserir_banco("notas_fiscais", nova_nota)
