# Detraf Unificado — RPAs

Repositório unificado dos RPAs de Detraf e Contestação de Despesa (GSA ATA0000574).

**Estado:** os **quatro** RPAs executam o fluxo ponta a ponta e têm suíte própria — **cinco suítes verdes**. O **RPA 4 nasceu em 2026-08-10**, quando o Projeto 6 chegou com a HU-21; a automação de tela dele veio da origem **sem calibração na VM**, e a primeira execução real precisa de acompanhamento (ver `rpa4_retificacao/FLUXO.md`).

🔴 **Antes da primeira execução contra o AGI:** as credenciais que vieram nos `.env` dos projetos de origem **precisam ser rotacionadas** (risco R20).

As pendências que restam estão organizadas por destinatário em [`docs/04-relatorios/pendencias-para-o-cliente.md`](../docs/04-relatorios/pendencias-para-o-cliente.md).

---

## Estrutura

```
unificado/
├── comum/                        base compartilhada pelos RPAs
│   ├── config/    configuration · constantes · logger_config
│   ├── dados/     repositorio_cache · repositorio_tabelas · tabelas
│   ├── arquivos/  gerenciador · historico · nomenclatura · estrutura_pastas
│   ├── dominio/   variacao · competencia · layout_detraf · retificacao
│   ├── integracoes/ outlook · outlook_config · agi · sftp
│   ├── view/imagens/ PNGs de referência do AGI, por tela
│   └── utils/     decoradores · debug
├── rpa1_captura/                 main.py + src/ + tests/
├── rpa2_validacao_apuracao/      main.py + src/ + tests/
├── rpa3_contestacao_agi_ec/      main.py + src/ + tests/   ⚠️ PARCIAL
├── rpa4_retificacao/             main.py + src/ + tests/   ⚠️ AGI não calibrado
└── tests/                        suíte da base comum
```

## Como executar

```bash
# 1. Ambiente
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# 2. Banco
.venv\Scripts\python espelhar_banco.py        # copia o MySQL real (preferível)
.venv\Scripts\python preparar_banco_dev.py    # ou, sem acesso ao MySQL

# 3. Configuração
copy .env.example .env      # e preencha

# 4. Criar a árvore de pastas que os robôs leem e escrevem
.venv\Scripts\python preparar_ambiente.py

# 5. Conferir o ambiente ANTES de rodar
.venv\Scripts\python verificar_ambiente.py

# 6. Rodar um RPA
.venv\Scripts\python rpa1_captura\main.py
.venv\Scripts\python rpa2_validacao_apuracao\main.py
.venv\Scripts\python rpa3_contestacao_agi_ec\main.py
.venv\Scripts\python rpa4_retificacao\main.py --dry-run
```

⚠️ O passo 2 não é opcional. Os SQLite que vieram com os projetos têm a tabela de
log com o nome **antigo** e o mapa de descritores com colunas em outro formato;
os dois scripts corrigem isso. O `espelhar_banco.py` também grava o **DDL real**
das tabelas, que é a resposta da pendência Q22.

### Onde os arquivos ficam

Em **`unificado/arquivos/`** — dentro do projeto, porque a regra do processo é
que os arquivos são locais. É a árvore que o `preparar_ambiente.py` monta:

```
arquivos/
  Operadoras/          {operadora}/{ano}/{aaaamm}/{4 subpastas} — só INSUMO
  Entrada/             anexos baixados pelo RPA 1
  Expectativa/         arquivos `_D` baixados do SFTP (etapa 1 do RPA 2)
  CT/                  numeração das cartas de contestação
  _NAO_IDENTIFICADOS/  arquivo íntegro, cadastro nosso faltando
  _QUARENTENA/         arquivo reprovado, operadora já avisada
  _TEMP/               área de trabalho do RPA 2 (cópias)
  _SAIDA/              artefatos da validação — e ENTRADA do batimento
  historico/           índice anti-reprocessamento
```

Está no `.gitignore`: são Detrafs reais, com tráfego e faturamento.

🔴 **Entrada e saída são pastas diferentes desde 2026-08-10.** O RPA 2 copia o
insumo para `_TEMP`, escreve **na cópia** e entrega os artefatos (`_EXP`,
`_ERRO`, `_BK`, `_RECUSADO.md`) em `_SAIDA/{aaaamm}/`. Antes disso ele regravava
o arquivo de expectativa no lugar, e um banco com uma coluna fora do lugar
bastava para reduzir o insumo ao cabeçalho — em produção, o arquivo da rede.

