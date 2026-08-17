# Imagens da tela "Contestação > Gerenciar" (HU-21)

**ATUALIZAÇÃO (22/07):** as 9 imagens abaixo foram encontradas e recortadas a partir dos
screenshots reais embutidos no docx `[btime] As Is - Detraf 2ª.docx` (enviado pelo
usuário), que documenta o passo a passo manual exatamente com prints de tela do AGI. Não
foi necessário pedir captura nova na VM para a maior parte do fluxo.

⚠️ **Atenção:** por serem recortes de um print de documentação (não capturados ao vivo na
VM de produção), a resolução/escala pode não bater 100% com o ambiente real de execução.
Antes de rodar de verdade, validar o reconhecimento (`pyautogui.locateOnScreen`) de cada
uma na VM e recapturar as que falharem.

| Arquivo | Status | Origem |
|---|---|---|
| `bnt_contestacao.png` | ✅ Encontrada | Recorte do menu principal (print do As Is) |
| `bnt_submenu_gerenciar.png` | ✅ Encontrada | Recorte do submenu Contestação (print do As Is) |
| `campo_periodo.png` | ✅ Encontrada | Campo "Periodo Referência" do modal de Filtro |
| `campo_empresa.png` | ✅ Encontrada | Campo "Operadora Prestadora" do modal de Filtro |
| `bnt_buscar_contestacao.png` | ✅ Encontrada | Botão "Filtrar" do modal |
| `bnt_mais_adicionar.png` | ✅ Encontrada | Botão "+ Adicionar" do painel de Eventos |
| `campo_tipo_evento.png` | ✅ Encontrada | Campo dropdown "Tipo Evento" (mostra "Complemento", valor padrão de linha nova) |
| `opcao_recuperacao.png` | ✅ Encontrada | Opção "Recuperação" dentro do dropdown já aberto |
| `bnt_salvar_evento.png` | ✅ Encontrada | Botão "Salvar" do painel de Eventos (à direita) |
| `bnt_pesquisar.png` | ✅ Encontrada (04/08) | Botão "Pesquisar" da tela principal (ao lado de "Número Processo") - **não é acessível via UIA** (diferente de "Filtro"/"Exportar"/"Operacão Lote", que são), por isso precisou de imagem |
| `coord_primeira_linha.png` | ⚠️ Substituída (04/08) | Recorte pequeno (25x24px), quase todo cor sólida - trocado por `cabecalho_id_processo.png` (mais estável). Mantido no repo mas não é mais referenciado no código. |
| `cabecalho_id_processo.png` | ✅ Encontrada (04/08) | Texto do cabeçalho da coluna "ID Processo" na grid de resultado (texto FIXO, nunca muda) - usado como âncora pra calcular o duplo-clique na 1ª linha de dado (offset fixo abaixo do cabeçalho, ver `_abrir_processo_selecionado`) |

## Atualização (29/07) - comportamento real do campo Periodo Referência

Confirmado com print da VM: "Periodo Referência" é um **range** ("de" + "ate"), não um
campo único. Os dois abrem em "Selecione" (nada escolhido); clicar só abre a lista, não
seleciona nada sozinho - precisa Down + Enter pra pegar o 1º item (que é sempre o mês
anterior). O exemplo real do print antigo ("202506 até 202506") mostra que os dois lados
do range recebem o **mesmo** período.

**Sem imagem nova pro campo "ate":** o "Selecione" é visualmente idêntico em vários campos
da tela (ate de Periodo Referência, de/ate de Periodo Tráfego) - qualquer template
genérico bateria no lugar errado. Em vez de imagem, o código usa `Tab` pra mover o foco do
campo "de" (já selecionado) pro campo "ate" ao lado, e repete a mesma seleção por teclado
(Down + Enter). Precisa confirmar na VM se 1 Tab move o foco exatamente pro campo certo.

## O que o print confirmou sobre o fluxo (atualiza o README)

