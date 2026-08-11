# Entendimento das Histórias de Usuário

> ⚠️ **Fotografia da etapa documental (2026-07-30).** Este documento foi escrito
> **antes** de qualquer código chegar, e descreve o entendimento daquele momento.
> Vários pontos já mudaram — em especial: o Épico 5 **tem** projeto (o P7, entregue
> em 2026-08-04), e as HUs 12 a 19 estão implementadas e orquestradas.
>
> **Fonte do estado atual:** `docs/04-relatorios/duvidas-pendentes.md` (pendências),
> `matriz-de-rastreabilidade.md` (HUs) e `unificado/README.md` (código).

> Fontes: `DETRAF_MVP2_Historias.pdf` (HUs e critérios V1), V2 (regras vigentes), `Analise_Mudancas_V2_por_Historia.md` (delta).

Uma seção por HU. Cada uma traz: descrição, critérios de aceitação **vigentes** (já ajustados pela V2), o que mudou da V1 para a V2, status e pendências.

## Legenda de status

| Ícone | Significado |
|---|---|
| 🟢 | Mantida — sem mudança relevante na V2 |
| 🟡 | Atualizada — critérios precisam de ajuste ou adição |
| 🔴 | Impactada estruturalmente — a V2 muda a natureza da entrega |
| ⚠️ | Risco / pendência — a V2 remove ou deixa em aberto algo que a HU pressupõe |

## Índice rápido

| HU | Título | Status | Projeto | RPA |
|---|---|---|---|---|
| HU-01 | Leitura e organização do inbox (Outlook) | 🟡⚠️ | P1 | 1 |
| HU-02 | Identificação da operadora | 🔴 | P1 | 1 |
| HU-03 | Salvamento na estrutura de pastas | 🟡 | P1 | 1 |
| HU-04 | Validação estrutural das colunas | 🟡 | P2 | 2 |
| HU-05 | Validação da tarifa regulada | 🟡 | P2 | 2 |
| HU-06 | Tratamento de arquivo `_BK` | 🟢 | P2 | 2 |
| HU-07 | Tratamento de erro L-L (STFC) | 🔴 | P2 | 2 |
| HU-08 | Registro dos arquivos no WebFat | 🟡 | P2 | 2 |
| HU-09 | Consolidação da Base Contestação | 🔴 | P3 | 2 |
| HU-10 | Análise de contestação por EOT | 🟡🔴 | P3 | 2 |
| HU-11 | Exibição no WebFat (analista) | 🟢 | P3 | 2 |
| HU-12 | Geração do arquivo `_EXT` | 🟢 | P4 | 3 |
| HU-13 | Geração do arquivo `_INT` | 🟢 | P4 | 3 |
| HU-14 | Geração do `_ENV` e carta | 🟢 | P4 | 3 |
| HU-15 | Envio do e-mail de contestação | ⚠️ | **P5** | 3 |
| HU-16 | Geração do `CONT_PROC` | 🟡 | P4 | 3 |
| HU-17 | Upload `_EXT`/`_INT` no AGI | 🟡⚠️ | **⚠️ nenhum** | 3 |
| HU-18 | Upload da contestação no AGI | 🟡 | **⚠️ nenhum** | 3 |
| HU-19 | Preenchimento do Encontro de Contas | 🔴 | P4 | 3 |
| HU-20 | Verificação do Relatório Receitas e Despesas | 🟡⚠️ | **P6** | 3 |
| HU-21 | Tráfego recuperado e retificação AGI | 🟢 | **P6** | **4** |
| HU-22 | Tratamento de CBS/IBS | 🆕 não existe | ⚠️ nenhum | ? |

---

# ÉPICO 1 — Captura de Arquivos via E-mail

## HU-01 — Leitura e organização do inbox de e-mail (Outlook) 🟡⚠️

**Descrição.** O robô acessa o Outlook Desktop Classic conectado à caixa `detrafTBRA.br@telefonica.com` (conta `tbr00848.br@telefonica.com`) e varre os e-mails recebidos, identificando os que trazem anexos de Detraf das operadoras. Organiza esses e-mails numa pasta "Detraf Despesas" dentro do próprio Outlook.

**Critérios de aceitação vigentes.**
- Acesso autenticado ao Outlook Desktop Classic
- Localizar e-mails que **não** contenham a palavra "CONTESTAÇÃO" *(novo na V2)*
- Filtrar pelo **mês de referência** *(novo na V2)*
- Baixar **apenas** anexos `.csv` ou Excel *(novo na V2 — a V1 dizia só "Excel")*
- Organizar os e-mails na pasta "Detraf Despesas" do Outlook
- ⚠️ Periodicidade da varredura: **indefinida** — ver pendência

**O que mudou.** A V2 **removeu** o parágrafo de periodicidade dos RPAs. O critério V1 "varredura diária após o dia 05" perdeu sustentação. No lugar, a V2 diz apenas que "a **data de corte** do processo está em análise pela área cliente". Em compensação, a V2 acrescentou o filtro negativo por "CONTESTAÇÃO", o filtro por mês de referência e a extensão `.csv`.

**Por que o filtro negativo existe.** A mesma caixa recebe e envia contestações. Sem o filtro, o robô reprocessaria os próprios e-mails de contestação da Vivo como se fossem Detraf de operadora.

**⚠️ Pendências.**
1. **Data de corte** — não definida. Bloqueia o critério de periodicidade e o gatilho de batimento. Destinatário: área cliente.
2. A V2 registra que "o robô poderá receber diversos e-mails da mesma operadora" — a regra de deduplicação depende da data de corte.

---

## HU-02 — Identificação da operadora 🔴

**Descrição (V2).** Para cada arquivo capturado, o robô lê a **EOT da Credora (1ª coluna do arquivo)** e busca no **Anexo 5** o **nome fantasia** da operadora.

