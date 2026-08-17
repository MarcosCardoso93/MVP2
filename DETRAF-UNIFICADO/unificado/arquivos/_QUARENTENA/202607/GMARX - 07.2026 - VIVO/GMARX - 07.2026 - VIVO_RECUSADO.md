# Arquivo recusado — GMARX - 07.2026 - VIVO.xlsx

**Pasta:** `C:\projetos\MVP2\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_QUARENTENA\202607\GMARX - 07.2026 - VIVO`
**Colunas encontradas:** 16

## Por que foi recusado

- Coluna 2 (EOT da Vivo): a coluna da devedora traz EOT que não corresponde a nenhum nome fantasia da Vivo.
- Tarifas remuneradas: há linhas cuja tarifa não corresponde à tarifa regulada vigente para a região, o grupo horário e o mês de tráfego da linha.

## Primeiras linhas do arquivo

```
45;C81;202607;202607;Vivo;0;LSNV;N;146;152.3;0.00608;0.92;0.03;0;0.9500000000000001;nan
45;C81;202607;202607;Vivo;0;LSNV;R;6;17.1;0.00425;0.07;0;0;0.07;nan
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
