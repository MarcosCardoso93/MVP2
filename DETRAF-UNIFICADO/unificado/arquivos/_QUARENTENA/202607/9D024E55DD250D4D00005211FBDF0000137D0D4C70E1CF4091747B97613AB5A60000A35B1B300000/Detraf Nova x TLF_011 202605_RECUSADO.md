# Arquivo recusado — Detraf Nova x TLF_011 202605.csv

**Pasta:** `C:\RPA\Dtraf\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_QUARENTENA\202607\9D024E55DD250D4D00005211FBDF0000137D0D4C70E1CF4091747B97613AB5A60000A35B1B300000`
**Colunas encontradas:** 15

## Por que foi recusado

- Coluna 3 (Referência): a referência precisa ser 202607 (AAAAMM) em todas as linhas.

## Primeiras linhas do arquivo

```
774;011;202605;202605;NVA.OCO.01;0;NENL;N;26995;136935,9;0,00610;835,31;31,64;0,00;866,95
774;011;202605;202605;NVA.OCO.01;0;NENL;R;2700;16590,6;0,00427;70,84;2,68;0,00;73,52
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
