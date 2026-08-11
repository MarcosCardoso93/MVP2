# Dependências Funcionais

> ⚠️ **Fotografia da etapa documental (2026-07-30).** Este documento foi escrito
> **antes** de qualquer código chegar, e descreve o entendimento daquele momento.
> Vários pontos já mudaram — em especial: o Épico 5 **tem** projeto (o P7, entregue
> em 2026-08-04), e as HUs 12 a 19 estão implementadas e orquestradas.
>
> **Fonte do estado atual:** `docs/04-relatorios/duvidas-pendentes.md` (pendências),
> `matriz-de-rastreabilidade.md` (HUs) e `unificado/README.md` (código).

Cadeia de dependências entre histórias, pontos de sincronização e o que cada projeto de origem precisa de outro.

---

## 1. A cadeia principal

```
┌─ RPA 1 ─────────────────────────────────────────────┐
│  HU-01 varre inbox                                  │
│     └─► HU-02 identifica operadora (lê o anexo!)    │
│            └─► HU-03 salva em rede + WebFat         │
└──────────────────────┬──────────────────────────────┘
                       │
              ⏸ ESPERA: data de corte  ⚠️ indefinida
                       │
┌─ RPA 2 ──────────────▼──────────────────────────────┐
│  HU-04 valida layout ──┬─► HU-06 gera _BK           │
│                        ├─► (HU-07 absorvida)        │
│                        └─► gera _ERRO               │
│  HU-05 valida tarifa ──┘                            │
│            └─► HU-08 registra em ..._arquivos       │
│                   └─► HU-09 consolida em banco      │
│                          └─► HU-10 sumariza e       │
│                              aplica regra de 1%     │
│                                 └─► HU-11 expõe     │
│                                     ao analista     │
└──────────────────────┬──────────────────────────────┘
                       │
              ⏸ ESPERA: decisão do analista (contestar? reter?)
                       │
┌─ RPA 3 ──────────────▼──────────────────────────────┐
│  HU-12 gera _EXT  (todos os cenários)               │
│  HU-13 gera _INT  (só COM retenção)                 │
│  HU-14 gera _ENV + carta CT                         │
│            └─► HU-15 envia e-mail  ⚠️ IRREVERSÍVEL   │
│  HU-16 gera CONT_PROC → atualiza tipo_contestacao   │
│            └─► HU-17 sobe _EXT/_INT no AGI          │
│                   └─► HU-18 sobe CONT_PROC          │
│                          → atualiza carga_agi       │
│                             └─► HU-19 alimenta EC   │
│                                    └─► HU-20 confere│
└──────────────────────┬──────────────────────────────┘
                       │
              ⏸ ESPERA: mês seguinte, se houver recuperação
                       │
┌─ RPA 4 ──────────────▼──────────────────────────────┐
│  HU-21 identifica recuperação e retifica no AGI     │
└─────────────────────────────────────────────────────┘
```

---

## 2. Os três pontos de sincronização

São eles que justificam a existência de quatro RPAs em vez de um.

### 2.1 Data de corte — entre RPA 1 e RPA 2

**Natureza:** temporal. O RPA 2 não pode processar antes de ter razoável certeza de que todos os arquivos do mês chegaram.

**Por que existe.** A V2: *"Naturalmente o robô poderá receber diversos e-mails da mesma operadora, por conta disso é importante definirmos a data de corte para leitura de e-mails para termos tempo para receber arquivos corretos das operadoras."*

⚠️ **Não definida.** "Data de corte do processo está em análise pela área cliente para termos a regra de reprocessamento e gatilho para batimento da operadora."

**O que fica bloqueado:** critério de periodicidade da HU-01; gatilho do RPA 2; regra de deduplicação de reenvios; regra de reprocessamento quando a operadora reenvia um arquivo depois do corte.

### 2.2 Decisão do analista — entre RPA 2 e RPA 3

**Natureza:** humana. O RPA 3 só existe depois que uma pessoa decidiu (a) quais linhas contestar e (b) com ou sem retenção.

**Onde está registrado.** HU-11: *"RPA só prossegue após sinalização explícita do analista"*. V2: *"a escolha se a contestação será retida ou não dependerá do usuário, após sua análise"*.

