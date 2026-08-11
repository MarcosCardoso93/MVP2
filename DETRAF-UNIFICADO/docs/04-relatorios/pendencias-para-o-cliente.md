# Pendências para encaminhamento — DETRAF MVP2

**Data:** 2026-08-05 · **Origem:** Btime (GP/dev) · **Demanda:** GSA ATA0000574

---

## Para que serve este documento

O código dos quatro RPAs está unificado e testado (**577 testes automatizados,
quatro suítes verdes**). O que sobrou não depende de mais desenvolvimento: são
**perguntas cuja resposta só o cliente tem**, e cada uma delas está listada aqui
com a citação literal da especificação, o que ela trava e o que já foi feito para
não ficar parado.

Cada item traz, quando existe, **o comportamento provisório adotado** — para que a
resposta seja uma confirmação ou uma correção, e não uma decisão do zero.

Referências: `¶N` remete ao parágrafo do `.docx` normativo (V2). "V1" é o
`DETRAF_MVP2_Historias.pdf`, histórico.

**Estado detalhado e histórico de cada item:**
[duvidas-pendentes.md](duvidas-pendentes.md).

> 📎 **Atualizado em 2026-08-06.** As imagens embutidas no `.docx` normativo —
> dois prints do MySQL Workbench, entre outros — responderam **três** destas
> pendências e encolheram outras quatro. Ver
> [pendencias-respondidas-pelos-anexos.md](pendencias-respondidas-pelos-anexos.md)
> e a conferência contra o código em
> [relatorio-conferencia-dos-anexos.md](relatorio-conferencia-dos-anexos.md).

---

# 📌 PO / GER-AC

## Q6 — CBS, IBS Estadual e IBS Municipal: onde ficam no layout?

> ¶702 — *"Comparar colunas CBS, IBS MUNICIPAL E IBS ESTADUAL."*

A V2 afirma que as três colunas existem no Detraf Vivo, na Carga Geral do AGI e
nos relatórios, e manda compará-las na HU-20. Mas **o layout de 15 colunas não as
inclui**, e nenhuma HU descreve de onde elas vêm.

**O que já foi apurado.** O CSV entregue dentro do próprio Projeto 6 tem **22
colunas**, incluindo `Vlr. CBS`, `Vlr. IBS Estadual` e `Vlr. IBS Municipal` — o que
confirma que elas existem no relatório do AGI. As três **já são somadas e
reportadas** pela HU-20.

**O que ainda falta.** Duas coisas:

1. **O layout dos arquivos** — o "isnumos" do ¶368. São as colunas 16, 17 e 18, ou
   deslocam as existentes? O arquivo **da operadora** também as terá?
2. **A contra-parte no Encontro de Contas** — a tabela do WebFat só tem
   `vb_operadora`, sem coluna de imposto. Não há contra o que comparar.

Por isso a comparação da HU-20 continua **só sobre o valor bruto**. Não é omissão:
é o limite do dado que existe.

### 🔴 E há uma terceira coisa, descoberta em 2026-08-06

O item 7 (Risco) da própria V2 diz:

> *"Existe a projeção para que em 2028 mais um imposto seja inserido na tabela
> **deslocando as colunas**."*

Ou seja: o imposto novo **não** entra no fim do arquivo. Ele entra no bloco de
impostos e **empurra `R$_Bruto` para a direita**.

Nossa validação de layout é **posicional** — por decisão de 2026-07-31, porque os
nomes das colunas não batem com os da V2 e variam por operadora. Quando o
deslocamento acontecer, toda leitura por índice passa a ler a coluna errada — **e
continua lendo um número**. A validação aprova, a apuração usa ICMS onde deveria
usar valor bruto, e **nada acusa**.

Isso torna a resposta a esta pendência mais urgente do que parecia: não é só sobre
somar três colunas novas, é sobre **como o robô vai saber qual layout está
lendo**. Precisamos do layout em "isnumos", e de saber se os arquivos futuros
terão cabeçalho confiável.

**Trava.** Layout de arquivo (HU-04), comparação (HU-10), o fechamento da HU-20 —
e, a partir de 2028, a correção de toda a apuração.

---

## Q11 — A coluna W do `CONT_PROC` recebe valor ou minutagem?

> ¶643 — *"Coluna W: 'VLR_BRUTO' - preencher com a **minutagem** total da linha."*

