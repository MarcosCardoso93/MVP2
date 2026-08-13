# Arquivo recusado — Solução Network - VIVO (FIXA) - DETRAF - JULHO 2026.csv

**Pasta:** `C:\projetos\MVP2\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_QUARENTENA\202607\Solução Network - VIVO (FIXA) - DETRAF - JULHO 2026`
**Colunas encontradas:** 15

## Por que foi recusado

- Coluna 11 (Tarifa): a tarifa admite no máximo 5 casas decimais e não pode ser zero.
- Tarifas remuneradas: há linhas cuja tarifa não corresponde à tarifa regulada vigente para a região, o grupo horário e o mês de tráfego da linha.

## Primeiras linhas do arquivo

```
B38;941;202607;202607;MGA-RC-1  ;00;LENL;N;1160;3216,2;0,000000;0,00;0,00;0,00;0,00
B38;941;202607;202607;MGA-RC-1  ;00;LENL;R;21;42,7;0,000000;0,00;0,00;0,00;0,00
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
