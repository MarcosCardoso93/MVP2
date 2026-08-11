# Conferência das respostas dos anexos contra o código

**Data:** 2026-08-06 · **Origem:** Btime · **Sobre:**
[pendencias-respondidas-pelos-anexos.md](pendencias-respondidas-pelos-anexos.md)

---

## O que este documento é

As respostas extraídas das imagens do `.docx` foram checadas **contra o
repositório**, uma a uma, antes de virar código. Três das "consequências no
código" propostas lá **não se confirmaram** — e uma delas, se aplicada como
escrita, teria quebrado a validação de todo arquivo real.

Isto não desmerece o levantamento: as **respostas** estão certas e fecham três
pendências. O que não bate é a leitura do que elas implicam para este código, que
é um passo separado.

---

# ✅ Aplicado, como proposto

## N10 — `tarifa` é `float` com ponto

**Confirmado e aplicado, com uma ressalva importante.**

O documento diz: *"O ramo que faz `replace(",", ".")` opera sobre um `float` e
deve sair"*. **Só metade dele.** Existem dois `replace` no mesmo trecho, e eles
fazem coisas diferentes:

```python
float(str(tarifa_linha).replace(",", "."))   # ← do ARQUIVO. NECESSÁRIO.
    in [float(str(valor).replace(",", ".")) for valor in tarifa_tabela]
    #        ↑ do BANCO. Morto, e removido.
```

O arquivo da operadora é um CSV em formato brasileiro: a tarifa vem como
`"0,01500"`. **Remover o `replace` desse lado reprovaria todo arquivo real.**

O do lado do banco era código morto — `str(0.00602)` nunca tem vírgula — e do
pior tipo: sugeria uma tolerância que o schema não pede, e mantinha viva a dúvida
sobre qual dos dois formatos valia.

**O teste mudou de sentido.** `test_tarifa_com_virgula_no_banco_quebra`
documentava uma inconsistência sem escolher lado; agora **garante que a leitura
não faz coerção de string**. Se alguém reintroduzir tolerância a vírgula "por
segurança", ele falha — e é o que se quer: essa tolerância esconderia uma tabela
com o tipo errado em vez de acusá-la.

Acrescentado `test_tarifa_do_arquivo_com_virgula_e_aceita`, que fixa o outro
lado — exatamente para que a leitura apressada não seja aplicada depois.

---

## Q22 — o DDL das duas tabelas confirmadas

Registrado em `comum/dados/tabelas.py::DDL_CONFIRMADO`, com os tipos reais.
Serve a duas coisas: o `verificar_ambiente.py` passa a poder dizer **o que está
confirmado e o que ainda é suposição**, e decisões de leitura ganham fundamento —
`tarifa` ser `float` é o que sustentou a N10.

**Conferência feita:** as colunas que o código usa estão **todas** presentes nos
dois DDLs reais. Nenhuma divergência.

Também registradas as cinco tabelas do schema que a V2 não cita
(`TABELAS_NAO_DOCUMENTADAS`), porque uma delas é o núcleo da N1.

---

## Q16 — o formato do CSV de contatos

O print do e-mail real mostrou o que a primeira ponte não daria conta. Aplicado:

```
operadora;para;cc
CLARO;contestacao@claro.com.br,fiscal@claro.com.br;gestor@claro.com.br
TIM;interconexao@tim.com.br;
*;;atacado@exemplo.com.br
```

A linha `*` é a **cópia fixa** — entra em Cc de todos os envios. Duas garantias
que os testes fixam:

- **a cópia fixa nunca vai para o `Para`**, mesmo escrita na coluna `para` da
  linha `*`. A operadora não pode ver um endereço interno da Vivo entre os
  destinatários diretos;
- **só cópia fixa não basta para enviar**. Sem ninguém em `Para` o envio é
  recusado — mandar a contestação só para a cópia interna seria pior do que não
  mandar, porque pareceria enviada.

O formato antigo de uma coluna continua valendo.

---

## A2 — a justificativa da coluna `remuneracao` foi corrigida

O achado está certo e a correção foi aplicada.

A justificativa registrada em 2026-07-28 era *"o sinal pode variar por remuneração
dentro do mesmo par de EOT"*. O print da aba `Contest` real **contradiz**: uma
linha por par de EOT, uma única marca `S`/`N`.

A coluna continua necessária, pelo motivo que a V2 afirma em dois pontos: **o
Encontro de Contas é por remuneração**. A granularidade muda ao longo do fluxo —
a decisão é por par de EOT, o registro no EC é por remuneração.

A consequência prática é a mesma; o argumento a levar ao DBA, não. Corrigido em
`repositorio_tabelas.obter_tipo_contestacao` e em `preparar_banco_dev.py`.

---

# ⚠️ Não se confirmou

## N4 — o código **já estava certo**

O documento conclui: *"Os quatro valores do projeto de origem não entram nesse
enum (…) Isso deixa de ser pergunta e vira correção a fazer."*

**Não há correção a fazer.** Os quatro valores são **parâmetro interno** de
`resultado_validacao.preparar_lote`, e a unificação já os mapeia antes de
qualquer escrita:

| `tipo_lote` (interno) | `tipo_registro` (banco) |
|---|---|
| `DETRAF_SUCESSO` | `DETRAF` |
| `DETRAF_ERRO` | `DETRAF` |
| `EXPECTATIVA_SUCESSO` | `EXPECTATIVA` |
| `EXPECTATIVA_ERRO` | `ERRO` |

