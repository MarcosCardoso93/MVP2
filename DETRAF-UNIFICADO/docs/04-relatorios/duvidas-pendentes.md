# Dúvidas Pendentes

Perguntas prontas para encaminhamento, com destinatário e o que fica bloqueado até a resposta.

**Trilha P1 do roadmap.** Este encaminhamento **não depende do código** e pode começar imediatamente, em paralelo ao recebimento dos projetos.

Detalhamento de cada achado em [`relatorio-inconsistencias-e-lacunas.md`](relatorio-inconsistencias-e-lacunas.md).

---

## ✅ Rodada de decisões de 2026-07-31 — 13 pendências fechadas

Respostas do GP/dev (Btime). O que foi implementado está em
[`relatorio-unificacao-p1-a-p4.md`](relatorio-unificacao-p1-a-p4.md).

| # | Pergunta | Decisão |
|---|---|---|
| Q1 | Data de corte | ⬜ **em análise** — segue bloqueada |
| Q2b | Borda de 1% | `>=`, como já estava |
| Q3 | Épico 5 | ✅ **RESOLVIDA (2026-08-04)** — chegou como Projeto 7 |
| Q5 | Envio automático HU-15 | **Rascunho por padrão**, com flag no `.env` para ligar o envio — igual ao adotado no RPA 2 |
| Q6 | CBS / IBS | ⬜ **precisa de detalhamento** — ver abaixo |
| Q7 | HU-20 | Será adicionada depois (P6) |
| Q8 | EC no RPA 2 ou 3 | **RPA 3** — o RPA 2 grava o baseline, o RPA 3 atualiza após a decisão do analista |
| Q9 | Tarifas não reguladas | **Só formato.** ✅ Verificado: já era assim — `__filtrar_tarifas_remuneradas` só manda as reguladas para validação de valor |
| Q11 | Coluna W do `CONT_PROC` | ✅ **respondida pelo código** — usa `vb_diferenca` (valor), não minutagem |
| Q12 | Descritores de transporte | ⬜ **precisa de detalhamento** |
| Q13 | Correção automática | **Ignorar** — sai do escopo |
| Q14 | `DE_EBT_..._MODELO.xlsx` | **Ignorar** — sai do escopo |
| Q15 | Local × WebFat × Lagoa | **Sempre local.** A gravação no servidor do WebFat **sai do escopo** da HU-03 |
| Q16 | Exceções da HU-02 | ⬜ **precisa de detalhamento** |
| Q17 | Nome de operadora que muda | ⬜ **precisa de detalhamento** |
| Q18 | Numeração CT | **Não pode duplicar.** Último número da pasta + 1; se não conseguir identificar por qualquer motivo, **acusa o erro** |
| Q19 | Escopo do WebFat | Decisão do analista vem de **coluna no banco**. ✅ Já implementado — `tipo_contestacao` |
| Q20 | Ambiente de teste | **Não existe** para banco/e-mail; validação só com mocks. 🆕 Para o **AGI existe homologação** — ver Q20b |
| Q21 | Pastas VIVO / TLF | **Ignorar** |
| Q23 | Demandas irmãs | **Ignorar** |
| N1 | Nome da tabela de log | **Usar o da V2** — `tbl_rpa_log_detraf_despesa_arquivos` |
| N3 | Expectativa sem `R$_Bruto` | **Layout da V2 vale para os dois** tipos de arquivo; o que não bater é rejeitado |
| N7 | Colunas do `CONT_PROC` | **Seguir a documentação** |

### 🔴 Consequências que precisam ser comunicadas

**1. O RPA 2 vai rejeitar todos os arquivos de expectativa atuais.** A decisão
sobre N3 manda validar o layout da V2 nos dois tipos de arquivo. O arquivo de
expectativa Vivo real não conforma em nenhum campo — será rejeitado com
`EXPECTATIVA_ERRO` e diagnóstico no log. **Não haverá comparação nem
contestação** até a geração ser corrigida no ICT. É o comportamento pedido, e é
melhor que comparar coluna errada em silêncio.

**2. O nome de tabela da V2 não existe em nenhum banco conhecido.** Os três
SQLite que vieram com os projetos só têm `tbl_detraf_despesa_arquivos`. **Se o
MySQL de produção usar o nome antigo, o RPA 1 e o RPA 2 falham ao gravar.**
Confirmar com o DBA antes de subir. Para dev, `preparar_banco_dev.py` gera o
banco com o nome certo.

**3. Sem ambiente de teste**, o envio de e-mail à operadora, a carga no AGI e a
retificação **não podem ser exercitados de verdade antes de produção**.

### ⬜ As quatro que precisam de detalhamento

| # | O que falta |
|---|---|
| **Q6** — CBS/IBS | Onde ficam no layout (16-18 ou deslocam?), se o arquivo da operadora também as terá, se entram na comparação, a partir de qual mês. **Afeta a validação de layout recém-implementada** — ela hoje espera no mínimo 15 colunas e valida as 15 primeiras; se os impostos entrarem no meio, ela passa a rejeitar arquivos válidos |
| **Q12** — Descritores de transporte | Existe tráfego de transporte na despesa? Como identificá-lo pelo descritor? As colunas `CORREDOR_TRANSPORTE`/`TIPO_TRANSPORTE` do arquivo Vivo são a fonte? |
| **Q16** — Exceções da HU-02 | O que fazer com arquivo corrompido, coluna Credora vazia, EOT fora do Anexo 5, e-mail com várias operadoras. E: a tabela de contatos do WebFat ainda existe? A HU-15 precisa dela |
| **Q17** — Nome de operadora que muda | Com que frequência acontece? O AGI filtra por EOT em vez de nome? Existe histórico de nomes no Anexo 5? |

## ✅ Rodada de decisões de 2026-08-10 — auditoria de cobertura das 21 HUs

Levantamento HU a HU do que a documentação exige contra o que os quatro robôs
fazem. **Nenhuma HU estava inteiramente ausente**; as lacunas eram internas.
Respostas do GP (Btime) na mesma data.

### Corrigido no código

| # | Achado | Decisão |
|---|---|---|
| **A1** | Reenvio de arquivo com o mesmo nome **nunca era reprocessado** — o histórico comparava só o caminho, e a correção da operadora era ignorada em silêncio (quebrava critério da HU-03) | ✅ **corrigido** — tamanho e data de modificação entram na comparação; ver `tests/test_historico_reenvio.py` |
| **A2** | RPA 1 e RPA 2 gravavam **duas linhas** para o mesmo arquivo válido, a do RPA 1 com seis campos zerados | ✅ **corrigido** — o RPA 1 deixou de gravar o arquivo válido. Regra: *ele só grava o que só ele sabe* |
| **A6** | Arquivo com EOT não identificada **sumia do WebFat** — nem verde nem vermelho | ✅ **corrigido** — passa a gravar com `tipo_registro='ERRO'` e `status='Não validado'` |
| **A4** | O fluxo `_BK` rodava só na expectativa; a HU-06 diz *"vale tanto para o arquivo da operadora quanto para o de expectativa Vivo"* | ✅ **corrigido** — passou a valer para os dois |

### Mantido como está, por decisão

Registrado para **não voltar como achado** na próxima auditoria.

| # | Achado | Decisão |
|---|---|---|
| **A3** | `detectar_linhas_vermelhas` nunca é chamado (parecia código morto) | **Não é do fluxo de Despesa** — é função do processo de Receita, que veio junto na migração. Não ligar |
| **A5** | A EOT da operadora é lida de **uma linha só**; arquivo com credoras diferentes vai inteiro para a primeira | **Manter.** Cenário não observado na prática |
| **A7** | A captura não filtra por mês de referência — e-mail antigo reposto é processado | **Manter.** É tolerância deliberada com o atraso da operadora: Detraf fora do prazo ainda entra |
| **B1** | A flag `S`/`N` da HU-10 é calculada e descartada (não há coluna no banco) | **Não pedir coluna.** A tela do WebFat aplica a regra de 1% sobre `vb_variacao_perc` |
| **B4** | HU-20 não compara CBS/IBS, só soma e loga | **Manter**, junto com a Q6 |
| **C1** | Salvamento no servidor do WebFat: documentação se contradiz | **Fora do escopo** — só local. É a leitura que o código já implementa |
| **C2** | Coluna 7 (descritor × remuneração do nome do arquivo) não é validada | **Não implementar** |
| **C3** | O Detraf da operadora é reprovado inteiro, sem `_ERRO` por registro | **Manter.** A separação linha a linha é só da expectativa |
| **C4** | A validação de tarifa ignora `eot_vivo`/`eot_operadora` e aceita a tarifa de qualquer par | **Ignorar essas colunas** — segue como está |
| **C5** | EOTs fixas da Vivo não consolidadas; nada decide Referência × Tráfego | **Manter** |
| **C6** | `CONT_PROC` sai `.xlsx` e sem usar a máscara | **Manter** |
| **C7** | Destinatários do e-mail vêm de um CSV de ponte, não do WebFat | **Manter** |
| **C10** | "Resposta da operadora à contestação" não existe no código | **Fora do escopo** |
| **C11** | O consolidado do Encontro de Contas não é persistido | **Manter como tabela** — é o destino, não a planilha |
| **D1** | O `.env` está versionado, com credenciais | **Continuar rastreando o `.env`** |

### ⬜ As quatro que a HU-21 trouxe (2026-08-10)

Nenhuma é defeito do robô: as quatro vieram declaradas como incertas no código de
origem, e a migração as preservou em vez de escolher por conta própria.

| # | O que falta |
|---|---|
| **Q26** — `carga_agi` tem dois donos | 🔴 **Decidido em 2026-08-10: fica como está.** O RPA 3 grava `'carregado'` quando o CONT_PROC sobe (HU-18); o RPA 4 usa o mesmo valor para dizer "já retifiquei", e procura por `carga_agi != 'carregado'`. **Consequência aceita: toda linha que o RPA 3 carregou fica invisível para o RPA 4** — na prática a HU-21 só enxerga meses em que a carga falhou. Reverter pede `retificacao_agi varchar(50)` e um `ALTER TABLE` |
| **Q27** — O que define "tráfego recuperado" | **Decidido: fica como está** — só `vb_variacao_perc < 0`. `minutos_variacao_perc` não entra |
| ~~**Q28**~~ — `vb_diferenca` × "Valor Bruto" do CSV | ✅ **RESOLVIDA (2026-08-10).** Confirmado pelo GP: os dois **são comparáveis**, e o cruzamento por EOT + Referência + Tráfego + Valor está correto |
| **Q29** — Nada confirma o evento no AGI | Depois do clique em Salvar o AGI não devolve sinal nenhum. O robô marca a linha e segue. Se o AGI recusou, a linha fica marcada como feita; se a execução morre no meio, reexecutar **duplica** o evento — que é irreversível. Existe alguma tela ou consulta que confirme o lançamento? |
| **Q30** — Controle de reenvio do e-mail (HU-15) | A HU diz que o e-mail sai *"automaticamente após a sinalização do analista"*, mas o RPA 3 roda por agenda: toda execução releria as mesmas linhas marcadas e reenviaria à operadora. Hoje o envio só acontece na execução que gerou os artefatos — se o analista marcar depois, **ninguém envia**. Uma coluna `email_enviado_em datetime` fecharia isso (mesmo padrão do `carga_agi`). Sem ela, o envio automático não pode existir sem risco de reenvio |

---

## ⚠️ Atualização de 2026-07-31 — o que a análise dos Projetos 1 a 4 resolveu

