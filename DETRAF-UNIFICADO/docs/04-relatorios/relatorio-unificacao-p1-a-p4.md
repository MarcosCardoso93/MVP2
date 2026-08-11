# Relatório da Unificação — Projetos 1 a 4

**Data:** 2026-07-31
**Escopo:** base comum + RPA 1 e RPA 2 completos + RPA 3 parcial
**Fora do escopo:** RPA 4, orquestração do Épico 4, projetos P5/P6/Épico 5 (não entregues)

---

## Resultado

| Entrega | Situação |
|---|---|
| Base compartilhada | ✅ 17 módulos (contagem corrigida em 2026-08-04) |
| **RPA 1** — captura | ✅ completo, 46 testes |
| **RPA 2** — validação e apuração | ✅ completo, ⚠️ **0 testes** |
| **RPA 3** — contestação, AGI e EC | ⚠️ **parcial**, 164 testes |
| **RPA 4** — retificação | ⬜ depende do P6 |

**246 testes passando.** `projetos-origem/` e `documentação/` intocados.

---

## Verificações do plano

| # | Verificação | Resultado |
|---|---|---|
| 1 | `projetos-origem/` e `documentação/` intocados | ✅ 0 arquivos `.py` alterados na origem |
| 2 | Cada RPA executa isolado | ✅ os três `main.py` carregam e resolvem o `sys.path` |
| 3 | Suítes do P1 e do P4 passam contra o código unificado | ✅ 46 e 164 |
| 4 | Comparação com as fixtures reais | ✅ 8 testes de equivalência |
| 5 | Nenhuma tarifa, mapeamento, limiar ou caminho absoluto constante | ✅ |
| 6 | `grep C:\Users` em `unificado/` | ✅ 0 ocorrências em código-fonte |
| 7 | Nenhuma regra de negócio em dois lugares | ✅ a variação existe num ponto só |
| 8 | HU-01 a HU-16 e HU-19 rastreáveis | ✅ matriz atualizada |

---

## A base compartilhada

17 módulos em `unificado/comum/`. Cada um com pelo menos duas ocorrências reais
na origem — **nenhum promovido por antecipação**.

| Módulo | Origem | Observação |
|---|---|---|
| `config/configuration.py` | união dos 4 | `load_dotenv()` sempre; credencial só por env |
| `config/constantes.py` | P4 | ⚠️ `COL_REL` corrigido de 4 para 5 |
| `config/logger_config.py` | P3 (superset) | nível por `LOG_LEVEL` |
| `dados/repositorio_cache.py` | união dos 4 | lista de tabelas virou parâmetro |
| `dados/repositorio_tabelas.py` | união dos 4 | 22 métodos, carregamento preguiçoso |
| `dados/tabelas.py` | novo | nomes de tabela num ponto só |
| `arquivos/gerenciador.py` | união de P2+P3+P4 | 17 comuns + 3 exclusivas |
| `arquivos/historico.py`, `utils/debug.py`, `utils/decoradores.py` | P2=P3=P4 | idênticos na origem |
| `arquivos/nomenclatura.py`, `arquivos/estrutura_pastas.py` | P4 + P1 | |
| `dominio/variacao.py` | **novo** | a regra de 1% unificada |
| `dominio/competencia.py` | P1 + P2/P3/P4 | |

**Deliberadamente fora:** validação de tarifa (só o RPA 2 usa — falha C1) e
acesso ao Outlook (**adiado** até o P5 chegar, que é o teste de confirmação da
abstração).

---

## Mudanças de comportamento

Toda alteração está marcada em comentário no ponto exato do código.

### 1. 🔴 A regra de variação — decidida a partir da V2

Os Projetos 3 e 4 a implementavam de formas incompatíveis. A versão unificada é
um híbrido:

| Aspecto | Adotado | Vinha de | Fundamento na V2 |
|---|---|---|---|
| Base do percentual | **operadora** | P4 | *"A origem dos dados é o Detraf 'oficial' enviado pela operadora"* |
| Par ausente | **contesta** (100%) | P4 | *"apresentar os valores zerados de expectativas"* |
| Sinal | **importa** | P3 | *"maior que **+1%**"*; variação negativa vai para a retificação |
| Limiar | `>= 1%` | ambos | |

