# Inventário — Projeto 1: Épico 1 (Captura de Arquivos via E-mail)

- **Pasta:** `projetos-origem/projeto-1-epico-1-captura/`
- **HUs esperadas:** HU-01, HU-02, HU-03
- **RPA de destino:** RPA 1 (correspondência 1:1)
- **Recebimento:** [`00-recebimento-p1-a-p4.md`](00-recebimento-p1-a-p4.md)

---

## 1. Estrutura e execução

```
src/
├── config/       configuration.py · logger_config.py · outlook_config.py
├── controllers/  outlook_controller.py · processamento_controller.py
├── main/         process_handle.py
├── models/
│   ├── dto/         arquivo_para_processar · operadora_resultado · registro_rastreamento
│   └── repository/  rastreamento · repositorio_arquivos · repositorio_cache · repositorio_tabelas
├── services/     competencia · email_filter · operadora · outlook · processamento
└── utils/        filesystem.py
tests/            8 arquivos
```

| Item | Valor |
|---|---|
| Ponto de entrada | `src/main/process_handle.py::run()` — **sem `main.py`** |
| Fluxo | `ProcessamentoController.processar()` → `OutlookController.capturar_arquivos()` → `ProcessamentoService.executar()` |
| Granularidade | por arquivo, dentro de um laço por e-mail |
| Paralelismo | não |
| Trava de execução | não |
| Estado acumulado | contadores de resumo em memória (não impede processar isoladamente) |

**P1 é o outlier estrutural dos quatro.** É o único com `models/dto/`, o único com `utils/filesystem.py` em vez de `utils/gerenciador_arquivos.py`, e o único sem `utils/utils.py`, `decoradores.py` e `historico_arquivos.py`. Foi construído em separado dos demais.

---

## 2. Mapeamento HU → código

| HU | Status | Onde |
|---|---|---|
| HU-01 — leitura e organização do inbox | ✅ implementada | `services/outlook_service.py`, `services/email_filter_service.py`, `controllers/outlook_controller.py` |
| HU-02 — identificação da operadora | ⚠️ **híbrida** | `services/operadora_service.py` |
| HU-03 — salvamento em pastas de rede | ⚠️ **parcial** | `services/processamento_service.py`, `utils/filesystem.py` |

### Código sem HU correspondente

| Onde | O quê | Classificação |
|---|---|---|
| `models/repository/rastreamento_repository.py` + `models/dto/registro_rastreamento.py` | Grava um JSON vinculando cada arquivo baixado ao `entry_id` do e-mail de origem | **Escopo extra necessário** — é o que permite ao P2 responder à operadora (HU-04). Não tem HU própria; é infraestrutura de integração entre RPA 1 e RPA 2 |
| `controllers/outlook_controller.py::responder_por_arquivo` | Cria rascunho de resposta ao e-mail | Pertence conceitualmente à HU-04 (crítica à operadora), mas está no P1. **O P2 tem a sua própria** (`notificacao_email.py`) |

---

## 3. 🔴 Versão da regra implementada

### HU-02 — identificação da operadora: **híbrida V1 + V2**

`OperadoraService.obter_operadora(caminho_arquivo, sender_email)` tenta, nesta ordem:

1. **V2 (correta):** `extrair_eot_arquivo()` lê a coluna Credora do anexo (`.csv` via `csv`, Excel via `openpyxl`), busca a EOT no Anexo 5 e retorna o nome fantasia
2. **V1 (revogada):** se a EOT falhar, `extrair_texto_busca_operadora()` usa a parte do domínio do remetente antes do primeiro ponto (`contato@vivo.com.br` → `vivo`) e busca por nome

O caminho primário está **aderente à V2**, e a ordem das operações é a exigida: abre o anexo antes de decidir onde salvar. O fallback é regra revogada.

**Decisão:** manter o fallback com aviso em log, marcado como pendente de remoção. Retirá-lo agora mudaria comportamento — precisa de decisão do PO (Q16).

### HU-03 — salvamento: **parcial**

`construir_caminho_saida(raiz, operadora, ano, competencia)` produz `{raiz}/{OPERADORA}/{YYYY}/{YYYYMM}` — falta o nível final `Detrafs Recebidos` que a V2 exige.

| Critério da V2 | Status |
|---|---|
| Salvar na pasta de rede da operadora/mês | ⚠️ parcial — sem a subpasta `Detrafs Recebidos` |
| **Salvar também no servidor do WebFat** | ❌ **não implementado** |
| Criar a pasta do mês copiando a estrutura do mês anterior | ❌ **não implementado** — só `mkdir` |
| Registro em `tbl_..._arquivos` | ✅ `_registrar_log_despesa` |
| Reenvio com mesmo nome sobrescreve e reprocessa | ⚠️ a confirmar |

---

## 4. Pontos de I/O

**Outlook** (`services/outlook_service.py`, 310 linhas, `pywin32` COM): lê pasta configurável, move para subpasta de processados, baixa anexos com retry (`OUTLOOK_MAX_RETRY`), cria rascunho de resposta. Conta e pastas por env.

**Sistema de arquivos:** lê `DIRETORIO_ENTRADA`, escreve em `DIRETORIO_SAIDA/{operadora}/{ano}/{aaaamm}`. Caminho construído por função dedicada (`filesystem.construir_caminho_saida`) — **bom**, é o padrão a levar para a base comum. Grava `_rastreamento.json`.

**Banco:** `tbl_anexo5_processado` (leitura — nome fantasia por EOT), `tbl_detraf_despesa_arquivos` (escrita). `repositorio_tabelas.py` tem só 3 métodos — o menor dos quatro.

**Anexo 5:** via banco, tabela `tbl_anexo5_processado`, com cache singleton.

