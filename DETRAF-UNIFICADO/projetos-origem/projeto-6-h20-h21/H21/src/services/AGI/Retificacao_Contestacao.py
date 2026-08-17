import os
import time
import pyautogui
import pandas as pd
from pywinauto.application import Application
from pywinauto import Desktop

from src.config.config import (
    DIRETORIO_IMGS_CONTESTACAO_GERENCIAR, DIRETORIO_IMGS_AGI_CONFIG,
    AGI_JANELA_HOST, PERIODO_REF, PERMITIR_ACAO_AGI, CONFIG_WEBFAT, DIRETORIO_TEMP,
)
from src.config.conexao import Banco
from src.services.AGI.AGI_config import AGI_CONFIG

# CONFIRMADO em 03/08 (reuniao com cliente): a estrategia de achar o processo certo NAO
# e mais selecionar a operadora no dropdown do Filtro (ver toda a investigacao com
# pywinauto/UIA/OCR - dropdown nao e acessivel de jeito nenhum). O caminho real e:
#   1) Filtrar so por periodo (estreita o resultado).
#   2) Exportar a grid pra CSV.
#   3) No CSV, achar a linha certa cruzando EOT + Periodo Referencia + Periodo Trafego +
#      Valor, e pegar o "ID Processo" dela.
#   4) Digitar esse ID Processo no campo "Numero Processo" (topo da tela) e Pesquisar -
#      isso retorna 1 unica linha, sem precisar mexer no dropdown de operadora.
#   5) Validar que "Processo Selecionado: <id>" aparece certo antes de Adicionar (ponto
#      critico reforcado pela cliente - sem isso, o evento pode ser lancado no lugar errado).
NOME_JANELA_AGI = "Portal Triad: Vivo - Produção: "

"""
HU-21 - Identificacao de trafego recuperado e retificacao no AGI (evento "Recuperacao")
=========================================================================================
NAO EXISTE NENHUM EQUIVALENTE NO EXEMPLO RPA_DETRAF_RECEITA. Tudo aqui e esqueleto novo,
construido reaproveitando PADROES de codigo (nao codigo pronto) do projeto:

    - Login/abertura do AGI: 100% igual ao resto do projeto (AGI_config).
    - Navegacao ate "Contestação > Gerenciar": MESMA tela usada na HU-18 (Epico 5,
      Upload_Contestacao.py) - se aquela HU capturar as imagens de menu primeiro
      (bnt_contestacao.png / bnt_submenu_gerenciar.png), sao as MESMAS imagens aqui, so
      copiar para DIRETORIO_IMGS_CONTESTACAO_GERENCIAR. Evita capturar 2x a mesma tela.
    - Selecao de opcao em dropdown (campo "Tipo Evento" = "Recuperacao"): o exemplo tem um
      padrao parecido em AGI_config._selecionar_periodo() (clica no campo e navega com
      down/tab/shift-tab/space no teclado, sem usar imagem para cada opcao do dropdown).
      A ideia e a mesma aqui, mas a sequencia exata de teclas precisa ser calibrada nesta
      tela especifica - nao e um copy-paste direto.
    - Preenchimento de campo de texto (Duracao, Valor Liquido, etc.): mesmo padrao de
      pyautogui.typewrite(...) usado em AGI_config.Login_AGI_producao() pra usuario/senha.

IMAGENS QUE FALTAM CAPTURAR - ver MANIFESTO_IMAGENS.md em
src/view/imagens/AGI_Contestacao_Gerenciar/ (6 imagens NOVAS, alem das 2 compartilhadas
com a HU-18).
"""


