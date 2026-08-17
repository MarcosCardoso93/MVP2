# Inventário — Projeto 2: Épico 2 (Validação dos Arquivos de Detraf)

- **Pasta:** `projetos-origem/projeto-2-epico-2-validacao/`
- **HUs esperadas:** HU-04, HU-05, HU-06, HU-07, HU-08
- **RPA de destino:** RPA 2 (converge com o P3)
- **Recebimento:** [`00-recebimento-p1-a-p4.md`](00-recebimento-p1-a-p4.md)

---

## 1. Estrutura e execução

```
src/
├── config/       configuration.py · logger_config.py
├── controllers/  validacao_detrafs_controller.py
├── main/         process_handle.py
├── models/repository/  repositorio_cache.py · repositorio_tabelas.py (526 linhas)
├── services/     validacao_detrafs.py (621) · resultado_validacao.py · notificacao_email.py
│   └── validacao_inicial/  validacao_colunas.py (556) · limpeza_trafegos.py (329)
└── utils/        classificadores · decoradores · geradores_tabelas_homo · gerenciador_arquivos
                  historico_arquivos · utils
```

| Item | Valor |
|---|---|
| Ponto de entrada | `src/main/process_handle.py::run()` — **sem `main.py`** |
| Fluxo | `ValidacaoDetrafsController.validar_detrafs()` → `ValidacaoDetrafsService.executar()` |
| Granularidade | lote — varre todos os arquivos da competência de uma vez |
| Paralelismo | não |
| Estado acumulado | ⚠️ **sim** — `executar()` monta listas de todos os arquivos antes de processar; não dá para rodar uma operadora isolada |

**Sem testes.** É o maior projeto sem cobertura alguma.

---

## 2. Mapeamento HU → código

| HU | Status | Onde |
|---|---|---|
| HU-04 — validação estrutural das colunas | ✅ | `validacao_inicial/validacao_colunas.py` (28 métodos, uma máscara + um validador por coluna) |
| HU-05 — validação da tarifa regulada | ✅ | `validacao_colunas.py::_validar_tarifas_remuneradas`, `repositorio_tabelas.py::validar_tarifas_na_tabela` |
| HU-06 — arquivo `_BK` | ✅ | `limpeza_trafegos.py::separar_linhas_bk` |
| HU-07 — erro L-L | ✅ **já genérico** | `limpeza_trafegos.py::separar_linhas_ll`, registrado no mapa de fluxos |
| HU-08 — registro no WebFat | ✅ | `resultado_validacao.py`, `repositorio_tabelas.py::salvar_dados_tabela_despesa` |

### Código sem HU correspondente

| Onde | O quê | Classificação |
|---|---|---|
| `utils/geradores_tabelas_homo.py` (166 linhas) | Gera as tabelas de homologação (Anexo 5, tarifas, descritores) a partir de planilhas locais | ⚠️ **Utilitário de bancada.** Caminhos absolutos da máquina do desenvolvedor, cinco blocos comentados. **Não migrar** — é ferramenta, não produto |
| `services/notificacao_email.py` | Responde o e-mail de origem do arquivo inválido | Pertence à HU-04 (crítica à operadora). Sobrepõe-se a `outlook_controller.responder_por_arquivo` do P1 |

---

## 3. 🔴 Versão da regra implementada

### HU-07 — **V2, já genérica. Nada a eliminar.**

Ao contrário do que a etapa documental previa, o caso L-L **não** tem caminho de erro dedicado. `LimpadorTrafegos` mantém um mapa de fluxos:

```python
self._fluxos = {
    "BK": self.separar_linhas_bk,
    "LL": self.separar_linhas_ll,   # "Novo fluxo adicionado como template"
}
```

E `ValidacaoDetrafsService._validar_fluxo(arquivos, tipo_fluxo="LL", sufixo="_ERRO")` é chamado pelo mesmo mecanismo genérico que trata o `_BK`. A regra geral de `_ERRO` da V2 está implementada em `separar_e_salvar_por_mascara` (`gerenciador_arquivos.py`) e em `renomear_arquivo_com_sufixo`.

