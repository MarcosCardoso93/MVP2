# Mapa: Projetos de Origem × Épicos × Histórias × RPAs

> ⚠️ **Fotografia da etapa documental (2026-07-30).** Este documento foi escrito
> **antes** de qualquer código chegar, e descreve o entendimento daquele momento.
> Vários pontos já mudaram — em especial: o Épico 5 **tem** projeto (o P7, entregue
> em 2026-08-04), e as HUs 12 a 19 estão implementadas e orquestradas.
>
> **Fonte do estado atual:** `docs/04-relatorios/duvidas-pendentes.md` (pendências),
> `matriz-de-rastreabilidade.md` (HUs) e `unificado/README.md` (código).

Este é o documento central da unificação. Ele responde à pergunta operacional da próxima etapa: **quando o código do projeto X chegar, para onde ele vai?**

> ⚠️ Todo o mapeamento abaixo é derivado da **documentação**. Ele descreve onde o código *deveria* estar. A análise dos fontes pode revelar que a realidade difere — e essa diferença é, ela própria, um dos achados mais importantes da próxima etapa.

---

## 1. A divisão informada dos seis projetos

| Projeto | Escopo informado | HUs resultantes |
|---|---|---|
| Projeto 1 | Épico 1 | HU-01, HU-02, HU-03 |
| Projeto 2 | Épico 2 | HU-04, HU-05, HU-06, HU-07, HU-08 |
| Projeto 3 | Épico 3 | HU-09, HU-10, HU-11 |
| Projeto 4 | Épico 4 + HU-19, **exceto HU-15** | HU-12, HU-13, HU-14, HU-16, HU-19 |
| Projeto 5 | HU-15 | HU-15 |
| Projeto 6 | HU-20 + HU-21 | HU-20, HU-21 |

**Cobertura:** 20 das 21 HUs... na verdade, **19**. Faltam duas.

---

## 2. ⚠️ Lacuna: o Épico 5 não está em nenhum projeto

**HU-17** (upload `_EXT`/`_INT` no AGI) e **HU-18** (upload `CONT_PROC` no AGI) não aparecem em nenhum dos seis projetos, embora sejam responsabilidade explícita do RPA 3.

Verificação por eliminação:
- Projeto 4 é "Épico 4 + HU-19" — o Épico 4 termina na HU-16
- Projeto 5 é apenas a HU-15
- Projeto 6 é HU-20 + HU-21
- Nenhum outro projeto alcança o Épico 5

**Tratamento adotado.** Pasta reservada `projetos-origem/projeto-7-epico-5-carga-agi/`, com o achado registrado como pergunta bloqueante. Três hipóteses a testar na análise:

1. **O código está dentro do Projeto 4.** Plausível — o P4 gera exatamente os arquivos que o Épico 5 carrega, e a fronteira entre "gerar `CONT_PROC`" e "subir `CONT_PROC`" é fina. Se confirmado, a pasta 7 é descartada e o P4 passa a cobrir HU-12..19.
2. **Existe um sétimo projeto ainda não mencionado.** A pasta reservada já o acomoda.
3. **HU-17/HU-18 não foram implementadas.** Nesse caso a unificação herda uma lacuna funcional, e o RPA 3 fica incompleto — o que precisa ser sinalizado ao GP antes de qualquer estimativa.

**Como testar rapidamente** (primeira coisa a fazer quando o código do P4 chegar): procurar, no P4, automação de UI apontando para `Detraf > Importar Dados` e `Contestação > Gerenciar`, e escrita no campo `carga_agi`. Se estiver lá, hipótese 1 confirmada.

---

## 3. Mapa completo

| HU | Título | Épico | Projeto de origem | RPA destino | Status V2 |
|---|---|---|---|---|---|
| HU-01 | Leitura e organização do inbox | 1 | P1 | **1** | 🟡⚠️ |
| HU-02 | Identificação da operadora | 1 | P1 | **1** | 🔴 |
| HU-03 | Salvamento em pastas de rede | 1 | P1 | **1** | 🟡 |
| HU-04 | Validação estrutural das colunas | 2 | P2 | **2** | 🟡 |
| HU-05 | Validação da tarifa regulada | 2 | P2 | **2** | 🟡 |
| HU-06 | Arquivo `_BK` (SMP não-PMS) | 2 | P2 | **2** | 🟢 |
| HU-07 | Erro L-L (STFC) | 2 | P2 | **2** | 🔴 fundir na HU-04 |
| HU-08 | Registro dos arquivos no WebFat | 2 | P2 | **2** | 🟡 |
| HU-09 | Consolidação da Base Contestação | 3 | P3 | **2** | 🔴 planilha→banco |
| HU-10 | Análise de contestação por EOT | 3 | P3 | **2** | 🟡🔴 |
| HU-11 | Exibição no WebFat (analista) | 3 | P3 | **2** | 🟢 |
| HU-12 | Arquivo `_EXT` | 4 | P4 | **3** | 🟢 |
| HU-13 | Arquivo `_INT` | 4 | P4 | **3** | 🟢 |
| HU-14 | Arquivo `_ENV` + carta | 4 | P4 | **3** | 🟢 |
| HU-15 | E-mail de contestação | 4 | **P5** | **3** | ⚠️ |
| HU-16 | Arquivo `CONT_PROC` | 4 | P4 | **3** | 🟡 |
| HU-17 | Upload `_EXT`/`_INT` no AGI | 5 | ⚠️ **nenhum** (P7 res.) | **3** | 🟡⚠️ |
| HU-18 | Upload contestação no AGI | 5 | ⚠️ **nenhum** (P7 res.) | **3** | 🟡 |
| HU-19 | Preenchimento do Encontro de Contas | 6 | P4 | **3** | 🔴 planilha→banco |
| HU-20 | Verificação Relatório Rec. e Desp. | 6 | **P6** | **3** | 🟡⚠️ pode ser descartada |
| HU-21 | Tráfego recuperado e retificação | 6 | **P6** | **4** | 🟢 |
| HU-22 | Tratamento CBS/IBS | — | ⚠️ **nenhum** | ⚠️ ? | 🆕 não existe |

