# Arquivo recusado — DETRAT_DATORA_STFC_X_TELEFONICA_BRASIL___STFC_STFC_R_072026_V00.xlsx

**Pasta:** `C:\projetos\MVP2\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_QUARENTENA\202607\DETRAT_DATORA_STFC_X_TELEFONICA_BRASIL___STFC_STFC_R_072026_V00`
**Colunas encontradas:** 19

## Por que foi recusado

| Posição | Campo | Esperado | Encontrado | Válidos |
|---|---|---|---|---|
| 7 | GH | S, R, N ou D | `TNENL`, `TNENI`, `TNENI` | 0/200 |
| 8 | Chamadas | número inteiro | `N`, `N`, `N` | 0/200 |

## Primeiras linhas do arquivo

```
621;011;202607;202607;DAT.FIX.FX;00;TU-TX-RL;TNENL;N;1831;2088.6;0.00605;12.62;0.47;0;13.09;nan;F;232
621;011;202607;202607;DAT.FIX.FX;00;TU-TX-RIU-F;TNENI;N;20868;28291.7;0.01275;360.72;13.67;0;374.39;nan;F;051
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