**O comentário no código — "novo fluxo adicionado como template" — indica que o mecanismo foi desenhado para receber outros fluxos.** É exatamente o que as premissas 10.3/10.4 da V2 pedem. Excelente candidato a base comum.

---

## 4. Pontos de I/O

**E-mail:** `notificacao_email.py` (140 linhas) responde via Outlook COM, usando o `_rastreamento.json` gerado pelo P1 para achar o `entry_id` a partir do nome do arquivo. **Acoplamento real entre RPA 1 e RPA 2 por arquivo JSON** — não documentado na V2. Template do corpo por env (`CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO`).

**Arquivos:** lê `CAMINHO_DETRAF_RECEBIDO` e `CAMINHO_EXPECTATIVA_DETRAF`; filtra expectativa por `EXPECTATIVA_SUBSTRING` (o `_D_` da V2, parametrizado) e por `PASTAS_EXPECTATIVAS` (as pastas VIVO/TLF). Ignora arquivos por `IGNORAR_ARQUIVOS` (`_BK`, ...). Escreve `_ERRO` e `_BK`. Histórico anti-reprocessamento em `historico_arquivos.py`.

**Banco:** `tbl_anexo5_processado` e `tbl_anexo5`, `tbl_detraf_tarifas`, `tbl_detraf_mapeamento_descritores` (leitura); `tbl_detraf_despesa_arquivos` (escrita).

⚠️ **`repositorio_cache.py:82` tem caminho absoluto** da máquina do desenvolvedor como fallback do SQLite.

---

## 5. Regras de negócio

`ValidadorColunas` implementa a validação das 15 colunas com um par (máscara, validador) por regra — a máscara permite separar linha a linha para o `_ERRO`, o validador dá o veredicto do arquivo. Desenho limpo.

| Regra | Situação |
|---|---|
| Col 1/2 — EOT válida no Anexo 5 | ✅ `_validar_col_1_2_eot`, `_validar_col_2_eot_vivo` |
| Col 3 — referência = mês −1 | ✅ `_preparar_datas_referencia` |
| Col 4 — tráfego = mês −1/−2/−3 | ✅ |
| Col 8 — GH ∈ {S,R,N,D} | ✅ |
| Col 9 — inteiros | ✅ |
| Col 10 — até 1 decimal | ✅ |
| Col 11 — até 5 decimais, sem zero | ✅ |
| Cols 12-15 — até 2 decimais | ✅ |
| Tarifa regulada × tabela | ✅ `_validar_tarifas_remuneradas` |
| **Dupla convivência em fevereiro** | ✅ `validar_tarifas_na_tabela` filtra por `data_inicio`/`data_fim` com o **mês do tráfego** |
| `gh` nulo vale para todos | ✅ trata `NULL` textual vindo do banco |
| Regra `_BK` (L…V, SMP, não-PMS) | ✅ `separar_linhas_bk` |
| **Recálculo do total no `_BK`** | ✅ `_adicionar_linha_total` — **responde a Q10** |
| Sem cabeçalho / aba de resumo | ⚠️ a confirmar em `carregar_dados` |
| Classificação de descritor | ✅ `utils/classificadores.py` |

**Q10 respondida pelo código:** o `_BK` **recalcula** a linha de total (`_adicionar_linha_total` após `_filtrar_rel`). Alinha com o PDF de HUs, contra a omissão da V2.

---

## 6. Tratamento de erro e logging

Erro do arquivo **da operadora** → `_notificar_arquivos_invalidos` dispara resposta por e-mail. Erro do arquivo **de expectativa** → só WebFat. **A assimetria exigida pela V2 está implementada.**

`resultado_validacao.py` grava com `tipo_lote` ∈ {`DETRAF_SUCESSO`, `DETRAF_ERRO`, `EXPECTATIVA_SUCESSO`, `EXPECTATIVA_ERRO`} — mais granular que os três valores de `tipo_registro` da V2 (`DETRAF`/`EXPECTATIVA`/`ERRO`). ⚠️ Verificar o mapeamento na migração.

