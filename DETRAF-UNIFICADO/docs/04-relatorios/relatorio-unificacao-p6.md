# Relatório — Unificação do Projeto 6 (HU-20)

**Data:** 2026-08-05 · **Escopo:** P6 → RPA 3

---

## 🔴 Veio metade do projeto

O Projeto 6 era o último previsto e devia trazer **duas** HUs: a HU-20 (RPA 3) e a
HU-21 (RPA 4). **Veio só a HU-20.**

`Retificação`, `Recuperação` e o fator `0,9635` não aparecem em nenhum `.py` —
só no README do briefing.

**Consequências:**

- o **RPA 4 continua com um `README.md` e nada mais**;
- o **marco M7 segue bloqueado**;
- a **Q17** (nome de operadora que muda), que a própria V2 declara como *"Pendência
  Vivo para mapear essa ponta"*, continua sem uso prático.

Registrado como pendência **N12**.

---

## 🔴 A credencial do AGI está em dois arquivos

`projeto-6-h20-h21/H20/.env` traz `RPA_DETRAF_DESPESA_AGI_USER` (8 caracteres) e
`RPA_DETRAF_DESPESA_AGI_PASSWORD` (28) **preenchidos** — **os mesmos tamanhos do
Projeto 7**. Provavelmente a mesma credencial.

Deixa de ser cópia isolada: são dois arquivos que circularam fora do controle de
versão. **A rotação, já escalada, fica mais urgente.** O risco R20 foi atualizado.

O arquivo se contradiz: a linha 1 diz *"Segredos NÃO ficam aqui"* e as linhas 4 e 5
os preenchem. O `load_dotenv` injeta o `.env` antes do `os.environ.get`, então o
valor do arquivo vence.

---

## A pergunta que sobreviveu à chegada do projeto

A **Q7** era *"a HU-20 continua no escopo?"*, marcada como *"depende do Projeto 6"*.
O projeto chegou e **a pergunta continua aberta** — porque nunca foi sobre o
código:

> ¶706 — *"Esse processo trata-se de uma **dupla checagem**, conferir com o
> solicitante se esse processo vale a pena ou não ser mantido."*
> ¶705 — *"Caso a conferência com o robô dê errado, qual o processo?"*

Os dois parágrafos são **acréscimo da V2** — não existem no bloco antigo.

**Decisão desta rodada: migrar assim mesmo**, atrás do kill-switch
`PERMITIR_ACESSO_AGI`. São ~190 linhas úteis; se a HU for descartada, sai inteira.
A severidade da Q7 subiu para 🔴: agora há código esperando uma decisão.

---

## As três decisões que destravaram a migração

| Ponto | Decisão | Efeito |
|---|---|---|
| **Fonte do Encontro de Contas** | **banco** | Some a leitura do `.xlsx` pela célula `O87` |
| **CBS / IBS** | **incluir as três** | O ¶702 deixa de estar sem implementação |
| **Sinalização** | **`.xlsx` na pasta comum de logs** | O esqueleto do P6 vira comportamento definido |

### O EC vinha de uma planilha, por uma célula fixa

O Projeto 6 lia um `.xlsx` por `openpyxl`, achava a aba com
`operadora.upper() in nome.upper()` e pegava a célula `O87`. Três fragilidades numa
linha: `"OI"` casaria com qualquer aba que contenha "oi". O próprio autor marcava o
risco — pode ser preciso um de-para entre `"AMPERNET"` (AGI) e
`"Ampernet Telecom"` (aba).

