# Checklist — Identificação de Componentes Compartilhados

Aplicar a **cada candidato**, na fase F3 (consolidação). Critérios completos em [`../02-planejamento/criterios-de-compartilhamento.md`](../02-planejamento/criterios-de-compartilhamento.md).

**Regra:** todo candidato avaliado gera uma [ficha](../05-proxima-etapa/templates/ficha-de-componente-candidato.md), **inclusive os rejeitados**.

---

## Parte A — Os quatro critérios

Um candidato só é promovido se passar nos **quatro**. Falhar em um encerra a avaliação — registre o motivo e pare.

### C1 — Recorrência comprovada

- [ ] Existem **pelo menos duas** ocorrências reais, com **arquivo e linha** registrados
- [ ] As ocorrências estão em **RPAs de destino diferentes** (não apenas em projetos diferentes que convergem no mesmo RPA)
- [ ] O veredicto entre elas é IDÊNTICO ou EQUIVALENTE-PARAMETRIZÁVEL — não FALSO PAR

⚠️ **Não conta como recorrência:** "provavelmente o RPA 3 vai usar", "é genérico por natureza", "seria bom ter".

> **Nota sobre "RPAs diferentes".** Duas ocorrências em P2 e P3 convergem ambas no RPA 2 — nesse caso a unificação é interna ao RPA, não motivo para promover à base comum. Promova quando houver consumidor em **outro** RPA.

**Falhou C1?** → fica no RPA. Registre como "**reavaliar quando surgir segunda ocorrência**".

### C2 — Independência de RPA

- [ ] Não assume decisão de analista já tomada (exclusivo do RPA 3)
- [ ] Não assume que a data de corte já passou (exclusivo do RPA 2)
- [ ] Não lê configuração específica de um RPA
- [ ] Não chama de volta o fluxo de nenhum RPA
- [ ] **Teste:** funcionaria se chamado pelo RPA 4, o mais isolado de todos?

**Falhou C2?** → fica no RPA. Não force a abstração.

### C3 — Regra fechada

- [ ] A regra que ele implementa **não** está na lista de pendências abertas

Verificar contra [`../04-relatorios/duvidas-pendentes.md`](../04-relatorios/duvidas-pendentes.md). Bloqueadores conhecidos hoje:

| Pendência | Bloqueia |
|---|---|
| Data de corte | Janela de captura, regra de reprocessamento |
| Borda de 1% (valor, sinal, base) | Cálculo de variação e decisão S/N |
| CBS/IBS | Layout de arquivo, validação, comparação |
| Envio automático HU-15 | Envio do e-mail de contestação |
| Correção automática de expectativa | Tratamento de erro de expectativa |
| Descritores de transporte | Validação de descritor |

**Falhou C3?** → fica no RPA, mas registrado como **compartilhamento adiado**, com a pendência nomeada. Promove-se automaticamente quando a pendência fechar. Isto é diferente de rejeição.

### C4 — Variação parametrizável

- [ ] A diferença entre as ocorrências cabe em parâmetro
- [ ] **Teste:** extraindo a diferença para um parâmetro, o corpo restante fica igual, **sem `if` sobre esse parâmetro**?
- [ ] O componente **não** precisa saber quem o chamou
- [ ] Não há flag booleana que ligue/desligue comportamento
- [ ] O número de parâmetros não cresceu para satisfazer um chamador específico

**Falhou C4?** → são dois componentes com um nome só. Mantenha separados, com nomes distintos.

---

## Parte B — Verificação da promoção

Só para os que passaram nos quatro:

- [ ] Qual implementação foi escolhida como base, e por quê (ordem: aderência à V2 → cobertura de bordas → menor acoplamento → testabilidade → legibilidade)
- [ ] A implementação escolhida está aderente à **V2**, não à V1
- [ ] Todas as ocorrências originais foram listadas, para que a migração saiba o que substituir
- [ ] O componente tem um nome que descreve sua responsabilidade — **não** é "utils", "helpers" ou "common"
- [ ] Não carrega consigo constante que viole as premissas 10.3/10.4 (tarifa, mapeamento, limiar, índice de coluna fixos)

---

## Parte C — Candidatos conhecidos a avaliar

Lista de partida derivada da documentação. ⚠️ **Hipóteses** — a contagem real de ocorrências vem da análise.

| # | Candidato | RPAs sugeridos pela doc | Atenção |
|---|---|---|---|
| 1 | Consulta ao Anexo 5 (EOT → nome fantasia, tipo de serviço, região, concessão) | 1, 2, 3, 4 | Candidato mais forte. HU-02, 04, 05, 06, 10, 21 |
| 2 | Conexão e acesso ao banco WebFat | 1, 2, 3, 4 | Forte |
| 3 | Consulta a `tbl_detraf_tarifas` | 2 | ⚠️ pode falhar C1 |
| 4 | Mapeamento descritor → remuneração | 2, 3 | ⚠️ C3 parcial: transporte indefinido |
| 5 | Leitura de arquivo Detraf (csv/xlsx, sem cabeçalho, ignora resumo) | 1?, 2, 3 | ⚠️ C3: CBS/IBS. Layout deve ser configurável |
| 6 | Construção de caminhos de rede Lagoa | 1, 2, 3 | Alto valor: divergência aqui é bug latente |
| 7 | Convenções de nome de arquivo (`_D_`, `_BK`, `_ERRO`, `_ENV`, `_EXT`, `_INT`) | 1, 2, 3 | Alto valor |
| 8 | Automação do Outlook — leitura e movimentação | 1, 2 | ok |
| 9 | Automação do Outlook — envio | 2, 3 | ⚠️ C3: envio automático da HU-15 |
| 10 | Automação de UI do AGI (login, navegação, upload) | 3, 4 | Provar no RPA 4 antes do RPA 3 |
| 11 | Logging e observabilidade | 1, 2, 3, 4 | Forte |
| 12 | Configuração e credenciais | 1, 2, 3, 4 | Forte |
| 13 | Escrita em `tbl_..._contestacao` | 2, 3 | ⚠️ possível FALSO PAR — quatro responsabilidades escrevem nessa tabela |
| 14 | Cálculo de variação e decisão S/N | 2 | ❌ falha C1 e C3 |
| 15 | Detecção de tráfego recuperado | 3, 4 | ⚠️ detecção no RPA 3, execução no RPA 4 |

- [ ] Todos os 15 avaliados e com ficha preenchida
- [ ] Candidatos **novos**, surgidos da análise, também avaliados

---

## Parte D — Antipadrões

Revisão final do conjunto promovido:

- [ ] ❌ Nenhum componente chamado "utils", "helpers", "common" ou "misc"
- [ ] ❌ Nenhum promovido por antecipação (viola C1)
- [ ] ❌ Nenhuma flag booleana de comportamento (viola C4)
- [ ] ❌ Nenhum componente que conhece o chamador (viola C2)
- [ ] ❌ Nenhuma regra em pendência aberta na base comum (viola C3)
- [ ] ❌ Nenhum promovido por semelhança de nome (FALSO PAR)

---

## Parte E — Fechamento

- [ ] Toda ficha tem veredicto: **promovido / rejeitado / adiado**
- [ ] Toda rejeição diz **qual critério falhou** e **o que mudaria o veredicto**
- [ ] Todo adiamento nomeia a **pendência** que o bloqueia
- [ ] O catálogo consolidado está em `trabalho/inventarios/`