O texto é **idêntico ao da coluna I** (`DURACAO`), numa coluna chamada
`VLR_BRUTO`. É erro de redação evidente — mas é **dado financeiro carregado no
AGI**, e por isso não corrigimos por conta própria.

**Comportamento adotado.** A coluna W recebe o **valor bruto**, com sinal
negativo.

**O que precisamos.** Só a confirmação de que a leitura está certa.

---

## ✅ Q13 — "avaliar possível correção automática" — **FECHADA**

Os dois parágrafos **seguintes** ao ¶424 descrevem tratamento **humano**: expor o
erro no WebFat para a área usuária, alerta em vermelho, seguir para o próximo
arquivo. Não há correção feita pelo robô, e o Fluxograma AS IS confirma.

O comportamento adotado já era esse. **Só registramos a leitura; nada a decidir.**

---

## Q16b — Casos de exceção da identificação da operadora (HU-02)

A V2 mudou a identificação para a EOT da Credora lida **dentro do arquivo**, o que
obriga a abrir o anexo antes de saber onde salvá-lo. Quatro casos ficaram sem
regra:

1. arquivo corrompido, protegido por senha ou que não abre;
2. coluna Credora vazia;
3. EOT que não existe no Anexo 5;
4. e-mail com anexos de **mais de uma operadora**.

**Comportamento adotado.** A V2 dá uma regra genérica (¶339/¶340/¶390) — registrar
o erro e sinalizar no WebFat —, e é ela que está implementada. **Falta só
confirmar que serve para os quatro casos.**

---

## ✅ N4 — `tipo_lote` × `tipo_registro` — **FECHADA**

O DDL real mostra `tipo_registro enum('DETRAF','EXPECTATIVA','ERRO') NOT NULL`, e
o mockup do WebFat tem exatamente essas abas. **O código já gravava só esses
três** — os quatro valores eram parâmetro interno, mapeados antes de qualquer
escrita. **Nada a fazer dos dois lados.**

---

# 🗄️ DBA / GP-Vivo

## ✅ Q22 — FECHADA em 2026-08-06

O DDL nunca tinha sido publicado. **Foi obtido direto do banco**, com
`espelhar_banco.py`, e está versionado em
`unificado/banco_de_dados/schema-real-20260806.sql` — `SHOW CREATE TABLE` das
cinco tabelas. Não é preciso pedir nada ao DBA neste item.

A leitura também fechou **N1** (a tabela de log existe com o nome da V2) e
confirmou **N10** (`tarifa` é `float`).

### 🔴 O que ela derrubou

O schema presumido estava errado em três pontos, e **cada um quebrava em
execução**. Nenhum aparecia na suíte de testes: os *fixtures* declaravam o schema
presumido, então os testes validavam a suposição.

| Presumido | Real | Efeito |
|---|---|---|
| `tbl_anexo5_processado` com acento (`Região`, `Tipo de Serviço`, `Concessão`, `Endereço de Correspondência`) | **sem acento** (`Regiao`, `Tipo de Servico`, `Concessao`, `Endereco de Correspondencia`) | `KeyError` nos três RPAs |
| `remuneracao` na contestação | **`remuneracoes`** (plural) | coluna-chave: derrubava o INSERT do RPA 2 e o UPDATE do RPA 3 |
| `vb_contestacao` presente | **ausente** | ver abaixo |

Os dois primeiros **já foram corrigidos no código**.

---

## Q24 (banco) — um único `ALTER TABLE`

### ❌ Retirado: o pedido de criar `remuneracao`

A versão anterior deste documento pedia a criação de `remuneracao` em
`tbl_rpa_log_detraf_despesa_contestacao`, apresentando-a como coluna acrescentada
pela unificação em 2026-07-28. **O pedido está retirado.**

A coluna sempre existiu, com outro nome: **`remuneracoes`**. Os valores confirmam
que é o mesmo campo — guarda **um** código por linha, exatamente como a
`remuneracoes` da tabela irmã `tbl_rpa_log_detraf_despesa_arquivos` (`'VU-M'`).
Criá-la produziria uma coluna duplicada. O código foi alinhado ao nome real.

A necessidade funcional que motivou o pedido continua válida e **está atendida**:
o sinal do analista varia por remuneração dentro do mesmo par de EOT, e
`remuneracoes` entra na chave.

### ✅ Ainda necessário: `vb_contestacao`

*(decidida em 2026-08-05, confirmada ausente em 2026-08-06)*

