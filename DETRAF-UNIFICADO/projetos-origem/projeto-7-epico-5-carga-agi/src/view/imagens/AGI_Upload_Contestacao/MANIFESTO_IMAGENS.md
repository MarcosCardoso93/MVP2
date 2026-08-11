# Imagens faltantes - tela "Contestação > Gerenciar" (HU-18)

Esta pasta está **vazia**. Nenhuma imagem desta tela existe no exemplo `RPA_DETRAF_RECEITA`
(lá só existe automação para Detraf/Importar, Relatórios e Remessa — nunca para Contestação).

Capturar os prints abaixo **na VM**, com o AGI aberto e logado, no mesmo padrão dos
templates já usados no projeto (recorte apertado só do botão/ícone, mesmo zoom/tema da
tela onde o robô vai rodar). Salvar cada um com o nome exato listado, dentro desta pasta.

| Arquivo a criar | Tela / momento | O que capturar |
|---|---|---|
| `bnt_contestacao.png` | Menu principal do AGI | O item de menu **"Contestação"** (mesmo nível de `bnt_detraf.png` usado no Detraf/Importar) |
| `bnt_submenu_gerenciar.png` | Submenu aberto após clicar em Contestação | A opção **"Gerenciar"** |
| `bnt_upload_contestacao.png` | Dentro da tela de Gerenciar | O botão **"Upload"** dessa tela (confirmar se o rótulo/ícone é igual ao do Detraf/Importar ou diferente) |
| `bnt_salvar_contestacao.png` | Depois do AGI carregar o arquivo | O botão **"Salvar"** citado no To Be MVP2, parágrafo 322: *"O AGI carrega as informações e o robô clica em Salvar na tela"* — esse clique em Salvar **não existe** no fluxo de Detraf/Importar, é exclusivo da Contestação |

## Pontos de atenção ao capturar

- Confirmar se o diálogo nativo do Windows que abre ao clicar em Upload tem o **mesmo título**
  já mapeado no exemplo (`"Select file for upload by {host}"`) ou se muda nesta tela — se for
  igual, o método `_Janela_salvar` do `AGI_config.py` pode ser reaproveitado sem alteração.
- Confirmar se, após clicar em "Salvar", aparece algum diálogo de confirmação (tipo
  "Confirm Save As") parecido com o do exemplo — se sim, também é coberto pelo
  `_Janela_salvar` sem precisar de código novo.
- Verificar se existe algum indicador de erro nessa tela (linha vermelha, mensagem, etc.) —
  hoje não há nenhuma rotina de tratamento de erro pensada para a Contestação.
- Depois de capturadas, atualizar `Upload_Contestacao.py` removendo os comentários `TODO`
  correspondentes e testar o fluxo com `PERMITIR_UPLOAD_AGI=False` primeiro (modo seguro).