**Impacto no RPA 2:** o batimento passa a contestar casos que antes passavam em
branco (operadora cobrou sem expectativa correspondente) e a calcular o
percentual sobre outra base. É mudança de resultado financeiro, intencional.

**Pendência residual:** a V2 diz *"se for **superior**"* (`> 1%`); o código usa
`>=`. Só difere em exatamente 1,000000%.

### 2. 🔴 `COL_REL` de 4 para 5

O Projeto 4 declarava o Rel no índice 4 — que é o **POI**. Com isso, o filtro de
linhas de total não removia nada.

**Comprovado contra arquivo real:** a fixture `algar_stfc_reduzido.csv` tem
cabeçalho, e no índice 5 está `tipo_relatorio`. Há teste fixando isso.

Isso também **esvazia a decisão D-8** do Projeto 4: a "variação de layout entre
o real e o documentado" não existia — o índice documentado é que estava errado.

### 3. Normalização de EOT

O Projeto 1 não removia a parte decimal antes de comparar. Lendo de Excel, uma
EOT que chega como `11.0` não casava com o Anexo 5 e caía no fallback por
domínio. Passou a usar a versão de P2/P3/P4.

### 4. Coluna `remuneracao` na tabela de contestação

O Projeto 3 não a gravava; o Projeto 4 lê a tabela por uma chave que a inclui.
O RPA 3 nunca casaria uma linha escrita pelo RPA 2. O dado já existia com outro
nome (`tipo_produto`) e passou a ser gravado.

### 5. Logging

Nível configurável (`LOG_LEVEL`, default `INFO` — o P1 usava `DEBUG` fixo) e
`opt(depth=2)` uniforme, inclusive em `error`. Com `depth=1` o log reportava
`logger_config.py` como origem em vez do código chamador.

### 6. Carregamento preguiçoso das tabelas

Os projetos carregavam todas as suas tabelas no `__init__`. Como cada RPA usa um
subconjunto, isso faria o RPA 1 exigir a tabela de tarifas que não usa.

### 7. Correções de higiene

- Caminho absoluto da máquina do desenvolvedor removido (`repositorio_cache.py:82` do P2)
- `load_dotenv()` passa a ser chamado sempre (o P2 não chamava)
- `geradores_tabelas_homo.py` **não migrado** — ferramenta de bancada, não produto

---

## 🔴 Achados que **não** foram corrigidos

Registrados, não tratados — corrigi-los seria desenvolvimento, não unificação.

### A. O layout da expectativa Vivo é outro arquivo — e não tem `R$_Bruto`

O Projeto 3 aplica os índices do arquivo da operadora **também** ao de
expectativa. Sobre o layout real, nenhum campo cai no lugar:

| Campo | Índice na operadora | O que há nesse índice na expectativa |
|---|---|---|
| Devedora | 1 | `EOT_CREDORA` |
| Tráfego | 3 | `PERIODO_REFERENCIA` |
| GH | 7 | `PARTE_TARIFADA` |
| Minutos | 9 | `GRUPO_HORARIO` |
| **R$_Bruto** | 14 | `MINUTOS_TARIFADOS` |

E o arquivo de expectativa **termina em `VALOR_LIQUIDO`** — não existe coluna de
valor bruto. Mas a comparação da HU-10 é justamente sobre `R$_Bruto`.

⚠️ **Evidência de uma única fixture reduzida.** A V2 menciona uma etapa de
conversão feita por outra demanda; é possível que o arquivo que chega em produção
já esteja normalizado. **Confirmar contra um arquivo real do pipeline.**

Se confirmado, é o achado mais grave: a decisão de contestar sairia de dados
desalinhados. As constantes `EXPECTATIVA_COL_*` foram criadas para o código
**nomear** o problema em vez de repeti-lo silenciosamente, e há teste fixando a
diferença entre os dois layouts.

→ pendência **N3**

### B. A orquestração do RPA 3 é um stub

`gerar_artefatos()` só emite logs. Os services existem e passam em 164 testes,
mas nada os encadeia. Conforme decidido, não foi implementado.

### C. Remuneração derivada do POI (Projeto 3)