| # | Situação após a análise |
|---|---|
| **Q2** — regra de 1% | ✅ **DECIDIDA pela documentação** (ver bloco abaixo). Resta só a borda `>` vs `>=` |
| **Q3** — onde está o Épico 5 | ✅ **RESOLVIDA (2026-08-04)** — era a hipótese 2: existe um sétimo projeto, e ele foi entregue |
| **Q4** — `_ENV` × `Base_Contestação` | ✅ **RESPONDIDA pelo código** — o P3 gera a planilha **e** grava no banco |
| **Q10** — recálculo do total no `_BK` | ✅ **RESPONDIDA pelo código** — o P2 **recalcula** (`_adicionar_linha_total`) |
| **Q13** — correção automática | ✅ **continua aberta, sem decisão silenciosa** — nenhum código a implementa |
| **Q18** — trava na numeração CT | ⚠️ **confirmado que não há trava** no P4 |
| **Q22** — DDL das tabelas | ⚠️ **parcialmente respondida** — ver divergência de nomes abaixo |

### Q2 — decidida pela documentação

O P3 e o P4 implementaram a regra de formas incompatíveis. A V2 resolve dois dos três aspectos:

| Aspecto | Decisão | Fundamento |
|---|---|---|
| Base do percentual | **lado operadora** | *"A origem dos dados é o Detraf 'oficial' enviado para a Vivo pela operadora"* |
| Par ausente (sem expectativa) | **contesta** (100%) | *"apresentar os valores zerados de expectativas. Os dados da operadora são considerados"* |
| Sinal | **importa** — só contesta se cobrou a mais | *"se a variação for maior que **+1%**"*; variação negativa tem destino próprio (retificação, HU-21) |

**Pendência residual:** a V2 diz *"se for **superior**"* (`> 1%`), mas P3, P4 e o PDF de HUs usam `>= 1%`. Só se manifesta em exatamente 1,000000%. Adotado `>=`; confirmar com o PO.

### Novas divergências que o código revelou

| # | Divergência | Quem decide |
|---|---|---|
| **N1** | Nome da tabela de log: código usa `tbl_detraf_despesa_arquivos`; a V2 documenta `tbl_rpa_log_detraf_despesa_arquivos` | PO / DBA |
| ~~**N2**~~ | ~~Nome da tabela de descritores~~ — **anulada.** Verificação posterior mostrou que `tbl_mapeamento_descritores` e `tbl_contestacao` no P4 são nomes de **atributo**, não de tabela. Os quatro projetos usam os mesmos cinco nomes de tabela | — |
| **N3** | O arquivo de **expectativa Vivo** tem layout próprio e **não possui coluna `R$_Bruto`** — termina em `VALOR_LIQUIDO`. Mas a comparação da HU-10 é sobre `R$_Bruto` | PO / área cliente |
| **N4** | `tipo_lote` do P2 tem 4 valores (`DETRAF_SUCESSO`, `DETRAF_ERRO`, `EXPECTATIVA_SUCESSO`, `EXPECTATIVA_ERRO`) contra 3 de `tipo_registro` na V2 | PO |

**N3 é a mais séria** — ver [`../../trabalho/inventarios/inventario-projeto-3.md`](../../trabalho/inventarios/inventario-projeto-3.md) §4.

---

## Como usar

Cada pergunta traz: o texto da fonte que a origina, a pergunta objetiva, o que fica bloqueado, e quem decide. Preencher **Resposta** e **Data** conforme forem respondidas.

Destinatários (conforme a V2):

| Sigla | Papel | Nome |
|---|---|---|
| **PO** | Product Owner, área cliente | Ana Carolina da Silva |
| **GER-AC** | Gerente, área cliente | Alan Ramos Baptista |
| **GP-Vivo** | GP, GSA | Luciana Santos Vargas |
| **GP-Btime** | GP, Btime | Ekiton Gomes |
| **DEV** | Desenvolvedor | Elias Leite |

---

# 🔴 Bloqueantes

## Q1 — Qual é a data de corte?

**Fonte.** V2: *"Data de corte do processo está em análise pela área cliente para termos a regra de reprocessamento e gatilho para batimento da operadora."*

**Perguntas.**
1. Qual é a data de corte do mês?
2. É data fixa (ex.: dia 10) ou depende de um evento?
3. O que acontece com arquivos que chegam **depois** do corte — descartados, guardados para o mês seguinte, reabrem o processamento?
4. Qual é o "gatilho para batimento da operadora" mencionado?
5. Quando a mesma operadora envia vários e-mails no mês, qual prevalece?

**Bloqueia.** Periodicidade da HU-01; gatilho do RPA 2; regra de reprocessamento; marcos M5 e M6.

**Decide.** PO / GER-AC

**Resposta:** _______ **Data:** _______

---

## Q2 — Qual é exatamente a regra de 1%?

**Fonte.** Três textos divergentes — ver achado 2 do relatório de inconsistências.

**Perguntas.**
1. Contesta-se quando a variação é **maior que 1%** ou **maior ou igual a 1%**?
2. O **sinal** importa? Ou seja: contesta-se apenas quando a operadora cobrou **a mais** que a expectativa, ou também quando cobrou a menos?
3. O percentual é calculado sobre o valor **da operadora** ou sobre o valor **da expectativa Vivo**?
4. Quando não há expectativa (valores zerados pela regra da V2), a variação é 100% e vai automaticamente para contestação. Isso é o desejado?

**Bloqueia.** A decisão S/N do RPA 2 — a regra financeira central do processo. Marco M6.

**Decide.** PO / GER-AC

**Resposta:** _______ **Data:** _______

---

## Q3 — Onde está o código do Épico 5 (HU-17 e HU-18)?

**Fonte.** A divisão dos seis projetos não contempla o Épico 5.

**Perguntas.**
1. O código de upload no AGI (`Detraf > Importar Dados` e `Contestação > Gerenciar`) está dentro do Projeto 4?
2. Existe um sétimo projeto não mencionado?
3. Ou HU-17/HU-18 ainda não foram implementadas?

**Bloqueia.** Composição do RPA 3. Marco M8. Se não estiver implementado, parte de M8 vira desenvolvimento, não migração.

**Decide.** GP-Btime / DEV

**Resposta (2026-08-04): era a hipótese 2.** Existe um sétimo projeto,
`projeto-7-epico-5-carga-agi/`, entregue nesta data e já migrado para o RPA 3. A
hipótese 1 estava eliminada desde a leitura do P4, que não tem nenhuma automação
de interface.

⚠️ **Parte de M8 vira desenvolvimento assim mesmo**, como o registro previa — só
que menos do que se temia:

| HU | Estado |
|---|---|
| HU-17 | mecânica de upload pronta; **falta a regra de cenário** (EXT sempre, INT só COM retenção) |
| HU-18 | as 4 imagens foram capturadas e a navegação foi escrita na migração, mas **nunca executou** contra o AGI |

Ver `trabalho/inventarios/inventario-projeto-7.md`.

---

## Q4 — O `_ENV` vem do arquivo `Base_Contestação` ou do banco?

**Fonte.** HU-09 diz que a `Base_Contestação` não é mais gerada como arquivo; HU-14 define o `_ENV` como cópia dela.

**Perguntas.**
1. A `Base_Contestação_..._M` continua existindo como arquivo, só para gerar o `_ENV`?
2. Ou o `_ENV` passa a ser gerado do zero a partir do banco?
3. Ligado a isso: **quais são os "dois arquivos"** da frase *"todas as planilhas foram substituídas por banco, exceto dois arquivos"*? O fluxo descreve cinco (`_EXT`, `_INT`, `_ENV`, carta, `CONT_PROC`).

**Bloqueia.** HU-14 e, por consequência, HU-15. Marco M8.

**Decide.** PO

**Resposta:** _______ **Data:** _______

---

## Q5 — O e-mail de contestação é enviado sem aprovação do usuário?

**Fonte — CORRIGIDA em 2026-08-04.** Este item dizia que a frase "sobrevive no
bloco de texto antigo ao final do documento". **Não sobrevive em bloco nenhum:**
a busca por `aprova|analista|sinaliza|automátic` na V2 inteira, incluindo o bloco
duplicado, não encontra nada sobre envio automático ou dispensa de aprovação. O
único texto correlato é o ¶437: *"O analista define se será com contestação ou
não."*

A frase é da **V1** (`DETRAF_MVP2_Historias.pdf`, HU-15): *"Automaticamente após a
sinalização do analista (…) Não requer aprovação manual adicional."*

Atribuir à V2 algo que é da V1 é o erro que a Q24 existe para evitar.

**Perguntas.**
1. O robô envia o e-mail de contestação à operadora **automaticamente**, sem aprovação adicional após a sinalização do analista?
2. Ou passou a exigir uma aprovação explícita antes do envio?
3. Se automático: há alguma condição em que o envio deve parar para revisão humana (valor acima de um limiar, operadora específica, primeira contestação do ciclo)?

**Por que importa.** O envio é irreversível e externo. Uma contestação enviada por engano tem consequência comercial.

**Bloqueia.** Fluxo do RPA 3. Marco M8.

**Decide.** PO / GP-Vivo — **por escrito**

**Resposta:** _______ **Data:** _______

---

## Q6 — Como tratar CBS, IBS Municipal e IBS Estadual?

**Fonte.** V2 afirma que as três colunas existem em Detraf Vivo, Carga Geral do AGI e relatórios, e manda compará-las na HU-20. Mas o layout das 15 colunas não as inclui e não há HU.

**Perguntas.**
1. Onde as colunas ficam no layout — são 16, 17 e 18, ou deslocam as existentes?
2. O arquivo **da operadora** também as terá, ou apenas o Detraf Vivo?
3. Elas entram na validação estrutural (HU-04)?
4. Entram na sumarização e comparação da HU-10, ou são apenas informativas?
5. A partir de qual mês de referência passam a ser obrigatórias?
6. Como se relacionam com o PIS/Cofins e o ICMS existentes — somam, substituem, convivem?
7. Qual projeto de origem (se algum) é responsável por esse escopo?

**Bloqueia.** Layout de arquivo, validação, comparação e HU-20. Marco M6.

**Decide.** PO / GER-AC, com apoio da área fiscal

**Resposta:** _______ **Data:** _______

---

# 🟡 Alta prioridade apesar da severidade média

## Q7 — A HU-20 continua no escopo?

**Fonte.** V2: *"Esse processo trata-se de uma dupla checagem, conferir com o solicitante se esse processo vale a pena ou não ser mantido."*

**Perguntas.**
1. A verificação do Relatório de Receitas e Despesas continua no escopo?
2. Se sim: **o que o robô faz quando os valores divergem**? Só sinaliza, ou há tratamento?
3. Se sim: qual é o destino do valor consolidado do EC, já que a planilha foi substituída por banco e a referência à "célula O87" não sobrevive?

**Bloqueia.** A **cisão do Projeto 6**. Se descartada, o P6 fica reduzido à HU-21 e o marco M7 simplifica muito.

**Urgência.** Responder **antes** de M7, que vem antes de M8.

**Decide.** PO / GER-AC

**Resposta:** _______ **Data:** _______

---

# 🟡 Médias

## Q8 — O Encontro de Contas é preenchido logo após a validação ou depois da contestação?

**Fonte.** A V2 diz *"Após a validação de cada arquivo, deve-se popular o Encontro de Contas..."* (o que seria RPA 2), mas a HU-19 e o relatório de separação colocam o EC no RPA 3.

**Perguntas.**
1. São dois momentos distintos — o valor da operadora logo após a validação, e o valor da contestação depois?
2. Ou é a mesma operação descrita duas vezes?
3. Se forem dois, o EC é escrito por **dois RPAs diferentes**?

**Bloqueia.** Posicionamento da HU-19; fronteira RPA 2 / RPA 3.

**Decide.** PO

**Resposta:** _______ **Data:** _______

---

## Q9 — Tarifas não reguladas: valida o valor ou apenas classifica?

**Fonte.** V2 diz que não são validadas em conteúdo, mas também que "a consulta de tarifas não reguladas é realizada através da tabela de tarifas".

**Pergunta.** A tabela `tbl_detraf_tarifas` serve apenas para **classificar** (descritor presente = regulada), ou há alguma validação de valor para as não reguladas?

**Bloqueia.** HU-05.

**Decide.** PO

