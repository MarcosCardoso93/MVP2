# Projeto 2 — Épico 2: Validação dos Arquivos de Detraf

**Insira aqui o código do Projeto 2, sem alterações.**

---

## Escopo

| Campo | Valor |
|---|---|
| Épico | 2 — Validação dos Arquivos de Detraf |
| HUs | HU-04, HU-05, HU-06, HU-07, HU-08 |
| RPA de destino | **RPA 2 — Validação e Apuração de Contestação** |
| Transformação | **Convergência** — junta-se ao P3 no RPA 2 |
| Ordem de análise | **2º** |

## Responsabilidades

1. Abrir os arquivos de "Detrafs Recebidos" e os convertidos com `_D_` no nome
2. Validar as 15 colunas conforme as regras de layout
3. Validar tarifas reguladas contra `tbl_detraf_tarifas`
4. Gerar arquivos `_BK` (SMP não-PMS) e `_ERRO` (qualquer regra violada)
5. Registrar em `tbl_rpa_log_detraf_despesa_arquivos` com `tipo_registro` ∈ {`DETRAF`, `EXPECTATIVA`, `ERRO`}
6. Acionar a operadora por e-mail quando o erro for do arquivo dela

---

## 🔴 Verificação prioritária — HU-07

**A V2 eliminou o tratamento específico do caso L-L (STFC).** Ele foi absorvido pela regra geral de `_ERRO` da HU-04.

- **Se existe caminho de erro dedicado ao caso L-L** → é V1, **candidato a eliminação**, não a migração
- **Se o caso cai na regra geral** → é V2, correto

Isso também é uma **duplicação interna ao projeto**: dois caminhos de erro onde a V2 prevê um.

---

## Pontos de atenção

- **Dupla convivência de tarifas em fevereiro** está implementada? A consulta usa o **mês do tráfego** ou a data de execução? Lembre que, como a coluna Tráfego aceita até mês −3, uma tarifa de fevereiro pode valer até o Detraf de maio.
- 🔴 **Tarifas, mapeamentos ou limiares constantes no código** violam as premissas 10.3/10.4 da V2. Verificar.
- 🔴 **Índices de coluna fixos** violam o requisito de layout dinâmico (risco do imposto de 2028 e da chegada de CBS/IBS).
- **Assimetria de tratamento de erro:** arquivo da operadora → aciona a operadora por e-mail; arquivo de expectativa → WebFat para a área usuária. Está implementada?
- **"Avalia possível correção automática" (Q13).** Se existe código fazendo isso, ele implementa decisão **não documentada** — a V2 não define a regra.
- **O `_BK` recalcula a linha de total (Q10)?** O PDF de HUs exige; a V2 não menciona.
- **Tarifas não reguladas (Q9):** valida o valor ou a tabela só classifica?
- **Descritores de transporte (Q12):** a V2 declara a regra como pendente.
- **Bordas de leitura:** aceita arquivo sem cabeçalho? ignora aba de resumo? tolera `Rel` vazia?

## Candidatos a componente compartilhado esperados aqui

Leitura de arquivo Detraf · consulta ao Anexo 5 · mapeamento descritor → remuneração · consulta a `tbl_detraf_tarifas` · construção de caminhos · convenções de nome · acesso ao banco · automação do Outlook (envio de crítica).

⚠️ **A fronteira P2 × P3 é onde a duplicação é mais provável.** Ao analisar o P3, confronte tudo daqui.

---

## Procedimento

1. [`../../docs/03-checklists/checklist-insercao-dos-codigos.md`](../../docs/03-checklists/checklist-insercao-dos-codigos.md)
2. [`../../docs/05-proxima-etapa/roteiro-analise-tecnica.md`](../../docs/05-proxima-etapa/roteiro-analise-tecnica.md)
3. [`../../docs/03-checklists/checklist-analise-de-codigo.md`](../../docs/03-checklists/checklist-analise-de-codigo.md)

**Regras a conferir:** [`../../docs/01-entendimento/regras-de-negocio-consolidadas.md`](../../docs/01-entendimento/regras-de-negocio-consolidadas.md) — este projeto é o que mais depende delas.

**Saídas:** `trabalho/inventarios/recebimento-projeto-2.md` e `inventario-projeto-2.md`
