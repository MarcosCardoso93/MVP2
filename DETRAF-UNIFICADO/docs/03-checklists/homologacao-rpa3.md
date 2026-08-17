# Homologação — RPA 3

**Escrito em 2026-08-06.** Leia antes o
[guia de partida](homologacao-guia-de-partida.md).

O RPA 3 é o maior dos três e o único que **escreve para fora**: carrega arquivo no
AGI e envia e-mail à operadora. Os dois estão atrás de kill-switch, desligado por
padrão.

**Cobre:** HU-12 a HU-20.

---

## Pré-condições

- [ ] `python verificar_ambiente.py --rpa rpa3` sem falhas
- [ ] O RPA 2 já rodou para o mês
- [ ] **O analista já sinalizou no WebFat** o que contestar — ver abaixo
- [ ] `CAMINHO_CONTROLE_CT` aponta para a pasta de numeração CT

### A pré-condição que não é técnica

O RPA 3 lê `tipo_contestacao` de `tbl_rpa_log_detraf_despesa_contestacao` — o
sinal que **o analista grava no WebFat**, por chave
`(eot_operadora, eot_tbra, referência, tráfego, remuneração)`.

**Sem esse sinal, o robô gera os artefatos e não contesta nada.** Não é defeito: é
o ponto de decisão humana que separa o RPA 2 do RPA 3.

Para homologar sem depender do WebFat, grave o sinal direto no espelho:

```sql
UPDATE tbl_rpa_log_detraf_despesa_contestacao
   SET tipo_contestacao = 'COM retenção'
 WHERE empresa = 'CLARO' AND referencia = '202507';
```

---

## Roteiro

### 1. Só os artefatos, uma operadora

```
python rpa3_contestacao_agi_ec/main.py --operadoras CLARO --etapa artefatos \
    --referencia 202507 --dry-run
```

