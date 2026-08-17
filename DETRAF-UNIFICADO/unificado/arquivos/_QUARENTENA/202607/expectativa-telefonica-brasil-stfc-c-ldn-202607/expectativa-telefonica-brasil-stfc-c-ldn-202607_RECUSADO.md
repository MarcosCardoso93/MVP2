# Arquivo recusado — expectativa-telefonica-brasil-stfc-c-ldn-202607.xlsx

**Pasta:** `C:\projetos\MVP2\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_QUARENTENA\202607\expectativa-telefonica-brasil-stfc-c-ldn-202607`
**Colunas encontradas:** 15

## Por que foi recusado

- Coluna 10 (Minutos): os minutos admitem no máximo 1 casa decimal.
- Tarifas remuneradas: há linhas cuja tarifa não corresponde à tarifa regulada vigente para a região, o grupo horário e o mês de tráfego da linha.

## Primeiras linhas do arquivo

```
B19;200;202607;202607;GLNK21;0;NENL;N;15;53.7;0.00605;0.32;0.01;0;0.33
B19;200;202607;202607;GLNK22;0;NENL;N;199;642.6;0.00605;3.88;0.15;0;4.03
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
