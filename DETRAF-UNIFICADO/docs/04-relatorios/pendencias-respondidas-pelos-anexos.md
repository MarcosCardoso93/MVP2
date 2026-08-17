# Pendências com resposta — DETRAF MVP2

**Data:** 2026-08-05 · **Origem:** análise dos anexos recebidos · **Demanda:** GSA ATA0000574

---

## Para que serve este documento

Complementa [pendencias-para-o-cliente.md](pendencias-para-o-cliente.md). Lista as
pendências que **deixaram de depender do cliente** — porque a resposta já estava
nos anexos, só não no texto extraído deles.

**De onde vêm as respostas.** O `.docx` normativo carrega 56 imagens embutidas.
Duas delas são **prints do MySQL Workbench conectado ao schema `webfat`**, com o
DDL real das tabelas. Outras mostram o mockup do WebFat, a aba `Contest` real, o
e-mail de contestação enviado e a tela de filtro do AGI. Nada disso aparece na
extração de texto do documento — por isso passou batido até agora.

Referências de imagem seguem a nomenclatura interna do `.docx`
(`word/media/imageNN`), recuperável descompactando o arquivo.

**Fontes usadas:**

- `_V2__Btime_SPTI_Detraf_MVP2__comentadaLuciana.docx` — texto e imagens embutidas
- `Tabelas_para_o_RPA_alimentar_o_Webfat_-_despesa.xlsx` — a planilha citada no ¶ de captura

---

# ✅ Fechadas

## N10 — Formato decimal da coluna `tarifa`

**Resposta: `float`, com ponto.**

> `image9.png` — MySQL Workbench, `select * from webfat.tbl_detraf_tarifas`,
> 127 linhas retornadas.

O painel *Object Info* mostra `tarifa` tipada como **`float`**. O result grid
confirma na prática: `0.00602`, `0.00421`, `0.00626`, `0.00438` — separador
decimal **ponto**, e valor numérico, não string.

**DDL completo observado:**

```
tbl_detraf_tarifas
  id                int AI PK
  sentido           text
  tipo_remuneracao  text
  regiao            text
  gh                text
  tarifa            float
  data_inicio       datetime
  data_fim          datetime
  regra_desc        text
  tipo_dado         text
  ativa             text
  created_at        datetime
  created_by        text
  updated_at        datetime
  updated_by        text
  observacao        text
```

Valores observados: `sentido` = `C`; `regiao` = `I`, `II`, `III`; `gh` = `N`, `R`;
`regra_desc` = string de regra legível (`DESC final "L"`); `tipo_dado` =
`REMUNERACAO`.

---

## N4 — `tipo_lote` tem quatro valores; a V2 descreve três

**Resposta: vale o recorte de três. O enum é fechado.**

> `image40.png` — MySQL Workbench, aba *Columns* de
> `tbl_rpa_log_detraf_despesa_arquivos`.

```
tipo_registro   enum('DETRAF','EXPECTATIVA','ERRO')   NOT NULL
```

Três fontes independentes concordam:

1. **O DDL real** — enum fechado, `NOT NULL`;
2. **A planilha de referência** — mesma definição, com a descrição de `ERRO` como
   *"arquivo de expectativa que não passou pela validação"*;
3. **O mockup do WebFat** (`image69.png`, `image77.png`) — a barra de filtro da
   tela *Encontro de Contas – Despesa* tem exatamente as abas
   **Detraf | Expectativa | Erro | Contestação**.

**DDL completo observado:**

```
tbl_rpa_log_detraf_despesa_arquivos                      (13 colunas)
  id                        int                          NOT NULL
  tipo_registro             enum('DETRAF','EXPECTATIVA','ERRO')  NOT NULL
  nome_arquivo              varchar(255)
  periodo                   varchar(20)
  empresa                   varchar(150)
  tipo_servico_operadora    varchar(100)
  tipo_servico_vivo         varchar(100)
  remuneracoes              varchar(255)
  minuto_desp               decimal(18,6)
  valor_bruto_desp          decimal(18,6)
  status                    varchar(50)
  codigo_erro               varchar(100)
  created_at                datetime  DEFAULT CURRENT_TIMESTAMP
```

Bate coluna a coluna com a planilha de referência. Charset `utf8mb4`.

---

## Q13 — O que é "avaliar possível correção automática"?

**Resposta: a própria V2 responde, dois parágrafos adiante — não há correção
automática.**

> ¶ seguinte ao ¶424 — *"Caso o erro encontrado esteja no arquivo de expectativa,
> o erro deve ser disponibilizado através do webfat para tratamento da área
> usuária."*
>
> E logo abaixo — *"Em caso de erro do processamento o robô seguirá para o próximo
> processamento, em seguida o erro deve ser apresentado via Webfat (…) sem
> detalhamento dos erros apenas com alerta em vermelho sinalizando a situação para
> o analista."*

