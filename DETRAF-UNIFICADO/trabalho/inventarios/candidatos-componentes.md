# Catálogo de Componentes Candidatos — P1 a P5 e P7

> Consolidado num documento em vez de uma ficha por candidato: com 19 candidatos que se referenciam, a leitura em tabela é melhor. Critérios em [`criterios-de-compartilhamento.md`](../../docs/02-planejamento/criterios-de-compartilhamento.md).

**Contexto que muda a aplicação do critério C1.** O critério exige duas ocorrências em **RPAs de destino diferentes**. Aqui só há três RPAs em jogo, e P2+P3 convergem no mesmo (RPA 2). Então:

- ocorrência em P1 e P2 → RPA 1 e RPA 2 → **conta**
- ocorrência em P2 e P3 → ambas RPA 2 → **não conta** para promover; é unificação interna ao RPA 2
- ocorrência em P2/P3 e P4 → RPA 2 e RPA 3 → **conta**

---

## Veredictos

| # | Candidato | Ocorrências (RPA) | C1 | C2 | C3 | C4 | Veredicto |
|---|---|---|---|---|---|---|---|
| 1 | `logger_config.py` | P1,P2,P3,P4 (1,2,3) | ✅ | ✅ | ✅ | ✅ | **PROMOVIDO** |
| 2 | `utils.py` (`salvar_debug_log`) | P2,P3,P4 (2,3) | ✅ | ✅ | ✅ | ✅ | **PROMOVIDO** |
| 3 | `decoradores.py` (`log_execucao`) | P2,P3,P4 (2,3) | ✅ | ✅ | ✅ | ✅ | **PROMOVIDO** |
| 4 | `historico_arquivos.py` | P2,P3,P4 (2,3) | ✅ | ✅ | ✅ | ✅ | **PROMOVIDO** |
| 5 | `gerenciador_arquivos.py` | P2,P3,P4 (2,3) | ✅ | ✅ | ✅ | ✅ | **PROMOVIDO** |
| 6 | `repositorio_cache.py` | P1,P2,P3,P4 (1,2,3) | ✅ | ✅ | ✅ | ✅ | **PROMOVIDO** |
| 7 | Anexo 5 (EOT, nome fantasia, tipo de serviço, concessão, região) | P1,P2,P3,P4 (1,2,3) | ✅ | ✅ | ✅ | ✅ | **PROMOVIDO** |
| 8 | Normalização de EOT | P1,P2,P3,P4 (1,2,3) | ✅ | ✅ | ✅ | ✅ | **PROMOVIDO** |
| 9 | Log de despesa (`salvar_dados_tabela_despesa`) | P1,P2,P3 (1,2) | ✅ | ✅ | ✅ | ✅ | **PROMOVIDO** |
| 10 | Mês de referência / mês anterior | P1,P2,P3,P4 (1,2,3) | ✅ | ✅ | ✅ | ✅ | **PROMOVIDO** |
| 11 | Estrutura de pastas / caminho de saída | P1,P4 (1,3) | ✅ | ✅ | ✅ | ✅ | **PROMOVIDO** |
| 12 | Constantes de layout e nomenclatura | P2,P3,P4 (2,3) | ✅ | ✅ | ⚠️ | ✅ | **PROMOVIDO (parcial)** |
| 13 | Classificação de descritor → remuneração | P2,P3,P4 (2,3) | ✅ | ✅ | ⚠️ | ✅ | **PROMOVIDO (parcial)** |
| 14 | Configuração (`configuration.py`) | P1,P2,P3,P4 (1,2,3) | ✅ | ✅ | ✅ | ✅ | **PROMOVIDO** |
| 15 | Regra de variação / flag S-N | P3,P4 (2,3) | ✅ | ✅ | ⚠️ | ✅ | **PROMOVIDO com ressalva** |
| 16 | Contrato de `tbl_..._contestacao` | P3,P4 (2,3) | ✅ | ✅ | ✅ | ✅ | **PROMOVIDO** |
| 17 | Validação de tarifa | P2,P3 (2,2) | ❌ | ✅ | ⚠️ | ✅ | **REJEITADO (C1)** |
| 18 | Acesso ao Outlook (COM) | P1,P2,P5 (1,2,3) | ✅ | ✅ | ✅ | ✅ | **PROMOVIDO** (era ADIADO) |
| 19 | Camada do AGI (`AGI_config.py`) | P7 (3) | ❌ | ✅ | ✅ | ✅ | **REJEITADO (C1)** |

---

## Notas por candidato

> ⚠️ **Caminhos de destino (2026-08-05).** As notas abaixo prometem
> `comum/dados/anexo5.py`, `log_despesa.py`, `descritores.py` e `contestacao.py`.
> **Nenhum existe:** tudo foi consolidado em `repositorio_cache.py`,
> `repositorio_tabelas.py` e `tabelas.py`. O veredicto de cada candidato continua
> valendo; o caminho, não.


### 1 — `logger_config.py` → `comum/config/logger_config.py`
Base: **P3** (superset com `%`-args). Nível por `LOG_LEVEL` (default `INFO`). `depth` uniformizado em 2. Ver duplicação D-04.

### 2, 3, 4 — `utils.py`, `decoradores.py`, `historico_arquivos.py` → `comum/utils/`, `comum/arquivos/historico.py`
Idênticos nos três. Migração literal.

### 5 — `gerenciador_arquivos.py` → `comum/arquivos/gerenciador.py`
União: 17 funções comuns + `separar_e_salvar_por_mascara` (P2) + `exportar_dataframe_para_excel` (P3) + `salvar_planilhas` (P4).

