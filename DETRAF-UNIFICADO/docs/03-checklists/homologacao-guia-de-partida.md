# Homologação — guia de partida

**DETRAF MVP2 · GSA ATA0000574 · escrito em 2026-08-06**

Este é o primeiro documento a ler. Ele diz **em que ordem** fazer as coisas, o
que cada modo significa, e o que fazer quando algo falha.

> Escrito para uma máquina **sem acesso a IA**, com homologação conduzida à mão.
> Tudo o que o robô sabe está na tela, no log ou num relatório — nada depende de
> perguntar a alguém.

---

## Os oito comandos que existem

| Comando | Para quê |
|---|---|
| `python preparar_ambiente.py` | Cria a árvore de pastas a partir do `.env`. **O primeiro de todos.** |
| `python verificar_ambiente.py` | Confere tudo antes de rodar. **Comece por aqui depois de preparar.** |
| `python verificar_imagens_agi.py` | Confere se as imagens do AGI batem com esta tela. Não clica em nada |
| `python espelhar_banco.py` | Copia o banco real para um SQLite local, e grava o DDL |
| `python preparar_banco_dev.py` | Alternativa sem acesso ao MySQL: usa os bancos de 2025 |
| `python rpa1_captura/main.py` | RPA 1 — captura, identificação, salvamento |
| `python rpa2_validacao_apuracao/main.py` | RPA 2 — validação e batimento |
| `python rpa3_contestacao_agi_ec/main.py` | RPA 3 — contestação, AGI e conferência |
| `python resetar_homologacao.py --referencia AAAAMM` | Desfaz uma rodada, para repetir |

**Todos aceitam `--help`**, e o `--help` de cada robô é a documentação de
invocação dele. Os três robôs rodam **independentemente** e podem ser agendados
separadamente.

### O fluxo de cada robô, passo a passo

Antes de rodar, vale ler o `FLUXO.md` do robô em questão — ele traz as etapas
sequenciais, o que cada passo produz e como ele falha:

| Robô | Etapas (`--etapa`) | Documento |
|---|---|---|
| RPA 1 | `captura` · `processamento` | [`unificado/rpa1_captura/FLUXO.md`](../../unificado/rpa1_captura/FLUXO.md) |
| RPA 2 | `validacao` · `batimento` | [`unificado/rpa2_validacao_apuracao/FLUXO.md`](../../unificado/rpa2_validacao_apuracao/FLUXO.md) |
| RPA 3 | `artefatos` · `carga` · `email` · `verificacao` | [`unificado/rpa3_contestacao_agi_ec/FLUXO.md`](../../unificado/rpa3_contestacao_agi_ec/FLUXO.md) |

---

## A ordem

### 1. Prepare o banco

Com acesso ao MySQL — **preferível**, porque valida o schema real:

```
python espelhar_banco.py
```

Ele copia as cinco tabelas para `banco_de_dados/TABELAS_DETRAF_espelho.db` e
grava `banco_de_dados/schema-real-AAAAMMDD.sql`.

> 📌 **Guarde o `schema-real-*.sql`.** O DDL nunca foi publicado pela
> especificação, e este arquivo é o registro dele.

Se ele acusar **colunas faltando**, pare e leia. As colunas `remuneracao` e
`vb_contestacao` foram acrescentadas pela unificação e **confirmadas presentes no
banco real em 2026-08-06** — se faltarem num ambiente, é ambiente desatualizado, e
o efeito é grande: sem a primeira o RPA 3 morre na primeira operadora
(`KeyError`), sem a segunda a despesa não é escrita para operadora nenhuma.

Sem acesso ao MySQL:

```
python preparar_banco_dev.py
```

⚠️ Este usa os SQLite de 2025 que vieram nos projetos de origem. Ele **adapta** o
`tbl_detraf_mapeamento_descritores`, que lá tem três colunas em caixa alta. O
banco real tem **as cinco em caixa baixa** que o código espera (confirmado em
2026-08-06) — a adaptação existe só porque os SQLite de origem estão defasados.

