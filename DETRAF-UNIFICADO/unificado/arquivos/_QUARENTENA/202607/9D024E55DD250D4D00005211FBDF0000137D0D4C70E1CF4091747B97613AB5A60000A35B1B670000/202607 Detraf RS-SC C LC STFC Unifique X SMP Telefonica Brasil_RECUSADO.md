# Arquivo recusado — 202607 Detraf RS-SC C LC STFC Unifique X SMP Telefonica Brasil.xlsx

**Pasta:** `C:\RPA\Dtraf\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_QUARENTENA\202607\9D024E55DD250D4D00005211FBDF0000137D0D4C70E1CF4091747B97613AB5A60000A35B1B670000`
**Colunas encontradas:** 15

## Por que foi recusado

- Coluna 10 (Minutos): os minutos admitem no máximo 1 casa decimal.

## Primeiras linhas do arquivo

```
I61;50;202607;202607;BRT_CPU1LE;0;LENL;N;245;371.6;0.00608;2.26;0.08;0;2.34
I61;50;202607;202607;BRT_PAS1LE;0;LENL;N;1581;3571.7999999999997;0.00608;21.72;0.82;0;22.54
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
