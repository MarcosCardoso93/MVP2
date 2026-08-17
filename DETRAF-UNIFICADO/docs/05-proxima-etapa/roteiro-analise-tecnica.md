# Roteiro da Análise Técnica

**Este é o documento de entrada da próxima etapa.** Ele assume que a documentação já foi analisada (etapa anterior) e que os códigos estão sendo inseridos em `projetos-origem/`.

Se você é uma IA ou pessoa começando agora: leia este documento, depois [`../01-entendimento/mapa-projetos-epicos-historias-rpas.md`](../01-entendimento/mapa-projetos-epicos-historias-rpas.md) e [`../01-entendimento/regras-de-negocio-consolidadas.md`](../01-entendimento/regras-de-negocio-consolidadas.md). Com esses três, você tem o suficiente para começar.

---

## Regras da fase

1. **`projetos-origem/` é somente leitura.** Nada é alterado, movido ou excluído.
2. **Todas as saídas vão para `trabalho/inventarios/`.**
3. **Nada é decidido sobre arquitetura ainda.** Esta fase produz o inventário; o desenho é a fase seguinte.
4. **Nenhuma suposição silenciosa.** Toda dúvida vira item registrado.
5. **A V2 é normativa.** Onde o código implementa a V1, isso é divergência a registrar, não comportamento a preservar.

---

## Ordem de análise

```
P1 → P2 → P3 → P4 → P7 → P5 → P6
```

**Por que esta ordem:**

- **Segue o fluxo de dados.** Cada projeto é lido já sabendo o que o anterior produziu. Fronteiras e duplicações aparecem por comparação, não por busca.
- **P4 antes de P7** porque é a análise do P4 que responde se o Épico 5 está lá dentro.
- **P5 e P6 por último** porque são pequenos e servem de **teste de confirmação** dos candidatos a componente compartilhado. O P5 tem uma única HU de e-mail; se a camada de e-mail identificada nos projetos anteriores não servir a ele, a abstração está errada. Mesmo raciocínio para o P6 e a automação do AGI.

---

## Passo 0 — Antes de abrir qualquer código

Por projeto, ao recebê-lo:

1. Aplicar [`../03-checklists/checklist-insercao-dos-codigos.md`](../03-checklists/checklist-insercao-dos-codigos.md)
2. Salvar o registro de recebimento em `trabalho/inventarios/recebimento-projeto-N.md`
3. 🔴 **Verificar credencial exposta** — se houver, escalar antes de prosseguir
4. 🔴 **Levantar os ambientes de teste** (AGI, e-mail, banco) — se não existirem, é impedimento

---

## Passo 1 — Reconhecimento (por projeto)

**Objetivo:** entender a forma do projeto antes de entrar no detalhe.

1. Mapear a árvore de diretórios
2. Localizar o ponto de entrada
3. **Traçar o fluxo principal do início ao fim**, sem entrar em detalhe de implementação
4. Identificar a granularidade de execução: por arquivo? por operadora? por lote mensal?
5. Listar as bibliotecas usadas — elas dizem muito (`win32com` → Outlook; `openpyxl`/`xlwings` → Excel; `pyautogui`/`pywinauto` → UI do AGI)

**Saída:** seção "Estrutura e execução" do inventário.

**Tempo esperado:** curto. Se você está lendo função por função aqui, está fundo demais para o passo 1.

---

## Passo 2 — Mapeamento código → HU

**Objetivo:** saber o que cada pedaço de código faz, em termos de negócio.

Nos **dois sentidos**:

**Sentido A — de HU para código.** Para cada HU que o projeto deveria cobrir:
- Localizar o código (arquivo e linha)
- Marcar: implementada / parcial / **ausente**

**Sentido B — de código para HU.** Para cada módulo/função relevante:
- A qual HU pertence?
- Se a nenhuma: é escopo extra, código morto, ou HU não documentada?

⚠️ **O sentido B é onde estão as surpresas.** Código sem HU pode ser: o Épico 5 escondido no P4, código do fluxo de **Receita** (fora de escopo deste MVP), ou funcionalidade que ninguém documentou.

**Saída:** matriz preenchida em `trabalho/inventarios/inventario-projeto-N.md` + atualização de [`../04-relatorios/matriz-de-rastreabilidade.md`](../04-relatorios/matriz-de-rastreabilidade.md).

---

