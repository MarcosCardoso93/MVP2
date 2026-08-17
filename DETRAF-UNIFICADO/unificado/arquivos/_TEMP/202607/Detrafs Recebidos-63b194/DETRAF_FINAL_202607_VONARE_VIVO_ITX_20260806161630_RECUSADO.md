# Arquivo recusado — DETRAF_FINAL_202607_VONARE_VIVO_ITX_20260806161630.csv

**Pasta:** `C:\RPA\Dtraf\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_TEMP\202607\Detrafs Recebidos-63b194`
**Colunas encontradas:** 0

## Por que foi recusado

O arquivo tem linha(s) que atendem ao fluxo LL (descritor iniciado e terminado em 'L', serviço STFC) — para arquivo de Detraf (diferente de expectativa), isso marca o arquivo **inteiro** como inválido, por decisão de configuração: tráfegos deste fluxo não são separados de arquivos de operadora.

## Primeiras linhas do arquivo

```
345;70;202607;202605;TTLK01     ;0; LENL;N;33930;76484,5;0,00605;479,62;16,89;462,73;14,48;0
345;70;202607;202605;TTLK01     ;0; LENL;R;3828;7050,8;0,00423;30,91;1,09;29,82;0,93;0
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