**Critérios de aceitação vigentes.**
- Leitura da EOT da coluna Credora do arquivo anexo
- Busca no Anexo 5 pela coluna nome fantasia
- Sinalização quando a EOT não for encontrada
- Arquivos divergentes → status "**não validado**" no WebFat, com comunicação visual em vermelho

**O que mudou — mudança de mecanismo, não de texto.** A V1 identificava a operadora pelo **domínio do remetente do e-mail**, consultando a tabela de contatos do WebFat. A V2 **retirou essa proposta** e substituiu por: *"o nome correto da operadora é pela EOT da credora presente no anexo 5, busca pela coluna nome fantasia"*.

**Consequência prática.** A identificação sai do **metadado do e-mail** e vai para o **conteúdo do arquivo**. Isso inverte a ordem das operações do RPA 1: antes bastava ler o cabeçalho do e-mail para saber onde salvar; agora é preciso **abrir e ler o anexo** antes de determinar o destino. Qualquer implementação do P1 baseada na regra antiga está desalinhada com a V2.

**⚠️ Impacto na análise de código.** Item obrigatório do checklist do P1: verificar qual das duas regras o código implementa. Se implementar a V1, é retrabalho, não migração.

**⚠️ Efeito colateral não documentado.** Se a identificação depende de ler o arquivo, o que acontece quando o arquivo está corrompido, protegido por senha, ou tem a coluna Credora vazia? A V2 não define. E se um e-mail traz anexos de mais de uma operadora? Também não definido.

---

## HU-03 — Salvamento dos arquivos na estrutura de pastas de rede 🟡

**Descrição.** Com a operadora identificada, o robô salva cada arquivo no caminho de rede correto e replica no servidor do WebFat.

**Critérios de aceitação vigentes.**
- Salvamento em `\\lagoa\DI\DI-A\DI-A1\Padronização de Detraf - Grupo Técnico\Operadoras\{operadora}\{ano}\{aaaamm}\Detrafs Recebidos`
- **Salvamento também no servidor do WebFat**, para o usuário abrir o documento pela ferramenta *(novo na V2)*
- Criação da pasta do mês copiando toda a estrutura interna do mês anterior
- Reenvio de arquivo com o **mesmo nome**: sobrescreve o anterior e **inicia novo processamento**, seguindo a regra de corte *(novo na V2)*
- Registro do arquivo em `tbl_rpa_log_detraf_despesa_arquivos`
- Arquivos de expectativa Vivo separados por pastas **VIVO** e **TLF** com "D" no final *(novo na V2 — pode caber aqui ou na HU-04)*

**⚠️ Pendência de desenho.** O item 2.13 da V2 diz: *"O robô irá atuar com a memória da máquina local. O RPA irá salvar na pasta local para que seja integrado ao Webfat. O Webfat terá a opção do analista transferir o arquivo para o Lagoa."* Isso sugere **três** locais de armazenamento (local, WebFat, Lagoa) e uma transferência para o Lagoa que passa a ser **manual, acionada pelo analista** — o que conflita com o critério de salvar direto na pasta de rede. Não está claro se são fluxos alternativos ou sequenciais. Destinatário: área cliente / GP.

---

# ÉPICO 2 — Validação dos Arquivos de Detraf

## HU-04 — Validação estrutural das colunas 🟡

**Descrição.** O robô abre cada arquivo de "Detrafs Recebidos" e cada arquivo de expectativa e valida coluna a coluna. Arquivos **sem cabeçalho são aceitos** desde que sigam o mesmo padrão. **Abas adicionais de resumo são desconsideradas.**

**Critérios de aceitação vigentes.** Layout completo em [`regras-de-negocio-consolidadas.md`](regras-de-negocio-consolidadas.md). Em resumo:

| Col | Nome | Regra |
|---|---|---|
| 1 | Credora | EOT de operadora válida no Anexo 5 |
| 2 | Devedora | EOT da Vivo válida no Anexo 5 |
| 3 | Referencia | apenas mês corrente −1, formato `AAAAMM` |
| 4 | Tráfego | mês corrente −1, −2 ou −3, formato `AAAAMM` |
| 5 | POI | escrita livre, não obrigatório |
| 6 | Rel | normalmente 0 nas linhas de tráfego, 1 nos totais/subtotais; pode estar vazia |
| 7 | DESC | descritor correspondente à remuneração do nome do arquivo |
| 8 | GH | apenas `S`, `R`, `N` ou `D` |
| 9 | Chamadas | inteiros |
| 10 | Minutos | até 1 casa decimal |
| 11 | Tarifa | até 5 casas decimais; **nunca zero**; ver HU-05 |
| 12 | R$_Liq | até 2 casas decimais |
| 13 | PIS_Cofins | até 2 casas decimais |
| 14 | ICMS | até 2 casas decimais |
| 15 | R$_Bruto | até 2 casas decimais |

**Regra geral de erro (nova na V2).** *"Caso as regras não sejam validadas, os registros devem ser direcionados para um arquivo de mesmo nome com `_ERRO` no final da sua nomenclatura."* Isso vale para **qualquer** regra violada.

**Tratamento diferenciado por origem do erro.**
- Erro no arquivo **da operadora** → criticar e acionar a operadora por e-mail, com opção de correção ou reenvio.
- Erro no arquivo **de expectativa** → disponibilizar via WebFat para a área usuária; "avalia possível correção automática".
- Em qualquer caso, o robô **segue para o próximo processamento** — não para. O erro aparece no WebFat como alerta vermelho, **sem detalhamento**.

**O que mudou.** A regra de `_ERRO` deixou de ser específica (antes só existia para o caso L→L / STFC) e virou geral. Isso **amplia o escopo desta HU** e esvazia a HU-07.