> ¶942 — *"Quando acontece a contestação com retenção, o robô também preenche a
> coluna de contestação da remuneração no EC para a EOT da Vivo atrelada à
> contestação com o valor bruto da Diferença apresentada aba Contest."*

Guarda o valor bruto da diferença **só nas linhas COM retenção**. É o que separa
"diferença apurada" de "diferença retida" — `vb_diferenca` é gravado para todas
as linhas, então a informação não existe em nenhuma outra coluna.

```sql
ALTER TABLE webfat.tbl_rpa_log_detraf_despesa_contestacao
  ADD COLUMN vb_contestacao DECIMAL(18,6) NULL
    COMMENT 'Valor bruto da diferença retido — só nas linhas COM retenção (V2 ¶942 / V1 HU-19)'
  AFTER vb_variacao_perc;
```

`DECIMAL(18,6)` para casar com a irmã `vb_diferenca`. **Precisa aceitar `NULL`**,
e não `DEFAULT 0`: `NULL` é "sem retenção, não se aplica"; zero seria "nada retido
apurado", que é outra afirmação.

**Não trava a entrega.** O robô já degrada em volta da ausência: grava as demais
seis colunas da HU-19 e registra um aviso por lote. No dia do `ALTER`, a coluna
volta a ser gravada sem tocar em código.

⚠️ Ressalva honesta: a regra está no **bloco antigo** da V2 e na **V1** (HU-19),
e não no texto vigente. Implementá-la foi decisão nossa — as duas versões
concordam entre si e a informação não existe em outro lugar.

### Três confirmações pedidas (sem mudança, só por escrito)

1. **`remuneracoes` guarda uma remuneração por linha**, e não uma lista
   delimitada? O nome no plural sugere o contrário, e a chave de negócio do RPA 3
   depende de ser singular.
2. **Filtrar `tbl_detraf_mapeamento_descritores.ativo = 1` e
   `tbl_detraf_tarifas.ativa = '1'`?** O código não filtra por nenhum dos dois.
   Hoje todas as linhas estão ativas, então nada muda — mas precisamos saber se
   desativar uma linha deve tirá-la da visão do robô.
3. **Precedência em `tbl_detraf_tarifas`** — ver A1, reaberta abaixo.

### 🔴 A1 reaberta: `eot_vivo` e `eot_operadora` existem

O achado A1 registrava que essas colunas **não existiam** no DDL real, com base
num print do Workbench que não as mostrava. **Estava errado.** Existem, e
`eot_vivo` está preenchida em **64 das 127 linhas** — a exceção
**RII (943) × SERCOMTEL** está lá.

O código não filtra por elas. A consequência não é erro, é afrouxamento: para a
mesma região/GH/regra/vigência há uma linha genérica (`eot_vivo` nulo) **e**
linhas por EOT com tarifas diferentes — grupos de até **13 linhas com 6 tarifas
distintas**. A validação aprova a linha do Detraf se ela bater com qualquer uma,
inclusive a de outro par de EOTs.

**Mantivemos a regra atual** (decisão de 2026-08-06): definir a precedência é
regra de negócio, e errá-la aperta ou afrouxa validação de faturamento real.
**O específico por EOT deve vencer o genérico?**

---

## 🔴 A1 — A exceção de tarifa por EOT não tem onde existir

*(achado de 2026-08-06)*

A V2 é explícita sobre como consultar a tabela de tarifas:

> *"eot_vivo e eot_operadora: serve para identificar exceções na regra da região
> (para a despesa a eot_vivo está sempre representando o campo DEVEDORA e a
> eot_operadora representa a CREDORA)"*

**Essas duas colunas não existem no DDL real.** A tabela tem `sentido`, `regiao`,
`gh`, `regra_desc`, `tipo_dado`, `ativa` e `observacao`.

**O código nunca dependeu delas** — filtra por GH, região, regra e datas —, então
nada quebra. Mas o efeito é concreto e tem nome: a exceção que a **própria V2
cita**, `RII (943) × SERCOMTEL (042/043)`, cuja tarifa difere da regra de região,
**não tem como ser encontrada**. O par cai na tarifa da região II e é **reprovado
na validação, como se o arquivo da operadora estivesse errado**.

Não é falha de execução — é falso positivo de validação, contra uma operadora
específica, que só se percebe conferindo à mão.

**Pergunta.** Como a exceção SERCOMTEL está representada nas 127 linhas da tabela?
Está em `observacao`? Em `sentido`? Ou a exceção deixou de valer?

---

## N1 — O nome da tabela de log