O texto operacional descreve **tratamento humano**: expor no WebFat, sinalizar em
vermelho, seguir para o próximo arquivo. Não descreve nenhuma correção feita pelo
robô. A expressão "avalia possível correção automática" do ¶424 é a única
ocorrência e não tem regra associada em lugar nenhum.

O **Fluxograma AS IS** (`image75.jpg`) reforça: o caminho de inconsistência leva a
crítica e retorno, sem passo de correção.

**Comportamento adotado (mantido).** Nenhuma correção automática; o arquivo de
expectativa com erro é rejeitado, registrado com `tipo_registro = 'ERRO'` e o
`codigo_erro` preenchido.

---

# 🟡 Parcialmente respondidas

## Q22 — O DDL das quatro tabelas do WebFat

**Duas das quatro chegaram** (acima).

**Faltam:**

1. `tbl_rpa_log_detraf_despesa_contestacao` — **a mais importante**, porque é onde
   moram as duas colunas acrescentadas (`remuneracao` e `vb_contestacao`). Dela
   temos só a especificação da planilha, 18 colunas, não o DDL real.
2. `tbl_detraf_mapeamento_descritores` — nada, em nenhuma fonte.

**O que o navigator do Workbench revelou de bônus.** O schema `webfat` tem tabelas
que a V2 não cita:

```
tbl_detraf_operadoras
tbl_detraf_regras_icms
tbl_detraf_tarifas_transformacao
tbl_encontro_contas
tbl_rpa_log_detraf_despesa          ← ver N1
```

O log de execução visível no print confirma que
`tbl_rpa_log_detraf_despesa_contestacao` **existe** (`select *` retornou 1 linha).

**Pedido reduzido.** Já não são quatro `SHOW CREATE TABLE` — são **dois**.

---

## N1 — O nome da tabela de log

**Resposta: o nome da V2 existe. Mas o outro também.**

> `image40.png`, painel *Schemas* — navigator do banco `webfat`.

Aparecem **as duas**:

- `tbl_rpa_log_detraf_despesa_arquivos` — o nome da V2, o que está implementado
- `tbl_rpa_log_detraf_despesa` — sem sufixo, quase certamente o nome legado

A pergunta muda de forma. Não é mais *"qual é o nome certo"*: é **"qual das duas o
WebFat lê hoje"**. Se a tela de Encontro de Contas apontar para a sem sufixo, o
robô grava numa tabela que ninguém consulta — falha silenciosa, a pior categoria.

**Pergunta ao DBA/GP-Vivo.** Qual das duas alimenta a tela? A outra é resíduo?

---

## Q16b — Casos de exceção da identificação da operadora (HU-02)

**Dois dos quatro casos têm cobertura no texto.**

A regra genérica **é explicitamente genérica** — *"Em caso de erro do
processamento o robô seguirá para o próximo processamento"* —, o que sustenta
aplicá-la a arquivo corrompido, protegido por senha ou que não abre, e a coluna
Credora vazia.

Há ainda regra própria, não citada antes, para um caso vizinho:

> V2 — *"Caso a operadora encaminhe diversos arquivos com o mesmo nome, o documento
> anterior é subscrito e um novo processamento é iniciado, seguindo a regra de
> corte."*

**Continuam sem regra:**

1. **EOT credora que não existe no Anexo 5** — não há onde salvar o arquivo, e a
   regra genérica não diz se isso é erro da operadora (devolve) ou erro de base
   (Anexo 5 desatualizado);
2. **E-mail com anexos de mais de uma operadora** — a regra de sobrescrita acima
   trata nome repetido, não operadora múltipla.

---

## N3 — A expectativa Vivo real não tem a coluna `R$_Bruto`

**Hipótese barata a testar antes de escalar: pode ser só o separador do nome.**

A V2 usa **duas grafias** para a mesma coluna:

- no layout de 15 colunas — *"15ª coluna ou `R$_Bruto`"* (underscore)
- ao descrever a cópia do arquivo de expectativa — *"até a coluna **`R$ Bruto`**"*
  (espaço)

**Verificação sugerida.** Ler o cabeçalho bruto do arquivo de expectativa recebido
e comparar.

---

## Q16 — A "tabela de contatos do WebFat" não existe na V2

**A tabela continua sem aparecer. Mas o processo manual de hoje ficou visível.**

> `image109.jpg` — print do e-mail de contestação real, em composição no Outlook.

