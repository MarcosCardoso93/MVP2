# Roadmap da Unificação

Sequência de marcos, do recebimento dos códigos à entrega do repositório unificado.

> Os marcos são **ordenados por dependência**, não por data. Não há estimativa de prazo: sem conhecer o volume e a qualidade do código, qualquer número seria ficção. As estimativas entram no M2, quando o inventário existir.

---

## Visão geral

```
M0  ✅ Preparação documental
M1  ⚠️ Códigos recebidos e verificados          ← o P6 veio SÓ com a HU-20; falta a HU-21
M2  ✅ Análise concluída — mapa real
M3  ✅ Arquitetura definida e aprovada
M4  ✅ Base comum estabelecida
M5  ✅ RPA 1 migrado e validado
M6  ✅ RPA 2 migrado e validado
M7  ⬜ RPA 4 migrado e validado                 ← bloqueado: a HU-21 não foi entregue
M8  ✅ RPA 3 migrado e validado                 ← parcial: HU-15 sem destinatários (Q16); HU-20 migrada, mas a V2 pede confirmação de escopo (Q7)
M9  ⬜ Unificação validada e entregue
```

Em paralelo, uma trilha que não depende do código:

```
P1  ✅ Pendências de negócio endereçadas à área cliente
P2  ⬜ Pendências de negócio respondidas        ← Q1, Q6, Q12, Q14, Q16, Q22 em aberto
```

> **Atualizado em 2026-08-04.** O restante deste documento é a fotografia da etapa
> documental e descreve o plano como ele foi traçado — a sequência se manteve, mas
> os detalhes de cada marco não foram reescritos. Para o estado atual, ver
> `docs/04-relatorios/relatorio-fechamento-pendencias-codigo.md` e
> `unificado/README.md`.

---

## M0 — Preparação documental ✅

**Entregue nesta etapa.**

- Documentação analisada e compreendida
- Estrutura de diretórios pronta para receber os códigos
- Documentos de entendimento, planejamento, checklists e relatórios
- Roteiro da análise técnica

**Critério de conclusão.** Alguém sem contexto prévio consegue iniciar a análise do Projeto 1 lendo apenas `docs/05-proxima-etapa/roteiro-analise-tecnica.md` e os checklists.

---

## M1 — Códigos recebidos e verificados

**Depende de:** M0 + disponibilização dos códigos pelo time.

**Trabalho.** Inserir cada projeto na pasta correspondente e aplicar o [checklist de inserção](../03-checklists/checklist-insercao-dos-codigos.md).

**Entregas.**
- `projetos-origem/` populada
- Um registro de recebimento por projeto
- Lista do que não chegou

**Decisões que se resolvem aqui.**
- **Onde está o Épico 5.** Verificar no P4 se HU-17/HU-18 estão lá. Manter ou descartar `projeto-7-epico-5-carga-agi/`
- **Existe ambiente de teste do AGI e caixa de e-mail de teste?** ⚠️ Se não, é impedimento para M7 e M8 — escale imediatamente
- **Há credencial commitada?** Achado de segurança, reportar na hora

**Critério de conclusão.** Todo projeto recebido tem ponto de entrada identificável, dependências listadas e registro preenchido. Ausências explicitamente listadas.

---

## M2 — Análise concluída, mapa real consolidado

**Depende de:** M1.

**Trabalho.** Analisar os projetos na ordem **P1 → P2 → P3 → P4 → P7 → P5 → P6**, conforme o [roteiro](../05-proxima-etapa/roteiro-analise-tecnica.md). Consolidar o mapa real, o catálogo de componentes e o registro de duplicações.

**Entregas.**
- Um inventário por projeto
- Mapa real (código → HU → RPA), reconciliado com o mapa documental
- Catálogo de componentes candidatos, com veredicto por critério
- Registro de duplicações classificadas
- Lista de divergências de regra, endereçada ao PO
- **Primeira estimativa de esforço** — só aqui ela deixa de ser chute

**Critério de conclusão.** Toda HU rastreada a código ou marcada explicitamente como não implementada. Todo candidato a componente compartilhado com pelo menos duas ocorrências localizadas (arquivo e linha). Toda divergência de regra com dono e encaminhamento.