A V2 é inequívoca sobre o nome; o código legado usa outro. **O conflito é com o
código, não dentro da documentação.**

**🔴 A pergunta mudou de forma em 2026-08-06.** O navigator do Workbench mostra
**as duas tabelas existindo no schema `webfat`**:

- `tbl_rpa_log_detraf_despesa_arquivos` — o nome da V2, o que está implementado;
- `tbl_rpa_log_detraf_despesa` — sem sufixo, quase certamente o legado.

Já não é *"qual é o nome certo"*. É: **qual das duas a tela de Encontro de Contas
lê hoje?**

**Por que subiu de prioridade.** Se o WebFat apontar para a sem sufixo, o robô
grava numa tabela que ninguém consulta. Nada falha, nada aparece — a pior
categoria de erro, porque só se descobre quando alguém procura um dado que
deveria estar lá.

**Comportamento adotado.** O nome da V2.

---

## ✅ N10 — Formato decimal da coluna `tarifa` — **FECHADA**

Respondida pelo print do Workbench: `tarifa` é **`float`**, com ponto decimal
(`0.00602`, `0.00421`). O código foi ajustado e a inconsistência que estava
registrada deixou de existir. **Nada a fazer do lado do cliente.**

---

# 🏢 Vivo

## Q17 — Operadoras cujo nome muda entre a contestação e a retificação

> V2, HU-21 — *"Operadoras que no anexo 5 possui um nome que sofrem alterações
> durante o processo, esse ponto de atenção precisa ser estudado. **Pendência
> Vivo para mapear essa ponta.**"*

A própria V2 registra isto como pendência da Vivo. O filtro do AGI é **por nome**:
se o nome mudou entre a contestação e a retificação, o robô não encontra o
processo anterior.

**Pergunta.** Já existe encaminhamento para essa pendência?

**Trava.** HU-21 e, portanto, o RPA 4 inteiro. Marco M7.

---

# 🔧 GP-Vivo

## Q23 — A interface com as demandas ATA0000571 / 567 / 572

A V2 registra que as quatro demandas formam o fluxo completo de faturamento do
Detraf, mas não descreve a interface entre elas.

**O que já se sabe.** O ¶410 responde em parte: a captura e conversão do ICT
pertence à demanda de **receita** — que é justamente a dona do arquivo da N3
abaixo.

**Perguntas.** Que dados são compartilhados? Há ordem de execução entre elas?

---

## Q20 — O que sobra do "não existe ambiente de teste"

Confirmado como **impedimento**, não inconveniente: não há ambiente de teste do
AGI, nem caixa de e-mail de teste, nem banco WebFat de teste, nem como isolar o
contador de numeração CT.

**Decisão de 2026-08-05:** validar contra produção, com cuidado. O modo "só
leitura" é a combinação de kill-switches

```
PERMITIR_ACESSO_AGI=true   PERMITIR_UPLOAD_AGI=false   PERMITIR_ENVIO_EMAIL=false
```

que abre o AGI e baixa o relatório **sem escrever nada nele e sem enviar e-mail** —
comportamento provado por teste automatizado. O roteiro completo está em
[checklist-validacao-agi.md](../03-checklists/checklist-validacao-agi.md).

**O que precisamos do GP-Vivo:**

1. **Autorização para o login em produção na VM de Despesa.** Ele é inerente: não
   há como exercitar a navegação sem ele.
2. **Combinar qual operadora e qual mês** serão usados na primeira carga real,
   quando `PERMITIR_UPLOAD_AGI` for ligado.
3. **Acesso às pastas de rede Lagoa** (ou réplica).

⚠️ **Antes de qualquer dessas etapas:** as credenciais do AGI que vieram nos
projetos de origem (`projeto-6`, `projeto-7`) estavam em arquivos `.env`
preenchidos e **precisam ser rotacionadas** (risco R20).

---

# 👤 Solicitante

## Q12 — A regra de validação dos descritores de transporte

> V2 — *"Descritores de transporte devem ser validados a partir da tabela
> Descritor_Remuneração **(aguardando informação do solicitante)**."*

A própria V2 registra que está aguardando o solicitante.

**Trava.** Parte da HU-05. E impede promover o mapeamento descritor→remuneração
integralmente à base comum.

---

# 🔴 As duas que já têm tratamento, mas continuam sendo pergunta

## Q16 — A "tabela de contatos do WebFat" não existe na V2

