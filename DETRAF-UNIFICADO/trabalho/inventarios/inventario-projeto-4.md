# Inventário — Projeto 4: Épico 4 (exceto HU-15) + HU-19

- **Pasta:** `projetos-origem/projeto-4-epico-4-h19/`
- **HUs esperadas:** HU-12, HU-13, HU-14, HU-16, HU-19
- **RPA de destino:** RPA 3 (converge com P5, P6 e o Épico 5)
- **Recebimento:** [`00-recebimento-p1-a-p4.md`](00-recebimento-p1-a-p4.md)

---

## 1. Estrutura e execução

```
src/
├── config/       configuration.py · constantes_epico4.py (163) · logger_config.py
├── controllers/  geracao_agi_controller.py (116)
├── main/         process_handle.py
├── models/repository/  repositorio_cache.py (360) · repositorio_tabelas.py (337)
├── services/     consolidacao_contestacao (430) · geracao_env_carta (489) · geracao_cont_proc (270)
│                 geracao_ext (177) · geracao_int (161) · mapa_remuneracao (190) · encontro_contas (91)
└── utils/        decoradores · estrutura_pastas · gerenciador_arquivos · historico_arquivos
                  nomenclatura · utils
tests/            14 arquivos + fixtures reais
```

**É o projeto mais bem construído dos quatro:** constantes centralizadas, decisões rastreadas (D-1 a D-21), 14 arquivos de teste com fixtures derivadas de arquivos de produção, e separação limpa entre service e repositório.

---

## 2. 🔴 O projeto não executa

`GeracaoAgiController.gerar_artefatos()` — o único método chamado pelo `process_handle.run()` — apenas emite logs:

```python
logger.info("[Épico 4] Orquestração iniciada (stub de Bootstrap).")
logger.info("[Épico 4] Etapa pendente: Consolidação (Base_Contestação).")
logger.info("[Épico 4] Etapa pendente: HU-12 EXT.")
...
logger.info("[Épico 4] Orquestração finalizada (nenhum artefato gerado ainda).")
```

Os 1.924 linhas de services estão implementadas e testadas, mas **nenhuma é chamada pelo ponto de entrada**. Dois métodos do controller (`gerar_cont_proc`, `atualizar_despesa_contestacao`) estão prontos e ligados aos services, mas só são alcançáveis por chamada direta.

**Conforme decidido, isto é registrado como lacuna funcional — não será implementado nesta etapa.** Ligar a cadeia é desenvolvimento, e sem P5/P6/Épico 5 o RPA 3 não fecha de qualquer forma.

---

## 3. Mapeamento HU → código

| HU | Service | Status |
|---|---|---|
| HU-12 — `_EXT` | `geracao_ext.py` | ✅ implementado e testado |
| HU-13 — `_INT` | `geracao_int.py` | ✅ implementado e testado |
| HU-14 — `_ENV` + carta | `geracao_env_carta.py` | ⚠️ parcial — ver §5 |
| HU-16 — `CONT_PROC` | `geracao_cont_proc.py` | ✅ implementado e testado |
| HU-19 — Encontro de Contas | `encontro_contas.py` | ✅ implementado e testado |
| (dependência D-2) | `consolidacao_contestacao.py` | ✅ — **duplica a HU-09 do P3** |

### Código sem HU correspondente

`consolidacao_contestacao.py` (430 linhas) reimplementa a consolidação Detraf × expectativa — que é a **HU-09, do P3**. O P4 a construiu por conta própria por depender dela ("dependência D-2"). **Duplicação de responsabilidade entre projetos** — o caso mais importante do registro de duplicações.

---

## 4. 🔴 Achado — `COL_REL` com erro de um índice

`constantes_epico4.py` declara o layout do Detraf. Conferindo contra a V2 (numeração 1-based) e contra a fixture real `algar_stfc_reduzido.csv` (que traz cabeçalho):

