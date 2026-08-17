# Entendimento dos Épicos

> ⚠️ **Fotografia da etapa documental (2026-07-30).** Este documento foi escrito
> **antes** de qualquer código chegar, e descreve o entendimento daquele momento.
> Vários pontos já mudaram — em especial: o Épico 5 **tem** projeto (o P7, entregue
> em 2026-08-04), e as HUs 12 a 19 estão implementadas e orquestradas.
>
> **Fonte do estado atual:** `docs/04-relatorios/duvidas-pendentes.md` (pendências),
> `matriz-de-rastreabilidade.md` (HUs) e `unificado/README.md` (código).

> Fontes: `DETRAF_MVP2_Historias.pdf` (estrutura de épicos), V2 (regras vigentes), `Relatorio_Separacao_RPAs_Detraf_MVP2.docx` (destino).

Seis épicos, 21 histórias. Cada épico abaixo traz sua responsabilidade, gatilho, entradas, saídas, HUs, o projeto de origem correspondente e o RPA de destino.

---

## Visão em uma tabela

| Épico | Responsabilidade | HUs | Projeto de origem | RPA destino |
|---|---|---|---|---|
| 1 — Captura de Arquivos via E-mail | Receber e organizar os arquivos das operadoras | 01, 02, 03 | P1 | RPA 1 |
| 2 — Validação dos Arquivos de Detraf | Validar layout, regras e tarifas | 04, 05, 06, 07, 08 | P2 | RPA 2 |
| 3 — Batimento Detraf × Expectativa | Consolidar, comparar e apurar contestação | 09, 10, 11 | P3 | RPA 2 |
| 4 — Geração de Arquivos para Contestação e Carga AGI | Produzir `_EXT`, `_INT`, `_ENV`, carta, e-mail e `CONT_PROC` | 12, 13, 14, 15, 16 | P4 (exceto HU-15) + **P5** (HU-15) | RPA 3 |
| 5 — Carga no AGI | Subir os arquivos no AGI | 17, 18 | ⚠️ **nenhum** — ver abaixo | RPA 3 |
| 6 — Encontro de Contas | Alimentar o EC, conferir e retificar | 19, 20, 21 | P4 (HU-19) + **P6** (HU-20, HU-21) | RPA 3 (19, 20) / **RPA 4** (21) |

⚠️ **O Épico 5 não foi atribuído a nenhum dos seis projetos de origem informados.** Foi reservada a pasta `projetos-origem/projeto-7-epico-5-carga-agi/` até que se esclareça onde o código vive. Ver [`../04-relatorios/relatorio-inconsistencias-e-lacunas.md`](../04-relatorios/relatorio-inconsistencias-e-lacunas.md), achado 1.

---

## ÉPICO 1 — Captura de Arquivos via E-mail

**Responsabilidade.** Ser o único ponto de entrada dos arquivos que as operadoras enviam. Identificar de qual operadora é cada arquivo, guardá-lo no lugar certo da rede e replicá-lo no servidor do WebFat.

**Gatilho.** Evento: chegada de e-mail na caixa `detrafTBRA.br@telefonica.com`, dentro de uma janela de tempo que termina na **data de corte** do mês.

**Entradas.** E-mails com anexos `.csv` ou Excel, do mês de referência, que **não** contenham a palavra "CONTESTAÇÃO" no e-mail (esse filtro negativo evita reprocessar as próprias contestações enviadas pela Vivo, que voltam na mesma caixa).

**Saídas.**
- Arquivos salvos em `\\lagoa\...\Operadoras\{operadora}\{ano}\{aaaamm}\Detrafs Recebidos`
- Cópia no servidor do WebFat (para o analista abrir pela ferramenta)
- E-mails arquivados na pasta "Detraf Despesas" do próprio Outlook
- Registro no WebFat, incluindo status "não validado" quando o envio for divergente

**HUs.** HU-01 (leitura e organização do inbox), HU-02 (identificação da operadora), HU-03 (salvamento na estrutura de pastas).

**O que mudou na V2.**
- A identificação da operadora **não usa mais** o domínio do remetente. Passa a ser a **EOT da Credora (1ª coluna do arquivo) buscada no Anexo 5 pela coluna nome fantasia**. Isso é uma inversão importante: a identificação sai do metadado do e-mail e vai para o conteúdo do arquivo — ou seja, é preciso **abrir o anexo** antes de saber onde salvá-lo.
- Salvar no servidor do WebFat virou obrigatório, além da pasta de rede.
- Reenvio com mesmo nome: sobrescreve e reinicia o processamento, respeitando a regra de corte.

