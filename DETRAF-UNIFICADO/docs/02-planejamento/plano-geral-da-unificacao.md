# Plano Geral da Unificação

> ⚠️ **Fotografia da etapa documental (2026-07-30).** Este documento foi escrito
> **antes** de qualquer código chegar, e descreve o entendimento daquele momento.
> Vários pontos já mudaram — em especial: o Épico 5 **tem** projeto (o P7, entregue
> em 2026-08-04), e as HUs 12 a 19 estão implementadas e orquestradas.
>
> **Fonte do estado atual:** `docs/04-relatorios/duvidas-pendentes.md` (pendências),
> `matriz-de-rastreabilidade.md` (HUs) e `unificado/README.md` (código).

Como sair de seis (talvez sete) projetos independentes e chegar a um repositório com quatro RPAs sobre base comum.

---

## Princípios

1. **Documentação antes de código.** Nenhuma decisão de arquitetura é tomada sem que o código relevante tenha sido lido e inventariado.
2. **Nenhuma suposição silenciosa.** Toda conclusão que dependa de algo não verificado é marcada ⚠️ e vira item de pendência.
3. **A V2 é normativa.** Onde o código implementa a V1, isso é registrado como **divergência de regra**, não como comportamento a preservar. Divergência de regra é decisão de produto — vai para a área cliente, não é resolvida na unificação.
4. **Equivalência funcional antes de melhoria.** A unificação preserva comportamento. Refatoração e correção de dívida são trabalho posterior e explícito.
5. **Compartilhar por evidência, não por intuição.** Um componente só vai para a base comum quando houver ocorrência real em mais de um lugar. Ver [`criterios-de-compartilhamento.md`](criterios-de-compartilhamento.md).
6. **Pendência aberta não vira código.** Regra em aberto (data de corte, borda de 1%, CBS/IBS, envio automático da HU-15) fica isolada no RPA que a usa, nunca na base comum.

---

## Fases

```
F0  Preparação          ← ESTA ETAPA (concluída ao final dela)
F1  Recebimento dos códigos
F2  Análise e inventário
F3  Consolidação do mapa real
F4  Desenho da arquitetura
F5  Migração
F6  Validação
F7  Encerramento
```

Cada fase tem um **gate**: uma condição objetiva sem a qual a fase seguinte não começa.

---

## F0 — Preparação (esta etapa)

**Entrada.** A pasta `documentação/`.

**Trabalho.** Compreensão da documentação, estrutura de diretórios, documentos de entendimento, checklists, relatórios de lacunas e roteiro da análise técnica.

**Saída.** Este conjunto de documentos, `projetos-origem/` pronta para receber os códigos.

**Gate para F1.** ✅ Os documentos de `docs/01-entendimento/` e `docs/05-proxima-etapa/` existem e são suficientes para que alguém sem contexto prévio comece a análise do Projeto 1.

**⚠️ Não é gate:** a resolução das pendências da área cliente. Elas bloqueiam a **implementação** de regras específicas, não a análise do código.

---

## F1 — Recebimento dos códigos

**Entrada.** Os códigos dos seis projetos (mais o sétimo, se existir).

**Trabalho.**
1. Inserir cada projeto na pasta correspondente de `projetos-origem/`, **sem alterar nada**
2. Aplicar [`../03-checklists/checklist-insercao-dos-codigos.md`](../03-checklists/checklist-insercao-dos-codigos.md) a cada um
3. Registrar o que chegou e o que não chegou

**Saída.** `projetos-origem/` populada; um registro de recebimento por projeto em `trabalho/inventarios/`.

**Gate para F2.** ✅ Todo projeto recebido tem: ponto de entrada identificável, lista de dependências, e o registro de recebimento preenchido. Projetos ausentes estão explicitamente listados como ausentes.

**Decisão que se resolve aqui.** O **Épico 5**: ao receber o P4, verifica-se se HU-17/HU-18 estão lá dentro. A pasta `projeto-7-epico-5-carga-agi/` é mantida ou descartada conforme o achado.

---

## F2 — Análise e inventário

**Entrada.** Códigos recebidos + [`../05-proxima-etapa/roteiro-analise-tecnica.md`](../05-proxima-etapa/roteiro-analise-tecnica.md).

**Trabalho.** Na ordem **P1 → P2 → P3 → P4 → P7 → P5 → P6**, para cada projeto:
1. Preencher o inventário (template em `docs/05-proxima-etapa/templates/`)
2. Mapear código → HU
3. Registrar qual **versão da regra** (V1 ou V2) cada trecho implementa
4. Registrar candidatos a componente compartilhado
5. Registrar duplicações contra os projetos já analisados

**Saída.** Um inventário por projeto, um catálogo de candidatos e um registro de duplicações, todos em `trabalho/inventarios/`.

**Gate para F3.** ✅ Todos os projetos inventariados; toda HU rastreada a código ou explicitamente marcada como "não implementada"; todo candidato a componente compartilhado com pelo menos duas ocorrências identificadas.

**⚠️ Esta é a fase que valida ou invalida o mapa de F0.** Se o código não respeitar a fronteira dos projetos informada, o mapa muda — e isso é resultado legítimo, não erro.

---

## F3 — Consolidação do mapa real