⚠️ **O mecanismo de sinalização não está especificado.** O RPA 3 faz polling numa coluna do banco? Existe uma fila? Um agendamento que verifica periodicamente? Isso depende da análise do código e da implementação do WebFat.

### 2.3 Recuperação de tráfego — entre RPA 3 e RPA 4

**Natureza:** condição de negócio assíncrona, com defasagem de pelo menos um mês.

⚠️ **Assimetria detecção/execução.** A **detecção** está descrita no Épico 4, dentro do fluxo do RPA 3 (*"Neste momento também, ele identifica se ele precisa fazer alguma retificação de contestação"*). A **execução** é o RPA 4. Como a informação passa de um para o outro não está definido.

---

## 3. Dependências de dados entre histórias

| Consumidora | Precisa de | Produzida por | Via |
|---|---|---|---|
| HU-02 | conteúdo do anexo (coluna Credora) | HU-01 | arquivo baixado |
| HU-03 | nome fantasia da operadora | HU-02 | Anexo 5 |
| HU-04 | arquivos em "Detrafs Recebidos" e convertidos | HU-03 + ICT (externo) | rede / servidor WebFat |
| HU-05 | descritor e EOTs da linha | HU-04 | leitura do arquivo |
| HU-06 | tipo de serviço e concessão das EOTs | Anexo 5 | consulta |
| HU-08 | resultado da validação | HU-04, HU-05 | memória do processo |
| HU-09 | dados validados de ambas as origens | HU-04, HU-08 | `..._arquivos` |
| HU-10 | base consolidada | HU-09 | `..._contestacao` |
| HU-11 | flags S/N por combinação | HU-10 | `..._contestacao` |
| HU-12 | Detraf consolidado da operadora + decisão | HU-09, HU-11 | banco |
| HU-13 | expectativa Vivo do tráfego contestado com retenção | HU-09, HU-11 | banco |
| HU-14 | base de contestação filtrada + numeração CT | HU-09, HU-11, **rede** | banco + contador em pasta |
| HU-15 | `_ENV` + carta + contatos da operadora | HU-14 + cadastro de contatos | arquivos + WebFat |
| HU-16 | totais por remuneração e mês + modalidade | HU-10, HU-11 + `CONT_PROC_MASCARA` | banco + planilha-modelo |
| HU-17 | `_EXT`, `_INT` | HU-12, HU-13 | pasta AGI |
| HU-18 | `CONT_PROC` | HU-16 | pasta |
| HU-19 | totais da operadora e diferenças | HU-09, HU-10 | banco |
| HU-20 | valores do EC + relatório do AGI | HU-19, HU-18 | banco + AGI |
| HU-21 | contestação do mês anterior + variação negativa | HU-16/HU-18 (mês N−1), HU-10 (mês N) | AGI + banco |

---

## 4. Dependências externas (fora do controle da automação)

| Dependência | Quem produz | Consumido por | Risco |
|---|---|---|---|
| **Arquivos de expectativa do ICT** | ICT (outra frente) | HU-04, HU-09, HU-13 | Se não chegam, a V2 manda processar com expectativa **zerada** — a contestação fica sem contraparte |
| **Anexo 5 (ABR Telecom)** | ABR Telecom | HU-02, HU-04, HU-05, HU-06, HU-10, HU-21 | Fonte externa, atualizada fora do ciclo; nomes de operadora mudam (pendência da HU-21) |
| **Tela do WebFat (aba Contestação)** | ⚠️ frente indefinida | HU-11 → gatilho do RPA 3 | Se for outra frente, é dependência de projeto |
| **Modelos de carta por operadora** | manual, em pasta de rede | HU-14 | Operadora nova sem modelo → falha não tratada |
| **`CONT_PROC_MASCARA Geral {aaaamm}`** | manual/externo | HU-10, HU-16 | Nome contém ano-mês; atualização não documentada |
| **Arquivos-modelo `_EXT`/`_INT` na pasta AGI** | pré-posicionados | HU-12, HU-13 | A V2 diz que o robô "abre" o arquivo, como se já existisse |
| **Contador de numeração CT** | compartilhado com humanos | HU-14 | Estado em pasta de rede, sem trava |
| **`DE_EBT_TBRA_TLF_202509_C_INT_MODELO.xlsx`** | ⚠️ desconhecido | HU-17 | Papel não explicado na V2 |
| **Tabela de contatos das operadoras** | WebFat | HU-15 (e HU-04, para crítica) | A V2 deixou de citá-la ao mudar a HU-02; existência a confirmar |
| **Autenticador de rede Vivo** | infraestrutura Vivo | HU-17, HU-18, HU-20, HU-21 | Sem ele, nenhuma automação do AGI funciona |
| **Demandas irmãs ATA0000571/567/572** | outras frentes | fluxo completo de faturamento | Interface não descrita |

