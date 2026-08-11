import subprocess
import os
import time
import pyautogui
import pygetwindow as gw
import pandas as pd
import pyperclip
from pywinauto import Desktop
import psutil
from src.config.config import DIRETORIO_AGI,DIRETORIO_IMGS_AGI_CONFIG,USUARIO_AGI,SENHA_AGI,DIRETORIO_REMESSA_BAIXADA,AGI_JANELA_HOST
import easygui

diretorio_do_exe = os.path.dirname(DIRETORIO_AGI)

img_bnt_prod_ini = rf"{os.path.join(DIRETORIO_IMGS_AGI_CONFIG,"bnt_producao_ini.png")}"
img_windows_login = rf"{os.path.join(DIRETORIO_IMGS_AGI_CONFIG,"windows_login.png")}"
img_bnt_user = rf"{os.path.join(DIRETORIO_IMGS_AGI_CONFIG,"bnt_user.png")}"
img_bnt_entrar = rf"{os.path.join(DIRETORIO_IMGS_AGI_CONFIG,"bnt_entrar.png")}"
img_bnt_acessar_AGI = rf"{os.path.join(DIRETORIO_IMGS_AGI_CONFIG,"bnt_acessar_agi.png")}"

img_bnt_menu_relatorio = rf"{os.path.join(DIRETORIO_IMGS_AGI_CONFIG,"bnt_menu_relatorio.png")}"
img_bnt_submenu_detraf = rf"{os.path.join(DIRETORIO_IMGS_AGI_CONFIG,"bnt_submenu_detraf.png")}"
img_bnt_submenu_receita_despesas = rf"{os.path.join(DIRETORIO_IMGS_AGI_CONFIG,"bnt_submenu_receita_despesas.png")}"
img_bnt_filtro = rf"{os.path.join(DIRETORIO_IMGS_AGI_CONFIG,"bnt_filtro.png")}"
img_bnt_periodo_referencia = rf"{os.path.join(DIRETORIO_IMGS_AGI_CONFIG,"bnt_periodo_referencia.png")}"
img_drop_box_export = rf"{os.path.join(DIRETORIO_IMGS_AGI_CONFIG,"drop_box_export.png")}"
img_submenu_export_area_transferencia = rf"{os.path.join(DIRETORIO_IMGS_AGI_CONFIG,"submenu_export_area_transferencia.png")}"
img_submenu_export_para_csv = rf"{os.path.join(DIRETORIO_IMGS_AGI_CONFIG,"submenu_export_para_csv.png")}"
img_bnt_ok_export = rf"{os.path.join(DIRETORIO_IMGS_AGI_CONFIG,"bnt_ok_export.png")}"
img_bnt_filtrar = rf"{os.path.join(DIRETORIO_IMGS_AGI_CONFIG,"bnt_filtrar.png")}"
img_bnt_menu_sap = rf"{os.path.join(DIRETORIO_IMGS_AGI_CONFIG,"bnt_menu_sap.png")}"
img_bnt_submenu_gerenciamento = rf"{os.path.join(DIRETORIO_IMGS_AGI_CONFIG,"bnt_submenu_gerenciamento.png")}"