## Passo 3 — 🔴 Versão da regra (V1 ou V2)

**O passo mais importante da fase.** Cinco HUs mudaram estruturalmente entre V1 e V2. Migrar código V1 carrega regra revogada para o repositório novo.

| HU | Projeto | Como verificar | V1 (revogada) | V2 (vigente) |
|---|---|---|---|---|
| HU-02 | P1 | Como a operadora é identificada | domínio do remetente + tabela de contatos | **EOT da Credora lida no arquivo** + Anexo 5 |
| HU-07 | P2 | Existe caminho de erro dedicado ao caso L-L? | sim, fluxo próprio | não, regra geral `_ERRO` |
| HU-09 | P3 | Onde a base de contestação é gravada | arquivo `Base_Contestação` com abas | `tbl_..._contestacao` |
| HU-10 | P3 | Onde a sumarização é gravada | aba `Contest` | banco |
| HU-19 | P4 | Onde o EC é preenchido | planilha de Encontro de Contas | campos do banco |

**Caso especial — se o P3 gravar nos dois:** verificar no P4 se o `_ENV` é montado a partir do **arquivo** ou do **banco**. Isso responde à pergunta Q4 (uma das "duas exceções" da frase *"todas as planilhas foram substituídas por banco, exceto dois arquivos"*).

**Saída:** seção "Versão da regra" do inventário. Cada V1 encontrada é **retrabalho a dimensionar**, não migração.

---

## Passo 4 — Pontos de I/O

**Objetivo:** mapear todo contato com o mundo externo. É aqui que estão os acoplamentos reais entre os RPAs.

Para cada categoria, registrar **o quê**, **onde no código** e **como**:

- **E-mail:** lê? move? envia? qual caixa, quais filtros, qual biblioteca
- **Arquivos:** que caminhos, **como são construídos** (inline? função? config?), que convenções de nome
- **Banco:** que tabelas, **que campos** (comparar com a lista documentada — campo não documentado é achado), como conecta, usa transação?
- **AGI:** que telas, que biblioteca de UI, como trata login, **como confirma sucesso**
- **Anexo 5:** de onde vem, como é atualizado, que colunas usa

⚠️ **Atenção especial à construção de caminhos.** Os caminhos de rede são o **contrato implícito entre os RPAs**. Se cada projeto os constrói por conta própria, qualquer divergência é bug latente.

---

## Passo 5 — Regras de negócio

Percorrer [`../01-entendimento/regras-de-negocio-consolidadas.md`](../01-entendimento/regras-de-negocio-consolidadas.md) e, para cada regra, registrar: **está implementada? onde? confere com a V2?**

Prioridade máxima nestas quatro, porque são as que a documentação deixou ambíguas — **registre literalmente o que o código faz**:

1. **Regra da variação.** Qual limiar (`>` ou `>=`)? Considera sinal? Base do percentual é a operadora ou a expectativa?
2. **Dupla convivência de tarifas em fevereiro.** Está implementada? A consulta usa o **mês do tráfego** ou a data de execução?
3. **Regra do `_BK`.** Recalcula a linha de total ou não?
4. **Tarifas não reguladas.** Valida valor, ou a tabela só classifica?

E as bordas de leitura de arquivo, que separam "idêntico" de "divergente" na hora de unificar:
- aceita arquivo sem cabeçalho? ignora aba de resumo? exclui `Rel = 1`? tolera `Rel` vazia?

---

## Passo 6 — 🔴 Aderência às premissas da V2

As premissas 10.3/10.4 exigem regras e tabelas **editáveis pelo usuário**. O risco do imposto de 2028 exige layout **não posicional-fixo**.

Procurar, no código:

- [ ] Valores de **tarifa** constantes
- [ ] **Mapeamento descritor → remuneração** constante
- [ ] **Limiares** constantes (1%, `0,9635`)
- [ ] **Índices de coluna fixos** na leitura de arquivos
- [ ] **EOTs da Vivo** (011, 200, 9\*\*) constantes
- [ ] **Caminhos de rede** constantes

Cada ocorrência é **dívida técnica a registrar**. ⚠️ Não corrigir agora — corrigir durante a migração mistura mudança de comportamento com mudança de estrutura.

---

## Passo 7 — Candidatos a componente compartilhado

Registrar toda ocorrência que pareça reutilizável, numa [ficha](templates/ficha-de-componente-candidato.md), **com arquivo e linha**.