`_enriquecer_com_tipo` lê o índice 4 (POI) e trata o valor como descritor. Com
dados reais, `"SPOX_1007"` → último caractere `"7"` → não casa com nenhum
descritor → `tipo_produto` nulo. O correto é o índice 6.

Não corrigido porque o service inteiro precisa ser revisto junto com o achado A —
os dois têm a mesma raiz.

### D. `tipo_operacao` derivado da Credora (Projeto 3)

A V2 diz que o Tipo de Operação é baseado na **EOT Vivo** (Devedora). O Projeto 3
usa a Credora (operadora). Mesma raiz do achado C.

### E. O RPA 2 não tem teste algum

É onde estão as regras mais densas — validação das 15 colunas, tarifas com dupla
convivência em fevereiro, batimento. **A maior dívida da unificação.**

Recomendação: escrever testes de caracterização com as fixtures do Projeto 4
**antes** de mexer nesse código.

### F. Numeração CT sem trava

Estado compartilhado em pasta de rede, lido e incrementado sem transação.
→ pendência **Q18**

### G. Índices de coluna fixos

Contrariam o requisito de layout configurável (risco do imposto de 2028 e da
chegada de CBS/IBS). Mitigado em parte: as constantes estão nomeadas e aceitam
override por parâmetro. A solução completa depende da definição de CBS/IBS (Q6).

---

## Pendências que a análise resolveu ou criou

**Resolvidas pelo código:**
- **Q2** (regra de 1%) — decidida a partir da V2
- **Q4** (`_ENV` × `Base_Contestação`) — o P3 gera a planilha **e** grava no banco; a planilha é insumo da HU-14
- **Q10** (recálculo do total no `_BK`) — o P2 recalcula
- **Q3** parcialmente — o Épico 5 **não está no P4**; ele não tem nenhuma automação de UI

**Anuladas:**
- **N2** — a "divergência de nome de tabela" no P4 era nome de **atributo**. Os quatro projetos usam os mesmos cinco nomes de tabela

**Criadas:**
- **N1** — `tbl_detraf_despesa_arquivos` (código) × `tbl_rpa_log_detraf_despesa_arquivos` (V2)
- **N3** — layout da expectativa e ausência de `R$_Bruto` 🔴
- **N4** — `tipo_lote` (4 valores) × `tipo_registro` (3 valores)
- **N5** — entregar a pasta `AI/` e o `TODO/` do P4, fonte das decisões D-1 a D-21
- **N6** — declaração de dependências dos quatro projetos

---

## Adendo — revisão do contrato RPA 1 → RPA 2 (2026-07-31)

Revisão dos dois canais por onde os robôs conversam: os **arquivos em disco** e
o **`_rastreamento.json`**. Quatro defeitos encontrados, todos corrigidos.

### O que estava quebrado

| # | Defeito | Consequência |
|---|---|---|
| 1 | 🔴 `RASTREAMENTO_ARQUIVO_PATH` era `str`, e o RPA 2 chama `.exists()` nele | **Nenhuma operadora era notificada.** O `AttributeError` caía no `try/except` e virava uma linha de log — o robô reportava sucesso |
| 2 | 🔴 `CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO` sem valor virava `Path('.')` | A guarda `if not ...exists()` passava e o `read_text()` estourava **fora** do `try` por arquivo, **abortando o RPA 2** depois de gravar tudo no banco |
| 3 | 🔴 `download_attachments` baixava **todos** os anexos não-inline | PDF, Word e imagem de assinatura iam para a pasta de rede da operadora e para o rastreamento. A V2 manda "baixar apenas os csv ou excel" |
| 4 | 🟡 A pasta `_NAO_IDENTIFICADOS` ficava dentro da raiz das operadoras | O RPA 2 a varria como se fosse uma operadora |

O defeito 1 **foi introduzido por mim na unificação**: o Projeto 1 definia a
variável como `str` e o Projeto 2 como `Path`; adotei a do Projeto 1 sem
verificar os consumidores.

### O que foi feito

- **Tipos corrigidos.** `RASTREAMENTO_ARQUIVO_PATH` é `Path`. Caminhos opcionais
  passam por `_caminho_opcional()`, que devolve `None` em vez de `Path('.')` —
  a armadilha do defeito 2 está fechada para todas as variáveis de caminho.