**⚠️ Pendências.** As colunas **CBS, IBS Municipal e IBS Estadual** não constam neste layout de 15 colunas, mas a V2 afirma que os arquivos de Detraf Vivo passam a tê-las. Não se sabe se são as colunas 16-18, se substituem alguma, nem se o arquivo da operadora também as terá. Ver HU-22.

---

## HU-05 — Validação da tarifa regulada 🟡

**Descrição.** Para cada linha, o robô consulta `tbl_detraf_tarifas` e verifica se o valor da coluna Tarifa está correto.

**Critérios de aceitação vigentes.**
- Identificar a remuneração pelo descritor, **consultando `tbl_detraf_mapeamento_descritores`** *(novo na V2 — antes o mapeamento estava implícito)*
- Consulta em `tbl_detraf_tarifas` pelos campos: `tipo_remuneracao`, `região`, `eot_vivo`, `eot_operadora`, `gh`, `data_inicio`/`data_fim`
- Região vem do campo região do Anexo 5 para a EOT da **Credora**
- `gh` nulo na tabela = a condição vale para todos os grupos horários
- `eot_vivo`/`eot_operadora` servem para exceções de região — na despesa, `eot_vivo` é sempre a **Devedora** e `eot_operadora` é a **Credora**
- **Dupla convivência de tarifas em fevereiro** (ano anterior e ano atual)
- **Tarifa zero nunca é aceita**
- Regra do horário reduzido da **VU-M**: considerar o tipo de serviço da operadora **DEVEDORA** — se atua como STFC é um valor, se atua como SMP é outro
- Tarifas **não** reguladas: valida apenas o formato

**Descritores → remuneração** (V2):

| Remuneração | Regra do descritor |
|---|---|
| VUM | final "V" |
| TU-RL | final "L" |
| TURIU1 | início "L" e final "I" |
| TURIU2 | início ≠ "L" e final "I" |
| TUCOM | final "C" |

E o final do descritor deriva do tipo de serviço da EOT Credora no Anexo 5: **SMP → "V"**; **STFC → "I" ou "L"**.

**Por que fevereiro é especial.** O Detraf é consolidado até 24/02, mas há tráfego entre 25/02 e o encaminhamento de fevereiro. O reajuste anual cai nessa janela — logo, **duas tarifas válidas para a mesma remuneração** durante todo o período em que fevereiro apareça na coluna Tráfego. Como a coluna Tráfego aceita até mês −3, isso significa que uma tarifa de fevereiro pode ser válida até o Detraf de maio.

**⚠️ Contradição interna da V2.** Dois trechos vizinhos dizem coisas opostas:
- *"As tarifas não reguladas não serão validadas em seu conteúdo, apenas no formato."*
- *"A consulta de tarifas não reguladas é realizada através da tabela de tarifas. Todos os descritores que não estiverem na tabela são tarifas não reguladas."*

A segunda frase parece querer dizer que a **tabela é usada para classificar** (está na tabela = regulada), não para validar valor. Mas está ambígua. Registrada como pendência.

**⚠️ Pendência da própria V2.** *"Descritores de transporte devem ser validados a partir da tabela Descritor_Remuneração (aguardando informação do solicitante)."* Ou seja, a validação de descritores de transporte **não tem regra definida**.

---

## HU-06 — Tratamento de arquivo `_BK` (SMP não-PMS) 🟢

**Descrição.** Quando o arquivo apresenta descritor **início "L" e final "V"**, com as EOTs envolvidas do tipo **SMP** e **não PMS** (coluna Concessão do Anexo 5 ≠ "P"), o robô cria uma cópia do arquivo com **`_BK`** no final do nome e salva na mesma pasta do original (Detrafs Recebidos ou Detrafs Enviados).

**Critérios de aceitação vigentes.**
- Identificação: descritor início "L" e final "V", tipo de serviço SMP, concessão ≠ "P"
- Cópia com sufixo `_BK` na mesma pasta do original
- **Nenhum alarme ou notificação** — operação silenciosa
- Vale tanto para o arquivo da operadora quanto para o de expectativa Vivo

**Status.** Sem mudanças relevantes na V2.

**⚠️ Conflito entre fontes.** O PDF de HUs (V1) exige "**linha de total recalculada** no arquivo `_BK`". A V2 diz apenas: *"Não é necessário gerar nenhum alarme, apenas criar na mesma pasta o arquivo conforme informado"* — **não menciona recálculo**. Não está claro se o recálculo foi removido ou se a V2 simplesmente não repetiu o detalhe. Como a V2 é normativa e a omissão pode ser acidental, isso precisa de confirmação antes de virar critério.

**Nota.** "BK" provavelmente remete a **Bill&Keep** — regime em que operadoras trocam tráfego sem cobrança recíproca, aplicável entre SMPs sem poder de mercado significativo. A V2 confirma indiretamente ao listar Bill&Keep entre os tipos de produto "com exceção do Bill&Keep que também deve considerar que ambas as EOTs tenham tipo de serviço = SMP". ⚠️ Inferência, não afirmação da documentação.

---

## HU-07 — Tratamento de erro L-L (STFC) 🔴

**Descrição original (V1).** Registros com descritor início "L" e final "L" e EOTs do tipo STFC seriam separados num arquivo `_ERRO`; se o problema fosse no arquivo da operadora, status "não validado" + e-mail à operadora.

**O que mudou.** A V2 **removeu o tratamento específico**. O comportamento foi **absorvido pela regra geral de `_ERRO`** da HU-04. A V2 mantém apenas a descrição do fenômeno — *"este tráfego deve ser criticado no arquivo da operadora, a qual deve enviar um novo arquivo sem os registros e/ou retirado no arquivo de expectativa de despesa da Vivo"* — mas sem fluxo diferenciado.