**Resposta:** _______ **Data:** _______

---

## Q10 — O arquivo `_BK` recalcula a linha de total?

**Fonte.** O PDF de HUs exige recálculo; a V2 diz apenas "criar a cópia, sem alarme".

**Pergunta.** O arquivo `_BK` deve ter a linha de total recalculada, ou é cópia idêntica do original?

**Bloqueia.** HU-06.

**Decide.** PO

**Resposta:** _______ **Data:** _______

---

## Q11 — A coluna W do `CONT_PROC` recebe valor bruto ou minutagem?

**Fonte.** V2: *"Coluna W: 'VLR_BRUTO' - preencher com a **minutagem** total da linha."* Texto idêntico ao da coluna I (`DURACAO`).

**Pergunta.** Confirmar que a coluna W recebe o **valor bruto** (com sinal negativo), e que o texto da V2 é erro de redação.

**Bloqueia.** HU-16. É confirmação, não deliberação — mas envolve dado financeiro carregado no AGI.

**Decide.** PO

**Resposta:** _______ **Data:** _______

---

## Q12 — Qual a regra de validação dos descritores de transporte?

**Fonte.** V2: *"Descritores de transporte devem ser validados a partir da tabela Descritor_Remuneração (aguardando informação do solicitante)."*

**Pergunta.** Qual é a regra? A própria V2 registra que está aguardando o solicitante.

**Bloqueia.** HU-05, parcialmente. E impede promover o mapeamento descritor→remuneração integralmente à base comum.

**Decide.** Solicitante / PO

**Resposta:** _______ **Data:** _______

---

## Q13 — O que é "avaliar possível correção automática" do arquivo de expectativa?

**Fonte.** V2: *"Caso o erro seja no arquivo de expectativa, avalia possível correção automática."* Na V1 era "correção manual ou abertura de chamado".

**Perguntas.**
1. Que tipos de erro são corrigíveis automaticamente?
2. Qual é a regra de correção?
3. O que acontece quando não é corrigível?
4. Isso é decisão de produto validada, ou intenção de redação?

**Bloqueia.** HU-08.

**Decide.** PO

**Resposta:** _______ **Data:** _______

---

## Q14 — O que é o arquivo `DE_EBT_TBRA_TLF_202509_C_INT_MODELO.xlsx`? — **REABERTA**

⚠️ **Esta pergunta foi marcada "Ignorar — sai do escopo" em 2026-07-31, e a
auditoria de 2026-08-04 mostrou que a decisão foi tomada sem um dado decisivo:**

O ¶652 — *"Carga dos arquivos com Detraf `DE_EBT_TBRA_TLF_202509_C_INT_MODELO.xlsx`"*
— abre a seção **Carga no AGI** no texto vigente. No bloco antigo, a mesma linha
(¶912) diz apenas *"Carga dos arquivos com Detraf `DE_AGI_D_..._EXT` e `..._INT`"*.

Ou seja: a menção ao `DE_EBT` é **a única alteração que a V2 fez naquele passo**.
Descartá-la como fora do escopo é descartar exatamente a novidade — e ela está no
caminho crítico da HU-17, que já está implementada sem ela.

O nome contém `TLF` e `INT`, o que o liga à Q21 (pastas VIVO/TLF) e à geração do
`_INT`.

**A pergunta certa:** este arquivo **substitui, precede ou acompanha** o `_INT` na
carga? Quem o produz?

**Fonte.** V2, etapa de carga, citado antes dos `_EXT`/`_INT` sem qualquer explicação.

**Perguntas.**
1. O que é esse arquivo?
2. Ele é carregado no AGI, ou serve de modelo para gerar outro?
3. Por que o período `202509` está fixo no nome?
4. Qual a relação com `TLF`?

**Bloqueia.** HU-17.

**Decide.** Área cliente / GP-Vivo

**Resposta:** _______ **Data:** _______

---

## Q15 — Memória local, servidor WebFat e Lagoa: qual é o fluxo real?

**Fonte.** V2, item 2.13: *"O robô irá atuar com a memória da máquina local. O RPA irá salvar na pasta local para que seja integrado ao Webfat. O Webfat terá a opção do analista transferir o arquivo para o Lagoa."* Mas a HU-03 manda salvar direto no Lagoa e no servidor do WebFat.

**Perguntas.**
1. O robô salva **direto** na pasta de rede Lagoa, ou salva local e o analista transfere?
2. Se o analista transfere, isso é um passo **manual** obrigatório no meio do fluxo?
3. São três locais de armazenamento (local, WebFat, Lagoa) ou dois?

**Bloqueia.** HU-03; desenho de armazenamento do RPA 1 e do RPA 3.

**Decide.** Área cliente / GP-Vivo

**Resposta:** _______ **Data:** _______

---

## Q16 — Casos de exceção da identificação da operadora (HU-02)

**Fonte.** A V2 mudou a identificação para a EOT da Credora lida **dentro do arquivo**, o que obriga a abrir o anexo antes de saber onde salvá-lo.

**Perguntas.**
1. O que fazer quando o arquivo está corrompido, protegido por senha ou não abre?
2. O que fazer quando a coluna Credora está vazia?
3. O que fazer quando a EOT não existe no Anexo 5?
4. E se um e-mail trouxer anexos de **mais de uma operadora**?
5. A "tabela de contatos do WebFat" ainda existe? A HU-15 precisa dela para os destinatários.

**Bloqueia.** Casos de exceção da HU-02 e da HU-15.

**Decide.** PO

**Resposta:** _______ **Data:** _______

---

## Q17 — Como tratar operadoras cujo nome muda entre a contestação e a retificação?

**Fonte.** V2, HU-21: *"Operadoras que no anexo 5 possui um nome que sofrem alterações durante o processo, esse ponto de atenção precisa ser estudado. **Pendência Vivo para mapear essa ponta.**"*

**Pergunta.** Já existe encaminhamento para essa pendência? O filtro do AGI é por nome — se o nome mudou, o robô não encontra o processo da contestação anterior.

**Bloqueia.** HU-21 e, portanto, o RPA 4. Marco M7.

**Decide.** Vivo — já registrado como pendência deles

**Resposta:** _______ **Data:** _______

---

## Q18 — A numeração CT pode ser consumida por mais de um processo ao mesmo tempo?

**Fonte.** V2, HU-14: o robô lê a última numeração numa pasta de rede e usa a seguinte.

**Perguntas.**
1. Alguém além do robô cria cartas nesse controle?
2. Qual a criticidade de duas cartas saírem com o mesmo número?
3. Existe algum controle hoje, ou o processo manual dependia de haver uma só pessoa fazendo?

**Bloqueia.** Não bloqueia; é risco operacional a dimensionar.

**Decide.** Área cliente (criticidade) + decisão técnica em F4 (trava)

**Resposta:** _______ **Data:** _______

---

## Q19 — O desenvolvimento do WebFat faz parte deste projeto?

**Fonte.** V2: *"No Webfat temos como sugestão a criação de uma nova tela... Para isso, uma nova tela no Webfat foi desenvolvida."*

**Perguntas.**
1. As telas do WebFat (abas Detraf e Contestação, tela de consolidado despesas) são entrega **deste** projeto ou de outra frente?
2. Se de outra frente: qual, e qual o status?
3. **Como o RPA 3 é notificado da decisão do analista** — coluna de estado no banco, fila, agendamento que consulta periodicamente?

**Bloqueia.** Gatilho do RPA 3; mecanismo de sincronização entre RPA 2 e RPA 3.

**Decide.** GP-Vivo / GP-Btime

**Resposta:** _______ **Data:** _______

---

## Q20 — Existe ambiente de teste?

**Fonte.** Necessidade da fase de validação — não é dúvida documental.

**Perguntas.**
1. Existe **ambiente de teste do AGI**?
2. Existe **caixa de e-mail de teste** para o Outlook?
3. Existe **banco WebFat de teste**?
4. É possível isolar o **contador de numeração CT**?
5. Há acesso às pastas de rede Lagoa (ou réplica de teste)?

**Por que importa.** Sem isso, os RPAs 3 e 4 só poderiam ser validados contra produção — o que significaria enviar contestações reais a operadoras e lançar valores no sistema financeiro. **É impedimento, não inconveniente.**

**Bloqueia.** Validação dos marcos M7 e M8.

**Decide.** GP-Vivo / infraestrutura Vivo

**Resposta:** _______ **Data:** _______

---

# 🟢 Baixas

## Q21 — Qual o critério de separação das pastas VIVO e TLF?

**Fonte.** V2: *"Todos os arquivos de expectativa Vivo estarão separados por pastas VIVO e TLF com 'D' no final."*

**Perguntas.** Qual o critério de separação? O que significa o "D" no final? Como se relaciona com o filtro `_D_` no nome dos arquivos?

**Decide.** PO

**Resposta:** _______ **Data:** _______

---

## Q22 — Qual é o layout completo das tabelas do WebFat?

**Fonte.** A V2 cita quatro tabelas e alguns campos, mas nunca publica o DDL.

**Pergunta.** É possível obter o DDL de `tbl_detraf_tarifas`, `tbl_detraf_mapeamento_descritores`, `tbl_rpa_log_detraf_despesa_arquivos` e `tbl_rpa_log_detraf_despesa_contestacao`?

**Por que importa.** Permite identificar, na análise do código, campos gravados que não constam da documentação.

**Decide.** GP-Vivo / DBA

**Resposta:** _______ **Data:** _______

---

## Q23 — Qual a interface com as demandas ATA0000571 / 567 / 572?

**Fonte.** V2 registra que as quatro demandas formam o fluxo completo de faturamento do Detraf, mas não descreve a interface.

**Perguntas.** Que dados são compartilhados? Há ordem de execução entre elas? O processo de captura e conversão do ICT pertence a qual delas?

**Decide.** GP-Vivo / GP-Btime

**Resposta:** _______ **Data:** _______

---

## Q24 — O bloco de texto duplicado da V2 pode ser removido?

**Fonte.** O `.docx` da V2 repete, após o item 7, um trecho de versão anterior com regras revogadas.

**Pergunta.** Pode-se emitir uma versão limpa do documento? O bloco duplicado é fonte recorrente de reintrodução de regra revogada.

**Decide.** GP-Vivo

**Resposta:** _______ **Data:** _______

---

## Painel de controle

**Fonte única do status.** Este painel esteve congelado em 2026-07-31 e passou a
contradizer o cabeçalho deste mesmo arquivo em doze linhas — corrigido em
2026-08-04, na auditoria.

