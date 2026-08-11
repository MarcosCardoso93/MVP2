# Checklist — Validação da Arquitetura Final

Aplicar duas vezes: **em papel** ao fim de F4 (gate para a migração) e **no código** em F6.

---

## 1. Independência dos RPAs

- [ ] Cada RPA tem seu próprio `main.py`
- [ ] Cada RPA executa isoladamente, sem que outro esteja rodando
- [ ] Nenhum RPA importa código de outro RPA
- [ ] Nenhum RPA chama outro diretamente
- [ ] A comunicação entre eles se dá **apenas** pelos artefatos e tabelas documentados:

| De → Para | Meio |
|---|---|
| RPA 1 → RPA 2 | arquivos em rede + servidor WebFat + `tbl_..._arquivos` |
| RPA 2 → RPA 3 | `tbl_..._contestacao` + decisão do analista |
| RPA 3 → RPA 4 | contestação registrada no AGI (mês anterior) |

- [ ] Cada RPA pode ser reexecutado sem exigir reexecução dos outros
- [ ] Falha de um RPA não impede os demais de rodarem

---

## 2. Cobertura funcional

- [ ] As 21 HUs estão rastreáveis a exatamente um RPA
- [ ] Nenhuma HU ficou sem dono
- [ ] Nenhuma HU está implementada em dois RPAs
- [ ] HUs **não implementadas** estão explicitamente listadas, não silenciosamente ausentes

Conferência por RPA:

| RPA | HUs esperadas | ✅ |
|---|---|---|
| RPA 1 | 01, 02, 03 | [ ] |
| RPA 2 | 04, 05, 06, 07*, 08, 09, 10, 11 | [ ] |
| RPA 3 | 12, 13, 14, 15, 16, 17, 18, 19, 20** | [ ] |
| RPA 4 | 21 | [ ] |

\* HU-07 fundida na HU-04 pela V2 — verificar que **não** existe caminho dedicado.
\*\* HU-20 pode ter sido descartada do escopo — verificar a decisão antes.

- [ ] O escopo de CBS/IBS (HU-22) tem destino definido, ou está explicitamente registrado como fora do escopo desta unificação

---

## 3. Base compartilhada

- [ ] Todo componente da base comum tem **pelo menos duas ocorrências reais** rastreadas na origem
- [ ] Nenhum componente foi promovido por antecipação
- [ ] Nenhum componente depende de estado exclusivo de um RPA
- [ ] Nenhum componente implementa regra em **pendência aberta**
- [ ] Nenhum componente precisa saber quem o chamou
- [ ] Nenhum componente chamado `utils`, `helpers`, `common` ou `misc`
- [ ] Cada componente tem ficha registrando origem e critérios atendidos

---

## 4. Ausência de duplicação de regra

- [ ] Nenhuma regra de negócio está implementada em mais de um lugar
- [ ] Cada uma destas existe uma única vez:
  - [ ] Resolução de EOT no Anexo 5
  - [ ] Mapeamento descritor → remuneração
  - [ ] Validação de tarifa
  - [ ] Construção de caminho de rede
  - [ ] Convenções de nome de arquivo
  - [ ] Cálculo de variação e decisão S/N
  - [ ] Regra do `_BK`
  - [ ] Regra do `_ERRO`
- [ ] Duplicações mantidas de propósito têm registro com a justificativa

---

## 5. Aderência à V2

- [ ] Nenhuma HU 🔴 implementa a regra da **V1**:
  - [ ] HU-02 identifica pela **EOT/Anexo 5**, não pelo domínio do remetente
  - [ ] HU-07 **não** tem caminho de erro dedicado
  - [ ] HU-09/HU-10 gravam em **banco**
  - [ ] HU-19 grava nos **campos do banco**, não em planilha
- [ ] Toda divergência de regra que restou foi decidida pelo **PO**, não pela equipe técnica
- [ ] Pontos com pendência aberta estão marcados no código, com a pendência nomeada

---

## 6. Premissas não-funcionais da V2