**Recomendação registrada na análise de mudanças.** **Fundir esta HU com a HU-04.** O caso L-L/STFC segue o mesmo fluxo genérico de erro.

**⚠️ Impacto na unificação.** Se o código do P2 tiver um caminho de tratamento dedicado ao caso L-L, ele é candidato a **eliminação**, não a migração. Item do checklist de duplicações: verificar se existem dois caminhos de erro (um geral e um específico) que deveriam ser um só.

---

## HU-08 — Registro dos arquivos validados no WebFat 🟡

**Descrição.** Após validar cada arquivo, o robô popula `tbl_rpa_log_detraf_despesa_arquivos` com o resultado, alimentando as abas Detraf e Contestação do WebFat.

**Critérios de aceitação vigentes.**
- Inserção em `tbl_rpa_log_detraf_despesa_arquivos`
- Campo **`tipo_registro`** com os valores explícitos *(detalhado na V2)*:

| Valor | Significado |
|---|---|
| `DETRAF` | dados da operadora — **sempre consolidados**, independentemente de erro |
| `EXPECTATIVA` | arquivo de expectativa validado sem erro |
| `ERRO` | arquivo de expectativa com problema |

- Flag visual **em vermelho** no WebFat para arquivos com erro, **sem detalhamento do erro**
- Os dados da operadora refletem na **aba Detraf** do WebFat

**O que mudou.** Além dos valores de `tipo_registro`, o tratamento de erro mudou de "correção manual ou abertura de chamado" para "**avalia possível correção automática**".

**⚠️ Pendência.** "Avalia possível correção automática" é vago — não há regra que diga o que é corrigível automaticamente nem como. É preciso confirmar se é decisão de produto validada ou apenas intenção de redação. Destinatário: PO / área cliente.

**Observação de assimetria.** Note que `tipo_registro` só distingue erro para o arquivo de **expectativa**. O arquivo da operadora é sempre `DETRAF`, mesmo com erro — porque os dados da operadora são o que ela **oficialmente** apresentou, e é contra eles que a contestação será feita. Isso é coerente com a V2: *"Caso tenha arquivo de detraf de uma operadora mas não o de expectativa, deve-se preencher a tabela normalmente e apresentar os valores zerados de expectativas. Os dados da operadora são considerados para o preenchimento da tabela."*

---

# ÉPICO 3 — Batimento Detraf × Expectativa

## HU-09 — Consolidação dos dados 🔴

**Descrição original (V1).** Criar o arquivo `Base_Contestação_{operadora}_{mês}` com duas abas — uma com os dados do Detraf da operadora e outra (`TBRA`) com a expectativa Vivo — mais as tabelas dinâmicas `RESUMO TBRA` e `RESUMO {operadora}`.

**Descrição vigente (V2).** **A mesma lógica, sem o arquivo.** A V2 é explícita: *"Não é necessário gerar o arquivo, mas usar a lógica e popular a tabela `tbl_rpa_log_detraf_despesa_contestacao`"*.

**Critérios de aceitação vigentes.**
- Dados da operadora de "Detrafs Recebidos", **sem as linhas de total (`Rel = 1`)**, de forma sequencial
- Dados de expectativa Vivo dos arquivos com `_D_` no nome, até a coluna `R$ Bruto`, também sem linhas de total
- Sumarização equivalente às tabelas dinâmicas: totais de `Minutos` e `R$ Bruto`, com as colunas `Tráfego` e `Referência`
- **Destino: `tbl_rpa_log_detraf_despesa_contestacao`** — não uma planilha
- Quando não há par operadora/expectativa, os valores de expectativa ficam **zerados** (os da operadora prevalecem)

**Esta é a mudança mais estrutural do documento.** O artefato central do processo deixa de existir como arquivo. Toda a manipulação de abas, cópia de intervalos e atualização de tabela dinâmica vira operação de banco.

**⚠️ Impacto na unificação — alto.** Se o código do P3 for construído sobre `openpyxl`/COM manipulando a planilha `Base_Contestação`, a migração para banco **não é refatoração, é reescrita da camada de saída**. A lógica de negócio (o que somar, por qual chave, o que excluir) é o que se preserva. Item de destaque no checklist de análise do P3.

**⚠️ Dependência transitiva não resolvida.** A HU-14 (`_ENV`) descreve copiar o arquivo `Base_Contestação_..._M` e apagar abas. Se a `Base_Contestação` não existe mais como arquivo, **de onde sai o `_ENV`?** A V2 não reconcilia isso. Ver HU-14.

---

## HU-10 — Análise de contestação por EOT e tipo de remuneração 🟡🔴

**Descrição.** O robô sumariza `Minutos` e `R$_Bruto` por **EOT devedora × tipo de tarifação × mês de tráfego**, comparando operadora contra expectativa Vivo, e marca cada combinação com `S` (contestar) ou `N` (não contestar).

**Critérios de aceitação vigentes.**
- Sumarização por EOT devedora, tipo de tarifação e mês de tráfego
- Regra de corte na variação do `R$_Bruto` — ver pendência de borda abaixo
- Uma análise para cada combinação de **Tipo de Operação** × **Tipo de Produto**, quando houver tráfego:
  - **Tipo de Operação:** SMP ou STFC (baseado na EOT Vivo e no tipo de serviço da EOT)
  - **Tipo de Produto (Remuneração):** TU-RL, TU-RIU, VU-M, MMS, SMS, Transporte, SIP, Bill&Keep, TU-COM, entre outros — baseado na tabela Descritor_Remuneração; **Bill&Keep** exige adicionalmente que **ambas** as EOTs tenham tipo de serviço = SMP
