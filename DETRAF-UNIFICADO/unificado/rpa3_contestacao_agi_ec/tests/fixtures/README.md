# Fixtures de teste — Épico 4

Amostras **reduzidas e versionadas**, derivadas dos exemplos reais em
`DOCS/Exemplos de arquivos de detraf/` e `.../de expectativa/` (D-10, L-001).
Os testes leem daqui — **nunca** de `DOCS/` (somente-leitura e não versionada).

## Arquivos

| Fixture | Origem (DOCS) | Formato observado |
|---------|---------------|-------------------|
| `detraf/algar_smp_reduzido.csv` | `.../detraf/ALGAR/.../DETRAT_ALGAR_..._SMP_..._ERRO.csv` | **vírgula**, **sem cabeçalho**, decimais entre aspas com vírgula |
| `detraf/algar_stfc_reduzido.csv` | `.../detraf/ALGAR/.../DETRAT_ALGAR_..._STFC_..._ERRO.csv` | **ponto e vírgula**, **com cabeçalho**, decimais com vírgula |
| `expectativa/vivo_d_reduzido.csv` | `.../expectativa/Vivo/DETRAF_FINAL_TRP_..._VIVO_D.csv` | **ponto e vírgula**, **com cabeçalho**, valores zero-padded com ponto decimal |
| `mapeamento_descritores.csv` | `DOCS/Outros arquivos auxiliares/Mapeamento_Descritores.xlsx` | descritor final → `remuneracao_fixa`, desambiguado por `produto` (D-5, resolvida) |

## Observações (D-8 — decidido pelo usuário: usar os índices documentados)

- A **variação de layout é real**: o mesmo fornecedor (ALGAR) entrega o arquivo
  SMP com vírgula/sem cabeçalho e o STFC com ponto e vírgula/com cabeçalho. Os
  **índices de coluna** e a **coluna `Rel`** diferem entre layouts (SMP/STFC = índice 5;
  Vivo = índice 6) do índice **documentado** (`AI/09 §6` = 4). **Decisão do usuário
  (2026-07-23):** os índices documentados são o **default/contrato** em todo o código
  (`src/config/constantes_epico4.py`); as funções de consolidação continuam aceitando um
  índice explícito como override para os casos reais conhecidos (L-008).
- Cada fixture contém **uma linha marcada como "total"** (valor `1` na coluna de
  relatório/`Rel` do respectivo layout) para exercitar a remoção de totais.
- Valores financeiros são **string** com vírgula decimal e/ou zero-padding — ler
  sempre com `dtype=str` (L-006).
