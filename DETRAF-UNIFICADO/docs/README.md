# Documentação da Unificação — Índice

Toda a documentação produzida na etapa de preparação. As fontes primárias (PDF, `.docx`) continuam em [`../documentação/`](../documentação/), intocadas.

---

## Leituras recomendadas por objetivo

**Quero começar a analisar os códigos.**
→ [`05-proxima-etapa/roteiro-analise-tecnica.md`](05-proxima-etapa/roteiro-analise-tecnica.md), depois [`01-entendimento/mapa-projetos-epicos-historias-rpas.md`](01-entendimento/mapa-projetos-epicos-historias-rpas.md) e [`01-entendimento/regras-de-negocio-consolidadas.md`](01-entendimento/regras-de-negocio-consolidadas.md). Com esses três, dá para começar.

**Quero entender o domínio.**
→ [`01-entendimento/visao-geral-do-projeto.md`](01-entendimento/visao-geral-do-projeto.md) → [`01-entendimento/glossario.md`](01-entendimento/glossario.md) → [`01-entendimento/entendimento-dos-epicos.md`](01-entendimento/entendimento-dos-epicos.md)

**Quero saber o que está furado.**
→ [`04-relatorios/relatorio-inconsistencias-e-lacunas.md`](04-relatorios/relatorio-inconsistencias-e-lacunas.md)

**Vou falar com o cliente.**
→ [`04-relatorios/duvidas-pendentes.md`](04-relatorios/duvidas-pendentes.md) — 24 perguntas prontas, com destinatário

**Quero o plano de execução.**
→ [`02-planejamento/plano-geral-da-unificacao.md`](02-planejamento/plano-geral-da-unificacao.md) → [`02-planejamento/roadmap-da-unificacao.md`](02-planejamento/roadmap-da-unificacao.md)

---

## 00-fontes

| Documento | Conteúdo |
|---|---|
| [`README.md`](00-fontes/README.md) | Índice das quatro fontes, **ordem de precedência** e o alerta sobre o bloco de texto duplicado na V2 |

## 01-entendimento

| Documento | Conteúdo |
|---|---|
| [`visao-geral-do-projeto.md`](01-entendimento/visao-geral-do-projeto.md) | O que o sistema faz, escopo, sistemas, tabelas, partes interessadas, premissas |
| [`entendimento-dos-epicos.md`](01-entendimento/entendimento-dos-epicos.md) | Os 6 épicos: responsabilidade, gatilho, entradas, saídas, o que mudou na V2 |
| [`entendimento-das-historias.md`](01-entendimento/entendimento-das-historias.md) | As 21 HUs em detalhe, com critérios vigentes, delta V1→V2 e pendências |
| [`responsabilidades-dos-rpas.md`](01-entendimento/responsabilidades-dos-rpas.md) | Os 4 RPAs de destino e por que cada corte foi feito |
| [`mapa-projetos-epicos-historias-rpas.md`](01-entendimento/mapa-projetos-epicos-historias-rpas.md) | **Documento central**: para onde vai cada projeto |
| [`dependencias-funcionais.md`](01-entendimento/dependencias-funcionais.md) | Cadeia entre HUs, pontos de sincronização, dependências externas, acoplamentos |
| [`glossario.md`](01-entendimento/glossario.md) | Detraf, EOT, Anexo 5, descritores, convenções de nome, estrutura de pastas |
| [`regras-de-negocio-consolidadas.md`](01-entendimento/regras-de-negocio-consolidadas.md) | Layout, descritores, tarifas, regra de 1%, contestação, EC, retificação |

## 02-planejamento

