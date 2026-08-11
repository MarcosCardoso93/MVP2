# Arquivo recusado — RECUSA_referencia_errada.csv

**Pasta:** `C:\RPA\Dtraf\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_TESTE_RPA1\_QUARENTENA\202603\RECUSA_referencia_errada`
**Colunas encontradas:** 15

## Por que foi recusado

- Coluna 3 (Referência): a referência precisa ser 202603 (AAAAMM) em todas as linhas.
- Coluna 4 (Tráfego): o mês de tráfego precisa ser um de 202601, 202602, 202603.

## Primeiras linhas do arquivo

```
025;010;202509;202509;SPOX_0001;0;LENX;N;1;2,0;0,00631;0,01;0,00;0,00;0,01
025;010;202509;202509;SPOX_0001;0;LENX;N;1;2,0;0,00631;0,01;0,00;0,00;0,01
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
