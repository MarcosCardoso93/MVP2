# Arquivo recusado — detraf_072026_credor.xlsx

**Pasta:** `C:\projetos\MVP2\MVP2\MVP2\DETRAF-UNIFICADO\unificado\arquivos\_QUARENTENA\202607\detraf_072026_credor`
**Colunas encontradas:** 17

## Por que foi recusado

| Posição | Campo | Esperado | Encontrado | Válidos |
|---|---|---|---|---|
| 1 | Devedora | EOT (Anexo 5) | `Xturbo Provedor de Internet EIRELI`, `Xturbo Provedor de Internet EIRELI`, `Xturbo Provedor de Internet EIRELI` | 0/5 |
| 2 | Referencia | AAAAMM | `010`, `010`, `011` | 0/5 |
| 3 | Tráfego | AAAAMM | `Vivo`, `Vivo`, `Telefâ€œnica` | 0/5 |
| 5 | Rel | 0, 1 ou vazio | `202607`, `202607`, `202607` | 0/5 |
| 7 | GH | S, R, N ou D | `00`, `00`, `00` | 0/5 |
| 8 | Chamadas | número inteiro | `LENL`, `LENL`, `LENLC` | 0/5 |
| 9 | Minutos | número | `N`, `R`, `N` | 0/5 |

## Primeiras linhas do arquivo

```
I55;Xturbo Provedor de Internet EIRELI;010;Vivo;202607;202607;Xturbo Provedor de Internet EIRELI;00;LENL;N;37255;77610.9;   0,00610;473.43;17.93;0,00;491.36
I55;Xturbo Provedor de Internet EIRELI;010;Vivo;202607;202607;Xturbo Provedor de Internet EIRELI;00;LENL;R;3459;8373;   0,00427;35.75;1.35;0,00;37.1
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
