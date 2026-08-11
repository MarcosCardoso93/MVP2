# RPA 3 — fluxo de execução

**Contestação, carga no AGI e Encontro de Contas · HU-12 a HU-20**

---

## O que este robô faz

**Gatilho:** a sinalização do analista no WebFat — o campo `tipo_contestacao`
de `tbl_rpa_log_detraf_despesa_contestacao`, preenchido depois que o RPA 2
apurou.

⚠️ **Sem esse sinal, o robô gera os artefatos e não contesta nada.** Não é
defeito: é o ponto de decisão humana que separa este robô do RPA 2.

**Entrega:** os arquivos carregados no AGI, o e-mail de contestação enviado à
operadora, e o Encontro de Contas conferido.

```
 👤 analista sinaliza no WebFat
         │
         ▼
 ┌──────────────────┐   por operadora: EXT, INT, _EXP, cartas, CONT_PROC
 │ 1. ARTEFATOS     │   + despesa da contestação no banco (HU-19)
 │    HU-12 a HU-16 │
 └────────┬─────────┘
          │
          ▼
 ┌──────────────────┐   Detraf > Importar Dados  (EXT, INT)
 │ 2. CARGA         │   Contestação > Gerenciar  (CONT_PROC)
 │    HU-17, HU-18  │   + carga_agi atualizado
 └────────┬─────────┘
          │
          ▼
 ┌──────────────────┐   e-mail com as cartas + o _EXP
 │ 3. EMAIL  HU-15  │
 └────────┬─────────┘
          │
          ▼
 ┌──────────────────┐   relatório do AGI × Encontro de Contas
 │ 4. VERIFICACAO   │   + .xlsx de inconsistências
 │    HU-20         │
 └──────────────────┘
```

**Por que esta ordem:** ela vem da V2. A carga fica **fora do laço** por
operadora porque os uploaders recebem a lista e abrem o AGI **uma vez só** —
abrir e logar custa minutos. E a verificação vem por último porque é ela que
confere *o que foi carregado* (¶690).

---

## A regra geral: pular com aviso, não abortar

O mês tem dezenas de operadoras. Abortar tudo faria uma pasta ausente bloquear o
mês inteiro; seguir cego produziria artefato errado. Então: **falta de insumo e
pendência conhecida viram aviso nomeado e seguem**, e erro inesperado numa
operadora não impede a seguinte.

**Duas exceções abortam a etapa para a execução inteira:**

1. **Numeração CT indeterminada.** Ela é global e serial: se falha para a
   primeira operadora, falha para todas, e insistir arriscaria **duplicar
   número** — o que a decisão do cliente de 2026-07-31 proíbe. A carta é
   desabilitada e os demais artefatos continuam saindo;
2. **Falha ao montar o índice de remuneração.** É pré-condição de tudo; aborta
   antes de o laço começar.

---

# Etapa 1 — `artefatos` (HU-12 a HU-16, e HU-19)

Por operadora, na ordem da V2 — `GeracaoAgiController._gerar_para_operadora`.

### 1.1 Consolidar os dois lados

**Onde:** `services/consolidacao_contestacao.py`

- `consolidar_detrafs_operadora` — o Detraf recebido;
- `consolidar_expectativa_vivo` — a expectativa;
- `montar_contest` — o comparativo linha a linha.

**Sem Detraf:** a operadora é **pulada inteira**. Importa o short-circuit:
`gerar_arquivo_ext` não tem guarda de vazio e gravaria um `.xlsx` vazio, que a
HU-17 tentaria subir no AGI.

**Sem expectativa:** o EXT ainda sai (ele só depende do lado da operadora), mas o
INT e o `_EXP` ficam vazios — a comparação sai com o lado da Vivo zerado, e o
robô avisa.

### 1.2 Gravar a despesa da contestação (HU-19)

**Onde:** `services/encontro_contas.py` → `atualizar_despesa_contestacao`

**Por que vem antes dos artefatos:** é um `UPDATE` idempotente, e garante o
panorama no WebFat **mesmo se a geração falhar adiante**.

Grava os seis campos que a V2 nomeia, mais o `vb_contestacao` — o valor bruto da
diferença **só nas linhas COM retenção** (regra do ¶942, decisão Q24).

