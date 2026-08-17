# Arquivo recusado — FORZA -  07.2026 - VIVO.xlsx

**Pasta:** `C:\RPA\Dtraf\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_QUARENTENA\202607\9D024E55DD250D4D00005211FBDF0000137D0D4C70E1CF4091747B97613AB5A60000A35B1B640000`
**Colunas encontradas:** 16

## Por que foi recusado

| Posição | Campo | Esperado | Encontrado | Válidos |
|---|---|---|---|---|
| 0 | Credora | EOT numérica | `B47`, `B47`, `B47` | 0/4 |

## Primeiras linhas do arquivo

```
B47;50;202607;202607;OI_CTW_SIP;0;LENL;N;15594;32462.44;0.00608;197.37;7.69;0;205.06;54
B47;50;202607;202607;OI_CTW_SIP;0;LENL;R;907;2152.02;0.00425;9.14;0.35;0;9.49;54
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