| Constante | Valor | V2 | ALGAR real | Veredicto |
|---|---|---|---|---|
| `COL_CREDORA` | 0 | col 1 | 0 `cd_eot_bil` | ✅ |
| `COL_DEVEDORA` | 1 | col 2 | 1 `cd_eot_rel` | ✅ |
| `COL_REFERENCIA` | 2 | col 3 | 2 `mes_ref` | ✅ |
| `COL_TRAFEGO` | 3 | col 4 | 3 `mes_traf` | ✅ |
| — POI — | — | col 5 | 4 `poi` | *não mapeada* |
| **`COL_REL`** | **4** | **col 6 → idx 5** | **5** `tipo_relatorio` | 🔴 **errado** |
| `COL_DESCRITOR` | 6 | col 7 | 6 `descritor` | ✅ |
| `COL_GH` | 7 | col 8 | 7 `grupo_horario` | ✅ |
| `COL_CHAMADAS`…`COL_R_BRUTO` | 8…14 | col 9…15 | 8…14 | ✅ |

**`COL_REL = 4` aponta para o POI.** Todas as outras constantes estão certas — inclusive `COL_DESCRITOR = 6`, que só é consistente se o Rel estiver em 5.

Consequência: `VALOR_REL_TOTAL = "1"` filtraria o POI (`"SPOX_1007"`, `"ULAX_4113"`) em vez do Rel, e **as linhas de total não seriam removidas**.

⚠️ **O projeto interpretou isso como variação de layout, não como defeito.** O README das fixtures registra: *"os índices de coluna e a coluna `Rel` diferem entre layouts (SMP/STFC = índice 5; Vivo = índice 6) do índice documentado (`AI/09 §6` = 4)"*, e a decisão D-8 fixou o valor documentado como contrato, com override opcional.

Mas a V2 **não** documenta Rel no índice 4 — documenta na **6ª coluna**, que é o índice 5. O `AI/09 §6` (não entregue) parece conter o erro. Como o override existe e os testes passam o índice certo, o defeito só se manifesta no uso do default.

**Reconciliação:** `COL_REL = 5` na base comum. Alteração intencional, registrada.

**Isto também esvazia parte da decisão D-8:** a "variação real de layout" entre ALGAR e o índice documentado não existe — o documentado é que estava errado. A variação **real** é entre o arquivo da operadora e o da expectativa Vivo (ver inventário do P3, §4).

---

## 5. HU-14 parcialmente implementada

`geracao_env_carta.py:273` contém `raise NotImplementedError`. Os textos da carta estão resolvidos (D-3: assunto, corpo, saudação, fecho, cidade São Paulo, assinatura fixa "ANGELICA GUIMARAES PEREIRA"), mas o preenchimento do modelo `.docx` depende de `CAMINHO_MODELO_CARTA`, marcado como **bloqueado** em `configuration.py` (D-3/D-4/D-5).

> ⚠️ **Desatualizado (2026-08-04).** Não havia bloqueio: `CAMINHO_MODELO_CARTA` e
> `CAMINHO_MASCARA_CONT_PROC` estavam declaradas e **nenhum módulo as lia** — foram
> removidas. A carta é montada do zero com `python-docx`, e o cliente confirmou
> **modelo único para todas as operadoras** (Q26). O `NotImplementedError` que
> restou é o método abstrato de `ProvedorAssinaturaCarta`, com implementação
> concreta logo abaixo. O pré-requisito real da HU-14 é `CAMINHO_CONTROLE_CT`.

Mesma situação para `CAMINHO_MASCARA_CONT_PROC`.

---

## 6. Pendências que o P4 resolveu

O P4 fechou, com o usuário, várias questões que a etapa documental registrou como abertas:

| Decisão | Conteúdo | Impacto |
|---|---|---|
| **D-4** | `ID_MODALIDADE` é **fixo `"00"`**, não lookup. A máscara real não tem a aba `Remuneração` com colunas I/J/K que a V2 previa | Fecha parte da HU-16 |
| **D-3** | Textos, cidade e assinatura da carta confirmados por duas cartas reais (CT 251/252-2026) | Fecha parte da HU-14 |
| **D-5** | Descritor ambíguo desambiguado pela coluna `produto` do mapeamento | Fecha a ambiguidade `T` → TU-RIU / VU-T |
| **D-11** | Base da variação = lado operadora | Entra na decisão da Q2 |
| **D-19/D-20** | Ordem do writeback de `tipo_contestacao`; os seis campos da HU-19 | Fecha a HU-19 |

⚠️ **A pasta `AI/` e o `TODO/` não foram entregues.** São a fonte dessas decisões. **Vale pedir** — ver §7 do recebimento.

---

## 7. Regras de negócio

