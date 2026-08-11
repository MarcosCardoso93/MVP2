# Projetos de Origem

Aqui serão inseridos os códigos dos projetos atuais, **sem qualquer alteração**.

---

## 🔴 Regra de ouro

**Depois de inserido, o conteúdo desta pasta é SOMENTE LEITURA — para sempre.**

Nada é movido, alterado, refatorado ou excluído. A migração **copia e adapta** para [`../unificado/`](../unificado/).

Isso não é preciosismo: `projetos-origem/` é a **única referência** para comprovar que a unificação preservou o comportamento. Sem ela, não há como distinguir "mudou porque decidimos" de "quebrou sem ninguém notar".

---

## As pastas

| Pasta | Escopo | HUs | RPA destino | Ordem de análise |
|---|---|---|---|---|
| [`projeto-1-epico-1-captura/`](projeto-1-epico-1-captura/) | Épico 1 | 01, 02, 03 | 1 | **1º** |
| [`projeto-2-epico-2-validacao/`](projeto-2-epico-2-validacao/) | Épico 2 | 04–08 | 2 | **2º** |
| [`projeto-3-epico-3-batimento/`](projeto-3-epico-3-batimento/) | Épico 3 | 09, 10, 11 | 2 | **3º** |
| [`projeto-4-epico-4-h19/`](projeto-4-epico-4-h19/) | Épico 4 (exceto HU-15) + HU-19 | 12, 13, 14, 16, 19 | 3 | **4º** |
| [`projeto-5-h15/`](projeto-5-h15/) | HU-15 | 15 | 3 | **6º** |
| [`projeto-6-h20-h21/`](projeto-6-h20-h21/) | HU-20 + HU-21 | 20, 21 | **3 e 4** | **7º** |
| [`projeto-7-epico-5-carga-agi/`](projeto-7-epico-5-carga-agi/) | ⚠️ **reservada** — Épico 5 | 17, 18 | 3 | **5º** |

Cada pasta tem um `README.md` com escopo, verificações prioritárias e pontos de atenção. **Leia o da pasta antes de analisar o projeto.**

---

## Por que a ordem de análise não é 1→7

```
P1 → P2 → P3 → P4 → P7 → P5 → P6
```

- **Segue o fluxo de dados.** Cada projeto é lido já sabendo o que o anterior produziu — fronteiras e duplicações aparecem por comparação, não por busca.
- **P4 antes de P7** porque é a análise do P4 que responde se o Épico 5 está lá dentro.
- **P5 e P6 por último** porque são pequenos e servem de **teste de confirmação** dos candidatos a componente compartilhado: se a camada de e-mail identificada nos projetos anteriores não servir ao P5, a abstração está errada.

---

## ⚠️ A pasta 7 é uma reserva, não um projeto

O **Épico 5 (HU-17 e HU-18 — carga no AGI)** não foi atribuído a nenhum dos seis projetos informados, embora seja responsabilidade explícita do RPA 3.

Três hipóteses, a testar ao receber o P4: (1) está dentro do P4 — mais provável; (2) existe um sétimo projeto; (3) não foi implementado.

Detalhes e o teste em [`projeto-7-epico-5-carga-agi/README.md`](projeto-7-epico-5-carga-agi/README.md).

---

## Ao inserir cada projeto

1. Copie o código para a pasta correspondente, **sem alterar nada**
2. Aplique [`../docs/03-checklists/checklist-insercao-dos-codigos.md`](../docs/03-checklists/checklist-insercao-dos-codigos.md)
3. Salve o registro em `trabalho/inventarios/recebimento-projeto-N.md`
4. Remova o `.gitkeep` da pasta
5. 🔴 **Verifique credencial exposta** — se houver, escale antes de prosseguir
6. 🔴 **Levante os ambientes de teste** (AGI, e-mail, banco) — a ausência é impedimento, não inconveniente

Projeto que **não** chegar: registre explicitamente como ausente, com a data em que foi solicitado. Ausência silenciosa vira suposição na fase seguinte.