---

## 4. Os quatro tipos de transformação

Nenhum projeto vira um RPA por simples renomeação. Cada um cai num destes quatro casos:

### 4.1 Correspondência direta — 1 projeto → 1 RPA

**Apenas o Projeto 1 → RPA 1.**

É o caso mais simples, e mesmo assim não é trivial: a HU-02 mudou de mecanismo na V2 (domínio do remetente → EOT/Anexo 5), então o código pode implementar uma regra revogada. Ver [`entendimento-das-historias.md`](entendimento-das-historias.md#hu-02--identificação-da-operadora-).

### 4.2 Convergência — N projetos → 1 RPA

**P2 + P3 → RPA 2.** Dois projetos que se sucedem no fluxo (validar, depois comparar). A fronteira entre eles é onde a duplicação é mais provável: leitura de arquivo Detraf, resolução de EOT no Anexo 5, mapeamento descritor→remuneração e acesso ao banco WebFat aparecem nos dois.

**P4 + P5 + P6(HU-20) + P7? → RPA 3.** Quatro origens num RPA. É o ponto de maior risco da unificação: quatro bases de código provavelmente com convenções, configurações e camadas de acesso diferentes, que precisam virar um `main.py` coerente.

### 4.3 Cisão — 1 projeto → 2 RPAs

**P6 → RPA 3 (HU-20) + RPA 4 (HU-21).** É o único projeto que precisa ser dividido. Ambas as HUs automatizam o AGI, então é provável que compartilhem a camada de automação de UI — que, uma vez cindida, vira **candidata natural à base compartilhada**.

⚠️ **Antes de planejar a cisão, confirmar se a HU-20 continua no escopo.** A própria V2 questiona se a dupla checagem "vale a pena ou não ser mantida". Se for descartada, o P6 fica reduzido à HU-21 e vira caso 4.1.

### 4.4 Órfão — 0 projetos → responsabilidade de um RPA

**Épico 5 (HU-17, HU-18) → RPA 3.** Ver seção 2.
**CBS/IBS (HU-22) → indefinido.** Nem HU, nem projeto, nem RPA designado.

---

## 5. Distribuição de carga por RPA

| RPA | HUs | Origens a consolidar | Complexidade de unificação |
|---|---|---|---|
| RPA 1 | 3 | 1 | **Baixa** — mas HU-02 pode exigir reescrita |
| RPA 2 | 8 | 2 | **Média** — convergência com alta chance de duplicação; HU-09 muda de planilha para banco |
| RPA 3 | 9 | 3 confirmadas + 1 órfã | **Alta** — maior fragmentação, artefatos irreversíveis (e-mail), automação de UI do AGI |
| RPA 4 | 1 | fração do P6 | **Baixa em volume, média em risco** — depende da cisão do P6 e do mecanismo de disparo, ambos indefinidos |

---

## 6. O que este mapa deliberadamente **não** decide

⚠️ Tudo abaixo depende da análise do código:

- **Se a fronteira dos projetos coincide com a fronteira das HUs.** É perfeitamente possível que o P2 contenha código do Épico 3, ou que o P4 já contenha o Épico 5. O mapa acima descreve a intenção, não a implementação.
- **Se há código compartilhado hoje.** Os seis projetos podem já compartilhar bibliotecas, ou terem sido feitos por pessoas diferentes sem qualquer reuso.
- **Qual versão da regra cada projeto implementa.** As HUs marcadas 🔴 (02, 07, 09, 10, 19) mudaram estruturalmente na V2. Código escrito antes da V2 implementa regra revogada.
- **Onde ficam as fronteiras de módulo dentro de cada RPA.** Fora do escopo desta etapa por decisão explícita.
- **Se algum projeto contém escopo fora deste MVP** — por exemplo código do fluxo de Receita (ATA0000571/567/572), que é escopo de outras demandas.

---

## 7. Ordem de análise recomendada

**P1 → P2 → P3 → P4 → P7 → P5 → P6**

Justificativa:
- **Segue o fluxo de dados.** Cada projeto é lido já sabendo o que o anterior produziu, o que torna as fronteiras e as duplicações visíveis por comparação em vez de por busca.
- **P4 antes de P7** porque a análise do P4 é o que responde se o Épico 5 está lá dentro.
- **P5 e P6 por último** porque são pequenos e, chegando ao fim, os candidatos a componente compartilhado já estarão mapeados — o P5 (uma única HU de e-mail) e o P6 (duas HUs de automação do AGI) funcionam bem como **teste de confirmação** desses candidatos: se a camada de e-mail identificada nos projetos anteriores não servir ao P5, a abstração está errada.

Procedimento detalhado em [`../05-proxima-etapa/roteiro-analise-tecnica.md`](../05-proxima-etapa/roteiro-analise-tecnica.md).
