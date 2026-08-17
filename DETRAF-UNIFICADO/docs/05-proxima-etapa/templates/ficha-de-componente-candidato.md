# Template — Ficha de Componente Candidato

> Copiar para `trabalho/inventarios/candidatos/{nome-do-candidato}.md`.
> Uma ficha por candidato, **inclusive os rejeitados**. Critérios: [`../../02-planejamento/criterios-de-compartilhamento.md`](../../02-planejamento/criterios-de-compartilhamento.md).

---

# Candidato: {nome}

- **Registrado em:**
- **Registrado por:**
- **Última atualização:**

## Responsabilidade

*Uma frase. O que este componente faz, em termos de negócio ou de infraestrutura.*

⚠️ Se a frase precisar de "e" para descrever o que ele faz, provavelmente são dois componentes.

---

## Ocorrências

| # | Projeto | Arquivo | Linha | RPA destino | Observação |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |

**Total de ocorrências:** **RPAs distintos atingidos:**

---

## Avaliação dos critérios

### C1 — Recorrência comprovada

- [ ] Pelo menos **duas** ocorrências reais, com arquivo e linha
- [ ] As ocorrências estão em **RPAs de destino diferentes**
- [ ] O veredicto entre elas é IDÊNTICO ou EQUIVALENTE-PARAMETRIZÁVEL (não FALSO PAR)

> Duas ocorrências em projetos que convergem no **mesmo** RPA (ex.: P2 e P3 → RPA 2) justificam unificação **interna ao RPA**, não promoção à base comum.

**Veredicto C1:** ✅ passa / ❌ falha
**Justificativa:**

### C2 — Independência de RPA

- [ ] Não assume decisão de analista já tomada (RPA 3)
- [ ] Não assume data de corte já ultrapassada (RPA 2)
- [ ] Não lê configuração específica de um RPA
- [ ] Não chama de volta o fluxo de nenhum RPA
- [ ] **Teste:** funcionaria se chamado pelo RPA 4?

**Veredicto C2:** ✅ / ❌
**Justificativa:**

### C3 — Regra fechada

- [ ] A regra **não** está em pendência aberta

Pendências que bloqueiam compartilhamento hoje:

| Pendência | Bloqueia | Aplica-se? |
|---|---|---|
| Q1 — data de corte | janela de captura, reprocessamento | ☐ |
| Q2 — borda de 1% | cálculo de variação, decisão S/N | ☐ |
| Q5 — envio automático HU-15 | envio do e-mail de contestação | ☐ |
| Q6 — CBS/IBS | layout, validação, comparação | ☐ |
| Q12 — descritores de transporte | validação de descritor | ☐ |
| Q13 — correção automática | tratamento de erro de expectativa | ☐ |

**Veredicto C3:** ✅ / ❌
**Pendência bloqueadora (se houver):**

### C4 — Variação parametrizável

- [ ] A diferença entre as ocorrências cabe em parâmetro
- [ ] **Teste:** extraindo a diferença, o corpo restante fica igual, **sem `if` sobre o parâmetro**?
- [ ] Não precisa saber quem o chamou
- [ ] Sem flag booleana de comportamento
- [ ] Número de parâmetros não cresceu para atender a um chamador específico

**Parâmetros necessários:**

| Parâmetro | Tipo de variação | Valores por ocorrência |
|---|---|---|

**Veredicto C4:** ✅ / ❌
**Justificativa:**

---

## Veredicto final

- [ ] ✅ **PROMOVIDO** — passa nos quatro critérios
- [ ] ❌ **REJEITADO** — falha em: C___
- [ ] ⏸️ **ADIADO** — falha apenas em C3, bloqueado por: ___

> **Adiado ≠ rejeitado.** Um candidato que falha apenas em C3 é compartilhamento **adiado**: promove-se automaticamente quando a pendência fechar. Registre isso.

**O que mudaria o veredicto:**

---

## Se PROMOVIDO

**Implementação escolhida como base:** ocorrência #___

**Por quê** (ordem: aderência à V2 → cobertura de bordas → menor acoplamento → testabilidade → legibilidade):

**Verificações finais:**
- [ ] A implementação escolhida está aderente à **V2**, não à V1
- [ ] Não carrega constante que viole as premissas 10.3/10.4 (tarifa, mapeamento, limiar, índice de coluna)
- [ ] O nome descreve a responsabilidade — **não** é "utils", "helpers", "common" ou "misc"

**Ocorrências a substituir na migração:**

| # | Projeto | Arquivo | Linha |
|---|---|---|---|

---

## Se REJEITADO ou ADIADO

**Onde o código fica:**

**Reavaliar quando:**

---

## Observações

*Bordas divergentes entre as ocorrências, dependências não óbvias, riscos de acoplamento.*
