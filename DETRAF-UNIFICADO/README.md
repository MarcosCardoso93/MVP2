# DETRAF UNIFICADO

Repositório de trabalho da **unificação dos projetos RPA do DETRAF MVP2** (Btime / Telefônica Vivo — GSA ATA0000574).

O objetivo é consolidar **seis projetos independentes** em um repositório único com **quatro RPAs** sobre uma base comum.

---

## Estado atual

🟢 **Etapa 0 — Preparação documental:** concluída.
🟢 **Etapa 1 — Unificação dos Projetos 1 a 4:** concluída. **246 testes passando.**
⬜ **Próxima etapa:** completar o RPA 3 e criar o RPA 4, quando P5, P6 e o Épico 5 forem entregues.

| RPA | Situação |
|---|---|
| **1** — captura | ✅ completo, 46 testes |
| **2** — validação e apuração | ✅ completo, ⚠️ **0 testes** (P2 e P3 vieram sem cobertura) |
| **3** — contestação, AGI e EC | ⚠️ **parcial** — orquestração é stub; faltam P5, P6 e o Épico 5 |
| **4** — retificação | ⬜ depende do P6 |

Mais 16 módulos numa base compartilhada, com 36 testes.

---

## Por onde começar

| Você quer… | Leia |
|---|---|
| **Rodar ou mexer no código** | [`unificado/README.md`](unificado/README.md) |
| **Saber o que a unificação mudou** | [`docs/04-relatorios/relatorio-unificacao-p1-a-p4.md`](docs/04-relatorios/relatorio-unificacao-p1-a-p4.md) |
| Entender o projeto | [`docs/01-entendimento/visao-geral-do-projeto.md`](docs/01-entendimento/visao-geral-do-projeto.md) |
| Onde cada HU está implementada | [`docs/04-relatorios/matriz-de-rastreabilidade.md`](docs/04-relatorios/matriz-de-rastreabilidade.md) |
| O que está furado na documentação | [`docs/04-relatorios/relatorio-inconsistencias-e-lacunas.md`](docs/04-relatorios/relatorio-inconsistencias-e-lacunas.md) |
| O que perguntar ao cliente | [`docs/04-relatorios/duvidas-pendentes.md`](docs/04-relatorios/duvidas-pendentes.md) |
| Análise de cada projeto de origem | [`trabalho/inventarios/`](trabalho/inventarios/) |
| Inserir os projetos que faltam | o `README.md` da pasta em [`projetos-origem/`](projetos-origem/) |

---

## Estrutura

```
DETRAF-UNIFICADO/
├── documentação/          ← fontes primárias (PDF, .docx) — INTOCADA
├── docs/                  ← entendimento, planejamento, checklists, relatórios
├── projetos-origem/       ← código dos projetos — SOMENTE LEITURA
├── trabalho/inventarios/  ← análise de cada projeto, duplicações, candidatos
└── unificado/             ← os RPAs + a base comum
    ├── comum/
    ├── rpa1_captura/
    ├── rpa2_validacao_apuracao/
    └── rpa3_contestacao_agi_ec/
```

---

## O sistema, em resumo

Automatiza o ciclo de **despesa e contestação de despesa do Detraf**: recebe por e-mail os arquivos que as operadoras enviam cobrando pelo tráfego trocado com a Vivo, valida contra as regras regulatórias, compara com a expectativa calculada internamente pelo ICT e — quando a diferença passa de 1% — gera a contestação formal, carrega tudo no AGI e alimenta o Encontro de Contas. Volume: ~1.600 arquivos/mês.

## Os quatro RPAs de destino

| RPA | Responsabilidade | Gatilho | HUs |
|---|---|---|---|
| **1** | Captura de arquivos das operadoras | evento de e-mail + janela até a data de corte | 01–03 |
| **2** | Validação e apuração de contestação | lote, após a data de corte | 04–11 |
| **3** | Contestação, carga no AGI e Encontro de Contas | sinalização do analista no WebFat | 12–20 |
| **4** | Retificação de contestação | condição assíncrona de recuperação de tráfego | 21 |

O corte entre eles é por **natureza do gatilho**, não por afinidade temática.

## De seis projetos para quatro RPAs

```
P1 ──────────────────────────────────►  RPA 1     (direto)
P2 ──┐
     ├───────────────────────────────►  RPA 2     (convergência)
P3 ──┘
P4 ──┐
P5 ──┤
P6 ──┼─ (HU-20) ────────────────────►  RPA 3     (convergência)
P7?──┘  ⚠️ Épico 5, sem projeto atribuído
P6 ─── (HU-21) ─────────────────────►  RPA 4     (cisão do P6)
```

Apenas o **P1** mapeia 1:1. O **P6 precisa ser cindido**. E o **Épico 5 não tem dono** — ver abaixo.

---

## 🔴 O que precisa de decisão

| # | Achado | Situação | Decide |
|---|---|---|---|
| 1 | **Layout da expectativa Vivo é outro, e sem coluna `R$_Bruto`** — mas a comparação é sobre ela | 🆕 achado da unificação | Área cliente |
| 2 | **Data de corte indefinida** — bloqueia o gatilho de dois RPAs | aberta | Área cliente |
| 3 | **Épico 5 (HU-17/HU-18)** não está em nenhum projeto — confirmado que **não está no P4** | aberta | GP / dev |
| 4 | **HU-15:** o envio automático só sobrevive em texto revogado da V2 | aberta (P5 não entregue) | PO |
| 5 | **CBS/IBS:** escopo novo sem HU, sem layout e sem dono | aberta | PO / fiscal |
| 6 | **A regra de 1%** | ✅ **decidida a partir da V2** | — |
| 7 | **`_ENV` × `Base_Contestação`** | ✅ **respondida pelo código** | — |

Catálogo completo em [`docs/04-relatorios/relatorio-inconsistencias-e-lacunas.md`](docs/04-relatorios/relatorio-inconsistencias-e-lacunas.md), com pergunta pronta e destinatário em [`docs/04-relatorios/duvidas-pendentes.md`](docs/04-relatorios/duvidas-pendentes.md).

**A maior dívida técnica:** o RPA 2 não tem teste algum — e é onde estão as regras de negócio mais densas. Ver [`docs/04-relatorios/relatorio-unificacao-p1-a-p4.md`](docs/04-relatorios/relatorio-unificacao-p1-a-p4.md).

---

## Regras deste repositório

1. **`documentação/` é intocada.** São as fontes primárias.
2. **`projetos-origem/` é somente leitura** depois que o código for inserido. É a referência para comprovar equivalência funcional.
3. **A V2 é normativa.** Onde o código implementar a V1, isso é divergência a registrar — não comportamento a preservar.
4. **Nenhuma suposição silenciosa.** Toda conclusão que dependa de algo não verificado está marcada com ⚠️.
5. **Equivalência funcional antes de melhoria.** A unificação preserva comportamento; refatoração é trabalho posterior e explícito.

---

## Fontes documentais

Todas em [`documentação/`](documentação/), com índice e precedência em [`docs/00-fontes/README.md`](docs/00-fontes/README.md).

⚠️ **Antes de citar a V2**, leia esse índice: o documento contém um bloco de texto duplicado ao final, remanescente de versão anterior, com regras que foram deliberadamente removidas.
