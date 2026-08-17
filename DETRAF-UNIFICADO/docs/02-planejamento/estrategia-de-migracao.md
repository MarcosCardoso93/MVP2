# Estratégia de Migração

> ⚠️ **Fotografia da etapa documental (2026-07-30).** Este documento foi escrito
> **antes** de qualquer código chegar, e descreve o entendimento daquele momento.
> Vários pontos já mudaram — em especial: o Épico 5 **tem** projeto (o P7, entregue
> em 2026-08-04), e as HUs 12 a 19 estão implementadas e orquestradas.
>
> **Fonte do estado atual:** `docs/04-relatorios/duvidas-pendentes.md` (pendências),
> `matriz-de-rastreabilidade.md` (HUs) e `unificado/README.md` (código).

Como mover o código de `projetos-origem/` para `unificado/` sem perder comportamento e sem inventar arquitetura.

> Esta é a estratégia — a ordem, o método e os critérios de parada. **Não** é o desenho da solução. O desenho é a fase F4 e depende da análise do código.

---

## Regra de ouro

**`projetos-origem/` é somente leitura, para sempre.**

Nada é movido, alterado ou excluído lá. A migração **copia e adapta** para `unificado/`. Isso garante que, em qualquer ponto, seja possível comparar o resultado com a origem — que é a única forma de comprovar equivalência funcional.

---

## Duas ordens simultâneas

A migração se organiza em duas dimensões, e as duas importam:

- **Por camada** — o que migra antes do quê, dentro de qualquer RPA
- **Por RPA** — qual robô fica pronto antes de qual

A regra que as concilia: **a base comum é construída pela primeira vez durante a migração do RPA 1 e vai sendo confirmada (ou corrigida) a cada RPA seguinte.**

---

## Ordem por camada

Da menos acoplada à mais acoplada. Cada camada só migra depois que a anterior estiver validada.

### 1. Utilitários sem regra de negócio
Formatação de datas, manipulação de strings, helpers de caminho, conversões. São os itens de menor risco e maior taxa de duplicação entre projetos — bons para calibrar o processo antes que ele encontre algo difícil.

**Critério de pronto:** compilam, têm teste, nenhum deles contém decisão de negócio.

### 2. Acesso a dados
Conexão e consulta ao banco WebFat; leitura do Anexo 5; consulta a `tbl_detraf_tarifas` e `tbl_detraf_mapeamento_descritores`.

Vem cedo porque **todos os quatro RPAs** dependem disso, e porque é onde as premissas 10.3/10.4 da V2 (regras e tabelas editáveis pelo usuário) se materializam. Se algum projeto tiver tarifas ou mapeamentos fixos no código, é aqui que aparece.

**Critério de pronto:** nenhum valor de tarifa, descritor ou limiar constante no código; toda consulta parametrizada.

### 3. Leitura e escrita de arquivos Detraf
Parsing dos arquivos (com e sem cabeçalho, ignorando aba de resumo), construção de caminhos de rede, convenções de nome (`_D_`, `_BK`, `_ERRO`, `_ENV`, `_EXT`, `_INT`).

⚠️ Camada de alto risco: é o **contrato implícito** entre os RPAs. Se cada projeto de origem construir caminhos por conta própria, qualquer divergência entre eles é bug latente — e a unificação precisa escolher **uma** convenção, o que pode mudar comportamento.

**Critério de pronto:** uma única forma de construir cada caminho e cada nome; o layout de colunas é configurável, não posicional-fixo (requisito da V2 — ver risco do imposto de 2028).

### 4. Regras de negócio compartilhadas
Resolução de EOT no Anexo 5 (nome fantasia, tipo de serviço, região, concessão), mapeamento descritor → remuneração, validação de tarifa, cálculo de variação.

**Critério de pronto:** cada regra tem uma única implementação; regras com pendência aberta **não estão aqui** — ficam no RPA que as usa.

### 5. Integrações
Outlook (leitura no RPA 1, envio no RPA 2 e no RPA 3) e AGI (upload no RPA 3, retificação no RPA 4).

Vem por último entre as camadas comuns porque é a mais frágil: depende de UI e de sessão autenticada, e é a mais difícil de testar sem ambiente.

**Critério de pronto:** o RPA 1 lê e-mail, o RPA 3 envia e-mail e o RPA 4 opera o AGI, todos pela mesma camada.

### 6. Fluxos específicos de cada RPA
O que sobra: a orquestração de cada `main.py`. Por definição, **não** é compartilhado.

---

## Ordem por RPA

**RPA 1 → RPA 2 → RPA 4 → RPA 3**

| Ordem | RPA | Por quê |
|---|---|---|
| 1º | **RPA 1** | Único caso 1:1 (só P1). Menor risco, e é onde a base comum nasce. Se o processo falha aqui, falha em tudo |
| 2º | **RPA 2** | Primeira convergência real (P2 + P3). Testa se a base comum criada no RPA 1 sobrevive a um segundo consumidor |
| 3º | **RPA 4** | Menor em volume (uma HU). Força a **cisão do P6**, que é melhor fazer cedo — e valida a camada de automação do AGI antes do RPA 3, que depende dela mais pesadamente |
| 4º | **RPA 3** | O mais complexo: 9 HUs, 3–4 origens, artefatos irreversíveis. Migra por último, com a base comum já provada por três consumidores |