**Nenhuma "correção automática" de expectativa implementada** — a Q13 continua aberta, e o código não tomou decisão silenciosa. Bom.

---

## 7. Aderência às premissas 10.3 / 10.4

| Item | Situação |
|---|---|
| Valores de tarifa | ✅ tudo de `tbl_detraf_tarifas` |
| Mapeamento descritor → remuneração | ⚠️ `utils/classificadores.py` tem a regra início/fim do descritor **em código**; o mapa para remuneração vem do banco |
| Limiares | ✅ nenhum |
| **Índices de coluna fixos** | 🔴 **sim** — `validacao_colunas.py` usa índices posicionais (`_mascara_col_3_referencia` etc.) |
| EOTs da Vivo | ✅ por env (`NOME_FANTASIA_VIVO`) |
| **Caminhos de rede** | 🔴 **`repositorio_cache.py:82`** e 5 pontos em `geradores_tabelas_homo.py` |

**Duas violações reais:** o caminho absoluto (corrigido na base comum) e os índices de coluna fixos (registrado como dívida — a correção completa depende da definição de CBS/IBS, Q6).

---

## 8. Candidatos a componente compartilhado

| Candidato | Onde | Ocorrências |
|---|---|---|
| `gerenciador_arquivos.py` | `utils/` | 3 (P2/P3/P4) — 17 funções idênticas |
| `historico_arquivos.py` | `utils/` | 3, **idênticos** |
| `utils.py`, `decoradores.py` | `utils/` | 3, **idênticos** |
| `logger_config.py` | `config/` | 4 |
| `repositorio_cache.py` | `models/repository/` | 4 |
| Anexo 5 (EOT, tipo de serviço, concessão, região) | `repositorio_tabelas.py` | 4 |
| Tarifas | `repositorio_tabelas.py::validar_tarifas_na_tabela` | 2 (P2/P3) |
| Log de despesa | `repositorio_tabelas.py::salvar_dados_tabela_despesa` | 3 |
| Classificação de descritor | `utils/classificadores.py` | 2 (P2 e `mapa_remuneracao.py` do P4) |
| Mecanismo de fluxos (`_BK`/`_LL`) | `limpeza_trafegos.py` | 1 — **não promover** (C1) |

---

## 9. Achados

### 🔴 Críticos
1. **Caminho absoluto da máquina do desenvolvedor** em `repositorio_cache.py:82` — impede rodar em outra máquina
2. **Senha de banco real no `.env`** (fora do git, mas não pode ser herdada)

### 🟡 Relevantes
3. **`load_dotenv()` ausente** — único dos quatro que não carrega o `.env`
4. **Sem testes** — nenhuma cobertura, no maior projeto de regra de negócio
5. **Índices de coluna fixos** em `validacao_colunas.py`
6. **`geradores_tabelas_homo.py` é ferramenta de bancada** — não migrar
7. **`tipo_lote` com 4 valores** contra 3 de `tipo_registro` na V2 — conferir mapeamento
8. **Acoplamento por `_rastreamento.json`** com o P1, não documentado na V2

### 🟢 Observações
- `ValidadorColunas` com par máscara/validador é o desenho mais maduro dos quatro
- Mecanismo de fluxos genérico já atende às premissas 10.3/10.4

---

## 10. Conclusão

**Escopo real × esperado:** cobre as cinco HUs. A HU-07, que a documentação mandava fundir, **já nasceu fundida**.

**Aderência à V2:** alta. Implementa dupla convivência de tarifas, assimetria de tratamento de erro e regra geral de `_ERRO`. Responde à Q10 (o `_BK` recalcula o total).

**Complexidade de migração:** **média** — o volume de regra é grande e não há teste para proteger a migração. Recomendo escrever testes de caracterização das regras de coluna **antes** de mover o código.
