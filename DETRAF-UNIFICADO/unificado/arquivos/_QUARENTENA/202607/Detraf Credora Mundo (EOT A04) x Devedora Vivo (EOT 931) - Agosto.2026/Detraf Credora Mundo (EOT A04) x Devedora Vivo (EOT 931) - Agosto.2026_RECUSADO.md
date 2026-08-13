# Arquivo recusado — Detraf Credora Mundo (EOT A04) x Devedora Vivo (EOT 931) - Agosto.2026.csv

**Pasta:** `C:\projetos\MVP2\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_QUARENTENA\202607\Detraf Credora Mundo (EOT A04) x Devedora Vivo (EOT 931) - Agosto.2026`
**Colunas encontradas:** 16

## Por que foi recusado

- Colunas 12 a 15 (valores financeiros): os valores financeiros admitem no máximo 2 casas decimais.
- Tarifas remuneradas: há linhas cuja tarifa não corresponde à tarifa regulada vigente para a região, o grupo horário e o mês de tráfego da linha.

## Primeiras linhas do arquivo

```
A04;931;202607;202607;MUNBH01   ;0;GS8L;N;65;493,7;0,0061;3,01;0,109865;0;3,119865;nan
nan;nan;nan;nan;nan;nan;nan;nan;nan;nan;nan;nan;nan;nan;3,119865;nan
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
