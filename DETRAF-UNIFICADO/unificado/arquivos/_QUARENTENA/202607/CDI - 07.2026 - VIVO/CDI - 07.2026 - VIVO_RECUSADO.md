# Arquivo recusado — CDI - 07.2026 - VIVO.xlsx

**Pasta:** `C:\projetos\MVP2\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_QUARENTENA\202607\CDI - 07.2026 - VIVO`
**Colunas encontradas:** 16

## Por que foi recusado

- Coluna 10 (Minutos): os minutos admitem no máximo 1 casa decimal.

## Primeiras linhas do arquivo

```
C61;45;202607;202607;OI_FPS;0;LENL;N;1511;4098.01;0.00608;24.91;0.9;0;25.81;48
C61;45;202607;202607;OI_FPS;0;LENL;R;87;325.42;0.00425;1.38;0.05;0;1.43;48
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