**Entrada.** Os inventários de F2.

**Trabalho.**
1. Reconciliar o mapa documental com o mapa real
2. Consolidar o catálogo de componentes compartilhados: promover o que atende aos critérios, rejeitar o resto com justificativa
3. Consolidar as duplicações e classificá-las (idêntica / divergente / falsa)
4. Para cada duplicação **divergente**, apontar qual implementação está aderente à V2
5. Listar o que é dívida técnica e **não** será tratada na unificação

**Saída.** Mapa real consolidado; catálogo fechado de componentes compartilhados; lista de divergências de regra endereçada à área cliente.

**Gate para F4.** ✅ Cada divergência de regra tem um dono e um encaminhamento. Nenhuma decisão de "qual implementação vale" foi tomada pela equipe técnica sozinha quando envolve regra de negócio.

---

## F4 — Desenho da arquitetura

**Entrada.** Mapa real + catálogo de componentes.

**Trabalho.** Definir a estrutura do repositório unificado: organização de pacotes, fronteiras da base comum, como cada `main.py` se compõe, configuração, logging, tratamento de erro, testes, e os pontos de retomada de cada RPA.

**Saída.** Documento de arquitetura, validável contra [`../03-checklists/checklist-validacao-da-arquitetura-final.md`](../03-checklists/checklist-validacao-da-arquitetura-final.md).

**Gate para F5.** ✅ A arquitetura passa no checklist de validação **em papel**, e cada componente da base comum tem sua origem rastreada a ocorrências reais no código.

⚠️ **Esta fase não pode ser antecipada.** É explicitamente fora do escopo de F0 — ver [`decisoes-que-dependem-do-codigo.md`](decisoes-que-dependem-do-codigo.md).

---

## F5 — Migração

**Entrada.** Arquitetura aprovada.

**Trabalho.** Ver [`estrategia-de-migracao.md`](estrategia-de-migracao.md). Em resumo: migração por camadas (utilitários → dados → arquivos → regras → integrações → fluxos), depois por RPA, na ordem RPA 1 → RPA 2 → RPA 4 → RPA 3.

**Saída.** `unificado/` com os quatro RPAs.

**Gate para F6.** ✅ Cada RPA executa de ponta a ponta em ambiente de teste; nenhum código de `projetos-origem/` foi alterado.

---

## F6 — Validação

**Entrada.** Repositório unificado.

**Trabalho.** Comprovar equivalência funcional contra os projetos de origem: mesmas entradas, mesmos artefatos e mesmos registros em banco. Aplicar os checklists de padronização e de validação da arquitetura.

**Saída.** Relatório de validação, com as divergências encontradas e sua justificativa (toda divergência é intencional e documentada, ou é bug).

**Gate para F7.** ✅ Todos os checklists aplicados; toda divergência de comportamento justificada.

---

## F7 — Encerramento

**Trabalho.** Documentar o estado final, registrar a dívida técnica que ficou, arquivar `projetos-origem/` (mantida para referência, não removida), e entregar a lista de pendências ainda abertas com a área cliente.

**Saída.** Repositório unificado documentado, com o que ficou de fora explicitamente listado.

---

## Papéis

| Papel | Responsabilidade |
|---|---|
| **Analista técnico / IA** | Executa F1–F6 seguindo os checklists; **não decide regra de negócio** |
| **GP (Btime)** | Escopo, prazo, encaminhamento das pendências à Vivo |
| **PO / área cliente (Vivo)** | Decide toda pendência de regra: data de corte, borda de 1%, CBS/IBS, envio automático, escopo da HU-20 |
| **Desenvolvedor original** | Fonte de contexto sobre decisões de implementação não documentadas |

**Regra de fronteira:** quando a análise encontra duas implementações divergentes da mesma regra, a escolha entre elas **não é técnica**. Vai para o PO. O papel da análise é apresentar as duas com clareza e dizer qual está aderente à V2.

---

## Pendências que atravessam o plano

Nenhuma destas bloqueia F1–F3, mas todas bloqueiam parte de F4–F6:

| Pendência | Bloqueia |
|---|---|
| Data de corte | Gatilho do RPA 1 e do RPA 2; regra de reprocessamento |
| Borda de 1% (valor, sinal, base) | Regra de decisão do RPA 2 |
| Épico 5 — onde está o código | Composição do RPA 3 (resolvido em F1) |
| Envio automático da HU-15 | Fluxo do RPA 3 — passo irreversível |
| Escopo da HU-20 | Cisão do P6; se descartada, o RPA 4 fica trivial |
| CBS/IBS | Layout de arquivo, validação, comparação |
| `DE_EBT_..._MODELO.xlsx` | HU-17 |
| Mecanismo de sinalização do analista | Gatilho do RPA 3 |
| Mecanismo de disparo do RPA 4 | Existência autônoma do RPA 4 |

Catálogo completo em [`../04-relatorios/duvidas-pendentes.md`](../04-relatorios/duvidas-pendentes.md).

---

## O que este plano não faz

- Não estima prazo. Sem o volume e a qualidade do código, qualquer número seria ficção.
- Não define arquitetura. É F4.
- Não resolve regra de negócio. É da área cliente.
- Não corrige dívida técnica. É trabalho posterior, explícito e separado.