`_SAIDA` é **o contrato entre as duas etapas do RPA 2**: a validação grava e o
batimento lê, os dois pela mesma função (`estrutura_pastas.caminho_de_saida`).
Até essa data cada um derivava o caminho por conta própria, eles divergiam, e o
batimento nunca encontrava um Detraf — a contestação saía com o lado da operadora
zerado e variação de -100%, sem erro nenhum no log.

🔴 **Caminho relativo no `.env` vale a partir de `unificado/`, não do diretório
de onde o robô foi lançado.** Sem essa ancoragem, agendar pelo Agendador de
Tarefas sem preencher "Iniciar em" faria nascer uma segunda árvore em
`C:\Windows\System32` — e o modo de falha é mudo: o RPA 1 grava numa, o RPA 2
varre a outra e termina com sucesso. Caminho absoluto passa intacto, que é o que
produção usa. Ver `configuration._ancorar` e `tests/test_ancoragem_de_caminhos.py`.

### Quando algo falha: o diagnóstico por etapa

Toda execução grava um `.txt` com **uma seção por etapa** — o que ela recebeu, o
que produziu, quanto demorou, e o erro com traceback quando houver:

```
logs/{host}/{robô}/diagnosticos/{carimbo}.txt
```

É o arquivo que se manda para análise. Ele sai **sempre**, inclusive quando dá
tudo certo: a etapa que passou é o contexto que diz se o erro é dela ou do que
veio antes — e "terminou bem sem fazer nada" não deixaria arquivo nenhum se só
gravasse em erro.

A primeira etapa é o `arranque`, que envolve o import dos módulos. É lá que caem
as falhas de banco e de configuração, que acontecem **antes** de qualquer etapa
de negócio começar.

### Rodar um recorte

Os quatro `main.py` aceitam argumentos — `--help` em cada um lista todos. Sem
argumento nenhum, o comportamento é o de produção, e as agendas não mudam.

```bash
.venv\Scripts\python rpa3_contestacao_agi_ec\main.py --referencia 202507 --operadoras CLARO --dry-run
```

`--dry-run` desliga **todos** os efeitos externos naquela execução,
independentemente do `.env`.

### Um modo por robô

Qualquer variável aceita o sufixo do robô, e o específico vence — é o que permite
deixar o RPA 1 em produção enquanto o RPA 3 aponta para um espelho local:

```
ENV=prod
ENV_RPA3=dev
CAMINHO_SQLITE_RPA3=banco_de_dados/TABELAS_DETRAF_espelho.db
```

Cada robô registra no arranque em que modo está **e de qual variável isso veio**.

## O fluxo de cada robô

Cada RPA tem um `FLUXO.md` na própria pasta, com as **etapas sequenciais**: o que
cada passo faz, a HU correspondente, o ponto de entrada no código, o que produz e
**como ele falha**.

| Robô | Etapas | Documento |
|---|---|---|
| RPA 1 | `captura` · `processamento` | [rpa1_captura/FLUXO.md](rpa1_captura/FLUXO.md) |
| RPA 2 | `expectativa` · `validacao` · `batimento` | [rpa2_validacao_apuracao/FLUXO.md](rpa2_validacao_apuracao/FLUXO.md) |
| RPA 3 | `artefatos` · `carga` · `email` · `verificacao` | [rpa3_contestacao_agi_ec/FLUXO.md](rpa3_contestacao_agi_ec/FLUXO.md) |
| RPA 4 | `deteccao` · `retificacao` | [rpa4_retificacao/FLUXO.md](rpa4_retificacao/FLUXO.md) |

Os nomes das etapas são os valores de `--etapa`: cada uma roda e se repete
isolada. Com `--pausar`, a execução **para ao fim de cada etapa** e mostra o que
ela produziu — só em `ENV=dev`, nunca em produção.

## Homologação

- [Guia de partida](../docs/03-checklists/homologacao-guia-de-partida.md) — a
  ordem das coisas e a tabela "erro visto → causa → onde olhar"
- [Credenciais e acessos](../docs/03-checklists/credenciais-e-acessos.md) — o que
  precisa ser provisionado, por quem fornece
