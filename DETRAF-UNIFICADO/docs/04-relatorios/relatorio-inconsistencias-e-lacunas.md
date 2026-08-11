# Relatório de Inconsistências e Lacunas da Documentação

> ⚠️ **Fotografia da etapa documental (2026-07-30).** Este documento foi escrito
> **antes** de qualquer código chegar, e descreve o entendimento daquele momento.
> Vários pontos já mudaram — em especial: o Épico 5 **tem** projeto (o P7, entregue
> em 2026-08-04), e as HUs 12 a 19 estão implementadas e orquestradas.
>
> **Fonte do estado atual:** `docs/04-relatorios/duvidas-pendentes.md` (pendências),
> `matriz-de-rastreabilidade.md` (HUs) e `unificado/README.md` (código).

Resultado da análise crítica das quatro fontes documentais. Cada achado traz: **onde aparece**, **por que é problema**, **o que bloqueia** e **quem decide**.

> Este relatório é o produto mais importante desta etapa. Nada aqui é suposição silenciosa: onde há dúvida, ela está declarada como dúvida.

## Sumário por severidade

| # | Achado | Severidade | Bloqueia |
|---|---|---|---|
| 1 | Épico 5 não atribuído a nenhum projeto | 🔴 Bloqueante | Composição do RPA 3 |
| 2 | Borda de 1% não fecha entre as fontes | 🔴 Bloqueante | Decisão financeira do RPA 2 |
| 3 | Data de corte indefinida | 🔴 Bloqueante | Gatilho do RPA 1 e do RPA 2 |
| 4 | Contradição `_ENV` × `Base_Contestação` | 🔴 Bloqueante | HU-14 |
| 5 | HU-15: envio automático só no texto revogado | 🔴 Alto | Passo irreversível do RPA 3 |
| 6 | CBS/IBS sem HU, sem layout, sem dono | 🔴 Alto | Layout, validação, comparação |
| 7 | HU-20 questionada pela própria V2 | 🟡 Médio | Cisão do P6 |
| 8 | "Exceto dois arquivos" não fecha | 🟡 Médio | Escopo de artefatos |
| 9 | Bloco de texto duplicado na V2 | 🟡 Médio | Leitura correta da V2 |
| 10 | `DE_EBT_..._MODELO.xlsx` sem papel definido | 🟡 Médio | HU-17 |
| 11 | Encontro de Contas: RPA 2 ou RPA 3? | 🟡 Médio | Posicionamento da HU-19 |
| 12 | Tarifas não reguladas: valida ou classifica? | 🟡 Médio | HU-05 |
| 13 | HU-06: recalcula o total ou não? | 🟡 Médio | HU-06 |
| 14 | `VLR_BRUTO` descrito como minutagem | 🟡 Médio | HU-16 |
| 15 | Descritores de transporte sem regra | 🟡 Médio | HU-05 |
| 16 | "Correção automática" sem regra | 🟡 Médio | HU-08 |
| 17 | Memória local × WebFat × Lagoa | 🟡 Médio | HU-03 |
| 18 | HU-02: efeitos colaterais não previstos | 🟡 Médio | HU-02 |
| 19 | Nome de operadora muda entre meses | 🟡 Médio | HU-21 |
| 20 | Numeração CT sem controle de concorrência | 🟡 Médio | HU-14 |
| 21 | Escopo do WebFat: deste projeto ou de outro? | 🟡 Médio | Gatilho do RPA 3 |
| 22 | Célula O87 e destino do consolidado do EC | 🟢 Baixo | HU-20 |
| 23 | Interface com as demandas irmãs | 🟢 Baixo | Contexto |
| 24 | Separação VIVO/TLF sem critério | 🟢 Baixo | HU-03/HU-04 |
| 25 | Layout do banco não publicado | 🟢 Baixo | Análise de código |

---

# 🔴 Bloqueantes

## 1. O Épico 5 não está atribuído a nenhum dos seis projetos

**Onde.** A divisão informada dos projetos: P1=Épico 1, P2=Épico 2, P3=Épico 3, P4=Épico 4 + HU-19 (exceto HU-15), P5=HU-15, P6=HU-20+HU-21. O Épico 5 (**HU-17** — upload `_EXT`/`_INT`; **HU-18** — upload `CONT_PROC`) não aparece em lugar nenhum.

