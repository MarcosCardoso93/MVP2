# Projeto 6 — HU-20 + HU-21

**Insira aqui o código do Projeto 6, sem alterações.**

---

## Escopo

| Campo | Valor |
|---|---|
| Épico | 6 — Encontro de Contas |
| HUs | **HU-20** (verificação do Relatório Receitas e Despesas) e **HU-21** (retificação) |
| RPA de destino | ⚠️ **DOIS**: HU-20 → RPA 3 · HU-21 → **RPA 4** |
| Transformação | 🔴 **CISÃO** — único projeto que precisa ser dividido |
| Ordem de análise | **7º (último)** |

---

## 🔴 Este é o único projeto que atravessa dois RPAs

| HU | O que faz | Gatilho | RPA |
|---|---|---|---|
| **HU-20** | Confere o Relatório de Receitas e Despesas do AGI contra o EC | ciclo mensal, após a carga | **3** |
| **HU-21** | Retifica contestação de mês anterior com evento "Recuperação" | condição assíncrona, mês seguinte | **4** |

As duas automatizam o AGI, mas respondem a **gatilhos diferentes** — e o gatilho é o critério de corte dos quatro RPAs.

### Perguntas centrais da análise

1. **A separação é limpa ou entrelaçada?** Isso define o custo da cisão.
2. **As duas compartilham a camada de automação do AGI?** Se sim, ela é candidata natural à base comum — e a cisão a torna obrigatória.
3. **Compartilham estado?**

---

## 🔴 ANTES de planejar a cisão — confirme Q7

**A HU-20 pode ter saído do escopo.** A própria V2 questiona:

> *"Caso a conferência com o robô dê errado, qual o processo? Esse processo trata-se de uma dupla checagem, conferir com o solicitante se esse processo vale a pena ou não ser mantido."*

**Se a HU-20 for descartada**, o P6 fica reduzido à HU-21, **não há cisão a fazer**, e o marco M7 simplifica muito.

Confirme com o PO antes de investir na cisão.

---

## HU-20 — Verificação do Relatório Receitas e Despesas (RPA 3)

**Fluxo:** `AGI > Relatórios > Detraf > Receitas e Despesas` → filtrar por período, natureza "D" e operadora → sumarizar `Vlr. Bruto` → comparar com o subtotal de despesa do EC → repetir para todas as operadoras.

**Novo na V2:** comparar também as colunas **CBS, IBS MUNICIPAL e IBS ESTADUAL**.

**Pontos de atenção:**
- ⚠️ **O que o código faz quando os valores divergem?** A V2 não define tratamento além de "sinalizar".
- ⚠️ **Referência órfã:** a V2 cita a "célula O87" da planilha de EC — planilha que a V2 substituiu por banco. Como o código resolve isso?
- ⚠️ A V2 admite: *"O robô precisa chegar nesse valor consolidado e copular em algum lugar. Parecendo com a planilha dos encontro de contas."* O destino **não está definido**.
- **CBS/IBS (Q6):** está implementado? Como?

---

## HU-21 — Retificação de contestação (RPA 4 inteiro)

**Fluxo:** `AGI > Contestação > Gerenciar` → filtrar por período e empresa → clicar no Id Processo → `+ Adicionar` → "Tipo Evento" = **"Recuperação"** → preencher → Salvar.

| Campo | Fórmula |
|---|---|
| Duração | Minutos da diferença |
| Valor Líquido | `VB × 0,9635` |
| Valor PIS Cofins | `VB − Valor Líquido` |
| Valor Bruto Negociado | `VB` |

**Pontos de atenção:**
- 🔴 **Como o RPA 4 é acionado?** A **detecção** da necessidade de retificação está descrita no Épico 4 (fluxo do RPA 3), mas a **execução** é aqui. A detecção está neste código ou no P4? Se está no P4, como a informação chega? Flag em banco? Agendamento que reavalia?
- ⚠️ **Nome de operadora que muda (Q17).** O filtro do AGI é por **nome da empresa**. A V2 registra como pendência da Vivo: *"Operadoras que no anexo 5 possui um nome que sofrem alterações durante o processo."* Se o nome mudou entre o mês da contestação e o da retificação, o robô não encontra o processo. **Verifique se o código falha visivelmente ou passa batido** — falhar silenciosamente aqui significa retificação que nunca acontece.
- 🔴 **O fator `0,9635`** (PIS/Cofins 3,65%) está constante no código? Viola as premissas 10.3/10.4. E tende a mudar com a chegada de CBS/IBS em 2027.
- **Como confirma que o evento foi salvo no AGI?** É passo irreversível — reprocessar duplica.

---

## ⚠️ Este projeto é um teste de confirmação

Por ser analisado por **último**, o P6 valida a camada de automação do AGI identificada nos projetos anteriores (P4 e P7, se existir). Se ela não servir aqui, a abstração está errada.

Note também que "contestação" significa coisas diferentes ao longo do projeto: decisão de negócio, tela do AGI, arquivo `CONT_PROC` e aba do WebFat. Armadilha de **FALSO PAR**.

## Candidatos a componente compartilhado esperados aqui

Automação de UI do AGI (login, navegação, extração de tela) · consulta ao Anexo 5 · acesso ao banco.

---

## Nota sobre a ordem de migração

⚠️ Na migração, o **RPA 4 vem antes do RPA 3** (ordem: RPA 1 → RPA 2 → **RPA 4** → RPA 3). É deliberado: o RPA 4 é o menor consumidor da automação do AGI, e provar essa camada com ele — onde um erro custa pouco — é melhor que descobrir problemas dentro do RPA 3, onde a automação do AGI está entrelaçada com envio de e-mail e geração de carta.

---

## Procedimento

1. [`../../docs/03-checklists/checklist-insercao-dos-codigos.md`](../../docs/03-checklists/checklist-insercao-dos-codigos.md)
2. [`../../docs/05-proxima-etapa/roteiro-analise-tecnica.md`](../../docs/05-proxima-etapa/roteiro-analise-tecnica.md)
3. [`../../docs/03-checklists/checklist-duplicacoes.md`](../../docs/03-checklists/checklist-duplicacoes.md) — inclusive **duplicação interna** entre HU-20 e HU-21

**Saídas:** `trabalho/inventarios/recebimento-projeto-6.md` e `inventario-projeto-6.md`
