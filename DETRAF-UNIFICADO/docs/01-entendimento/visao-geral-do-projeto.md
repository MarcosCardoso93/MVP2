# Visão Geral do Projeto — DETRAF MVP2

> ⚠️ **Fotografia da etapa documental (2026-07-30).** Este documento foi escrito
> **antes** de qualquer código chegar, e descreve o entendimento daquele momento.
> Vários pontos já mudaram — em especial: o Épico 5 **tem** projeto (o P7, entregue
> em 2026-08-04), e as HUs 12 a 19 estão implementadas e orquestradas.
>
> **Fonte do estado atual:** `docs/04-relatorios/duvidas-pendentes.md` (pendências),
> `matriz-de-rastreabilidade.md` (HUs) e `unificado/README.md` (código).

> Fonte: V2 (`[V2] Btime SPTI Detraf MVP2_ comentadaLuciana.docx`), itens 1, 5, 6, 7 e 10.

---

## Identificação

| Campo | Valor |
|---|---|
| Nome do RPA | DETRAF E CONTESTAÇÃO DE DESPESA |
| ID GSA | ATA0000574 |
| Segmento | Atacado |
| Cliente | Telefônica Vivo (TBRA) — Gerência de Sistemas e Serviços Atacado (GSA) |
| Fornecedor | Btime |
| Sistemas envolvidos | AGI, WebFat, Outlook Desktop Classic, rede Lagoa, autenticador Vivo |
| Volume | ~1.600 arquivos de Detraf de despesa por mês |

---

## O que o sistema faz

O Detraf (Documento de Declaração de Tráfego e de Prestação de Serviços) é o documento pelo qual operadoras de telecomunicações declaram, mês a mês, o tráfego trocado entre si e o valor devido por ele. Quando outra operadora presta serviço à Vivo, ela emite um Detraf cobrando — isso é **despesa** para a Vivo.

A automação cobre o ciclo completo dessa despesa:

1. **Receber** os arquivos de Detraf que as operadoras enviam por e-mail e guardá-los organizadamente.
2. **Validar** esses arquivos contra o layout e as regras regulatórias (EOTs válidas, meses aceitos, descritores coerentes, tarifas reguladas corretas).
3. **Comparar** o que a operadora cobrou com a **expectativa** que a própria Vivo calculou (arquivos gerados internamente pelo ICT).
4. **Decidir** se a diferença justifica contestação — regra de corte: variação do `R$_Bruto` acima de 1%.
5. **Contestar** formalmente: carta numerada, e-mail à operadora e arquivos de contestação.
6. **Carregar** os resultados no AGI (sistema financeiro) em todos os cenários.
7. **Alimentar** o Encontro de Contas e conferir os valores pelo Relatório de Receitas e Despesas do AGI.
8. **Retificar** contestações de meses anteriores quando o tráfego contestado é recuperado.

O produto declarado pela V2:

> "Criar uma automação que receba os arquivos de Detraf das operadoras, impostos, valide as informações e compare com os arquivos de expectativa gerados pelo ICT. Após a comparação, realizar os procedimentos de carga no AGI para os cenários sem contestação, contestação sem retenção e contestação com retenção. Realizar o processo de envio e formalização da contestação para a operadora e, por fim alimentar o Encontro de Contas."

E a arquitetura de destino:

> "A automação será composta entre 3 e 4 RPA's para atender as necessidades do processo do início ao fim."

O `Relatorio_Separacao_RPAs_Detraf_MVP2.docx` optou por **4 RPAs**. Ver [`responsabilidades-dos-rpas.md`](responsabilidades-dos-rpas.md).

---

## Os três cenários de saída

Todo o processo converge para um destes três desfechos por combinação de operadora × EOT × tipo de remuneração × mês de tráfego:

| Cenário | Quando | Arquivos gerados | Carta/e-mail |
|---|---|---|---|
| **Sem contestação** | Variação do `R$_Bruto` < 1% | `_EXT` | não |
| **Contestação SEM retenção** | Variação ≥ 1%, analista opta por não reter | `_EXT`, `_ENV`, carta CT, `CONT_PROC` | sim |
| **Contestação COM retenção** | Variação ≥ 1%, analista opta por reter | `_EXT`, **`_INT`**, `_ENV`, carta CT, `CONT_PROC` | sim |

O `_INT` (expectativa Vivo apenas do tráfego contestado com retenção) **só existe** no terceiro cenário — nos outros dois ele não chega a ser criado.

---

## Escopo

### Dentro do escopo

- Fluxo de **Despesa** do Detraf de ITX
- **Contestação de Despesa**
- Preenchimento do Encontro de Contas com a despesa
- Retificação de contestação (evento "Recuperação" no AGI)

### Fora do escopo (declarado na premissa 10.1 da V2)

- Fluxo de Receita
- Contestação de Receita
- Fechamento do Encontro de Contas
- Status ITX (contabilidade)
- Geração do CDR (receita e despesa)

Existem três demandas irmãs — **ATA0000571, ATA0000567, ATA0000572** — que, junto com esta, formam o fluxo completo de faturamento do Detraf. ⚠️ A V2 registra a existência delas mas **não descreve a interface** entre esta automação e as outras três. Isso é uma lacuna: ver [`../04-relatorios/duvidas-pendentes.md`](../04-relatorios/duvidas-pendentes.md).