| # | Pergunta | Sev. | Decide | Status |
|---|---|---|---|---|
| Q1 | Data de corte | — | GP/dev | ✅ **fechada (2026-08-05) por decisão nossa**: dia 5, o que a V1 registrava, configurável em `DETRAF_DIA_LIBERACAO` |
| Q2 | Regra de 1% | — | PO / GER-AC | ✅ decidida pela documentação; borda `>=` confirmada |
| Q3 | Onde está o Épico 5 | — | GP-Btime / DEV | ✅ **resolvida** — era a hipótese 2: existe um sétimo projeto, entregue e migrado |
| Q4 | `_ENV` × `Base_Contestação` | — | PO | ✅ **resolvida pelo cliente (2026-08-04)**: a base de contestação é uma **tabela**. O código deixou de gerar o arquivo |
| Q5 | Envio automático HU-15 | — | PO / GP-Vivo | ✅ resolvida — rascunho por padrão, com kill-switch `PERMITIR_ENVIO_EMAIL` |
| Q6 | CBS / IBS | 🟢 | PO | ✅ **layout recebido; a comparação fica para 2027 (2026-08-06)**. O EC não tem coluna de imposto, e a V2 (¶367) trata os impostos como informativos até lá. As somas passam a ser **registradas todo mês**, para a série existir quando o recolhimento começar |
| Q7 | HU-20 continua no escopo | — | GP/dev | ✅ **fechada (2026-08-05)**: fica no escopo. O `PERMITIR_ACESSO_AGI` continua, agora como proteção de ambiente (Q20), não dúvida de escopo |
| Q8 | EC no RPA 2 ou 3 | — | PO | ✅ RPA 3 |
| Q9 | Tarifas não reguladas | — | PO | ✅ **respondida pela V2** (¶181/¶182): só formato; a tabela serve para classificar, não para validar valor |
| Q10 | Recálculo no `_BK` | — | PO | ✅ respondida pela **V1** (HU-06): "linha de total recalculada" |
| Q11 | Coluna W do `CONT_PROC` | — | PO | ✅ **respondida (2026-08-06): NÃO é o valor bruto.** A coluna recebe **minutagem**, como o ¶643 diz literalmente. O código gravava `vb_diferenca` e passou a gravar `minutos_diferenca` |
| Q12 | Descritores de transporte | — | GP/dev | ✅ **fechada (2026-08-06)**: a regra já vinha aplicada do Épico 2 — `classificar_descritor_remuneracao`, por caractere inicial/final. ⚠️ A conferência revelou que ela **diverge da tabela D-5**; ver o defeito **A4** |
| Q13 | Correção automática | — | — | ✅ **fechada (2026-08-05)**: os dois ¶ seguintes ao ¶424 descrevem **tratamento humano** (expor no WebFat, alerta vermelho, seguir para o próximo). Não há correção automática — o comportamento adotado já era o certo |
| Q14 | `DE_EBT_..._MODELO.xlsx` | — | GP/dev | ✅ **fica fora de escopo (2026-08-05)**, reconfirmado sabendo que é acréscimo da V2 |
| Q15 | Local × WebFat × Lagoa | — | Área cliente | ✅ sempre local |
| Q16 | Destinatários da HU-15 | — | GP/dev | ✅ **fechada (2026-08-06)**: o CSV é a solução, não ponte. Modelo em `unificado/configuracao/contatos-operadoras.csv`, com Para, Cc e cópia fixa. ⚠️ com ele preenchido e `PERMITIR_ENVIO_EMAIL=true`, o envio é real |
| Q16b | Exceções da HU-02 | — | PO | ✅ **fechada (2026-08-06)**: EOT fora do Anexo 5 fica como está (vai para `_NAO_IDENTIFICADOS`); e-mail multi-operadora **não existe** — cada e-mail traz uma operadora só |
| Q17 | Nome da operadora muda | — | GP/dev | ✅ **fechada (2026-08-06)**: não é pendência — o caso não existe. A coluna de `ID Processo` que chegou a ser cogitada **sai do pedido de DDL** |
| Q18 | Numeração CT concorrente | — | GP/dev | ✅ **resolvida no código (2026-08-05)**: trava por arquivo (`O_CREAT\|O_EXCL`) cobrindo o par ler→gravar, com timeout e liberação garantida |
| Q19 | Escopo do WebFat | — | GP-Vivo / GP-Btime | ✅ decisão do analista vem de coluna no banco (`tipo_contestacao`) |
| Q20 | Ambiente de teste | — | GP-Vivo | ✅ **fechada (2026-08-06)**: autorização concedida. Tudo menos o AGI se isola por configuração; para o AGI há procedimento em `checklist-validacao-agi.md`, com conferência prévia das imagens. ⚠️ A **rotação das credenciais (R20)** continua sendo pré-condição da primeira execução. 🆕 **Reaberta em parte no mesmo dia:** o AGI **tem** homologação — ver Q20b |
| **Q20b** | O AGI de homologação serve? | O Portal AIR abre dois ambientes: produção (`10.238.6.120:7010/Agi/`) e **homologação** (`10.129.178.159:7010/Agi/`). A premissa de que "não existe ambiente de teste do AGI" era do lado errado: o ambiente existe. Falta saber se ele **serve**. (1) A instância de homologação tem dado de Detraf **Despesa** utilizável? (2) A credencial `RPA_DETRAF_DESPESA_AGI_USER` vale nela, ou é outra? (3) Um upload lá tem algum efeito a jusante que precise de autorização? | Área cliente / GP-Vivo | ⬜ **aberta (2026-08-06)**. Achado ao instalar o aplicativo em `unificado/aplicacao_agi/`. O robô **já sabe abrir os dois**: `AGI_AMBIENTE=homologacao`. Enquanto não houver resposta, o default continua `producao`, que é o comportamento anterior |
| Q21 | Pastas VIVO / TLF | — | GP/dev | ✅ **tratada no código (2026-08-05)**: pasta ausente ou sem arquivo válido vira `error` nomeando-a, em vez de passar batido. Não aborta — pasta vazia pode ser legítima |
| Q22 | DDL das tabelas | — | DBA | ✅ **fechada (2026-08-06)**: `remuneracao` e `vb_contestacao` **existem** no MySQL real, e o mapeamento de descritores tem as cinco colunas. Nenhuma divergência entre o schema real e o que o código usa |
| Q23 | Demandas irmãs | — | GP/dev | ✅ **fechada (2026-08-06)**: fora de escopo. O ¶410 já dizia que a captura/conversão do ICT é da demanda de **receita** |
| Q24 | Bloco duplicado da V2 | — | GP/dev | ✅ **fechada (2026-08-06)**: não é pendência. O requisito que só existia no bloco antigo (¶942) já foi implementado; a versão limpa do documento deixa de ser pedida |
| **Q25** | Carta com cenários mistos | — | GP/dev | ✅ **resolvida no código (2026-08-05)**: **uma carta por cenário**, cada uma com o seu número CT. O `_ENV` continua único |
| **Q26** | Modelo da carta | — | PO | ✅ **resolvida (2026-08-04)**: modelo **único** para todas as operadoras |
| N1 | Nome da tabela de log | — | GP/dev | ✅ **fechada (2026-08-06) por decisão nossa**: vale `tbl_rpa_log_detraf_despesa_arquivos`, que é o nome da V2 e o que já está implementado. A `tbl_rpa_log_detraf_despesa` fica como resíduo |
| ~~N2~~ | ~~Nome da tabela de descritores~~ | — | — | ✅ anulada — era nome de atributo |
| N3 | Expectativa Vivo sem `R$_Bruto` | 🔴 | PO / área cliente | ⬜ — **contradição entre a V2 e o arquivo real**. Decisão de 2026-08-05: **manter a rejeição** (falhar alto > comparar coluna errada). A contradição segue encaminhada |
| N4 | `tipo_lote` (4) × `tipo_registro` (3) | — | — | ✅ **fechada (2026-08-05)** pelo DDL real: `enum('DETRAF','EXPECTATIVA','ERRO')`. **Sem mudança de código** — os quatro são parâmetro interno e já eram mapeados para os três |
| N5 | Entregar a pasta `AI/` e o `TODO/` do P4 | — | GP/dev | ✅ **fechada (2026-08-05)**: os inventários cobrem o que ela traria |
| N6 | Declaração de dependências dos projetos | — | GP/dev | ✅ **fechada (2026-08-05)**: o `requirements.txt` unificado está consolidado e testado |
| ~~N7~~ | ~~Colunas do `CONT_PROC`~~ | — | — | ✅ decidida em 2026-07-31 — seguir a documentação |
| **N9** | De-para oficial de `codigo_erro` | — | GP/dev | ✅ **fechada (2026-08-05)**: o ¶340 pede erro "sem detalhamento, apenas com alerta em vermelho" — de-para oficial não é requisito de produto |
| **N10** | Formato decimal de `tarifa` no banco | — | — | ✅ **fechada (2026-08-05)** pelo DDL real: `float`, com ponto. O `replace(",", ".")` do lado do banco saiu; o do lado do **arquivo** fica, e sem ele todo arquivo real seria reprovado |
| **N11** | Limiar de tolerância da HU-20 | — | GP/dev | ✅ **fechada (2026-08-05)**: 0,01, configurável em `TOLERANCIA_VERIFICACAO`. Escolha nossa, registrada como tal |
| **N12** | A HU-21 não foi entregue | — | GP/dev | ✅ **entrega adiada por decisão (2026-08-05)**: a HU-21 vem depois. O `rpa4_retificacao/` fica preparado e a ficha do AGI mantém o gatilho de reavaliação |

---

# Rodada de 2026-08-04 — o que a busca na documentação apurou

Antes de fechar as pendências de código, cada assunto em aberto foi conferido
**contra os documentos-fonte**, e não contra os relatórios internos. Três achados
mudam o entendimento anterior.

## 🔴 A "tabela de contatos do WebFat" não existe na V2 (Q16)

A expressão **não ocorre uma única vez** no documento normativo. Tudo o que a V2
diz sobre destinatários, na seção do e-mail à operadora:

> "O robô cria um e-mail para enviar as operadoras:"
> "Destinatários: contatos das operadoras"

O nome vem da **V1** (`DETRAF_MVP2_Historias.pdf`, HU-15): *"Destinatários da
tabela de contatos do WebFat"*. E a V1 usava a mesma tabela na HU-02, para
identificar a operadora pelo domínio do remetente — **uso que a V2 eliminou**,
trocando por EOT credora × Anexo 5:

> "O nome correto da operadora é pela EOT da credora presente no anexo 5 busca
> pela coluna nome fantasia."

Ou seja: a V2 removeu o único uso da tabela que estava descrito, e deixou o outro
sem detalhe. **Não há como saber, pela documentação, se essa tabela existe.**

**O que perguntar ao cliente:** a tabela existe? Qual o nome e a coluna de e-mail?
Se não existe, de onde vêm os contatos das operadoras no processo manual de hoje?

**Enquanto isso:** `envio_email_contestacao.buscar_destinatarios` devolve lista
vazia e o envio é recusado — a HU-15 gera a carta e o `_ENV`, mas não envia.

## 🔴 A evidência por screenshot não é requisito da V2

O Projeto 7 atribuía a captura de tela ao "To Be MVP2, item 4.7.3"
(`projeto-7-epico-5-carga-agi/README.md:100`). A citação **não resolve**: a V2 usa
numeração automática do Word, então não há números de item no texto, e as palavras
*evidência*, *print*, *screenshot* e *comprovante* não ocorrem no documento.

A confirmação de carga que a V2 **de fato** exige é de banco, na seção *Carga no
AGI*:

> "O robô atualiza o campo 'carga_agi' com o o status da carga na tabela
> 'tbl_rpa_log_detraf_despesa_contestacao' do banco webfat."

Isso foi implementado (`repositorio_tabelas.atualizar_carga_agi`). A captura de
tela permanece — é barata e não atrapalha —, mas deixou de ser tratada como
requisito normativo.

## 🟢 A regra de cenário da HU-17 era menor do que registrado

Estava registrado que faltava "EXT sempre, INT só COM retenção". A V2 é explícita
sobre por que a regra, **na carga**, é simples:

> "O arquivo final INT existirá apenas para o caso de contestação com retenção.
> Para os cenários sem contestação e contestação sem retenção, o arquivo INT não
> chegou nem a ser criado, então o robô sobe apenas no AGI o arquivo final EXT."

Quem aplica a regra é a **HU-13**. O que faltava era só uma guarda contra sobra de
execução anterior, implementada.

⚠️ A V2 **não diz** que EXT vem antes de INT — só "um de cada vez". A ordem é
escolha nossa, herdada da V1.

---

## Q25 — Carta de contestação com cenários mistos

**Fonte.** O sinal do analista é por chave `(eot_operadora, eot_tbra, referência,
tráfego, remuneração)` — `tbl_rpa_log_detraf_despesa_contestacao.tipo_contestacao`.
A mesma operadora pode ter, no mesmo mês, linhas "com retenção" e "sem retenção".

Mas a carta é **um documento por operadora/mês**, com **um** número CT e um texto
que descreve **um** cenário.

**Perguntas.**
1. Quando a operadora tem linhas dos dois tipos, sai uma carta ou duas?
2. Se for uma, qual texto prevalece?
3. Se forem duas, consomem dois números CT?

