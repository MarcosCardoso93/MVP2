# Detraf MVP2 — Análise de Mudanças da V2 por História de Usuário

**Referência base:** `DETRAF_MVP2_Historias.pdf` (21 HUs / 6 Épicos)
**Referência comparada:** `_V2_Btime_SPTI_Detraf_MVP2_comentadaLuciana.docx` (páginas citadas conforme conversão em PDF)

## Legenda de status

| Ícone | Significado |
|---|---|
| 🟢 Mantida | Sem mudança relevante na V2 |
| 🟡 Atualizada | Critérios de aceitação precisam de ajuste/adição |
| 🔴 Impactada estruturalmente | A V2 muda a arquitetura da entrega, não só o texto |
| ⚠️ Risco/pendência | A V2 remove ou deixa em aberto algo que a história pressupõe |

---

## ÉPICO 1 — Captura de Arquivos via E-mail

### HU-01 — Leitura e organização do inbox de e-mail (Outlook) — 🟡⚠️

**O que muda:**
- ⚠️ O critério "varredura diária **após o dia 05**" perde sustentação: o parágrafo de periodicidade dos RPAs foi **removido** da V2. No lugar, existe apenas a menção de que a "**data de corte** do processo está em análise pela área cliente" (pág. 3), ainda sem regra definida.
- 🟡 Novo critério a incluir: o robô passa a localizar **e-mails que não contenham a palavra "CONTESTAÇÃO"**, filtrando pelo **mês de referência**, e baixando **apenas arquivos csv ou excel** (pág. 13, item 4.1.3).

**Ação recomendada:** não fechar o critério de periodicidade até a área cliente confirmar a regra de data de corte; adicionar o novo filtro de e-mail aos critérios de aceitação.

---

### HU-02 — Identificação da operadora pelo remetente (WebFat) — 🔴

**O que muda:**
- A V2 **não utiliza mais** o lookup do "@ do remetente" na tabela de contatos do WebFat para identificar a operadora a partir do e-mail — essa proposta foi retirada do texto.
- Em seu lugar: "**o nome correto da operadora é pela EOT da credora** presente no anexo 5, busca pela coluna nome fantasia" (pág. 13, item 4.1.6).

**Impacto:** o mecanismo de identificação muda de "metadado do e-mail (domínio do remetente)" para "conteúdo do arquivo (EOT credora × Anexo 5)".

**Ação recomendada:** reescrever a história substituindo o critério de lookup de domínio pelo novo mecanismo baseado em EOT/Anexo 5.

---

### HU-03 — Salvamento dos arquivos na estrutura de pastas de rede — 🟡

**O que muda:**
- Novo critério: além da pasta de rede, é **obrigatório salvar também no servidor do Webfat**, "para que o usuário consiga abrir o documento pela ferramenta" (pág. 13, item 4.1.5).
- Novo critério (não coberto anteriormente): se a operadora reenviar um **arquivo com o mesmo nome**, "o documento anterior é subscrito e um novo processamento é iniciado, seguindo a regra de corte" (pág. 9, item 2.7).

**Ação recomendada:** adicionar os dois critérios acima à história.

---

## ÉPICO 2 — Validação dos Arquivos de Detraf

### HU-04 — Validação estrutural das colunas do arquivo da operadora — 🟡

**O que muda:**
- A regra de erro deixou de ser específica (antes só existia para o caso descritor L→L / STFC) e passou a ser uma **regra geral**: "caso as regras não sejam validadas, os registros devem ser direcionados para um arquivo de mesmo nome com `_ERRO`" (pág. 10).

**Impacto:** amplia o escopo desta história e reduz a especificidade da HU-07 (ver abaixo).

---

### HU-05 — Validação da tarifa regulada (tbl_detraf_tarifas) — 🟡

**O que muda:**
- A HU já contempla o descritor TU-COM nos critérios de aceitação, alinhado com a V2 (pág. 7).
- Falta o critério: a relação descritor × remuneração agora é consultada na tabela **`tbl_detraf_mapeamento_descritores`** do banco Webfat (pág. 7) — não estava explícito na história.

**Ação recomendada:** adicionar referência à tabela `tbl_detraf_mapeamento_descritores`.

---

### HU-06 — Tratamento de arquivo BK (SMP não-PMS) — 🟢

Sem mudanças relevantes identificadas na V2.

---

### HU-07 — Tratamento de erro L-L (STFC) — arquivo `_ERRO` — 🔴