- Tabela **SMP**: uma linha por EOT móvel da Vivo
- Tabela **STFC**: EOTs fixas da Vivo (011, 200 e 9\*\*), **sumarizadas numa única linha**, com as colunas EOT Operadora, Referência e Tráfego
- Determinar se a contestação é por **Referência** ou por **Tráfego**
- Identificar a **modalidade** via `CONT_PROC_MASCARA`
- **Destino: banco**, não a aba `Contest`
- Desejável: **Grupo Horário** na visualização do resumo, por filtro ou desdobramento de linhas

**⚠️ Pendência crítica — a borda de 1% não fecha entre as fontes.**

| Fonte | Texto |
|---|---|
| V2, regra de negócio | "Se a diferença do `R$_Bruto` for **menor que 1%**, o processo segue sem contestação... Se for **superior** deve ser criada a contestação" |
| V2, fórmula da aba Contest | "se a variação for **maior que +1%** ele marca com S" |
| PDF de HUs | "< 1%: flag N" / "**>= 1%**: flag S" |

Exatamente 1% cai em lugares diferentes conforme a fonte. E o "+1%" sugere que o **sinal** importa (só contesta se a operadora cobrou **a mais**), o que as outras fontes não dizem. Isso é uma regra de decisão financeira — precisa ser resolvida antes da implementação, não durante.

**⚠️ Pendência CBS/IBS.** Os novos impostos aparecem nos arquivos, mas não há regra sobre se entram na sumarização e na comparação desta etapa.

---

## HU-11 — Exibição dos dados de contestação no WebFat 🟢

**Descrição.** O WebFat exibe na aba **Contestação** todos os casos com variação identificada. O analista seleciona quais incluir na contestação e escolhe **com ou sem retenção**. Só depois dessa sinalização o robô prossegue.

**Critérios de aceitação vigentes.**
- Listagem por operadora, EOT e tipo de remuneração
- Analista seleciona as linhas a contestar e define com/sem retenção
- WebFat recalcula e exibe os novos valores conforme a seleção
- **O RPA só prossegue após sinalização explícita do analista**

**O que mudou.** Apenas nomenclatura: "cava Expectativa" (erro de digitação da doc antiga) → "**aba Contestação**".

**Papel arquitetural.** Esta HU é o **ponto de sincronização humana** do processo inteiro — é ela que justifica o corte entre RPA 2 e RPA 3. A V2 reforça: *"a escolha se a contestação será retida ou não dependerá do usuário, após sua análise"*.

**⚠️ Zona cinzenta de escopo.** A V2 sugere criar uma **nova tela no WebFat** ("consolidado despesas", com filtro e marcação de erro) e diz "para isso, uma nova tela no Webfat foi desenvolvida". Não está claro se o desenvolvimento do WebFat faz parte deste projeto ou é entrega de outra frente. Se for de outra frente, **é uma dependência externa** do RPA 2 e do RPA 3. Destinatário: GP.

---

# ÉPICO 4 — Geração de Arquivos para Contestação e Carga AGI

## HU-12 — Geração do arquivo `_EXT` para carga no AGI 🟢

**Descrição.** Para **todos** os cenários (sem contestação, com retenção, sem retenção), o robô monta `DE_AGI_D_{aaaamm}_TBRA_X_{NOMEOPERADORA}_EXT` na pasta `AGI` da operadora, copiando o Detraf consolidado da operadora até o valor bruto a partir da célula A2.

**Critérios de aceitação vigentes.**

| Campo | Valor |
|---|---|
| ORIGEM | `"E"` |
| EXPECTATIVA | `"S"` para linhas contestadas **COM retenção**; `"N"` para as demais |
| INSERÇÃO | `"EXTERNO"` |
| AJUSTE | em branco |
| OBS | em branco |
| REMUNERACAO | conforme tabela Descritor_Remuneração |

- Salvo em `\\lagoa\...\Operadoras\{operadora}\{ano}\{aaaamm}\AGI`

**Status.** Sem mudanças relevantes na V2.

**⚠️ Nota.** A V2 diz que o robô "**abre o arquivo de nome** `DE_AGI_D_AAAAMM_TBRA_X_{OPERADORA}_EXT`", como se ele já existisse na pasta — provavelmente um modelo pré-posicionado. Isso significa uma **dependência de arquivo-modelo em pasta de rede**. Se não existir, o comportamento não está definido.

---

## HU-13 — Geração do arquivo `_INT` para carga no AGI 🟢

**Descrição.** **Apenas** no cenário de contestação **COM retenção**, o robô monta `DE_AGI_D_{aaaamm}_TBRA_X_{NOMEOPERADORA}_INT` na mesma pasta `AGI`, com a expectativa Vivo **somente do tráfego contestado com retenção**, da primeira coluna até `R$_Bruto`, colando em A2.

**Critérios de aceitação vigentes.**
- Gerado **exclusivamente** para contestação COM retenção
- Dados da aba `TBRA` (expectativa Vivo) do arquivo de contestação
- Somente as linhas do tráfego contestado com retenção
- ORIGEM = `"E"`, EXPECTATIVA = `"N"`, INSERÇÃO = `"EXTERNO"`, AJUSTE e OBS em branco
- REMUNERACAO conforme tabela Descritor_Remuneração

**Status.** Sem mudanças relevantes na V2.

**Nota sobre o par EXPECTATIVA.** No `_EXT` o campo EXPECTATIVA marca `"S"` justamente nas linhas contestadas com retenção — as mesmas que geram o `_INT` com EXPECTATIVA = `"N"`. Os dois arquivos são complementares: o `_EXT` carrega o que a operadora apresentou (sinalizando o que está retido) e o `_INT` carrega o que a Vivo esperava para esse mesmo tráfego.

---

## HU-14 — Geração do arquivo `_ENV` e carta para a operadora 🟢

**Descrição.** Para contestação COM e SEM retenção, o robô produz o arquivo que vai anexado à contestação e a carta formal numerada.