- **Para:** dois contatos nomeados na operadora (contabilidade e um contato direto)
- **Cc:** mais dois endereços, incluindo um que **não é da operadora** —
  aparentemente cópia fixa do processo
- **Assunto:** `CONTESTAÇÃO_TBRA| AMPERNET_202506` — bate com o padrão da V2
- **Anexo:** `CT 334_2025_DIR A1-CONT_AMPERNET_202506.docx`

**Consequências para a ponte por CSV.** O formato `operadora;emails` precisa
suportar:

1. **múltiplos destinatários** por operadora;
2. **distinção entre Para e Cc**;
3. uma **cópia fixa** aplicada a todas as operadoras.

Nenhuma tabela de contatos aparece no navigator do banco.

⚠️ O anexo revela também o padrão de numeração CT (`CT 334_2025_...`).

---

## Q17 — Operadoras cujo nome muda entre contestação e retificação

**Continua pendência Vivo. Mas há caminho técnico que talvez dispense a espera.**

> `image73.jpg` e `image159.jpg` — tela *Contestação > Gerenciar* do AGI.

O filtro de registros não tem só nome. Tem:

- **`Número Processo`** — campo de busca direta, no topo da tela
- **`Grupo Oper. Prest.`** — agrupamento acima da operadora individual
- **`Operadoras Vivo`** — por EOT (`020-TELERJ CELULAR`), não por nome
- `Período Referência`, `Período Tráfego`, `Nat. Operação`, `Modalidade Contestação`

O grid de resultado mostra `ID Processo` como primeira coluna, e o painel lateral
é *"Eventos do Processo de Contestação — Processo Selecionado: 586492"*.

**Proposta.** Se o RPA 3 guardar o `ID Processo` retornado pelo AGI no momento da
contestação, o RPA 4 recupera por número, e a mudança de nome deixa de importar.
Isso exige uma coluna a mais na tabela de contestação — a decidir junto com o DDL
da Q22.

**A pendência Vivo continua válida** para o caso de contestações já criadas antes
do robô, sem `ID Processo` registrado.

---

## Q6 — CBS, IBS Estadual e IBS Municipal: onde ficam no layout?

**Não respondida — e o documento agora explica por que ela importa mais do que
parecia.**

O layout de 15 colunas está completo no texto, e as três colunas não estão nele:

```
12ª  R$_Liq        valor, até 2 casas decimais
13ª  PIS_Cofins    valor, até 2 casas decimais
14ª  ICMS          valor, até 2 casas decimais
15ª  R$_Bruto      valor, até 2 casas decimais
```

E o item 7 (Risco) responde à segunda metade da pergunta:

> ¶ item 7 — *"Existe a projeção para que em 2028 mais um imposto seja inserido na
> tabela **deslocando as colunas**."*

Ou seja: a inserção de imposto **é posicional e desloca** as colunas existentes.
Não são colunas 16/17/18 no fim — entram no bloco de impostos e empurram
`R$_Bruto`. Um parser por posição fixa quebra; um parser por cabeçalho sobrevive.

**"isnumos" não ocorre em nenhum outro ponto do documento**, e nenhuma das 56
imagens mostra esse layout.

**Trava mantida.** HU-04, HU-10, HU-20.

---

## Q24 — O bloco de texto duplicado da V2

**Confirmado: a duplicação persiste nesta versão comentada.**

As seções *Contestação e criação dos arquivos para o AGI* → *Carga no AGI* →
*Preenchimento do Encontro de Contas* → *Geração do Relatório* → *Retificação de
Contestação* aparecem **duas vezes** no `.docx`.

Distinguem-se com clareza:

| | Bloco vigente | Bloco antigo |
|---|---|---|
| Cita as tabelas `tbl_…` | sim | não |
| Cita CBS/IBS | sim | não |
| Contém o ¶942 | **não** | **sim** |

**Evidência a favor de manter `vb_contestacao`.**

> `image93.jpg` — print do resumo real do Encontro de Contas.

```
Total Receita             37,90
Total Contestação Rec      0,00
Subtotal Receita          37,90

Total Despesa           -769,10
Total Contestação Desp   247,50
Subtotal Despesa        -521,60      ← célula O87, a citada na V2
```

O EC trata **"Total Contestação Despesa" como linha própria**, separada de "Total
Despesa", e o subtotal é a soma das duas. A informação do ¶942 tem lugar
estrutural no destino. Isso sustenta a decisão de 2026-08-05.

**Pedido mantido.** Versão limpa do documento com o ¶942 reintegrado ao texto
vigente — ou a confirmação de que foi revogado.

---

# 🔴 Achados novos, não estavam na lista

## A1 — `tbl_detraf_tarifas` não tem `eot_vivo` nem `eot_operadora`