A expressão **não ocorre uma única vez** no documento normativo. Tudo o que a V2
diz sobre destinatários:

> *"O robô cria um e-mail para enviar as operadoras:"*
> *"Destinatários: contatos das operadoras"*

O nome vem da **V1** (HU-15). E a V1 usava a mesma tabela também na HU-02, para
identificar a operadora pelo domínio do remetente — **uso que a V2 eliminou**,
trocando por EOT credora × Anexo 5. Ou seja: a V2 removeu o único uso descrito da
tabela e deixou o outro sem detalhe.

**Ponte implementada em 2026-08-05.** Os contatos podem vir de um CSV
`operadora;emails` apontado por `CAMINHO_CONTATOS_OPERADORAS`. Sem o arquivo, a
HU-15 continua recusando o envio em vez de mandar e-mail para lugar nenhum.

**Perguntas que continuam.** A tabela existe? Qual o nome e a coluna de e-mail? Se
não existe, **de onde vêm os contatos das operadoras no processo manual de hoje**?

⚠️ A ponte **desbloqueia o envio real**: com o arquivo preenchido e
`PERMITIR_ENVIO_EMAIL=true`, o robô envia para as operadoras. É o único efeito
deste repositório que chega a alguém de fora da Vivo.

---

## N3 — A expectativa Vivo real não tem a coluna `R$_Bruto`

**Contradição entre a V2 e o arquivo real**, não ambiguidade de redação: a V2
descreve a coluna, e o arquivo de expectativa efetivamente recebido não a tem.

**Comportamento adotado (mantido em 2026-08-05).** O arquivo sem `R$_Bruto` é
**rejeitado**. Falhar alto é melhor do que comparar a coluna errada em silêncio —
comparar errado produziria variação de 100% e **contestação indevida** de uma
operadora inteira.

**Pergunta.** Qual dos dois está certo — a especificação ou o arquivo? Se o
arquivo, qual coluna substitui a `R$_Bruto`?

*(Relacionada à Q23: o arquivo pertence à demanda de receita.)*

---

# 📋 Também encaminhado, sem bloquear

## Q24 — O bloco de texto duplicado da V2

O `.docx` da V2 repete, após o item 7, um trecho de versão anterior com regras
revogadas. **Não é duplicata pura:** ao menos um requisito só existe ali — o ¶942,
que virou a coluna `vb_contestacao` acima.

**Pedido.** Uma versão limpa do documento, **com o ¶942 reintegrado ao texto
vigente se ele continua valendo** — ou a confirmação de que foi revogado, caso em
que a coluna sai.

O bloco duplicado é fonte recorrente de reintrodução de regra revogada: apagá-lo
sem revisar perderia requisito, e mantê-lo faz cada leitura recomeçar a dúvida.

---

# Resumo

| Destinatário | Itens | O mais urgente |
|---|---|---|
| **PO / GER-AC** | Q6, Q11, Q16, Q16b, N3 | **Q6** — subiu: o deslocamento de colunas de 2028 quebraria a apuração em silêncio |
| **DBA / GP-Vivo** | Q24 (1 `ALTER` + 3 confirmações), **A1 reaberta** | **A1** — a validação de tarifa está afrouxando em silêncio |
| **Vivo** | Q17 | trava o RPA 4 inteiro |
| **GP-Vivo** | Q20, Q23, Q24 | **Q20** — autorização para validar em produção |
| **Solicitante** | Q12 | a própria V2 aponta para ele |

**São 13 pendências abertas.** Em 2026-08-06 **cinco fecharam** — N10, N4 e Q13
(respondidas pelas imagens do próprio `.docx`), e **Q22 e N1**, respondidas pela
primeira leitura do banco real. **Três entraram** (A1, A2, A3), e a **A1 foi
reaberta** no mesmo dia: dizia que duas colunas não existiam, e elas existem.
Nenhuma depende de desenvolvimento adicional da Btime.

**Três não travam a entrega** — têm comportamento provisório definido e testado:
**Q16** (ponte por CSV), **N3** (rejeição mantida) e **Q24** (`vb_contestacao`
ausente, escrita degradada com aviso). Elas continuam na lista porque a pergunta
que fazem só o cliente responde.

> Nota de precisão: uma versão anterior deste documento dizia **12**, depois
> **15**, e o planejamento da rodada estimava **10**. A de 15 contava a Q22 como
> aberta e listava as "duas colunas acrescentadas" como pedido ao DBA — uma delas
> não era pedido nenhum. São 13.