### 2. Aponte o `.env`

> 📌 O que precisa ser provisionado — credenciais, endereços, permissões de rede
> e os valores que param o robô em silêncio — está em
> [credenciais-e-acessos.md](credenciais-e-acessos.md), organizado por **quem
> fornece** e com a ordem em que dá para liberar.

```
ENV=dev
CAMINHO_SQLITE=<caminho do espelho que você acabou de gerar>
```

Os caminhos de dados já vêm apontando para **`unificado/arquivos/`** (2026-08-07)
— dentro do projeto, porque a regra do processo é que os arquivos são locais:

```
CAMINHO_OPERADORAS=arquivos/Operadoras
DIRETORIO_ENTRADA=arquivos/Entrada
CAMINHO_EXPECTATIVA_DETRAF=arquivos/Expectativa
CAMINHO_CONTROLE_CT=arquivos/CT
```

🔴 **Relativo aqui vale a partir de `unificado/`, não de onde você lançou o
robô.** Agendar pelo Agendador de Tarefas sem preencher "Iniciar em" faria nascer
uma segunda árvore em `C:\Windows\System32`, e o modo de falha é mudo: o RPA 1
grava numa, o RPA 2 varre a outra e **termina com sucesso**. Caminho absoluto
passa intacto — é o que produção usa.

### 2b. Monte a árvore

```
python preparar_ambiente.py
python preparar_ambiente.py --operadora CLARO --referencia 202507
```

Ele lê as **variáveis**, não uma lista de nomes: apontar o `.env` para um
compartilhamento de rede faz o script preparar aquele compartilhamento. É
idempotente — rodar de novo não duplica nem apaga nada — e recusa rodar com
`ENV=prod`.

Sem ele, a primeira execução esbarra numa pasta faltando, quase sempre no meio do
fluxo, depois de o robô já ter aberto o Outlook ou o AGI.

### 3. Confira o ambiente

```
python verificar_ambiente.py --rpa rpa3
```

Ele diz, com a correção ao lado de cada falha:

- variáveis ausentes, e variáveis **com nome digitado errado** (que não dão erro
  nenhum — o default vale e a linha é ignorada);
- credenciais presentes ou não, **sem revelar valor**;
- pastas: não configurada × não existe × **sem permissão de escrita** — três
  causas que produzem o mesmo sintoma no robô e pedem correções diferentes;
- banco: conecta, tabelas existem, colunas existem;
- **quais efeitos externos estão ligados**.

Rode uma vez por robô (`--rpa rpa1`, `rpa2`, `rpa3`), porque cada um pode estar
num modo diferente.

### 4. Rode os robôs, nesta ordem

O RPA 2 consome o que o RPA 1 salvou; o RPA 3 consome o que o RPA 2 apurou **e a
decisão do analista no WebFat**.

```
python rpa1_captura/main.py --referencia 202507 --dry-run
python rpa2_validacao_apuracao/main.py --referencia 202507 --dry-run
python rpa3_contestacao_agi_ec/main.py --referencia 202507 --operadoras CLARO --dry-run
```

⚠️ **Entre o RPA 2 e o RPA 3 há uma decisão humana.** O RPA 3 lê o
`tipo_contestacao` que o analista gravou no WebFat. Sem esse sinal, ele gera os
artefatos e não contesta nada — e isso não é defeito.

### 5. Leia o diagnóstico, não o log

Cada execução grava **dois** arquivos, e eles respondem perguntas diferentes:

| Arquivo | Responde |
|---|---|
| `logs/{host}/{robo}/diagnosticos/{carimbo}.txt` | **em qual ETAPA parou, e por quê** |
| `logs/{host}/{robo}/execucoes/{carimbo}.md` | o que saiu **por operadora** (só RPA 3) |

O `.txt` é o de partida, e é o que se manda para análise. Ele tem uma seção por
etapa — o que ela recebeu, o que produziu, quanto demorou — e, quando falha, o
erro **com traceback** e a causa traduzida quando é erro de banco.

