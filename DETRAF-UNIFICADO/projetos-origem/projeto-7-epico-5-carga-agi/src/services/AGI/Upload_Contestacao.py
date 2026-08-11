import os
import time
from datetime import datetime
import pyautogui

from src.config.config import (
    DIRETORIO_IMGS_UPLOAD_CONTESTACAO, DIRETORIO_PASTA_CONTESTACAO,
    DIRETORIO_EVIDENCIAS, AGI_JANELA_HOST, PERMITIR_UPLOAD_AGI, CONFIG_WEBFAT,
)

from src.services.AGI.AGI_config import AGI_CONFIG

"""
HU-18 - Upload do arquivo de contestacao no AGI (Contestação > Gerenciar)
==========================================================================
NAO EXISTE NENHUM EQUIVALENTE PRONTO NO EXEMPLO RPA_DETRAF_RECEITA.
A tela "Contestação > Gerenciar" nunca foi automatizada no fluxo de Receita
(o modulo Criacao_Remessa.py trata da tela de Remessa/SAP, que e outra coisa).

Este arquivo foi montado seguindo o PADRAO DE CODIGO mais parecido que existe no
exemplo: Upload_planliha_erro_DI_DE.py (classe Tratativa_Erro), que faz exatamente
o formato que a HU-18 precisa -> navega ATE A TELA uma unica vez, depois repete
em loop "carregar arquivo -> selecionar -> confirmar" para cada arquivo, sem
refazer a navegacao do menu a cada upload.

TUDO abaixo e ESQUELETO/TODO: os nomes de metodo e a estrutura de classe seguem o
padrao do projeto, mas a logica de clique (imagens, tempos de espera, nome exato
do dialogo) ainda precisa ser implementada e testada na VM.

IMAGENS QUE FALTAM CAPTURAR (nenhuma existe ainda - ver MANIFESTO_IMAGENS.md em
src/view/imagens/AGI_Upload_Contestacao/):
    - bnt_contestacao.png              (item de menu "Contestação")
    - bnt_submenu_gerenciar.png        (submenu "Gerenciar")
    - bnt_upload_contestacao.png       (botao "Upload" dentro da tela de Gerenciar)
    - bnt_salvar_contestacao.png       (botao "Salvar" apos o AGI carregar as informacoes -
      To Be MVP2 paragrafo 322: "O AGI carrega as informações e o robô clica em Salvar na tela")
"""


