# Glossário — DETRAF MVP2

Termos que aparecem na documentação e são necessários para ler o resto destes documentos.

> Onde a definição não está na documentação e foi inferida do contexto, está marcado com ⚠️.

---

## Domínio de telecomunicações

**Detraf** — Documento de Declaração de Tráfego e de Prestação de Serviços. Documento mensal em que operadoras declaram o tráfego trocado entre si e o valor devido. Neste projeto, trata-se apenas do Detraf de **despesa**: o que outras operadoras cobram da Vivo.

**EOT** — Entidade Operadora de Telecomunicações. Código que identifica uma operadora (ou uma unidade dela) nos arquivos de Detraf. Cada arquivo tem uma EOT **Credora** (quem cobra) e uma **Devedora** (quem paga). Na despesa, a Devedora é sempre da Vivo.

**Anexo 5** — Tabela pública mantida pela ABR Telecom (`abrtelecom.com.br/padronizacao`) com o cadastro das EOTs. Colunas usadas por este projeto: **nome fantasia**, **Tipo de Serviço** (SMP/STFC), **Região** e **Concessão**. É a fonte de verdade para identificar a operadora e determinar regra de descritor e tarifa.

**SMP** — Serviço Móvel Pessoal. Telefonia móvel.

**STFC** — Serviço Telefônico Fixo Comutado. Telefonia fixa.

**PMS** — Poder de Mercado Significativo. Operadora classificada pela Anatel como detentora de PMS está sujeita a tarifas reguladas em situações em que operadoras sem PMS não estão. No Anexo 5, identificado pela coluna **Concessão** — valor `"P"` indica PMS. Relevante na HU-06.

**Bill&Keep** — Regime em que operadoras trocam tráfego sem cobrança recíproca. ⚠️ Provável origem do sufixo `_BK` da HU-06: a V2 lista Bill&Keep entre os tipos de produto, com a ressalva de que **ambas** as EOTs precisam ter tipo de serviço = SMP — as mesmas condições da regra do `_BK`.

**Descritor** — Código na coluna 7 (`DESC`) de cada linha do Detraf, que indica o tipo de tráfego e determina a remuneração aplicável. Sua primeira e última letra carregam significado:

| Padrão | Remuneração |
|---|---|
| final "V" | VUM (Credora do tipo SMP) |
| final "L" | TU-RL (Credora do tipo STFC) |
| início "L" e final "I" | TURIU1 |
| início ≠ "L" e final "I" | TURIU2 |
| final "C" | TU-COM |

A relação completa está em `tbl_detraf_mapeamento_descritores` (banco WebFat) e na planilha Descritor_Remuneração.

**Remuneração** — Tipo de valor cobrado pelo uso da rede. Os tipos citados: **VU-M** (Valor de Uso de rede Móvel), **TU-RL** (Tarifa de Uso de rede Local), **TU-RIU** (Tarifa de Uso de rede Interurbana, subdividida em TURIU1 e TURIU2), **TU-COM**, MMS, SMS, Transporte, SIP, Bill&Keep.

**Tarifa regulada** — Valor definido pela Anatel, alterado anualmente em **fevereiro**, por combinação de remuneração × região × grupo horário. Consultada em `tbl_detraf_tarifas`. Tarifas **não reguladas** são negociadas entre operadoras: apenas o formato é validado, não o valor.

**Região I, II, III** — Regiões do Plano Geral de Outorgas, determinadas pela EOT Credora no Anexo 5. Cada uma tem sua tabela de tarifas. Há uma exceção documentada: `RII (943) – SERCOMTEL (042/043)`.

**GH — Grupo Horário** — Faixa horária do tráfego. Valores aceitos: `S`, `R`, `N`, `D`. A tarifa pode variar por GH (notadamente a VU-M em horário reduzido). Quando o campo `gh` está nulo em `tbl_detraf_tarifas`, a tarifa vale para todos os grupos.

**Referência (mês de)** — Mês do Detraf em si. Coluna 3. Aceita apenas o mês corrente −1.

**Tráfego (mês de)** — Mês em que o tráfego efetivamente ocorreu. Coluna 4. Aceita mês corrente −1, −2 ou −3 — ou seja, um Detraf pode conter tráfego de até três meses atrás.