⚠️ **Este marco pode invalidar o mapa documental.** Se o código não respeitar a fronteira informada dos projetos, o mapa muda — e isso é resultado legítimo, não erro de M0.

---

## M3 — Arquitetura definida e aprovada

**Depende de:** M2.

**Trabalho.** Tomar as decisões listadas em [`decisoes-que-dependem-do-codigo.md`](decisoes-que-dependem-do-codigo.md).

**Entregas.**
- Documento de arquitetura do repositório unificado
- Definição da base comum, com cada componente rastreado a ocorrências reais
- Estratégias de configuração, logging, tratamento de erro e testes
- Pontos de retomada de cada RPA

**Critério de conclusão.** A arquitetura passa no [checklist de validação](../03-checklists/checklist-validacao-da-arquitetura-final.md) **em papel**, e nenhum componente da base comum foi promovido por antecipação.

---

## M4 — Base comum estabelecida

**Depende de:** M3.

**Trabalho.** Migrar as camadas compartilhadas na ordem: utilitários → acesso a dados → arquivos Detraf → regras de negócio → integrações.

**Entregas.** Base comum funcional, com testes.

**Critério de conclusão.** Nenhum componente com uma única ocorrência (salvo justificativa registrada). Nenhuma regra em pendência aberta. Nenhuma tarifa, mapeamento ou limiar constante no código.

⚠️ **A base comum não fica pronta aqui — fica *iniciada*.** Ela é confirmada e corrigida a cada RPA migrado. Esperar que M4 produza a versão final é o erro clássico.

---

## M5 — RPA 1 migrado e validado

**Depende de:** M4.

**Escopo.** HU-01, HU-02, HU-03. Origem: apenas P1.

**Por que primeiro.** Único caso 1:1. Menor risco. É onde o processo de migração se calibra.

**Ponto de atenção.** ⚠️ A HU-02 mudou de mecanismo na V2 (domínio do remetente → EOT/Anexo 5). Se o P1 implementa a V1, isto não é migração — é retrabalho, e precisa ser dimensionado à parte.

**Bloqueio parcial.** ⚠️ A data de corte não está definida, então o gatilho e a regra de reprocessamento ficam em aberto. Migre o resto e isole o ponto.

**Critério de conclusão.** Executa ponta a ponta; arquivos salvos e registros em banco equivalentes à origem.

---

## M6 — RPA 2 migrado e validado

**Depende de:** M5.

**Escopo.** HU-04 a HU-11. Origem: P2 + P3 (primeira convergência).

**Pontos de atenção.**
- ⚠️ **HU-09 muda de artefato:** planilha → banco. Se o P3 manipula a `Base_Contestação` como planilha, a camada de saída é reescrita, não migrada
- ⚠️ **HU-07 deve ser fundida na HU-04.** Se houver caminho de erro dedicado ao caso L-L, ele é candidato a eliminação
- ⚠️ **Borda de 1% indefinida.** Isole a decisão S/N; não promova para a base comum
- A fronteira P2/P3 é onde a duplicação é mais provável

**Critério de conclusão.** Registros em `tbl_..._arquivos` e `tbl_..._contestacao` equivalentes à origem; arquivos `_BK` e `_ERRO` idênticos.

---

## M7 — RPA 4 migrado e validado

**Depende de:** M6.

**Escopo.** HU-21. Origem: fração do P6.

**Por que antes do RPA 3.** É o menor consumidor da automação do AGI. Provar essa camada aqui, onde um erro custa pouco, é melhor que descobrir problemas dentro do RPA 3.

**Pontos de atenção.**
- ⚠️ **Exige a cisão do P6.** Confirmar antes se a HU-20 continua no escopo — se for descartada, não há cisão
- ⚠️ **Mecanismo de disparo indefinido.** A detecção está descrita no RPA 3, a execução é aqui
- ⚠️ **Pendência da V2** sobre nomes de operadora que mudam entre a contestação e a retificação
- ⚠️ **Requer ambiente de teste do AGI** — o evento "Recuperação" é irreversível