| Documento | Conteúdo |
|---|---|
| [`plano-geral-da-unificacao.md`](02-planejamento/plano-geral-da-unificacao.md) | Princípios, fases F0–F7, gates, papéis |
| [`estrategia-de-migracao.md`](02-planejamento/estrategia-de-migracao.md) | Ordem por camada e por RPA, método, como comprovar equivalência |
| [`criterios-de-unificacao.md`](02-planejamento/criterios-de-unificacao.md) | Quando dois trechos são "a mesma coisa" — os quatro veredictos |
| [`criterios-de-compartilhamento.md`](02-planejamento/criterios-de-compartilhamento.md) | Os quatro critérios (C1–C4) para a base comum |
| [`decisoes-que-dependem-do-codigo.md`](02-planejamento/decisoes-que-dependem-do-codigo.md) | **O que esta etapa deliberadamente não decidiu, e por quê** |
| [`roadmap-da-unificacao.md`](02-planejamento/roadmap-da-unificacao.md) | Marcos M0–M9 e a trilha paralela de pendências |

## 03-checklists

| Documento | Quando aplicar |
|---|---|
| [`checklist-insercao-dos-codigos.md`](03-checklists/checklist-insercao-dos-codigos.md) | Ao receber cada projeto (M1) |
| [`checklist-analise-de-codigo.md`](03-checklists/checklist-analise-de-codigo.md) | Ao analisar cada projeto (M2) |
| [`checklist-componentes-compartilhados.md`](03-checklists/checklist-componentes-compartilhados.md) | Ao avaliar cada candidato (F3) |
| [`checklist-duplicacoes.md`](03-checklists/checklist-duplicacoes.md) | A partir do 2º projeto analisado |
| [`checklist-padronizacao.md`](03-checklists/checklist-padronizacao.md) | Durante a migração (F5) e a validação (F6) |
| [`checklist-validacao-da-arquitetura-final.md`](03-checklists/checklist-validacao-da-arquitetura-final.md) | Ao fim de F4 (em papel) e em F6 (no código) |

## 04-relatorios

| Documento | Conteúdo |
|---|---|
| [`relatorio-inconsistencias-e-lacunas.md`](04-relatorios/relatorio-inconsistencias-e-lacunas.md) | 25 achados: contradições, ambiguidades e lacunas da documentação |
| [`riscos-conhecidos.md`](04-relatorios/riscos-conhecidos.md) | 20 riscos (declarados pela V2 + introduzidos pela unificação), com matriz de priorização |
| [`duvidas-pendentes.md`](04-relatorios/duvidas-pendentes.md) | 24 perguntas prontas, com destinatário e o que bloqueiam |
| [`matriz-de-rastreabilidade.md`](04-relatorios/matriz-de-rastreabilidade.md) | HU → item da V2 → projeto → RPA → código *(a preencher em M2)* |

## 05-proxima-etapa

| Documento | Conteúdo |
|---|---|
| [`roteiro-analise-tecnica.md`](05-proxima-etapa/roteiro-analise-tecnica.md) | **Documento de entrada da próxima etapa** — procedimento completo, passo a passo |
| [`templates/inventario-por-projeto.md`](05-proxima-etapa/templates/inventario-por-projeto.md) | A preencher por projeto |
| [`templates/ficha-de-componente-candidato.md`](05-proxima-etapa/templates/ficha-de-componente-candidato.md) | Uma por candidato, inclusive os rejeitados |
| [`templates/registro-de-duplicacao.md`](05-proxima-etapa/templates/registro-de-duplicacao.md) | Um por par avaliado, inclusive os não unificados |

---

## Convenções destes documentos

- ⚠️ **marca conclusão que depende de verificação futura** — análise do código ou decisão da área cliente. Nunca é afirmação.
- 🔴 marca item bloqueante ou verificação obrigatória.
- Status das HUs: 🟢 mantida · 🟡 atualizada · 🔴 impactada estruturalmente · 🆕 escopo novo sem HU.
- **V1** = `DETRAF_MVP2_Historias.pdf` (backlog histórico). **V2** = documento normativo vigente.
- Onde a V2 é ambígua ou contraditória, a ambiguidade está **declarada como tal** — não resolvida por interpretação.