**O que muda:**
- A V2 **removeu o tratamento específico** descrito anteriormente ("crítica... encaminha e-mail para operadora" / "separar em `_ERRO`" para o arquivo de expectativa). Esse comportamento foi absorvido pela regra geral do `_ERRO` (ver HU-04).

**Ação recomendada:** fundir esta história com a HU-04, deixando claro que o caso L-L/STFC não tem mais tratamento diferenciado — segue o mesmo fluxo genérico de erro.

---

### HU-08 — Registro dos arquivos validados no WebFat — 🟡

**O que muda:**
- A V2 detalha o campo **`tipo_registro`** com valores explícitos: `"DETRAF"` (dados da operadora sempre consolidados), `"EXPECTATIVA"` (arquivo validado sem erro) e `"ERRO"` (arquivo com problema) — pág. 16-17.
- Mudança de tratamento de erro: "correção manual ou abertura de chamado" (documentação antiga) virou "**avalia possível correção automática**" (pág. 16).

**Ação recomendada:** atualizar os critérios com os valores do campo `tipo_registro`; confirmar com o time se a correção automática já é uma decisão de produto validada ou apenas uma intenção de redação.

---

## ÉPICO 3 — Batimento Detraf x Expectativa

### HU-09 — Consolidação dos dados no arquivo Base Contestação — 🔴

**Esta é a mudança mais estrutural do documento.**

A V2 afirma explicitamente: "**não é necessário gerar o arquivo**, mas usar a lógica e popular a tabela `tbl_rpa_log_detraf_despesa_contestacao`" (pág. 19). Isso é reforçado por: "todas as planilhas deste processo foram substituídas por banco, **exceto dois arquivos**" (o `_ENV` para a operadora e o de carga no AGI).

**Impacto:** o artefato "Base_Contestação" com abas e tabelas dinâmicas deixa de ser uma planilha física e passa a ser lógica que grava diretamente no banco de dados.

**Ação recomendada:** reescrever a história trocando "criar arquivo Base_Contestação" por "popular tabela do banco", preservando a lógica de cálculo mas mudando o artefato de saída.

---

### HU-10 — Análise de contestação por EOT e tipo de remuneração — 🟡🔴

**O que muda:**
- Mesma observação da HU-09: o resultado da sumarização vai para a tabela do banco, não mais para a aba "Contest" de uma planilha.
- Novo ponto em aberto, sem critério definido: os **novos impostos CBS/IBS** aparecem nos arquivos de Detraf Vivo, Carga Geral do AGI e relatórios (pág. 10, itens 2.10.2–2.10.3), mas não há regra clara sobre se entram na sumarização/comparação desta etapa.

**Ação recomendada:** atualizar o destino de dados (banco em vez de planilha) e abrir uma pendência específica sobre CBS/IBS nesta análise.

---

### HU-11 — Exibição dos dados de contestação no WebFat (analista) — 🟢

**O que muda:**
- Apenas renomeação: "cava Expectativa" (erro de digitação da doc. antiga) virou "**aba Contestação**" no Webfat (pág. 19). Sem mudança de critério.

---

## ÉPICO 4 — Geração de Arquivos para Contestação e Carga AGI

### HU-12 — Geração do arquivo EXT para carga no AGI — 🟢
### HU-13 — Geração do arquivo INT para carga no AGI — 🟢

Sem mudanças relevantes identificadas na V2.

---

### HU-14 — Geração do arquivo `_ENV` e carta para a operadora — 🟢

Sem mudanças relevantes identificadas.

---

### HU-15 — Envio do e-mail de contestação à operadora — ⚠️

**O que muda:**
- A frase que sustentava o critério "disparo automático... sem aprovação manual" ("o robô deve enviar o e-mail, sem necessidade de autorização do usuário, após a escolha do analista") foi **removida do corpo principal da V2**. Ela só sobrevive em um bloco de conteúdo duplicado ao final do documento, que corresponde a uma versão antiga do texto remanescente no arquivo, não à redação vigente.

**Ação recomendada:** confirmar explicitamente com a área cliente (Luciana/PO) se o envio automático sem aprovação continua sendo a regra de negócio antes de manter este critério como está.

---

### HU-16 — Geração do arquivo CONT_PROC para carga AGI — 🟡