**Por que é problema.** O Épico 5 é responsabilidade explícita do RPA 3 no relatório de separação. Sem saber onde o código está — ou se existe — não se sabe se o RPA 3 pode ser montado.

**O que bloqueia.** Composição do RPA 3; marco M8.

**Hipóteses.**
1. Está dentro do P4 (que gera exatamente os arquivos carregados). Plausível.
2. Existe um sétimo projeto não mencionado.
3. Não foi implementado — nesse caso M8 vira parte migração, parte desenvolvimento.

**Tratamento.** Pasta `projetos-origem/projeto-7-epico-5-carga-agi/` reservada. **Teste imediato ao receber o P4:** procurar automação apontando para `Detraf > Importar Dados`, `Contestação > Gerenciar`, e escrita no campo `carga_agi`.

**Quem decide.** GP (Btime), com o time de desenvolvimento.

---

## 2. A borda de 1% não fecha entre as fontes

**Onde.** Três textos, três regras:

| Fonte | Texto |
|---|---|
| V2, regras de negócio | *"Se a diferença do `R$_Bruto` for **menor que 1%**, o processo segue sem contestação... Se for **superior** deve ser criada a contestação"* |
| V2, fórmula da aba Contest | *"se a variação for **maior que +1%** ele marca com S"* |
| PDF de HUs | *"< 1%: flag N"* / *"**>= 1%**: flag S"* |

**Por que é problema.** Três ambiguidades numa única regra:
1. **O ponto exato de 1%** — "superior a 1%" exclui o valor; "≥ 1%" inclui.
2. **O sinal** — "+1%" sugere contestar apenas quando a operadora cobrou **a mais**. Sem isso, uma cobrança 5% **abaixo** da expectativa também seria contestada, o que não faz sentido de negócio.
3. **A base do percentual** — variação sobre o valor da operadora ou sobre a expectativa? Dá resultados diferentes.

**O que bloqueia.** Esta é **a** regra de decisão do processo: define, por combinação de operadora × EOT × remuneração × mês, se há ou não contestação formal a uma operadora e retenção de pagamento. Errar aqui tem consequência financeira e jurídica direta.

**Quem decide.** PO / área cliente. Não é decisão técnica.

---

## 3. Data de corte indefinida

**Onde.** V2: *"Data de corte do processo está em análise pela área cliente para termos a regra de reprocessamento e gatilho para batimento da operadora."* E: *"é importante definirmos a data de corte para leitura de e-mails."*

**Por que é problema.** A V2 **removeu** o parágrafo de periodicidade dos RPAs, e com ele o critério V1 "varredura diária após o dia 05". Não há nada no lugar.

**O que bloqueia.**
- Critério de periodicidade da HU-01
- Gatilho do RPA 2 (que roda "após a data de corte")
- Regra de deduplicação quando a mesma operadora envia vários e-mails
- Regra de reprocessamento quando a operadora reenvia depois do corte
- O "gatilho para batimento da operadora", também citado como pendente

**Quem decide.** Área cliente.

---

## 4. Contradição: `_ENV` é cópia de um arquivo que não existe mais

**Onde.**
- HU-09 (V2): *"**Não é necessário gerar o arquivo**, mas usar a lógica e popular a tabela `tbl_rpa_log_detraf_despesa_contestacao`"*
- HU-14 (V2, corpo principal): *"Ele copia o `Base_Contestação_{operadora}_{mesdodetraf}_M` da operadora e salva na pasta com o novo nome `Base Contestação_{operadora}_{mesdodetraf}_ENV`. O robô deixa apenas a aba 'Contest' e a aba da 'TBRA' e apaga as demais."*

**Por que é problema.** A HU-14 opera sobre um arquivo com abas que a HU-09 diz não ser mais gerado. As duas afirmações estão no mesmo documento e não são reconciliadas.

**O que bloqueia.** A implementação da HU-14, e por consequência a HU-15 (o `_ENV` é anexo do e-mail).

**Leituras possíveis.**
- A `Base_Contestação_..._M` é **uma das "duas exceções"** da frase *"todas as planilhas foram substituídas por banco, exceto dois arquivos"* — e continua existindo só para gerar o `_ENV`
- Ou o `_ENV` passa a ser gerado do zero a partir do banco, e o texto da HU-14 é remanescente não atualizado

A primeira é mais coerente com o texto ("exceto dois arquivos... antes da carga no AGI e em caso de contestação"), mas é **inferência**.

**Quem decide.** PO. E a análise do código pode ajudar: ver o que o P3 gera e de onde o P4 lê.

