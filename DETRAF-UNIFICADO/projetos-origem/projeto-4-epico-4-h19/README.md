# Projeto 4 — Épico 4 (exceto HU-15) + HU-19

**Insira aqui o código do Projeto 4, sem alterações.**

---

## Escopo

| Campo | Valor |
|---|---|
| Épicos | 4 (Geração de arquivos) + parte do 6 (Encontro de Contas) |
| HUs | HU-12, HU-13, HU-14, HU-16, HU-19 — **exceto HU-15** (que está no P5) |
| RPA de destino | **RPA 3 — Contestação, Carga no AGI e Encontro de Contas** |
| Transformação | **Convergência** — junta-se a P5, P6(HU-20) e P7? no RPA 3 |
| Ordem de análise | **4º** |

## Responsabilidades

1. Gerar `DE_AGI_D_{aaaamm}_TBRA_X_{operadora}_EXT` — **todos** os cenários
2. Gerar `..._INT` — **apenas** contestação COM retenção
3. Gerar `Base Contestação_..._ENV` e a carta CT numerada
4. Gerar `CONT_PROC_MASCARA_{operadora}_{aaaamm}.xls` e atualizar `tipo_contestacao`
5. Alimentar o Encontro de Contas (HU-19)

---

## 🔴 Verificação prioritária 1 — o Épico 5 está aqui? (Q3)

**Fazer isto ANTES de qualquer outra análise deste projeto.**

O Épico 5 (**HU-17** — upload `_EXT`/`_INT`; **HU-18** — upload `CONT_PROC`) não foi atribuído a nenhum dos seis projetos, apesar de ser responsabilidade do RPA 3. Procure aqui:

- [ ] Automação de UI apontando para **`Detraf > Importar Dados`** no AGI
- [ ] Automação de UI apontando para **`Contestação > Gerenciar`** no AGI
- [ ] Escrita no campo **`carga_agi`** de `tbl_rpa_log_detraf_despesa_contestacao`

**Se encontrar** → o Épico 5 está no P4. Registre, descarte `projeto-7-epico-5-carga-agi/` e atualize o mapa.
**Se não encontrar** → verifique se chegou um sétimo projeto. Se não chegou, ⚠️ **HU-17/HU-18 provavelmente não foram implementadas** — escale ao GP, porque isso transforma parte do marco M8 em desenvolvimento.

---

## 🔴 Verificação prioritária 2 — de onde vem o `_ENV`? (Q4)

Há uma **contradição na V2**:
- A HU-09 diz que a `Base_Contestação` **não é mais gerada como arquivo**
- A HU-14 define o `_ENV` como **cópia** da `Base_Contestação_..._M`, apagando abas

**Verifique:** o `_ENV` é montado a partir do **arquivo** (produzido pelo P3) ou **do banco**?

A resposta identifica qual é uma das "duas exceções" da frase *"todas as planilhas foram substituídas por banco, exceto dois arquivos"*.

---

## 🔴 Verificação prioritária 3 — HU-19: planilha ou banco?

| Encontrado | Significado |
|---|---|
| Escreve na **planilha** de Encontro de Contas | V1 — revogada |
| Escreve em `minutos_operadora`, `vb_operadora`, `minutos_diferenca`, `vb_diferenca`, `minutos_variacao_perc`, `vb_variacao_perc` | V2 — correto |

Verifique também se o **momento** confere: a V2 tem um trecho que coloca o EC logo após a validação (RPA 2) e outro depois da contestação (RPA 3). Ver **Q8**.

---

## Pontos de atenção

- **Numeração CT (Q18).** Como lê e incrementa o contador em `\\lagoa\...\Correspondências Enviadas\CT\{ano}`? **Há trava?** É estado compartilhado sem transação — duas execuções simultâneas geram cartas com o mesmo número.
- **Modelos de carta por operadora.** O que acontece com uma operadora nova, sem modelo? Não documentado.
- **Arquivos-modelo `_EXT`/`_INT`.** A V2 diz que o robô "abre" esses arquivos, como se já existissem na pasta AGI. Confirme.
- **`CONT_PROC_MASCARA Geral {aaaamm}`** tem o ano-mês no nome. Como o código encontra a versão vigente?
- **Coluna W do `CONT_PROC` (Q11).** A V2 diz "minutagem", mas o campo é `VLR_BRUTO`. O que o código faz?
- **Regra de agregação do `CONT_PROC`:** pode consolidar por EOT Vivo (uma móvel, uma fixa), mas **não** pode sumarizar remunerações diferentes nem meses de tráfego diferentes.
- **Passos irreversíveis.** Este projeto consome a numeração CT e produz a carta. Onde ficam os pontos de retomada?

## Candidatos a componente compartilhado esperados aqui

Construção de caminhos de rede · convenções de nome de arquivo · acesso ao banco · mapeamento descritor → remuneração · geração de arquivo de carga (`_EXT` e `_INT` são fortes candidatos a EQUIVALENTE-PARAMETRIZÁVEL entre si).

---

## Procedimento

1. [`../../docs/03-checklists/checklist-insercao-dos-codigos.md`](../../docs/03-checklists/checklist-insercao-dos-codigos.md) — inclusive o **§7.1**, específico deste projeto
2. [`../../docs/05-proxima-etapa/roteiro-analise-tecnica.md`](../../docs/05-proxima-etapa/roteiro-analise-tecnica.md)
3. [`../../docs/03-checklists/checklist-analise-de-codigo.md`](../../docs/03-checklists/checklist-analise-de-codigo.md)

**Saídas:** `trabalho/inventarios/recebimento-projeto-4.md` e `inventario-projeto-4.md`

> ⚠️ Este é o **hub do fluxo**: alimenta o P5, o P7 e o P6, e é alimentado de volta pelo P7 (`carga_agi` antes da HU-19). Se o Épico 5 estiver mesmo aqui dentro, esse ciclo desaparece.