O mapeamento bate com a planilha de referência, que define `ERRO` como *"arquivo
de expectativa que não passou pela validação"* — é por isso que `DETRAF_ERRO` vira
`DETRAF`, e não `ERRO`.

A confusão é compreensível: "quatro contra três" parece um a mais. Mas os dois
recortes **não se sobrepõem linha a linha** — um é dimensão × resultado, o outro é
categoria de registro.

**O que foi feito:** `TestEnumDoTipoRegistro` fixa o mapeamento, para que um
quinto tipo de lote sem correspondência seja acusado. E `TIPO_REGISTRO_VALIDOS`
registra o enum fechado em `tabelas.py`.

---

## N3 — a hipótese do cabeçalho não se aplica

O documento sugere: *"Se o arquivo real usa a grafia com espaço e o parser procura
a com underscore, a rejeição não é contradição de especificação — é normalização
de cabeçalho."*

**A validação de layout é posicional e descarta o cabeçalho** antes de olhar
qualquer coisa — decisão do cliente de 2026-07-31, tomada justamente porque os
nomes reais não batem com os da V2 e variam por operadora. Os nomes em `LAYOUT_V2`
são rótulo de mensagem de erro, não critério.

Normalizar `_` e espaço não mudaria nada.

**A N3 continua sendo o que estava registrado**, e é estrutural: o arquivo de
expectativa tem **uma coluna a mais no início** (`GROUP_CREDORA`), **outra no
meio** (`PARTE_TARIFADA`) — o que desloca todos os campos — e **termina em
`VALOR_LIQUIDO`**, sem coluna de valor bruto alguma.

**O que foi feito:** `TestGrafiaDoCabecalhoNaoImporta` fixa que o nome da coluna
não é critério, para que a hipótese não volte.

---

## A1 — real, mas com outro efeito

O documento diz: *"Impacto: validação de tarifa — HU-04"*, dando a entender que
algo quebra.

**O código nunca usou `eot_vivo` nem `eot_operadora`.** `validar_tarifas_na_tabela`
filtra por GH, região, regra e datas. Nada quebrou nem vai quebrar por causa da
ausência das colunas.

**Mas o achado é real, e o efeito tem nome:** a exceção que a própria V2 cita —
**RII (943) × SERCOMTEL (042/043)** — **não tem como ser encontrada**. O par cai
na tarifa da região II e é **reprovado na validação, como se o arquivo estivesse
errado**.

Não é falha de execução; é falso positivo de validação, contra uma operadora
específica. Registrado no docstring de `validar_tarifas_na_tabela` e no
encaminhamento ao DBA: *como a exceção SERCOMTEL está representada nas 127
linhas?*

---

# 🔴 O achado mais importante do lote, e ele é sobre o futuro

## Q6 — a inserção de imposto **desloca** as colunas

Esta não é uma correção; é um risco que o documento tornou explícito e que vale
mais que as três pendências fechadas juntas.

> ¶ item 7 (Risco) — *"Existe a projeção para que em 2028 mais um imposto seja
> inserido na tabela **deslocando as colunas**."*

Nossa validação é **posicional**. Quando CBS/IBS entrarem, eles não vão para o fim
do arquivo — entram no bloco de impostos (posições 13-14) e empurram `R$_Bruto`
para a direita.

**E o modo de falha é o pior possível:** toda leitura por índice fixo passa a ler
a coluna errada, e **continua lendo um número**. O `_eh_numero` aprova, a
validação passa, e a apuração usa ICMS onde deveria usar valor bruto. Nada acusa.

`COLUNAS_MINIMAS` não protege — extras à direita são aceitas de propósito (a ALGAR
entrega 18 colunas hoje).

**O que isso pede** — e que não dá para decidir antes de a Q6 ser respondida: ou
casar por cabeçalho quando ele existir, ou uma constante de versão de layout por
período de tráfego.

Registrado em `comum/dominio/layout_detraf.py` e nos riscos conhecidos.

---

# Saldo

| Pendência | Estado |
|---|---|
| **N10** | ✅ fechada — código ajustado, teste com sentido novo |
| **N4** | ✅ fechada — **sem mudança de código**, mapeamento fixado em teste |
| **Q13** | ✅ fechada — comportamento já era o certo |
| **Q22** | 🟡 encolheu: faltam 2 DDLs, não 4 |
| **N1** | 🟡 mudou de forma: qual das duas tabelas o WebFat lê? |
| **N3** | 🔴 continua aberta — a hipótese barata não se aplica |
| **Q16** | 🟡 ponte melhorada; a tabela definitiva continua sendo pergunta |
| **Q16b** | 🟡 encolheu: faltam 2 casos, não 4 |
| **Q17** | 🟡 caminho técnico proposto (`ID Processo`) |
| **Q6** | 🔴 aberta, e agora com **risco datado** (2028) |
| **A1** | 🔴 novo — exceção SERCOMTEL não expressável |
| **A2** | ✅ justificativa corrigida |
| **A3** | 🟡 novo — entra no R20 |

**Três fecham** (N10, N4, Q13). **Contando os três achados novos, a lista vai de
15 para 15** — o que sai em número entra em qualidade: as que ficam estão melhor
delimitadas, e o pedido ao DBA caiu de quatro DDLs para dois mais duas perguntas
pontuais.

**685 testes, quatro suítes verdes.**