Três coisas que ele resolve e o log não resolvia:

- **"onde parou?"** — antes, o `except` de topo dizia só *"erro não tratado"*.
  Agora o desfecho é `ERRO na etapa 2/4 (carga)`;
- **"rodou e não produziu nada"** aparece escrito, distinto de *"não rodou"*. É o
  modo de falha mais comum aqui — lista de filtro vazia, pasta errada, mês sem
  arquivo;
- **falha de arranque** — SQLite faltando, WebFat fora do ar — cai na etapa
  `arranque`, que envolve o import dos módulos. Antes ela matava o processo antes
  de qualquer registro existir.

Ele sai **sempre**, inclusive quando dá tudo certo: a etapa que passou é o
contexto que diz se o erro é dela ou do que veio antes.

O log completo continua lá, para quando o diagnóstico não bastar.

### 6. Para repetir o mesmo cenário

```
python resetar_homologacao.py --referencia 202507
```

⚠️ **Sem isto, a segunda execução do mesmo mês não faz nada** — e parece defeito.
O histórico anti-reprocessamento guarda o que já passou, que é o comportamento
certo em produção e o mais confuso possível na homologação.

---

## ⚠️ `ENV=dev` isola o banco — e só o banco

Vale ser explícito, porque a suposição contrária é natural e cara:

| O que | `ENV=dev` isola? | O que isola de verdade |
|---|---|---|
| **Banco WebFat** | ✅ **sim** | `ENV=dev` + `CAMINHO_SQLITE` |
| **AGI** | ❌ não | `PERMITIR_ACESSO_AGI` / `PERMITIR_UPLOAD_AGI` |
| **Outlook** | ❌ não | `PERMITIR_ENVIO_EMAIL` / `NOTIFICAR_OPERADORA_ENVIAR` |
| **Pastas de rede** | ❌ não | apontar as variáveis de caminho para pastas locais |
| **Numeração CT** | ❌ não | `CAMINHO_CONTROLE_CT` numa pasta local |

`ENV` é lido em **um** lugar: `repositorio_cache._obter_engine`, que escolhe entre
SQLite e MySQL. Ele não sabe que o AGI existe.

**Não existe "AGI de desenvolvimento".** O AGI é um aplicativo de produção numa
VM; o que protege são os kill-switches, não o modo.

### O perfil de homologação isolada

Com este `.env`, **nada sai da máquina** — e o fluxo roda inteiro:

```ini
# Banco: espelho local, escrita à vontade
ENV=dev
CAMINHO_SQLITE=banco_de_dados/TABELAS_DETRAF_espelho.db

# Efeitos externos: todos desligados
PERMITIR_ENVIO_EMAIL=false
NOTIFICAR_OPERADORA_ENVIAR=false
PERMITIR_UPLOAD_AGI=false
PERMITIR_ACESSO_AGI=false

# Pastas: cópias locais, não os compartilhamentos
CAMINHO_OPERADORAS=C:\homologacao\Operadoras
CAMINHO_EXPECTATIVA_DETRAF=C:\homologacao\Expectativa
DIRETORIO_ENTRADA=C:\homologacao\Entrada
DIRETORIO_HISTORICO_ARQUIVOS=C:\homologacao\historico

# Numeração CT: pasta local, para não consumir números da sequência real
CAMINHO_CONTROLE_CT=C:\homologacao\CT
CT_NUMERO_INICIAL=1
```

`--dry-run` força os quatro kill-switches para `false` na execução, sem depender
de o `.env` estar certo. **Use sempre**, mesmo com o perfil acima.

⚠️ **A pasta CT é a que mais se esquece.** Ela não é lida do banco nem protegida
por kill-switch: se apontar para o compartilhamento real, cada rodada de teste
**consome números da sequência de verdade** — e eles não voltam.

### O que sobra, e é irredutível

