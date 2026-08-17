# Checklist — Identificação de Duplicações

Aplicar a partir do **segundo** projeto analisado, e novamente na consolidação (F3).

**Regra:** todo par avaliado gera um [registro](../05-proxima-etapa/templates/registro-de-duplicacao.md), **inclusive os que não foram unificados**. O registro de um não-par vale tanto quanto o de um par: sem ele, a próxima pessoa reavalia o mesmo trecho e chega a outra conclusão.

---

## Parte A — Onde procurar

Duplicação não se encontra por busca textual. Procure por **responsabilidade**, nestes lugares:

### A.1 Fronteiras entre projetos que convergem no mesmo RPA
- [ ] **P2 × P3** (ambos → RPA 2) — a fronteira mais provável
- [ ] **P4 × P5** (ambos → RPA 3) — o P5 tem uma única HU e depende de artefatos do P4
- [ ] **P4 × P6(HU-20)** (ambos → RPA 3)
- [ ] **P4 × P7** (se o Épico 5 for separado)

### A.2 Responsabilidades que a documentação mostra em vários lugares
- [ ] Leitura de arquivo Detraf — P1?, P2, P3
- [ ] Consulta ao Anexo 5 — P1, P2, P3, P6
- [ ] Construção de caminho de rede — P1, P2, P3, P4
- [ ] Convenções de nome de arquivo — P1, P2, P3, P4
- [ ] Acesso ao banco WebFat — todos
- [ ] Envio de e-mail — P2 (crítica) e P5 (contestação)
- [ ] Automação do AGI — P6 (HU-20, HU-21) e P7? (HU-17, HU-18)
- [ ] Mapeamento descritor → remuneração — P2, P3, P4
- [ ] Cálculo de variação — P3 e possivelmente P4/P6

### A.3 Dentro do mesmo projeto
- [ ] O P2 tem caminho de erro **dedicado ao caso L-L** (HU-07) **e** a regra geral de `_ERRO` (HU-04)? ⚠️ Na V2 é um só — o dedicado é candidato a eliminação
- [ ] O P3 grava **no arquivo** `Base_Contestação` **e** no banco? ⚠️ Ver a contradição `_ENV` × `Base_Contestação`
- [ ] O P6 duplica a camada de automação do AGI entre HU-20 e HU-21?

---

## Parte B — Avaliação de cada par

### B.1 Identificação
- [ ] Ocorrência A: projeto, arquivo, linha
- [ ] Ocorrência B: projeto, arquivo, linha
- [ ] Responsabilidade declarada de cada uma
- [ ] RPA de destino de cada uma

### B.2 🔴 Comparação de bordas — obrigatória

**Não declare IDÊNTICO comparando o caminho feliz.** Para cada par que manipula arquivo Detraf:

- [ ] Arquivo **sem cabeçalho** — ambos aceitam? (a V2 exige)
- [ ] **Aba de resumo** presente — ambos ignoram? (a V2 exige)
- [ ] Linhas com `Rel = 1` — ambos excluem nas consolidações?
- [ ] Coluna `Rel` **vazia** — ambos toleram? (a V2 permite)
- [ ] Coluna `POI` vazia — ambos toleram? (a V2 permite)
- [ ] Separador decimal e formato numérico
- [ ] Encoding do `.csv`
- [ ] `.csv` **e** `.xlsx` — ambos suportam os dois?
- [ ] Arquivo vazio ou só com cabeçalho
- [ ] EOT não encontrada no Anexo 5

Para pares que consultam tarifa:
- [ ] **Dupla convivência em fevereiro** — ambos tratam?
- [ ] `gh` nulo na tabela (vale para todos os grupos)
- [ ] Exceção Sercomtel (943 / 042-043)
- [ ] Tarifa zero — ambos rejeitam?
- [ ] Descritor não mapeado (tarifa não regulada)

