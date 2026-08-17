# Inventário — Projeto 3: Épico 3 (Batimento Detraf × Expectativa)

- **Pasta:** `projetos-origem/projeto-3-epico-3-batimento/`
- **HUs esperadas:** HU-09, HU-10, HU-11
- **RPA de destino:** RPA 2 (converge com o P2)
- **Recebimento:** [`00-recebimento-p1-a-p4.md`](00-recebimento-p1-a-p4.md)

---

## 1. Estrutura e execução

```
src/
├── config/       configuration.py · logger_config.py
├── controllers/  batimento_detraf_controller.py
├── main/         process_handle.py
├── models/repository/  repositorio_cache.py · repositorio_tabelas.py (545 linhas)
├── services/     batimento_detraf.py (329) · criacao_arquivo_contestacao.py (528)
└── utils/        decoradores · gerenciador_arquivos · historico_arquivos · utils
```

| Item | Valor |
|---|---|
| Ponto de entrada | `src/main/process_handle.py::run()` — **sem `main.py`** |
| Fluxo | `BatimentoDetrafController.batimento_detraf()` → `BatimentoDetrafService.executar()` → `CriacaoArquivoContestacao.criar_arquivo_contestacao()` |
| Granularidade | lote, com agrupamento por operadora (`_mapear_arquivos_por_operadora`) |
| Fim de linha | **LF** — os outros três usam CRLF |

**Sem testes.**

---

## 2. Mapeamento HU → código

| HU | Status | Onde |
|---|---|---|
| HU-09 — consolidação | ✅ **V2 + V1** | `criacao_arquivo_contestacao.py` — grava no banco **e** gera a planilha |
| HU-10 — análise por EOT e remuneração | ✅ com defeitos | `_gerar_aba_contest`, `_aplicar_analise_contestacao` |
| HU-11 — exibição no WebFat | ➖ N/A | É tela do WebFat, não do RPA. O RPA só popula a tabela |

---

## 3. 🔴 Versão da regra implementada

### HU-09 — implementa **as duas versões**

`criar_arquivo_contestacao()` faz os dois caminhos:
- **V2:** `_preparar_dados_persistencia_contestacao` → `salvar_dados_tabela_contestacao` → `tbl_rpa_log_detraf_despesa_contestacao` ✅
- **V1:** `_exportar_planilha_operadora` → gera `Base_Contestação_{operadora}_{mês}.xlsx` em `DIRETORIO_BASE_CONTESTACAO`, com abas de dados, `RESUMO` e `Contest`

**Isto responde à pergunta Q4.** A planilha continua sendo gerada — é ela que o P4 espera consumir na HU-14 para produzir o `_ENV`. Na prática, a `Base_Contestação` **é uma das "duas exceções"** da frase *"todas as planilhas foram substituídas por banco, exceto dois arquivos"*.

**Decisão de migração:** manter os dois caminhos. O banco é o destino normativo; a planilha é insumo do `_ENV` (HU-14). Registrar para confirmação do PO.

---

## 4. 🔴 Achados críticos de layout de arquivo

Confrontando o código com as fixtures reais do P4 (`tests/fixtures/`), que vêm de arquivos de produção.

### Layout real observado

| Campo (V2) | V2 col | **ALGAR** (operadora) | **Vivo `_D`** (expectativa) |
|---|---|---|---|
| Credora | 1 | 0 `cd_eot_bil` | 1 `EOT_CREDORA` |
| Devedora | 2 | 1 `cd_eot_rel` | 2 `EOT_DEVEDORA` |
| Referencia | 3 | 2 `mes_ref` | 3 `PERIODO_REFERENCIA` |
| Tráfego | 4 | 3 `mes_traf` | 4 `PERIODO_TRAFEGO` |
| POI | 5 | 4 `poi` | 5 `POI` |
| Rel | 6 | **5** `tipo_relatorio` | **6** `REL` |
| DESC | 7 | **6** `descritor` | **8** `DESCRITOR` |
| GH | 8 | 7 `grupo_horario` | 9 `GRUPO_HORARIO` |
| Chamadas | 9 | 8 `qtde` | 13 `QTDE_CHAMADAS` |
| Minutos | 10 | 9 `minutos` | 14 `MINUTOS_TARIFADOS` |
| Tarifa | 11 | 10 `tarifa` | 10 `TARIFA_APLICAVEL` |
| R$_Liq | 12 | 11 `valor_liq` | 15 `VALOR_LIQUIDO` |
| PIS_Cofins | 13 | 12 `valor_piscofins` | ❌ **não existe** |
| ICMS | 14 | 13 `valor_icms` | ❌ **não existe** |
| **R$_Bruto** | 15 | 14 `valor_total` | ❌ **não existe** |