A decisão **confirma a V2** (¶374: *"Todas as planilhas deste processo foram
substituídas por banco"*). Novo
`repositorio_tabelas.obter_subtotal_despesa_por_operadora`, que soma
`vb_operadora` por `empresa`.

### O dado de CBS/IBS já estava no pacote

O CSV entregue **dentro do próprio projeto** tem **22 colunas**, incluindo
`Vlr. CBS`, `Vlr. IBS Estadual` e `Vlr. IBS Municipal`. O código comparava só
`Vlr. Bruto` — literalmente uma tupla de um elemento.

⚠️ O `H20/README.md` afirma que as colunas são *"idênticas às usadas no exemplo de
Receita"* e lista 17 — **contrariado pelo arquivo entregue junto com ele**.

**Isso avança a Q6 sem fechá-la.** Continuam pendentes o **layout dos arquivos**
(o "isnumos" do ¶368) e a **contra-parte no EC**: a tabela só tem `vb_operadora`,
sem coluna de imposto. As três são **somadas e reportadas**; a comparação segue só
sobre o valor bruto. Não é omissão — é o limite do dado que existe.

---

## O kill-switch existia só no nome

O Projeto 6 declarava `PERMITIR_ACAO_AGI` em `config.py:24` e **nunca o lia** —
busca global retorna essa única ocorrência. Era decorativo, diferente do P5 e do
P7, onde o kill-switch de fato guarda a ação.

Agora é `PERMITIR_ACESSO_AGI`, **separado do `PERMITIR_UPLOAD_AGI` de propósito**:
dá para conferir o relatório sem liberar a carga, que é o que altera dado. A HU-20
é leitura — mas **abre o aplicativo e faz login em produção**, e não há ambiente de
teste (Q20).

---

## O que o Projeto 6 ensinou sobre o AGI

`AGI_config.py` é **idêntico ao do Projeto 7 em 283 das 286 linhas**. As três
divergências são **melhorias**, de quem rodou contra produção:

| Ponto | `agi.py` tinha | P6 |
|---|---|---|
| Título do diálogo de download | literal em inglês | **regex bilíngue** — o idioma da VM varia |
| Reescrita do CSV pós-download | `open("w")` direto | `chmod` + **retry 5×** tratando `PermissionError` |

As duas foram portadas. O `_corrigir_aspas_impares` unificado tinha exatamente o
bug de permissão que o P6 aprendeu a contornar: logo após o download, o antivírus
ou o processo que salvou ainda seguram o arquivo — e a falha viria **depois** de o
robô já ter aberto o AGI, logado e baixado, que é o pedaço caro.

`baixar_remessa` também deixou de ser órfão e ganhou o docstring certo: dizia que
*"quem vai usá-lo é o RPA 4"*, mas a HU-21 usa `Contestação > Gerenciar`, não esta
tela. Quem usa é a **HU-20, no próprio RPA 3**.

### A promoção do AGI para `comum/` continua rejeitada

O P6 era o teste de confirmação previsto na ficha. O resultado é misto:

- ✅ **a abstração está validada** — serviu a um terceiro caso de uso **sem uma
  linha de alteração de API**;
- ❌ **mas o critério C1 continua falhando** — a HU-21 não veio, então o AGI segue
  com **um consumidor só**.

O gatilho de reavaliação muda de *"quando o P6 chegar"* para **"quando a HU-21
chegar"**.

---

## Verificação

| Critério | Resultado |
|---|---|
| `python executar_testes.py` | ✅ **554 testes**, quatro suítes verdes (eram 530) |
| Testes novos da HU-20 | ✅ 24 |
| Com `PERMITIR_ACESSO_AGI=false`, o AGI não é aberto | ✅ provado por dublê que explode ao primeiro toque |
| O subtotal do EC vem do banco | ✅ nenhum `openpyxl` nem célula `O87` |
| As três colunas de imposto entram na soma | ✅ |
| `projetos-origem/` intocada | ✅ |
| Credencial em código ou `.env.example` | ✅ nenhuma |

---

## O que fica

**Bloqueado no cliente:** **Q7** (a V2 pede confirmação de que a HU-20 deve
existir — subiu para 🔴), Q6 (layout do "isnumos" e contra-parte de CBS/IBS no EC),
**N11** (limiar de tolerância — o `0,01` veio do P6 com TODO), e as demais já
registradas.

**Não entregue:** **N12** — a HU-21. O RPA 4 continua sem código e o M7 bloqueado.

**Sem ambiente:** a HU-20 nunca rodou a partir deste repositório contra o AGI —
mas as duas planilhas de inconsistência que vieram no pacote são **evidência de
que o fluxo rodou** na origem, contra produção.
