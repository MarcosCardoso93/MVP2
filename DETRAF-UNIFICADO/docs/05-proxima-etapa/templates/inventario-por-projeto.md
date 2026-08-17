# Template — Inventário por Projeto

> Copiar para `trabalho/inventarios/inventario-projeto-N.md` e preencher durante a análise.
> Procedimento: [`../roteiro-analise-tecnica.md`](../roteiro-analise-tecnica.md). Checklist: [`../../03-checklists/checklist-analise-de-codigo.md`](../../03-checklists/checklist-analise-de-codigo.md).

---

# Inventário — Projeto N: {nome}

- **Analisado em:**
- **Analisado por:**
- **Pasta:** `projetos-origem/{pasta}/`
- **HUs esperadas:**
- **RPA(s) de destino:**

---

## 1. Estrutura e execução

**Árvore (nível relevante):**
```
```

| Item | Valor |
|---|---|
| Ponto de entrada | |
| Como executa | |
| Granularidade | por arquivo / por operadora / por lote mensal |
| Paralelismo | |
| Trava de execução | |
| Acumula estado em memória entre operadoras? | ⚠️ se sim, impede processar isoladamente |

**Fluxo principal, do início ao fim:**
1.
2.
3.

**Bibliotecas relevantes:**

| Biblioteca | Para quê |
|---|---|

---

## 2. Mapeamento HU → código

| HU | Status | Arquivo | Linha | Observação |
|---|---|---|---|---|
| HU-xx | implementada / parcial / **ausente** | | | |

## 3. Mapeamento código → HU

| Módulo / função | HU | Observação |
|---|---|---|

**⚠️ Código sem HU correspondente:**

| Onde | O que faz | Classificação |
|---|---|---|
| | | escopo extra / código morto / HU não documentada / **fluxo de Receita (fora de escopo)** |

---

## 4. 🔴 Versão da regra implementada

Preencher apenas para as HUs deste projeto que constam da tabela.

| HU | V1 ou V2? | Evidência (arquivo:linha) | Consequência |
|---|---|---|---|
| HU-02 (P1) | | | V1 → retrabalho |
| HU-07 (P2) | | | V1 → caminho a eliminar |
| HU-09 (P3) | | | V1 → reescrita da camada de saída |
| HU-10 (P3) | | | |
| HU-19 (P4) | | | |

**Se o P3 grava no arquivo E no banco** — verificar no P4 de onde o `_ENV` é montado:

---

## 5. Pontos de I/O

### 5.1 E-mail (Outlook)
| Operação | Onde | Detalhe |
|---|---|---|
| Lê | | caixa, filtros |
| Move | | pastas |
| Envia | | destinatários, anexos |
| Biblioteca | | |

### 5.2 Arquivos
| Operação | Caminho | Como o caminho é construído |
|---|---|---|

⚠️ **Construção de caminhos:** inline / função dedicada / configuração →

**Convenções de nome usadas:** `_D_` ☐ `_BK` ☐ `_ERRO` ☐ `_ENV` ☐ `_EXT` ☐ `_INT` ☐ `CT` ☐

### 5.3 Banco de dados
| Tabela | Lê/Escreve | Campos | Onde |
|---|---|---|---|

⚠️ **Campos não documentados na V2 encontrados:**
**Usa transação?** **Como trata falha no meio da escrita?**

### 5.4 AGI
| Tela | Operação | Onde | Como confirma sucesso |
|---|---|---|---|

**Biblioteca de automação de UI:** **Tratamento do login:**

### 5.5 Anexo 5
**Origem:** arquivo local / download / banco →
**Como é atualizado:** **Colunas consultadas:**

---

## 6. Regras de negócio implementadas