---

## 5. HU-15 — o envio automático só sobrevive em texto revogado

**Onde.** A frase *"o robô deve enviar o e-mail, sem necessidade de autorização do usuário, após a escolha do analista"* **não está no corpo principal da V2**. Ela só aparece no bloco de conteúdo duplicado ao final do documento (ver achado 9), que é remanescente de versão anterior.

**Por que é problema.** O envio do e-mail à operadora é **irreversível e externo**. Uma contestação enviada por engano a uma operadora não se desfaz — tem consequência comercial e possivelmente contratual.

**O que bloqueia.** O fluxo do RPA 3. Enquanto não confirmado, não se deve implementar disparo sem aprovação.

**Quem decide.** PO / área cliente (Luciana / Ana Carolina), explicitamente e por escrito.

---

## 6. CBS/IBS: escopo novo sem história, sem layout e sem dono

**Onde.** V2:
- *"Será destacado em nota fiscal e demonstrativos do DETRAF os novos impostos CBS e IBS, apenas como informativo nesse primeiro ano, a partir de 2027 será feito o devido recolhimento."*
- *"Arquivos de DETRAF VIVO, Carga Geral do AGI e relatórios do AGI possuem três colunas CBS, IBS MUNICIPAL E IBS ESTADUAL."*
- HU-20: *"Comparar colunas CBS, IBS MUNICIPAL E IBS ESTADUAL."*

**Por que é problema.** Afeta o layout dos arquivos (Épico 2), possivelmente a comparação (Épico 3) e explicitamente a conferência (HU-20). Mas:
- Não há HU
- O layout das 15 colunas da V2 **não as inclui**
- Não se sabe se são colunas 16-18 ou se deslocam as existentes
- Não se sabe se o arquivo **da operadora** também as terá, ou só o Detraf Vivo
- Não se sabe se entram na sumarização/comparação da HU-10
- Nenhum projeto de origem foi indicado como responsável

**Agravante.** A V2 registra que *"existe a projeção para que em 2028 mais um imposto seja inserido na tabela deslocando as colunas"*, e que *"os ajustes nos arquivos são dinâmicos; a solução não poderá ficar condicionada a regras de negócio que podem ser alteradas a qualquer momento"*. Junto, isso é um **requisito não-funcional explícito**: o layout dos arquivos precisa ser configurável, não posicional-fixo.

**Quem decide.** PO / área cliente, com apoio da área fiscal.

---

# 🟡 Médios

## 7. A HU-20 é questionada pela própria V2

**Onde.** V2: *"Caso a conferência com o robô dê errado, qual o processo? Esse processo trata–se de uma dupla checagem, conferir com o solicitante se esse processo vale a pena ou não ser mantido."*

**Por que é problema.** Duas questões abertas: (a) a HU-20 continua no escopo? (b) o que fazer quando os valores divergem — não há tratamento além de "sinalizar".

**O que bloqueia.** A **cisão do Projeto 6**. Se a HU-20 for descartada, o P6 fica reduzido à HU-21 e não há cisão a fazer. Isso muda o planejamento do marco M7.

**Urgência.** Alta apesar da severidade média — M7 vem antes de M8.

**Quem decide.** PO / área cliente.

---

## 8. "Todas as planilhas foram substituídas por banco, exceto dois arquivos"

**Onde.** V2, item 2: *"Todas as planilhas deste processo foram substituídas por banco, exceto dois arquivos. Antes da carga no AGI e em caso de contestação com ou sem retenção."*

**Por que é problema.** O fluxo descreve pelo menos **cinco** artefatos de arquivo que continuam existindo: `_EXT`, `_INT`, `_ENV`, carta CT e `CONT_PROC_MASCARA`. Quais são os "dois"?

A frase que segue ("antes da carga no AGI e em caso de contestação com ou sem retenção") sugere que sejam o **arquivo de carga do AGI** e o **arquivo de contestação** — mas isso deixa de fora a carta, que é inegavelmente um arquivo, e não distingue `_EXT` de `_INT`.

**O que bloqueia.** A leitura correta do escopo de artefatos; diretamente ligado ao achado 4.

**Quem decide.** PO.

---

## 9. Bloco de conteúdo duplicado ao final da V2

**Onde.** Depois do item 7 (Risco/Premissas), o `.docx` repete um trecho inteiro de versão anterior — de *"Da mesma forma, o robô copia o conteúdo dos arquivos gerados internamente…"* até *"Retificação de Contestação"*.

