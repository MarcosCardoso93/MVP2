import os
from pathlib import Path

from src.config.config import (
    CONFIG_WEBFAT, DIRETORIO_CONTESTACOES, DIRETORIO_TEMP,
    OUTLOOK_ACCOUNT, PERMITIR_ENVIO_EMAIL, PERIODO_REF,
)
from src.config.conexao import Banco
from src.services.Outlook.outlook_standalone_com_anexo import (
    OutlookServiceComAnexo, OutlookConfig, OutlookError,
)

"""
HU-15 - Envio do e-mail de contestação à operadora
=====================================================
Critérios de aceite:
    - Destinatários da tabela de contatos do WebFat
    - Assunto: CONTESTAÇÃO_TBRA|{operadora}_{mês}
    - Anexos: carta de contestação + arquivo _ENV
    - Disparo automático após sinalização do analista - sem aprovação manual

REAPROVEITADO:
    - Conexao/envio via Outlook COM: 100% do modulo outlook_standalone.py fornecido
      (classe OutlookService, agora estendida em OutlookServiceComAnexo - ver
      src/services/Outlook/outlook_standalone_com_anexo.py).
    - Acesso a banco (Banco/conexao.py) - mesmo padrao usado em todo o projeto
      (Batimento.py, Criacao_Remessa.py etc. no exemplo RPA_DETRAF_RECEITA).
    - Padrao de "buscar responsavel/contato por operadora via SQL" - inspirado no
      Criacao_Remessa._tratativa_remessa(), que ja faz
      `self.db_webfat.selecionar_dados(sql="select * from tbl_carteirizacao WHERE
      operadora_nome LIKE %s;", params=(...))` pra achar o e-mail responsavel por operadora.
      Aqui a ideia e igual, so mudando para a tabela de CONTATOS DA OPERADORA (nao a
      carteirizacao interna) - ver TODO abaixo.

NOVO (nao existe equivalente pronto no exemplo nem no outlook_standalone.py):
    - Toda a logica de negocio desta classe (buscar contestacoes sinalizadas, montar
      destinatarios/assunto/corpo, decidir os 2 anexos, marcar como enviado).
    - O GATILHO "apos sinalizacao do analista" - precisa ser uma condicao de banco
      (WHERE algum campo indica que o analista ja decidiu com/sem retencao), nao existe
      hoje nenhuma tabela/coluna mapeada para isso neste pacote - ver TODO em
      _buscar_contestacoes_sinalizadas.
"""

# Template do corpo do e-mail - texto EXATO do To Be MVP2 (paragrafos 278-283)
CORPO_EMAIL_TEMPLATE = """Prezados,

Segue a contestação para a sua análise e validação, referente ao mês {mes}

Att,
"""


