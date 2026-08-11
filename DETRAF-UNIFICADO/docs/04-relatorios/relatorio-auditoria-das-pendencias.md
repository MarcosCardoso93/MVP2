# Relatório — Auditoria das pendências

**Data:** 2026-08-05 · **Motivo:** conferir, contra a documentação-fonte e contra
o código atual, se as pendências registradas estão corretas.

---

## O que a auditoria era

Não uma revisão de código: uma conferência de **veracidade**. Cada pendência foi
reaberta e comparada com o que a V2 realmente diz, e cada afirmação sobre o
código foi executada contra o código.

O resultado justifica a rodada: **a HU-09/HU-10 não executava**, e o relatório
anterior afirmava que ela estava coberta por testes.

---

## 🔴 O defeito que a auditoria encontrou

`criacao_arquivo_contestacao.py` — 554 linhas, HU-09 e HU-10, **zero testes**.
Nenhum arquivo do repositório o mencionava. E o relatório de fechamento afirmava
que os 103 testes do RPA 2 cobriam "a consolidação no banco".

Ao escrever os testes que faltavam, dois defeitos apareceram no primeiro minuto:

### 1. Chamada para um método que não existe

```python
bd_tabelas.obter_tipo_produto_por_poi(poi)   # AttributeError
```

A unificação **deliberadamente não migrou** esse método do Projeto 3 — ele lia a
coluna POI e tratava o valor como descritor, e o próprio
`repositorio_tabelas.py` registra isso no docstring. O chamador ficou para trás.

**Consequência:** toda execução real da HU-09/HU-10 estourava. Sem a tabela de
contestação, o RPA 3 nunca receberia linha nenhuma — a orquestração que ligamos
na rodada anterior rodaria em cima de um banco vazio.

A fonte certa é a que a V2 nomeia (¶195): *"A identificação da Remuneração
regulada (…) deve ser baseada no campo DESC (descritor) **ou 7ª coluna**"*. E
`classificar_descritor_remuneracao` já implementa exatamente isso — é o que os
outros dois módulos do mesmo RPA usam.

### 2. `tipo_servico_vivo` recebia o tipo de serviço da operadora

A coluna era preenchida com `tipo_operacao`, derivado da **Credora**. Pela V2, a
Credora é a **operadora**; a Vivo é a Devedora.

A prova de que estava errado é interna ao próprio RPA 2:
`resultado_validacao.py` preenche a **mesma coluna** a partir da Devedora. Dois
módulos do mesmo robô gravavam lados opostos.

A raiz dos dois defeitos é a mesma: o docstring de
`_preparar_dados_persistencia_contestacao` afirmava a convenção **invertida** —
"Credora = EOT Vivo, Devedora = EOT da operadora". A V2 diz o contrário, e
`validacao_colunas` concorda (valida a coluna de índice 1 contra os nomes
fantasia da Vivo). Os EOTs sempre estiveram certos; a explicação é que estava
trocada, e quem leu o docstring para escrever o resto se guiou por ela.

---

## As duas decisões do cliente

| # | Pergunta | Decisão |
|---|---|---|
| **Q4** | O `_ENV` vem do arquivo `Base_Contestação` ou do banco? | **A base de contestação é uma tabela** |
| **Q26** | A carta sai de um modelo por operadora? | **Modelo único para todas** |

A Q4 **confirma a V2**, que dizia (¶445): *"Não é necessário gerar o arquivo, mas
usar a lógica e popular a tabela"*. O RPA 2 gravava um `.xlsx` de cinco abas que
**ninguém lia** — o `_ENV` do RPA 3 é montado de DataFrames, não daquele arquivo.
Removido.

A Q26 **supera a V2** (¶601: *"um modelo pré-existente para cada operadora"*).

---

## 🔴 Onde eu errei

### Inverti a hierarquia de fontes

Na rodada anterior eu "corrigi" o repositório afirmando que **a carta não depende
de modelo externo, ao contrário do que este arquivo afirmava**. Verifiquei que
`CAMINHO_MODELO_CARTA` estava declarada e ninguém a lia — verdade sobre o
**código** — e conclui daí algo sobre a **documentação**. A V2 exigia o modelo.

Respondi *"o que a V2 exige?"* com *"o que o código faz"*, e apaguei um marcador
de requisito por causa disso. Pelo mesmo motivo, a **Q4 estava marcada como
"respondida pelo código"** quando o código fazia o oposto do documento.

Q10 e Q11 têm o mesmo vício, mais brando: as conclusões estão certas, as
justificativas não — a Q9 é respondida pela V2 (¶182), a Q10 pela V1, e a Q11 é
erro de redação que **só o PO confirma**, porque é dado financeiro carregado no
AGI.

### Três outras afirmações que não se sustentavam

| Afirmei | Realidade |
|---|---|
| "os 103 testes cobrem a consolidação no banco" | não cobriam — ver acima |
| "a V2 não tem números de item, por isso o 4.7.3 não resolve" | a V2 **tem** (¶84 "item 3.3", ¶136 "item 10.8", ¶637 "5.4.6.4.3.6"). A conclusão vale pelo motivo simples: aquele item não existe, e não há texto sobre print |
| "as variáveis de configuração órfãs foram zeradas" | sobravam `HOSTNAME`, `ANO_REFERENCIA` e `NOME_FANTASIA_VIVO` |