**Critérios de aceitação vigentes — arquivo `_ENV`.**
- Criado em `\\lagoa\...\{operadora}\{ano}\{aaaamm}\Contestações`
- Cópia de `Base_Contestação_{operadora}_{mês}_M` salva como `Base Contestação_{operadora}_{mês}_ENV`
- Mantém **apenas** as abas `Contest` e `TBRA`; as demais são apagadas
- Nas duas abas, remove as linhas do que **não** será contestado

**Critérios de aceitação vigentes — carta.**
- Criada na mesma pasta `Contestações`, a partir de um **modelo pré-existente por operadora**
- Numeração **CT sequencial**, obtida lendo a última numeração em `\\lagoa\...\Correspondências Enviadas\CT\{ano}` e usando a seguinte (ex.: último CT 362 → nova carta CT-363)
- Dentro da carta, altera: número, data, mês do Detraf no "Assunto:", e o tipo de contestação ("SEM retenção" / "COM retenção")
- Inclui no corpo as tabelas da aba `Contest` do `_ENV`, **sem a coluna "Contestação a enviar"**
- Cópia da carta salva em `\\lagoa\...\Correspondências Enviadas\CT\{ano}`

**Status.** Sem mudanças relevantes na V2.

**⚠️ Contradição com a HU-09.** O `_ENV` é definido como cópia da `Base_Contestação_..._M`, mas a HU-09 (V2) determina que a `Base_Contestação` **não é mais gerada como arquivo**. Então: o `_ENV` é gerado do zero a partir do banco? Ou a `Base_Contestação` continua existindo só para servir de origem ao `_ENV`? Esta é provavelmente uma das duas exceções da frase *"todas as planilhas foram substituídas por banco, exceto dois arquivos"* — mas isso é **inferência**, não está escrito. Pendência de alta prioridade.

**⚠️ Risco de concorrência.** A numeração CT é estado compartilhado em **pasta de rede**, lido e incrementado sem transação. Duas execuções simultâneas (ou o robô junto com um humano) podem gerar cartas com o mesmo número. A V2 não define trava. Ver [`../04-relatorios/riscos-conhecidos.md`](../04-relatorios/riscos-conhecidos.md).

**⚠️ Dependência não versionada.** Existe um **modelo de carta por operadora** em pasta de rede. Se o robô depende de um modelo por operadora, o cadastro de uma operadora nova exige criar o modelo manualmente — passo não documentado.

---

## HU-15 — Envio do e-mail de contestação à operadora ⚠️

**Descrição.** O robô cria e envia o e-mail de contestação às operadoras.

**Critérios de aceitação vigentes.**
- Destinatários: contatos das operadoras
- Assunto: `CONTESTAÇÃO_TBRA|{NOMEDAOPERADORA}_{MESDODETRAF}`
- Corpo: *"Prezados, Segue a contestação para a sua análise e validação, referente ao mês {mesdodetraf}. Att,"*
- Anexos: **carta** + `Base Contestação_{operadora}_{mês}_ENV`
- ⚠️ **Disparo automático sem aprovação manual: em dúvida** — ver pendência

**⚠️ Pendência bloqueante.** O critério V1 "disparo automático após sinalização do analista — sem aprovação manual" se apoiava na frase *"o robô deve enviar o e-mail, sem necessidade de autorização do usuário, após a escolha do analista"*. Essa frase **foi removida do corpo principal da V2** e só sobrevive no **bloco de conteúdo duplicado ao final do documento**, que é remanescente de uma versão antiga — não a redação vigente.

Isso importa porque o e-mail é **irreversível e externo**: uma vez enviado a uma operadora, uma contestação incorreta não se desfaz. Confirmar explicitamente com a área cliente (PO / GP) antes de manter o critério como está.

**Por que esta HU é um projeto de origem inteiro (P5).** Não há explicação na documentação. É a menor unidade de escopo entre os seis projetos — uma única HU. ⚠️ Possível que o P5 contenha mais do que a HU-15 sugere (por exemplo, toda a camada de e-mail, compartilhada com o RPA 1). A confirmar na análise do código.

**Nota.** A V2 diz *"Destinatários: contatos das operadoras"* sem dizer onde esse cadastro vive. A V1 referenciava a "tabela de contatos do WebFat" — a mesma que a V2 deixou de usar para identificar a operadora (HU-02). Se a tabela continua existindo para contatos, isso precisa ser confirmado.

---

## HU-16 — Geração do arquivo `CONT_PROC` para carga AGI 🟡

**Descrição.** Para contestação COM e SEM retenção, o robô parte do modelo `CONT_PROC_MASCARA Geral 202506`, filtra pelo nome da empresa, preenche as colunas e salva as linhas alteradas num arquivo `.xls` novo: `CONT_PROC_MASCARA_{nomeoperadora}_{aaaamm}`.

**Critérios de aceitação vigentes.**

| Coluna | Campo | Conteúdo |
|---|---|---|
| C | `ID_OPERADORA_JV` | EOT da Vivo que gera a contestação — uma linha móvel (SMP) e uma fixa |
| D | `ID_OPERADORA_PREST` | EOT da operadora contestada |
| E | `ID_PERIODO_REF` | mês do Detraf da contestação |
| F | `ID_PERIODO_TRAF` | mês do tráfego contestado — se houver mais de um, abre em mais linhas |
| G | `DEBIT_CREDIT` | `"D"` (despesa) |
| H | `FLAG_PAG_REC` | `"P"` se retida, `"R"` se não retida |
| I | `DURACAO` | minutagem total da linha, **com sinal negativo** |
| W | `VLR_BRUTO` | valor bruto total da linha, **com sinal negativo** |
| AB | `ID_MODALIDADE` | número da modalidade, das colunas I e J da aba `Remuneração` |
| AG | `REMUNERACAO_FIXA` | tipo de remuneração da contestação, baseado no descritor |

