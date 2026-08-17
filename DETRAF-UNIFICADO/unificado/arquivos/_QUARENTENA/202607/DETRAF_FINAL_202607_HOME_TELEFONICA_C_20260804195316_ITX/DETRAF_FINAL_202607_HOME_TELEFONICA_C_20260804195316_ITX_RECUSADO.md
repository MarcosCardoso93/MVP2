# Arquivo recusado — DETRAF_FINAL_202607_HOME_TELEFONICA_C_20260804195316_ITX.csv

**Pasta:** `C:\projetos\MVP2\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_QUARENTENA\202607\DETRAF_FINAL_202607_HOME_TELEFONICA_C_20260804195316_ITX`
**Colunas encontradas:** 15

## Por que foi recusado

- Tarifas remuneradas: há linhas cuja tarifa não corresponde à tarifa regulada vigente para a região, o grupo horário e o mês de tráfego da linha.

## Primeiras linhas do arquivo

```
006;011;202607;202607;5121100Y;0; GS3V;N;1209;6787,8;0,01686;114,44;4,34;0;118,78
006;011;202607;202607;53211008;0; GS3V;N;135;457,9;0,01686;7,72;0,29;0;8,01
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