- **Raiz única.** Os projetos davam **três** nomes à mesma pasta física:
  `DIRETORIO_SAIDA`, `CAMINHO_DETRAF_RECEBIDO` e `CAMINHO_OPERADORAS`. Nada
  garantia que apontassem para o mesmo lugar — e, se divergissem, o RPA 2 só
  registrava "nenhum arquivo encontrado". Agora `CAMINHO_OPERADORAS` é canônica
  e as outras duas são alias; os nomes antigos seguem aceitos como fallback.
- **Subpasta `Detrafs Recebidos`.** Os dois RPAs passam a usar o helper
  `comum/arquivos/estrutura_pastas.py::caminho_detrafs_recebidos`. **Fecha a
  lacuna da HU-03**, que exigia essa subpasta.
- **Filtro de anexo** no download, por `EXTENSOES_PERMITIDAS`.
- **Pasta de exceção** movida para fora da raiz das operadoras.
- **Envio configurável.** `NOTIFICAR_OPERADORA_ENVIAR` (default `false` —
  rascunho). A V2 determina que a notificação seja enviada, mas o envio é
  irreversível e a caixa de teste ainda não foi confirmada (Q20). Ligar em
  produção após validar em homologação.

### Rede de proteção

**+29 testes** (`tests/test_contrato_rpa1_rpa2.py` e
`rpa1_captura/tests/test_outlook_service_anexos.py`), fixando: os tipos da
configuração, a raiz única, a pasta de exceção fora da varredura, o caminho que
o RPA 1 grava sendo o mesmo que o RPA 2 varre, e a busca no rastreamento **pelo
nome** do arquivo — que é o único elemento comum, já que o arquivo muda de lugar
entre os dois robôs.

Além de uma simulação ponta a ponta: o RPA 1 recebe csv + pdf, grava só o csv na
subpasta certa, e o RPA 2 o encontra e localiza o e-mail de origem.

**Total: 275 testes passando** (59 base comum · 52 RPA 1 · 164 RPA 3).

### Ainda em aberto neste contrato

- **Nomes de arquivo ambíguos.** Se duas operadoras enviarem arquivos homônimos,
  a busca no rastreamento devolve o mais recente e registra aviso — pode
  responder à operadora errada. Resolver exige mudar a chave do rastreamento.
- **`_rastreamento.json` cresce indefinidamente.** É reescrito por inteiro a cada
  anexo e varrido linearmente. Com ~1.600 arquivos/mês, é O(n²).
- **O RPA 2 continua sem testes próprios.** O contrato agora está coberto pela
  suíte comum, mas as regras de validação e batimento seguem sem rede.

---

## Adendo 2 — decisões aplicadas (2026-07-31)

13 pendências foram decididas e implementadas. O registro completo está em
[`duvidas-pendentes.md`](duvidas-pendentes.md).

### Validação de layout — a mudança de maior impacto

**Novo:** `comum/dominio/layout_detraf.py`.

Antes, um arquivo com layout diferente passava direto e era lido por posição: o
código pegava o índice 14 achando que era `R$_Bruto` e recebia minutos. Agora o
arquivo é conferido **antes** de qualquer validação linha a linha.

A regra decidida: **posicional**, mínimo de **15 colunas** (as 3 extras da ALGAR
são aceitas), cabeçalho descartado — os nomes reais (`cd_eot_bil`, `mes_ref`) não
batem com os da V2 e variam por operadora. Vale para **os dois** tipos de arquivo.

Além da contagem, confere o **tipo de dado** por posição: EOT nas 1 e 2, `AAAAMM`
nas 3 e 4, `Rel` na 6, descritor com letra na 7, `GH` ∈ {S,R,N,D} na 8, numéricos
nas 9 a 15. Tolera linha ruim isolada — uma posição só reprova quando a maioria
dos valores amostrados falha, o que distingue "arquivo errado" de "arquivo com
sujeira".

🔴 **Consequência operacional:** os arquivos de expectativa Vivo **atuais serão
todos rejeitados**. O RPA 2 registrará `EXPECTATIVA_ERRO` para cada um e **não
haverá comparação nem contestação** até a geração ser corrigida no ICT.