A V2 é explícita sobre como consultar a tabela:

> *"eot_vivo e eot_operadora: serve para identificar exceções na regra da região
> (para a despesa a eot_vivo está sempre representando o campo DEVEDORA e a
> eot_operadora representa a CREDORA)"*

**Essas colunas não existem no DDL real.** A tabela tem `sentido`, `regiao`, `gh`,
`regra_desc`, `tipo_dado`, `ativa`, `observacao`.

O caso concreto que isso quebra é o da própria V2: a exceção
**RII (943) – SERCOMTEL (042/043)**, cuja tarifa difere da regra de região. Sem as
duas colunas, não há como expressá-la — a menos que esteja codificada em
`observacao` ou `sentido`, o que precisa ser confirmado com dados.

**Impacto.** Validação de tarifa — HU-04.

**Pergunta.** Como a exceção SERCOMTEL está representada nas 127 linhas da tabela?

---

## A2 — A aba `Contest` real é por EOT, não por remuneração

> `image80.jpg` — print da aba `Contest` do arquivo Base Contestação.

```
STFC
EOT      | TBRA (Min, VB) | AMPERNET (Min, VB) | Diferença | Variação Perc. | Contestação a enviar
11/200   | 1.971,00 29,17 | 52.036,80 317,95   | …         | 96,2%  90,8%   | S
TOTAL    | 1.971,0  29,2  | 52.036,8  318,0    | …         |                |
```

**Uma linha por par de EOT, uma única marca `S`/`N`.** Não há quebra por
remuneração nesse nível.

Isso é **evidência contrária à premissa da coluna `remuneracao`** — decidida em
2026-07-28 sob o argumento de que *"o sinal de contestação do analista pode variar
por remuneração dentro do mesmo par de EOT"*.

**Mas o quadro completo é mais sutil.** A V2 diz, em dois pontos distintos, que o
**Encontro de Contas** é por remuneração:

> *"popular o Encontro de Contas com o valores total apresentado pela operadora,
> **aberto por tipo de remuneração e EOT Vivo**"*
>
> *"O que vai para o EC é o somatório do valor bruto **por remuneração e
> operadora**"*

Então a granularidade **muda ao longo do fluxo**: a decisão de contestar é por par
de EOT, o registro no EC é por remuneração. A coluna pode continuar necessária —
mas a justificativa precisa ser essa, e não a que está registrada hoje.

---

## A3 — Exposição de dados internos no `.docx`

Os prints embutidos no documento normativo expõem, em claro, endereços de rede
internos, host e schema do banco, matrícula de usuário, versão do AGI, endereços
de e-mail de contatos de operadoras e a caixa de e-mail do processo.

Não é vulnerabilidade por si — o documento circula em ambiente controlado — mas
entra no mesmo balde do **R20** e vale mencionar no mesmo encaminhamento.

---

# Resumo

| Item | Antes | Agora |
|---|---|---|
| **N10** | aguardando DBA | ✅ `float`, ponto |
| **N4** | aguardando PO | ✅ enum de três, fechado |
| **Q13** | aguardando PO | ✅ respondida pelo próprio texto da V2 |
| **N1** | aguardando DBA | 🟡 as duas tabelas existem; perguntar qual o WebFat lê |
| **Q22** | 4 DDLs | 🟡 faltam **2** |
| **Q16b** | 4 casos | 🟡 faltam **2** |
| **N3** | aguardando PO | 🟡 testar `R$ Bruto` × `R$_Bruto` antes de escalar |
| **Q16** | aguardando PO | 🟡 formato do CSV precisa de Para/Cc e cópia fixa |
| **Q17** | aguardando Vivo | 🟡 propor recuperação por `ID Processo` |
| **Q6, Q11, Q12, Q20, Q23, Q24** | — | ❌ sem mudança |

---

# ⚠️ Conferência contra o código (Btime, 2026-08-06)

As conclusões acima foram checadas contra o repositório. **Três das
"consequências no código" não se confirmaram** — ver
[`relatorio-conferencia-dos-anexos.md`](relatorio-conferencia-dos-anexos.md).

| Item | O documento dizia | O que o código mostra |
|---|---|---|
| **N4** | "corrigir os quatro valores" | ✅ **já está certo** — os quatro são parâmetro interno, e a unificação já os mapeia para os três do enum |
| **N10** | "o ramo `replace` deve sair" | ⚠️ **só metade** — o `replace` do lado do **arquivo** é necessário; só o do lado do **banco** é morto |
| **A1** | "trava a HU-04" | ⚠️ o código **nunca usou** essas colunas; o efeito real é a exceção SERCOMTEL ser reprovada |
