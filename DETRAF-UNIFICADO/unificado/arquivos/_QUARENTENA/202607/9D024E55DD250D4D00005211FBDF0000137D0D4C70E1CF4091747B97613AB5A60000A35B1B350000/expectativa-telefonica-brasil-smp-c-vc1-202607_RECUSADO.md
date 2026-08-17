# Arquivo recusado — expectativa-telefonica-brasil-smp-c-vc1-202607.xlsx

**Pasta:** `C:\RPA\Dtraf\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_QUARENTENA\202607\9D024E55DD250D4D00005211FBDF0000137D0D4C70E1CF4091747B97613AB5A60000A35B1B350000`
**Colunas encontradas:** 15

## Por que foi recusado

| Posição | Campo | Esperado | Encontrado | Válidos |
|---|---|---|---|---|
| 0 | Credora | EOT numérica | `B19`, `B19`, `B19` | 0/4 |
| 9 | Minutos | número | `72,370.7`, `6,291.4`, `nan` | 1/4 |

## Primeiras linhas do arquivo

```
B19;020;202607;202607;GLNK21;0;LENL;N;71;295.1;0.00605;1.78;0.07;0;1.85
B19;020;202607;202607;GLNK22;0;LENL;N;23351;72,370.7;0.00605;437.84;16.59;0;454.43
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