class Upload_Contestacao:

    def __init__(self):
        self.AGI_CONFIG = AGI_CONFIG()
        
    # ------------------------------------------------------------------
    # Fluxo principal - esqueleto seguindo o padrao Fluxo_Tratativa_Erro do exemplo:
    # so abre o AGI se houver arquivo pendente, respeita o kill-switch, navega 1x e
    # sobe tudo em sequencia reaproveitando a mesma tela.
    # ------------------------------------------------------------------
    def Fluxo_Upload_Contestacao(self):
        pendencias = self._listar_arquivos_contestacao()
        if not pendencias:
            print("[UPLOAD CONTESTACAO] Nenhum CONT_PROC_MASCARA pendente; nada a fazer.")
            return

        if not PERMITIR_UPLOAD_AGI:
            print(f"[MODO SEGURO] Upload no AGI desabilitado (PERMITIR_UPLOAD_AGI=False); "
                  f"{len(pendencias)} arquivo(s) de contestacao pendente(s), nada enviado.")
            return

        self.AGI_CONFIG.Fechar_AGI()
        self.AGI_CONFIG.Inicializando_AGI()
        self.AGI_CONFIG.Acessando_producao_AGI()
        self.AGI_CONFIG.Login_AGI_producao()

        # TODO: so faz sentido chamar isto DEPOIS que as imagens abaixo existirem
        self._navegar_contestacao_gerenciar()

        for caminho in pendencias:
            arquivo = os.path.basename(caminho)
            try:
                self._upload_um_arquivo_contestacao(caminho)
                self._capturar_evidencia_sucesso(arquivo)
               
                print(f"[UPLOAD CONTESTACAO][OK] {arquivo}")
            except Exception as e:
                print(f"[UPLOAD CONTESTACAO][FALHA] {arquivo}: {e}")
            time.sleep(1)

        self.AGI_CONFIG.Fechar_AGI()

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    def _listar_arquivos_contestacao(self):
        if not DIRETORIO_PASTA_CONTESTACAO or not os.path.isdir(DIRETORIO_PASTA_CONTESTACAO):
            return []
        return [
            os.path.join(DIRETORIO_PASTA_CONTESTACAO, f)
            for f in sorted(os.listdir(DIRETORIO_PASTA_CONTESTACAO))
            if os.path.isfile(os.path.join(DIRETORIO_PASTA_CONTESTACAO, f))
        ]


    # ------------------------------------------------------------------
    # TODO [NOVO - imagens nao existem ainda]: navegar Contestação > Gerenciar.
    # Estrutura copiada do padrao _navegar_base_rateio (Tratativa_Erro.py) e
    # _importar_dados (Upload_DI_DE.py) - so trocar as imagens quando forem capturadas.
    # ------------------------------------------------------------------
    def _navegar_contestacao_gerenciar(self):
        img_bnt_contestacao = os.path.join(DIRETORIO_IMGS_UPLOAD_CONTESTACAO, "bnt_contestacao.png")
        img_bnt_submenu_gerenciar = os.path.join(DIRETORIO_IMGS_UPLOAD_CONTESTACAO, "bnt_submenu_gerenciar.png")

        while True:
            self.AGI_CONFIG._wait_appear(img_bnt_contestacao, timeout=30)
            self.AGI_CONFIG._click(img_bnt_contestacao)
            pyautogui.moveRel(0, 70)
            self.AGI_CONFIG._wait_appear(img_bnt_submenu_gerenciar, 15)
            sub_menu = self.AGI_CONFIG._click(img_bnt_submenu_gerenciar)
            if sub_menu != "Não encontrou a imagem":
                break

    # ------------------------------------------------------------------
    # TODO [NOVO - imagens nao existem ainda]: subir 1 arquivo de contestacao e, ao final,
    # clicar em "Salvar" (diferente do fluxo de Detraf/Importar, que nao tem esse passo extra -
    # ver To Be MVP2 paragrafo 322).
    # ------------------------------------------------------------------
    def _upload_um_arquivo_contestacao(self, caminho_arquivo):
        img_bnt_upload_contestacao = os.path.join(DIRETORIO_IMGS_UPLOAD_CONTESTACAO, "bnt_upload_contestacao.png")
        img_bnt_salvar_contestacao = os.path.join(DIRETORIO_IMGS_UPLOAD_CONTESTACAO, "bnt_salvar_contestacao.png")

        if self.AGI_CONFIG._wait_appear(img_bnt_upload_contestacao, timeout=40) == "Nao encontrado":
            raise RuntimeError(f"botao upload (contestacao) nao apareceu p/ {os.path.basename(caminho_arquivo)}")
        self.AGI_CONFIG._click(img_bnt_upload_contestacao)

        # TODO: confirmar o texto exato do dialogo nativo na VM (padrao observado no exemplo:
        # "Select file for upload by {host}", mas nunca validado nesta tela especifica)
        self.AGI_CONFIG._Janela_salvar(diretorio=caminho_arquivo, nome_janela=rf"(Select location for download by|Selecionar local para download de) {AGI_JANELA_HOST}")
        # Passo extra que so existe na Contestacao (nao existe no Detraf/Importar):
        if self.AGI_CONFIG._wait_appear(img_bnt_salvar_contestacao, timeout=60) == "Nao encontrado":
            raise RuntimeError(f"botao Salvar nao apareceu apos upload de {os.path.basename(caminho_arquivo)}")
        self.AGI_CONFIG._click(img_bnt_salvar_contestacao)

    # ------------------------------------------------------------------
    # TODO [NOVO]: mesma necessidade da HU-17 - nao existe rotina de evidencia de sucesso
    # no exemplo. Reaproveitar a mesma implementacao usada em Upload_Detraf_EXT_INT.py.
    # ------------------------------------------------------------------
    def _capturar_evidencia_sucesso(self, nome_arquivo_origem):
        if not DIRETORIO_EVIDENCIAS:
            return
        os.makedirs(DIRETORIO_EVIDENCIAS, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        caminho = os.path.join(DIRETORIO_EVIDENCIAS, f"evidencia_contestacao_{nome_arquivo_origem}_{timestamp}.png")
        # TODO: pyautogui.screenshot().save(caminho)  -- ainda nao implementado, so o esqueleto
        print(f"[EVIDENCIA][TODO] implementar screenshot em: {caminho}")


if "__main__" == __name__:
    Upload_Contestacao().Fluxo_Upload_Contestacao()