Para pares que calculam variação:
- [ ] **Limiar** — `> 1%`, `>= 1%` ou `> +1%`?
- [ ] **Sinal** — considera direção da diferença?
- [ ] **Base do percentual** — sobre a operadora ou sobre a expectativa?
- [ ] Expectativa **zerada** (sem par) — o que acontece?
- [ ] Divisão por zero

**Se qualquer borda diverge, o veredicto é DIVERGENTE, não IDÊNTICO.**

### B.3 Veredicto

Marcar **um**:

- [ ] **IDÊNTICO** — mesmo comportamento em toda entrada válida → unificar
- [ ] **EQUIVALENTE-PARAMETRIZÁVEL** — a diferença é dado → unificar com parâmetro
- [ ] **DIVERGENTE** — comportamentos diferentes → **não unificar sem decisão**
- [ ] **FALSO PAR** — mesmo nome, propósitos diferentes → não unificar; renomear

### B.4 Se DIVERGENTE — sub-classificar

- [ ] **DIVERGENTE-VERSÃO** — uma segue a V1, outra a V2
  → A V2 é normativa. A implementação V1 é **retrabalho**, não migração. Encaminhar ao PO como confirmação
- [ ] **DIVERGENTE-INTERPRETAÇÃO** — ambas leram a V2 e chegaram a comportamentos diferentes, porque o texto é ambíguo
  → **Não decidir tecnicamente.** Apresentar as duas leituras e o impacto de cada uma ao PO
- [ ] **DIVERGENTE-DEFEITO** — uma está objetivamente errada em relação à V2
  → Migrar a correta; registrar a incorreta no backlog; **não corrigir durante a migração**

---

## Parte C — Armadilhas de FALSO PAR

Verificar explicitamente antes de unificar qualquer par cujo nome coincida:

| Termo | Significados diferentes |
|---|---|
| **"validar arquivo"** | P1: é divergente? abre? é csv/excel? — P2: as 15 colunas e as tarifas |
| **"enviar e-mail"** | P2: crítica à operadora sobre erro — P5: contestação formal com carta |
| **"contestação"** | decisão de negócio × tela do AGI × arquivo `CONT_PROC` × aba do WebFat |
| **"expectativa"** | arquivo do ICT × campo `EXPECTATIVA` do `_EXT`/`_INT` (vale "S"/"N") |
| **"operadora"** | entidade × nome fantasia × EOT × pasta de rede |
| **"processar"** | baixar × validar × consolidar × carregar |
| **"salvar"** | pasta de rede × servidor WebFat × máquina local × banco |
| **"total"** | linha `Rel = 1` × sumarização por EOT × subtotal do EC |

- [ ] Todos os pares com nome coincidente foram checados contra esta tabela

---

## Parte D — Duplicações que **não** devem ser unificadas

Três casos em que manter duplicado é a escolha certa:

- [ ] **A regra está em pendência aberta.** Unificar antes da decisão obriga a mexer na base comum depois, com impacto nos quatro RPAs
- [ ] **A unificação criaria acoplamento entre RPAs que devem ser independentes.** O requisito é que cada RPA execute isolado
- [ ] **Uma das ocorrências vai desaparecer.** Se a HU-20 sair do escopo, unificar código dela é trabalho perdido

Cada caso desses gera registro com o motivo — não é omissão, é decisão.

---

## Parte E — Fechamento

- [ ] Todo par identificado tem registro
- [ ] Todo veredicto DIVERGENTE está sub-classificado
- [ ] Toda DIVERGENTE-INTERPRETAÇÃO foi encaminhada ao PO, com as duas leituras descritas
- [ ] Toda DIVERGENTE-VERSÃO tem a implementação V1 identificada e dimensionada como retrabalho
- [ ] Todo FALSO PAR tem proposta de renomeação
- [ ] Nenhum par foi unificado "escolhendo a que parecia melhor" quando envolvia regra de negócio
- [ ] Registro consolidado em `trabalho/inventarios/`
