# Arquivo recusado — DETRAT_ALGAR_X_TELEFONICA_BRASIL_STFC_STFC_R_032026_V02.csv

**Pasta:** `C:\projetos\MVP2\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_TESTE_RPA1\_QUARENTENA\202603\DETRAT_ALGAR_X_TELEFONICA_BRASIL_STFC_STFC_R_032026_V02`
**Colunas encontradas:** 18

## Por que foi recusado

- Tarifas remuneradas: há linhas cuja tarifa não corresponde à tarifa regulada vigente para a região, o grupo horário e o mês de tráfego da linha.

## Primeiras linhas do arquivo

```
12;11;202603;202603;ULAX_1204;0;2NENI;N;194;230,1;0,00787;1,81;0,06;0;1,87;0;F;356
12;11;202603;202603;SPO_10156;0;2NENI;S;11;15,6;0,00787;0,11;0;0;0,11;0;F;143
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