**Pendência bloqueante.** ⚠️ A **data de corte** está "em análise pela área cliente". Sem ela, não há como fechar o critério de periodicidade nem o gatilho de batimento. O critério antigo ("varredura diária após o dia 05") perdeu sustentação: o parágrafo de periodicidade foi removido da V2.

**Por que é um RPA separado.** Depende de evento externo e precisa **esperar** uma janela de tempo. Se estivesse junto do processamento em lote, ou bloquearia o lote esperando e-mail, ou rodaria com dados incompletos.

---

## ÉPICO 2 — Validação dos Arquivos de Detraf

**Responsabilidade.** Garantir que cada arquivo — tanto o da operadora quanto o de expectativa gerado pelo ICT — obedece ao layout e às regras regulatórias antes de qualquer comparação.

**Gatilho.** Lote, disparado após a data de corte.

**Entradas.** Arquivos de "Detrafs Recebidos" (operadora) e arquivos convertidos de expectativa que contenham **`_D_`** no nome.

**Saídas.**
- `tbl_rpa_log_detraf_despesa_arquivos` populada, com `tipo_registro` = `DETRAF` (dados da operadora, sempre consolidados), `EXPECTATIVA` (validado sem erro) ou `ERRO`
- Arquivos `_ERRO` com os registros que falharam
- Arquivos `_BK` para o caso SMP não-PMS
- Sinalização visual em vermelho no WebFat para o analista

**HUs.** HU-04 (validação estrutural), HU-05 (tarifa regulada), HU-06 (arquivo `_BK`), HU-07 (erro L-L), HU-08 (registro no WebFat).

**Regras centrais.** Layout de 15 colunas; descritores derivados do tipo de serviço da EOT no Anexo 5; tarifas reguladas consultadas em `tbl_detraf_tarifas` por remuneração × região × grupo horário × período, com dupla convivência em fevereiro. Detalhe completo em [`regras-de-negocio-consolidadas.md`](regras-de-negocio-consolidadas.md).

**O que mudou na V2.**
- A regra de `_ERRO` **deixou de ser específica e virou geral**: qualquer regra violada joga os registros num arquivo de mesmo nome com sufixo `_ERRO`. Com isso, a **HU-07 perde razão de existir separada** — o caso L-L/STFC não tem mais tratamento diferenciado.
- Tratamento de erro no arquivo de expectativa mudou de "correção manual ou abertura de chamado" para "**avalia possível correção automática**". ⚠️ Não está claro se isso é decisão de produto ou intenção de redação.
- A relação descritor × remuneração passa a ser consultada em `tbl_detraf_mapeamento_descritores`.

**Assimetria importante entre operadora e expectativa.** Erro no arquivo **da operadora** → aciona a operadora por e-mail para corrigir. Erro no arquivo **de expectativa** → fica no WebFat para a área usuária tratar. São dois caminhos de tratamento distintos para a mesma validação.

---

## ÉPICO 3 — Batimento Detraf × Expectativa

**Responsabilidade.** Consolidar os dados de operadora e expectativa lado a lado, sumarizar, calcular a variação e apontar o que precisa de contestação. Termina em **decisão humana**.

**Gatilho.** Conclusão da validação do Épico 2 (mesmo lote).

**Entradas.** Dados validados da operadora e da expectativa Vivo, sem as linhas de total (`Rel = 1`).

**Saídas.**
- `tbl_rpa_log_detraf_despesa_contestacao` populada
- Flag `S`/`N` por combinação de EOT devedora × tipo de tarifação × mês de tráfego
- Aba "Contestação" do WebFat exibindo os casos ao analista

**HUs.** HU-09 (consolidação), HU-10 (análise por EOT e remuneração), HU-11 (exibição ao analista).

**Regra de corte.** Comparam-se os sumarizados de `Minutos` e `R$_Bruto`. Se a diferença do `R$_Bruto` for **menor que 1%**, segue sem contestação e vai direto para carga no AGI. Se for **igual ou superior**, cria-se a contestação.

⚠️ Divergência de borda: a V2 diz "se a diferença for **menor que 1%**, segue sem contestação"; o PDF de HUs diz "< 1% → N" e "≥ 1% → S"; e o texto da V2 sobre a fórmula da aba `Contest` diz "se a variação for **maior que +1%** marca S". Os três não fecham no ponto exato de 1% nem no sinal. Registrado como pendência.