class Retificacao_Contestacao:

    def __init__(self):
        self.AGI_CONFIG = AGI_CONFIG()
        self.db = Banco(CONFIG_WEBFAT)

    # ------------------------------------------------------------------
    # Fluxo principal
    # ------------------------------------------------------------------
    def Fluxo_Retificacao_Recuperacao(self):
        recuperacoes = self._identificar_trafego_recuperado()
        if not recuperacoes:
            print("[HU-21] Nenhum trafego recuperado identificado neste ciclo.")
            return

        if not PERMITIR_ACAO_AGI:
            print(f"[MODO SEGURO] Acao no AGI desabilitada (PERMITIR_ACAO_AGI=False); "
                  f"{len(recuperacoes)} retificacao(oes) calculada(s), nada gravado no AGI.")
            for r in recuperacoes:
                print(f"  - {r}")
            return

        self.AGI_CONFIG.Fechar_AGI()
        self.AGI_CONFIG.Inicializando_AGI()
        self.AGI_CONFIG.Acessando_producao_AGI()
        self.AGI_CONFIG.Login_AGI_producao()
        self._navegar_contestacao_gerenciar()  # MESMA tela da HU-18 (Epico 5)

        for recuperacao in recuperacoes:
            # Estrutura de log ja pronta (mesmo padrao do RPA_DETRAF_RECEITA, so mudando a
            # tabela em conexao.py) - descomentar quando tbl_rpa_log_detraf_despesa_retificacao
            # for criada/confirmada.
            # self.db.log(processo="Iniciado", status="Sucesso",
            #             descricao=f"{recuperacao['operadora']}/{recuperacao['periodo']}")
            try:
                self._retificar_um_processo(recuperacao)
                self.db.marcar_carga_agi(recuperacao["id"])
                print(f"[HU-21][OK] {recuperacao['operadora']} / {recuperacao['periodo']}")
                # self.db.log(processo="Finalizado", status="Sucesso",
                #             descricao=f"{recuperacao['operadora']}/{recuperacao['periodo']}")
            except Exception as e:
                print(f"[HU-21][FALHA] {recuperacao['operadora']} / {recuperacao['periodo']}: {e}")
                # self.db.log(processo="Finalizado", status="Erro",
                #             descricao=f"{recuperacao['operadora']}/{recuperacao['periodo']}: {e}")
            time.sleep(1)

        self.AGI_CONFIG.Fechar_AGI()

    # ------------------------------------------------------------------
    # Identifica trafego recuperado consultando tbl_rpa_log_detraf_despesa_contestacao
    # (WebFat) - tabela confirmada em 29/07 via DESCRIBE na VM: guarda a comparacao
    # Vivo x Operadora (mesma estrutura do print do As Is 4.2.8.6.1) com colunas
    # eot_tbra/eot_operadora, referencia/trafego, minutos_tbra+vb_tbra (Vivo),
    # minutos_operadora+vb_operadora, minutos_diferenca+vb_diferenca,
    # minutos_variacao_perc+vb_variacao_perc, e carga_agi (flag de controle).
    #
    # O "id" (PK desta tabela) e devolvido no dict e usado depois em
    # self.db.marcar_carga_agi(id) para fechar o ciclo (carga_agi='carregado') apos
    # retificar com sucesso - evita reprocessar a mesma linha no proximo ciclo.
    # NAO confundir com o "id_processo" do AGI (numero da linha na grid de Contestacao),
    # que e outra coisa e continua sem resposta (TODO em _retificar_um_processo, passo 2).
    #
    # TODO [CONFIRMAR COM NEGOCIO - so 1 linha de teste na tabela ate agora, sem dado
    # real pra validar]:
    #   - Qual variacao define "recuperacao": vb_variacao_perc, minutos_variacao_perc,
    #     ou as duas? Hoje filtrando so por vb_variacao_perc < 0.
    #   - Valores de carga_agi alem de 'nao carregado' (ex.: 'carregado'/'erro'?) -
    #     assumindo que != 'carregado' = ainda nao retificado no AGI.
    # ------------------------------------------------------------------
    @staticmethod
    def _mes_anterior(periodo):
        """Formato YYYYMM -> mes anterior, tambem em YYYYMM (sem depender de libs externas)."""
        ano, mes = int(str(periodo)[:4]), int(str(periodo)[4:6])
        mes -= 1
        if mes == 0:
            mes, ano = 12, ano - 1
        return f"{ano:04d}{mes:02d}"

    def _identificar_trafego_recuperado(self):
        # "referencia" na tabela e o periodo da contestacao ORIGINAL (mes anterior a
        # PERIODO_REF) - a recuperacao e identificada no mes seguinte aquela contestacao,
        # entao o filtro compara com o mes anterior, nao com PERIODO_REF direto.
        periodo_contestacao_original = self._mes_anterior(PERIODO_REF)
        sql = (
            "SELECT id, empresa, eot_operadora, referencia, trafego, minutos_diferenca, vb_diferenca "
            "FROM tbl_rpa_log_detraf_despesa_contestacao "
            "WHERE referencia = %s AND carga_agi != 'carregado' AND vb_variacao_perc < 0"
        )
        linhas = self.db.selecionar_dados(sql, params=(periodo_contestacao_original,))

        return [
            {
                "id": linha["id"],
                "operadora": linha["empresa"],
                # CONFIRMADO em reuniao com cliente (03/08): pra achar o processo certo no
                # CSV exportado, precisa cruzar EOT + Periodo Referencia + Periodo Trafego +
                # Valor - por isso eot_operadora e periodo_trafego sao devolvidos aqui.
                "eot_operadora": linha["eot_operadora"],
                "periodo": linha["referencia"],
                "periodo_trafego": linha["trafego"],
                "minutos": abs(float(linha["minutos_diferenca"])),
                "valor_bruto": abs(float(linha["vb_diferenca"])),
            }
            for linha in linhas
        ]

    # ------------------------------------------------------------------
    # ATUALIZADO com base nos prints reais do As Is (docx enviado em 22/07): o menu
    # Contestação abre um submenu com 3 opções (Gerenciar / Análise de Contestação /
    # Risco Contestação) - imagens capturadas a partir do print e ja incluidas em
    # src/view/imagens/AGI_Contestacao_Gerenciar/. MESMAS imagens usadas na HU-18.
    # ------------------------------------------------------------------
    def _navegar_contestacao_gerenciar(self):
        img_bnt_contestacao = os.path.join(DIRETORIO_IMGS_CONTESTACAO_GERENCIAR, "bnt_contestacao.png")
        img_bnt_submenu_gerenciar = os.path.join(DIRETORIO_IMGS_CONTESTACAO_GERENCIAR, "bnt_submenu_gerenciar.png")
        while True:
            self.AGI_CONFIG._wait_appear(img_bnt_contestacao, timeout=30)
            self.AGI_CONFIG._click(img_bnt_contestacao)
            pyautogui.moveRel(0, 70)
            self.AGI_CONFIG._wait_appear(img_bnt_submenu_gerenciar, 15)
            sub_menu = self.AGI_CONFIG._click(img_bnt_submenu_gerenciar)
            if sub_menu != "Não encontrou a imagem":
                break

    # ------------------------------------------------------------------
    # ATUALIZADO com base nos prints reais do As Is. Tela real "Contestação > Gerenciar":
    #   - Botão "Filtro" (reaproveita bnt_filtro.png, ja copiado em AGI_CONFIG) abre um
    #     modal "Filtro de Registros" com dropdowns: Periodo Referencia, Periodo Trafego,
    #     Grupo Oper. Prest., Nat. Operacao, Operadoras Vivo, Operadora Prestadora, etc.
    #     Os campos usados aqui (campo_periodo.png = Periodo Referencia, campo_empresa.png
    #     = Operadora Prestadora) e o botao "Filtrar" (bnt_buscar_contestacao.png) ja
    #     foram capturados a partir do print.
    #   - O resultado aparece numa grid a esquerda (colunas: ID Processo, Data Processo,
    #     Ope. JV, Ope. Prest., Per. Ref., Per. Traf., Nat. Oper.). Ao clicar numa linha,
    #     abre o painel "Eventos do Processo de Contestação" a direita, com botao
    #     "+ Adicionar" (bnt_mais_adicionar.png) que cria uma linha nova editavel com as
    #     colunas: Tipo Evento, Data Evento, Data Vencimento, Data Pagamento Rec.,
    #     Data Envio Cont., Observação, Duração, Valor Liquido, Valor PisCofins,
    #     Valor Icms (e mais colunas a direita, incluindo Valor Bruto Negociado, fora do
    #     recorte capturado - CONFIRMAR ao rolar a grid para a direita na VM).
    #   - O campo "Tipo Evento" e um dropdown HTML padrao (nao precisa de navegacao por
    #     teclado): clica no campo (campo_tipo_evento.png, mostra "Complemento" que e o
    #     valor padrao de uma linha nova) e depois clica na opcao "Recuperação"
    #     (opcao_recuperacao.png) na lista que abre.
    #   - O botao final e "Salvar" (bnt_salvar_evento.png), dentro do painel de Eventos
    #     (NAO o Salvar do painel esquerdo, que e outro botao/funcao - grid tem os dois).
    # ------------------------------------------------------------------
    def _retificar_um_processo(self, recuperacao):
        img_bnt_filtro = os.path.join(DIRETORIO_IMGS_AGI_CONFIG, "bnt_filtro.png")
        img_campo_periodo = os.path.join(DIRETORIO_IMGS_CONTESTACAO_GERENCIAR, "campo_periodo.png")
        img_bnt_buscar = os.path.join(DIRETORIO_IMGS_CONTESTACAO_GERENCIAR, "bnt_buscar_contestacao.png")
        img_bnt_adicionar = os.path.join(DIRETORIO_IMGS_CONTESTACAO_GERENCIAR, "bnt_mais_adicionar.png")
        img_campo_tipo_evento = os.path.join(DIRETORIO_IMGS_CONTESTACAO_GERENCIAR, "campo_tipo_evento.png")
        img_bnt_salvar_evento = os.path.join(DIRETORIO_IMGS_CONTESTACAO_GERENCIAR, "bnt_salvar_evento.png")

        # 0) Abre o modal "Filtro de Registros" (botao "Filtro" no topo da tela) - e onde
        # ficam os campos Periodo Referencia / Operadora Prestadora usados no passo 1.
        self.AGI_CONFIG._wait_appear(img_bnt_filtro, timeout=20)
        time.sleep(1)
        self.AGI_CONFIG._click(img_bnt_filtro)

        # 1) Filtro por periodo + empresa.
        # Periodo Referencia: CONFIRMADO NA VM (29/07, print real) - o campo abre em
        # "Selecione" (nada escolhido); o clique so ABRE a lista, nao seleciona nada
        # sozinho. A lista vem em ordem decrescente (202606, 202605, 202604, ...) e o
        # PRIMEIRO item e sempre o mes anterior - por isso so descer 1 vez (Down) e
        # confirmar (Enter) ja seleciona o valor certo, sem precisar digitar/comparar
        # texto nenhum.
        # A validacao de que "primeiro item = mes anterior = recuperacao['periodo']" fica
        # em Python puro (assert abaixo), sem ler a UI: a query de
        # _identificar_trafego_recuperado ja filtra "referencia = mes_anterior(PERIODO_REF)",
        # entao recuperacao["periodo"] SEMPRE e o mes anterior por construcao. O assert so
        # pega inconsistencia de configuracao (ex.: PERIODO_REF desatualizado).
        assert str(recuperacao["periodo"]) == self._mes_anterior(PERIODO_REF), (
            f"recuperacao['periodo'] ('{recuperacao['periodo']}') nao bate com "
            f"mes_anterior(PERIODO_REF) ('{self._mes_anterior(PERIODO_REF)}') - "
            f"PERIODO_REF pode estar desatualizado."
        )
        self.AGI_CONFIG._wait_appear(img_campo_periodo, timeout=30)
        self.AGI_CONFIG._click(img_campo_periodo)
        # PRECISA CONFIRMAR NA VM: Down uma vez move a selecao pro 1o item ("Selecione" ->
        # primeiro periodo) e Enter confirma/fecha a lista - se o 1o item ja vier
        # destacado ao abrir, o Down pode pular pro 2o item por engano (nesse caso, trocar
        # por so "Enter" ou usar "Home" antes do Enter pra garantir o topo da lista).
        pyautogui.press("down")
        pyautogui.press("enter")

        # Periodo Referencia e um RANGE (campo "de" + campo "ate", ver print 29/07) - o
        # exemplo real do As Is preenche os dois com o MESMO periodo (ex.: "202506 ate
        # 202506"). NAO da pra ter uma imagem separada pro campo "ate": o "Selecione" e
        # visualmente identico em varios campos da tela (ate de Periodo Referencia, de/ate
        # de Periodo Trafego) - qualquer template desses bateria no lugar errado. Em vez
        # disso, usa Tab pra mover o foco pro proximo campo (o "ate" ao lado) e repete a
        # mesma selecao (1o item = mes anterior).
        # PRECISA CONFIRMAR NA VM: 1 Tab move o foco exatamente pro campo "ate" certo (e
        # nao pula pra outro campo, ex. se houver algum elemento invisivel no meio).
        pyautogui.press("tab")
        pyautogui.press("down")
        pyautogui.press("enter")

        # 2) Clica "Filtrar" - so estreita o resultado por periodo (NAO seleciona
        # operadora nenhuma - essa etapa foi removida, ver bloco 2.1-2.4 abaixo).
        self.AGI_CONFIG._click(img_bnt_buscar,confidence=0.9)

        # 2.1) Exporta a grid filtrada pra CSV (mesmo padrao ja usado em
        # AGI_CONFIG.Baixar_Remessa, lado Receita).
        caminho_csv = self._exportar_grid_csv()

        # 2.2) Acha, no CSV, a linha certa cruzando EOT + Periodo Referencia +
        # Periodo Trafego + Valor - e pega o "ID Processo" dela.
        id_processo = self._achar_id_processo_no_csv(caminho_csv, recuperacao)

        # 2.3) Digita o ID Processo no campo "Numero Processo" (topo da tela) e clica
        # em "Pesquisar" - isso restringe a grid a exatamente 1 linha.
        self._selecionar_processo_por_id(id_processo)

        # 2.4) PONTO CRITICO (reforcado pela cliente em 03/08): antes de dar duplo-clique
        # e Adicionar, confirma que "Processo Selecionado: <id>" aparece certo no painel
        # direito - se nao aparecer, o Adicionar lanca o evento no lugar errado (ou em nada).
        self._abrir_processo_selecionado()
        self._validar_processo_selecionado(id_processo)

        # 3) "+ Adicionar" - cria a linha nova de evento. CONFIRMADO NA VM (06/08): existem
        # DOIS botoes "+ Adicionar" identicos na tela (grid de processos, esquerda, e
        # painel de Eventos, direita) - a imagem sozinha nao diferencia. Usa
        # _clicar_botao_mais_a_direita pra garantir que clica no do painel de Eventos.
        self.AGI_CONFIG._wait_appear(img_bnt_adicionar, timeout=20)
        self._clicar_botao_mais_a_direita(img_bnt_adicionar)

        # 4) Tipo Evento = "Recuperação" - CONFIRMADO NA VM (06/08): 12 "Down" a partir do
        # valor padrao ("Complemento") chega em "Recuperação" - contagem real medida ao
        # vivo (a lista tem mais opcoes do que as visiveis no print original).
        self.AGI_CONFIG._wait_appear(img_campo_tipo_evento, timeout=20)
        self.AGI_CONFIG._click(img_campo_tipo_evento)
        for _ in range(12):
            pyautogui.press("down")
        pyautogui.press("enter")

        # 5) Calculo e preenchimento dos valores (formulas do To Be MVP2, paragrafos
        # 369-372). CONFIRMADO (print da grid rolada TOTALMENTE pra direita, 04/08): a
        # ordem real e completa das colunas e:
        #   Tipo Evento | Data Evento | Data Vencimento | Data Pagamento Rec. |
        #   Data Envio Contabil | Observacao | Duracao | Valor Liquido | Valor PisCofins |
        #   Valor Icms | Valor Ibs Estadual | Valor Ibs Municipal | Valor Cbs |
        #   Valor BrutoNegociado | Valor Provisionado | Usuario | Arquivo
        # "Data Evento" ja vem AUTO-PREENCHIDA (data de hoje) ao clicar Adicionar - so
        # precisa pular por ela (TAB), sem digitar nada. As demais colunas de data
        # (Vencimento/Pagamento Rec./Envio Contabil) e Observacao ficam em branco (sem
        # regra definida no To Be). TAB deve navegar entre as celulas da mesma linha
        # (padrao comum de grid web), mas CONFIRMAR na VM se e assim mesmo ou se cada
        # celula precisa de um clique proprio.
        valores = self._calcular_valores_evento(recuperacao)

        for _ in range(6):
            pyautogui.press("TAB")  # pula Data Evento, Data Vencimento, Data Pagamento Rec., Data Envio Contabil, Observação

        # interval: mesmo motivo do campo Periodo/Empresa acima - digitar rapido demais
        # em campos JS faz perder caracteres.
        pyautogui.typewrite(str(valores["duracao"]), interval=0.15); pyautogui.press("TAB")
        pyautogui.typewrite(str(valores["valor_liquido"]), interval=0.15); pyautogui.press("TAB")
        pyautogui.typewrite(str(valores["valor_pis_cofins"]), interval=0.15); pyautogui.press("TAB")

        # "Valor Icms", "Valor Ibs Estadual", "Valor Ibs Municipal" e "Valor Cbs" NAO tem
        # formula definida no To Be (so Duracao/Valor Liquido/PisCofins/Valor Bruto
        # Negociado tem regra) - por isso so pulam com TAB, sem digitar nada, deixando o
        # valor padrao (0) da linha nova.
        for _ in range(5):
            pyautogui.press("TAB")  # pula Valor Icms, Valor Ibs Estadual, Valor Ibs Municipal, Valor Cbs

        pyautogui.typewrite(str(valores["valor_bruto_negociado"]), interval=0.15)

        # 6) Salvar - botao do painel de EVENTOS (direita), nao o da grid de processos
        # (esquerda) - sao dois botoes "Salvar" identicos na mesma tela, mesmo caso do
        # "+ Adicionar" acima. Usa o mesmo helper pra garantir o botao certo.
        self.AGI_CONFIG._wait_appear(img_bnt_salvar_evento, timeout=20)
        self._clicar_botao_mais_a_direita(img_bnt_salvar_evento)

    # ------------------------------------------------------------------
    # NOVO (03/08, pos-reuniao com cliente): exporta a grid de Contestacao (ja filtrada
    # por periodo) pra CSV, reaproveitando o MESMO padrao ja usado em
    # AGI_CONFIG.Baixar_Remessa (lado Receita): botao de dropdown de exportacao ->
    # "Exportar para CSV" -> janela nativa "Salvar Como" (_Janela_salvar) -> corrige
    # aspas quebradas no arquivo salvo.
    #
    # TODO [CONFIRMAR NA VM]: o dropdown de exportacao da tela de Contestacao usa as
    # MESMAS imagens (drop_box_export.png / submenu_export_para_csv.png) do dropdown da
    # tela de Receita? Ambos ficam em DIRETORIO_IMGS_AGI_CONFIG (pasta compartilhada),
    # entao e provavel que sim (mesmo componente reaproveitado pelo AGI), mas precisa
    # validar - se nao bater, recapturar versoes especificas de Contestacao.
    # ------------------------------------------------------------------
    def _exportar_grid_csv(self):
        img_drop_box_export = os.path.join(DIRETORIO_IMGS_AGI_CONFIG, "drop_box_export.png")
        img_submenu_export_csv = os.path.join(DIRETORIO_IMGS_AGI_CONFIG, "submenu_export_para_csv.png")
        caminho_csv = os.path.join(DIRETORIO_TEMP, "contestacao_exportada.csv")

        # Apaga o CSV da rodada anterior ANTES de exportar de novo - o loop de
        # recuperacoes reaproveita o mesmo nome de arquivo, entao se a exportacao falhar
        # silenciosamente (imagem nao bate, tela em estado diferente), o codigo NAO pode
        # ler o CSV antigo sem perceber (acharia o ID Processo de outra recuperacao, sem
        # erro nenhum). Tambem evita depender do dialogo nativo "Confirm Save As".
        if os.path.exists(caminho_csv):
            os.remove(caminho_csv)

        while True:
            self.AGI_CONFIG._wait_appear(img_drop_box_export, timeout=10)
            self.AGI_CONFIG._click(img_drop_box_export)
            time.sleep(2)
            pyautogui.moveRel(0, -20)
            resultado = self.AGI_CONFIG._click(img_submenu_export_csv)
            if resultado != "Não encontrou a imagem":
                break

        self.AGI_CONFIG._Janela_salvar(
            diretorio=caminho_csv,
            nome_janela=rf"(Select location for download by|Selecionar local para download de) {AGI_JANELA_HOST}",
        )

        # Corrige linhas com aspas quebradas - mesmo tratamento do Baixar_Remessa.
        with open(caminho_csv, "r", encoding="utf-8") as f:
            linhas = f.readlines()
        linhas_corrigidas = [
            linha.replace('"', '') if linha.count('"') % 2 != 0 else linha
            for linha in linhas
        ]
        time.sleep(1)
        with open(caminho_csv, "w", encoding="utf-8") as f:
            f.writelines(linhas_corrigidas)

        return caminho_csv

    # ------------------------------------------------------------------
    # CONFIRMADO (03/08) com exemplo real de CSV exportado (data/Temp/teste.csv):
    # colunas batem com o esperado - "ID Processo", "Ope. Prest." (EOT puro, ex.: "076",
    # NAO "EOT-Nome"), "Per. Ref.", "Per. Traf.", "Valor Bruto" (formato BR: "852.618,97").
    # Todos os campos vem entre aspas duplas - pandas.read_csv lida com isso sozinho.
    #
    # IMPORTANTE: EOT + Periodo Referencia + Periodo Trafego SOZINHOS NAO bastam pra
    # achar 1 unica linha - confirmado no exemplo real, onde 2 linhas (590969 e 590971)
    # tem o MESMO EOT+Ref+Traf, so diferindo no valor. Por isso o "Valor Bruto" tambem
    # entra no cruzamento, com uma tolerancia pra arredondamento.
    #
    # TODO [CONFIRMAR COM NEGOCIO]: qual valor de `recuperacao` deve bater com "Valor
    # Bruto" do CSV - hoje uso recuperacao["valor_bruto"] (que vem de vb_diferenca, a
    # DIFERENCA da recuperacao), mas "Valor Bruto" no CSV parece ser o valor da
    # contestacao ORIGINAL ja lancada (nao necessariamente a mesma coisa). Se nao bater
    # nunca na VM, provavelmente precisa trocar por outro campo/coluna.
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_valor_br(texto):
        """Converte numero no formato BR ('852.618,97') pra float."""
        return float(str(texto).replace(".", "").replace(",", "."))

    def _achar_id_processo_no_csv(self, caminho_csv, recuperacao, tolerancia=0.01):
        df = pd.read_csv(caminho_csv, sep=";", encoding="utf-8", dtype=str)

        filtro = (
            (df["Ope. Prest."].astype(str).str.strip() == str(recuperacao["eot_operadora"]).strip())
            & (df["Per. Ref."].astype(str).str.strip() == str(recuperacao["periodo"]).strip())
            & (df["Per. Traf."].astype(str).str.strip() == str(recuperacao["periodo_trafego"]).strip())
        )
        candidatas = df[filtro]

        valor_esperado = recuperacao["valor_bruto"]
        candidatas = candidatas[
            candidatas["Valor Bruto"].apply(self._parse_valor_br).sub(valor_esperado).abs() <= tolerancia
        ]

        if len(candidatas) != 1:
            raise ValueError(
                f"Esperava encontrar exatamente 1 linha no CSV para "
                f"eot_operadora={recuperacao['eot_operadora']!r}, "
                f"periodo={recuperacao['periodo']!r}, "
                f"periodo_trafego={recuperacao['periodo_trafego']!r}, "
                f"valor_bruto={valor_esperado!r} - encontrou {len(candidatas)}."
            )
        return str(candidatas.iloc[0]["ID Processo"]).strip()

    # ------------------------------------------------------------------
    # NOVO (03/08): digita o ID Processo no campo "Numero Processo" (topo da tela) e
    # clica em "Pesquisar" - restringe a grid a exatamente 1 linha, SEM precisar do
    # dropdown de operadora.
    #
    # CONFIRMADO NA VM (04/08, dump real - dump_tela_principal.txt): o campo "Numero
    # Processo" e um Edit de verdade, acessivel via UIA (child_window(title="Número
    # Processo : ", control_type="Edit")). MAS o botao "Pesquisar" NAO aparece em
    # NENHUM lugar da arvore UIA (nem com outro nome/control_type) - diferente dos
    # vizinhos na mesma barra ("Filtro", "Exportar", "Operacão Lote", que SAO
    # acessiveis). Por isso o clique em "Pesquisar" precisa ser por imagem mesmo.
    # ------------------------------------------------------------------
    def _conectar_janela_agi_uia(self):
        for w in Desktop(backend="uia").windows():
            if w.window_text() == NOME_JANELA_AGI:
                app = Application(backend="uia").connect(title=NOME_JANELA_AGI)
                return app.window(title=NOME_JANELA_AGI)
        raise RuntimeError(f"Janela '{NOME_JANELA_AGI}' nao encontrada.")

    def _selecionar_processo_por_id(self, id_processo):
        janela = self._conectar_janela_agi_uia()

        campo_numero_processo = janela.child_window(title="Número Processo : ", control_type="Edit")
        campo_numero_processo.click_input()
        campo_numero_processo.type_keys(str(id_processo), with_spaces=True)

        # bnt_pesquisar.png CAPTURADA (04/08) - botao "Pesquisar" da tela principal de
        # Contestacao (ao lado de "Numero Processo"), nao acessivel via UIA.
        img_bnt_pesquisar = os.path.join(DIRETORIO_IMGS_CONTESTACAO_GERENCIAR, "bnt_pesquisar.png")
        self.AGI_CONFIG._wait_appear(img_bnt_pesquisar, timeout=10)
        self.AGI_CONFIG._click(img_bnt_pesquisar)
        time.sleep(5)

    # ------------------------------------------------------------------
    # NOVO (04/08): apos "Pesquisar" (grid com exatamente 1 linha), da duplo-clique
    # nela pra abrir/selecionar no painel direito "Eventos do Processo de Contestação".
    #
    # ATUALIZADO (04/08, print de tela cheia): em vez de usar coord_primeira_linha.png
    # (recorte pequeno e quase todo de uma cor solida - pouco confiavel), ancora no
    # CABECALHO "ID Processo" (texto fixo, nunca muda) e clica num offset fixo abaixo
    # dele, caindo sempre na 1a linha de dado, seja qual for o ID Processo.
    #
    # Offset medido no print (04/08): cabecalho "ID Processo" em y~209, linha de dado em
    # y~277 -> diferenca de ~68px (cabecalho -> linha de filtro por coluna -> linha de
    # dado). TODO [CALIBRAR NA VM]: essa medida veio de estimativa visual sobre o print,
    # nao de pixel exato - se o clique cair na linha de filtro (a fileira de caixas
    # vazias logo abaixo do cabecalho) em vez da linha de dado, ajustar OFFSET_Y_LINHA
    # pra cima ou pra baixo. Como _validar_processo_selecionado roda logo depois, um
    # offset errado vai FALHAR de forma clara (nao vai silenciosamente abrir o processo
    # errado).
    # ------------------------------------------------------------------
    OFFSET_Y_CABECALHO_ATE_LINHA = 72

    def _abrir_processo_selecionado(self):
        img_cabecalho = os.path.join(DIRETORIO_IMGS_CONTESTACAO_GERENCIAR, "cabecalho_id_processo.png")
        self.AGI_CONFIG._wait_appear(img_cabecalho, timeout=15)
        posicao_cabecalho = pyautogui.locateOnScreen(img_cabecalho, confidence=0.8)
        if not posicao_cabecalho:
            raise ValueError(
                "Nao encontrou o cabecalho 'ID Processo' (cabecalho_id_processo.png) na "
                "grid de resultado."
            )
        x = posicao_cabecalho.left + (posicao_cabecalho.width // 2)
        y = posicao_cabecalho.top + self.OFFSET_Y_CABECALHO_ATE_LINHA
        pyautogui.doubleClick(x, y)
        pyautogui.doubleClick(x, y)
        time.sleep(1)

    # ------------------------------------------------------------------
    # NOVO (03/08): valida que "Processo Selecionado: <id_processo>" aparece certo no
    # painel direito ANTES de clicar em Adicionar - ponto critico reforcado pela cliente
    # na reuniao (03/08): sem essa confirmacao, o evento pode ser lancado no processo
    # errado, ou em nenhum. Usa UIA porque esse Static e DINAMICO (o proprio texto muda
    # com o numero do processo, diferente do label fixo "Operadora Prestadora:") - ja
    # confirmamos que Statics desse tipo (ex.: "Processo Selecionado: 0" no estado
    # inicial) aparecem na arvore com o valor atual no nome.
    # ------------------------------------------------------------------
    def _validar_processo_selecionado(self, id_processo):
        janela = self._conectar_janela_agi_uia()
        texto_esperado = f"Processo Selecionado: {id_processo}"

        # PRECISA CONFIRMAR NA VM: title_re com regex generica pra achar o Static atual
        # (o numero muda), depois compara o texto exato lido.
        campo_selecionado = janela.child_window(title_re=r"Processo Selecionado: .*", control_type="Text")
        if not campo_selecionado.exists():
            raise ValueError(
                "Nao encontrou nenhum Static 'Processo Selecionado: ...' na tela - "
                "nao da pra confirmar se o processo certo foi selecionado."
            )

        texto_atual = campo_selecionado.window_text()
        if texto_atual.strip() != texto_esperado.strip():
            raise ValueError(
                f"Processo selecionado errado: esperava {texto_esperado!r}, "
                f"achou {texto_atual!r}. Abortando antes de clicar Adicionar."
            )

    # ------------------------------------------------------------------
    # NOVO (06/08): "+ Adicionar" e "Salvar" tem DOIS botoes identicos na tela
    # (grid de processos esquerda + painel de Eventos direita) - a MESMA imagem bate nos
    # dois, entao um locateOnScreen simples pode pegar o errado (o da esquerda, que faz
    # outra coisa - adicionar processo/salvar a grid, nao o evento). Pega TODAS as
    # ocorrencias da imagem e clica na que estiver mais a DIREITA, ja que o painel de
    # Eventos sempre fica a direita da grid de processos nessa tela.
    # ------------------------------------------------------------------
    @staticmethod
    def _clicar_botao_mais_a_direita(img, confidence=0.8):
        posicoes = list(pyautogui.locateAllOnScreen(img, confidence=confidence))
        if not posicoes:
            raise ValueError(f"Nao encontrou nenhuma ocorrencia de '{img}' na tela.")
        posicao_direita = max(posicoes, key=lambda caixa: caixa.left)
        pyautogui.click(pyautogui.center(posicao_direita))

    # ------------------------------------------------------------------
    # Calculo dos campos do evento de Recuperacao - REGRA JA CONHECIDA (To Be MVP2,
    # paragrafos 369-372), pura funcao de calculo, sem dependencia de tela. Isolada aqui
    # pra poder ser testada sem precisar do AGI aberto.
    # ------------------------------------------------------------------
    @staticmethod
    def _calcular_valores_evento(recuperacao):
        minutos = recuperacao["minutos"]
        valor_bruto = recuperacao["valor_bruto"]  # "VB da tabela"
        valor_liquido = round(valor_bruto * 0.9635, 2)
        valor_pis_cofins = round(valor_bruto - valor_liquido, 2)
        return {
            "duracao": minutos,
            "valor_liquido": valor_liquido,
            "valor_pis_cofins": valor_pis_cofins,
            "valor_bruto_negociado": valor_bruto,
        }


if "__main__" == __name__:
    Retificacao_Contestacao().Fluxo_Retificacao_Recuperacao()