Com o perfil acima, **um** ponto continua sem isolamento possível: **a automação
de interface do AGI**. Ela é por reconhecimento de imagem, contra o aplicativo
real, e validá-la exige abri-lo e logar em produção.

Era a pendência **Q20**, ✅ **autorizada em 2026-08-06**. Tudo o mais se isola por
configuração; para o AGI existe procedimento, em
[checklist-validacao-agi.md](checklist-validacao-agi.md).

⚠️ **Uma coisa ainda bloqueia a primeira execução:** as credenciais do AGI que
vieram nos `.env` dos projetos de origem **precisam ser rotacionadas** (risco
R20). Autorização para usar o AGI não é autorização para usar aquela credencial.

---

## Os modos

`ENV` decide para onde o robô escreve. **Cada robô pode ter o seu**, com o sufixo
vencendo o valor geral:

```
ENV=dev            # vale para todos
ENV_RPA1=prod      # menos para o RPA 1
```

Vale para **qualquer** variável: `CAMINHO_SQLITE_RPA3`, `LOG_LEVEL_RPA2`,
`PERMITIR_ACESSO_AGI_RPA3`. É o que permite ligar o acesso ao AGI só no RPA 3, na
validação em produção, sem tocar nos outros.

Todo robô registra no arranque **em que modo está e de qual variável isso veio**.

| Modo | Banco | Quando usar |
|---|---|---|
| `dev` | SQLite local | Toda a homologação funcional |
| `prod` | MySQL real | Só na validação final, combinada com o GP-Vivo |

---

## Os efeitos externos

Quatro kill-switches, **todos desligados por padrão**. Com eles desligados o
fluxo roda inteiro, gera todos os arquivos e registra o que faria — só não age
para fora.

| Variável | O que libera |
|---|---|
| `PERMITIR_ENVIO_EMAIL` | e-mail de contestação à operadora (HU-15) |
| `NOTIFICAR_OPERADORA_ENVIAR` | e-mail de arquivo inválido (RPA 2) |
| `PERMITIR_UPLOAD_AGI` | carga no AGI (HU-17/18) — **escreve em produção** |
| `PERMITIR_ACESSO_AGI` | abre o AGI e baixa o relatório (HU-20) |

`--dry-run` desliga os quatro **independentemente do `.env`**, só naquela
execução. Use sempre que a rodada for exploratória.

⚠️ O e-mail à operadora é **o único efeito que chega a alguém de fora da Vivo**.
Ele depende de duas coisas ao mesmo tempo: o kill-switch **e** o
`CAMINHO_CONTATOS_OPERADORAS` preenchido. Na dúvida, aponte o arquivo de contatos
para um endereço interno.

---

## Parar entre as etapas para conferir

```bash
python main.py --pausar --dry-run
```

Ao fim de cada etapa abre uma caixa com **o que ela acabou de produzir**, e a
execução só segue no **Continuar**:

- **Continuar** — segue para a próxima etapa;
- **Cancelar** — aborta a execução. O que já foi feito fica feito; a etapa
  seguinte pode ser rodada depois com `--etapa`. Código de saída **2**, distinto
  de 0 (sucesso) e de 1 (erro);
- **Abrir pasta** — abre no Explorer o que a etapa produziu.

A caixa diz sempre **qual é a próxima etapa**, e avisa em caixa alta quando ela
escreve para fora (`ESCREVE NO AGI`, `SAI DA EMPRESA`). A parada mais útil é a do
fim do `artefatos` do RPA 3: é a última antes de o AGI ser tocado.

### 🔴 Ela nunca vai acontecer em produção

A caixa **espera indefinidamente** — num robô desassistido isso travaria o
processo. Por isso ela exige **quatro** condições ao mesmo tempo:

| # | Condição | O que protege |
|---|---|---|
| 1 | `ENV=dev` | Produção, sem exceção |
| 2 | `PAUSA_ENTRE_ETAPAS=true` | Estar em dev não basta — precisa ser pedido |
| 3 | Sessão gráfica utilizável | Tarefa agendada em sessão 0 não tem desktop: **segue** |
| 4 | Fora do pytest | Uma suíte que abre diálogo trava o CI |

