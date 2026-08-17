import os
import time
import pyautogui
from datetime import datetime
import numpy as np

from src.config.config import (
    DIRETORIO_IMGS_UPLOAD_DETRAF, DIRETORIO_EXPORT_ERRO, DIRETORIO_PASTA_EXT,
    DIRETORIO_PASTA_INT, AGI_JANELA_HOST, PERIODO_REF, DIRETORIO_TEMP,
    DIRETORIO_EVIDENCIAS, CONFIG_WEBFAT, PERMITIR_UPLOAD_AGI,
)
from src.services.AGI.AGI_config import AGI_CONFIG
# from src.config.conexao import Banco

"""
HU-17 - Upload dos arquivos EXT/INT no AGI (Detraf > Importar Dados)
=====================================================================
Adaptado de src/services/AGI/Upload_DI_DE.py do exemplo RPA_DETRAF_RECEITA.

O QUE FOI REAPROVEITADO DO EXEMPLO (sem alteracao de logica):
    - Navegacao Detraf > Importar Dados (padrao de retry-loop com wait_appear/click)
    - Upload de 1 arquivo por vez (_upload_um_arquivo): clicar Upload -> _Janela_salvar
    - Loop de percorrer a pasta e subir cada arquivo com try/except marcando sucesso/falha
    - Deteccao de linha vermelha de erro pos-upload (_detectar_linhas_vermelhas, _captura_erro)
      -> ATENCAO: isto so foi validado na tela de Receita. Confirmar na VM se a tela de
      Despesa mostra erro do mesmo jeito (grid + linha vermelha) antes de confiar nisso.

O QUE PRECISA SER FEITO/AJUSTADO AQUI (todos os TODO abaixo):
    1. Regra de cenario (EXT sempre, INT so em contestacao COM retencao) - NAO existe no
       exemplo, la ele sobe cegamente tudo que esta na pasta.
    2. Ordem "um de cada vez, EXT depois INT" por operadora (To Be MVP2 paragrafo 313).
    3. Evidencia de sucesso (print automatico) - requisito novo do To Be (item 4.7.3),
       nao existe rotina equivalente no exemplo (so existe captura de ERRO, nao de sucesso).
    4. Gravar o resultado do upload nas tabelas novas de log da Despesa (ver README).
"""

# TODO: confirmar se estas imagens (copiadas do exemplo de Receita) realmente batem com a
# tela de Despesa antes de rodar em producao - o menu "Detraf > Importar Dados" deveria ser
# o mesmo aplicativo AGI, mas resolucao/tema da VM podem mudar o resultado do match.
img_bnt_detraf = os.path.join(DIRETORIO_IMGS_UPLOAD_DETRAF, "bnt_detraf.png")
img_bnt_submenu_importar_dados = os.path.join(DIRETORIO_IMGS_UPLOAD_DETRAF, "bnt_submenu_importar_dados.png")
img_bnt_upload = os.path.join(DIRETORIO_IMGS_UPLOAD_DETRAF, "bnt_upload.png")
img_tab_regs_Erro = os.path.join(DIRETORIO_IMGS_UPLOAD_DETRAF, "tab_regs_Erro.png")
img_tab_regs_Erro_bgd_white = os.path.join(DIRETORIO_IMGS_UPLOAD_DETRAF, "tab_regs_Erro_bgd_white.png")
img_bnt_export_erro = os.path.join(DIRETORIO_IMGS_UPLOAD_DETRAF, "bnt_export_erro.png")
img_bnt_voltar = os.path.join(DIRETORIO_IMGS_UPLOAD_DETRAF, "bnt_voltar.png")
img_row_scroll = os.path.join(DIRETORIO_IMGS_UPLOAD_DETRAF, "row_scroll.png")
img_row_scroll_up = os.path.join(DIRETORIO_IMGS_UPLOAD_DETRAF, "row_scroll_up.png")

REGION = (20, 241, 1880, 740)  # REAPROVEITADO do exemplo - conferir se a grid fica na mesma area de tela