- É possível consolidar numa única linha por EOT Vivo (uma móvel, uma fixa), **mas respeitando** a diferença de tipo de remuneração e mês de tráfego — **não se pode sumarizar remunerações diferentes**
- Salvo em formato `.xls`
- Um único documento pode conter contestação de mais de uma operadora
- **Após gerar, atualiza o campo `tipo_contestacao` de `tbl_rpa_log_detraf_despesa_contestacao`** *(novo na V2)*

**⚠️ Erro na própria V2.** A descrição da coluna W diz: *"VLR_BRUTO — preencher com a **minutagem** total da linha (colocar o sinal negativo na frente)"* — copiada da coluna I. Pelo nome do campo e pelo contexto, deveria ser o **valor bruto**, não a minutagem. Erro de redação evidente, mas precisa de confirmação formal.

**⚠️ Dependência de modelo externo.** O `CONT_PROC_MASCARA Geral 202506` tem o ano-mês **no nome**. Não está definido se o modelo é atualizado mensalmente, nem onde o robô encontra a versão vigente.

---

# ÉPICO 5 — Carga no AGI

⚠️ **Nenhum dos seis projetos de origem foi indicado como dono deste épico.** Pasta reservada: `projetos-origem/projeto-7-epico-5-carga-agi/`.

## HU-17 — Upload dos arquivos `_EXT`/`_INT` no AGI 🟡⚠️

**Descrição.** O robô acessa o AGI por automação de interface, navega em **Detraf > Importar Dados**, clica em Upload e seleciona os arquivos finais `_EXT` e `_INT`, **um de cada vez**.

**Critérios de aceitação vigentes.**
- Navegação em `Detraf > Importar Dados`
- Upload do `_EXT` em **todos** os cenários
- Upload do `_INT` **apenas** em contestação COM retenção — nos demais cenários o `_INT` nem chega a ser criado
- Um arquivo por vez, aguardando confirmação antes de prosseguir

**⚠️ Pendência.** A V2 cita, antes de `_EXT`/`_INT`, um terceiro arquivo: **`DE_EBT_TBRA_TLF_202509_C_INT_MODELO.xlsx`**. O documento **não explica o que ele é nem o que se faz com ele**. Pelo nome (`_MODELO`, período fixo `202509`, `TLF`) parece um arquivo-modelo, talvez da expectativa TLF — mas isso é especulação. Levantar com a área cliente / GP antes de detalhar os critérios.

---

## HU-18 — Upload do arquivo de contestação no AGI 🟡

**Descrição.** O robô navega em **Contestação > Gerenciar**, clica em Upload, seleciona `CONT_PROC_MASCARA_{operadora}_{aaaamm}` e clica em **Salvar**.

**Critérios de aceitação vigentes.**
- Navegação em `Contestação > Gerenciar`
- Upload do arquivo `CONT_PROC_...`
- Confirmação com clique em "Salvar"
- **Após salvar, atualiza o campo `carga_agi`** com o status da carga em `tbl_rpa_log_detraf_despesa_contestacao` *(novo na V2)*

**Nota de ordem.** A carga do Detraf (HU-17) precede a da contestação (HU-18): a contestação referencia tráfego que precisa já estar no AGI.

---

# ÉPICO 6 — Encontro de Contas

## HU-19 — Preenchimento do Encontro de Contas com despesa 🔴

**Descrição vigente (V2).** O robô pega o valor de despesa total apresentado pela operadora (minutos e valor bruto) e **atualiza `tbl_rpa_log_detraf_despesa_contestacao`**, sempre com **sinal negativo**.

**Critérios de aceitação vigentes.**
- Campos atualizados: `minutos_operadora`, `vb_operadora`, `minutos_diferenca`, `vb_diferenca`, `minutos_variacao_perc`, `vb_variacao_perc`
- Aberto por **EOT da Vivo** e **tipo de remuneração**
- Valor **sempre negativo** (é despesa)
- Mapeamento descritor → coluna via tabela Descritor_Remuneração

**O que mudou.** Mesma mudança estrutural do Épico 3: em vez de colar valores na **planilha** de Encontro de Contas, grava em **campos do banco**.

**⚠️ Pendência.** O critério V1 *"coluna de contestação preenchida quando houver retenção"* — que na V2 aparece como *"Quando acontece a contestação com retenção, o robô também preenche a coluna de contestação da remuneração no EC... com o valor bruto da Diferença apresentada aba Contest"* — **só existe no bloco duplicado/antigo**. Confirmar se o comportamento foi absorvido pelos campos `*_diferenca` ou se ficou pendente de definição.

**⚠️ Sobreposição de responsabilidade.** A V2 também diz, no Épico 2: *"Após a validação de cada arquivo, deve-se popular o Encontro de Contas com o valores total apresentado pela operadora, aberto por tipo de remuneração e EOT Vivo."* Isso é praticamente o texto da HU-19, mas colocado **logo após a validação** — ou seja, no RPA 2, não no RPA 3. Há um conflito de posicionamento no fluxo: o EC é preenchido logo após a validação, ou depois da contestação? Pendência.

---

## HU-20 — Verificação do Relatório Receitas e Despesas no AGI 🟡⚠️

**Descrição.** O robô acessa `AGI > Relatórios > Detraf > Receitas e Despesas`, filtra por período do Detraf, natureza **"D"** e nome da operadora, sumariza `Vlr. Bruto` e compara com o subtotal de despesa do Encontro de Contas. Repete para todas as operadoras.