A terceira é a que segura o caso perigoso de verdade, porque **não depende de
ninguém ter configurado nada certo**: ela tenta abrir a janela, falha, e a
execução continua.

Qualquer uma que falhe → o robô segue sem parar, com o motivo no log. O
`verificar_ambiente.py` anuncia o estado da pausa junto dos kill-switches.

> 💡 Prefira `--pausar` a mexer no `.env`: ele liga só naquela execução, e não
> fica ligado por engano depois.

---

## Erro visto → causa provável → onde olhar

| O que aparece | Causa provável | O que fazer |
|---|---|---|
| `[BANCO] usuário ou senha recusados` | credencial errada | `USUARIO_BD` / `SENHA_BD` |
| `[BANCO] não foi possível alcançar o servidor` | rede, VPN, firewall | `HOST_BD_RPA` / `PORT_BD_RPA` |
| `[BANCO] o SQLite ... não existe` | espelho não gerado | `python espelhar_banco.py` |
| `[BANCO] falta uma coluna` | schema divergente | `python espelhar_banco.py --somente-schema` — é a Q22 |
| `[OUTLOOK] não foi possível conectar` | perfil / "Novo Outlook" | Use `--pasta-entrada` para homologar sem Outlook |
| `[Q21] Sem expectativa Vivo em [...]` | pasta vazia ou ausente | **Grave.** Sem expectativa a variação dá 100% e a operadora inteira é contestada indevidamente |
| `... valores viraram ZERO` | separador de milhar | O arquivo tem `1.234,56`; a V2 não define separador. Confira antes de aceitar a apuração |
| `Arquivo [...] rejeitado: layout fora do padrão` | layout diferente | Leia o `*_RECUSADO.md` ao lado do arquivo |
| `numeração CT indisponível` | `CAMINHO_CONTROLE_CT` | A carta é desabilitada para a execução inteira, de propósito: emitir arriscaria duplicar número |
| `HU-15 sem destinatários` | `CAMINHO_CONTATOS_OPERADORAS` | Pendência **Q16** — a tabela de contatos não existe na V2 |
| Segunda execução não faz nada | histórico anti-reprocessamento | `python resetar_homologacao.py --referencia AAAAMM` |
| Imagem do AGI não encontrada | resolução / tema da VM | Recapture **nesta VM** — ver [checklist-validacao-agi.md](checklist-validacao-agi.md) |

---

## O que **não** está no escopo da homologação

- **RPA 4 / HU-21.** Não tem código — o Projeto 6 veio só com a HU-20. A entrega
  foi adiada por decisão de 2026-08-05 (pendência **N12**). A pasta
  `rpa4_retificacao/` tem só um `README.md`.
- **O AGI de verdade**, até o GP-Vivo autorizar. Não existe ambiente de teste
  (pendência **Q20**); o roteiro do modo "só leitura" está em
  [checklist-validacao-agi.md](checklist-validacao-agi.md).
- **As 15 pendências abertas** — ver
  [pendencias-para-o-cliente.md](../04-relatorios/pendencias-para-o-cliente.md).
  Várias produzem comportamento que **parece defeito e não é**; a tabela acima
  cobre as que mais aparecem.

---

## Antes de abrir um defeito

Três perguntas que evitam a maior parte dos falsos positivos:

1. **Está na lista de pendências?** Vários comportamentos são decisão registrada,
   não erro — a rejeição da expectativa sem `R$_Bruto` (N3) é o caso mais comum.
2. **O relatório da execução diz que foi pulado, e por quê?** Etapa pulada com
   motivo nomeado é comportamento projetado: o robô prefere pular com aviso a
   derrubar o mês inteiro por causa de uma operadora.
3. **Em que modo rodou?** O cabeçalho do relatório diz, e diz também de qual
   variável o modo veio.