**Bloqueia.** Nada — há um comportamento adotado. Mas ele é uma escolha nossa.

**Adotado enquanto não há resposta:** **prevalece COM retenção**, com aviso no log
e registro no resumo da execução. É o conservador: a carta de retenção descreve uma
consequência maior, e anunciá-la a mais é preferível a omiti-la.

**Decide.** PO

**Resposta:** _______ **Data:** _______

---

## N9 — De-para oficial de `codigo_erro`

*(era "N7" — renumerada em 2026-08-04: já existia uma N7, decidida em 2026-07-31.)*

**Fonte.** A tabela `tbl_rpa_log_detraf_despesa_arquivos` tem a coluna
`codigo_erro`, mas a V2 não traz nenhuma tabela de códigos.

**Situação.** Até 2026-08-04 o código gravava **um valor fixo** —
`"ERR_VALIDACAO_PROCESSAMENTO"` — para toda e qualquer falha, o que tornava a
coluna inútil para diagnóstico. Agora há códigos por categoria
(`resultado_validacao.py`), distinguindo o arquivo que **não pôde ser lido** do
que foi lido e **reprovado na validação**.

**Pergunta.** Existe um de-para oficial de códigos de erro? Se sim, qual?

⚠️ **Severidade rebaixada para 🟢 em 2026-08-04.** A V2 (¶340) pede o oposto de um
de-para rico: *"o erro deve ser apresentado via Webfat (…) **sem detalhamento dos
erros apenas com alerta em vermelho** sinalizando a situação para o analista"*. Um
de-para oficial, portanto, **não é requisito de produto** — os códigos são
diagnóstico interno nosso, e os que existem hoje bastam até segunda ordem.

**Decide.** PO

**Resposta:** _______ **Data:** _______

---

## N10 — Formato decimal da coluna `tarifa`

*(era "N8" — renumerada junto com a N9.)*

**Fonte.** `repositorio_tabelas.validar_tarifas_na_tabela` faz `.astype(float)`
direto na coluna `tarifa` vinda do banco — o que exige **ponto** decimal. Mas a
comparação seguinte, no mesmo fluxo, faz `replace(",", ".")` — ou seja, **tolera
vírgula**.

Uma metade do fluxo assume um formato e a outra, o outro. Se a tabela real usar
vírgula, o robô estoura com *"could not convert string to float"* na validação de
tarifa — que é justamente o coração da HU-04.

O comportamento atual está fixado em
`rpa2_validacao_apuracao/tests/test_validacao_colunas.py::test_tarifa_com_virgula_no_banco_quebra`.
**O teste não escolhe um lado**: ele documenta a inconsistência até o formato real
ser confirmado.

**Pergunta.** Como a coluna `tarifa` de `tbl_detraf_tarifas` está tipada e
formatada no MySQL de produção? (Parte da Q22 — DDL das tabelas.)

**Decide.** DBA / GP-Vivo

**Resposta:** _______ **Data:** _______

---

# Auditoria de 2026-08-04 — o que a releitura mudou

Cada pendência foi reconferida **contra a documentação-fonte**, e não contra os
relatórios internos. Oito mudaram de descrição, severidade ou status.

## As duas decisões do cliente

| # | Pergunta | Decisão |
|---|---|---|
| **Q4** | O `_ENV` vem do arquivo `Base_Contestação` ou do banco? | **A base de contestação é uma tabela no banco** |
| **Q26** | A carta sai de um modelo por operadora? | **Modelo único para todas** |

A primeira **confirma a V2**, que dizia (¶445): *"Não é necessário gerar o
arquivo, mas usar a lógica e popular a tabela
'tbl_rpa_log_detraf_despesa_contestacao'"*. O RPA 2 gravava um `.xlsx` de cinco
abas que **ninguém lia** — removido.

A segunda **supera a V2**, que pede (¶601) *"um modelo pré-existente para cada
operadora"*. O código monta a carta do zero, com um padrão único, e agora isso
está registrado como decisão, não como se a V2 nunca tivesse exigido modelo.

⚠️ **A Q4 estava marcada como "respondida pelo código".** Não estava: a pergunta
era *o que a V2 exige*, e o código fazia o oposto. Responder uma pergunta sobre a
documentação com o comportamento do código inverte a hierarquia de fontes. Q10 e
Q11 tinham o mesmo vício, mais brando — as conclusões estavam certas, as
justificativas não.

## Corrigido

**Q5 — a "Fonte" era falsa.** Dizia que a frase sobre envio automático sobrevive
no bloco antigo da V2. Não existe em bloco nenhum: é da V1.

**Q14 — reaberta.** Ver a seção própria: o `DE_EBT_..._MODELO` é a única
alteração que a V2 fez no passo de carga.

**N7 tinha dois donos.** Já existia uma N7 ("Colunas do `CONT_PROC`", decidida em
2026-07-31) quando uma segunda foi criada para o de-para de `codigo_erro`.
Renumeradas: **N9** (`codigo_erro`) e **N10** (formato da tarifa).

## Severidade revista

| # | De | Para | Por quê |
|---|---|---|---|
| Q20 | 🟡 | 🔴 | Deixou de ser "probabilidade desconhecida": **não existe** ambiente de teste. É impedimento confirmado |
| Q24 | 🟢 | 🟡 | O bloco duplicado **não é duplicata pura** — ver abaixo |
| Q21 | "ignorar" | 🟡 | Determina onde o RPA 2 procura a expectativa; errar a pasta gera contestação indevida |
| Q23 | "ignorar" | 🟢 | O ¶410 responde em parte, e conecta a N3 ao seu dono |
| Q13 | "ignorar" | 🟡 | É **redução de escopo acordada**, não descarte: o ¶424 pede a correção automática no texto vigente |
| N9 | 🟡 | 🟢 | O ¶340 pede erro *"sem detalhamento (…) apenas com alerta em vermelho"* — o de-para não é requisito de produto |
| Q16b | 🔴 | 🟢 | A V2 dá regra genérica para as exceções da HU-02; só os destinatários da HU-15 ficam sem resposta |

## 🟡 Q24 — apagar o bloco duplicado perderia um requisito

O bloco final da V2 **não repete** o texto vigente. Diferenças (novo → antigo):

| Conteúdo | Vigente | Antigo |
|---|---|---|
| aba "Contestação" | ✅ | "cava Expectativa" |
| TU-COM na lista de produtos | ✅ | ausente |
| "Não é necessário gerar o arquivo" | ✅ | ausente |
| `DE_EBT_..._MODELO` na carga | ✅ | ausente |
| comparar CBS/IBS | ✅ | ausente |
| EC via banco (9 campos) | ✅ | "cola na planilha" |
| **"contestação com retenção → preencher a coluna de contestação no EC"** | ❌ **ausente** | ✅ ¶942 |

A última linha é o problema: **existe uma regra só no bloco antigo**, sem
contrapartida no texto vigente — e ela também está na V1 (HU-19: *"Coluna de
contestação preenchida quando houver retenção"*).

**A pergunta certa não é "pode remover?", e sim: essa regra foi revogada de
propósito quando o EC virou banco, ou caiu na edição?**

## Reforço de fonte em N3

A pendência dizia que a V2 é ambígua sobre o `R$_Bruto` da expectativa. **É pior:
a V2 é explícita, e o arquivo real a contradiz.**

> ¶149 — "A validação dos arquivos recebidos, **assim como dos arquivos internos
> de expectativa**, deve passar pelas regras abaixo."
> ¶443 — "o robô copia o conteúdo dos arquivos gerados internamente (expectativa
> Vivo) para esta operadora **até a coluna 'R$ Bruto'**"

