# Regras de Negócio Consolidadas

> ⚠️ **Fotografia da etapa documental (2026-07-30).** Este documento foi escrito
> **antes** de qualquer código chegar, e descreve o entendimento daquele momento.
> Vários pontos já mudaram — em especial: o Épico 5 **tem** projeto (o P7, entregue
> em 2026-08-04), e as HUs 12 a 19 estão implementadas e orquestradas.
>
> **Fonte do estado atual:** `docs/04-relatorios/duvidas-pendentes.md` (pendências),
> `matriz-de-rastreabilidade.md` (HUs) e `unificado/README.md` (código).

> Fonte normativa: V2, item 3 (Regras de negócio) e item 4 (Passo a passo). Complementada pelo PDF de HUs onde a V2 é omissa — e essas complementações estão marcadas.

Este documento reúne, num só lugar, as regras que a próxima etapa vai usar para julgar se o código faz a coisa certa. Ele **não** propõe implementação.

---

## 1. Layout do arquivo de Detraf

15 colunas. Vale para o arquivo da operadora **e** para o de expectativa Vivo.

| # | Nome | Regra de validação |
|---|---|---|
| 1 | **Credora** | EOT relacionada à operadora. Base de busca: **Anexo 5** |
| 2 | **Devedora** | EOT da **Vivo**. Base de busca: Anexo 5 |
| 3 | **Referencia** | Apenas **mês corrente −1**, formato `AAAAMM` |
| 4 | **Tráfego** | Meses corrente −1, −2 ou −3, formato `AAAAMM` |
| 5 | **POI** | Escrita livre, preenchimento **não obrigatório** |
| 6 | **Rel** | Normalmente `0` nas linhas de tráfego e `1` nas linhas de total/subtotal. **Pode estar vazia** |
| 7 | **DESC** | Descritor correspondente à remuneração descrita no nome do arquivo |
| 8 | **GH** | Apenas `S`, `R`, `N` ou `D` |
| 9 | **Chamadas** | Apenas números **inteiros** |
| 10 | **Minutos** | Números com **até 1** casa decimal |
| 11 | **Tarifa** | Números com **no máximo 5** casas decimais. Ver seção 3. **Não existe tarifa zero** |
| 12 | **R$_Liq** | Valor com até 2 casas decimais |
| 13 | **PIS_Cofins** | Valor com até 2 casas decimais |
| 14 | **ICMS** | Valor com até 2 casas decimais |
| 15 | **R$_Bruto** | Valor com até 2 casas decimais |

**Tolerâncias de formato declaradas pela V2:**
- Algumas operadoras enviam o Detraf **sem cabeçalho** — deve ser aceito, desde que siga o mesmo padrão.
- Algumas enviam uma **aba adicional de resumo** — deve ser **desconsiderada**.

**Regra geral de erro.** *"Caso as regras não sejam validadas, os registros devem ser direcionados para um arquivo de mesmo nome com `_ERRO` no final da sua nomenclatura."* Aplica-se a **qualquer** regra violada, não a um caso específico.

⚠️ **CBS, IBS Municipal e IBS Estadual não constam neste layout**, embora a V2 afirme que os arquivos de Detraf Vivo passam a tê-las. Posição, obrigatoriedade e aplicabilidade ao arquivo da operadora: indefinidas.

---

## 2. Descritores

O descritor (coluna 7) determina a remuneração, e sua forma deriva do **tipo de serviço da EOT Credora** no Anexo 5.

### 2.1 Formação do descritor

| Condição da EOT Credora (Anexo 5) | Final do descritor |
|---|---|
| Tipo de Serviço = **SMP** | `"V"` |
| Tipo de Serviço = **STFC** | `"I"` ou `"L"` |

### 2.2 Descritor → remuneração

| Remuneração | Regra |
|---|---|
| **VUM** | final `"V"` |
| **TU-RL** | final `"L"` |
| **TURIU1** | início `"L"` e final `"I"` |
| **TURIU2** | início ≠ `"L"` e final `"I"` |
| **TUCOM** | final `"C"` |

A relação completa está em **`tbl_detraf_mapeamento_descritores`** (banco WebFat) e na planilha Descritor_Remuneração.

⚠️ **Descritores de transporte:** a V2 diz que devem ser validados a partir da tabela Descritor_Remuneração, mas anota "**aguardando informação do solicitante**". **Sem regra definida.**

### 2.3 Caso L…V — arquivo `_BK`

