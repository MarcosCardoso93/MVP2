# Fontes da Documentação — DETRAF MVP2

Índice das fontes primárias, o que cada uma decide e qual prevalece em caso de conflito.
Os arquivos originais permanecem em [`documentação/`](../../documentação/) e **não foram movidos nem alterados**.

---

## Ordem de precedência

Quando duas fontes divergirem, vale esta ordem:

1. **V2** — `[V2] Btime SPTI Detraf MVP2_ comentadaLuciana.docx` — **fonte normativa vigente**
2. `Analise_Mudancas_V2_por_Historia.md` — interpretação do delta V1→V2 (não cria regra, apenas registra a mudança)
3. `Relatorio_Separacao_RPAs_Detraf_MVP2.docx` — desenho de separação em 4 RPAs (proposta, derivada da V2)
4. `DETRAF_MVP2_Historias.pdf` — **backlog histórico (V1)**; vários critérios de aceitação estão desatualizados

> ⚠️ O PDF de histórias **não** é a especificação vigente. Ele é útil pela granularidade (21 HUs com critérios de aceitação), mas cada critério precisa ser conferido contra a V2 antes de virar requisito.

---

## 1. `DETRAF_MVP2_Historias.pdf` — Backlog (V1)

**Conteúdo:** 21 histórias de usuário organizadas em 6 épicos, cada uma com descrição e critérios de aceitação.

**Para que serve:** é a única fonte que quebra o processo em unidades rastreáveis (HU-01 a HU-21). A divisão dos seis projetos de origem é expressa em termos dessas HUs, então ela é indispensável para o mapeamento projeto → RPA.

**Cuidados:**
- Critérios de aceitação de HU-02, HU-07, HU-09, HU-10, HU-15 e HU-19 **estão superados pela V2**.
- Não contém as colunas CBS/IBS (escopo novo da V2).
- Não contém a data de corte (que a V2 deixa em aberto).

---

## 2. `[V2] Btime SPTI Detraf MVP2_ comentadaLuciana.docx` — Especificação vigente

**Conteúdo:** documento oficial de Solicitação de um novo RPA (GSA ATA0000574). Inclui partes interessadas, produto do projeto, regras de negócio (layout das 15 colunas, descritores, tarifas por região), passo a passo completo do processo, volume, anexos, riscos e premissas.

**Para que serve:** é a especificação normativa. Tudo que virar requisito precisa ter âncora aqui.

**Cuidados — leia antes de usar:**

- ⚠️ **Bloco de conteúdo duplicado ao final do documento.** Depois do item 7 (Risco/Premissas), o arquivo repete um trecho inteiro de uma versão anterior do texto (do "Da mesma forma, o robô copia o conteúdo dos arquivos gerados internamente…" até "Retificação de Contestação"). Esse bloco **não é a redação vigente** — ele contém regras que foram deliberadamente removidas do corpo principal. Duas delas sustentavam critérios de aceitação hoje frágeis:
  - o envio automático de e-mail sem aprovação do usuário (HU-15);
  - o preenchimento da coluna de contestação no Encontro de Contas quando há retenção (HU-19).

  Ao citar a V2, **verifique se a passagem está no corpo principal ou no bloco duplicado**.

- ⚠️ O documento contém contradições internas não resolvidas. Estão catalogadas em [`../04-relatorios/relatorio-inconsistencias-e-lacunas.md`](../04-relatorios/relatorio-inconsistencias-e-lacunas.md).

- A numeração de itens/páginas citada nos demais documentos (`pág. 13, item 4.1.3`) refere-se à **conversão do `.docx` em PDF**, não à paginação do Word.

**Anexos e planilhas externas referenciadas pela V2** (não versionados neste repositório):
- Anexo 5 — ABR Telecom (`https://www.abrtelecom.com.br/padronizacao`) — EOT, nome fantasia, tipo de serviço, região, concessão
- `Descritor_Remuneração` (Google Sheets)
- `CONT_PROC_MASCARA Geral 202506` (Google Sheets)
- `Tabelas para o RPA alimentar o Webfat - despesa.xlsx`
- `Base Contestação_GT GROUP_TBRA_202601_ROBO.xlsx`
- Mockup Detraf Despesa - MVP2 (Google Slides)

---

## 3. `Analise_Mudancas_V2_por_Historia.md` — Delta V1 → V2

**Conteúdo:** para cada uma das 21 HUs, o que mudou da V1 para a V2, com status (🟢 mantida / 🟡 atualizada / 🔴 impactada estruturalmente / ⚠️ risco-pendência) e ação recomendada. Traz também itens novos da V2 sem HU correspondente e as pendências que a V2 deixa em aberto.

**Para que serve:** é a ponte entre o backlog e a especificação. É o atalho para saber, por HU, se o código do projeto de origem pode estar implementando uma regra revogada.

**Cuidados:** é um documento analítico, não normativo. Onde ele recomenda ação ("reescrever a história…"), isso ainda **não foi feito** no PDF de histórias.

---

## 4. `Relatorio_Separacao_RPAs_Detraf_MVP2.docx` — Desenho dos 4 RPAs

**Conteúdo:** proposta de separação da automação em 4 RPAs, com gatilho, responsabilidades, entrega e justificativa de cada corte, ancorada em páginas da V2.

**Para que serve:** define o **alvo** da unificação. É a fonte de `docs/01-entendimento/responsabilidades-dos-rpas.md`.

**Cuidados:**
- A V2 diz "entre 3 e 4 RPA's"; o relatório opta por 4. É uma proposta consistente com a V2, mas é proposta.
- O relatório **não** menciona explicitamente a divisão em seis projetos de código. O mapeamento projeto → RPA foi derivado nesta etapa e está em [`../01-entendimento/mapa-projetos-epicos-historias-rpas.md`](../01-entendimento/mapa-projetos-epicos-historias-rpas.md).
- O próprio relatório levanta uma alternativa em aberto: isolar a carga no AGI em etapa própria dentro do RPA 3, caso ela se mostre instável. ⚠️ Decisão que depende da análise do código.

---

## 5. Arquivo de trava do LibreOffice

`documentação/.~lock.Relatorio_Separacao_RPAs_Detraf_MVP2.docx#` é um arquivo temporário de trava, gerado por um editor com o documento aberto. Não é fonte documental. Não foi removido (esta etapa não exclui arquivos), mas é candidato a `.gitignore`.

---

## Como esta documentação foi extraída

Os `.docx` foram lidos descompactando o pacote OOXML e extraindo o texto de `word/document.xml`; o PDF foi lido decodificando os streams de conteúdo (ASCII85 + Flate). Nenhum arquivo fonte foi modificado no processo. Se for preciso reextrair, note que o `.docx` da V2 tem ~6,8 MB, quase todos em imagens de tela do WebFat e do AGI — as imagens **não** foram analisadas nesta etapa e podem conter detalhe de interface relevante para as HUs de automação de UI (HU-17, HU-18, HU-20, HU-21).