- [ ] Nenhum valor de tarifa constante no código
- [ ] Nenhum mapeamento descritor → remuneração constante
- [ ] Nenhum limiar constante (1%, `0,9635`)
- [ ] Layout dos arquivos **configurável, não posicional-fixo** (risco do imposto de 2028)
- [ ] Tabelas de consulta editáveis pelo usuário, conforme a premissa 10.4

---

## 7. Passos irreversíveis e retomada

- [ ] Passos irreversíveis identificados e marcados no código:
  - [ ] HU-14 — consumo da numeração CT
  - [ ] HU-15 — envio do e-mail à operadora
  - [ ] HU-17/HU-18 — carga no AGI
  - [ ] HU-21 — evento "Recuperação"
- [ ] Cada RPA tem pontos de retomada documentados
- [ ] Reprocessar o RPA 3 após falha na carga do AGI **não** reenvia carta e e-mail
- [ ] Reprocessar não duplica lançamento financeiro no AGI
- [ ] Reprocessar não queima numeração CT desnecessariamente
- [ ] A numeração CT tem controle de concorrência, ou o risco está registrado e aceito

---

## 8. Equivalência funcional

Para cada RPA, com as mesmas entradas da origem:

| RPA | Comparar | ✅ |
|---|---|---|
| RPA 1 | Arquivos salvos (caminho, nome, conteúdo); e-mails movidos; registros em `tbl_..._arquivos` | [ ] |
| RPA 2 | Registros em `tbl_..._arquivos` e `tbl_..._contestacao`; arquivos `_BK` e `_ERRO`; e-mails de crítica | [ ] |
| RPA 3 | `_EXT`, `_INT`, `_ENV`, carta, `CONT_PROC`; e-mail; `tipo_contestacao`; `carga_agi`; campos do EC | [ ] |
| RPA 4 | Evento "Recuperação" com os quatro campos | [ ] |

- [ ] Toda divergência encontrada é **intencional e documentada**, ou é bug
- [ ] Diferenças esperadas (timestamp, ordem de linhas, metadados) foram declaradas **antes** da comparação
- [ ] A validação **não tocou produção** em nenhum momento

---

## 9. Configuração, logging e erro

- [ ] Um único mecanismo de configuração
- [ ] Separação entre configuração comum e por RPA
- [ ] Nenhuma credencial no repositório
- [ ] Um único mecanismo de logging, com correlação por operadora/mês/RPA
- [ ] Uma única política de tratamento de erro
- [ ] O comportamento "segue para o próximo processamento" está implementado de uma só forma

---

## 10. Testabilidade

- [ ] Cada RPA é executável em ambiente de teste, sem tocar produção
- [ ] Existe massa de dados de teste
- [ ] Regras de negócio são testáveis isoladamente, sem rede, banco ou UI
- [ ] Existe ambiente de teste do AGI e caixa de e-mail de teste
- [ ] O contador de numeração CT é isolável

⚠️ Falha nos dois últimos é **impedimento de validação**, não item pendente.

---

## 11. Documentação

- [ ] README por RPA: o que faz, gatilho, como executar, dependências de ambiente
- [ ] README da base comum
- [ ] Mapa HU → RPA → código atualizado com a realidade
- [ ] Pendências ainda abertas listadas
- [ ] Dívida técnica registrada, com o que ficou de fora e por quê
- [ ] `projetos-origem/` documentada como referência arquivada

---

## 12. Verificação final de integridade

- [ ] `projetos-origem/` **intacta** — nada movido, alterado ou excluído
- [ ] `documentação/` **intacta**
- [ ] O repositório unificado não contém código morto herdado
- [ ] Nenhum código do fluxo de **Receita** (ATA0000571/567/572) foi arrastado junto

---

## Veredicto

- [ ] **Aprovado** — todos os itens atendidos
- [ ] **Aprovado com ressalvas** — itens abertos listados, com dono e prazo
- [ ] **Reprovado** — itens bloqueantes:

> ⚠️ Falha em **§1 (independência)**, **§4 (duplicação de regra)**, **§5 (aderência à V2)** ou **§8 (equivalência funcional)** é bloqueante. Os demais admitem ressalva registrada.