`vb_operadora` e `vb_diferenca` são gravados **sempre negativos** (é despesa).

### 1.3 EXT (HU-12)

**Onde:** `services/geracao_ext.py`
**Sai:** `AGI/DE_AGI_D_{aaaamm}_TBRA_X_{OP}_EXT.xlsx`

O tráfego da operadora, **todos os cenários**. A coluna de expectativa marca `S`
nas linhas contestadas com retenção.

### 1.4 INT (HU-13)

**Onde:** `services/geracao_int.py`
**Sai:** `AGI/..._INT.xlsx`

A expectativa da Vivo, **apenas para o tráfego contestado COM retenção**.

### 1.5 `_EXP` e as cartas (HU-14)

**Onde:** `services/geracao_env_carta.py`
**Sai:** `Contestações/Base Contestação_{OP}_{aaaamm}_EXP.xlsx` e uma ou mais
`Contestações/CT - {n}.docx`

⚠️ A V2 (¶599) cita o sufixo como `_ENV`; o código usa `_EXP` desde esta troca —
ver a nota em `nomenclatura.nome_env`.

⚠️ **Mais de uma carta é o caso normal** desde a decisão Q25. O sinal do analista
é por chave, então a mesma operadora pode ter linhas COM e SEM retenção no mesmo
mês — e a carta é um documento com **um** texto de cenário. Sai **uma carta por
cenário, cada uma com o seu número CT**.

O `_EXP` **continua único**: o nome dele não tem cenário, e ele é o anexo de
dados da contestação inteira.

**A numeração CT** sai do maior número na pasta de controle, +1. Como a mesma
execução consome dois números seguidos, a leitura e a gravação acontecem dentro
de uma **trava por arquivo** (`.numeracao-ct.lock`, decisão Q18) — dois processos
entre os dois passos emitiriam o mesmo número.

### 1.6 CONT_PROC (HU-16)

**Onde:** `services/geracao_cont_proc.py`
**Sai:** `AGI/CONT_PROC_MASCARA_{OP}_{aaaamm}.xlsx`

O consolidado da contestação para o AGI. Só as linhas **efetivamente
contestadas**: `contestacao_a_enviar == "S"` **e** sinal do analista presente.

⚠️ `DURACAO` **e** `VLR_BRUTO` recebem a **minutagem**, negativa — o ¶643 diz
isso literalmente, e o PO confirmou em 2026-08-06 (pendência Q11).

Ao final, regrava `tipo_contestacao` nas linhas contestadas — o eco do sinal
aplicado (HU-16, ¶ da V2 pág. 34).

---

# Etapa 2 — `carga` (HU-17 e HU-18)

**Onde:** `services/upload_detraf_agi.py` e `upload_contestacao_agi.py`

Fora do laço: os uploaders recebem a **lista** de operadoras e abrem o AGI uma
vez só.

1. **`Detraf > Importar Dados`** — EXT e INT, um de cada vez (HU-17);
2. **`Contestação > Gerenciar`** — CONT_PROC → Salvar (HU-18);
3. grava `carga_agi` = `carregado` / `erro na carga`.

**Atrás de `PERMITIR_UPLOAD_AGI`**, desligado por padrão: com ele desligado, a
lista é montada e registrada, e nada é tocado.

Arquivo anterior ao início da execução é **descartado com aviso** — sobra de
rodada anterior não sobe.

⚠️ A automação é por **reconhecimento de imagem**. Antes da primeira execução
numa VM nova, rode `python verificar_imagens_agi.py` — ele confere as imagens
contra a tela **sem clicar em nada**.

---

# Etapa 3 — `email` (HU-15)

**Onde:** `services/envio_email_contestacao.py`

- **Assunto:** `CONTESTAÇÃO_TBRA|{operadora}_{mês}`
- **Anexos:** **todas as cartas** + o `_EXP`, com o `_EXP` por último
- **Destinatários:** do CSV `operadora;para;cc` em
  `CAMINHO_CONTATOS_OPERADORAS`, com uma linha `*` de **cópia fixa**