**Critérios de aceitação vigentes.**
- Acesso a `Relatórios > Detraf > Receitas e Despesas`
- Filtro por período, natureza "D" e operadora
- Sumarização de `Vlr. Bruto` (a V2 nota que "é possível extrair os dados da tela")
- Comparação com o subtotal de despesa do EC (a V2 cita a **célula O87** da planilha — ⚠️ referência que não sobrevive à migração para banco)
- **Comparar as colunas CBS, IBS MUNICIPAL e IBS ESTADUAL** *(novo na V2)*
- Sinalização de inconsistência quando divergir
- Repetição para todas as operadoras do ciclo

**⚠️ Pendência de escopo — esta HU pode ser descartada.** A própria V2 questiona: *"Caso a conferência com o robô dê errado, qual o processo? Esse processo trata-se de uma dupla checagem, conferir com o solicitante se esse processo vale a pena ou não ser mantido."*

Duas perguntas em aberto: (a) a HU-20 continua no escopo? (b) o que acontece quando os valores divergem — não há tratamento definido além de "sinalizar".

**Impacto na unificação.** Se a HU-20 for descartada, o **P6 fica reduzido à HU-21** e a cisão do projeto entre RPA 3 e RPA 4 deixa de ser necessária. Confirmar **antes** de planejar a cisão.

**⚠️ Referência órfã.** "Célula O87 da planilha de Encontro de Contas" pressupõe uma planilha que a V2 substituiu por banco. A V2 também escreve, de forma reveladora: *"O robô precisa chegar nesse valor consolidado e copular [popular] em algum lugar. Parecendo com a planilha dos encontro de contas."* — o destino do consolidado do EC **não está definido**.

---

## HU-21 — Identificação de tráfego recuperado e retificação AGI 🟢

**Descrição.** Quando o robô identifica que um tráfego contestado em mês anterior foi **recuperado** no mês corrente (variação negativa), entra no AGI em `Contestação > Gerenciar`, localiza o processo da contestação anterior e adiciona um evento do tipo **"Recuperação"**.

**Critérios de aceitação vigentes.**
- Identificação de tráfego recuperado (variação negativa no mês corrente sobre tráfego contestado no mês anterior)
- Filtro no AGI por **Período** (sempre o período em tratamento) e **Empresa**
- Seleção do **Id Processo** correto na grade retornada
- Clique em "+ Adicionar"; campo "Tipo Evento" = **"Recuperação"**
- Preenchimento dos valores, correspondentes à **diferença entre o Detraf da Vivo e o Detraf da operadora**:

| Campo | Fórmula |
|---|---|
| Duração | Minutos da tabela |
| Valor Líquido | `VB × 0,9635` |
| Valor PIS/Cofins | `VB − Valor Líquido` |
| Valor Bruto Negociado | `VB` |

- Clique em "Salvar"

**Status.** Sem mudanças relevantes na V2.

**Onde a detecção acontece.** Note que a **identificação** da necessidade de retificação está descrita no Épico 4 (*"Neste momento também, ele identifica se ele precisa fazer alguma retificação de contestação"*), mas a **execução** é o RPA 4. Isso significa que o RPA 3 e o RPA 4 compartilham o critério de detecção, ou que o RPA 4 o reavalia por conta própria. ⚠️ Decisão de desenho que depende da análise do código.

**⚠️ Pendência declarada pela própria V2.** No filtro por Empresa: *"Operadoras que no anexo 5 possui um nome que sofrem alterações durante o processo, esse ponto de atenção precisa ser estudado. Pendência Vivo para mapear essa ponta."* O nome da operadora pode mudar entre o mês da contestação e o mês da retificação — e o filtro do AGI é por nome. Sem regra definida.

**Nota sobre o fator 0,9635.** Corresponde a PIS/Cofins de 3,65% sobre o valor bruto. É uma **constante embutida na especificação** — e as premissas 10.3/10.4 da V2 exigem que regras e tabelas sejam editáveis pelo usuário. ⚠️ Verificar, na análise do código, se está hardcoded. Com a chegada de CBS/IBS a partir de 2027, essa alíquota tende a mudar.

---

# HU-22 (proposta) — Tratamento das colunas de novos impostos CBS/IBS 🆕

**Ainda não existe como história.** Proposta registrada em `Analise_Mudancas_V2_por_Historia.md`.

**O que a V2 diz.**
- *"Será destacado em nota fiscal e demonstrativos do DETRAF os novos impostos CBS e IBS, apenas como informativo nesse primeiro ano, a partir de 2027 será feito o devido recolhimento."*
- *"Arquivos de DETRAF VIVO, Carga Geral do AGI e relatórios do AGI possuem três colunas CBS, IBS MUNICIPAL E IBS ESTADUAL."*
- HU-20: *"Comparar colunas CBS, IBS MUNICIPAL E IBS ESTADUAL."*

**Escopo provável.** Estrutura (layout dos arquivos), validação (Épico 2), comparação/sumarização (Épico 3) e conferência (HU-20).

**⚠️ Tudo em aberto.**
- Onde as colunas ficam no layout? São 16, 17 e 18, ou deslocam as existentes?
- O arquivo **da operadora** também as terá, ou só o Detraf Vivo?
- Entram na comparação da HU-10 ou são só informativas?
- A partir de quando são obrigatórias?
- Nenhum projeto de origem foi indicado como responsável.

**Conexão com o risco de 2028.** A V2 registra que *"existe a projeção para que em 2028 mais um imposto seja inserido na tabela deslocando as colunas"*. Junto com *"os ajustes nos arquivos são dinâmicos; a solução não poderá ficar condicionada a regras de negócio que podem ser alteradas a qualquer momento"*, isso é um requisito não-funcional explícito: **o layout dos arquivos precisa ser configurável, não fixo**. ⚠️ Se os projetos de origem lerem colunas por posição fixa, isso é dívida a tratar na unificação — mas o desenho da solução depende da análise do código.