Para que isso seja acionável, o diagnóstico nomeia as posições divergentes e
reconhece o caso:

```
Arquivo [vivo_d_reduzido.csv] rejeitado: layout fora do padrão da V2.
  posição 6 (DESC): esperado descritor (contém letra), encontrado "0" [0/4 válidos]
  posição 7 (GH): esperado S, R, N ou D, encontrado "0" [0/4 válidos]
  posição 8 (Chamadas): esperado número inteiro, encontrado "_NSN5" [0/4 válidos]
  Diagnóstico provável: layout de expectativa Vivo. Ele tem uma coluna a mais no
  início (GROUP_CREDORA) e outra no meio (PARTE_TARIFADA), o que desloca todos os
  campos, e NÃO possui coluna de R$_Bruto — termina em VALOR_LIQUIDO. Como a
  comparação da HU-10 é sobre R$_Bruto, a geração do arquivo precisa ser
  corrigida na origem (ICT).
```

Isso também dissolve a pendência do `R$_Bruto` ausente: se o arquivo precisa
conformar com as 15 colunas da V2, ele tem `R$_Bruto` por definição.

### Nome da tabela de log → o da V2

`tbl_detraf_despesa_arquivos` passou a `tbl_rpa_log_detraf_despesa_arquivos`.

🔴 **Risco registrado:** o nome novo **não existe** em nenhum dos três SQLite que
vieram com os projetos, e não há confirmação de qual existe no MySQL de produção.
Se o banco real usar o antigo, o RPA 1 e o RPA 2 falham ao gravar. **Confirmar
com o DBA antes de subir.**

Para dev, o novo `preparar_banco_dev.py` copia o SQLite do Projeto 2 para
`unificado/banco_de_dados/` e aplica a renomeação — `projetos-origem/` segue
somente leitura.

### Numeração CT — erro em vez de silêncio

`obter_proximo_numero_carta` devolvia `1` quando a pasta não existia ou estava
vazia. Isso reemitiria a carta nº 1 sobre uma sequência já existente sempre que a
pasta estivesse inacessível. Agora **levanta `NumeracaoCartaIndeterminada`**.

Exceção deliberada: em janeiro a pasta do ano é legitimamente nova. Para esse
caso existe `CT_NUMERO_INICIAL` no `.env`, usado **somente** quando a pasta existe
e não tem nenhuma carta — assim o bootstrap nunca acontece por acidente.

### Demais decisões

| Decisão | Situação |
|---|---|
| EC fica no RPA 3 | ✅ já era assim |
| Decisão do analista vem de coluna no banco | ✅ já implementado (`tipo_contestacao`) |
| `CONT_PROC` segue a documentação | ✅ já era assim (colunas nomeadas) |
| Tarifas não reguladas: só formato | ✅ verificado — `__filtrar_tarifas_remuneradas` já filtrava |
| HU-15: rascunho + flag | Registrado; implementar quando o P5 chegar |
| WebFat sai do escopo da HU-03 | Matriz atualizada |
| Sem ambiente de teste | E-mail, AGI e retificação só validáveis com mock |

### Rede de proteção

**+26 testes** — 21 de layout (contra as fixtures reais) e 5 de numeração CT.

**Total: 278 testes passando** (59 base comum · 52 RPA 1 · 167 RPA 3).

### Ainda em aberto

Quatro pendências precisam de detalhamento antes de virar código: **CBS/IBS**
(que afeta diretamente a validação de layout recém-criada), **descritores de
transporte**, **exceções da HU-02** e **nome de operadora que muda**. Mais a
**data de corte**, ainda em análise pela área cliente.

---

## Próximos passos sugeridos

1. **Confirmar o achado A** contra um arquivo de expectativa real — é o que decide se a apuração está correta hoje
2. **Escrever testes de caracterização do RPA 2** antes de qualquer mudança nele
3. **Pedir a pasta `AI/`/`TODO/` do P4** — contém decisões já fechadas com o cliente
4. **Encaminhar as pendências** de `duvidas-pendentes.md` à área cliente
5. Quando P5, P6 e o Épico 5 chegarem: completar o RPA 3, criar o RPA 4 e reavaliar a camada de Outlook (candidato adiado)