**Por que é problema.** O bloco contém regras que foram **deliberadamente removidas** do corpo principal, incluindo as que sustentavam os critérios da HU-15 (achado 5) e da HU-19. Quem citar a V2 sem saber disso pode reintroduzir regra revogada.

**Diferenças verificadas entre o corpo principal e o bloco duplicado:**

| Trecho | Corpo principal (vigente) | Bloco duplicado (antigo) |
|---|---|---|
| Base Contestação | "não é necessário gerar o arquivo, popular a tabela" | gera o arquivo com abas e tabelas dinâmicas |
| Aba do WebFat | "aba Contestação" | "cava Expectativa" (erro de digitação) |
| Encontro de Contas | atualiza campos do banco | "cola na planilha de encontro de contas" |
| Coluna de contestação no EC | ausente | presente |
| `tipo_contestacao` / `carga_agi` | presentes | ausentes |
| CBS/IBS na HU-20 | presente | ausente |
| Envio de e-mail sem autorização | ausente | ⚠️ (frase que sustentava a HU-15) |

**Tratamento.** Registrado em [`../00-fontes/README.md`](../00-fontes/README.md). Ao citar a V2, verificar sempre se a passagem está no corpo principal.

**Quem decide.** GP — idealmente limpando o documento.

---

## 10. `DE_EBT_TBRA_TLF_202509_C_INT_MODELO.xlsx` sem papel definido

**Onde.** V2, etapa de carga: *"Carga dos arquivos com Detraf `DE_EBT_TBRA_TLF_202509_C_INT_MODELO.xlsx` `DE_AGI_D_202506_TBRA_X_{OPERADORA}_EXT` e `..._INT`."*

**Por que é problema.** O arquivo aparece **antes** dos `_EXT`/`_INT`, como se fosse mais um a carregar, mas nada no documento explica o que é. Pelo nome (`_MODELO`, período fixo `202509`, `TLF`, `C`, `INT`) parece um modelo de expectativa TLF — mas isso é especulação. Note também que ele aparece **só no corpo principal**, não no bloco duplicado: é conteúdo **novo** da V2.

**O que bloqueia.** Os critérios de aceitação da HU-17.

**Quem decide.** Área cliente / GP.

---

## 11. O Encontro de Contas é preenchido no RPA 2 ou no RPA 3?

**Onde.** V2, logo após a validação: *"Após a validação de cada arquivo, deve-se popular o Encontro de Contas com o valores total apresentado pela operadora, aberto por tipo de remuneração e EOT Vivo."*

Mas a HU-19 e o relatório de separação colocam o EC no **RPA 3**, depois da contestação. E a V2 também diz, mais adiante: *"Após a contestação, deve-se atualizar a planilha Encontro de Contas com o valor da Contestação."*

**Por que é problema.** Ou são dois momentos distintos (o valor da operadora logo após a validação; o valor da contestação depois), ou é a mesma coisa dita duas vezes em lugares diferentes. Se forem dois momentos, o EC é escrito por **dois RPAs diferentes** — o que muda o desenho.

**O que bloqueia.** Posicionamento da HU-19 e a fronteira RPA 2 / RPA 3.

**Quem decide.** PO, com apoio da análise do código.

---

## 12. Tarifas não reguladas: validar ou apenas classificar?

**Onde.** Dois trechos vizinhos da V2:
- *"As tarifas não reguladas não serão validadas em seu conteúdo, apenas no formato."*
- *"A consulta de tarifas não reguladas é realizada através da tabela de tarifas. Todos os descritores que não estiverem na tabela são tarifas não reguladas."*

**Por que é problema.** Se não são validadas em conteúdo, por que consultá-las na tabela? A leitura mais coerente é que a tabela serve para **classificar** (presente = regulada), não para validar valor — mas o texto não diz isso.

**O que bloqueia.** HU-05.

**Quem decide.** PO / área cliente.

---

## 13. HU-06: o arquivo `_BK` recalcula a linha de total?

**Onde.**
- PDF de HUs: *"Linha de total recalculada no arquivo `_BK`"*
- V2: *"Não é necessário gerar nenhum alarme, apenas criar na mesma pasta o arquivo conforme informado"* — **sem mencionar recálculo**

