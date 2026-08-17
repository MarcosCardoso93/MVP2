# Projeto 3 — Épico 3: Batimento Detraf × Expectativa

**Insira aqui o código do Projeto 3, sem alterações.**

---

## Escopo

| Campo | Valor |
|---|---|
| Épico | 3 — Batimento Detraf × Expectativa |
| HUs | HU-09, HU-10, HU-11 |
| RPA de destino | **RPA 2 — Validação e Apuração de Contestação** |
| Transformação | **Convergência** — junta-se ao P2 no RPA 2 |
| Ordem de análise | **3º** |

## Responsabilidades

1. Consolidar dados da operadora e da expectativa Vivo, sem linhas de total (`Rel = 1`)
2. Sumarizar `Minutos` e `R$_Bruto` por EOT devedora × tipo de tarifação × mês de tráfego
3. Aplicar a regra de variação e marcar `S` (contestar) / `N` (não contestar)
4. Popular `tbl_rpa_log_detraf_despesa_contestacao`
5. Expor os casos na aba Contestação do WebFat para decisão do analista

**Entrega:** tabelas atualizadas, aguardando decisão humana. Este projeto termina no **ponto de sincronização** que separa o RPA 2 do RPA 3.

---

## 🔴 Verificação prioritária 1 — HU-09: arquivo ou banco?

**A mudança mais estrutural da V2.** A `Base_Contestação` deixou de ser planilha:

> *"Não é necessário gerar o arquivo, mas usar a lógica e popular a tabela `tbl_rpa_log_detraf_despesa_contestacao`"*

| Encontrado | Significado |
|---|---|
| Gera o **arquivo** com abas e tabelas dinâmicas | V1 — a migração para banco é **reescrita da camada de saída**, não refatoração |
| Popula o **banco** | V2 — correto |
| **Ambos** | ⚠️ ver abaixo |

**Se gerar os dois:** verifique, ao analisar o P4, se o `_ENV` é montado a partir do **arquivo** ou do **banco**. Isso responde à pergunta **Q4** — qual é uma das "duas exceções" da frase *"todas as planilhas foram substituídas por banco, exceto dois arquivos"*.

⚠️ A lógica de negócio (o que somar, por qual chave, o que excluir) é o que se preserva. O destino é o que muda.

---

## 🔴 Verificação prioritária 2 — a regra da variação

**Registre literalmente o que o código faz.** A documentação é ambígua em três aspectos (Q2):

| Aspecto | O que verificar |
|---|---|
| **Limiar** | `> 1%` ou `>= 1%`? As fontes divergem |
| **Sinal** | Contesta só quando a operadora cobrou **a mais**, ou em qualquer direção? |
| **Base** | O percentual é sobre o valor da operadora ou sobre a expectativa? |

Esta é a regra que decide o desfecho financeiro de cada caso. **Não interprete — registre e encaminhe ao PO.**

⚠️ Por estar em pendência aberta, este componente **não pode ir para a base comum** (critério C3).

---

## Pontos de atenção

- **Expectativa ausente → valores zerados.** A V2 manda processar mesmo assim, com os dados da operadora. Isso significa variação de 100% e contestação automática. Está implementado?
- **Sumarização STFC numa única linha** (EOTs 011, 200, 9\*\*), contra uma linha por EOT no SMP.
- **Exceção Bill&Keep:** exige que **ambas** as EOTs sejam SMP.
- **Como o RPA espera a decisão do analista (Q19)?** Polling? Coluna de estado? Isso define o mecanismo de sincronização com o RPA 3.
- **Grupo Horário na visualização** era "desejável" na V2 — está implementado?
- **CBS/IBS entram na sumarização (Q6)?** Sem regra definida.

## Candidatos a componente compartilhado esperados aqui

Leitura de arquivo Detraf · mapeamento descritor → remuneração · consulta ao Anexo 5 · acesso ao banco · escrita em `tbl_..._contestacao` (⚠️ possível FALSO PAR — cinco responsabilidades escrevem nessa tabela).

⚠️ **Confronte tudo com o P2.** É a fronteira de maior probabilidade de duplicação.

---

## Procedimento

1. [`../../docs/03-checklists/checklist-insercao-dos-codigos.md`](../../docs/03-checklists/checklist-insercao-dos-codigos.md)
2. [`../../docs/05-proxima-etapa/roteiro-analise-tecnica.md`](../../docs/05-proxima-etapa/roteiro-analise-tecnica.md)
3. [`../../docs/03-checklists/checklist-duplicacoes.md`](../../docs/03-checklists/checklist-duplicacoes.md) — confronto com o P2

**Saídas:** `trabalho/inventarios/recebimento-projeto-3.md` e `inventario-projeto-3.md`