| Regra | Implementada? | Onde | Confere com a V2? | Observação |
|---|---|---|---|---|
| Layout das 15 colunas | | | | por posição ou por cabeçalho? |
| Aceita arquivo sem cabeçalho | | | | |
| Ignora aba de resumo | | | | |
| Exclui `Rel = 1` | | | | |
| Tolera `Rel` vazia | | | | |
| Regras de descritor | | | | |
| Regra do `_BK` | | | | **recalcula o total?** |
| Regra geral do `_ERRO` | | | | |
| Consulta de tarifa | | | | quais campos na chave |
| **Dupla convivência em fevereiro** | | | | usa mês do tráfego? |
| Horário reduzido VU-M (Devedora) | | | | |
| Rejeita tarifa zero | | | | |
| **Regra da variação** | | | | ver 6.1 |
| Expectativa ausente → zerada | | | | |
| Exceção Bill&Keep | | | | |
| Sumarização STFC em uma linha | | | | |
| Campos fixos `_EXT`/`_INT` | | | | |
| Colunas do `CONT_PROC` | | | | coluna W: valor ou minutagem? |
| Numeração CT | | | | **há trava?** |
| Fator `0,9635` | | | | |

### 6.1 🔴 Regra da variação — registrar literalmente

| Aspecto | O que o código faz |
|---|---|
| Limiar | `> 1%` / `>= 1%` / outro |
| Considera sinal | sim / não |
| Base do percentual | operadora / expectativa |
| Divisão por zero | |
| Trecho do código | |

---

## 7. 🔴 Aderência às premissas 10.3 / 10.4 da V2

| Item | Constante no código? | Onde |
|---|---|---|
| Valores de tarifa | | |
| Mapeamento descritor → remuneração | | |
| Limiares (1%, `0,9635`) | | |
| **Índices de coluna fixos** | | |
| EOTs da Vivo (011, 200, 9\*\*) | | |
| Caminhos de rede | | |

**Total de violações:** → dívida técnica a registrar, **não corrigir durante a migração**

---

## 8. Tratamento de erro e logging

| Aspecto | Como é hoje |
|---|---|
| Captura de exceção | |
| "Segue para o próximo processamento" implementado? | |
| Estado persistido para retomada | |
| O que registra em log | |
| Formato e destino do log | |
| Como o erro chega ao WebFat | |
| Distingue erro da operadora × de expectativa? | |
| Há "correção automática" de expectativa? | ⚠️ regra não documentada |

---

## 9. Configuração e segredos

| Item | Onde | Observação |
|---|---|---|
| Mecanismo de configuração | | |
| Caminhos de rede | | |
| String de conexão | | |
| Credenciais | | |
| 🔴 **Credencial commitada** | sim / não | se sim: **ESCALADO EM {data}** |

---

## 10. Testes e testabilidade

| Item | Situação |
|---|---|
| Testes automatizados | quantos, que tipo |
| Rodam? | |
| Massa de dados | |
| Executável sem produção? | |
| Regras testáveis isoladamente? | |

---

## 11. Candidatos a componente compartilhado

| # | Candidato | Onde (arquivo:linha) | Ficha |
|---|---|---|---|

---

## 12. Duplicações identificadas

(a partir do segundo projeto)

| # | Responsabilidade | Este projeto | Comparado com | Veredicto | Registro |
|---|---|---|---|---|---|

---

## 13. Achados

### 🔴 Críticos (escalar imediatamente)
| Achado | Escalado para | Data |
|---|---|---|

### 🟡 Relevantes
### 🟢 Observações

---

## 14. Dúvidas novas

| # | Dúvida | Destinatário | Bloqueia |
|---|---|---|---|

→ Acrescentar a [`../../04-relatorios/duvidas-pendentes.md`](../../04-relatorios/duvidas-pendentes.md)

---

## 15. Conclusão

**Escopo real × esperado:**

**Aderência à V2:**

**Complexidade de migração:** baixa / média / alta — porque:

**Pontos de atenção para a migração:**

---

## Checklist de fechamento

- [ ] Toda HU esperada rastreada ou marcada como ausente
- [ ] Todo código atribuído a uma HU ou classificado
- [ ] Versão da regra registrada para as HUs 🔴 deste projeto
- [ ] Pontos de I/O mapeados
- [ ] Regras de negócio conferidas contra a V2
- [ ] Aderência às premissas verificada
- [ ] Candidatos com arquivo e linha
- [ ] Duplicações com veredicto
- [ ] Achados críticos escalados
- [ ] Matriz de rastreabilidade atualizada
