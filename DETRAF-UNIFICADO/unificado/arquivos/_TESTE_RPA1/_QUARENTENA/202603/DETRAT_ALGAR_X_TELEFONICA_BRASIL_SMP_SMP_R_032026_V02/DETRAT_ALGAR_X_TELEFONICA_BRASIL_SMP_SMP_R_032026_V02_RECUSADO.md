# Arquivo recusado — DETRAT_ALGAR_X_TELEFONICA_BRASIL_SMP_SMP_R_032026_V02.csv

**Pasta:** `C:\RPA\Dtraf\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_TESTE_RPA1\_QUARENTENA\202603\DETRAT_ALGAR_X_TELEFONICA_BRASIL_SMP_SMP_R_032026_V02`
**Colunas encontradas:** 18

## Por que foi recusado

- Tarifas remuneradas: há linhas cuja tarifa não corresponde à tarifa regulada vigente para a região, o grupo horário e o mês de tráfego da linha.

## Primeiras linhas do arquivo

```
25;10;202603;202603;SPOX_1007;0; LENL;N;1;2;0,00631;0,01;0;0;0,01;0;F;25
25;10;202603;202603;SPOX_0046;0; LENL;R;7;9,8;0,00441;0,04;0;0;0,04;0;F;25
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