Em `{CAMINHO_OPERADORAS}\CLARO\2025\202507\`:

| Artefato | Onde | HU |
|---|---|---|
| `DE_AGI_D_202507_TBRA_X_CLARO_EXT.xlsx` | `AGI\` | HU-12 |
| `..._INT.xlsx` | `AGI\` | HU-13 — só o tráfego contestado **com retenção** |
| `Base Contestação_CLARO_202507_ENV.xlsx` | `Contestações\` | HU-14 |
| `CT - {n}.docx` | `Contestações\` | HU-14 |
| `CONT_PROC_MASCARA_CLARO_202507.xlsx` | `AGI\` | HU-16 |

### 2. Confira a numeração e as cartas

⚠️ **Mais de uma carta é o caso normal**, desde a decisão Q25 (2026-08-05). A
operadora com linhas COM e SEM retenção no mesmo mês recebe **uma carta por
cenário, cada uma com o seu número CT** — a carta é um documento com um texto de
cenário, e um só documento não conseguiria dizer as duas coisas.

| O que conferir | Esperado |
|---|---|
| Número CT | o maior encontrado na pasta de controle, **+1** |
| Duas cartas | números **consecutivos** |
| O `_ENV` | **continua único** — o nome dele não tem cenário, e ele é o anexo de dados da contestação inteira |
| Trava | um `.numeracao-ct.lock` aparece na pasta durante a emissão e some depois |

**Se a numeração falhar**, a carta é desabilitada **para a execução inteira** e os
demais artefatos continuam saindo. É deliberado: a numeração é global e serial, e
insistir arriscaria emitir número duplicado — o que a decisão do cliente de
2026-07-31 proíbe.

### 3. A despesa da contestação (HU-19)

Confira em `tbl_rpa_log_detraf_despesa_contestacao`:

| Coluna | Esperado |
|---|---|
| `vb_operadora`, `vb_diferenca` | **sempre negativos** (é despesa) |
| `remuneracoes` | a remuneração da linha (⚠️ **plural**, é o nome no banco) |
| `vb_contestacao` | **não confira** — a coluna não existe ainda; ver abaixo |

> 🔴 **`vb_contestacao` não existe no banco** — confirmado em 2026-08-06, lendo o
> MySQL de verdade (pendência **Q24**). É a regra do ¶942, e falta um único
> `ALTER TABLE`.
>
> **Isto não trava a homologação.** O robô grava as outras seis colunas
> normalmente e registra **um aviso por lote** no log:
>
> ```
> [HU-19 Despesa Contestação] A tabela '...' não tem a(s) coluna(s)
> vb_contestacao — NÃO gravada(s). As demais seguem normalmente.
> ```
>
> Ver esse aviso é o comportamento **esperado** hoje. O que seria defeito é ele
> aparecer por linha em vez de por lote, ou as outras seis não gravarem.

### 4. Carga no AGI

⛔ **Não faça esta etapa sem ler o
[checklist-validacao-agi.md](checklist-validacao-agi.md) e sem autorização do
GP-Vivo.** Não existe ambiente de teste do AGI (pendência **Q20**): a única forma
de exercitar é contra produção.

Com os switches desligados, a etapa monta a lista e registra o que subiria:

```
python rpa3_contestacao_agi_ec/main.py --etapa carga --referencia 202507 --dry-run
```

| O que conferir | Esperado |
|---|---|
| A lista | EXT **antes** do INT — a ordem importa para o AGI |
| Nada é aberto | log diz `[MODO SEGURO] PERMITIR_UPLOAD_AGI=false` |
| Sobra de execução anterior | arquivo anterior à execução é descartado, com aviso |

### 5. E-mail de contestação (HU-15)

```
python rpa3_contestacao_agi_ec/main.py --etapa email --referencia 202507 --dry-run
```

| O que conferir | Esperado |
|---|---|
| Assunto | `CONTESTAÇÃO_TBRA\|CLARO_202507` |
| Anexos | **todas as cartas** + o `_ENV`, com o `_ENV` por último |
| Sem contatos | recusa o envio e nomeia a pendência **Q16** |

⚠️ Para o envio acontecer de verdade são precisas **duas** coisas:
`CAMINHO_CONTATOS_OPERADORAS` apontando para um CSV `operadora;emails` **e**
`PERMITIR_ENVIO_EMAIL=true`. É o único efeito deste repositório que chega a
alguém de fora da Vivo. **Valide primeiro com um endereço interno no CSV.**

### 6. Conferência do relatório (HU-20)

```
python rpa3_contestacao_agi_ec/main.py --etapa verificacao --referencia 202507
```

Com `PERMITIR_ACESSO_AGI=false`, roda sobre um relatório **já baixado** em
`DIRETORIO_RELATORIO_AGI`. Compara a soma por operadora com o Encontro de Contas
do banco, com tolerância de `TOLERANCIA_VERIFICACAO` (0,01 — decisão nossa, N11).

Divergência aqui **não é falha de automação**: é o que a HU existe para achar.
Compare com o AGI na tela antes de tratar como defeito.

### 7. Tudo, como na agenda

```
python rpa3_contestacao_agi_ec/main.py --referencia 202507 --dry-run
```

Leia o relatório em `logs/{host}/rpa3_contestacao_agi_ec/execucoes/`.

---

## Comportamentos que parecem defeito e não são

| O que acontece | Por quê |
|---|---|
| Operadora pulada com "sem Detraf recebido" | Sem Detraf não há o que gerar. Gerar um EXT vazio faria a HU-17 tentar subi-lo |
| "_ENV e carta sem expectativa Vivo" | Sem expectativa não há a comparação lado a lado que o `_ENV` é. O EXT e o CONT_PROC continuam saindo |
| Carta desabilitada para todas | A numeração falhou. É global e serial: se falha para a primeira, falha para todas |
| Nada foi contestado | O analista não sinalizou no WebFat. É o ponto de decisão humana |
| "chave sem linha correspondente" | A linha-base é do Épico 3, fora deste projeto (B-D20) |
| Duas cartas para a mesma operadora | Cenário misto — é o comportamento correto desde a Q25 |
| Erro numa operadora e as outras seguem | Deliberado: o mês tem dezenas de operadoras, e abortar tudo faria uma pasta ausente bloquear o mês inteiro |

---

## Repetir um cenário

```
python resetar_homologacao.py --referencia 202507
```

⚠️ **A carta CT não é apagada**, de propósito: o número dela já foi consumido da
sequência global e apagar o arquivo não o devolve. Se repetir a rodada, a próxima
carta virá com o número seguinte — o que é correto, e faz a numeração avançar mais
rápido do que em produção.
