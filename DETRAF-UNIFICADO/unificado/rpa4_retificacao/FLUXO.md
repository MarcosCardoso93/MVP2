# RPA 4 — retificação de contestação (HU-21)

## O que este robô faz

Quando a Vivo **recupera** tráfego que havia sido contestado no mês anterior, o
evento "Recuperação" precisa ser lançado no AGI, em `Contestação > Gerenciar`
(V2 ¶713). Este robô faz isso.

**Gatilho:** não é agenda, é **condição de negócio**. Só há trabalho quando existe
linha com variação **negativa** na contestação do mês anterior. Um mês sem
recuperação termina com sucesso e zero processos — e esse é o resultado certo.

**Entrega:** o evento no AGI, mais a linha marcada em
`tbl_rpa_log_detraf_despesa_contestacao` para não ser refeita.

```
 tbl_rpa_log_detraf_despesa_contestacao   ← RPA 2 apurou, RPA 3 contestou
         │  variação NEGATIVA = recuperação
         ▼
 ┌──────────────────┐   nada em disco, nada no AGI
 │ 1. DETECCAO      │   → lista + valores do evento calculados
 └────────┬─────────┘
          │  só se PERMITIR_ACESSO_AGI
          ▼
 ┌──────────────────┐   evento "Recuperação" no AGI  ⚠️ IRREVERSÍVEL
 │ 2. RETIFICACAO   │   + carga_agi = 'carregado'
 └──────────────────┘
```

> 🔴 **A etapa 2 não se desfaz, e o AGI não confirma nada.** Depois do clique em
> Salvar não há sinal de retorno; o robô marca a linha e segue. Se o AGI recusou,
> a linha fica marcada como feita. Reexecutar depois de uma falha no meio duplica
> evento.

---

# Etapa 1 — `deteccao`

**Onde:** `services/deteccao_recuperacao.py` → `comum/dados/repositorio_tabelas.py`

Lê a contestação do **mês anterior** ao de processamento — a recuperação é
percebida no mês seguinte ao da contestação — e separa as linhas com
`vb_variacao_perc < 0` que ainda não foram retificadas. Para cada uma, calcula os
valores do evento (`comum/dominio/retificacao.calcular_valores_evento`).

Não abre o AGI, não escreve nada. É a metade conferível do robô, e roda a
qualquer momento sem risco: `--etapa deteccao` responde "há o que retificar?".

⚠️ **O critério de "recuperado" não foi validado com o negócio.** Só
`vb_variacao_perc < 0`. A origem registra a dúvida — poderia ser
`minutos_variacao_perc`, ou as duas — e diz que havia uma única linha de teste na
tabela quando aquilo foi escrito.

🔴 **`carga_agi` tem dois donos.** Este robô o usa como "já retifiquei"; o RPA 3
o usa como "o CONT_PROC subiu" (HU-18). Duas consequências reais: **toda linha
que o RPA 3 já carregou fica invisível aqui**, e uma linha retificada passa a
parecer carregada. Foi decisão manter como na origem; a alternativa é uma coluna
própria (`retificacao_agi`), que precisa de `ALTER TABLE`.

# Etapa 2 — `retificacao`

**Onde:** `services/retificacao_agi.py` → `comum/integracoes/agi.py`

Por processo, sempre nesta ordem:

```
filtrar por período → exportar a grid → achar no CSV
   → pesquisar → abrir → VALIDAR → lançar → salvar
```

**Por que passar pelo CSV.** A estratégia foi decidida com a cliente em
2026-08-03, e não é a óbvia: o dropdown de operadora do modal de Filtro **não é
alcançável por UIA** (a origem tentou e registrou o timeout). Então filtra-se só
por período, exporta-se a grid, e a linha certa sai do CSV cruzando
**EOT + Referência + Tráfego + Valor**.

O valor entra no cruzamento porque as três primeiras chaves **não bastam**:
confirmado no export real, onde duas linhas têm as três iguais e diferem só no
valor. Não achar exatamente um processo é erro — zero e vários pelo mesmo motivo:
nos dois casos não se sabe qual é, e escolher seria pior do que parar.

**A validação é o ponto sem volta.** `AGI.validar_processo_selecionado` lê
`Processo Selecionado: <id>` na tela e **aborta** se divergir. É a guarda que a
cliente reforçou, e existe porque o duplo-clique que abre a linha usa um
deslocamento em pixels que não está calibrado nesta VM.

---

## Rodando

```powershell
python rpa4_retificacao\main.py --referencia 202606 --dry-run   # calcula e mostra
python rpa4_retificacao\main.py --referencia 202606             # lança no AGI
python rpa4_retificacao\main.py --etapa deteccao                # só a conferência
```

`--referencia` é o mês de **processamento**; a contestação procurada é a do mês
anterior. `--dry-run` desliga todos os efeitos externos — o robô calcula tudo,
lista o que faria e não abre o AGI.

## O que parece defeito e não é

- **"Nenhum tráfego recuperado"** — é o caso comum. A HU-21 não roda todo mês.
- **Zero recuperações mesmo havendo contestação** — confira a referência: o robô
  procura no mês **anterior** ao que você passou.
- **Uma operadora falha e as outras seguem** — é deliberado. O que falhou não é
  marcado, e volta na próxima execução.
- **`PERMITIR_ACESSO_AGI` desligado e nada é lançado** — o robô avisa quantas
  deixou de lançar. É o modo de conferência.

## ⚠️ O que veio da origem sem calibração

Marcado "PRECISA CONFIRMAR NA VM" no código de origem, e mantido:

| O quê | Onde | Risco se estiver errado |
|---|---|---|
| `12×down` até "Recuperação" | `agi.DESCIDAS_ATE_RECUPERACAO` | lança o **tipo de evento errado** |
| offset de 72px do cabeçalho | `agi.OFFSET_CABECALHO_ATE_PRIMEIRA_LINHA` | abre a linha errada — a validação pega |
| `6 TABs` / `5 TABs` no evento | `agi.lancar_evento_recuperacao` | valores nos campos errados |
| 1º item do dropdown = mês anterior | `agi.filtrar_por_periodo` | filtra período errado — o cruzamento no CSV não acha e o robô para |
| PNGs recortados de print | `comum/view/imagens/AGI_Contestacao_Gerenciar/` | não acha o botão; falha ruidosa |

A primeira execução real precisa de alguém olhando a tela. `verificar_imagens_agi.py`
confere as imagens antes.

## Ver também

- `comum/dominio/retificacao.py` — o cálculo e a busca do processo, com testes.
- `comum/dominio/variacao.py` — a regra que manda a variação negativa para cá.
- `README.md` deste robô — o histórico e as pendências de negócio.