A partir do segundo projeto: confrontar cada novo candidato com os já registrados. É esse confronto que produz a **segunda ocorrência** exigida pelo critério C1.

⚠️ **Não promova nada nesta fase.** A promoção é F3, e exige os quatro critérios de [`../02-planejamento/criterios-de-compartilhamento.md`](../02-planejamento/criterios-de-compartilhamento.md).

Lista de partida com 15 candidatos derivados da documentação: [`../03-checklists/checklist-componentes-compartilhados.md`](../03-checklists/checklist-componentes-compartilhados.md), Parte C.

---

## Passo 8 — Duplicações

A partir do **segundo** projeto. Para cada par com responsabilidade equivalente:

1. Registrar as duas ocorrências (projeto, arquivo, linha)
2. 🔴 **Comparar as bordas, não o caminho feliz** — a lista completa está no [checklist de duplicações](../03-checklists/checklist-duplicacoes.md), Parte B.2
3. Dar veredicto: IDÊNTICO / EQUIVALENTE-PARAMETRIZÁVEL / DIVERGENTE / FALSO PAR
4. Se DIVERGENTE, sub-classificar: VERSÃO / INTERPRETAÇÃO / DEFEITO

**Onde procurar primeiro:** fronteiras P2×P3, P4×P5, P4×P6, P4×P7 — projetos que convergem no mesmo RPA.

**E dentro do mesmo projeto:** o P2 tem caminho L-L **e** regra geral de `_ERRO`? O P3 grava no arquivo **e** no banco? O P6 duplica a automação do AGI entre HU-20 e HU-21?

---

## Passo 9 — Fechamento do projeto

- [ ] Inventário completo em `trabalho/inventarios/inventario-projeto-N.md`
- [ ] Matriz de rastreabilidade atualizada
- [ ] Fichas de candidatos criadas
- [ ] Registros de duplicação criados
- [ ] Achados críticos escalados (não esperar o fim da fase)
- [ ] Dúvidas novas acrescentadas a [`../04-relatorios/duvidas-pendentes.md`](../04-relatorios/duvidas-pendentes.md)

**Só então passar ao próximo projeto.**

---

## Pontos de atenção específicos por projeto

### P1 — Épico 1 (RPA 1)
- 🔴 **HU-02: V1 ou V2?** É a verificação mais importante deste projeto
- Se implementa a V2, o código precisa **abrir o anexo** antes de decidir onde salvá-lo — verificar a ordem das operações
- Como trata arquivo corrompido, protegido por senha, ou com Credora vazia? (Q16)
- Salva no servidor do WebFat, além do Lagoa? (novo na V2)
- Como implementa a periodicidade, já que a data de corte não existe? (Q1)
- Como trata reenvio com o mesmo nome?

### P2 — Épico 2 (RPA 2)
- Existe caminho de erro dedicado ao caso **L-L** além da regra geral? (candidato a eliminação)
- **Dupla convivência de tarifas em fevereiro** está implementada?
- Tarifas ou mapeamentos **constantes no código**?
- Como distingue erro do arquivo da operadora (aciona a operadora) de erro do arquivo de expectativa (WebFat)?
- Existe alguma "correção automática" de expectativa? (Q13 — regra não documentada)
- O `_BK` recalcula o total? (Q10)

### P3 — Épico 3 (RPA 2)
- 🔴 **HU-09: arquivo, banco, ou os dois?**
- Se manipula planilha: a migração para banco é **reescrita da camada de saída**, não refatoração
- **Qual é exatamente a regra de variação implementada?** Limiar, sinal, base — registre literalmente (Q2)
- Como trata expectativa ausente (valores zerados)?
- Como o RPA espera a decisão do analista? Polling? Coluna de estado? (Q19)

### P4 — Épico 4 + HU-19 (RPA 3)
- 🔴 **PRIMEIRO: o Épico 5 está aqui?** Procurar `Detraf > Importar Dados`, `Contestação > Gerenciar`, escrita em `carga_agi` (Q3)
- 🔴 **De onde vem o `_ENV`** — do arquivo `Base_Contestação` ou do banco? (Q4)
- HU-19 escreve na planilha ou nos campos do banco?
- Como lê e incrementa a **numeração CT**? Há trava? (Q18)
- Como trata operadora sem modelo de carta?
- Coluna W do `CONT_PROC`: valor bruto ou minutagem? (Q11)
- Onde estão os pontos de retomada entre os passos irreversíveis?