Duas garantias: a cópia fixa **nunca vai para o `Para`** (a operadora não pode
ver um endereço interno da Vivo entre os destinatários diretos), e **sem ninguém
em `Para` o envio é recusado** — mandar só para a cópia interna pareceria
enviado.

⚠️ **É o único efeito deste repositório que chega a alguém de fora da Vivo.**
Depende de **duas** coisas ao mesmo tempo: o arquivo de contatos preenchido **e**
`PERMITIR_ENVIO_EMAIL=true`.

---

# Etapa 4 — `verificacao` (HU-20)

**Onde:** `services/verificacao_relatorio.py`

1. baixa o relatório *Detraf > Receitas e Despesas* do AGI (atrás de
   `PERMITIR_ACESSO_AGI`; desligado, usa um relatório já baixado);
2. soma por operadora — valor bruto **e** CBS, IBS Estadual e IBS Municipal;
3. compara com o subtotal de despesa do Encontro de Contas, **do banco**,
   com tolerância de `TOLERANCIA_VERIFICACAO` (0,01);
4. grava o `.xlsx` de inconsistências, **só quando há divergência**.

**Operadora sem EC conta como divergente**, não como zero — é exatamente o que
esta HU existe para pegar.

⚠️ **Os impostos são somados e registrados, mas não comparados**: a tabela do EC
não tem coluna de imposto. A V2 (¶367) os trata como informativos até 2027. As
somas vão para o log **todo mês**, para a série existir quando o recolhimento
começar.

**Falha aqui não derruba a execução:** os artefatos já foram gerados e
carregados, e esta é uma conferência posterior.

---

## Rodando cada etapa

```bash
python main.py                                          # as quatro, como na agenda
python main.py --operadoras CLARO --etapa artefatos --dry-run
python main.py --etapa carga --referencia 202507        # repete só a carga
python main.py --etapa email --dry-run
python main.py --etapa verificacao
```

**Por que a divisão funciona:** as três últimas etapas leem **o disco e o
banco**, não o resultado da primeira. Repetir a carga com os arquivos que já
estão em disco é legítimo — e é por isso que `--etapa carga` não filtra a lista
por "gerou algo agora".

### Parar entre as etapas para conferir

```bash
python main.py --pausar --dry-run
```

Ao fim de cada etapa abre uma caixa com o que ela produziu, e a execução só
segue no **Continuar**. Há também **Cancelar** (aborta, com código de saída 2) e
**Abrir pasta**.

🔴 Só funciona com `ENV=dev`, em sessão gráfica, e **nunca** em produção — a
caixa espera indefinidamente, e num robô desassistido isso travaria o processo.
Ver [`../../docs/03-checklists/homologacao-guia-de-partida.md`](../../docs/03-checklists/homologacao-guia-de-partida.md).


---

## O que parece defeito e não é

| O que acontece | Por quê |
|---|---|
| Nada foi contestado | O analista não sinalizou no WebFat. É o ponto de decisão humana |
| Operadora pulada, "sem Detraf recebido" | Sem Detraf não há o que gerar (1.1) |
| "_EXP e carta sem expectativa Vivo" | Sem expectativa não há a comparação lado a lado que o `_EXP` é |
| Carta desabilitada para **todas** | A numeração falhou. É global e serial: falhou para uma, falha para todas |
| **Duas** cartas para a mesma operadora | Cenário misto — comportamento correto desde a Q25 |
| "chave sem linha correspondente" | A linha-base é do Épico 3, fora deste projeto (B-D20) |
| Erro numa operadora e as outras seguem | Deliberado — ver "pular com aviso" acima |
| HU-20 não executada | `PERMITIR_ACESSO_AGI` desligado e nenhum relatório já baixado |

---

## Ver também

- [`../../docs/03-checklists/homologacao-rpa3.md`](../../docs/03-checklists/homologacao-rpa3.md) — roteiro de homologação
- [`../../docs/03-checklists/checklist-validacao-agi.md`](../../docs/03-checklists/checklist-validacao-agi.md) — a validação contra produção
- [`../rpa2_validacao_apuracao/FLUXO.md`](../rpa2_validacao_apuracao/FLUXO.md) — o que acontece antes