### 6 — `repositorio_cache.py` → `comum/dados/repositorio_cache.py`
**Parâmetro:** `TABELAS_CACHE` por RPA. **Alteração obrigatória:** remover o caminho absoluto de `P2:82`.

### 7, 8 — Anexo 5 e normalização de EOT → `comum/dados/anexo5.py`
União dos métodos dos quatro. Normalização: base P2/P3/P4 (remove parte decimal). Fecha o defeito do P1 — ver D-07.

### 9 — Log de despesa → `comum/dados/log_despesa.py`
Nome da tabela em constante única. ⚠️ Divergência `tbl_detraf_despesa_arquivos` (código) × `tbl_rpa_log_detraf_despesa_arquivos` (V2) registrada para o PO.

### 10 — Mês de referência → `comum/dominio/competencia.py`
Expõe string (`ANO_MES_REFERENCIA`) e o par ano/competência do P1. Padronizar o nome da variável de override.

### 11 — Estrutura de pastas → `comum/arquivos/estrutura_pastas.py`
Base: **P4**. Subpastas por env. Fecha o vazio da HU-03 no P1.

### 12 — Constantes → `comum/config/constantes.py` — ⚠️ **parcial por C3**
Base: `constantes_epico4.py` do P4, **com `COL_REL = 5`** (correção — D-14).

**Não entram na base comum**, por dependerem de pendência aberta:
- colunas CBS/IBS (Q6) — a definir
- o perfil de layout da **expectativa Vivo**, que é genuinamente outro arquivo (inventário do P3 §4)

Constantes exclusivas do RPA 3 (textos da carta, `ID_MODALIDADE`) ficam no RPA 3 — falham C1.

### 13 — Descritor → remuneração → `comum/dados/descritores.py` — ⚠️ **parcial por C3**
Base: **P4** (desambigua por `produto`). ⚠️ **Descritores de transporte ficam de fora** — a V2 declara a regra pendente (Q12).

### 14 — Configuração → `comum/config/configuration.py`
União das quatro. **Alterações obrigatórias:** `load_dotenv()` sempre (fecha o desvio do P2); credencial só por env; SQLite só por env.

### 15 — Regra de variação → `comum/dominio/variacao.py` — ⚠️ **ressalva**
Formalmente falharia C3 (a Q2 está aberta), mas o plano aprovado **decidiu a regra pela documentação**, o que fecha o critério na prática. Promovido com a pendência residual (`>` vs `>=`) registrada. Ver D-13.

Implementação: base = operadora, com sinal, `>= 1%`, par ausente = 100%.

### 16 — Contrato de `tbl_..._contestacao` → `comum/dados/contestacao.py`
Colunas, chave e valores iniciais num ponto só. Resolve D-15 (`remuneracao` ausente).

### 17 — Validação de tarifa — **REJEITADO por C1**
Só P2 e P3, ambos no RPA 2. É unificação **interna ao RPA 2**, não base comum.
**Reavaliar quando:** o Épico 5 ou outro projeto precisar validar tarifa.
→ Fica em `rpa2_validacao_apuracao/`.

### 18 — Acesso ao Outlook — **PROMOVIDO** (2026-08-04; era ADIADO)
→ `comum/integracoes/outlook.py` + `outlook_config.py`

Ficou adiado esperando o P5, que era o teste de confirmação. **A hipótese se confirmou:**
- **C1 ✅** — três consumidores em três RPAs: 1 lê a caixa, 2 responde à operadora, 3 envia a contestação;
- **C3 ✅** — a Q5 foi respondida e a HU-15 chegou implementada no P5;
- **C4 ✅** — ler, responder e enviar cabem na mesma classe. `send_email` é `send_email_com_anexos` sem anexo, e `create_reply_draft` é `responder_email(enviar=False)`.

**Base: o P1**, não o P5 — o standalone do P5 navega por inbox (modelo antigo) e o P1 por pasta nomeada, que é o que a V2 exige. Do P5 vieram os dois métodos de envio, que era o que faltava. Ver D-19.

### 19 — Camada do AGI (`AGI_config.py`) — **REJEITADO (C1)**

**Teste de confirmação feito em 2026-08-05, e o resultado é misto.**

O Projeto 6 chegou — mas **só com a HU-20**. A HU-21, que era o segundo consumidor
previsto, não veio, e o RPA 4 continua sem código.

- ✅ **A abstração está validada.** O `AGI_config.py` do P6 serviu a um **terceiro
  caso de uso** (`Relatórios > Receitas e Despesas`) **sem uma linha de alteração
  de API** — 283 das 286 linhas idênticas às do P7, e as três divergências são
  melhorias, não adaptações;
- ❌ **Mas o C1 continua falhando.** O AGI segue com **um consumidor só**: o
  RPA 3. Promover agora seria exatamente a antecipação que o critério impede.

**Reavaliar quando:** a **HU-21** chegar (antes era "quando o P6 chegar"). Até lá
fica em `rpa3_contestacao_agi_ec/src/integracoes/agi.py`, agora com as duas
correções que o P6 trouxe (ver D-23).

---

## Resumo

| Veredicto | Qtd |
|---|---|
| **PROMOVIDO** | 14 |
| **PROMOVIDO (parcial / com ressalva)** | 3 |
| **REJEITADO** | 2 |
| **ADIADO** | 0 |

**Nenhum componente foi promovido por antecipação.** Todos têm ocorrência real localizada, com arquivo e linha nos inventários.