### P7 — Épico 5 (RPA 3) — se existir
- Como confirma que o upload no AGI teve sucesso?
- O que é o `DE_EBT_..._MODELO.xlsx`? (Q14)
- Como trata falha na carga? Reprocessa? Duplica lançamento?

### P5 — HU-15 (RPA 3)
- **É autossuficiente ou depende de artefatos do P4 por caminho de arquivo?**
- Envia automaticamente ou espera aprovação? (Q5)
- De onde vêm os contatos das operadoras? (Q16)
- ⚠️ **Teste de confirmação:** a camada de e-mail identificada no P1/P2 serve a este projeto? Se não, a abstração candidata está errada

### P6 — HU-20 + HU-21 (RPA 3 e RPA 4)
- **As duas HUs compartilham a camada de automação do AGI?** Se sim, é candidata natural à base comum
- A separação entre elas é limpa ou entrelaçada? (define o custo da cisão)
- Como o RPA 4 é acionado? A detecção está aqui ou no P4? (achado do relatório)
- Como trata operadora cujo nome mudou entre os meses? (Q17)
- ⚠️ **Confirmar Q7 antes:** se a HU-20 saiu do escopo, não há cisão a fazer

---

## Critérios de decisão — referência rápida

### Componente reutilizável (todos os quatro)
1. **C1** — duas ocorrências reais, em RPAs diferentes, com arquivo e linha
2. **C2** — não depende de estado exclusivo de um RPA
3. **C3** — a regra não está em pendência aberta
4. **C4** — a variação cabe em parâmetro, sem `if` sobre o parâmetro

### Duplicação
Mesma responsabilidade em lugares distintos, ainda que implementada de forma diferente. Classificar em IDÊNTICO / EQUIVALENTE-PARAMETRIZÁVEL / DIVERGENTE / FALSO PAR — comparando **bordas**, não caminho feliz.

### Responsabilidade de RPA
O **gatilho** é o corte primário:

| Gatilho | RPA |
|---|---|
| Evento de e-mail + espera | 1 |
| Lote após a data de corte | 2 |
| Sinalização do analista | 3 |
| Condição assíncrona de recuperação | 4 |

Código que atravessa dois gatilhos é candidato à base comum ou à cisão.

### Base compartilhada
Só entra o que atende aos quatro critérios **e** cuja regra estiver fechada. Regra em pendência fica no RPA, registrada como **compartilhamento adiado**.

### Ordem de migração (fase seguinte)
**Por camada:** utilitários → acesso a dados → arquivos Detraf → regras compartilhadas → integrações → fluxos específicos.
**Por RPA:** RPA 1 → RPA 2 → RPA 4 → RPA 3.

### Validação da arquitetura
Cada RPA com `main.py` próprio e execução isolada; toda HU rastreável a um RPA; nenhuma regra duplicada; nenhuma dependência de runtime entre RPAs além dos artefatos documentados; equivalência funcional comprovada.

---

## Saídas esperadas da fase

Em `trabalho/inventarios/`:

```
recebimento-projeto-1.md ... recebimento-projeto-7.md
inventario-projeto-1.md   ... inventario-projeto-7.md
candidatos/               ← uma ficha por candidato
duplicacoes/              ← um registro por par avaliado
mapa-real.md              ← consolidação (F3)
```

E atualizados em `docs/`:
- `04-relatorios/matriz-de-rastreabilidade.md` — coluna Código preenchida
- `04-relatorios/duvidas-pendentes.md` — dúvidas novas
- `04-relatorios/riscos-conhecidos.md` — riscos confirmados ou descartados

---

## Gate para a fase de arquitetura (F4)

- [ ] Todos os projetos inventariados
- [ ] Toda HU rastreada a código **ou** marcada como não implementada
- [ ] Todo código atribuído a uma HU **ou** classificado como extra/morto
- [ ] Versão da regra (V1/V2) registrada para as cinco HUs 🔴
- [ ] Todo candidato a componente com pelo menos duas ocorrências localizadas
- [ ] Toda duplicação com veredicto; toda DIVERGENTE sub-classificada
- [ ] Toda divergência de regra encaminhada ao PO — **nenhuma decidida tecnicamente**
- [ ] Achados críticos escalados