**O que mudou na V2.** Mudança de artefato, não de lógica: nada de planilha `Base_Contestação` com abas e tabelas dinâmicas — "**não é necessário gerar o arquivo, mas usar a lógica e popular a tabela** `tbl_rpa_log_detraf_despesa_contestacao`". A aba `Contest` vira registro em banco; a "cava Expectativa" (erro de digitação da doc antiga) vira "aba Contestação" no WebFat.

**Ponto de sincronização humana.** A HU-11 estabelece que o RPA **só prossegue após sinalização explícita do analista**, que escolhe quais linhas contestar e se será com ou sem retenção. Este é o corte entre o RPA 2 e o RPA 3.

---

## ÉPICO 4 — Geração de Arquivos para Contestação e Carga AGI

**Responsabilidade.** Materializar a decisão do analista em artefatos: arquivos para o AGI, arquivo e carta para a operadora, e o consolidado de contestação.

**Gatilho.** Sinalização do analista no WebFat.

**Entradas.** Decisão do analista (contestar ou não; com ou sem retenção) + dados de `tbl_rpa_log_detraf_despesa_contestacao`.

**Saídas.**

| Artefato | Quando é gerado |
|---|---|
| `DE_AGI_D_{aaaamm}_TBRA_X_{operadora}_EXT` | **todos** os cenários |
| `DE_AGI_D_{aaaamm}_TBRA_X_{operadora}_INT` | **apenas** contestação COM retenção |
| `Base Contestação_{operadora}_{mês}_ENV` | contestação COM e SEM retenção |
| Carta CT numerada | contestação COM e SEM retenção |
| E-mail à operadora | contestação COM e SEM retenção |
| `CONT_PROC_MASCARA_{operadora}_{aaaamm}.xls` | contestação COM e SEM retenção |

Mais a atualização do campo `tipo_contestacao` em `tbl_rpa_log_detraf_despesa_contestacao`.

**HUs.** HU-12 (`_EXT`), HU-13 (`_INT`), HU-14 (`_ENV` + carta), HU-15 (e-mail), HU-16 (`CONT_PROC`).

**Decisões que o robô toma neste épico.** Contestação por **Referência** ou por **Tráfego**; **modalidade** (colunas I/J/K da aba `Remuneração` do `CONT_PROC_MASCARA`); **com ou sem retenção** (decidido pelo analista, executado aqui). É também aqui que ele identifica se há **retificação** a fazer — que é desviada para o Épico 6/RPA 4.

**Detalhe de estado externo.** A numeração da carta vem de um **contador em pasta de rede** (`\\lagoa\...\Correspondências Enviadas\CT\{ano}`): lê a última numeração e usa a seguinte. ⚠️ É estado compartilhado fora do banco — condição de corrida se dois processos rodarem juntos. Ver riscos.

**Pendência.** ⚠️ HU-15: o critério "disparo automático sem aprovação manual" se apoia numa frase que **só sobrevive no bloco de texto duplicado/antigo** no fim da V2. Precisa de confirmação da área cliente antes de ser mantido.

---

## ÉPICO 5 — Carga no AGI

**Responsabilidade.** Subir no AGI, por automação de interface, os arquivos produzidos no Épico 4.

**Gatilho.** Conclusão da geração dos arquivos (mesmo fluxo do Épico 4).

**Entradas.** `_EXT`, `_INT` (quando existir) e `CONT_PROC_MASCARA_{operadora}_{aaaamm}`.

**Saídas.** Dados carregados no AGI; campo `carga_agi` atualizado em `tbl_rpa_log_detraf_despesa_contestacao` com o status da carga.

**HUs.** HU-17 (Detraf > Importar Dados — `_EXT` e `_INT`, um de cada vez), HU-18 (Contestação > Gerenciar — `CONT_PROC`, com clique em Salvar).

⚠️ **Lacuna estrutural: este épico não consta em nenhum dos seis projetos de origem.** É responsabilidade explícita do RPA 3 no relatório de separação, mas nenhum projeto foi indicado como dono do código. Três hipóteses, todas a confirmar na análise dos fontes:
1. o código está embutido no Projeto 4 (que gera os arquivos carregados);
2. existe um sétimo projeto ainda não mencionado;
3. HU-17/HU-18 ainda não foram implementadas.