**Por que é problema.** A V2 é normativa, mas a omissão pode ser acidental (o documento é um resumo do passo a passo, não uma especificação exaustiva). Se o recálculo era necessário e foi omitido, o arquivo `_BK` sai com totais inconsistentes.

**O que bloqueia.** HU-06.

**Quem decide.** PO.

---

## 14. `VLR_BRUTO` descrito como "minutagem total"

**Onde.** V2, HU-16: *"Coluna W: 'VLR_BRUTO' - preencher com a **minutagem** total da linha (colocar o sinal negativo na frente)."*

Texto idêntico ao da coluna I (`DURACAO`).

**Por que é problema.** Pelo nome do campo e pelo contexto (é o valor da contestação carregado no AGI), deveria ser **valor bruto**, não minutagem. É erro de redação evidente — copiar e colar da linha anterior — mas carrega dado financeiro para dentro do AGI.

**O que bloqueia.** HU-16. Erro óbvio, mas precisa de confirmação formal antes de ser "corrigido" na implementação.

**Quem decide.** PO — confirmação, não deliberação.

---

## 15. Descritores de transporte sem regra

**Onde.** V2: *"Descritores de transporte devem ser validados a partir da tabela Descritor_Remuneração (**aguardando informação do solicitante**)."*

**Por que é problema.** "Transporte" aparece na lista de Tipos de Produto da HU-10, então existe tráfego dessa natureza. Mas a regra de validação do descritor está declaradamente pendente.

**O que bloqueia.** HU-05, parcialmente. E impede que o mapeamento descritor → remuneração seja promovido integralmente à base comum (critério C3).

**Quem decide.** Solicitante / área cliente — a própria V2 diz isso.

---

## 16. "Avalia possível correção automática" sem regra

**Onde.** V2: *"Caso o erro seja no arquivo de expectativa, **avalia possível correção automática** e envia o resultado para a tabela `tbl_rpa_log_detraf_despesa_arquivos`."*

Na documentação V1, isso era "correção manual ou abertura de chamado".

**Por que é problema.** Não há regra que diga o que é corrigível automaticamente, como, nem o que fazer quando não é. É mudança significativa de comportamento expressa numa frase.

**O que bloqueia.** HU-08. E, se houver código implementando alguma "correção automática", ele estará implementando decisão não documentada.

**Quem decide.** PO — confirmar se é decisão de produto validada ou apenas intenção de redação.

---

## 17. Memória local × servidor WebFat × Lagoa

**Onde.** V2, item 2.13: *"O robô irá atuar com a memória da máquina local. O RPA irá salvar na pasta local para que seja integrado ao Webfat. O Webfat terá a opção do analista transferir o arquivo para o Lagoa."*

Mas a HU-03 determina salvar direto na pasta de rede Lagoa **e** no servidor do WebFat.

**Por que é problema.** São três locais e dois fluxos incompatíveis: ou o robô salva direto no Lagoa, ou salva local, integra ao WebFat, e a transferência para o Lagoa passa a ser **manual, acionada pelo analista**. A segunda leitura muda a natureza da HU-03 e introduz um passo humano onde não havia.

**O que bloqueia.** HU-03, e o desenho de armazenamento do RPA 1 e do RPA 3.

**Quem decide.** Área cliente / GP.

---

## 18. HU-02: efeitos colaterais da mudança de mecanismo

**Onde.** A V2 troca a identificação da operadora do **domínio do remetente** para a **EOT da Credora lida no arquivo**.

**Por que é problema.** A mudança é clara, mas suas consequências não foram tratadas:
- Agora é preciso **abrir o anexo** antes de saber onde salvá-lo. O que fazer se o arquivo estiver corrompido, protegido por senha, ou com a coluna Credora vazia?
- E se um e-mail trouxer anexos de **mais de uma operadora**?
- E se a EOT não existir no Anexo 5?
- A "tabela de contatos do WebFat", que a V1 usava, ainda existe? A HU-15 precisa dela para os destinatários.

**O que bloqueia.** Casos de exceção da HU-02 e da HU-15.

**Quem decide.** PO, para as regras de exceção.

---

## 19. Nome da operadora muda entre a contestação e a retificação

**Onde.** V2, HU-21: *"Empresa: Operadoras que no anexo 5 possui um nome que sofrem alterações durante o processo, esse ponto de atenção precisa ser estudado. **Pendência Vivo para mapear essa ponta.**"*

