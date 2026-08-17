# Arquivo recusado — DETRAF-TMCO-0123-2026-GGNET-VIVO SMP - RESUMO EOT_044_045_202607.csv

**Pasta:** `C:\RPA\Dtraf\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_TEMP\202607\Detrafs Recebidos-60b037`
**Colunas encontradas:** 0

## Por que foi recusado

O arquivo tem linha(s) que atendem ao fluxo LL (descritor iniciado e terminado em 'L', serviço STFC) — para arquivo de Detraf (diferente de expectativa), isso marca o arquivo **inteiro** como inválido, por decisão de configuração: tráfegos deste fluxo não são separados de arquivos de operadora.

## Primeiras linhas do arquivo

```
197;45;202607;202607;BRT_47LC1E;00;LENL;N;5015;11460,1;0,00608;69,67;2,63;0;72,3
197;45;202607;202607;BRT_47LC1E;00;LENL;R;416;947,7;0,00425;4,02;0,15;0;4,17
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
