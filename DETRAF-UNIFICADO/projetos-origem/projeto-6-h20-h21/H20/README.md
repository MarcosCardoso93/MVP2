# HU-20 - Verificação do Relatório Receitas e Despesas no AGI

Pacote isolado para a HU-20 (Épico 6 - Encontro de Contas), montado seguindo a mesma
estrutura do Épico 5 e do exemplo de referência `RPA_DETRAF_RECEITA`.

Legenda: ✅ Pronto (reaproveitado)  |  🔄 Adaptado  |  🆕 A criar/confirmar

**ATUALIZAÇÃO (22/07):** os prints reais embutidos no docx `[btime] As Is - Detraf 2ª.docx`
confirmaram os dois principais pontos em aberto — ver seção "Confirmado pelos prints" abaixo.

## Critérios de aceite x status

| Critério | Status |
|---|---|
| Acesso a Relatórios > Detraf > Receitas e Despesas no AGI | ✅ Pronto |
| Filtro por período | ✅ Pronto |
| Filtro por natureza "D" e operadora | ✅ Confirmado (mesma coluna do exemplo) |
| Comparação do somatório de Vlr. Bruto com subtotal do EC | ✅ Confirmado e implementado (Excel, aba por operadora, célula O87) |
| Sinalização de inconsistência quando valores divergirem | 🆕 A criar (mecanismo ainda não definido) |
| Repetição para todas as operadoras | ✅ Coberto pelo `groupby` da adaptação |

## ✅ Confirmado pelos prints reais do As Is (resolve os 2 principais TODOs)

- **Cabeçalho do export**: o print da tela "SAP Receita e Despesa" mostra as colunas
  `Per. Refer.`, `Per. Traf.`, `Grp. Oper .Prest`, `Oper. Prest.`, `Div. SAP`,
  `Remuneração`, `Remun.`, `Natureza`, `C. Contábil`, `Operadora JV`, `Tp. Mercado Vivo`,
  `Tp. Mercado Prest.`, `Chamadas`, `Minutos`, `Vlr. Bruto`, `Vlr. PisCofins`, `Vlr. ICMS`
  — **idênticas** às usadas no exemplo de Receita (`Criacao_Remessa._tratativa_remessa`).
  É o mesmo relatório do AGI para os dois fluxos, só muda o valor filtrado em "Natureza"
  (`C` para receita, `D` para despesa). Filtro por Natureza/Operadora também aparece feito
  **direto na grid do AGI** (campos de filtro no cabeçalho de cada coluna, ex.: digitar "D"
  em Natureza e "AMPERNE" em Grp. Oper .Prest) — alternativa via UI, além do filtro em pandas
  já implementado.
- **Formato do Encontro de Contas**: confirmado que é uma **planilha Excel real**, com uma
  **aba por operadora** (ex.: aba "AMPERNET") e um bloco "ENCONTRO DE CONTAS" com as linhas
  Total Despesa / Total Contestação Despesa / **Subtotal Despesa** (linha 87, valor
  ex.: -521,60) — bate exatamente com o "célula O87" citado no To Be MVP2. `config.py` e
  `Verificacao_Relatorio.py` já foram atualizados para ler por `openpyxl`, achando a aba
  pelo nome da operadora e lendo a célula `CELULA_SUBTOTAL_DESPESA` (default `"O87"`).
- Também aparece na tela um recurso nativo do AGI de somar coluna direto na grid (dropdown
  "Sum" no cabeçalho de "Vlr. Bruto", mostrando o total agregado na tela) — não foi usado
  na implementação (pandas é mais confiável que ler valor agregado da tela), mas serve como
  conferência visual/manual se precisar validar o robô rodando.

## ✅ O que está pronto (reaproveitado 1:1)

- **`AGI_config.Baixar_Remessa()`** — é literalmente o passo "AGI > Relatórios > Detraf >
  Receitas e Despesas", com filtro de período e exportação para CSV. Nenhuma imagem nova
  precisa ser capturada para essa parte.
- `AGI_config` completo (login, abrir/fechar AGI, helpers de imagem) — igual ao Épico 5.
- `conexao.py`, `utils.py`, `requirements.txt` (já inclui `openpyxl`) — copiados sem alteração.

## 🆕 O que ainda precisa ser criado/confirmado

- **Mecanismo de sinalização de inconsistência.** O exemplo de Receita nunca teve isso — ele
  só gravava um Excel local sem nenhum alerta. Hoje o esqueleto (`_sinalizar_inconsistencias`)
  só grava um Excel de divergências e imprime no console. Falta decidir **como** o time vai
  ser avisado: status no Webfat, e-mail automático, ou log em tabela nova — decisão de
  negócio, não técnica.
- **Nome da aba x nome da operadora**: o código busca a aba do EC cujo nome contém o nome
  da operadora do AGI (`"AMPERNET" in nome_da_aba`) — confirmar se não há divergência de
  nomenclatura entre os dois sistemas (ex.: AGI usa "AMPERNET", aba usa "Ampernet Telecom").
- Limiar de tolerância da diferença (hoje `> 0.01`, arbitrário) — confirmar o valor oficial.
- Gravação em tabela de log específica da Despesa (mesma pendência já registrada no Épico 5).

## Checklist antes de rodar

1. Copiar `.env.example` para `.env` e ajustar os caminhos (incluindo o caminho real do
   arquivo `.xlsx` do Encontro de Contas).
2. Confirmar o nome das abas do EC bate com o nome das operadoras no AGI.
3. Definir o mecanismo de sinalização de inconsistência com o solicitante.
4. Rodar `python main.py` e conferir o Excel gerado em `data/inconsistencias/`.