- [RPA 1 e RPA 2](../docs/03-checklists/homologacao-rpa1-e-rpa2.md)
- [RPA 3](../docs/03-checklists/homologacao-rpa3.md)
- [Validação do AGI](../docs/03-checklists/checklist-validacao-agi.md) — o modo
  "só leitura" contra produção

## Como testar

```bash
.venv\Scripts\python executar_testes.py
```

⚠️ Os quatro RPAs têm um pacote chamado `src`, e eles **não coexistem num mesmo
processo Python**. Por isso cada suíte roda numa invocação separada do pytest —
é o que `executar_testes.py` faz. Rodar `pytest` na raiz coleta apenas a suíte
da base comum.

| Suíte | Testes |
|---|---|
| base comum | 375 |
| RPA 1 — captura | 107 |
| RPA 2 — validação e apuração | 74 |
| RPA 3 — contestação, AGI e EC | 291 |

O RPA 2 era a maior dívida da unificação — os Projetos 2 e 3 vieram sem nenhum
teste, e é neles que estão as regras mais densas da V2. A suíte foi escrita em
2026-08-04, cobrindo as 15 colunas uma a uma, a tarifa contra a tabela regulada,
a limpeza de tráfegos, a consolidação no banco e a varredura de arquivos.

⚠️ **A contagem do RPA 2 caiu em 2026-08-06 sem nada ter sido perdido.** As 15
colunas migraram para a suíte da base comum, junto com o `ValidadorColunas` que
elas testam; os testes da notificação saíram porque a notificação saiu. Compare
os totais, não as suítes.

O **contrato** com o RPA 1 está em `tests/test_contrato_rpa1_rpa2.py`.

---

## Os RPAs

| RPA | Responsabilidade | Gatilho | HUs |
|---|---|---|---|
| **1** — captura | Recebe e organiza os arquivos das operadoras | evento de e-mail + janela até a data de corte | 01–03 |
| **2** — validação e apuração | Valida, compara com a expectativa, apura contestação | lote, após a data de corte | 04–11 |
| **3** — contestação, AGI e EC | Gera artefatos, carrega no AGI, alimenta o EC | sinalização do analista no WebFat | 12–20 |
| **4** — retificação | Retifica contestações de meses anteriores | recuperação de tráfego | 21 |

O corte é por **natureza do gatilho**, não por afinidade temática.

### O fluxo do RPA 3

Por operadora do mês, na ordem que a V2 define: consolida o Detraf recebido contra
a expectativa Vivo → **HU-19** (despesa) → **HU-12** (`_EXT`) → **HU-13** (`_INT`)
→ **HU-14** (`_EXP` e carta) → **HU-16** (`CONT_PROC`). Depois, para o lote
inteiro: **HU-17/HU-18** (carga no AGI), **HU-15** (e-mail de contestação) e
**HU-20** (conferência do relatório contra o Encontro de Contas).

A HU-20 vem por último porque é ela que **confere o que foi carregado** — a V2
(¶690): *"Este relatório é gerado para conferir os valores carregados no AGI e no
EC"*.

A carga fica fora do laço porque os uploaders recebem a lista e abrem o AGI **uma
vez só** — abrir e logar custa minutos.

**A HU-14 pode emitir mais de uma carta.** O sinal do analista é por chave, então a
mesma operadora pode ter linhas COM e SEM retenção no mesmo mês — e a carta é um
documento com **um** texto de cenário. Desde a decisão de 2026-08-05 (Q25) sai
**uma carta por cenário**, cada uma com o seu número CT; o `_EXP` continua único, e
a HU-15 anexa todos. Por isso a numeração CT tem trava por arquivo (Q18): é a
mesma execução consumindo dois números seguidos da sequência global.

**Diante de etapa bloqueada, pula com aviso e segue.** O mês tem dezenas de
operadoras; abortar tudo faria uma pasta ausente bloquear o mês inteiro. Duas
exceções desabilitam a etapa para a execução inteira:

- **numeração CT indisponível** — ela é global e serial: se falha para a primeira
  operadora, falha para todas, e insistir arriscaria emitir número duplicado. A
  carta é desabilitada e os demais artefatos continuam saindo;
- **índice de remuneração** — é pré-condição de tudo; aborta antes do laço.

### ⚠️ O que ainda não sai

