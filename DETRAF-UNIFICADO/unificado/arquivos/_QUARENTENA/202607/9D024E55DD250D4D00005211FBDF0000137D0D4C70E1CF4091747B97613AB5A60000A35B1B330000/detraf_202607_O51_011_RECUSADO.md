# Arquivo recusado — detraf_202607_O51_011.csv

**Pasta:** `C:\RPA\Dtraf\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_QUARENTENA\202607\9D024E55DD250D4D00005211FBDF0000137D0D4C70E1CF4091747B97613AB5A60000A35B1B330000`
**Colunas encontradas:** 16

## Por que foi recusado

| Posição | Campo | Esperado | Encontrado | Válidos |
|---|---|---|---|---|
| 0 | Credora | EOT numérica | `H90`, `H90`, `nan` | 0/3 |
| 9 | Minutos | número | `167.921,31`, `3.128,81`, `nan` | 0/3 |
| 11 | R$_Liq | número | `1.024,32`, `1.037,68` | 1/3 |
| 14 | R$_Bruto | número | `1.061,68`, `1.075,53` | 1/3 |

## Primeiras linhas do arquivo

```
H90;11;202607;202607;SPO.IB;0;NENL;N;55494;167.921,31;0,0061;1.024,32;37,36;0;1.061,68;11
H90;11;202607;202607;SPO.IB;0;NENL;R;1146;3.128,81;0,00427;13,36;0,49;0;13,85;11
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
