# Arquivo recusado — Declaração de Tráfego UFINET x VIVO SMP 07-2026.xlsx

**Pasta:** `C:\projetos\MVP2\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_QUARENTENA\202607\Declaração de Tráfego UFINET x VIVO SMP 07-2026`
**Colunas encontradas:** 15

## Por que foi recusado

- Coluna 10 (Minutos): os minutos admitem no máximo 1 casa decimal.

## Primeiras linhas do arquivo

```
125;010;202607;202607;AVA.BRT.01;0;LENL; N;73;101.7;0.0061;0.62;0.02;0;0.64
125;010;202607;202607;AVA.BRT.01;0;LENL; R;8;11.8;0.00427;0.05;0;0;0.05
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