Quando o arquivo (da operadora **ou** de expectativa Vivo) apresenta:
- descritor com **início "L" e final "V"**, **e**
- EOTs envolvidas com Tipo de Serviço = **SMP**, **e**
- **não** PMS (coluna Concessão do Anexo 5 ≠ `"P"`)

então:
1. Fazer uma **cópia** do arquivo
2. Acrescentar **`_BK`** ao final do nome
3. Salvar na **mesma pasta** do original (Detrafs Recebidos ou Detrafs Enviados)
4. **Não gerar nenhum alarme** — operação silenciosa

⚠️ O PDF de HUs acrescenta "linha de total recalculada no arquivo `_BK`". A V2 **não menciona** recálculo. A confirmar.

### 2.4 Caso L…L — STFC

Quando o descritor tem **início "L" e final "L"** e as EOTs são do tipo **STFC**, o tráfego deve ser criticado no arquivo da operadora — que deve reenviar sem esses registros — e/ou retirado do arquivo de expectativa de despesa da Vivo.

**Na V2 este caso não tem mais fluxo próprio:** segue a regra geral de `_ERRO`. Ver [`entendimento-das-historias.md`](entendimento-das-historias.md#hu-07--tratamento-de-erro-l-l-stfc-).

---

## 3. Tarifas

### 3.1 Reguladas × não reguladas

- **Reguladas:** valor validado contra `tbl_detraf_tarifas`.
- **Não reguladas:** *"não serão validadas em seu conteúdo, apenas no formato"*.
- Critério de classificação: *"Todos os descritores que não estiverem na tabela são tarifas não reguladas."*
- **Não existe tarifa zero** — em nenhum caso.

⚠️ **Ambiguidade.** A V2 também diz "a consulta de tarifas não reguladas é realizada através da tabela de tarifas", o que contradiz "não serão validadas em seu conteúdo". A leitura mais coerente é que a tabela serve para **classificar** (presente = regulada), não para validar valor de não regulada — mas isso é inferência.

### 3.2 Consulta em `tbl_detraf_tarifas`

| Campo | Significado |
|---|---|
| `tipo_remuneracao` | Remuneração da tarifa, identificada pelo descritor do arquivo × campo `regra_desc` da tabela |
| `região` | Região da EOT da **Credora** presente no arquivo |
| `eot_vivo` / `eot_operadora` | Exceções à regra de região. Na **despesa**: `eot_vivo` = **DEVEDORA**; `eot_operadora` = **CREDORA** |
| `gh` | Grupo horário. **Nulo = vale para todos os grupos horários** |
| `tarifa` | Valor a validar |
| `data_inicio` / `data_fim` | Período do tráfego — considerar **apenas o mês** |

### 3.3 Tabela de tarifas reguladas (referência da V2)

| Região | VUM N | VUM R (STFC) | VUM R (SMP) | TU-RL N | TU-RL R | TU-COM N | TU-COM R | TURIU1 | TURIU2 |
|---|---|---|---|---|---|---|---|---|---|
| Região I | 0,01499 | 0,01049 | 0,01499 | 0,00605 | 0,00423 | 0,00302 | 0,00211 | 0,00716 | 0,00651 |
| Região II | 0,01686 | 0,0118 | 0,01686 | 0,00608 | 0,00425 | 0,00304 | 0,00212 | 0,00721 | 0,00657 |
| Região III | 0,01779 | 0,01245 | 0,01779 | 0,0061 | 0,00427 | 0,00305 | 0,00213 | 0,00732 | 0,00663 |
| RII (943) – SERCOMTEL (042/043)\* | — | — | — | 0,00607 | 0,00424 | — | — | 0,00729 | 0,00665 |

\* Valor para CREDORA (042/043) e DEVEDORA (943).

⚠️ **Estes valores são referência documental, não fonte de verdade.** A fonte é `tbl_detraf_tarifas`, e a premissa 10.4 da V2 exige que a tabela seja **editável e gerenciável pelo usuário**. Valores fixos no código violam a premissa.

### 3.4 Regra do horário reduzido da VU-M

Na VU-M em horário reduzido, considerar o **tipo de serviço da operadora DEVEDORA** (campo do Anexo 5): se atua como STFC é um valor, se atua como SMP é outro. Daí as duas colunas `VUM R (STFC)` e `VUM R (SMP)` na tabela acima.

### 3.5 Dupla convivência em fevereiro

As tarifas reguladas mudam **uma vez por ano, em fevereiro** — e apenas em fevereiro.

O motivo, na V2: o Detraf é consolidado até **24/02**, mas há tráfego entre 25/02 e o encaminhamento de fevereiro. O reajuste cai nessa janela, gerando **duas tarifas válidas para a mesma remuneração** no mês de fevereiro.

**Consequência prática:** como a coluna Tráfego aceita até mês −3, uma tarifa de fevereiro pode continuar válida no Detraf de **março, abril e maio**. Ou seja, a dupla convivência não é um problema de um mês, mas de quatro.

A alteração dos valores deve ser liberada e gerenciada pelo usuário de Detraf.

### 3.6 Tabela SMP

Recebe os valores das EOTs móveis da Vivo, identificáveis no Anexo 5 pelo campo "tipo de serviço" = "SMP". O resultado deve ser preenchido **por cada EOT da Vivo**.

---

## 4. Consolidação e comparação

### 4.1 O que entra

- Dados da operadora: todos os arquivos de "Detraf Recebidos", **sem as linhas de total (`Rel = 1`)**, de forma sequencial
- Dados de expectativa Vivo: arquivos com **`_D_`** no nome, até a coluna `R$ Bruto`, também sem linhas de total
- **Destino: `tbl_rpa_log_detraf_despesa_contestacao`** — a V2 é explícita: *"Não é necessário gerar o arquivo, mas usar a lógica e popular a tabela"*

### 4.2 Ausência de par

*"Caso tenha arquivo de detraf de uma operadora mas não o de expectativa, deve-se preencher a tabela normalmente e apresentar os valores zerados de expectativas. Os dados da operadora são considerados para o preenchimento da tabela."*

Ou seja: **o dado da operadora sempre entra**; a expectativa ausente vira zero. Isso significa que a variação nesse caso será de 100%, e o caso irá para contestação.

### 4.3 Chave de sumarização

Comparar os sumarizados de **`Minutos`** e **`R$_Bruto`** por:
- **EOT devedora**
- **tipo de tarifação** (remuneração)
- **mês de tráfego**

Com desdobramento por **Tipo de Operação** × **Tipo de Produto**:

| Dimensão | Valores |
|---|---|
| **Tipo de Operação** | SMP, STFC — baseado na EOT Vivo e no tipo de serviço dela |
| **Tipo de Produto** | TU-RL, TU-RIU, VU-M, MMS, SMS, Transporte, SIP, Bill&Keep, TU-COM, entre outros — baseado na tabela Descritor_Remuneração |

**Exceção Bill&Keep:** exige adicionalmente que **ambas** as EOTs tenham tipo de serviço = SMP.

**Apresentação:**
- Tabela **SMP**: uma linha por EOT móvel da Vivo
- Tabela **STFC**: EOTs fixas da Vivo (011, 200 e 9\*\*) **sumarizadas numa única linha**, com as colunas EOT Operadora, Referência e Tráfego
- Desejável: **Grupo Horário** na visualização, por filtro ou desdobramento

### 4.4 ⚠️ Regra de decisão — a borda de 1% não fecha

| Fonte | Texto |
|---|---|
| V2, item 3 | *"Se a diferença do `R$_Bruto` for **menor que 1%**, o processo segue sem contestação e deve ser logo carregado no AGI. Se for **superior** deve ser criada a contestação"* |
| V2, aba Contest | *"se a variação for **maior que +1%** ele marca com S"* |
| PDF de HUs | *"Variação `R$_Bruto` **< 1%**: flag N"* / *"**>= 1%**: flag S"* |

Três problemas:
1. **O ponto exato de 1%** cai em lugares diferentes: "superior a 1%" exclui, "≥ 1%" inclui.
2. **O sinal.** "+1%" sugere que só se contesta quando a operadora cobrou **a mais**. As outras fontes falam em "diferença", sem sinal. Se o sinal não for considerado, uma cobrança 5% **abaixo** da expectativa também seria contestada.
3. **A base do percentual.** Variação sobre o valor da operadora ou sobre a expectativa? Não está dito.

Como é a regra que decide o desfecho financeiro de cada caso, precisa ser resolvida antes da implementação.

### 4.5 Resultado

- `"S"` → contestar
- `"N"` → não contestar; segue direto para carga no AGI

---

## 5. Contestação

### 5.1 Decisões do robô

1. Contestação por **Referência** ou por **Tráfego**
2. **Modalidade** — uma das opções das colunas I, J e K da aba `Remuneração` do `CONT_PROC_MASCARA`: escolhe o tipo (coluna K), depois a descrição (coluna J), e usa o número (coluna I) na coluna `ID_MODALIDADE`
3. **Com ou sem retenção** — na prática **decidida pelo analista**: *"a escolha se a contestação será retida ou não dependerá do usuário, após sua análise"*
4. Se há **retificação** a fazer (tráfego contestado no período anterior recuperado neste)

### 5.2 O que cada cenário produz

| Artefato | Sem contestação | SEM retenção | COM retenção |
|---|---|---|---|
| `_EXT` | ✅ | ✅ | ✅ |
| `_INT` | ❌ | ❌ | ✅ |
| `_ENV` | ❌ | ✅ | ✅ |
| Carta CT | ❌ | ✅ | ✅ |
| E-mail | ❌ | ✅ | ✅ |
| `CONT_PROC` | ❌ | ✅ | ✅ |

**Definições:**
- **SEM retenção:** enviar à operadora carta e arquivo com a expectativa da Vivo, e carregar no AGI o apresentado pela operadora com indicativo de contestação sem retenção.
- **COM retenção:** o mesmo, com indicativo de retenção, **mais** a carga no AGI da expectativa gerada pelo ICT **somente para o tráfego contestado**.

### 5.3 Campos fixos dos arquivos de carga

| Campo | `_EXT` | `_INT` |
|---|---|---|
| ORIGEM | `"E"` | `"E"` |
| EXPECTATIVA | `"S"` nas linhas contestadas COM retenção, `"N"` nas demais | `"N"` |
| INSERÇÃO | `"EXTERNO"` | `"EXTERNO"` |
| AJUSTE | em branco | em branco |
| OBS | em branco | em branco |
| REMUNERACAO | tabela Descritor_Remuneração | tabela Descritor_Remuneração |

Ambos colam os dados a partir da célula **A2**.

### 5.4 `CONT_PROC` — colunas preenchidas

| Coluna | Campo | Conteúdo |
|---|---|---|
| C | `ID_OPERADORA_JV` | EOT da Vivo que gera a contestação — uma linha móvel (SMP) e uma fixa |
| D | `ID_OPERADORA_PREST` | EOT da operadora contestada |
| E | `ID_PERIODO_REF` | Mês do Detraf da contestação |
| F | `ID_PERIODO_TRAF` | Mês do tráfego contestado — mais de um mês abre em mais linhas |
| G | `DEBIT_CREDIT` | `"D"` — é despesa |
| H | `FLAG_PAG_REC` | `"P"` se retida, `"R"` se não retida |
| I | `DURACAO` | Minutagem total da linha, **negativa** |
| W | `VLR_BRUTO` | ⚠️ A V2 escreve "minutagem total"; deveria ser **valor bruto**, **negativo** |
| AB | `ID_MODALIDADE` | Das colunas I e J da aba `Remuneração` |
| AG | `REMUNERACAO_FIXA` | Tipo de remuneração, baseado no descritor |

**Regra de agregação:** pode-se criar uma única linha para a Vivo móvel e uma para a Vivo fixa com o total, **mas respeitando a diferença de tipo de remuneração e de mês de tráfego** — não se pode sumarizar contestações de remunerações diferentes.

Um único arquivo pode conter contestação de mais de uma operadora. Formato `.xls`.

### 5.5 Carta

- Modelo pré-existente **por operadora**
- Numeração **CT sequencial**, lida do controle em `\\lagoa\...\Correspondências Enviadas\CT\{ano}` — pega a última e usa a seguinte
- Altera: número, data, mês do Detraf no "Assunto:", tipo de contestação ("SEM retenção" / "COM retenção")
- Inclui no corpo as tabelas da aba `Contest` do `_ENV`, **sem a coluna "Contestação a enviar"**
- Cópia salva em `Correspondências Enviadas\CT\{ano}`

### 5.6 E-mail

```
Assunto: CONTESTAÇÃO_TBRA|{NOMEDAOPERADORA}_{MESDODETRAF}

Prezados,
Segue a contestação para a sua análise e validação, referente ao mês {mesdodetraf}

Att,
```
Anexos: carta + `Base Contestação_{operadora}_{mês}_ENV`
Destinatários: contatos das operadoras

---

## 6. Encontro de Contas

- Valor de despesa total apresentado pela operadora (**minutos e valor bruto**)
- Aberto por **EOT da Vivo** e **tipo de remuneração**
- **Sempre com sinal negativo**
- Mapeamento descritor → coluna pela tabela Descritor_Remuneração
- **Destino (V2): campos de `tbl_rpa_log_detraf_despesa_contestacao`** — `minutos_operadora`, `vb_operadora`, `minutos_diferenca`, `vb_diferenca`, `minutos_variacao_perc`, `vb_variacao_perc`

⚠️ **Conflito de posicionamento no fluxo.** A V2 diz, no bloco de validação: *"Após a validação de cada arquivo, deve-se popular o Encontro de Contas com o valores total apresentado pela operadora, aberto por tipo de remuneração e EOT Vivo"* — o que colocaria o EC no **RPA 2**. Mas a HU-19 e o relatório de separação colocam o EC no **RPA 3**, depois da contestação. Pendência.

---

## 7. Conferência (Relatório Receitas e Despesas)

- `AGI > Relatórios > Detraf > Receitas e Despesas`
- Filtrar por **período do Detraf**, natureza **"D"** e nome da operadora
- Sumarizar a coluna `Vlr. Bruto` (a V2 nota que "é possível extrair os dados da tela")
- Comparar com o subtotal de despesa do EC — a V2 cita a célula **O87** ⚠️ (referência a uma planilha que a V2 substituiu por banco)
- **Comparar também CBS, IBS MUNICIPAL e IBS ESTADUAL**
- Repetir para todas as operadoras

⚠️ **A V2 questiona a própria existência desta etapa:** *"Esse processo trata-se de uma dupla checagem, conferir com o solicitante se esse processo vale a pena ou não ser mantido."* E não define o que fazer quando os valores divergem.

---

## 8. Retificação (Recuperação)

**Quando:** o robô identifica que um tráfego contestado foi recuperado no mês seguinte (variação negativa).

**Como:**
1. `AGI > Contestação > Gerenciar`
2. Filtrar por **Período** (o período em tratamento) e **Empresa**
3. Clicar no **Id Processo** desejado
4. `+ Adicionar`, "Tipo Evento" = **"Recuperação"**
5. Preencher com a **diferença entre o Detraf da Vivo e o Detraf da operadora**:

| Campo | Fórmula |
|---|---|
| Duração | Minutos da tabela |
| Valor Líquido | `VB × 0,9635` |
| Valor PIS Cofins | `VB − Valor Líquido` |
| Valor Bruto Negociado | `VB` |

6. Salvar

⚠️ **Pendência da V2:** *"Operadoras que no anexo 5 possui um nome que sofrem alterações durante o processo, esse ponto de atenção precisa ser estudado. Pendência Vivo para mapear essa ponta."* O filtro do AGI é por nome, e o nome pode mudar entre a contestação e a retificação.

⚠️ **O fator `0,9635`** corresponde a PIS/Cofins de 3,65%. É constante embutida na especificação, e as premissas 10.3/10.4 exigem regras editáveis pelo usuário. Com CBS/IBS a partir de 2027, tende a mudar.

---

## 9. Requisitos não-funcionais explícitos

Da seção de premissas e riscos da V2. São **requisitos**, não observações:

1. *"As regras de negócio devem ser editáveis e acessadas pelo usuário para que possa incluir, editar ou finalizar a sua aplicação."*
2. *"As tabelas de consulta devem ser editáveis e gerenciáveis pelos usuários para que tenham autonomia na edição dos valores."*
3. *"Os ajustes nos arquivos são dinâmicos. A solução não poderá ficar condicionada a regras de negócio que podem ser alteradas a qualquer momento."*
4. Projeção de **novo imposto em 2028 deslocando as colunas**.

**Leitura conjunta:** tarifas, mapeamento de descritores, layout de arquivo e limiares não podem ser constantes no código. ⚠️ Verificar aderência é item obrigatório do checklist de análise de cada projeto — e uma violação encontrada é dívida técnica a tratar na unificação, não algo a replicar.

---

## 10. Tratamento de erro

| Origem do erro | Tratamento |
|---|---|
| Arquivo **da operadora** | Criticar e acionar a operadora por e-mail, com opção de correção ou reenvio de novo e-mail com arquivos válidos |
| Arquivo **de expectativa** | Disponibilizar via WebFat para a área usuária; *"avalia possível correção automática"* ⚠️ regra não definida |
| **Qualquer** regra violada | Registros para arquivo `_ERRO` de mesmo nome |
| Erro no **processamento** | *"o robô seguirá para o próximo processamento"* — não para. Erro apresentado via WebFat, pela tabela do banco, **sem detalhamento**, apenas alerta em vermelho |
| Arquivos **divergentes** da operadora | Status **"não validado"** no WebFat, com comunicação visual em vermelho |
| Reenvio com **mesmo nome** | Sobrescreve o anterior e **inicia novo processamento**, seguindo a regra de corte |

**Nomenclatura por status** (V2): `_ENV` = pronto para envio; `_ERRO` = erro em alguma parte do arquivo.