**Rel** — Coluna 6. Marca linhas de total/subtotal com `1`; linhas de tráfego trazem `0` ou vazio. **Linhas com `Rel = 1` são excluídas** nas consolidações (HU-09).

**Expectativa** — Cálculo que a própria Vivo faz do quanto deveria pagar, gerado pelo **ICT**. É contra ela que o Detraf da operadora é comparado. Os arquivos ficam em "Detrafs Enviados" e no servidor do WebFat.

**Contestação** — Discordância formal da Vivo com o valor cobrado pela operadora, quando a diferença ultrapassa o limiar de 1%. Formalizada por carta numerada + e-mail + arquivos, e registrada no AGI.

**Contestação COM retenção** — A Vivo contesta **e retém** o pagamento do valor contestado. Além dos artefatos usuais, carrega no AGI a expectativa do ICT (`_INT`) apenas para o tráfego contestado. No `CONT_PROC`, `FLAG_PAG_REC = "P"`.

**Contestação SEM retenção** — A Vivo contesta mas **paga** enquanto discute. Não gera arquivo `_INT`. No `CONT_PROC`, `FLAG_PAG_REC = "R"`.

**Retificação / Recuperação** — Quando um tráfego contestado é recuperado pela Vivo no mês seguinte (variação negativa), a contestação anterior é corrigida no AGI com um evento do tipo "Recuperação" (HU-21).

**Encontro de Contas (EC)** — Consolidação de tudo que a Vivo deve e tem a receber de cada operadora no período. Neste projeto, alimentado apenas do lado da **despesa**, sempre com sinal negativo. Na V2, deixou de ser planilha e passou a ser campos de `tbl_rpa_log_detraf_despesa_contestacao`.

**Modalidade de contestação** — Classificação da contestação, escolhida nas colunas I (número), J (descrição) e K (tipo) da aba `Remuneração` do arquivo `CONT_PROC_MASCARA`. O número vai para a coluna `ID_MODALIDADE`.

**Contestação por Referência / por Tráfego** — Duas formas de recortar a contestação: pelo mês do Detraf ou pelo mês em que o tráfego ocorreu. O robô decide qual usar (HU-10).

---

## Sistemas

**AGI** — Sistema financeiro da Vivo onde o Detraf e as contestações são registrados. Acesso por automação de interface desktop, e exige estar logado no autenticador de rede Vivo. Telas usadas: `Detraf > Importar Dados`, `Contestação > Gerenciar`, `Relatórios > Detraf > Receitas e Despesas`.

**WebFat** — Sistema da Vivo com duas faces neste projeto: o **banco de dados** (tabelas `tbl_*`) onde o robô grava tudo, e a **interface do analista** (abas Detraf e Contestação), onde ele acompanha o processamento e decide sobre as contestações. Tem também um **servidor de arquivos** onde os Detrafs são replicados.

**ICT** — Sistema que gera os arquivos de expectativa da Vivo. Fora do escopo desta automação; os arquivos já chegam prontos no servidor do WebFat.

