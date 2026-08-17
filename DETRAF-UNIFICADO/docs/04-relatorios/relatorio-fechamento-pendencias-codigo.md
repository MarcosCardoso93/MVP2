# Relatório — Fechamento das pendências de código

**Data:** 2026-08-04 · **Escopo:** tudo o que não depende de resposta do cliente
nem de projeto não entregue

---

## Ponto de partida

Os Projetos 1 a 5 e 7 estavam unificados e 345 testes passavam — mas **nenhum RPA
produzia o resultado final**. O RPA 3 não encadeava nada, o RPA 2 não tinha um
único teste, e havia defeitos ativos que faziam o robô reportar sucesso em cima de
falha.

Ao final: **506 testes**, as quatro suítes verdes, e os três robôs executando o
fluxo ponta a ponta.

| Suíte | Antes | Depois |
|---|---|---|
| base comum | 94 | 119 |
| RPA 1 — captura | 52 | 52 |
| RPA 2 — validação e apuração | **0** | **103** |
| RPA 3 — contestação | 199 | 232 |

---

## 🔧 Três coisas que eu tinha registrado errado

### 1. A evidência por screenshot não tem fonte na V2

Eu atribuí a captura de tela ao "V2, item 4.7.3" no relatório dos Projetos 5 e 7,
no README e no docstring do serviço. A citação veio dos comentários do próprio
Projeto 7 e **não resolve**: não existe item 4.7.3, e as palavras *evidência*,
*print*, *screenshot* e *comprovante* não ocorrem no documento.

O que a V2 exige como confirmação de carga é outra coisa — e não estava feita.

> ⚠️ **O argumento original estava errado (corrigido em 2026-08-05).** Esta seção
> dizia que "a V2 usa numeração automática do Word, então não há números de item
> no texto". Há: ¶84 "item 3.3", ¶136 "vide item 10.8", ¶637 "5.4.6.4.3.6". A
> conclusão se sustenta pelo motivo simples — **aquele item não existe e não há
> texto sobre print** —, não pela ausência de numeração.

### 2. A carta da HU-14 não estava bloqueada — **e esta correção foi longe demais**

`unificado/README.md` e `rpa3/main.py` diziam que "o preenchimento do modelo
`.docx` está bloqueado". `CAMINHO_MODELO_CARTA` e `CAMINHO_MASCARA_CONT_PROC`
eram, de fato, **declaradas e nenhum módulo as lia** — e foram removidas.

> 🔴 **Mas a conclusão que tirei disso estava errada (2026-08-05).** Eu escrevi
> que a carta "não depende de modelo externo, ao contrário do que este arquivo
> afirmava", como se a V2 nunca tivesse exigido modelo. **Ela exige**, no ¶601:
> *"a carta da operadora a partir de um modelo pré-existente para cada
> operadora"*.
>
> O que eu verifiquei era verdade sobre o **código**; concluí daí algo sobre a
> **documentação**, que é outra fonte. Respondi *"o que a V2 exige?"* com *"o que
> o código faz"* — e apaguei um marcador de requisito por causa disso.
>
> O mérito ficou resolvido pelo cliente em 2026-08-04: **modelo único para todas
> as operadoras** (Q26). O código está certo; o que faltava era registrar a
> divergência em vez de negá-la.

### 3. 🐛 O CONT_PROC nunca seria encontrado — defeito meu

- HU-16 grava em `caminho_agi` (`geracao_cont_proc.py:263`)
- HU-18 procurava em `caminho_contestacoes` (`upload_contestacao_agi.py:69`)

Eu escrevi o uploader na rodada anterior e apontei para a pasta errada. Ninguém
percebeu porque nada encadeava as duas HUs — e o teste repetia a mesma suposição
errada, então passava.

Agora existe um teste que **roda a HU-16 de verdade** e afirma que a HU-18 encontra
o que ela gravou. Amarrar as duas pontas é o que impede a divergência de voltar.

---

## Falha tem que parecer falha

Um defeito de uma classe só, em cinco lugares: **o robô concluía com sucesso em
cima de uma falha.**

