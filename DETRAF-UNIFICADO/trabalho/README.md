# Trabalho — Saídas da Análise

Destino de tudo que a análise dos códigos produzir. **Ainda vazio.**

---

## Estrutura esperada

```
trabalho/
├── inventarios/
│   ├── recebimento-projeto-1.md ... recebimento-projeto-7.md
│   ├── inventario-projeto-1.md   ... inventario-projeto-7.md
│   ├── candidatos/       ← uma ficha por componente candidato
│   ├── duplicacoes/      ← um registro por par avaliado
│   └── mapa-real.md      ← consolidação em F3
└── evidencias/           ← trechos de código, saídas de execução, comparações
```

---

## `inventarios/`

**Registros de recebimento** — um por projeto, preenchido em M1 conforme o [checklist de inserção](../docs/03-checklists/checklist-insercao-dos-codigos.md).

**Inventários** — um por projeto, preenchido em M2 a partir do [template](../docs/05-proxima-etapa/templates/inventario-por-projeto.md).

**`candidatos/`** — uma [ficha](../docs/05-proxima-etapa/templates/ficha-de-componente-candidato.md) por componente candidato, **inclusive os rejeitados**. A ficha de um rejeitado precisa dizer qual critério falhou e o que mudaria o veredicto.

**`duplicacoes/`** — um [registro](../docs/05-proxima-etapa/templates/registro-de-duplicacao.md) por par avaliado, **inclusive os que não foram unificados**. Sem o registro de um não-par, a próxima pessoa reavalia o mesmo trecho e chega a outra conclusão.

**`mapa-real.md`** — a reconciliação, em F3, entre o mapa documental e o que o código realmente mostrou. Se divergirem, o mapa real prevalece.

## `evidencias/`

Trechos de código que sustentam um achado, saídas de execução, comparações de artefatos entre origem e destino.

Útil sobretudo para os achados que **contradizem a documentação** — a evidência é o que sustenta a conversa com o PO.

---

## Convenções

- Um arquivo por unidade de análise. Nada de documento único e gigante.
- Toda afirmação sobre código traz **arquivo e linha**.
- Toda conclusão que depende de verificação futura vem marcada com ⚠️.
- Registros de itens **rejeitados** ou **não unificados** valem tanto quanto os positivos.

---

## Fluxo de atualização

Conforme a análise avança, estes documentos de `docs/` são atualizados:

| Documento | O que atualizar |
|---|---|
| [`docs/04-relatorios/matriz-de-rastreabilidade.md`](../docs/04-relatorios/matriz-de-rastreabilidade.md) | coluna **Código** (arquivo e linha) — é gate de M2 |
| [`docs/04-relatorios/duvidas-pendentes.md`](../docs/04-relatorios/duvidas-pendentes.md) | dúvidas novas e respostas recebidas |
| [`docs/04-relatorios/riscos-conhecidos.md`](../docs/04-relatorios/riscos-conhecidos.md) | riscos confirmados ou descartados |
| [`docs/01-entendimento/mapa-projetos-epicos-historias-rpas.md`](../docs/01-entendimento/mapa-projetos-epicos-historias-rpas.md) | se o mapa real divergir do documental |