**Por que é problema.** O filtro do AGI na retificação é por **nome da empresa**. Se o nome mudou entre o mês da contestação e o da retificação, o robô não encontra o processo. A própria V2 reconhece e registra como pendência da Vivo.

**O que bloqueia.** HU-21, e portanto o RPA 4 inteiro.

**Quem decide.** Vivo — já registrado como pendência deles.

---

## 20. Numeração CT sem controle de concorrência

**Onde.** V2, HU-14: *"O robô altera a numeração da carta a partir de um controle de numeração que fica na rede... O robô pega a última numeração e usa na sua nova numeração o número seguinte."*

**Por que é problema.** É estado compartilhado numa **pasta de rede**, lido e incrementado sem transação nem trava. Duas execuções simultâneas — ou o robô junto com um humano criando uma carta manualmente — podem gerar duas cartas com o mesmo número. Cartas de contestação são documentos formais enviados a terceiros; numeração duplicada é problema de controle documental.

**O que bloqueia.** Não bloqueia a implementação, mas é risco operacional real que a documentação não trata.

**Quem decide.** Área cliente (sobre a criticidade) + decisão técnica em F4 (sobre a trava).

---

## 21. O desenvolvimento do WebFat faz parte deste projeto?

**Onde.** V2: *"No Webfat temos como sugestão a criação de uma nova tela, chamada de consolidado despesas e filtro com alguma marcação que demonstre o erro do arquivo! ... Para isso, uma nova tela no Webfat foi desenvolvida."*

**Por que é problema.** A frase mistura sugestão ("temos como sugestão") e fato consumado ("foi desenvolvida"). Não fica claro se o WebFat é entrega deste projeto ou de outra frente. Se for de outra frente, é **dependência externa** do RPA 2 (que grava para exibição) e do RPA 3 (cujo gatilho é a decisão tomada nessa tela).

**O que bloqueia.** O gatilho do RPA 3 e o mecanismo de sinalização do analista.

**Quem decide.** GP.

---

# 🟢 Baixos

## 22. Célula O87 e o destino do consolidado do EC

**Onde.** V2, HU-20: *"Compara com os valores totalizados no EC no Subtotal despesa (**célula O87**)."* E, logo adiante: *"O robô precisa chegar nesse valor consolidado e **copular** [popular] **em algum lugar**. Parecendo com a planilha dos encontro de contas."*

**Por que é problema.** A referência à célula O87 pressupõe uma planilha que a V2 substituiu por banco. E a frase seguinte admite abertamente que o destino do consolidado **não está definido**.

**O que bloqueia.** HU-20 — que, por sua vez, pode ser descartada (achado 7).

---

## 23. Interface com as demandas irmãs não descrita

**Onde.** V2: *"ATA0000571 / ATA0000567 / ATA0000572 — as 3 demandas junto com esta em questão formam todo o fluxo de faturamento do Detraf que está se automatizando."*

**Por que é problema.** Sabe-se que existem e que formam o mesmo fluxo, mas não há descrição de interface, dado compartilhado ou ordem de execução. O ICT, que gera os arquivos de expectativa, é citado como "processo de captura e conversão realizado no início do processo de detraf (detalhado junto com o processo da receita)" — ou seja, documentado em **outra** demanda.

**Impacto na unificação.** Baixo agora — mas se algum projeto de origem contiver código do fluxo de Receita, isso é escopo fora deste MVP e precisa ser identificado.

---

## 24. Separação VIVO/TLF sem critério

**Onde.** V2: *"Todos os arquivos de expectativa Vivo estarão separados por pastas VIVO e TLF com 'D' no final."*

**Por que é problema.** Não se explica o critério de separação, nem o que significa o "D" no final, nem como isso se relaciona com o filtro `_D_` no nome dos arquivos.

**O que bloqueia.** Detalhe da HU-03 / HU-04.

---

## 25. Layout do banco não publicado

**Onde.** A V2 cita quatro tabelas e vários campos, mas nunca o DDL.

**Por que é problema.** As listas de campos conhecidas são apenas as citadas em texto e **não devem ser assumidas como completas**. Na análise do código, campos gravados que não constam da documentação são achado — podem ser necessidade real não documentada ou resíduo.

**O que bloqueia.** Nada imediatamente; é ponto de atenção da análise.

---

## Encaminhamento

Todos os achados estão consolidados como perguntas endereçáveis em [`duvidas-pendentes.md`](duvidas-pendentes.md), com destinatário e o que fica bloqueado até a resposta.