**Por que o RPA 4 antes do RPA 3.** Contraintuitivo, mas deliberado: o RPA 4 é o menor consumidor da automação do AGI. Provar essa camada com ele — onde um erro custa pouco — é melhor do que descobrir problemas dentro do RPA 3, onde a automação do AGI está entrelaçada com envio de e-mail e geração de carta.

---

## Método por RPA

Para cada RPA, sempre na mesma sequência:

1. **Recortar.** A partir dos inventários de F2, listar exatamente que trechos de que projetos compõem este RPA.
2. **Migrar o que é comum.** Para cada camada, verificar se o componente já existe na base comum. Se existe, **usar**; se não, criar a partir da ocorrência mais aderente à V2.
3. **Migrar o específico.** O fluxo do RPA e o `main.py`.
4. **Executar.** Ponta a ponta, em ambiente de teste.
5. **Comparar com a origem.** Mesmas entradas → mesmos artefatos e mesmos registros em banco.
6. **Registrar as divergências.** Toda diferença é intencional e justificada, ou é bug. Não existe terceira opção.

**Ponto de atenção no passo 2.** Quando um componente já existe na base comum mas não serve exatamente ao novo consumidor, há três saídas — em ordem de preferência:

1. **Parametrizar** — a diferença é dado (caminho, tabela, sufixo)
2. **Manter separado** — a diferença é de comportamento; forçar a abstração criaria acoplamento pior que a duplicação
3. **Reabrir a abstração** — a diferença revela que o desenho original estava errado

⚠️ A opção 3 é legítima e esperada nos primeiros RPAs. Se ela ainda estiver acontecendo no RPA 3, o problema é do desenho da base comum, não do RPA.

---

## Como comprovar equivalência funcional

A unificação preserva comportamento. Comprovar isso exige comparar saídas, não ler código.

**Superfícies observáveis, por RPA:**

| RPA | O que comparar |
|---|---|
| RPA 1 | Arquivos salvos (caminho, nome, conteúdo byte a byte); e-mails movidos no Outlook; registros em `tbl_..._arquivos` |
| RPA 2 | Registros em `tbl_..._arquivos` e `tbl_..._contestacao`; arquivos `_BK` e `_ERRO` gerados; e-mails de crítica |
| RPA 3 | `_EXT`, `_INT`, `_ENV`, carta, `CONT_PROC`; e-mail enviado; campos `tipo_contestacao` e `carga_agi`; campos do EC |
| RPA 4 | Evento "Recuperação" no AGI, com os quatro campos |

**Cuidados:**
- ⚠️ **RPA 3 e RPA 4 tocam sistemas externos irreversíveis.** Envio de e-mail para operadora, carga no AGI e evento de recuperação **não podem** ser exercitados contra produção durante a validação. Exige ambiente de teste do AGI e uma caixa de e-mail de teste. Se esses ambientes não existirem, isso é **impedimento**, não detalhe — levante em F1.
- ⚠️ **A numeração CT é consumida a cada execução.** Testar o RPA 3 contra o contador real queima números de carta. Precisa de isolamento.
- Diferenças de timestamp, ordem de linhas e metadados de arquivo são esperadas e não contam como divergência — desde que isso esteja **declarado antes** da comparação, não justificado depois.

---

## Tratamento de divergências de regra

Quando dois projetos implementam a mesma regra de formas diferentes:

1. **Não escolher tecnicamente.** Registrar as duas implementações e o que cada uma faz.
2. **Apontar a aderente à V2.** Isso é análise documental, e a análise pode fazer.
3. **Encaminhar ao PO.** A decisão de qual comportamento vale é de negócio.
4. **Enquanto não houver resposta:** manter o comportamento aderente à V2 e marcar o ponto no código como pendente de confirmação.

O mesmo vale quando um projeto implementa a **V1** de uma HU marcada 🔴 (HU-02, HU-07, HU-09, HU-10, HU-19). Nesses casos, migrar o código como está seria carregar uma regra revogada para o repositório novo.

---

## Critérios de parada

**A migração de um RPA está pronta quando:**
- Executa de ponta a ponta sem intervenção manual
- Todas as suas HUs estão rastreáveis a código
- Nenhuma regra dele está duplicada em outro RPA
- A comparação com a origem não tem divergência inexplicada
- `projetos-origem/` continua intocada

**A unificação está pronta quando:**
- Os quatro RPAs atendem ao acima
- A base comum não contém nada com uma única ocorrência (salvo justificativa registrada)
- A base comum não contém nenhuma regra em pendência aberta
- O checklist de validação da arquitetura passa

---

## O que **não** fazer durante a migração

| Não fazer | Por quê | Quando fazer |
|---|---|---|
| Refatorar código que já funciona | Muda duas variáveis ao mesmo tempo — se quebrar, não se sabe se foi a migração ou a refatoração | Depois de F6, como trabalho explícito |
| Corrigir bugs encontrados | Idem. Registre e siga | Backlog pós-unificação |
| Implementar HU não implementada | É desenvolvimento, não unificação | Escopo separado, com estimativa própria |
| Resolver pendência de regra por conta própria | Não é decisão técnica | Área cliente |
| Antecipar a base comum sem duas ocorrências | Abstração inventada é a fonte mais comum de acoplamento ruim | Quando a segunda ocorrência aparecer |
| Alterar `projetos-origem/` | Destrói a referência de comparação | Nunca |