| Regra | Situação |
|---|---|
| Campos fixos `_EXT` / `_INT` (ORIGEM, EXPECTATIVA, INSERÇÃO) | ✅ em `constantes_epico4.py` |
| `_INT` só para COM retenção | ✅ `geracao_int.py` |
| Colunas do `CONT_PROC` (C, D, E, F, G, H, I, W, AB, AG) | ✅ `geracao_cont_proc.py` |
| Não sumarizar remunerações diferentes | ✅ |
| `FLAG_PAG_REC` P/R | ✅ |
| Numeração CT sequencial | ✅ `nomenclatura.py` — ⚠️ **sem trava** (Q18) |
| Seis campos da HU-19 | ✅ `COLUNAS_ATUALIZADAS_DESPESA_CONTESTACAO` |
| Regra de variação | ✅ `LIMIAR_VARIACAO_CONTESTACAO = 0.01`, base operadora, **`abs()`** |
| Par ausente → 100% | ✅ |

**Coluna W do `CONT_PROC` (Q11):** verificar em `geracao_cont_proc.py` se recebe valor bruto ou minutagem — a V2 diz "minutagem" no texto do campo `VLR_BRUTO`, o que é erro de redação evidente.

---

## 8. Aderência às premissas 10.3 / 10.4

| Item | Situação |
|---|---|
| Tarifas / mapeamentos | ✅ do banco |
| Limiares | ✅ `LIMIAR_VARIACAO_CONTESTACAO` em constante nomeada |
| Índices de coluna | ⚠️ constantes nomeadas com override por parâmetro — **melhor padrão dos quatro**, apesar do erro em `COL_REL` |
| Caminhos | ✅ todos por env |
| Textos da carta | ✅ em constantes |

**É o projeto mais aderente às premissas.** `constantes_epico4.py` é o modelo a levar para a base comum.

---

## 9. Testes

14 arquivos, incluindo `test_configuracao_ambiente.py`, `test_contestacao_sinal.py` e `test_repositorio_escrita.py`. **Fixtures derivadas de arquivos reais** (`algar_smp_reduzido.csv`, `algar_stfc_reduzido.csv`, `vivo_d_reduzido.csv`, `mapeamento_descritores.csv`), com formatos deliberadamente diferentes entre si — vírgula sem cabeçalho, ponto e vírgula com cabeçalho, decimais com vírgula e zero-padding.

**Esse conjunto é o ativo mais valioso da unificação:** é a única massa de teste com dados reais, e serve para validar o RPA 2 também.

---

## 10. Candidatos a componente compartilhado

`constantes_epico4.py` (**base das constantes comuns**) · `gerenciador_arquivos.py` (+`salvar_planilhas`) · `historico_arquivos.py` · `utils.py` · `decoradores.py` · `logger_config.py` · `repositorio_cache.py` · `estrutura_pastas.py` · `nomenclatura.py` · `mapa_remuneracao.py` (2ª ocorrência de `classificadores.py` do P2) · Anexo 5 · descritores · **`consolidacao_contestacao.py` (duplica a HU-09 do P3)**.

---

## 11. Achados

### 🔴 Críticos
1. **Não executa** — orquestração stub (§2)
2. **`COL_REL = 4`** — erro de um índice (§4)
3. **`consolidacao_contestacao.py` duplica a HU-09 do P3** com regra de variação divergente

### 🟡 Relevantes
4. ~~`NotImplementedError` em `geracao_env_carta.py:273` — HU-14 depende de modelo bloqueado~~ — **não procede**, ver §acima (2026-08-04)
5. Numeração CT sem trava (Q18)
6. `AI/` e `TODO/` não entregues — fonte das decisões D-1 a D-21
7. Chave de leitura inclui `remuneracao`, que o P3 não grava (ver inventário do P3, §5)

### 🟢 Observações
- Único com `.env.example` em vez de `.env` — padrão correto
- Único com fixtures reais versionadas

---

## 12. Conclusão

**Escopo real × esperado:** os services cobrem as cinco HUs (HU-14 parcial), mas **o projeto não tem orquestração** — é uma biblioteca, não um robô.

**Aderência à V2:** a mais alta dos quatro, com decisões rastreadas e confirmadas com o cliente.

**Complexidade de migração:** **baixa para os services** (bem isolados, testados, com constantes centralizadas), **alta para fechar o RPA 3** — mas isso está fora do escopo desta etapa.
