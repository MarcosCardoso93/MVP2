# Checklist — Análise de Código

Aplicar a **cada projeto**, na ordem **P1 → P2 → P3 → P4 → P7 → P5 → P6**. Marco **M2**.

**Regra:** esta análise é de **leitura**. Nada em `projetos-origem/` é alterado. As saídas vão para `trabalho/inventarios/`.

Preencher o template [`../05-proxima-etapa/templates/inventario-por-projeto.md`](../05-proxima-etapa/templates/inventario-por-projeto.md) conforme avança.

---

## 1. Estrutura e execução

- [ ] Árvore de diretórios mapeada
- [ ] Ponto de entrada e fluxo principal traçados do início ao fim
- [ ] Granularidade de execução identificada: por arquivo? por operadora? por lote mensal?
- [ ] Existe paralelismo? Concorrência? Trava de execução?
- [ ] O processo acumula estado em memória ao longo de todas as operadoras? ⚠️ Se sim, processar uma operadora isoladamente pode não ser possível — afeta reprocessamento
- [ ] Ordem de execução dos passos registrada

---

## 2. Mapeamento código → HU

Para **cada HU** que o projeto deveria cobrir:

- [ ] Localizado o código que a implementa (arquivo e linha)
- [ ] Registrado se está **implementada / parcial / ausente**
- [ ] Registrado se implementa a **V1 ou a V2** da regra — ver seção 3

E o inverso, que é onde estão as surpresas:

- [ ] Todo código foi atribuído a **alguma** HU
- [ ] Código que não corresponde a nenhuma HU foi registrado: é escopo extra, código morto, ou HU não documentada?

---

## 3. 🔴 Versão da regra implementada

**A verificação mais importante desta fase.** Cinco HUs mudaram estruturalmente entre V1 e V2. Código escrito antes da V2 implementa regra revogada — e migrá-lo como está carrega o erro para o repositório novo.

### HU-02 — identificação da operadora (P1)
- [ ] O código identifica a operadora pelo **domínio do remetente** do e-mail? → **V1, revogada**
- [ ] Ou pela **EOT da Credora buscada no Anexo 5** (coluna nome fantasia)? → **V2, correta**
- [ ] O código **abre o anexo** antes de decidir onde salvar? (consequência necessária da V2)

### HU-07 — erro L-L (P2)
- [ ] Existe caminho de tratamento **dedicado** ao caso L-L/STFC? → **V1** — candidato a eliminação
- [ ] Ou o caso cai na **regra geral de `_ERRO`**? → **V2**

### HU-09 / HU-10 — Base Contestação (P3)
- [ ] O código gera o **arquivo** `Base_Contestação` com abas e tabelas dinâmicas? → **V1**
- [ ] Ou popula **`tbl_rpa_log_detraf_despesa_contestacao`**? → **V2**
- [ ] Ou **ambos**? ⚠️ Ver seção 3.1

### HU-19 — Encontro de Contas (P4)
- [ ] O código escreve na **planilha** de Encontro de Contas? → **V1**
- [ ] Ou nos campos `minutos_operadora`, `vb_operadora`, `minutos_diferenca`, `vb_diferenca`, `minutos_variacao_perc`, `vb_variacao_perc`? → **V2**

### 3.1 Caso "ambos" — a contradição `_ENV` × `Base_Contestação`
- [ ] Se o P3 gera **e** o arquivo **e** o banco, verificar no P4: o `_ENV` é montado a partir do **arquivo** ou do **banco**?
- [ ] Isso responde à pendência de qual é uma das "duas exceções" da frase *"todas as planilhas foram substituídas por banco, exceto dois arquivos"*

**Registrar cada resposta.** Uma implementação V1 numa HU 🔴 não é migração — é retrabalho, e precisa ser dimensionada à parte.

---

## 4. Pontos de entrada e saída (I/O)

Mapear **todo** contato com o mundo externo:

### E-mail (Outlook)
- [ ] Lê? Qual caixa, quais filtros
- [ ] Move e-mails entre pastas?
- [ ] Envia? Para quem, com que anexos
- [ ] Que biblioteca/mecanismo usa (COM, `win32com`, outro)

### Sistema de arquivos
- [ ] Que caminhos lê e escreve
- [ ] **Como os caminhos são construídos** — concatenação inline, função dedicada, configuração? ⚠️ Item de alto valor: é o contrato implícito entre RPAs
- [ ] Que convenções de nome aplica (`_D_`, `_BK`, `_ERRO`, `_ENV`, `_EXT`, `_INT`)
- [ ] Cria estrutura de pastas? Copia do mês anterior?
- [ ] Toca o servidor do WebFat, além do Lagoa?

### Banco de dados
- [ ] Que tabelas lê e escreve
- [ ] **Que campos** — comparar com a lista conhecida; campos não documentados são achado
- [ ] Como a conexão é obtida
- [ ] Usa transação? Como trata falha no meio da escrita?

### AGI
- [ ] Que telas navega
- [ ] Que biblioteca de automação de UI usa
- [ ] Como trata o login no autenticador
- [ ] Como sabe que a operação teve sucesso? ⚠️ Confirmação de upload é ponto crítico

### Anexo 5
- [ ] De onde vem — arquivo local, download, banco?
- [ ] Como é atualizado?
- [ ] Que colunas consulta

---

## 5. Regras de negócio implementadas

Para cada regra encontrada, registrar **onde está** e **se confere com a V2**:

- [ ] Layout das 15 colunas — validação por posição fixa ou por cabeçalho? ⚠️ Ver seção 7
- [ ] Aceita arquivo **sem cabeçalho**?
- [ ] **Ignora aba de resumo**?
- [ ] Exclui linhas com `Rel = 1` nas consolidações?
- [ ] Trata coluna `Rel` **vazia**?
- [ ] Regras de descritor (início/final, SMP/STFC)
- [ ] Regra do `_BK` (L…V, SMP, não-PMS) — **recalcula a linha de total?** ⚠️ conflito entre fontes
- [ ] Consulta de tarifa: quais campos usa na chave
- [ ] **Dupla convivência de tarifas em fevereiro** — implementada?
- [ ] Regra do horário reduzido da VU-M (tipo de serviço da **Devedora**)
- [ ] Rejeita **tarifa zero**?
- [ ] **Regra da variação:** qual limiar, qual sinal, qual base de cálculo? ⚠️ Registrar literalmente o que o código faz — é a pendência mais impactante
- [ ] Regra de expectativa ausente → valores zerados
- [ ] Exceção Bill&Keep (ambas EOTs SMP)
- [ ] Sumarização STFC numa única linha (EOTs 011, 200, 9\*\*)
- [ ] Campos fixos de `_EXT` e `_INT` (ORIGEM, EXPECTATIVA, INSERÇÃO)
- [ ] Colunas do `CONT_PROC` e a regra de não sumarizar remunerações diferentes
- [ ] Numeração CT sequencial — **como lê e incrementa?** ⚠️ há trava?
- [ ] Fator `0,9635` da retificação

---

## 6. Tratamento de erro e logging

- [ ] Como trata exceção — captura, propaga, ignora?
- [ ] O comportamento da V2 ("o robô seguirá para o próximo processamento") está implementado?
- [ ] Existe estado persistido que permita **retomar** de onde parou?
- [ ] O que registra em log, em que formato, para onde
- [ ] Como o erro chega ao WebFat (alerta vermelho, sem detalhamento)
- [ ] Distingue erro do arquivo **da operadora** (aciona a operadora) de erro do arquivo **de expectativa** (WebFat)?
- [ ] Há alguma implementação de "correção automática" de expectativa? ⚠️ A regra não está definida na V2 — se existe código, é decisão não documentada

---

## 7. 🔴 Aderência às premissas da V2

As premissas 10.3/10.4 exigem regras e tabelas **editáveis pelo usuário**. O risco de 2028 exige layout **não posicional-fixo**.

- [ ] Há **valores de tarifa** constantes no código? → violação
- [ ] Há **mapeamento descritor → remuneração** constante no código? → violação
- [ ] Há **limiares** (1%, 0,9635) constantes no código? → violação
- [ ] Há **índices de coluna** fixos na leitura dos arquivos? → violação do requisito de layout dinâmico
- [ ] Há **EOTs da Vivo** (011, 200, 9\*\*) constantes? → registrar
- [ ] Há **caminhos de rede** constantes no código? → registrar

Cada violação é **dívida técnica a registrar**, não comportamento a replicar — mas também **não se corrige durante a migração**. Ver [`../02-planejamento/estrategia-de-migracao.md`](../02-planejamento/estrategia-de-migracao.md).

---

## 8. Candidatos a componente compartilhado

- [ ] Todo trecho que pareça reutilizável foi registrado numa [ficha de candidato](../05-proxima-etapa/templates/ficha-de-componente-candidato.md)
- [ ] Cada ficha tem **arquivo e linha** da ocorrência
- [ ] A partir do segundo projeto: cada candidato foi confrontado com os já registrados

⚠️ **Não promova nada nesta fase.** A promoção é F3. Aqui só se registra.

---

## 9. Duplicações

A partir do **segundo** projeto analisado:

- [ ] Todo trecho com responsabilidade equivalente a algo já visto foi registrado
- [ ] Cada par recebeu veredicto: IDÊNTICO / EQUIVALENTE-PARAMETRIZÁVEL / DIVERGENTE / FALSO PAR
- [ ] Os **casos de borda** foram comparados, não só o caminho feliz
- [ ] Toda divergência foi sub-classificada: VERSÃO / INTERPRETAÇÃO / DEFEITO

Critérios em [`../02-planejamento/criterios-de-unificacao.md`](../02-planejamento/criterios-de-unificacao.md).

---

## 10. Qualidade e testabilidade

- [ ] Existem testes? Cobrem o quê?
- [ ] O código é executável sem acesso a produção?
- [ ] Há acoplamento que impeça testar uma regra isoladamente?
- [ ] Há código morto?
- [ ] Há dependência de estado de máquina (caminho absoluto, registro do Windows, sessão aberta)?

---

## 11. Achados a escalar imediatamente

Não esperar o fim da análise:

- [ ] 🔴 Credencial exposta
- [ ] 🔴 HU esperada **não implementada**
- [ ] 🔴 Código do fluxo de **Receita** (fora de escopo deste MVP)
- [ ] 🔴 Comportamento que contradiz a V2 em regra financeira (limiar, sinal, base de cálculo)
- [ ] 🔴 Ausência de qualquer forma de testar sem tocar produção

---

## Gate para F3

O projeto está analisado quando:

- [ ] Inventário completo em `trabalho/inventarios/`
- [ ] Toda HU esperada rastreada a código ou marcada como ausente
- [ ] Todo código atribuído a uma HU ou classificado como extra/morto
- [ ] Versão da regra (V1/V2) registrada para todas as HUs 🔴
- [ ] Candidatos e duplicações registrados com arquivo e linha
- [ ] Achados críticos escalados