**Lagoa** — Servidor de arquivos de rede. Raiz: `\\lagoa\DI\DI-A\DI-A1\Padronização de Detraf - Grupo Técnico\`.

**Outlook Desktop Classic** — Cliente de e-mail automatizado pelo robô. Conta `tbr00848.br@telefonica.com`, caixa `detrafTBRA.br@telefonica.com`.

**TBRA** — Telefônica Brasil. Identificador da Vivo nos nomes de arquivo e no assunto dos e-mails.

**TLF / VIVO** — Pastas que separam os arquivos de expectativa Vivo, "com D no final" (V2). ⚠️ O critério exato de separação não está explicado.

---

## Tabelas do banco WebFat

| Tabela | Conteúdo |
|---|---|
| `tbl_detraf_tarifas` | Tarifas reguladas. Campos citados: `tipo_remuneracao`, `regra_desc`, `região`, `eot_vivo`, `eot_operadora`, `gh`, `tarifa`, `data_inicio`, `data_fim` |
| `tbl_detraf_mapeamento_descritores` | Relação descritor × tipo de remuneração |
| `tbl_rpa_log_detraf_despesa_arquivos` | Um registro por arquivo processado. Campo `tipo_registro` ∈ {`DETRAF`, `EXPECTATIVA`, `ERRO`} |
| `tbl_rpa_log_detraf_despesa_contestacao` | Base de contestação e Encontro de Contas. Campos citados: `tipo_contestacao`, `carga_agi`, `minutos_operadora`, `vb_operadora`, `minutos_diferenca`, `vb_diferenca`, `minutos_variacao_perc`, `vb_variacao_perc` |

⚠️ A V2 não publica o DDL. As listas de campos são as citadas no texto e não devem ser assumidas como completas.

---

## Convenções de nome de arquivo

| Marca | Significado |
|---|---|
| **`_D_`** | Presente no nome dos arquivos de expectativa **convertidos** que devem ser processados. Filtro obrigatório na HU-04 e HU-09 |
| **`_BK`** | Cópia gerada para o caso SMP não-PMS com descritor L…V (HU-06) |
| **`_ERRO`** | Arquivo com os registros que falharam alguma regra de validação (HU-04) |
| **`_M`** | Sufixo da `Base_Contestação` "modelo", origem do `_ENV` (HU-14) |
| **`_ENV`** | "Pronto para envio" — arquivo de contestação anexado ao e-mail da operadora (HU-14) |
| **`_EXT`** | Arquivo de carga no AGI com o Detraf **da operadora** — todos os cenários (HU-12) |
| **`_INT`** | Arquivo de carga no AGI com a **expectativa Vivo** — só contestação COM retenção (HU-13) |
| **`CT`** | Prefixo da numeração sequencial das cartas de contestação (HU-14) |

**Padrões completos:**
- `DE_AGI_D_{aaaamm}_TBRA_X_{NOMEOPERADORA}_EXT`
- `DE_AGI_D_{aaaamm}_TBRA_X_{NOMEOPERADORA}_INT`
- `Base_Contestação_{operadora}_{mesdodetraf}` / `..._M` / `..._ENV`
- `CONT_PROC_MASCARA_{nomeoperadora}_{aaaamm}` (`.xls`)
- Assunto do e-mail: `CONTESTAÇÃO_TBRA|{NOMEDAOPERADORA}_{MESDODETRAF}`

---

## Estrutura de pastas de rede

Raiz: `\\lagoa\DI\DI-A\DI-A1\Padronização de Detraf - Grupo Técnico\`

```
Operadoras\{operadora}\{ano}\{aaaamm}\
    ├── Detrafs Recebidos\     ← arquivos da operadora (HU-03)
    ├── Detrafs Enviados\      ← expectativa Vivo (ICT)
    ├── Contestações\          ← _ENV e cartas (HU-14)
    ├── AGI\                   ← _EXT e _INT (HU-12, HU-13)
    └── Encontro de Contas\    ← planilha de EC (legado; V2 migrou para banco)

Correspondências Enviadas\CT\{ano}\   ← cópia das cartas + contador de numeração (HU-14)
```

A estrutura do mês é criada **copiando a pasta do mês anterior** com toda a sua estrutura interna (HU-03).

---

## Impostos e valores

**PIS/Cofins** — Coluna 13 do Detraf. Na retificação (HU-21), o Valor Líquido é `VB × 0,9635` e o PIS/Cofins é a diferença — ou seja, alíquota de **3,65%**.

**ICMS** — Coluna 14 do Detraf.

**CBS / IBS Municipal / IBS Estadual** — Três colunas novas da reforma tributária, presentes em Detraf Vivo, Carga Geral do AGI e relatórios do AGI. **Informativas no primeiro ano; recolhimento a partir de 2027.** ⚠️ Sem HU correspondente e sem posição definida no layout.

**R$_Liq / R$_Bruto** — Colunas 12 e 15. O **`R$_Bruto` é a métrica de decisão**: é sobre a variação dele que a regra de 1% opera.

---

## Termos da automação

**RPA** — Robotic Process Automation. Aqui, cada um dos quatro robôs independentes do desenho de destino.

**Usuário robótico** — Conta de serviço com que o robô acessa os sistemas. A V2 remete a uma "tabela interna GSA".

**Data de corte** — Momento a partir do qual o RPA 1 para de aceitar novos arquivos do mês e o RPA 2 pode processar. ⚠️ **Ainda não definida** pela área cliente. É a pendência mais bloqueante do projeto.

**Gatilho** — Condição que dispara cada RPA. Foi o critério de corte usado para separar os quatro robôs. Ver [`responsabilidades-dos-rpas.md`](responsabilidades-dos-rpas.md).