| Onde | O que fazia |
|---|---|
| `limpeza_trafegos.executar` | `except` logava e caía num `return True` no fim — o Detraf seguia para a validação como se estivesse íntegro |
| `resultado_validacao._extrair_dados_internos` | falha de I/O gravava no banco com minutos e valor **zerados**, e marcava o arquivo como processado. Zero é resultado legítimo de operadora sem tráfego — os dois casos ficavam indistinguíveis |
| `historico._carregar_json` | JSON corrompido devolvia `{}` **sem log**. O histórico é a proteção anti-reprocessamento: o robô refazia o mês inteiro |
| `outlook._build_attachments` | `pass` engolia falha na enumeração e devolvia lista **parcial** — um anexo podia sumir sem rastro |
| `CAMINHO_EXPECTATIVA_DETRAF` | era `Path(".")` quando não configurada, e a guarda `exists()`/`is_dir()` passava: o robô varria o CWD e a validação virava no-op |

O arquivo de histórico corrompido agora é **preservado com sufixo**, não
sobrescrito: ele é o registro de auditoria do que já tinha sido processado, e
pode ser a única pista de por que o mês foi refeito.

---

## O log passou a servir para diagnosticar

| Item | Era | É |
|---|---|---|
| Caminho | relativo ao CWD → **três** árvores de log no disco | `RAIZ_LOGS` absoluta |
| Arquivo | um por dia, os três robôs juntos | um por robô (`NOME_RPA`) |
| Data | congelada **no import** | placeholders do loguru, por escrita |
| Retenção | **7 dias** | 90, configurável |
| Traceback | **nenhum** dos ~70 `except` gravava | `logger.excecao` nos que engolem — hoje 20 usos |
| `diagnose` | `True` fixo — gravava variáveis locais, inclusive senha | segue o `ENV` |

Os `except` que **re-levantam** ficaram como estavam: quem captura acima é que
decide, e `raise ... from erro` já preserva a cadeia.

*(Contagens corrigidas em 2026-08-05: são 73 blocos `except` e 20 usos de
traceback, não 65 e 11.)*

---

## A orquestração do RPA 3

`gerar_artefatos()` emitia sete `logger.info` de "etapa pendente". Eram **2.276
linhas de service implementado e testado sem chamador** — os Projetos 4, 5 e 7 não
produziam nada em execução.

A ordem vem da V2. Por operadora: consolidação → HU-19 → EXT → INT → `_ENV`/carta
→ CONT_PROC. Depois, para o lote inteiro: `Detraf > Importar Dados` e
`Contestação > Gerenciar`.

**Diante de etapa bloqueada, pula com aviso e segue** — o mês tem dezenas de
operadoras. Duas exceções desabilitam a etapa para a execução inteira: a numeração
CT (global e serial: insistir arriscaria duplicar número) e o índice de remuneração
(pré-condição de tudo).

### Dois achados que só apareceram ao ligar as peças

- **Sem expectativa Vivo, o `_ENV` estourava** com *"single positional indexer is
  out-of-bounds"* no meio da HU-14. Agora degrada: o EXT sai (só depende do lado da
  operadora), o `_ENV` e a carta não, com aviso.
- **`gerar_arquivo_ext` não tem guarda de vazio**, ao contrário do
  INT/`_ENV`/CONT_PROC. Sem o short-circuit da operadora sem Detraf, ele gravaria
  um `.xlsx` vazio que a HU-17 tentaria subir no AGI.

---

## A suíte do RPA 2

Era a maior dívida da unificação: a pasta `tests/` **não existia**. 103 testes
cobrindo as 15 colunas uma a uma, a tarifa contra a tabela regulada, a limpeza de
tráfegos, a varredura de arquivos e a notificação.

> 🔴 **Correção (2026-08-05).** Esta frase dizia também "e a consolidação no
> banco". **Não cobria:** `criacao_arquivo_contestacao.py` (554 linhas, HU-09 e
> HU-10) não tinha um único teste, e nenhum arquivo de teste o mencionava. A
> auditoria encontrou a lacuna, e os 20 testes escritos em seguida revelaram que
> **a HU-09/HU-10 não executava** — chamava `obter_tipo_produto_por_poi`, um
> método que a unificação deliberadamente não migrou. Ver
> `relatorio-auditoria-das-pendencias.md`.

