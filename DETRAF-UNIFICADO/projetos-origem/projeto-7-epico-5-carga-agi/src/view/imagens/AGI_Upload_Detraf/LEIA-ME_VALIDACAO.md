# Imagens copiadas do exemplo - precisam de validação, não recaptura do zero

Estes 8 arquivos foram copiados de `RPA_DETRAF_RECEITA/src/view/imagens/AGI_Upload_DI_DE/`,
porque a tela "Detraf > Importar Dados > Upload" é a mesma aplicação AGI, usada tanto na
Receita quanto na Despesa (não é uma tela específica de um dos dois fluxos).

| Arquivo | Uso |
|---|---|
| `bnt_detraf.png` | Item de menu "Detraf" |
| `bnt_submenu_importar_dados.png` | Submenu "Importar Dados" |
| `bnt_upload.png` | Botão "Upload" na tela |
| `bnt_export_erro.png` | Botão de exportar erro (grid pós-upload) |
| `bnt_voltar.png` | Botão "Voltar" |
| `row_scroll.png` / `row_scroll_up.png` | Referências de scroll da grid |
| `tab_regs_Erro.png` / `tab_regs_Erro_bgd_white.png` | Aba de registros com erro |

## O que falta fazer (não é captura do zero, é validação)

- Rodar `pyautogui.locateOnScreen()` com cada uma destas imagens na VM de Despesa e conferir
  se o match funciona (`confidence` padrão do projeto é 0.8). Se a resolução, escala ou tema
  da VM de Despesa for diferente da VM onde estas imagens foram capturadas originalmente, o
  reconhecimento pode falhar e será necessário recapturar.
- Confirmar se a tela de erro (linha vermelha na grid) aparece da mesma forma para arquivos
  de Despesa como aparece para os de Receita — isso não foi validado, só assumido por
  similaridade de tela.