class Envio_Email_Contestacao:

    def __init__(self):
        self.db = Banco(CONFIG_WEBFAT)
        self.outlook_cfg = OutlookConfig(
            account=OUTLOOK_ACCOUNT,
            root_folder="DETRAF-DESPESA-CONTESTACAO",  # TODO: confirmar nome de pasta desejado
            dest_root=Path(DIRETORIO_TEMP or "."),
        )
        self._outlook: OutlookServiceComAnexo | None = None

    # ------------------------------------------------------------------
    # Fluxo principal
    # ------------------------------------------------------------------
    def Fluxo_Envio_Email_Contestacao(self):
        pendentes = self._buscar_contestacoes_sinalizadas()
        if not pendentes:
            print("[HU-15] Nenhuma contestação sinalizada pelo analista pendente de envio.")
            return

        if not PERMITIR_ENVIO_EMAIL:
            print(f"[MODO SEGURO] Envio de e-mail desabilitado (PERMITIR_ENVIO_EMAIL=False); "
                  f"{len(pendentes)} e-mail(s) montado(s) em memória, nada enviado.")
            for c in pendentes:
                print(f"  - {self._montar_assunto(c)} -> {self._buscar_destinatarios(c['operadora'])}")
            return

        self._outlook = OutlookServiceComAnexo(self.outlook_cfg)

        for contestacao in pendentes:
            # self.db.log(processo="Iniciado", status="Sucesso",
            #             descricao=f"{contestacao['operadora']}/{contestacao['mes']}")
            try:
                self._enviar_email_operadora(contestacao)
                self._marcar_email_enviado(contestacao, sucesso=True)
                print(f"[HU-15][OK] {contestacao['operadora']} / {contestacao['mes']}")
            except Exception as e:
                self._marcar_email_enviado(contestacao, sucesso=False, erro=str(e))
                print(f"[HU-15][FALHA] {contestacao['operadora']} / {contestacao['mes']}: {e}")

    # ------------------------------------------------------------------
    # TODO [NOVO - gatilho de negocio]: buscar no banco as contestacoes que o analista ja
    # sinalizou (com ou sem retencao) no WebFat e que AINDA NAO tiveram o e-mail enviado.
    # E este flag/coluna que substitui a "aprovacao manual adicional" - uma vez marcado
    # pelo analista, o envio e automatico (criterio de aceite: "sem aprovacao manual").
    # Confirmar com o solicitante:
    #   - Nome da tabela/coluna que registra a escolha do analista (com/sem retencao)
    #   - Nome da coluna que marca se o e-mail ja foi enviado (p/ nao reenviar)
    # Retorna uma lista de dicts:
    #   {"operadora": ..., "mes": ..., "caminho_carta": ..., "caminho_env": ..., "id": ...}
    # ------------------------------------------------------------------
    def _buscar_contestacoes_sinalizadas(self):
        # --- esqueleto: substituir pela query real quando a tabela for confirmada ---
        # exemplo de formato esperado da query (adaptar nomes reais):
        # sql = (
        #     "SELECT id, operadora, periodo AS mes FROM tbl_contestacao_despesa "
        #     "WHERE status_analista IN ('COM_RETENCAO','SEM_RETENCAO') "
        #     "AND email_enviado = 0"
        # )
        # linhas = self.db.selecionar_dados(sql)
        linhas = []
        pendentes = []
        for linha in linhas:
            caminho_carta, caminho_env = self._localizar_arquivos_contestacao(
                linha["operadora"], linha["mes"]
            )
            if not caminho_carta or not caminho_env:
                print(f"[HU-15][AVISO] carta/_ENV nao encontrados para {linha['operadora']}/{linha['mes']}")
                continue
            pendentes.append({
                "id": linha["id"],
                "operadora": linha["operadora"],
                "mes": linha["mes"],
                "caminho_carta": caminho_carta,
                "caminho_env": caminho_env,
            })
        return pendentes

    # ------------------------------------------------------------------
    # NOVO - localiza os 2 arquivos que este processo (etapas anteriores do Epico 4:
    # geracao do arquivo _ENV e da carta) ja deixou prontos na pasta da operadora.
    # ------------------------------------------------------------------
    def _localizar_arquivos_contestacao(self, operadora, mes):
        if not DIRETORIO_CONTESTACOES or not os.path.isdir(DIRETORIO_CONTESTACOES):
            return None, None
        caminho_carta = None
        caminho_env = None
        for arquivo in os.listdir(DIRETORIO_CONTESTACOES):
            nome_upper = arquivo.upper()
            if operadora.upper() not in nome_upper or str(mes) not in nome_upper:
                continue
            if nome_upper.endswith("_ENV.XLS") or nome_upper.endswith("_ENV.XLSX"):
                caminho_env = os.path.join(DIRETORIO_CONTESTACOES, arquivo)
            elif "CARTA" in nome_upper or nome_upper.endswith((".DOC", ".DOCX", ".PDF")):
                caminho_carta = os.path.join(DIRETORIO_CONTESTACOES, arquivo)
        return caminho_carta, caminho_env

    # ------------------------------------------------------------------
    # TODO [CONFIRMAR tabela real]: buscar destinatarios na "tabela de contatos do WebFat"
    # (citada no To Be MVP2, paragrafo 136, mas sem nome de tabela/coluna especificado).
    # Padrao de QUERY inspirado em Criacao_Remessa._tratativa_remessa() (exemplo de
    # Receita), que busca e-mail responsavel via tbl_carteirizacao - aqui e outra tabela
    # (contatos da OPERADORA, nao carteirizacao interna), mas o JEITO de consultar e igual.
    # ------------------------------------------------------------------
    def _buscar_destinatarios(self, operadora: str) -> list[str]:
        # --- esqueleto: substituir pela query real quando a tabela for confirmada ---
        # sql = "SELECT email FROM tbl_contatos_operadora WHERE operadora_nome LIKE %s"
        # linhas = self.db.selecionar_dados(sql, params=(f"%{operadora}%",))
        # return [linha["email"] for linha in linhas]
        return []

    def _montar_assunto(self, contestacao) -> str:
        # Criterio de aceite: Assunto: CONTESTAÇÃO_TBRA|{operadora}_{mês}
        return f"CONTESTAÇÃO_TBRA|{contestacao['operadora']}_{contestacao['mes']}"

    def _montar_corpo(self, contestacao) -> str:
        # Texto EXATO do To Be MVP2 (paragrafos 278-283)
        return CORPO_EMAIL_TEMPLATE.format(mes=contestacao["mes"])

    def _enviar_email_operadora(self, contestacao):
        destinatarios = self._buscar_destinatarios(contestacao["operadora"])
        if not destinatarios:
            raise RuntimeError(f"Nenhum destinatario encontrado p/ operadora '{contestacao['operadora']}'")

        self._outlook.send_email_com_anexos(
            to=destinatarios,
            subject=self._montar_assunto(contestacao),
            body=self._montar_corpo(contestacao),
            attachments=[contestacao["caminho_carta"], contestacao["caminho_env"]],
        )

    # ------------------------------------------------------------------
    # TODO [NOVO]: gravar o resultado do envio (sucesso/falha) - mesma pendencia ja
    # registrada nos pacotes anteriores (tabela de log especifica da despesa).
    # Estrutura de log ja pronta (mesmo padrao do RPA_DETRAF_RECEITA, so mudando a tabela
    # em conexao.py) - descomentar quando a tabela tbl_rpa_log_detraf_despesa_contestacao
    # for criada/confirmada.
    # ------------------------------------------------------------------
    def _marcar_email_enviado(self, contestacao, sucesso: bool, erro: str = ""):
        print(f"[HU-15][TODO] gravar no banco: id={contestacao.get('id')} "
              f"sucesso={sucesso} erro={erro!r}")
        # if sucesso:
        #     self.db.log(processo="Finalizado", status="Sucesso",
        #                  descricao=f"{contestacao['operadora']}/{contestacao['mes']} - e-mail enviado")
        # else:
        #     self.db.log(processo="Finalizado", status="Erro",
        #                  descricao=f"{contestacao['operadora']}/{contestacao['mes']}: {erro}")


if "__main__" == __name__:
    Envio_Email_Contestacao().Fluxo_Envio_Email_Contestacao()