- **HU-15 — o e-mail só é enviado se os contatos forem configurados.** A "tabela
  de contatos do WebFat" **não existe na V2**: ela só diz *"Destinatários:
  contatos das operadoras"*. O nome vem da V1 — pendência **Q16**, ainda aberta.
  Desde 2026-08-05 há uma ponte: um CSV `operadora;emails` apontado por
  `CAMINHO_CONTATOS_OPERADORAS`. ⚠️ **Com ele preenchido e
  `PERMITIR_ENVIO_EMAIL=true`, o robô envia de verdade para as operadoras.**
- **O RPA 4 nunca rodou contra o AGI.** A HU-21 chegou em 2026-08-10 e foi
  migrada, mas contagens de TAB, deslocamento em pixels e posição no dropdown
  vieram da origem marcadas "PRECISA CONFIRMAR NA VM" — e o evento de Recuperação
  é irreversível. Tabela do que falta calibrar em `rpa4_retificacao/FLUXO.md`.
- 🔴 **`carga_agi` tem dois donos** desde o RPA 4: para o RPA 3 significa "o
  CONT_PROC subiu", para o RPA 4 "já retifiquei". Toda linha carregada pelo RPA 3
  fica invisível para o RPA 4. Resolver pede uma coluna própria e um `ALTER TABLE`.
- **A HU-18 e a HU-20 nunca executaram contra o AGI.** Não há ambiente de teste
  (**Q20**); a decisão foi validar contra produção no modo "só leitura" — roteiro
  em [`docs/03-checklists/checklist-validacao-agi.md`](../docs/03-checklists/checklist-validacao-agi.md).
  Falta a autorização do GP-Vivo.
### O RPA 4 — retificação (HU-21)

Lança o evento "Recuperação" no AGI quando a Vivo recupera tráfego que havia sido
contestado no mês anterior. O gatilho não é agenda, é condição de negócio: sem
variação negativa no mês anterior, não há o que fazer.

Duas etapas: `deteccao` (só lê e calcula — roda sem risco a qualquer momento) e
`retificacao` (abre o AGI; atrás de `PERMITIR_ACESSO_AGI`). Ver
[`rpa4_retificacao/FLUXO.md`](rpa4_retificacao/FLUXO.md).

---

## A base comum

Um componente só entra em `comum/` se tiver **duas ocorrências reais em RPAs
diferentes**, não depender de estado exclusivo de um RPA, implementar regra
fechada e ter variação parametrizável. Critérios em
[`../docs/02-planejamento/criterios-de-compartilhamento.md`](../docs/02-planejamento/criterios-de-compartilhamento.md);
veredicto de cada candidato em
[`../trabalho/inventarios/candidatos-componentes.md`](../trabalho/inventarios/candidatos-componentes.md).

**Ficou de fora de propósito:** a validação de tarifa, que só o RPA 2 usa.

A **camada do AGI** era o outro caso adiado — ocorrência única enquanto só o
RPA 3 operava o Portal. O RPA 4 nasceu em 2026-08-10 usando o mesmo AGI noutra
tela, o critério passou a ser satisfeito, e ela subiu para
`comum/integracoes/agi.py`, com as imagens em `comum/view/imagens/`.

A **camada de Outlook** era o caso adiado, esperando o Projeto 5 como teste de
confirmação. Ele chegou, a abstração se sustentou, e ela foi promovida para
`comum/integracoes/outlook.py` — com três consumidores em três RPAs: o 1 lê a
caixa, o 2 responde à operadora e o 3 envia a contestação.

### `comum/dominio/layout_detraf.py` — confere a forma do arquivo

Roda **antes** de qualquer validação linha a linha, e responde a outra pergunta:
não "esta linha está boa?", mas "este é o arquivo que eu esperava?".

Validação **posicional**, mínimo de 15 colunas, cabeçalho descartado — os nomes
reais das colunas não batem com os da V2 e variam por operadora. Vale para os
dois tipos de arquivo, operadora e expectativa.

⚠️ **Os arquivos de expectativa Vivo atuais são rejeitados por ela.** O layout
real não conforma com a V2 e não tem coluna de `R$_Bruto`. É o comportamento
decidido — antes, o arquivo passava e era lido por posição, comparando valor
bruto com minutos em silêncio. Enquanto a geração no ICT não for corrigida, **o
RPA 2 não produz contestação**. O diagnóstico no log identifica o caso pelo nome.