**Critério de conclusão.** Evento "Recuperação" gravado no AGI de teste com os quatro campos corretos.

---

## M8 — RPA 3 migrado e validado

**Depende de:** M7.

**Escopo.** HU-12 a HU-20. Origem: P4 + P5 + P6(HU-20) + P7?.

**O marco mais complexo.** 9 HUs, 3–4 origens, artefatos irreversíveis.

**Pontos de atenção.**
- ⚠️ **Passos irreversíveis:** envio de e-mail, consumo da numeração CT, carga no AGI. Exige caixa de e-mail de teste e contador CT isolado
- ⚠️ **Envio automático da HU-15 não confirmado.** Não implemente disparo sem aprovação até a área cliente confirmar
- ⚠️ **Contradição `_ENV` × `Base_Contestação`** (M13 de `decisoes-que-dependem-do-codigo.md`) precisa estar resolvida
- ⚠️ **HU-19 muda de artefato:** planilha de EC → campos de banco
- ⚠️ **HU-17 depende do papel do `DE_EBT_..._MODELO.xlsx`**, ainda desconhecido
- ⚠️ Definir onde fica o ponto de retomada entre "carta enviada" e "carga no AGI"

**Critério de conclusão.** Todos os artefatos e registros equivalentes à origem, validados sem tocar produção.

---

## M9 — Unificação validada e entregue

**Depende de:** M8.

**Trabalho.** Validação integrada, aplicação dos checklists de padronização e de arquitetura, documentação final.

**Entregas.**
- Relatório de validação, com toda divergência justificada
- Documentação do repositório unificado
- Backlog de dívida técnica que ficou
- Lista de pendências ainda abertas com a área cliente
- `projetos-origem/` arquivada **intacta** para referência

---

## Trilha paralela — pendências de negócio

**P1 — Endereçar.** Pode e deve começar **junto com M1**. Não depende de código.

Consolidar [`../04-relatorios/duvidas-pendentes.md`](../04-relatorios/duvidas-pendentes.md) e encaminhar formalmente à área cliente.

**P2 — Respostas.** Cada resposta desbloqueia um ponto específico:

| Pendência | Desbloqueia |
|---|---|
| Data de corte | Gatilho do RPA 1 e do RPA 2 — **M5, M6** |
| Borda de 1% (valor, sinal, base) | Decisão S/N — **M6** |
| Envio automático HU-15 | Fluxo do RPA 3 — **M8** |
| Escopo da HU-20 | Cisão do P6 — **M7** |
| CBS/IBS | Layout e validação — **M6** |
| `DE_EBT_..._MODELO.xlsx` | HU-17 — **M8** |
| `_ENV` vs `Base_Contestação` | HU-14 — **M8** |
| Correção automática de expectativa | HU-08 — **M6** |
| Descritores de transporte | HU-05 — **M6** |
| Posição do EC no fluxo (RPA 2 ou 3) | HU-19 — **M6/M8** |

⚠️ **A pendência mais urgente é o escopo da HU-20**, porque ela decide se M7 exige cisão do P6 ou não — e M7 vem antes de M8.

⚠️ **A mais bloqueante é a data de corte**, porque atinge dois RPAs e a regra de reprocessamento.

---

## Riscos que podem alterar este roadmap

| Risco | Impacto |
|---|---|
| Épico 5 não implementado | O RPA 3 fica incompleto; M8 vira parte migração, parte desenvolvimento |
| Ausência de ambiente de teste do AGI | **M7 e M8 não podem ser validados.** Impedimento, não atraso |
| Código implementa a V1 nas HUs 🔴 | M5, M6 e M8 viram retrabalho parcial. Redimensionar após M2 |
| Fronteira real dos projetos ≠ informada | M2 refaz o mapa; M3 em diante se ajusta |
| Regras ou tarifas fixas no código | Viola premissas da V2; gera dívida a tratar após M9 |
| Pendências de negócio sem resposta | Partes de M5–M8 ficam isoladas e incompletas |

Catálogo completo em [`../04-relatorios/riscos-conhecidos.md`](../04-relatorios/riscos-conhecidos.md).