- O menu Contestação tem 3 opções: **Gerenciar**, Análise de Contestação, Risco Contestação.
- A tela de Gerenciar tem duas grids lado a lado: à esquerda a lista de processos (colunas
  ID Processo, Data Processo, Ope. JV, Ope. Prest., Per. Ref., Per. Traf., Nat. Oper.,
  com botões Atualizar/Remover/Adicionar/Salvar/**Upload**/Alterar — o botão Upload aqui é
  o mesmo que a HU-18 usa); à direita, ao clicar numa linha, abre "Eventos do Processo de
  Contestação" com o botão **+ Adicionar** que cria a linha do evento.
- O campo "Tipo Evento" é um **dropdown HTML comum** (clica, abre lista, clica na opção) —
  mais simples do que o padrão de navegação por teclado usado em
  `AGI_config._selecionar_periodo`.
- A linha do evento tem colunas em sequência: Tipo Evento, Data Evento, Data Vencimento,
  Data Pagamento Rec., Data Envio Cont., Observação, Duração, Valor Liquido, Valor
  PisCofins, Valor Icms — e mais colunas à direita (Valor Bruto Negociado deve estar entre
  elas, mas ficou fora do recorte do print; **confirmar rolando a grid para a direita na
  VM**).

## Atualização (03-04/08) - mudança de estratégia pra achar o ID Processo

Reunião com a cliente (03/08) confirmou o caminho real: em vez de tentar selecionar a
operadora no dropdown do Filtro (investigação extensa com pywinauto/UIA/OCR mostrou que
esse dropdown **não é acessível de jeito nenhum**), o fluxo é: Filtrar só por período →
Exportar a grid pra CSV → achar a linha certa no CSV (cruzando EOT + Período Referência +
Período Tráfego + Valor) → digitar o "ID Processo" encontrado no campo **"Número
Processo"** (topo da tela) → **Pesquisar** → validar "Processo Selecionado: X" antes de
Adicionar. Ver `_retificar_um_processo` em `Retificacao_Contestacao.py`.

Confirmado via UIA (04/08): "Número Processo" é um `Edit` acessível, e "Processo
Selecionado: X" é um `Static` dinâmico acessível (dá pra ler o valor atual direto, sem
imagem/OCR). Mas o botão "Pesquisar" **não aparece em nenhum lugar da árvore UIA** -
precisou de imagem (`bnt_pesquisar.png`).

## Atualização (04/08) - duplo-clique na linha de resultado por âncora de cabeçalho

O duplo-clique na 1ª linha da grid de resultado foi implementado em
`_abrir_processo_selecionado`, mas trocado de estratégia depois de um print de tela
cheia: em vez de `coord_primeira_linha.png` (recorte pequeno, quase só cor sólida, pouco
confiável), agora ancora no **cabeçalho "ID Processo"** (texto fixo, nunca muda) e clica
num offset fixo abaixo dele (`OFFSET_Y_CABECALHO_ATE_LINHA = 68`, estimado visualmente no
print - cabeçalho em y~209, linha de dado em y~277).

**TODO [CALIBRAR NA VM]:** o offset de 68px é uma estimativa visual, não medição exata de
pixel - se o duplo-clique cair na linha de filtro por coluna (fileira de caixas vazias
logo abaixo do cabeçalho) em vez da linha de dado, ajustar `OFFSET_Y_CABECALHO_ATE_LINHA`.
Como `_validar_processo_selecionado` roda logo depois, um offset errado vai falhar de
forma clara, não vai silenciosamente abrir o processo errado.

## O que ainda não dá pra resolver só com o print

- **Regra de negócio "identificar tráfego recuperado"**: os prints (imagens 13/5 do As Is)
  mostram uma planilha comparando Vivo x Operadora (Minutos/VB) por Referência x Tráfego,
  com colunas Diferença e Variação Perc. — provavelmente a aba "Contest" do
  `Base_Contestação`. Ainda falta confirmar qual arquivo/aba exatamente o robô deve ler
  para detectar a variação negativa mês a mês.