Cada teste de coluna altera **uma** posição da linha válida — se dois campos
mudassem juntos, a reprovação não diria qual regra quebrou.

### Achados

- **A tarifa é lida com `.astype(float)`**, que exige ponto decimal, enquanto a
  comparação seguinte **no mesmo fluxo** faz `replace(",", ".")`. Uma metade assume
  um formato e a outra tolera o outro. Como o formato real da coluna nunca foi
  confirmado, o teste **fixa o comportamento atual** em vez de escolher um lado —
  registrado como pendência **N10** (era "N8", renumerada).
- **"Arquivos vazios são ignorados"** no docstring de
  `_mapear_arquivos_por_operadora` só vale para o arquivo que abre e resulta num
  DataFrame vazio. Um de 0 byte não abre: vai para `OPERADORA_NAO_IDENTIFICADA` —
  que por sinal é o melhor dos dois, porque ignorar em silêncio faria o arquivo
  sumir sem ninguém saber.

Só **depois** da cobertura o RPA 2 passou a usar `listar_operadoras_do_mes` de
`comum/`: refatorar 695 linhas sem teste era o risco que a suíte remove.

---

## Requisito da V2 que não estava implementado

> "O robô atualiza o campo 'carga_agi' com o o status da carga na tabela
> 'tbl_rpa_log_detraf_despesa_contestacao' do banco webfat."

Não existia método para isso. O RPA 2 gravava `"não carregado"` ao criar a linha e
ninguém tocava no campo depois — o WebFat nunca soube que a carga aconteceu.

A granularidade é **operadora × referência**, não a chave de negócio que as outras
escritas usam: quem chama é o uploader, e ele só conhece o arquivo — que é um
CONT_PROC por operadora e mês, contendo todas as linhas contestadas dela.

Grava também no fracasso (`"erro na carga"`): deixar `"não carregado"` faria a
falha parecer uma execução que nunca aconteceu.

---

## Pendências novas registradas

| # | O quê | Decide |
|---|---|---|
| **Q25** | Carta com cenários mistos (COM e SEM retenção na mesma operadora). Adotado "prevalece COM retenção" com aviso — é o conservador, mas é escolha nossa | PO |
| **N9** | De-para oficial de `codigo_erro` (era "N7" — colidia com uma pendência já decidida) | PO |
| **N10** | Formato decimal da coluna `tarifa` no banco (era "N8") | DBA |

E a **Q16 subiu para 🔴**: a busca na documentação mostrou que a "tabela de
contatos do WebFat" **não ocorre uma única vez na V2**. O nome vem da V1, que a
usava na HU-02 — uso que a V2 eliminou, trocando por EOT credora × Anexo 5. Não há
como saber, pela documentação, se a tabela existe.

---

## Verificação

| Critério | Resultado |
|---|---|
| `python executar_testes.py` | ✅ 506 testes, quatro suítes verdes |
| RPA 2 deixa de reportar "sem testes" | ✅ 103 |
| A HU-18 encontra o CONT_PROC que a HU-16 gravou | ✅ coberto por teste que roda as duas |
| Kill-switches desligados não tocam AGI nem Outlook | ✅ provado por dublê que explode ao primeiro toque |
| `carga_agi` sai de "não carregado" após o upload | ✅ |
| Log com traceback em arquivo, um por robô | ✅ verificado em subprocesso |
| Os três `main.py` carregam com `.env` vazio | ✅ |
| `projetos-origem/` intocada | ✅ |
| Credencial em código ou `.env.example` | ✅ nenhuma |

---

## O que continua fora

**Bloqueado no cliente:** Q1 (data de corte), Q6 (CBS/IBS), Q12 (descritores de
transporte), Q16 (contatos), Q22/N8 (DDL e formato da tarifa), Q25 (cenário misto).

**Projeto não entregue:** HU-20, HU-21 e o RPA 4 inteiro dependem do Projeto 6.

**Sem ambiente:** as imagens do AGI vieram da VM de Receita e nunca foram
validadas na de Despesa; a HU-18 nunca executou contra o AGI. Não há ambiente de
teste (Q20) — é por isso que `PERMITIR_UPLOAD_AGI` importa tanto.