**O que muda:**
- Novo critério: após gerar o arquivo, "o robô atualiza o campo **`tipo_contestacao`** da `tbl_rpa_log_detraf_despesa_contestacao`" (pág. 34) — não estava na história original.

---

## ÉPICO 5 — Carga no AGI

### HU-17 — Upload dos arquivos EXT/INT no AGI — 🟡⚠️

**O que muda:**
- Aparece um arquivo novo, sem contexto explicado: **`DE_EBT_TBRA_TLF_202509_C_INT_MODELO.xlsx`**, citado antes dos arquivos EXT/INT na etapa de carga (pág. 34). A V2 não esclarece seu papel no processo.

**Ação recomendada:** levantar com a área cliente/GP o propósito desse arquivo antes de detalhar os critérios de aceitação desta história.

---

### HU-18 — Upload do arquivo de contestação no AGI — 🟡

**O que muda:**
- Novo critério: após salvar no AGI, "o robô atualiza o campo **`carga_agi`** com o status da carga na `tbl_rpa_log_detraf_despesa_contestacao`" (pág. 38) — não estava na história original.

---

## ÉPICO 6 — Encontro de Contas

### HU-19 — Preenchimento do Encontro de Contas com despesa — 🔴

**O que muda:**
- Mesma mudança estrutural do Épico 3: em vez de "colar valores na planilha de Encontro de Contas", a V2 determina que o robô "**atualiza a tabela do banco webfat** `tbl_rpa_log_detraf_despesa_contestacao`", preenchendo os campos `minutos_operadora`, `vb_operadora`, `minutos_diferenca`, `vb_diferenca`, `minutos_variacao_perc`, `vb_variacao_perc` (pág. 38).
- ⚠️ O critério original sobre "coluna de contestação preenchida quando houver retenção" também não aparece mais no corpo principal da V2 — só no bloco duplicado de conteúdo antigo ao final do documento.

**Ação recomendada:** substituir "planilha" por "tabela/campos do banco" nos critérios; confirmar se o comportamento de retenção foi absorvido pelos novos campos ou se ficou pendente de definição.

---

### HU-20 — Verificação do Relatório Receitas e Despesas no AGI — 🟡

**O que muda:**
- Novo critério: "**comparar colunas CBS, IBS MUNICIPAL E IBS ESTADUAL**" (pág. 40) — adicionar aos critérios de aceitação existentes.

---

### HU-21 — Identificação de tráfego recuperado e retificação AGI — 🟢

Sem mudanças relevantes; a V2 mantém a mesma lógica descrita originalmente (pág. 42).

---

## Itens novos na V2 sem história correspondente

| Item | Descrição | Página V2 | Ação sugerida |
|---|---|---|---|
| CBS/IBS | Tratamento das 3 novas colunas (CBS, IBS Municipal, IBS Estadual) em arquivos de Detraf, Carga AGI e relatórios | pág. 10, 40 | Criar **HU-22 — Tratamento das colunas de novos impostos (CBS/IBS)**, cobrindo estrutura, validação e comparação |
| Memória local do RPA | "O robô irá atuar com a memória da máquina local... o Webfat terá a opção do analista transferir o arquivo para o Lagoa" | pág. 9-10, item 2.13 | Avaliar se precisa de história técnica própria ou se é detalhe de implementação da HU-03 |
| Separação de pastas VIVO/TLF | Arquivos de expectativa Vivo separados por pastas VIVO e TLF com "D" no final | pág. 3 | Incorporar como critério adicional na HU-03/HU-04 |

## Pendências que a própria V2 deixa em aberto

- **Data de corte e gatilho de batimento com a operadora** — impacta diretamente a HU-01 (pág. 3 e pág. 9, itens 2.4–2.5).
- **Papel do arquivo `DE_EBT_TBRA_TLF_202509_C_INT_MODELO.xlsx`** — impacta a HU-17 (pág. 34).
- **Envio automático de e-mail sem aprovação** — precisa confirmação, pois a frase que sustentava esse critério foi removida do corpo principal da V2 (impacta a HU-15).
- **Preenchimento da coluna de contestação com retenção no Encontro de Contas** — não aparece mais explicitamente no corpo principal da V2 (impacta a HU-19).

---

*Elaborado a partir da comparação entre `DETRAF_MVP2_Historias.pdf` e a documentação V2 (`_V2_Btime_SPTI_Detraf_MVP2_comentadaLuciana.docx`). Numeração de páginas refere-se à conversão do documento V2 em PDF.*