Contagens erradas: **73** blocos `except` (eu disse 65) e **20** usos de
traceback (eu disse 11).

E um defeito da mesma classe que declarei ter eliminado: `historico.py` devolvia
**zero sem log** quando não conseguia contar as linhas de um arquivo. Zero linhas
é resultado legítimo — os dois casos ficavam indistinguíveis no histórico.

---

## Um diagnóstico que estava incompleto

`NOME_FANTASIA_VIVO` aparecia como "variável órfã, remover". Olhando o outro
lado, era o inverso: a lista `["Vivo", "Telefônica"]` estava **embutida em dois
pontos** de `validacao_colunas.py`, com o comentário *"Adicionar aqui caso haja
outros"*. Configurar exigiria editar o fonte, em dois lugares — e a Q17 (nome de
operadora que muda) vive exatamente nesse território.

A variável passou a ser usada, com aquela lista como default.

---

## Pendências revistas

**Reabertas:** **Q4** (agora resolvida pelo cliente) e **Q14** — o
`DE_EBT_..._MODELO` estava marcado "ignorar", e é **a única alteração que a V2 fez
no passo de carga**: a linha existe no texto vigente e não no bloco antigo.

**Corrigida:** a "Fonte" da **Q5** era falsa — dizia que a frase sobre envio
automático sobrevive no bloco antigo da V2; ela é da V1.

**Colisão de número:** havia **duas N7**. A de `codigo_erro` virou **N9**, e a do
formato da tarifa virou **N10**.

**Severidade revista:** Q20 sobe para 🔴 (o ambiente de teste não existe — deixou
de ser incerteza), Q24 sobe para 🟡 (o bloco duplicado **não é duplicata pura**:
tem uma regra sem contrapartida no texto vigente), Q13/Q21/Q23 saem de "ignorar",
N9 desce para 🟢 (a V2 pede erro *"sem detalhamento"*), e a parte da Q16 sobre
exceções da HU-02 desce para 🟢 — a V2 dá regra genérica; só os destinatários da
HU-15 ficam sem resposta.

**Reescritas:** a **Q6** ficou mais respondível (a V2 aponta a fonte do layout,
"isnumos", e diz que os impostos são informativos até 2027); a **N3** ganhou
fundamento textual (a V2 afirma **duas vezes** que a expectativa tem `R$ Bruto` —
é contradição com a realidade, não ambiguidade); e a **Q12** teve uma
sub-pergunta remarcada como hipótese nossa, não leitura da fonte.

---

## Varredura documental

Doze documentos descreviam estado que já mudou. Os de `docs/01-entendimento/` e
`docs/02-planejamento/` ganharam **nota de corte** — são fotografia da etapa
documental e não diziam isso; três deles afirmavam que o Épico 5 não tem projeto.

Corrigidos por contradizerem o código atual: o painel de controle do
`duvidas-pendentes.md` (congelado em 2026-07-31, contradizia o cabeçalho do
próprio arquivo em doze linhas), o inventário do P4 ("carta bloqueada"), o do P7
("`carga_agi` sem método"), o relatório dos P5/P7 ("orquestração continua stub",
"RPA 2 sem suíte"), a tabela de achados da matriz (contradizia a linha 7 do mesmo
arquivo) e o diagrama do README (omitia `rpa2_validacao_apuracao/tests/`).

`riscos-conhecidos.md` nunca tinha sido tocado desde a etapa documental e ganhou
tabela de status: **R6 e R18 fechados**, **R20 já aconteceu** (não é mais risco, é
achado com rotação pendente), **R4 e R5 confirmados** (deixaram de ser
probabilidade), **R1 e R13 mitigados**.

Contagens corrigidas: 19 candidatos (não 18), 17 módulos na base comum (não 16).

---

## Verificação

| Critério | Resultado |
|---|---|
| `python executar_testes.py` | ✅ **530 testes**, quatro suítes verdes |
| HU-09/HU-10 executa | ✅ 20 testes novos, dois defeitos corrigidos |
| Nenhum `Base_Contestação` é gravado | ✅ a exportação foi removida |
| Variáveis de configuração órfãs | ✅ nenhuma |
| `projetos-origem/` intocada | ✅ |
| Credencial em código ou `.env.example` | ✅ nenhuma |

---

## O que fica

**Bloqueado no cliente:** Q1 (data de corte), Q6 (CBS/IBS — peça o "isnumos"),
Q12 (descritores de transporte), **Q14** (o `DE_EBT_..._MODELO`, reaberta), Q16
(destinatários da HU-15), Q22/N10 (DDL e formato da tarifa), Q24 (o requisito que
só existe no bloco antigo), Q25 (carta com cenário misto).

**Projeto não entregue:** HU-20, HU-21 e o RPA 4 dependem do Projeto 6.

**Sem ambiente:** a HU-18 nunca executou contra o AGI, e as imagens vieram da VM
de Receita. Não há ambiente de teste (Q20) — confirmado, não mais suposto.

**Limitação registrada e não corrigida:** `_converter_coluna_numerica` transforma
`"1.234,56"` em **zero**, em silêncio. A V2 não define separador de milhar, então
aceitar seria assumir convenção que o documento não dá. A proteção é a validação
de colunas, que reprova o arquivo antes.