**O layout do arquivo da operadora casa com a V2 nos índices 0–14** (+ 3 colunas extras). **O da expectativa Vivo é outro arquivo**: tem `GROUP_CREDORA` a mais no início, `PARTE_TARIFADA`, `CORREDOR_TRANSPORTE` e `TIPO_TRANSPORTE` intercalados, e **termina em `VALOR_LIQUIDO`**.

### ⚠️ Achado A — o P3 aplica o índice da operadora também à expectativa

`_gerar_aba_contest::_preparar_agregado` usa o mesmo mapa para os dois lados:

```python
df_work["Devedora"] = df_work.iloc[:, 1]    # Vivo: EOT_CREDORA
df_work["Trafego"]  = df_work.iloc[:, 3]    # Vivo: PERIODO_REFERENCIA
df_work["GH"]       = df_work.iloc[:, 7]    # Vivo: PARTE_TARIFADA
df_work["Minutos"]  = df_work.iloc[:, 9]    # Vivo: GRUPO_HORARIO
df_work["R$_Bruto"] = df_work.iloc[:, 14]   # Vivo: MINUTOS_TARIFADOS
```

Sobre o layout da expectativa, **nenhum campo cai no lugar certo**. A comparação central do processo — `R$_Bruto` da operadora contra `R$_Bruto` da Vivo — estaria confrontando **valor bruto contra minutos**, agrupado por chaves erradas.

⚠️ **Evidência parcial, requer confirmação.** Baseio-me numa única fixture reduzida (`vivo_d_reduzido.csv`), derivada de um arquivo real segundo o README do P4. A V2 menciona uma etapa de conversão (*"da pasta dos arquivos convertidos"*) executada por outra demanda — é possível que o arquivo que chega ao P3 em produção já esteja normalizado. **Confirmar contra um arquivo de expectativa real do pipeline antes de tratar como defeito.**

Se confirmado, é o achado mais grave da análise: afeta a decisão de contestar, que tem consequência financeira direta.

### ⚠️ Achado B — remuneração derivada da coluna errada

`_enriquecer_com_tipo` deriva `tipo_produto` de `df.iloc[:, 4]` — o **POI** —, mas o método consumidor trata o valor como descritor:

```python
def obter_tipo_produto_por_poi(self, poi: str):
    caractere_final = poi_tratado[-1]        # último caractere
    ... ["FINAL_DO_DESCRITOR"] == caractere_final
```

A V2 é explícita: *"A identificação da Remuneração regulada... deve ser baseada no campo DESC (descritor) ou 7ª coluna"* — índice **6**, não 4.

Com dados reais: `poi = "SPOX_1007"` → último caractere `"7"` → não casa com nenhum `FINAL_DO_DESCRITOR` (C, T, L, V) → `tipo_produto = None`. O correto seria `descritor = " LENL"` → `"L"` → **TU-RL**.

O próprio nome do método (`por_poi`) denuncia a confusão. **Defeito.**

### ⚠️ Achado C — `tipo_operacao` derivado da EOT errada

`_enriquecer_com_tipo` deriva `tipo_operacao` da **Credora** (índice 0 = operadora). A V2 diz: *"Tipo de Operação: SMP e STFC (baseado na **EOT Vivo** e no tipo de serviço da EOT)"*, e a HU-10 confirma — *"Tabela SMP recebe os valores das EOTs móveis **da Vivo**"*.

O correto é a **Devedora** (índice 1). **Defeito.**

Note que a mesma classe usa a Devedora corretamente na regra do horário reduzido da VU-M (`_aplicar_analise_contestacao`) — a inconsistência é interna ao P3.

### ⚠️ Achado D — docstring com a convenção invertida

