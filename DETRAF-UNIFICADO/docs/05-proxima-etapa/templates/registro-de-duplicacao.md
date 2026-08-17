# Template — Registro de Duplicação

> Copiar para `trabalho/inventarios/duplicacoes/{responsabilidade}-{projA}-{projB}.md`.
> Um registro por par avaliado, **inclusive os que não foram unificados**. Critérios: [`../../02-planejamento/criterios-de-unificacao.md`](../../02-planejamento/criterios-de-unificacao.md).

---

# Duplicação: {responsabilidade}

- **Registrado em:**
- **Registrado por:**

## Responsabilidade avaliada

*O que ambos os trechos supostamente fazem.*

---

## Ocorrências

### Ocorrência A
| Campo | Valor |
|---|---|
| Projeto | |
| Arquivo | |
| Linha | |
| RPA destino | |
| HU | |

**O que faz:**

### Ocorrência B
| Campo | Valor |
|---|---|
| Projeto | |
| Arquivo | |
| Linha | |
| RPA destino | |
| HU | |

**O que faz:**

---

## 🔴 Comparação de bordas — obrigatória

**Não declare IDÊNTICO comparando o caminho feliz.**

### Se manipulam arquivo Detraf

| Borda | A | B | Diverge? |
|---|---|---|---|
| Arquivo **sem cabeçalho** (V2 exige aceitar) | | | |
| **Aba de resumo** presente (V2 exige ignorar) | | | |
| Linhas `Rel = 1` (excluir nas consolidações) | | | |
| Coluna `Rel` **vazia** (V2 permite) | | | |
| Coluna `POI` vazia (V2 permite) | | | |
| Separador decimal / formato numérico | | | |
| Encoding do `.csv` | | | |
| Suporta `.csv` **e** `.xlsx` | | | |
| Arquivo vazio ou só cabeçalho | | | |
| EOT não encontrada no Anexo 5 | | | |

### Se consultam tarifa

| Borda | A | B | Diverge? |
|---|---|---|---|
| **Dupla convivência em fevereiro** | | | |
| `gh` nulo (vale para todos os grupos) | | | |
| Exceção Sercomtel (943 / 042-043) | | | |
| Tarifa zero rejeitada | | | |
| Descritor não mapeado (não regulada) | | | |
| Horário reduzido VU-M (tipo da Devedora) | | | |

### Se calculam variação

| Borda | A | B | Diverge? |
|---|---|---|---|
| **Limiar** (`> 1%` / `>= 1%` / `> +1%`) | | | |
| **Sinal** considerado | | | |
| **Base do percentual** (operadora / expectativa) | | | |
| Expectativa zerada | | | |
| Divisão por zero | | | |

### Outras bordas relevantes a este par

| Borda | A | B | Diverge? |
|---|---|---|---|

**Alguma borda diverge?** sim / não
→ **Se sim, o veredicto é DIVERGENTE, não IDÊNTICO.**

---

## Veredicto

- [ ] **IDÊNTICO** — mesmo comportamento em toda entrada válida
- [ ] **EQUIVALENTE-PARAMETRIZÁVEL** — a diferença é dado
- [ ] **DIVERGENTE** — comportamentos diferentes
- [ ] **FALSO PAR** — mesmo nome, propósitos diferentes

**Justificativa:**

---

## Se EQUIVALENTE-PARAMETRIZÁVEL

| Parâmetro | Valor em A | Valor em B |
|---|---|---|

- [ ] Extraindo a diferença, o corpo restante fica igual, **sem `if` sobre o parâmetro**

---

## Se DIVERGENTE — sub-classificar

- [ ] **DIVERGENTE-VERSÃO** — uma segue a V1, outra a V2
  - Qual segue a V2:
  - Esforço de retrabalho na outra:
  - → A V2 é normativa. Encaminhar ao PO como **confirmação**

- [ ] **DIVERGENTE-INTERPRETAÇÃO** — ambas leram a V2 e chegaram a comportamentos diferentes
  - Trecho ambíguo da V2:
  - Leitura de A:
  - Leitura de B:
  - **Impacto de cada leitura:**
  - → **Não decidir tecnicamente.** Encaminhar ao PO com as duas leituras

- [ ] **DIVERGENTE-DEFEITO** — uma está objetivamente errada
  - Qual está errada:
  - Evidência na V2:
  - → Migrar a correta; registrar a incorreta no backlog; **não corrigir durante a migração**

**Encaminhado para:** **Em:**

---

## Se FALSO PAR

**Por que pareciam iguais:**

| Ocorrência | Propósito real | Nome proposto no destino |
|---|---|---|
| A | | |
| B | | |

> Armadilhas conhecidas: "validar arquivo", "enviar e-mail", "contestação", "expectativa", "operadora", "processar", "salvar", "total". Ver [checklist de duplicações](../../03-checklists/checklist-duplicacoes.md), Parte C.

---

## Ação

- [ ] **Unificar** — implementação base: A / B, porque:
- [ ] **Unificar com parâmetro**
- [ ] **Não unificar** — motivo:
  - [ ] regra em pendência aberta:
  - [ ] criaria acoplamento entre RPAs que devem ser independentes
  - [ ] uma das ocorrências vai desaparecer (ex.: HU-20 fora do escopo)
  - [ ] aguardando decisão do PO
- [ ] **Não unificar e renomear** (FALSO PAR)

**Componente candidato relacionado:** *(link para a ficha, se houver)*

---

## Observações