Não é ambiguidade a resolver — é contradição entre documento e realidade, o que
sustenta melhor o 🔴 e torna a decisão já tomada ("o layout da V2 vale para os
dois") textualmente fundamentada.

## Q6 fica mais respondível

A V2 **aponta a fonte do layout**: *"Layout dos arquivos presentes em isnumos"*
(¶368, grafia do original). E responde duas sub-perguntas que estavam abertas:

- os impostos são **informativos até 2027** (¶367: *"apenas como informativo nesse
  primeiro ano, a partir de 2027 será feito o devido recolhimento"*);
- as três colunas são dos arquivos **Vivo e do AGI**, não do Detraf da operadora —
  o que enfraquece o risco à validação das 15 colunas.

**A pergunta principal passa a ser: nos dê acesso ao layout em "isnumos".**

## Q12 — uma sub-pergunta era hipótese nossa

`CORREDOR_TRANSPORTE` e `TIPO_TRANSPORTE` **não ocorrem na V2 nem na V1** — vêm de
`comum/dominio/layout_detraf.py`. Estavam apresentadas como leitura da fonte.

---

## Q26 — A carta usa um modelo por operadora?

**Fonte.** V2, ¶601: *"O robô cria na mesma pasta Contestações (…) a carta da
operadora **a partir de um modelo pré-existente para cada operadora**."*

**Situação.** O código monta a carta do zero com `python-docx`, a partir de dois
exemplos reais já emitidos (CT 251-2026 e CT 252-2026), com assinatura fixa.

**Resposta (2026-08-04): modelo único para todas as operadoras.** O código está
alinhado à decisão. Registrado em `geracao_env_carta.py`.

⚠️ Uma rodada anterior afirmou que a V2 "não exigia modelo externo". Exigia — o
que mudou foi a regra.

**Decide.** PO ✅ **Data:** 2026-08-04

---

# Rodada de 2026-08-05 — a chegada do Projeto 6

O último projeto previsto chegou — **mas só com a HU-20**. `Retificação`,
`Recuperação` e o fator `0,9635` não aparecem em nenhum `.py`.

## 🔴 N12 — A HU-21 não foi entregue

**Consequências.** O RPA 4 continua com só um `README.md`. O marco **M7 segue
bloqueado**, e a cisão prevista do Projeto 6 não aconteceu. A **Q17** (nome de
operadora que muda), que bloqueia a HU-21, permanece sem uso prático até o código
existir.

**Efeito colateral positivo:** o P6 era o teste de confirmação da camada do AGI
para dois consumidores. Com um só, o critério C1 continua falhando — mas a
**abstração se validou**: o `AGI_config.py` serviu a um terceiro caso de uso sem
uma linha de alteração de API.

**Pergunta.** A HU-21 será entregue? Quando?

**Decide.** GP-Btime / DEV

**Resposta:** _______ **Data:** _______

---

## 🔴 Q7 — a pergunta sobreviveu à chegada do projeto

A Q7 era *"a HU-20 continua no escopo?"*, e estava marcada como *"depende do
Projeto 6"*. **O projeto chegou e a pergunta continua aberta** — porque ela nunca
foi sobre o código, e sim sobre o texto da V2:

> ¶706 — *"Esse processo trata-se de uma **dupla checagem**, conferir com o
> solicitante se esse processo vale a pena ou não ser mantido."*

Esse parágrafo é **acréscimo da V2**: não existe no bloco antigo. Junto dele veio
outro, igualmente sem resposta:

> ¶705 — *"Caso a conferência com o robô dê errado, qual o processo?"*

**Decisão de 2026-08-05: migrar assim mesmo**, atrás do kill-switch
`PERMITIR_ACESSO_AGI`. O código útil são ~190 linhas; se a HU for descartada, sai
inteira, sem arrastar nada junto. **A severidade sobe para 🔴** porque agora existe
código em produção potencial esperando uma decisão que nunca veio.

---

## 🟡 Q6 avançou — mas não fechou

O CSV que veio **dentro do próprio pacote do Projeto 6** tem **22 colunas**,
incluindo `Vlr. CBS`, `Vlr. IBS Estadual` e `Vlr. IBS Municipal`. O export do AGI
já ganhou as colunas novas.

⚠️ O `H20/README.md` afirma que as colunas são *"idênticas às usadas no exemplo de
Receita"* e lista 17 — **contrariado pelo arquivo entregue junto com ele**.

**O que destravou:** a HU-20 passou a somar as três colunas, como o ¶702 manda.

**O que continua:**
1. o **layout dos arquivos** — o "isnumos" do ¶368, que ninguém localizou;
2. a **contra-parte no Encontro de Contas** — `tbl_rpa_log_detraf_despesa_contestacao`
   só tem `vb_operadora`, sem coluna de CBS nem de IBS. As três são **somadas e
   reportadas**, mas a comparação segue só sobre o valor bruto. Não é omissão: é o
   limite do dado que existe.

---

## Decisões desta rodada

| # | Pergunta | Decisão |
|---|---|---|
| **Fonte do EC na HU-20** | planilha (célula `O87`) ou banco? | **Banco** — `obter_subtotal_despesa_por_operadora` |
| **CBS / IBS** | incluir na comparação? | **Sim, as três** |
| **Sinalização de inconsistência** | tabela, e-mail ou arquivo? | **`.xlsx` na pasta comum de logs** |
| **Q7** | migrar sem resposta? | **Sim, atrás de kill-switch** |

A decisão do EC **confirma a V2** (¶374: *"Todas as planilhas deste processo foram
substituídas por banco"*) e elimina três fragilidades que estavam numa linha só do
Projeto 6: célula fixa `O87`, arquivo externo, e busca de aba por substring do
nome da operadora — `"OI"` casaria com qualquer aba que contenha "oi".

---

## N11 — Qual é o limiar de tolerância da HU-20?

**Fonte.** O Projeto 6 usa `> 0.01` com um TODO ao lado: *"confirmar limiar de
tolerância oficial"*. A V2 não menciona tolerância na HU-20.

**Por que importa.** Um limiar apertado demais gera alerta por arredondamento; um
frouxo demais deixa passar divergência real. Hoje é um centavo.

**Situação.** Configurável em `TOLERANCIA_VERIFICACAO`, para não exigir mexer no
código quando a resposta vier.

**Decide.** PO / área cliente

**Resposta:** _______ **Data:** _______

---

# ✅ Rodada de decisões de 2026-08-05 — 26 pendências revisadas, 11 fechadas

Decisões do GP/dev (Btime) sobre **todas** as pendências abertas. O plano está em
[`plano-rodada-2026-08-05.md`](../02-planejamento/plano-rodada-2026-08-05.md); as
que sobraram foram organizadas por destinatário em
[`pendencias-para-o-cliente.md`](pendencias-para-o-cliente.md).

**Saldo: de 26 abertas para 15**, e nenhuma das 15 depende de desenvolvimento
adicional da Btime — todas esperam resposta de terceiros.

## Fecharam por decisão nossa (6)

| # | Decisão | Por quê |
|---|---|---|
| **Q7** | A HU-20 **fica no escopo** | O ¶706 mandava confirmar. O `PERMITIR_ACESSO_AGI` continua, com outra justificativa: proteção de ambiente (Q20) |
| **Q1** | **Dia 5, configurável no `.env`** | A V1 dizia "após o dia 05"; a V2 removeu a regra e não pôs nada no lugar. Herdamos a V1 em vez de inventar |
| **N9** | Os códigos internos bastam | O ¶340 pede o oposto de um de-para rico: erro "sem detalhamento, apenas com alerta em vermelho" |
| **N11** | **0,01, configurável** | `TOLERANCIA_VERIFICACAO`. Escolha nossa, ajustável sem tocar no código |
| **N5** | A pasta `AI/`/`TODO/` do P4 não faz falta | Os inventários cobrem o que ela traria |
| **N6** | Idem, declaração de dependências | O `requirements.txt` unificado está consolidado e testado |

## Viraram código (4)

| # | O que mudou | Onde |
|---|---|---|
| **Q25** | **Uma carta por cenário**, cada uma com o seu número CT. O `_ENV` continua único | `geracao_env_carta.separar_por_cenario`, `geracao_agi_controller._emitir_cartas` |
| **Q18** | **Trava por arquivo** na numeração CT, cobrindo o par ler→gravar | `geracao_env_carta.travar_numeracao` |
| **Q21** | Pasta de expectativa ausente ou vazia vira `error` **nomeando a pasta** | `rpa2/src/services/expectativa.py`, usada pelas duas varreduras |
| **Q24** | A regra do ¶942 virou a coluna **`vb_contestacao`**, preenchida só nas linhas COM retenção | `encontro_contas._valor_contestado` |

⚠️ **A Q25 e a Q18 andam juntas:** emitir duas cartas faz a **mesma execução**
consumir dois números seguidos da sequência global. A trava deixou de ser
precaução e virou pré-requisito.

⚠️ **A Q24 conflita com a resposta da Q22** ("deixar o DDL como está"): o ¶942 pede
uma coluna que a tabela presumida não tem. Seguimos o precedente da `remuneracao`,
acrescentada do mesmo jeito em 2026-07-28 — implementar e **encaminhar ao DBA**.

## Ficam como estão (4)

**N3** — manter a rejeição da expectativa sem `R$_Bruto`: falhar alto é melhor que
comparar coluna errada em silêncio. **Q22** — o código segue com o schema
presumido. **Q14** — o `DE_EBT_..._MODELO` continua fora de escopo, agora
reconfirmado sabendo que é acréscimo da V2. **N12** — a HU-21 vem depois; o
`rpa4_retificacao/` fica preparado e a ficha do AGI mantém o gatilho.

## Ponte, não solução (1)

**Q16** — os contatos da HU-15 passam a poder vir de um CSV `operadora;emails`
apontado por `CAMINHO_CONTATOS_OPERADORAS`. A pergunta continua aberta: a "tabela
de contatos do WebFat" não existe na V2. Quando ela existir, o que muda é o corpo
de uma função — por isso a leitura ficou isolada em `buscar_destinatarios`.

⚠️ **Isto desbloqueia o envio real.** Com o arquivo preenchido e
`PERMITIR_ENVIO_EMAIL=true`, o robô envia para as operadoras. O kill-switch passa
a ser a única proteção.

## Q20 — validar contra produção, com cuidado

Não há ambiente de teste, e a decisão foi validar em produção usando o modo "só
leitura":

```
PERMITIR_ACESSO_AGI=true   PERMITIR_UPLOAD_AGI=false   PERMITIR_ENVIO_EMAIL=false
```

O roteiro está em
[`checklist-validacao-agi.md`](../03-checklists/checklist-validacao-agi.md), e a
premissa dele — que essa combinação **não escreve nada no AGI e não envia e-mail** —
está provada por teste (`TestModoSoLeitura`), com os uploaders reais ligados a um
AGI que explode ao primeiro toque.

O que continua faltando é do GP-Vivo: **autorização** para o login em produção,
combinar a primeira operadora da carga real, e acesso às pastas Lagoa.

## As 15 que continuam abertas

| Destinatário | Pendências |
|---|---|
| **PO / GER-AC** | Q6, Q11, Q13, Q16, Q16b, N3, N4 |
| **DBA / GP-Vivo** | Q22, N1, N10 — **mais as colunas `remuneracao` e `vb_contestacao`** |
| **Vivo** | Q17 |
| **GP-Vivo** | Q20, Q23, Q24 |
| **Solicitante** | Q12 |

⚠️ **Correção de contagem (2026-08-05).** Este bloco dizia **12**, e o plano
estimava **10**. São **15**: a soma anterior deixou de fora a linha "com
tratamento provisório" (Q16 e N3) e a Q24.

As 11 que fecharam: **Q1, Q7, Q14, Q18, Q21, Q25, N5, N6, N9, N11, N12**. A
**Q22** e a **N3** têm decisão nossa sobre como o código se comporta, mas
**continuam abertas** — a pergunta que elas fazem só o cliente responde. A **Q24**
teve o requisito extraído (o ¶942), mas o pedido da versão limpa do documento
continua de pé.

Três das 15 têm comportamento provisório definido e **não travam a entrega**: Q16
(ponte por CSV), N3 (rejeição mantida) e Q22 (schema presumido). As outras 12
travam alguma coisa.

---

# 📎 Rodada de 2026-08-05 — as imagens do `.docx` responderam três

O `.docx` normativo carrega **56 imagens embutidas**, e duas delas são prints do
**MySQL Workbench conectado ao schema `webfat`**, com o DDL real. Nada disso
aparece na extração de texto — por isso passou batido em todas as leituras
anteriores.

O levantamento está em
[`pendencias-respondidas-pelos-anexos.md`](pendencias-respondidas-pelos-anexos.md);
a conferência contra o código, em
[`relatorio-conferencia-dos-anexos.md`](relatorio-conferencia-dos-anexos.md).

## Fecham (3)

| # | Resposta | Efeito no código |
|---|---|---|
| **N10** | `tarifa` é `float`, com ponto | O `replace(",", ".")` do lado do **banco** saiu. O do lado do **arquivo** fica — sem ele, todo arquivo real seria reprovado |
| **N4** | `tipo_registro` é `enum('DETRAF','EXPECTATIVA','ERRO')` | **Nenhum.** Os quatro valores são parâmetro interno e já eram mapeados para os três |
| **Q13** | Não há correção automática | **Nenhum.** O comportamento adotado já era o certo |

## Encolhem (4)

**Q22** — dois dos quatro DDLs chegaram e **batem com o que o código usa**.
Faltam `..._contestacao` e `..._mapeamento_descritores`.
**Q16b** — a regra genérica cobre 2 dos 4 casos; faltam EOT fora do Anexo 5 e
e-mail multi-operadora.
**Q16** — a tabela continua sem aparecer, mas o processo manual ficou visível: o
CSV da ponte ganhou **Para, Cc e cópia fixa**.
**Q17** — a tela do AGI tem busca por **`Número Processo`**; guardar o `ID
Processo` da contestação dispensaria o nome.

## Sobem de severidade (2)

**N1 → 🔴.** O navigator mostra **as duas** tabelas no schema:
`tbl_rpa_log_detraf_despesa_arquivos` e `tbl_rpa_log_detraf_despesa`. A pergunta
deixou de ser "qual é o nome certo" e passou a ser **qual delas o WebFat lê** — se
for a sem sufixo, o robô grava numa tabela que ninguém consulta.

**Q6 → 🔴.** O item 7 diz que o imposto novo de 2028 **desloca as colunas**. Ver
o risco **R21** abaixo.

## Achados novos (3)

**A1 🔴** — `tbl_detraf_tarifas` **não tem** `eot_vivo` nem `eot_operadora`, que a
V2 manda usar para exceções de região. O código nunca dependeu delas, então nada
quebra — mas a exceção **RII (943) × SERCOMTEL (042/043)** não tem como ser
expressa, e o par é **reprovado na validação como se o arquivo estivesse errado**.

**A2 ✅ corrigido** — a justificativa da coluna `remuneracao` estava errada. O
print da aba `Contest` mostra **uma linha por par de EOT, uma marca só**: a
decisão de contestar não se abre por remuneração. A coluna continua necessária
porque **o Encontro de Contas é por remuneração** — a granularidade muda ao longo
do fluxo. O argumento a levar ao DBA é este, não o anterior.

**A3 🟡** — os prints expõem endereços de rede internos, host e schema do banco,
matrícula e e-mails de contato. Entra no mesmo encaminhamento do R20.

## O que **não** se confirmou

Três das "consequências no código" propostas no levantamento não se sustentaram
na conferência — e uma delas, aplicada como escrita, teria reprovado todo arquivo
real. Detalhe em
[`relatorio-conferencia-dos-anexos.md`](relatorio-conferencia-dos-anexos.md).

## Saldo

Continuam **15 abertas**: três fecham, três entram. O que sai em número entra em
qualidade — as que ficam estão melhor delimitadas, e o pedido ao DBA caiu de
quatro DDLs para **dois, mais duas perguntas pontuais** (qual tabela o WebFat lê;
como a exceção SERCOMTEL está representada).

---

# 🗓️ Rodada de 2026-08-06 — decisões, e um defeito achado no caminho

## Fecham (4)

| # | Decisão | Fundamento |
|---|---|---|
| **N1** | Vale `tbl_rpa_log_detraf_despesa_arquivos` | É o nome da V2 e o que já está implementado. A tabela sem sufixo fica como resíduo |
| **Q12** | A regra já vinha do Épico 2 | `classificar_descritor_remuneracao`, por caractere inicial/final. Não era pergunta em aberto — era regra implementada e não reconhecida como tal |
| **N3** | Manter a rejeição | Confirmado: falhar alto continua melhor que comparar coluna errada |
| **A1** | Não é pendência | O código nunca dependeu de `eot_vivo`/`eot_operadora`; fica como está |

## Q17 — caminho técnico aceito

Guardar o **`ID Processo`** devolvido pelo AGI no momento da contestação, e o
RPA 4 recupera por número em vez de por nome. A mudança de nome deixa de
importar.

**Exige uma coluna a mais** em `tbl_rpa_log_detraf_despesa_contestacao` — entra no
mesmo pedido de DDL da Q22, agora com **três** colunas nossas: `remuneracao`,
`vb_contestacao` e a do processo.

⚠️ A pendência Vivo **continua valendo** para contestações criadas antes do robô,
que não têm `ID Processo` registrado.

## Q16 — o arquivo modelo existe

`unificado/configuracao/contatos-operadoras.csv`, com o formato documentado no
próprio arquivo e três exemplos. Basta apontar `CAMINHO_CONTATOS_OPERADORAS` e
substituir pelos contatos reais.

---

## Q22 — os SQLites de origem responderam metade

Os bancos que vieram em `projetos-origem/` foram abertos e conferidos. **O do
Projeto 3 tem as duas tabelas que faltavam**, com dados reais (1.175 linhas de
contestação).

### `tbl_rpa_log_detraf_despesa_contestacao` — 18 colunas

```
id, tipo_servico_vivo, eot_tbra, eot_operadora, empresa, referencia, trafego,
minutos_tbra, vb_tbra, minutos_operadora, vb_operadora, minutos_diferenca,
vb_diferenca, minutos_variacao_perc, vb_variacao_perc, carga_agi,
tipo_contestacao, created_at
```

**Bate exatamente com a planilha de referência** — e **confirma** que as colunas
que acrescentamos (`remuneracao`, `vb_contestacao`) não existem em nenhuma fonte
observada. Elas continuam sendo acréscimo nosso, e o pedido ao DBA continua de pé.

⚠️ **Isto não é o DDL do MySQL.** É um SQLite gerado pelo Projeto 3, que reflete o
que aquele projeto escrevia. Serve como confirmação da forma, não como
substituto do `SHOW CREATE TABLE`.

### `tbl_detraf_mapeamento_descritores` — 3 colunas, em caixa alta

```
FINAL_DO_DESCRITOR, REMUNERACAO_FIXA, DS_OBS
```

Os dois SQLites que a têm (P2 e P3) trazem **as mesmas três**. O código espera
**cinco em caixa baixa** (`id`, `final_descritor`, `remuneracao_fixa`,
`observacao`, `produto`) — expectativa que veio do Projeto 4 e **não se confirma
em nenhuma fonte observada**.

O `preparar_banco_dev.py` já adapta isso para o banco de dev. Mas a pergunta ao
DBA fica mais precisa: **a tabela em produção tem três colunas ou cinco?** Se
tiver três, o filtro por `produto == "DETRAF"` do RPA 3 não tem sobre o que
operar.

---

## 🔴 A4 — As duas fontes de remuneração não falam a mesma língua

**Achado em 2026-08-06, ao verificar a Q12.** É o item mais grave da lista.

Existem **duas** fontes de remuneração no repositório, e elas produzem strings
diferentes para o mesmo descritor:

| Fim do descritor | RPA 2 grava | RPA 3 procura | Casam? |
|---|---|---|---|
| `L` | `TU-RL` | `TU-RL` | ✅ |
| `V` | `VU-M` | `VU-M` | ✅ |
| `C` | **`TUCOM`** | **`TU-COM`** | ❌ |
| `I` | **`TU-RIU1`/`TU-RIU2`** | **`TU-RIU`** | ❌ |
| `T`, `M`, `U`, `W`, `D`, `S`… (17 outros) | **`None`** | valor real da tabela | ❌ |

- **RPA 2** grava `remuneracao` em `tbl_rpa_log_detraf_despesa_contestacao` usando
  `classificar_descritor_remuneracao` — regra fixa do Épico 2, cinco resultados;
- **RPA 3** monta a remuneração a partir da **tabela D-5**
  (`tbl_detraf_mapeamento_descritores`, 25 linhas, 21 finais distintos) e a usa
  como **parte da chave** de `obter_tipo_contestacao`.

A comparação é igualdade exata de string, depois de `strip`
(`_filtrar_contestacao_por_chave`). `TUCOM` ≠ `TU-COM`.

### O efeito

Para todo descritor que não termine em `L` ou `V`, **o RPA 3 não encontra o sinal
do analista**. A linha não é contestada, e nada acusa: `obter_tipo_contestacao`
devolve `None`, que é indistinguível de "o analista não sinalizou".

### Por que os testes não pegaram

O seed do conftest usa `TU-RL` e `VU-M` — exatamente os **dois valores em que as
duas fontes concordam**.

### Por que as duas fontes existem, e por que ambas são legítimas

Não é uma duplicação a eliminar. As duas vocabulários servem a coisas diferentes,
e o dado real confirma:

- `tbl_detraf_tarifas.tipo_remuneracao` tem **`TU-RIU1`, `TU-RIU2`, `TU-RL`,
  `VU-M`** — o vocabulário da **tarifa regulada**, com o RIU dividido em dois
  porque a tarifa difere;
- `tbl_detraf_mapeamento_descritores.REMUNERACAO_FIXA` tem **`TU-COM`, `TU-RIU`,
  `VU-T`, `PU`, `MU`…** — o catálogo **amplo** de remuneração.

A regra fixa está **certa para a validação de tarifa** (é o vocabulário da tabela
de tarifas). O que está errado é usá-la para a **chave da contestação**, que o
RPA 3 monta pelo catálogo.

### Correção proposta

Separar os dois usos: manter `classificar_descritor_remuneracao` na validação de
tarifa, e fazer o RPA 2 resolver o `remuneracao` que **grava** pela mesma tabela
D-5 que o RPA 3 usa para **ler** — o que a V2 manda (*"validados a partir da
tabela Descritor_Remuneração"*) e a D-21 já estabelecia.

**Não aplicada ainda** — muda comportamento do RPA 2 e merece decisão explícita.

---

# 🗓️ Rodada de 2026-08-06 (segunda parte) — cinco fecham

| # | Decisão | Efeito |
|---|---|---|
| **Q11** | 🔴 **NÃO é o valor bruto** | A coluna `VLR_BRUTO` do CONT_PROC passa a receber **minutagem**, como o ¶643 diz literalmente. **Mudança de código, em dado que vai para o AGI** |
| **Q16b** | EOT fora do Anexo 5 fica como está; e-mail multi-operadora **não existe** | Fecha. Cada e-mail traz uma operadora só |
| **Q16** | O CSV é a solução, não ponte | Fecha. Modelo em `unificado/configuracao/contatos-operadoras.csv` |
| **Q23** | Fora de escopo | Fecha |
| **Q24** | Não é pendência | Fecha. O ¶942 já foi implementado; a versão limpa do documento não será pedida |
| **A3** | Não é pendência | Fecha. Segue no encaminhamento do R20, sem status próprio |

## ⚠️ Q11 merece registro à parte

Era a pendência que eu chamava de "a mais barata e a de maior consequência
isolada", e a resposta **inverteu o comportamento**.

O código gravava `vb_diferenca` — o valor — porque uma coluna chamada
`VLR_BRUTO` recebendo minutos parecia erro de redação: o texto do ¶643 é
**idêntico ao da coluna `DURACAO`**. A pendência existia justamente porque é
**dado financeiro carregado no AGI**, onde errar não é reversível e ninguém
confere linha a linha.

**Resposta: não é o valor bruto.** As duas colunas recebem a mesma minutagem.

Fixado em `test_duracao_e_vlr_bruto_sao_negativos_da_diferenca`, que agora
**também afirma que o valor não aparece** — se alguém reintroduzir o
`vb_diferenca`, o teste falha em vez de passar por coincidência.

A reversão, se um dia for preciso, é uma linha em `montar_linhas_cont_proc`.

---

# 🗓️ Rodada de 2026-08-06 (terceira parte) — o layout chegou e a A4 foi corrigida

## Q6 — o layout completo, e o R21 fecha junto

O layout tem **21 colunas**:

```
 1 Credora      6 Rel         11 Tarifa       16 CN_RELACIONAMENTO
 2 Devedora     7 DESC        12 R$_Liq       17 CBS
 3 Referencia   8 GH          13 PIS_Cofins   18 IBS_Municipal
 4 Trafego      9 Chamadas    14 ICMS         19 IBS_Estadual
 5 POI         10 Minutos     15 R$_Bruto     20 EOT_Ponta
                                              21 Corredor
```

✅ **As 15 primeiras não se mexem.** CBS e IBS entram **depois** do `R$_Bruto`,
não no bloco de impostos. Toda a leitura posicional deste repositório (índices 0
a 14) continua correta.

Isso **fecha o risco R21**, registrado no dia anterior a partir do item 7 da V2
(*"mais um imposto deslocando as colunas"*): o deslocamento que se temia não
acontece neste layout.

**O que se ganhou de brinde:** duas colunas que apareciam no código sem fonte
agora têm nome e posição. O `Corredor` (índice 20) estava em `layout_detraf.py` e
a Q12 chegou a registrá-lo como **suposição nossa** — é real. O `EOT_Ponta`
(índice 19) não tinha nome em lugar nenhum.

⚠️ **As posições 16-21 não são validadas**, de propósito: os arquivos de hoje têm
outra coisa ali. A ALGAR entrega 18 colunas em que a 16ª é `valor_total_real`, a
17ª `OPERATOR_TYPE` e a 18ª `cd_eot`. Validar por estas posições rejeitaria
arquivos que estão certos para o layout vigente deles.

**Q6 continua aberta em uma coisa só:** a contra-parte no Encontro de Contas. A
tabela tem `vb_operadora` e nenhuma coluna de imposto — não há contra o que
comparar, e é por isso que a HU-20 compara só o valor bruto.

## Q22 — cinco colunas

`tbl_detraf_mapeamento_descritores` tem **as cinco** que o código espera. A
divergência dos SQLites de origem (três colunas em caixa alta) era deles, não do
banco real. O `preparar_banco_dev.py` continua adaptando o banco de dev.

## Q17 — não é pendência

O caso não existe. A coluna de `ID Processo` que chegou a ser cogitada **sai do
pedido de DDL** — voltam a ser duas colunas nossas: `remuneracao` e
`vb_contestacao`.

---

## ✅ A4 — corrigido

O RPA 2 passou a resolver a remuneração pelo **mesmo catálogo D-5** que o RPA 3
usa para ler. Quem grava e quem lê a chave usam uma fonte só.

`mapa_remuneracao` foi **promovido** de `rpa3/src/services/` para
`comum/dominio/` — os critérios C1-C4 já se cumpriam; o que travava era o
bloqueio B-D21 (schema não confirmado), levantado pela resposta da Q22 acima. O
módulo do RPA 3 virou reexport, para os imports dele seguirem valendo.

⚠️ **A regra fixa do Épico 2 continua existindo e continua certa** — para a
validação de **tarifa**, onde o vocabulário é o de
`tbl_detraf_tarifas.tipo_remuneracao` (`TU-RIU1`, `TU-RIU2`, `TU-RL`, `VU-M`, com
o RIU dividido porque a tarifa difere). Não eram duas implementações da mesma
coisa: são duas coisas com nomes parecidos.

**Achado de brinde.** O seed do conftest do RPA 2 preenchia a coluna `produto`
com a própria remuneração (`"VU-M"`, `"TU-RL"`…) em vez de `"DETRAF"`. Como
`construir_indice_remuneracao` filtra por `produto == "DETRAF"`, o índice sairia
**vazio** e toda remuneração viraria `None`. Passou despercebido porque, até
agora, **nada no RPA 2 lia essa tabela**.

Agora o RPA 2 também **avisa** quando um descritor não está no catálogo, nomeando
os descritores — sem isso, a linha fica sem remuneração em silêncio e o RPA 3
nunca a encontra.

---

# 🗓️ Rodada de 2026-08-06 (quarta parte) — as três últimas

## ✅ Q22 — fechada

As duas colunas acrescentadas pela unificação — `remuneracao` e `vb_contestacao`
— **existem no MySQL real**. Somadas às cinco colunas do mapeamento de
descritores e aos dois DDLs vindos dos prints, **não há divergência entre o
schema real e o que o código usa**.

Vale registrar o que estava em jogo, porque o efeito era desproporcional ao
tamanho da pergunta — e foi medido, não estimado:

- **sem `remuneracao`**, a leitura do sinal levanta `KeyError: 'remuneracao'`. É
  pré-condição de todas as HUs do RPA 3, que **morre na primeira operadora**,
  antes de gerar artefato nenhum;
- **sem `vb_contestacao`**, o `UPDATE` da HU-19 falha inteiro (`no such column`)
  e a despesa não é escrita para operadora alguma — nem os campos que existem,
  porque é uma instrução só.

O `verificar_ambiente.py` e o `espelhar_banco.py` continuam conferindo as duas: o
custo é zero e o modo de falha, caro.

## 🟡 Q20 — encolheu para um ponto só

**`ENV=dev` isola o banco, e só o banco.** Ele é lido em um único lugar
(`repositorio_cache._obter_engine`) e não sabe que o AGI existe.

O resto se isola, mas por outras variáveis:

| O que | O que isola |
|---|---|
| Banco WebFat | `ENV=dev` + `CAMINHO_SQLITE` |
| AGI | `PERMITIR_ACESSO_AGI` / `PERMITIR_UPLOAD_AGI` |
| Outlook | `PERMITIR_ENVIO_EMAIL` / `NOTIFICAR_OPERADORA_ENVIAR` |
| Pastas de rede | apontar os caminhos para pastas locais |
| **Numeração CT** | `CAMINHO_CONTROLE_CT` numa pasta local |

⚠️ **A numeração CT é a que mais se esquece.** Não é banco nem kill-switch: é uma
pasta. Apontada para o compartilhamento real, cada rodada de teste **consome
números da sequência de verdade**, e eles não voltam.

O *perfil de homologação isolada* — o `.env` completo — está no
[guia de partida](../03-checklists/homologacao-guia-de-partida.md).

**O que sobra é irredutível:** a automação de interface do AGI. Ela é por
reconhecimento de imagem contra o aplicativo real, e não existe "AGI de
desenvolvimento". Validá-la exige abrir e logar em produção — com autorização.

## 🟢 Q6 — a comparação fica para 2027, e o registro começa agora

O layout chegou e as três colunas de imposto **já são lidas e somadas**. O que
não existe é a contra-parte: `tbl_rpa_log_detraf_despesa_contestacao` não tem
coluna de imposto, então não há contra o que comparar.

E não corre: a V2 (¶367) diz que os impostos são *"apenas como informativo nesse
primeiro ano, a partir de 2027 será feito o devido recolhimento"*.

**O que mudou.** Até aqui as somas de CBS e IBS só apareciam **quando havia
divergência** — elas iam junto no `.xlsx` de inconsistências, e num mês limpo
nenhum arquivo era gravado. Em 2027, a pergunta *"quanto foi de CBS em julho de
2026?"* não teria resposta.

Agora elas são **registradas no log todo mês**, marcadas como informativas e
citando a Q6. Custa uma linha e cria a série histórica.

**A pergunta que fica para o PO, sem urgência:** quando o recolhimento começar,
onde os impostos entram do lado do Encontro de Contas? Colunas novas na tabela,
tabela à parte, ou a conferência continua só sobre o bruto?

---

# 🎉 2026-08-06 — Q20 fechada. Nenhuma pendência aberta.

A autorização para abrir e logar no AGI de produção foi concedida. **Era a
última pergunta que dependia de terceiros.**

## O que a Q20 virou

Deixou de ser pendência e virou **procedimento**, em
[`checklist-validacao-agi.md`](../03-checklists/checklist-validacao-agi.md).

O que se acrescentou junto com o fechamento:

**`verificar_imagens_agi.py`** — procura cada uma das 30 imagens de referência na
tela atual e diz quais são encontradas, com o grau de confiança. **Não clica, não
digita, não abre o AGI**: é `locateOnScreen`, leitura de tela.

Existe porque este era o maior risco operacional da validação. Sem ele, descobrir
uma imagem quebrada custava uma execução inteira — abrir o AGI, logar, navegar, e
falhar no meio, **uma imagem por vez**, porque cada `_wait_appear` espera até 180
segundos antes de desistir. Sete imagens quebradas eram sete rodadas.

Ele também distingue a categoria pior de todas: a imagem **fraca**, que casa
abaixo de 0.8. Ela passa no teste e **falha de forma intermitente** em produção.

O modo "só leitura" do checklist passou a usar o ferramental atual:
`PERMITIR_ACESSO_AGI_RPA3` (sufixo por robô, para não ligar nos outros), `ENV=dev`
com espelho, `--etapa verificacao` e `CAMINHO_CONTROLE_CT` numa pasta local.

## 🔴 O que ainda bloqueia a primeira execução

**A rotação das credenciais do AGI (risco R20).** Elas vieram preenchidas nos
`.env` de dois projetos de origem, com os mesmos comprimentos — provavelmente a
mesma credencial, circulando fora do controle de versão.

**Autorização para usar o AGI não é autorização para usar aquela credencial.**
Rotacione, ponha a nova no ambiente da VM — não num `.env` versionado — e só
então rode.

Não é pendência de negócio: é tarefa de segurança, com dono definido.

---

## Saldo final da série

Das **26 pendências abertas em 2026-08-05**, restam **zero**.

| Como fecharam | Quantas |
|---|---|
| Decisão do GP/dev | 11 |
| Respondidas pelas imagens do `.docx` | 3 |
| Respondidas pelo cliente nesta série | 8 |
| Descartadas como não-pendência | 4 |

Ao longo do caminho, **quatro defeitos reais** foram achados e corrigidos — todos
invisíveis para os testes que existiam:

1. **A4** — o RPA 2 gravava a remuneração por uma regra e o RPA 3 a lia por
   outra. A contestação só funcionava para 2 dos 21 descritores;
2. **Q11** — a coluna `VLR_BRUTO` do CONT_PROC recebia valor onde o AGI espera
   minutagem;
3. o banco de dev **quebrava o RPA 3 no arranque** (mapa de descritores em outro
   formato) e não tinha a `vb_contestacao`;
4. o seed do RPA 2 punha a remuneração na coluna `produto`, o que zerava o índice.

**O que resta é trabalho, não pergunta:** rotacionar as credenciais e executar a
homologação.

---

# 🗓️ Rodada de 2026-08-06 (quarta parte) — o portão de validação sobe para o RPA 1

Não é pendência: é decisão de arquitetura tomada pelo GP/dev, com um defeito
achado no caminho.

## A mudança

Até aqui o **RPA 2** validava os Detrafs e respondia ao e-mail da operadora
quando um era inválido. O arquivo ruim já estava dentro da árvore de pastas
quando alguém descobria, e a resposta saía uma execução depois — que, com a
agenda em lote, podia ser dias.

Agora quem valida é o **RPA 1**, antes de salvar. O que reprova **nunca chega à
pasta da operadora**: vai para `DIRETORIO_QUARENTENA`, com o diagnóstico ao lado,
e a resposta sai na mesma execução.

| | Antes | Agora |
|---|---|---|
| Quem valida | RPA 2 | **RPA 1** (portão) e RPA 2 (rede de segurança) |
| Quem responde à operadora | RPA 2 | **RPA 1** |
| Onde vai o reprovado | `Detrafs Recebidos/`, renomeado `_ERRO` | `_QUARENTENA/{aaaamm}/{entry_id}/` |
| Como o e-mail é localizado | busca por **nome de arquivo** no rastreamento | `entry_id`, que a captura já tem |
| O corpo diz o motivo? | não | **sim** — placeholder `{motivos}` |

### Decisões que a acompanham

| Decisão | |
|---|---|
| Profundidade no RPA 1 | **completa** — layout + regras de coluna, a mesma classe do RPA 2 |
| Arquivo reprovado | **não** entra na árvore das operadoras |
| Corpo da resposta | leva os motivos, uma linha por regra |
| Reprovação em massa | **notifica assim mesmo**, sem disjuntor |

> ⚠️ Sobre a última. Se a causa da reprovação for **nossa** — mês de referência
> errado, Anexo 5 desatualizado, tabela de tarifas vencida — todas as operadoras
> recebem um e-mail indevido de uma vez. A proteção que resta é o
> `NOTIFICAR_OPERADORA_ENVIAR`, que por padrão só cria **rascunho**: nada sai sem
> alguém ligar a chave. Registrado para que a decisão seja revisitável.

## 🔴 Defeito achado: o motivo da coluna 3 nomeava o mês errado

`_validar_col_3_referencia` comparava a referência contra `ANO_MES_REFERENCIA` —
correto — mas **logava `ref_mes_menos_1`**, que é o mês *anterior* ao exigido.

Enquanto aquilo era uma linha de log, era ruído. Nesta mudança a mesma frase
passou a ser o **corpo do e-mail que diz à operadora qual mês reenviar** — e ela
mandaria o mês errado, gerando uma segunda rodada de recusa.

Corrigido, com regressão em
`tests/test_motivos_da_validacao.py::TestOMotivoDaColuna3CitaOMesCerto`.

## Duas coisas que mudaram de significado

**`_NAO_IDENTIFICADOS` ficou raro.** A validação exige que a EOT credora exista
no Anexo 5, e a identificação procura o nome fantasia **nessa mesma tabela** — um
arquivo que passa na validação tem, portanto, a operadora identificável. O ramo
continua no código como rede de segurança (divergências de normalização, Excel
devolvendo `11.0`), mas deixou de ser um desfecho comum.

**Um `_ERRO` no RPA 2 virou anomalia.** Nada reprovado deveria chegar até ele. Se
chegar, ou o portão do RPA 1 falhou, ou alguém pôs o arquivo na pasta à mão — por
isso a reprovação lá passou a ser registrada em nível `error`.

## O que a mudança exige do ambiente

| | |
|---|---|
| `DIRETORIO_QUARENTENA` | nova. Default `_QUARENTENA`, **fora** da raiz das operadoras |
| `CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO` | passou a ser do RPA 1, e ganhou `{motivos}` |
| `NOTIFICAR_OPERADORA_ENVIAR` | mesmo nome, mesmo default; passou a ser do RPA 1 |
| Leitura em `tbl_detraf_tarifas` | o usuário do banco do RPA 1 passou a precisar dela |

⚠️ **A quarentena precisa ficar fora da raiz das operadoras** por dois motivos: o
conhecido (o RPA 2 trata todo diretório da raiz como uma operadora) e um novo —
se ficasse dentro, o RPA 2 encontraria o arquivo reprovado e responderia à
operadora uma **segunda** vez.

⚠️ **A captura ficou mais lenta.** Ela lia duas linhas do arquivo; passou a ler o
arquivo inteiro. Com Detrafs de centenas de milhares de linhas, sai da casa dos
segundos. A leitura é **uma só**, compartilhada entre as duas camadas de
validação, e a promessa de paralelização no docstring do `ProcessamentoService`
foi retirada — N threads seriam N arquivos grandes em memória.