class AGI_CONFIG():

    def _click(self,img,tentativa=3,confidence = 0.8):
        target = None
        retentativa = 0
        while retentativa < tentativa:
            try:
                target = pyautogui.locateOnScreen(img, confidence=confidence)
                break
            except:
                time.sleep(1)
                retentativa += 1
        if target:
            pyautogui.click(target)
        else: return "Não encontrou a imagem"

    def _wait_appear(self,img,timeout=180,confidence = 0.8):
        
        target = ""
        count_time = 0 # Espera de 2min

        while count_time < timeout: 
            try:
                target = pyautogui.locateOnScreen(img, confidence=confidence) #Tentando encontrar a log da vivo
            except Exception as e:
                time.sleep(1)
                count_time += 1
                print(f"segundos de espera para {img}: {count_time}")
                # print(f"o Erro: {e}")

            #quando encontrar a tela de login
            if target: 
                break
            if  count_time == timeout: 
                return "Nao encontrado"

    def Inicializando_AGI(self):
        self.Fechar_AGI()
        try:
            # O segredo está no 'cwd' (current working directory)
            AGI = subprocess.Popen([DIRETORIO_AGI], cwd=diretorio_do_exe)
            print("Executado com sucesso!")

            # Loop para verificar se o programa "sobreviveu" à inicialização
            while True: # Tenta checar por 5 segundos
                # poll() retorna None se o processo ainda estiver rodando
                status = AGI.poll()
            
                if status is None:
                    print(f"O programa foi aberto corretamente: {status}")
                    break
                
                time.sleep(1)
        except subprocess.CalledProcessError as e:
            print(f"Erro persistente: {e}")

        time.sleep(2)

    def Verificando_janela_aberta(self,nome_janela):
                # 1. Capturar a janela específica
            while True:
                janela = gw.getWindowsWithTitle(nome_janela)
            
                if len(janela) > 0:
                    break
                time.sleep(1)

            janela_encontrada = janela[0]
            if not janela_encontrada.isActive:
                    janela_encontrada.restore()
                    time.sleep(1)

                    janela_encontrada.minimize()
                    time.sleep(0.5)

                    janela_encontrada.restore()
                    time.sleep(0.5)

                    janela_encontrada.activate()
                                    
                    janela_encontrada.maximize()


    def Fechar_AGI(self):
        for proc in psutil.process_iter(['name']):
            if 'adl.exe' in proc.info['name'].lower():
                
                print(proc)

                #Fechar o next caso ele esteja aberto
                try:

                    subprocess.run(["taskkill","/f","/im",f"{proc.info['name'].lower()}"])

                except:

                    pass

    def Acessando_producao_AGI(self):
        self.Verificando_janela_aberta(nome_janela='Portal Triad: Vivo')

        time.sleep(1)
        #clicando em "producao"
        # self._wait_appear(img=img_bnt_prod_ini)
        self._wait_appear(img=img_bnt_prod_ini,confidence=0.9)
        self._click(img=img_bnt_prod_ini,confidence=0.9)
        #clicando em "Acessar" de baixo da imagem AGI
        self._wait_appear(img_bnt_acessar_AGI,confidence=0.9)
        self._click(img_bnt_acessar_AGI,confidence=0.9)
        pyautogui.moveRel(0,75)
        pyautogui.click()

    def Login_AGI_producao(self):
        self.Verificando_janela_aberta(nome_janela='Portal Triad: Vivo - Produção')

        #Login - Usuario:
        self._wait_appear(img_windows_login)
        self._click(img_windows_login)
        self._wait_appear(img_bnt_user)
        self._click(img_bnt_user)
        # pyautogui.moveRel(175,15 )
        # pyautogui.click()
        pyautogui.typewrite(USUARIO_AGI)

        #Login - Senha:
        self._wait_appear(img_windows_login)
        self._click(img_windows_login)
        pyautogui.moveRel(175,50)
        pyautogui.click()
        pyautogui.typewrite(SENHA_AGI)

        self._click(img_bnt_entrar)

    def _Janela_salvar(self,diretorio,nome_janela):

        # Conecta ao dialogo de arquivo do AGI pelo titulo (title_re; o AGI traduz o titulo conforme o idioma da VM)
        app = Desktop(backend="win32").window(title_re=nome_janela)

        # Aguarda a janela ficar pronta
        app.wait('visible', timeout=220)

        # Digita o nome do arquivo no campo de edição 
        app.Edit.type_keys( diretorio, with_spaces=True)
        pyautogui.press("Enter")
        # app.Button.click() # Clica no botão Salvar


        # --- VALIDAR SE ARQUIVO JÁ EXISTENTE ---
        janela_confirmar = Desktop(backend="win32").window(title_re="Confirm Save As")

        # Verificamos se ela apareceu (esperamos até 2 segundos)
        if janela_confirmar.exists(timeout=2):
            print("Arquivo já existe, será substituido")
            # No Windows, o botão de confirmação geralmente tem o nome "Sim" ou o ID 'CommandButton 6'
            # janela_confirmar.child_window(title="Sim", control_type="Button").click()
            janela_confirmar.type_keys("%s")
            print("Parar")

    def _selecionar_periodo (self):
        pyautogui.click()

        passos = [
            ("down", 1),
            ("tab", 1),
            ("down", 1),
            ("tab",1)
        ]

        for key, qtd in passos:
            for _ in range(qtd):
                pyautogui.press(key)
        
        for _ in range(3):
            pyautogui.hotkey("Shift","TAB")
            
        pyautogui.press("SPACE")
        # easygui.msgbox("VErificar filtro")  # removido para execucao desassistida na VM

    # ------------------------------------------------------------------
    # NOVO (HU-21): alternativa ao typewrite para dropdowns do Portal AIR/Flex que so
    # aceitam 1 caractere por vez (digitar a string toda perde/sobrescreve caracteres -
    # confirmado na VM em 29/07). Em vez de digitar, desce opcao por opcao e LE o valor
    # atualmente selecionado via Ctrl+A/Ctrl+C + clipboard (pyperclip) ate bater com o
    # valor procurado. Nao da pra usar pywinauto/UI Automation aqui: o Portal AIR (Adobe
    # AIR/Flex) nao expoe esses campos como controles acessiveis - so os dialogos NATIVOS
    # do Windows (Save As) sao lidos via pywinauto (_Janela_salvar acima). OCR (pytesseract)
    # tambem nao esta instalado no projeto - por isso a leitura via clipboard.
    #
    # PRESSUPOE que o campo ja esta em foco (clique antes de chamar) e que mover a selecao
    # com as setas atualiza o texto exibido no campo (sem precisar abrir a lista) - PRECISA
    # CONFIRMAR NA VM se e assim mesmo.
    # ------------------------------------------------------------------
    def _ler_valor_dropdown(self):
        """Le o texto atualmente exibido no campo em foco via Ctrl+A/Ctrl+C + clipboard."""
        # Garante que a janela do Portal Triad esta em foco antes de mandar os hotkeys -
        # sem isso, Ctrl+A/Ctrl+C podem ir pra outra janela ativa (ex.: o VSCode/editor),
        # copiando codigo em vez do valor do campo (ja aconteceu em teste na VM 29/07).
        self.Verificando_janela_aberta(nome_janela='Portal Triad: Vivo - Produção')
        pyautogui.hotkey("ctrl", "a")
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.15)
        return pyperclip.paste().strip()

    def _selecionar_dropdown_por_valor(self, valor_alvo, max_tentativas=60, direcao="down", extrair=None):
        """
        extrair: funcao opcional aplicada ao texto lido antes de comparar - ex.: para um
        dropdown no formato "EOT-NOME" (ex.: "020-TELERJ CELLULAR"), passar
        extrair=lambda t: t.split("-", 1)[0].strip() pra comparar so o EOT.
        """
        valor_alvo = str(valor_alvo).strip()
        for _ in range(max_tentativas):
            atual = self._ler_valor_dropdown()
            comparavel = extrair(atual) if extrair else atual
            if comparavel == valor_alvo:
                return True
            pyautogui.press(direcao)
            time.sleep(0.15)
        raise ValueError(
            f"_selecionar_dropdown_por_valor: valor '{valor_alvo}' nao encontrado "
            f"apos {max_tentativas} tentativas (ultimo valor lido: '{atual}')."
        )

    def Baixar_Remessa(self):
        while True:
            self._wait_appear(img_bnt_menu_relatorio,timeout=30)
            self._click(img_bnt_menu_relatorio)
            pyautogui.moveRel(0,70)
            self._wait_appear(img_bnt_submenu_detraf,15)
            sub_menu = self._click(img_bnt_submenu_detraf)
            print(sub_menu)
            if sub_menu != "Não encontrou a imagem":
                print(f"Entrou no if com o sub_menu como : {sub_menu}")
                break

        self._wait_appear(img_bnt_submenu_receita_despesas,timeout=30)
        self._click(img_bnt_submenu_receita_despesas)

        
        self._wait_appear(img_bnt_filtro)
        time.sleep(1)
        self._click(img_bnt_filtro)

        
        self._wait_appear(img_bnt_periodo_referencia)
        self._click(img_bnt_periodo_referencia)
        pyautogui.moveRel(10,0)
        self._selecionar_periodo()
        
    
        while True:
            self._wait_appear(img_drop_box_export,timeout=10)
            self._click(img_drop_box_export)
            time.sleep(2)
            pyautogui.moveRel(0,-20)
            sub_menu = self._click(img_submenu_export_para_csv)
            print(sub_menu)
            if sub_menu != "Não encontrou a imagem":
                    break
        # VM em ingles: o app AGI traduz o titulo do dialogo -> f"Select location for download by {host}".
        # (era f"Selecionar local para download de {AGI_JANELA_HOST}"). AGI_JANELA_HOST deve ser o host de PRODUCAO da VM.
        self._Janela_salvar(diretorio=os.path.join(DIRETORIO_REMESSA_BAIXADA,"remessa_baixada.csv"),nome_janela=f"Select location for download by {AGI_JANELA_HOST}")
        # self.AGI_CONFIG._wait_appear(img_bnt_ok_export,timeout=300)

        #Ajustando o csv caso ele venha com o aspas faltante
        linhas_corrigidas = []
        with open(os.path.join(DIRETORIO_REMESSA_BAIXADA,"remessa_baixada.csv"), "r", encoding="utf-8") as f:

            for linha in f:

                # linha suspeita de aspas quebradas
                if linha.count('"') % 2 != 0:
                    print(linha)
                    linha = linha.replace('"', '')

                linhas_corrigidas.append(linha)
        time.sleep(1)
        f.close()
        with open(os.path.join(DIRETORIO_REMESSA_BAIXADA,"remessa_baixada.csv"), "w", encoding="utf-8") as f:
            f.writelines(linhas_corrigidas)