### `comum/dominio/variacao.py` — leia antes de mexer

É a regra que decide se há contestação, e tem consequência financeira direta.
Os Projetos 3 e 4 a implementavam de formas **incompatíveis**; a versão aqui é
um híbrido decidido a partir da V2 — base = lado operadora, com sinal, limiar
`>= 1%`. A fundamentação está no docstring do módulo e em
[`../docs/04-relatorios/duvidas-pendentes.md`](../docs/04-relatorios/duvidas-pendentes.md) Q2.

---

## O contrato RPA 1 → RPA 2

Um canal só: **arquivos em disco**. Quebrá-lo falha em silêncio — por isso tem
teste em `tests/test_contrato_rpa1_rpa2.py`.

O RPA 1 grava em
`{CAMINHO_OPERADORAS}/{operadora}/{ano}/{aaaamm}/Detrafs Recebidos/`, que é
exatamente onde o RPA 2 varre. Os dois lados usam o mesmo helper
(`comum/arquivos/estrutura_pastas.py::caminho_detrafs_recebidos`) e a mesma
constante de subpasta, para não poderem divergir.

`CAMINHO_OPERADORAS` é a **única** variável dessa raiz. `DIRETORIO_SAIDA` e
`CAMINHO_DETRAF_RECEBIDO` são alias mantidos por compatibilidade.

E, desde 2026-08-06, lá só entra **o que passou na validação** — ver abaixo.

**Duas pastas ficam FORA dessa raiz**, e não é preferência de organização: o
RPA 2 varre a raiz tratando **todo diretório como uma operadora**.

| Pasta | O que significa |
|---|---|
| `DIRETORIO_NAO_IDENTIFICADOS` | arquivo íntegro, cadastro **nosso** faltando |
| `DIRETORIO_QUARENTENA` | arquivo **reprovado**, e a operadora já foi avisada |

A quarentena tem um motivo a mais para ficar fora: se estivesse dentro, o RPA 2
acharia o arquivo reprovado e responderia à operadora uma **segunda** vez.

### O portão de validação

**O RPA 1 valida antes de salvar.** Layout (`comum/dominio/layout_detraf.py`) e
regras de coluna (`comum/dominio/validacao_colunas.py`) — **a mesma classe** que
o RPA 2 usa. Se cada robô tivesse a sua, os dois portões divergiriam em silêncio.

O que reprova vai para a quarentena com um `_RECUSADO.md` ao lado, entra no log
com `status = "Não validado"`, e gera resposta ao e-mail de origem com os
**motivos** da recusa.

O RPA 2 continua validando, como rede de segurança, e continua marcando `_ERRO`
— mas um `_ERRO` lá agora é **anomalia**, registrada em nível `error`.

Por padrão a resposta apenas **cria o rascunho** no Outlook;
`NOTIFICAR_OPERADORA_ENVIAR=true` liga o envio de verdade.

> O `_rastreamento.json` era o segundo canal do contrato: o RPA 2 procurava lá,
> **pelo nome do arquivo**, de qual e-mail cada Detraf viera. Como quem responde
> passou a ser o RPA 1 — que tem o `entry_id` em mãos —, o rastreamento voltou a
> ser interno a ele.

## O log

Os robôs rodam desassistidos: o log é a única testemunha do que aconteceu, e boa
parte das falhas não deixa outro rastro — um clique que não achou o botão no AGI,
um e-mail que não casou com a pasta, um arquivo que a operadora mandou diferente.

```
{RAIZ_LOGS}/{host}/{robô}/{ano}/{mês}/{dia}.log
```

**Um arquivo por robô.** `RAIZ_LOGS` é absoluta (default `unificado/logs`); antes
era relativa ao diretório de trabalho, e como cada robô é lançado da sua pasta,
existiam três árvores de log separadas no disco.

Retenção de **90 dias** (`LOG_RETENCAO`), não 7: o ciclo do Detraf é mensal, e uma
contestação de julho é questionada em agosto.

`logger.excecao(...)` registra **com traceback** — use dentro de um `except`
quando a falha for inesperada (I/O, parsing, COM). Para condição prevista —
anexo inline ignorado, e-mail sem anexo relevante — continue usando `warning`:
ali o traceback é ruído.