---

## Sistemas e ambientes

| Sistema | Papel | Forma de acesso |
|---|---|---|
| **Outlook Desktop Classic** | Recebimento dos arquivos das operadoras e envio das contestações | Automação de aplicação desktop. Conta: `tbr00848.br@telefonica.com`; caixa: `detrafTBRA.br@telefonica.com` |
| **Rede Lagoa** | Armazenamento estruturado dos arquivos por operadora/ano/mês | `\\lagoa\DI\DI-A\DI-A1\Padronização de Detraf - Grupo Técnico\...` |
| **WebFat** | Banco de dados + interface do analista (abas Detraf e Contestação) | Banco (tabelas `tbl_*`) e servidor de arquivos |
| **AGI** | Sistema financeiro — carga do Detraf e das contestações, relatórios | Automação de UI, desktop. Requer autenticador de rede Vivo (`https://10.238.231.25/`) |
| **ICT** | Gera os arquivos de expectativa da Vivo | Fora desta automação; os arquivos já chegam no servidor do WebFat |

---

## Tabelas do banco WebFat citadas

| Tabela | Uso |
|---|---|
| `tbl_detraf_tarifas` | Tarifas reguladas por remuneração, região, EOTs, grupo horário e período |
| `tbl_detraf_mapeamento_descritores` | Relação descritor × tipo de remuneração |
| `tbl_rpa_log_detraf_despesa_arquivos` | Registro por arquivo processado; campo `tipo_registro` ∈ {`DETRAF`, `EXPECTATIVA`, `ERRO`} |
| `tbl_rpa_log_detraf_despesa_contestacao` | Base de contestação e Encontro de Contas; campos `tipo_contestacao`, `carga_agi`, `minutos_operadora`, `vb_operadora`, `minutos_diferenca`, `vb_diferenca`, `minutos_variacao_perc`, `vb_variacao_perc` |

⚠️ A V2 não publica o DDL dessas tabelas. A lista de campos acima é a que aparece citada no texto e **não deve ser assumida como completa**.

---

## Mudança estrutural da V2: planilhas → banco

A alteração mais importante entre a V1 e a V2:

> "Todas as planilhas deste processo foram substituídas por banco, exceto dois arquivos. Antes da carga no AGI e em caso de contestação com ou sem retenção."

Na prática:
- `Base_Contestação_{operadora}_{mês}` com abas de dados, `RESUMO TBRA`, `RESUMO {operadora}` e `Contest` **deixa de ser planilha física** — a lógica permanece, o destino passa a ser `tbl_rpa_log_detraf_despesa_contestacao`.
- A planilha de Encontro de Contas **deixa de ser preenchida** — os valores vão para campos da mesma tabela.

⚠️ A frase "exceto dois arquivos" **contradiz** o restante da V2, que continua descrevendo pelo menos cinco artefatos de arquivo (`_ENV`, carta CT, `CONT_PROC_MASCARA`, `_EXT`, `_INT`). Pendência registrada em [`../04-relatorios/relatorio-inconsistencias-e-lacunas.md`](../04-relatorios/relatorio-inconsistencias-e-lacunas.md).

---

## Partes interessadas

| Área | Papel | Nome |
|---|---|---|
| Área cliente (Vivo) | PO | Ana Carolina da Silva |
| Área cliente (Vivo) | Gerente | Alan Ramos Baptista |
| GSA (Vivo) | GP | Luciana Santos Vargas |
| GSA (Vivo) | Gerente | Guilherme Lage |
| Btime | GP | Ekiton Gomes |
| Btime | PMO | Helder Rezende |
| Btime | Desenvolvedor | Elias Leite |

As pendências abertas em [`../04-relatorios/duvidas-pendentes.md`](../04-relatorios/duvidas-pendentes.md) estão endereçadas a esses papéis.

---

## Premissas do projeto (item 10 da V2)

1. Cobre apenas Despesa e Contestação de Despesa do Detraf de ITX.
2. **As regras de negócio devem ser editáveis e acessadas pelo usuário** para incluir, editar ou finalizar sua aplicação.
3. **As tabelas de consulta devem ser editáveis e gerenciáveis pelos usuários**, com autonomia na edição dos valores.
4. Tarifas reguladas mudam anualmente em fevereiro, gerando dupla convivência de tarifas.
5. Projeção de mais um imposto em 2028, deslocando colunas.
6. O acesso ao AGI exige estar logado no autenticador de rede da Vivo.

As premissas 2 e 3 são as mais consequentes para a unificação: elas dizem que regra de negócio e tabela de consulta são **dado gerenciado pelo usuário**, não constante embutida no código. ⚠️ Se os projetos de origem tiverem regras ou tarifas fixas no código, isso é violação de premissa — item obrigatório do checklist de análise.

---

## Riscos declarados pela própria V2 (item 7)

1. Tarifas reguladas alteradas anualmente em fevereiro → duas tarifas válidas simultaneamente.
2. Projeção de novo imposto em 2028 deslocando as colunas dos arquivos.
3. "Os ajustes nos arquivos são dinâmicos. A solução não poderá ficar condicionada a regras de negócio que podem ser alteradas a qualquer momento."

Ver o catálogo ampliado em [`../04-relatorios/riscos-conhecidos.md`](../04-relatorios/riscos-conhecidos.md).