⚠️ Além disso, a V2 cita um arquivo **`DE_EBT_TBRA_TLF_202509_C_INT_MODELO.xlsx`** na etapa de carga, antes de `_EXT`/`_INT`, **sem explicar seu papel**. Ele aparece só no corpo principal (não no bloco duplicado), então é conteúdo novo da V2.

**Nota do relatório de separação.** Sugere-se avaliar isolar a carga no AGI como etapa própria dentro do RPA 3, para permitir reprocessar a carga sem reenviar carta e e-mail — o que é irreversível. ⚠️ Decisão que depende da análise do código e do histórico de estabilidade do AGI.

---

## ÉPICO 6 — Encontro de Contas

**Responsabilidade.** Fechar o ciclo: alimentar o Encontro de Contas, conferir contra o AGI e retificar contestações de meses anteriores quando houver recuperação de tráfego.

**HUs.** HU-19 (preenchimento do EC), HU-20 (verificação do Relatório Receitas e Despesas), HU-21 (retificação).

⚠️ **Este épico se divide entre dois RPAs.** HU-19 e HU-20 seguem o ciclo mensal e pertencem ao RPA 3. HU-21 responde a uma condição assíncrona e é o RPA 4 inteiro. Como HU-20 e HU-21 estão **no mesmo projeto de origem (P6)**, esse projeto precisará ser cindido na unificação.

### HU-19 — Preenchimento do EC (RPA 3)

Pega o valor total de despesa apresentado pela operadora (minutos e valor bruto), aberto por EOT Vivo e tipo de remuneração, **sempre com sinal negativo**.

**O que mudou na V2.** Deixou de colar na planilha de Encontro de Contas: agora atualiza `tbl_rpa_log_detraf_despesa_contestacao` nos campos `minutos_operadora`, `vb_operadora`, `minutos_diferenca`, `vb_diferenca`, `minutos_variacao_perc`, `vb_variacao_perc`.

⚠️ O critério "coluna de contestação preenchida quando houver retenção" **só aparece no bloco duplicado/antigo** da V2. Não se sabe se foi absorvido pelos novos campos ou se ficou pendente.

### HU-20 — Verificação do Relatório Receitas e Despesas (RPA 3)

Acessa `AGI > Relatórios > Detraf > Receitas e Despesas`, filtra por período, natureza "D" e operadora, sumariza `Vlr. Bruto` e compara com o subtotal de despesa do EC. Repete para todas as operadoras.

**Novo na V2:** comparar também as colunas **CBS, IBS MUNICIPAL e IBS ESTADUAL**.

⚠️ A própria V2 questiona esta HU: *"Caso a conferência com o robô dê errado, qual o processo? Esse processo trata-se de uma dupla checagem, conferir com o solicitante se esse processo vale a pena ou não ser mantido."* Ou seja, **a HU-20 pode ser descartada**. Antes de investir na unificação do código do P6, confirmar se ela continua no escopo.

### HU-21 — Retificação de contestação (RPA 4)

Existe **apenas** quando o robô identifica que um tráfego contestado em mês anterior foi recuperado no mês seguinte (variação negativa). Entra no AGI em `Contestação > Gerenciar`, filtra pela contestação já inserida, seleciona o ID Processo e adiciona um evento **"Recuperação"**:

| Campo | Valor |
|---|---|
| Duração | minutos da diferença |
| Valor Líquido | `VB × 0,9635` |
| Valor PIS/Cofins | `VB − Valor Líquido` |
| Valor Bruto Negociado | `VB` |

⚠️ A V2 sinaliza uma pendência própria no filtro por empresa: *"Operadoras que no anexo 5 possui um nome que sofrem alterações durante o processo, esse ponto de atenção precisa ser estudado. Pendência Vivo para mapear essa ponta."* Ou seja, o nome da operadora pode mudar entre o mês da contestação e o mês da retificação — e não há regra definida para isso.

---

## Escopo novo da V2 sem épico nem HU

**CBS / IBS Municipal / IBS Estadual.** Três colunas novas em arquivos de Detraf Vivo, Carga Geral do AGI e relatórios do AGI. Informativas em 2026; recolhimento a partir de 2027. Afetam layout (Épico 2), possivelmente a comparação (Épico 3) e explicitamente a conferência (HU-20).

A `Analise_Mudancas_V2_por_Historia.md` sugere criar uma **HU-22 — Tratamento das colunas de novos impostos (CBS/IBS)**. Isso ainda não foi feito. ⚠️ Nenhum projeto de origem foi indicado como responsável por esse escopo.