---

## 5. Regras de negócio

| Regra | Situação |
|---|---|
| Filtro: e-mails sem a palavra "CONTESTAÇÃO" | ✅ `email_filter_service.py` |
| Filtro por mês de referência | ✅ `competencia_service.py` |
| Apenas `.csv` e Excel | ✅ `EXTENSOES_PERMITIDAS` por env |
| Competência = mês anterior | ✅ trata virada de ano |
| **Dia de liberação (`DETRAF_DIA_LIBERACAO=5`)** | ⚠️ **regra V1** — ver abaixo |
| Normalização de EOT | ⚠️ **divergente** — ver abaixo |

### ⚠️ Dia de liberação — regra revogada, parametrizada

`OutlookController.deve_processar_hoje()` usa `DETRAF_DIA_LIBERACAO` (default 5) — é o critério V1 *"varredura diária após o dia 05"*, que a V2 removeu sem substituir. Como está por variável de ambiente, é o **melhor placeholder possível** para a data de corte enquanto a Q1 não é respondida. Mantém-se como está.

### ⚠️ Normalização de EOT diverge dos outros três

```python
# P1 — operadora_service.py::_normalizar_eot
if texto.isdigit():
    return texto.zfill(3)     # não remove parte decimal

# P2/P3/P4 — repositorio_tabelas.py::_tratar_eot
if "." in eot:
    eot = eot.split(".")[0]   # remove decimal ANTES
if eot.isdigit() and int(eot) < 100:
    return eot.zfill(3)
```

Lendo de Excel, uma EOT que chega como float vira `"11.0"`: o P1 não remove o `.0`, falha o `isdigit()`, devolve `"11.0"` e **não casa com o Anexo 5** — caindo no fallback por domínio. É defeito, não escolha. Reconciliado na base comum.

---

## 6. Tratamento de erro e logging

`ProcessamentoService.executar()` captura por arquivo e segue para o próximo — **aderente à V2**. Arquivos não identificados vão para `_salvar_nao_identificado`. Contadores de resumo ao final.

⚠️ **`logger_config.py` do P1 diverge:** nível `DEBUG` (os outros usam `INFO`) e `opt(depth=1)` nos métodos do wrapper, onde P2/P3/P4 usam `depth=2`. Com `depth=1`, o log reporta `logger_config.py` como origem em vez do código que chamou — **defeito**, não escolha.

---

## 7. Aderência às premissas 10.3 / 10.4

| Item | Constante no código? |
|---|---|
| Valores de tarifa | ✅ não usa tarifas |
| Mapeamento descritor → remuneração | ✅ não usa |
| Limiares | ✅ `DETRAF_DIA_LIBERACAO` por env |
| **Índices de coluna fixos** | ⚠️ `INDICE_COLUNA_FALLBACK = 0` — mas só como *fallback*: busca a coluna pelo nome `"credora"` primeiro. Aceitável |
| EOTs da Vivo | ✅ não usa |
| Caminhos de rede | ✅ todos por env |

**Nenhuma violação relevante.** É o projeto mais limpo dos quatro nesse quesito.

---

## 8. Testes

8 arquivos em `tests/`, cobrindo `competencia_service`, `email_filter_service`, `filesystem`, `operadora_service`, `processamento_service`, `rastreamento_repository`, `repositorio_arquivos`, `repositorio_tabelas`. Sem cobertura de `outlook_service` (depende de COM) nem dos controllers.

---

## 9. Candidatos a componente compartilhado

| Candidato | Onde | Observação |
|---|---|---|
| Consulta ao Anexo 5 | `repositorio_tabelas.py::buscar_nome_fantasia_por_eot` | 2ª ocorrência em P2/P3/P4 |
| Cache de tabelas | `repositorio_cache.py` | 4 ocorrências |
| Log de despesa | `repositorio_tabelas.py::salvar_dados_tabela_despesa` | 3 ocorrências (P1/P2/P3) |
| Construção de caminho | `utils/filesystem.py::construir_caminho_saida` | Confrontar com `estrutura_pastas.py` do P4 |
| Competência / mês anterior | `competencia_service.py`, `filesystem.mes_anterior` | Equivalente ao `ANO_MES_REFERENCIA` de P2/P3/P4 |
| Logging | `config/logger_config.py` | 4 ocorrências |
| Configuração | `config/configuration.py` | 4 ocorrências |
| Automação do Outlook | `services/outlook_service.py` | 2ª ocorrência em P2 (`notificacao_email.py`) |

---

## 10. Achados

### 🔴 Críticos
Nenhum.

### 🟡 Relevantes
1. **HU-03 incompleta** — falta o salvamento no servidor do WebFat e a criação da pasta do mês por cópia da estrutura anterior
2. **Normalização de EOT defeituosa** (§5)
3. **`logger_config.py` com `depth` errado** (§6)
4. **Fallback V1 na HU-02** (§3) — mantido de propósito

### 🟢 Observações
- Ausência de `main.py` (comum aos quatro)
- `outlook_service.py` não tem teste — inevitável sem mock de COM
- `responder_por_arquivo` no P1 sobrepõe-se a `notificacao_email.py` do P2

---

## 11. Conclusão

**Escopo real × esperado:** cobre as três HUs, com HU-02 híbrida e HU-03 parcial.

**Aderência à V2:** boa no mecanismo principal (identificação por EOT), com dois pontos abertos por decisão de negócio (dia de liberação, fallback por domínio) e dois por implementação incompleta (WebFat, cópia de estrutura).

**Complexidade de migração:** **baixa** — origem única, sem duplicação interna. O trabalho é trocar `utils/filesystem.py` pelos equivalentes da base comum e reconciliar EOT e logger.
