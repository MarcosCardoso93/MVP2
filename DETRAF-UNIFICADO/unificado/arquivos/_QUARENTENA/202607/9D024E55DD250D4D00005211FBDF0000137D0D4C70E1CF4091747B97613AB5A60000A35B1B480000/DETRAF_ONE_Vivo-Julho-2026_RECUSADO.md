# Arquivo recusado — DETRAF_ONE_Vivo-Julho-2026.xlsx

**Pasta:** `C:\RPA\Dtraf\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_QUARENTENA\202607\9D024E55DD250D4D00005211FBDF0000137D0D4C70E1CF4091747B97613AB5A60000A35B1B480000`
**Colunas encontradas:** 15

## Por que foi recusado

- Coluna 10 (Minutos): os minutos admitem no máximo 1 casa decimal.
- Colunas 12 a 15 (valores financeiros): os valores financeiros admitem no máximo 2 casas decimais.

## Primeiras linhas do arquivo

```
121;50;202607;202607;BRG.PAE.01;0; LENL;R;12786;17793.05;0.00425;75.6204625;2.8647087506486764;0;78.48517125064868
121;50;202607;202607;BRG.PAE.01;0; LENL;R;24260;30262.64;0.00425;128.61622;4.872332153606642;0;133.48855215360663
```

## O que fazer

1. Compare a tabela acima com o arquivo. Se as posições estiverem
   deslocadas, o arquivo veio noutro layout — é a operadora que precisa
   reenviar.
2. Se as posições batem e mesmo assim foi recusado, o problema é de
   **formato de valor** (decimal, data, zero à esquerda). Guarde este
   arquivo: ele é a evidência.
3. A validação é **posicional** e ignora os nomes das colunas — os nomes
   reais variam por operadora e não servem de critério (decisão do
   cliente, 2026-07-31).

> ⚠️ **Se este for um arquivo de expectativa Vivo**, a recusa pode ser a
> pendência **N3**: a V2 manda o layout valer para os dois tipos de
> arquivo (¶149) e exige a coluna `R$ Bruto` (¶443), mas o arquivo real
> termina em `VALOR_LIQUIDO`. É contradição entre a especificação e o
> arquivo, não defeito do robô — ver `pendencias-para-o-cliente.md`.