O docstring de `_preparar_dados_persistencia_contestacao` afirma: *"Pela convenção já adotada neste serviço (Credora = EOT Vivo, Devedora = EOT da operadora)"*, e conclui *"eot_tbra -> Devedora (operadora)"*.

**O código está certo** (`eot_tbra ← Devedora` = Vivo; `eot_operadora ← Credora` = operadora, conforme a V2). **O comentário está invertido** e induz ao erro num mapeamento de campo financeiro. O próprio autor registrou a dúvida ("Validar se essa é de fato a intenção").

---

## 5. 🔴 Achado E — contrato quebrado com o P4

P3 grava em `tbl_rpa_log_detraf_despesa_contestacao` as colunas:

`tipo_servico_vivo`, `eot_tbra`, `eot_operadora`, `empresa`, `referencia`, `trafego`, `minutos_tbra`, `vb_tbra`, `minutos_operadora`, `vb_operadora`, `minutos_diferenca`, `vb_diferenca`, `minutos_variacao_perc`, `vb_variacao_perc`, `carga_agi`, `tipo_contestacao`

P4 **lê** essa tabela pela chave (`constantes_epico4.py`):

```python
COLUNAS_CHAVE_DESPESA_CONTESTACAO = [
    "eot_operadora", "eot_tbra", "referencia", "trafego", "remuneracao",
]
```

**`remuneracao` não é gravada pelo P3.** O P4 nunca casa uma linha escrita pelo P3.

O P3 tem a informação (`tipo_produto`), mas grava com outro nome e não a inclui. **Reconciliar na base comum**, definindo o contrato da tabela num único ponto.

---

## 6. Regra de variação (a decisão do plano)

```python
variacao_rs  = RS_op - RS_tbra                       # com sinal
variacao_pct = variacao_rs / RS_tbra.replace(0, NA) * 100   # base = EXPECTATIVA
flag = "S" if notna(v) and v >= 1.0 else "N"
```

Confrontado com o P4 e resolvido no plano aprovado: **base = operadora (P4), com sinal (P3), limiar `>=`**. Ver [`../../docs/04-relatorios/duvidas-pendentes.md`](../../docs/04-relatorios/duvidas-pendentes.md) Q2.

P3 também calcula `minutos_variacao_perc` com base na expectativa (`Minutos_tbra`) — mesma reconciliação se aplica.

---

## 7. Aderência às premissas 10.3 / 10.4

| Item | Situação |
|---|---|
| Tarifas / mapeamentos | ✅ do banco |
| Limiares | 🔴 `1.0` embutido em `_aplicar_analise_contestacao` |
| **Índices de coluna fixos** | 🔴 **sim**, e é a raiz dos achados A, B e C |
| EOTs da Vivo | ✅ por env |
| Caminhos | ✅ por env |

---

## 8. Candidatos a componente compartilhado

`gerenciador_arquivos.py` (+`exportar_dataframe_para_excel`) · `historico_arquivos.py` · `utils.py` · `decoradores.py` · `logger_config.py` (**versão superset — aceita `%`-args**) · `repositorio_cache.py` · Anexo 5 · tarifas · descritores · escrita em `tbl_..._contestacao` · **regra de variação**.

---

## 9. Achados

### 🔴 Críticos
1. **Achado A** — índices da operadora aplicados à expectativa (a confirmar contra arquivo real)
2. **Achado E** — contrato quebrado com o P4 (`remuneracao` ausente)

### 🟡 Relevantes
3. **Achado B** — remuneração derivada do POI em vez do descritor
4. **Achado C** — `tipo_operacao` derivado da Credora em vez da Devedora
5. **Achado D** — docstring com convenção invertida
6. Limiar `1.0` embutido
7. Sem testes
8. HU-09 gera planilha **e** banco (é resposta à Q4, não defeito)

---

## 10. Conclusão

**Aderência à V2:** a estrutura do batimento está certa (dimensões de agrupamento, dupla escrita, regra de corte), mas **a extração dos campos tem defeitos** que só aparecem com dados reais.

**Complexidade de migração:** **alta** — não pelo volume, mas porque a migração precisa resolver o layout por origem de arquivo, e não há teste para proteger. **Escrever testes de caracterização com as fixtures do P4 antes de mover.**