---

## 5. Dependências entre os projetos de origem

Reformulação do mesmo grafo, na unidade que importa para a unificação.

```
P1 ──(arquivos em rede + WebFat)──► P2
P2 ──(tbl_..._arquivos)──────────► P3
P3 ──(tbl_..._contestacao + decisão do analista)──► P4
P4 ──(_ENV + carta)──────────────► P5
P4 ──(_EXT/_INT/CONT_PROC)───────► P7? (Épico 5)
P7? ─(carga_agi)─────────────────► P4 (HU-19)
P4 ──(EC no banco)───────────────► P6 (HU-20)
P4/P7 ─(contestação do mês N−1)──► P6 (HU-21), no mês N+1
```

**Leituras importantes:**

- **P4 é o hub.** Alimenta P5, P7 e P6, e é alimentado de volta por P7 (`carga_agi` antes da HU-19). Se o Épico 5 estiver mesmo dentro do P4, esse ciclo desaparece — é mais um indício a favor da hipótese 1.
- **P5 depende inteiramente do P4.** Uma única HU que consome artefatos produzidos por outro projeto. É improvável que o P5 seja autossuficiente; espere encontrar código duplicado ou uma dependência implícita de caminho de arquivo.
- **P6 tem duas dependências de naturezas diferentes.** HU-20 depende do ciclo corrente (síncrona); HU-21 depende do ciclo anterior (defasada em um mês). Mais um argumento para a cisão.
- **Nenhum projeto depende do P6.** É folha do grafo nas duas pontas — o que o torna o mais seguro de mexer por último.

---

## 6. Acoplamentos que a unificação precisa observar

⚠️ Todos os itens abaixo são hipóteses derivadas da documentação. A confirmação depende da análise do código.

### 6.1 Acoplamento por caminho de arquivo

Os projetos se comunicam por **convenção de caminho e nome de arquivo** na rede Lagoa, não por interface. Isso significa que a estrutura de pastas e as convenções de sufixo (`_D_`, `_BK`, `_ERRO`, `_ENV`, `_EXT`, `_INT`) são, na prática, **o contrato entre os RPAs**. Se cada projeto de origem construir esses caminhos por conta própria, há duplicação garantida — e qualquer divergência entre eles é um bug latente.

### 6.2 Acoplamento por tabela

`tbl_rpa_log_detraf_despesa_contestacao` é escrita por **quatro** responsabilidades diferentes: HU-09/HU-10 (RPA 2, popula), HU-16 (`tipo_contestacao`), HU-18 (`carga_agi`), HU-19 (campos do EC). Ou seja, a mesma linha é atualizada por RPAs distintos em momentos distintos. Sem controle de concorrência ou de estado, isso é fonte de inconsistência.

### 6.3 Acoplamento por estado externo não transacional

- Numeração CT em pasta de rede (HU-14)
- Pasta "Detraf Despesas" do Outlook, que marca o que já foi processado (HU-01)
- Presença ou ausência do arquivo `_INT`, que **é** o sinal de que houve retenção (HU-17)

Esse último é notável: o RPA que faz a carga descobre o cenário pela **existência do arquivo**, não por consulta ao banco.

### 6.4 Passos irreversíveis

| Passo | Por que importa |
|---|---|
| HU-15 — envio do e-mail à operadora | Externo; não se desfaz. Reprocessar o RPA 3 do início reenviaria a contestação |
| HU-14 — consumo da numeração CT | Incrementa um contador compartilhado; reprocessar queima números |
| HU-17/HU-18 — carga no AGI | Reprocessar pode duplicar lançamentos financeiros |
| HU-21 — evento "Recuperação" | Idem |

Isso sustenta a observação do relatório de separação sobre isolar a carga no AGI para permitir reprocessamento sem repetir o envio da carta. ⚠️ Onde colocar os pontos de retomada é decisão que depende da análise do código.