class Upload_Detraf_EXT_INT:

    def __init__(self):
        self.AGI_CONFIG = AGI_CONFIG()
        #self.db = Banco(CONFIG_WEBFAT)

    # ------------------------------------------------------------------
    # Fluxo principal - REAPROVEITADO (estrutura identica ao Fluxo_Upload_DI_DE do exemplo)
    # ------------------------------------------------------------------
    def Fluxo_Upload_Detraf(self):
        pendencias = self._montar_lista_upload()
        if not pendencias:
            print("[UPLOAD DETRAF] Nada pendente em EXT/INT; nada a fazer.")
            return

        if not PERMITIR_UPLOAD_AGI:
            print(f"[MODO SEGURO] Upload no AGI desabilitado (PERMITIR_UPLOAD_AGI=False); "
                  f"{len(pendencias)} arquivo(s) pendente(s), nada enviado.")
            return

        self.AGI_CONFIG.Fechar_AGI()
        self.AGI_CONFIG.Inicializando_AGI()
        self.AGI_CONFIG.Acessando_producao_AGI()
        self.AGI_CONFIG.Login_AGI_producao()
        self._navegar_importar_dados()
        self._subir_pendencias(pendencias)
        self.AGI_CONFIG.Fechar_AGI()

    # ------------------------------------------------------------------
    # TODO [NOVO - regra de negocio]: montar a lista de upload respeitando o cenario.
    #   - Ler o(s) arquivo(s) EXT de DIRETORIO_PASTA_EXT (sempre existe, todo cenario).
    #   - Ler o(s) arquivo(s) INT de DIRETORIO_PASTA_INT (SO existe quando o cenario for
    #     "contestacao COM retencao" - conferir manifest/])sinalizacao vinda do Epico 4).
    #   - Retornar pares (operadora, [EXT, INT ou so EXT]) na ORDEM em que devem subir:
    #     "um de cada vez" e por operadora (To Be MVP2 paragrafo 313).
    #   No exemplo de Receita (Upload_DI_DE._consolidar_arquivos) essa etapa monta lotes de
    #   ate 17.900 linhas a partir de varios CSVs brutos - aqui provavelmente NAO se aplica,
    #   pois o Epico 4 ja deve entregar 1 arquivo EXT (+ opcional 1 INT) pronto por operadora.
    #   CONFIRMAR isso com quem esta desenvolvendo o Epico 4 antes de finalizar este metodo.
    # ------------------------------------------------------------------
    def _montar_lista_upload(self):
        pendencias = []
        
        # Processa a pasta externa
        if DIRETORIO_PASTA_EXT and os.path.isdir(DIRETORIO_PASTA_EXT):
            for arquivo in sorted(os.listdir(DIRETORIO_PASTA_EXT)):
                caminho_completo = os.path.join(DIRETORIO_PASTA_EXT, arquivo)
                if os.path.isfile(caminho_completo):
                    pendencias.append(caminho_completo)
                    
        # Processa a pasta interna
        if DIRETORIO_PASTA_INT and os.path.isdir(DIRETORIO_PASTA_INT):
            for arquivo in sorted(os.listdir(DIRETORIO_PASTA_INT)):
                caminho_completo = os.path.join(DIRETORIO_PASTA_INT, arquivo)
                if os.path.isfile(caminho_completo):
                    pendencias.append(caminho_completo)
                    
        return pendencias


    # ------------------------------------------------------------------
    # Navegacao Detraf > Importar Dados - REAPROVEITADO (mesmo padrao de retry-loop do exemplo)
    # ------------------------------------------------------------------
    def _navegar_importar_dados(self):
        while True:
            if self.AGI_CONFIG._wait_appear(img_bnt_detraf, timeout=130) == "Nao encontrado":
                print("[NAVEGAR] bnt_detraf nao apareceu, tentando novamente...")
                continue

            if self.AGI_CONFIG._click(img_bnt_detraf) == "Não encontrou a imagem":
                print("[NAVEGAR] falha ao clicar em bnt_detraf, tentando novamente...")
                continue

            pyautogui.moveRel(0, 70)

            if self.AGI_CONFIG._wait_appear(img_bnt_submenu_importar_dados, timeout=15) == "Nao encontrado":
                print("[NAVEGAR] submenu_importar_dados nao apareceu, clicando em bnt_detraf novamente...")
                continue

            sub_menu = self.AGI_CONFIG._click(img_bnt_submenu_importar_dados)
            if sub_menu != "Não encontrou a imagem":
                break

    # ------------------------------------------------------------------
    # Upload de 1 arquivo - REAPROVEITADO (identico ao _upload_um_arquivo do exemplo)
    # ------------------------------------------------------------------
    def _upload_um_arquivo(self, caminho_arquivo):
        if self.AGI_CONFIG._wait_appear(img_bnt_upload, timeout=40) == "Nao encontrado":
            raise RuntimeError(f"botao upload nao apareceu p/ {os.path.basename(caminho_arquivo)}")
        if self.AGI_CONFIG._click(img_bnt_upload) == "Não encontrou a imagem":
            raise RuntimeError(f"falha ao clicar em upload p/ {os.path.basename(caminho_arquivo)}")
        self.AGI_CONFIG._Janela_salvar(diretorio=caminho_arquivo, nome_janela=f"(Select location for download by|Selecionar local para download de) {AGI_JANELA_HOST}")
        

    def _subir_pendencias(self, pendencias):
        for caminho in pendencias:
            arquivo = os.path.basename(caminho)
            # Estrutura de log ja pronta (mesmo padrao do RPA_DETRAF_RECEITA, so mudando a
            # tabela em conexao.py) - descomentar quando tbl_rpa_log_detraf_despesa_arquivos
            # for criada/confirmada.
            # self.db.log(processo="Iniciado", status="Sucesso", descricao=f"Upload {arquivo}")
            try:
                self._upload_um_arquivo(caminho)
                # TODO [NOVO]: chamar aqui a captura de evidencia de sucesso (ver metodo abaixo)
                self._capturar_evidencia_sucesso(arquivo)
                print(f"[UPLOAD][OK] {arquivo}")
                # self.db.log(processo="Finalizado", status="Sucesso", descricao=f"Upload {arquivo}")
            except Exception as e:
                print(f"[UPLOAD][FALHA] {arquivo}: {e}")
                # self.db.log(processo="Finalizado", status="Erro", descricao=f"Upload {arquivo}: {e}")
            time.sleep(1)

    # ------------------------------------------------------------------
    # TODO [NOVO - nao existe no exemplo]: capturar print de tela como evidencia do upload
    # bem-sucedido (To Be MVP2, item 4.7.3 "Captura de mensagens de sucesso / Print automático").
    # O exemplo so tem captura de ERRO (linha vermelha), nunca captura de SUCESSO.
    # Sugestao de implementacao: pyautogui.screenshot() logo apos o _Janela_salvar confirmar,
    # salvando em DIRETORIO_EVIDENCIAS com nome rastreavel (operadora + timestamp).
    # ------------------------------------------------------------------
    def _capturar_evidencia_sucesso(self, nome_arquivo_origem):
        if not DIRETORIO_EVIDENCIAS:
            return
        os.makedirs(DIRETORIO_EVIDENCIAS, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        caminho = os.path.join(DIRETORIO_EVIDENCIAS, f"evidencia_{nome_arquivo_origem}_{timestamp}.png")
        # TODO: pyautogui.screenshot().save(caminho)  -- ainda nao implementado, so o esqueleto
        print(f"[EVIDENCIA][TODO] implementar screenshot em: {caminho}")

    # ------------------------------------------------------------------
    # Deteccao/tratamento de erro pos-upload - ADAPTADO do exemplo (_detectar_linhas_vermelhas,
    # _baixar_erro, _erro_na_linha, _captura_erro do Upload_DI_DE.py).
    # TODO: validar na VM se a tela de Despesa realmente marca erro com linha vermelha igual
    # a tela de Receita antes de confiar nesta parte - copiada como referencia, nao testada
    # no contexto de Despesa.
    # ------------------------------------------------------------------
    def _detectar_linhas_vermelhas(self):
        screenshot = pyautogui.screenshot(region=REGION)
        img = np.array(screenshot)
        r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]
        mask = (r > 180) & (g < 130) & (b < 130)
        red_pixels_por_linha = mask.sum(axis=1)
        linhas_indices = np.where(red_pixels_por_linha > 50)[0]
        linhas_unicas, ultimo_y = [], -100
        for y in linhas_indices:
            if y - ultimo_y > 10:
                linhas_unicas.append(y)
                ultimo_y = y
        return [(REGION[0] + REGION[2] // 2, REGION[1] + y) for y in linhas_unicas]