⚠️ `LOG_DIAGNOSE` inclui os **valores das variáveis locais** no traceback gravado.
Ajuda a diagnosticar e, pelo mesmo motivo, grava senha de banco e credencial do
AGI em arquivo. Segue o `ENV`: ligado fora de produção.

---

## Kill-switches

Três variáveis controlam os efeitos **externos e irreversíveis**. Todas têm
default `false`: com elas desligadas, o fluxo roda inteiro, decide tudo e registra
no log — só não age para fora.

| Variável | RPA | O que libera |
|---|---|---|
| `NOTIFICAR_OPERADORA_ENVIAR` | 2 | envia a resposta à operadora, em vez de deixar rascunho |
| `PERMITIR_ENVIO_EMAIL` | 3 | envia o e-mail de contestação (HU-15) |
| `PERMITIR_UPLOAD_AGI` | 3 | executa a carga no AGI (HU-17/HU-18) |
| `PERMITIR_ACESSO_AGI` | 3 | abre o AGI para **baixar** o relatório da HU-20 |

`PERMITIR_UPLOAD_AGI` é o mais crítico: **não existe ambiente de teste do AGI**
(pendência Q20). Sem ele, a única forma de exercitar o fluxo seria contra
produção.

---

## Automação de interface do AGI

O AGI não tem API. `rpa3_contestacao_agi_ec/src/integracoes/agi.py` opera o
aplicativo procurando botões na tela por comparação de imagem (`pyautogui`) e
conversando com os diálogos nativos do Windows (`pywinauto`). As imagens de
referência ficam em `rpa3_contestacao_agi_ec/src/view/imagens/`.

⚠️ **As imagens de `AGI_CONFIG/` e `AGI_Upload_Detraf/` vieram da máquina de
Receita e não foram validadas na de Despesa.** Resolução, escala de DPI e tema do
Windows mudam o pixel, e o `locateOnScreen` compara pixel. O mesmo vale para a
constante `REGION`, que delimita a área da grade na tela.

⚠️ **A credencial do AGI nunca entra no `.env`.** Vem de variável de ambiente da
máquina (`RPA_DETRAF_DESPESA_AGI_USER` / `..._PASSWORD`). O `.env` do Projeto 7
vinha com as duas preenchidas — esse padrão não foi herdado.

---

## Convenções

- **Configuração:** `comum/config/configuration.py` é o único ponto autorizado a
  chamar `os.getenv`. Nenhuma credencial no código.
- **Caminhos opcionais** usam `_caminho_opcional()`, que devolve `None` quando
  não configurados. Nunca `Path("")` — o pathlib o transforma em `Path(".")`, o
  diretório atual, e guardas como `if not caminho.exists()` passam.
- **Banco:** `comum/dados/repositorio_cache.py` é a única camada que fala com o
  banco. Nomes de tabela só em `comum/dados/tabelas.py`.
- **Regra de negócio:** nunca em dois lugares. Se aparecer duplicada, é bug.
- **Imports:** dentro de um RPA, `src.*`; da base comum, `comum.*`. O `main.py`
  de cada RPA resolve o `sys.path`.
- **Alterações da unificação** estão marcadas em comentário no ponto exato, com
  a origem e o motivo.

---

## Rastreabilidade

| Quero saber | Onde |
|---|---|
| O que cada RPA faz | [`../docs/01-entendimento/responsabilidades-dos-rpas.md`](../docs/01-entendimento/responsabilidades-dos-rpas.md) |
| Onde cada HU está implementada | [`../docs/04-relatorios/matriz-de-rastreabilidade.md`](../docs/04-relatorios/matriz-de-rastreabilidade.md) |
| O que mudou de comportamento | [`../trabalho/inventarios/duplicacoes.md`](../trabalho/inventarios/duplicacoes.md) |
| Por que um componente está (ou não) em `comum/` | [`../trabalho/inventarios/candidatos-componentes.md`](../trabalho/inventarios/candidatos-componentes.md) |
| O que falta decidir com o cliente | [`../docs/04-relatorios/duvidas-pendentes.md`](../docs/04-relatorios/duvidas-pendentes.md) |
| O código de origem | [`../projetos-origem/`](../projetos-origem/) — **somente leitura** |

`projetos-origem/` é a referência para comprovar equivalência funcional. Nada
lá é alterado.
