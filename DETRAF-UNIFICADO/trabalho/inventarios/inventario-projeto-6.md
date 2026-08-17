# Inventário — Projeto 6: HU-20 e HU-21

- **Pasta:** `projetos-origem/projeto-6-h20-h21/`
- **HUs esperadas:** HU-20 (RPA 3) e HU-21 (RPA 4)
- **HUs entregues:** as duas — a HU-20 em 2026-08-05, a **HU-21 em 2026-08-10**
- **Estado:** ambas migradas

---

## 1. ✅ A HU-21 chegou em 2026-08-10 — o RPA 4 existe

**O texto abaixo descreve a primeira entrega, de 2026-08-05, e está mantido como
registro.** Na segunda entrega a pasta ganhou `H21/`, com
`src/services/AGI/Retificacao_Contestacao.py` (563 linhas), as imagens de
`Contestação > Gerenciar` e o fator `0,9635` no código.

A migração está em `unificado/rpa4_retificacao/`; o que mudou no caminho está no
README de lá. Em resumo: a camada de banco foi reescrita sobre SQLAlchemy, os
`print` viraram log, o kill-switch passou a ser lido de fato, o fator virou
constante, e a automação do AGI subiu para `comum/integracoes/agi.py` — a
promoção que este inventário previa como "quando o Projeto 6 chegar".

### O que a primeira entrega dizia (2026-08-05)

A pasta tem apenas `H20/`. Busca exaustiva: `HU-21`, `Retificação`, `Recuperação`
e o fator `0,9635` só aparecem no `README.md` do briefing, **em nenhum `.py`**.
Não há `Retificacao*.py`, nem imagens de `Contestação > Gerenciar`.

**Consequências:**

- a **cisão P6 → RPA 3 + RPA 4** não acontece; `unificado/rpa4_retificacao/`
  continua com só um `README.md`;
- o marco **M7 permanece bloqueado**;
- o Projeto 6 era o teste de confirmação da camada do AGI para **dois**
  consumidores. Com só a HU-20, o teste é parcial — mas dá resultado (§5).

---

## 2. Estrutura e execução

```
H20/
├── main.py                                   4 linhas
├── src/
│   ├── config/     config.py (73) · conexao.py (161)
│   ├── main/       process_handle.py (15)
│   ├── services/AGI/
│   │   ├── AGI_config.py            (286)  login/navegação/export
│   │   └── Verificacao_Relatorio.py (192)  HU-20
│   ├── utils/      utils.py (24)
│   └── view/imagens/AGI_CONFIG/            15 PNGs
└── data/
    ├── relatorio_baixado/remessa_baixada.csv    20,6 MB · 93.108 linhas
    └── inconsistencias/*.xlsx                   2 saídas reais
```

**Total: 755 linhas — mas 471 (62%) são cópia do Projeto 7.** A contribuição
genuína são as ~190 linhas de `Verificacao_Relatorio.py`.

| Item | Valor |
|---|---|
| Ponto de entrada | `main.py` → `ProcessHandle().run()` |
| Segundo entrypoint | `Verificacao_Relatorio.py:191` — dispara login em **produção** se o arquivo for executado direto |
| Testes | **nenhum** |
| Kill-switch | ⚠️ **declarado e nunca lido** — ver §7 |
| Python | **3.12+** — f-strings aninhadas (PEP 701), como o P7 |

Mesma origem do P5 e do P7: o `RPA_DETRAF_RECEITA` (MVP1). `config.py:11` declara:
*"REAPROVEITADO do RPA_DETRAF_RECEITA"*. E `conexao.py` e `utils.py` são **byte a
byte iguais aos do P7**, exceto duas linhas — é o mesmo pacote, montado na mesma
sessão.

---

## 3. 🔴 Credencial do AGI — segunda cópia

O `.env` traz **preenchidos**:

| Variável | Tamanho |
|---|---|
| `RPA_DETRAF_DESPESA_AGI_USER` | 8 caracteres |
| `RPA_DETRAF_DESPESA_AGI_PASSWORD` | 28 caracteres |

**Os tamanhos batem exatamente com os do Projeto 7.** Provavelmente é a **mesma
credencial**, agora em **dois** arquivos que circularam fora do controle de
versão. A rotação, já escalada no P7, deixa de ser sobre uma cópia isolada.

**O arquivo se contradiz:** a linha 1 diz *"Segredos NÃO ficam aqui"*, e as linhas
4 e 5 os preenchem. O `config.py:31` lê por `os.environ.get`, coerente com a
intenção — mas o `load_dotenv` injeta o `.env` antes, então o valor do arquivo
vence.

O `.env.example` está correto: não traz as duas.

### 🟡 Dado de produção junto com o código

`data/relatorio_baixado/remessa_baixada.csv` — **20,6 MB, 93.108 linhas** de
tráfego real de 202607, com nomes de operadora, minutos e valores financeiros.
Mais duas planilhas de inconsistência reais. Não migra.

---

## 4. Mapeamento HU → código

| Critério de aceite (V2, ¶689–¶702) | Status |
|---|---|
| `Relatórios > Detraf > Receitas e Despesas` | ✅ `AGI_config.Baixar_Remessa` |
| Filtro por período | ✅ `_selecionar_periodo` |
| Filtro por Natureza "D" | ✅ no DataFrame, não na tela |
| Filtro por operadora | ⚠️ `groupby`, não filtro — cobre "todas as operadoras", não "filtrar uma" |
| Somar `Vlr. Bruto` × subtotal do EC | ✅ implementado e **exercitado** |
| **CBS / IBS Municipal / IBS Estadual** (¶702) | ❌ **ausente, com o dado em mãos** |
| **Sinalização de inconsistência** | ❌ **esqueleto** — grava `.xlsx` e `print()` |

### 🔴 O CSV real **tem** CBS/IBS — e o README afirma o contrário

O `remessa_baixada.csv` entregue traz **22 colunas**, incluindo `Vlr. IBS
Estadual`, `Vlr. IBS Municipal` e `Vlr. CBS`.

Mas `H20/README.md:24-29` lista **17** e conclui que são *"**idênticas** às usadas
no exemplo de Receita"*. **Não são** — o export do AGI já ganhou as cinco colunas
novas, e o arquivo entregue no próprio pacote prova isso.

O código tem `for col in ("Vlr. Bruto",)` — uma tupla de **um** elemento. Ou seja:
o requisito do ¶702 estava a poucas linhas de distância, com o insumo disponível.
A afirmação *"CONFIRMADO … não precisa mais de confirmação"* em
`Verificacao_Relatorio.py:29` está **factualmente errada**.

### 🔴 A fonte do Encontro de Contas diverge do unificado

`config.py:69` fixa `CELULA_SUBTOTAL_DESPESA = "O87"` e o service lê o `.xlsx` por
`openpyxl`, achando a aba com `operadora.upper() in nome.upper()`.

Três fragilidades numa linha: célula fixa, arquivo externo, e busca por substring
— `"OI"` casaria com qualquer aba que contenha "oi". O próprio autor marca o risco
(`:150`): pode ser preciso um DE-PARA entre `"AMPERNET"` (AGI) e
`"Ampernet Telecom"` (aba).

No unificado o EC é **banco**. **Resolvido pelo cliente em 2026-08-05: banco.**

---

## 5. Duplicação — e o veredito sobre a camada do AGI

### `AGI_config.py`: **283 de 286 linhas idênticas ao P7**

As três divergências são **melhorias reais**, de quem rodou em produção:

| Ponto | P7 / unificado | P6 |
|---|---|---|
| Título do diálogo de download | literal em inglês | **regex bilíngue** — o idioma da VM varia |
| Reescrita do CSV | `open("w")` direto | `chmod` + **retry 5×** com `PermissionError` tratado |
| Comentário do `Confirm Save As` | — | nota bilíngue |

**A API pública é idêntica; nenhuma função nova.**

→ As duas primeiras foram **portadas** para `agi.py`. O `_corrigir_aspas_impares`
unificado tinha exatamente o bug de permissão que o P6 aprendeu a contornar —
sinal de que alguém rodou e apanhou.

### O veredito: a abstração está certa, a promoção continua rejeitada

- ✅ `AGI_config.py` serviu a um **terceiro caso de uso sem uma linha de alteração
  de API** — a abstração se sustenta;
- ❌ mas a HU-21 não veio, então o AGI segue com **um consumidor só** (o RPA 3), e
  o critério **C1 continua falhando**.

→ Ficha **REJEITADA por C1**, com o gatilho mudando de *"quando o P6 chegar"* para
**"quando a HU-21 chegar"**.

### O resto é duplicação pura

| Arquivo | Situação |
|---|---|
| `utils.py` | **diff vazio** contra o P7 — descartado |
| `conexao.py` | difere do P7 em 2 linhas; mysql-connector + SQL cru — descartado |
| `config.py` | replica `comum/config/configuration.py` — descartado |
| `print()` × 6 | → `logger` |
| 15 PNGs | **14 idênticos** ao unificado |

⚠️ `tbl_rpa_log_detraf_despesa_verificacao` (`conexao.py:110`) **não existe** em
`comum/dados/tabelas.py`, e o próprio comentário admite que o nome é *sugerido,
não confirmado*. Com a decisão do `.xlsx` em logs, a tabela **não foi criada**.

A camada de banco está **desligada** de qualquer forma: o import de `Banco` e
todas as chamadas de `log()` estão comentados.

---

## 6. Dependências

`requirements.txt` — 28 pacotes, **diff vazio contra o P7**. Realmente importados:
7. Os outros ~20 são transitivos ou herança morta (`xlwt`, `easygui`, `requests`…).

⚠️ **Terceira ocorrência dos mesmos dois problemas:**
- `mysql-connector-python` — a camada unificada usa SQLAlchemy + PyMySQL;
- `dotenv==0.9.9` **junto com** `python-dotenv==1.2.1` — o primeiro é pacote
  **diferente**, um stub do PyPI que conflita.

---

## 7. Achados

### 🔴 Críticos

1. **HU-21 não entregue** — o RPA 4 continua vazio, M7 bloqueado (§1)
2. **Credencial do AGI preenchida**, segunda cópia, mesmos tamanhos do P7 (§3)
3. **Kill-switch decorativo** — `PERMITIR_ACAO_AGI` existe em `config.py:24` e
   **não é lido em lugar nenhum**. Diferente do P5 e do P7, onde ele guarda a
   ação. Corrigido na migração: `PERMITIR_ACESSO_AGI`
4. **CBS/IBS ausente com o dado disponível** (§4)
5. **`_sinalizar_inconsistencias` é esqueleto** — é o critério de aceite central

### 🟡 Relevantes

6. **`DIRETORIO_REMESSA_BAIXADA` fora do `.env.example`** — quem seguir o README e
   rodar recebe `TypeError` **depois** de já ter logado no AGI de produção
7. Fonte do EC divergente do unificado (§4)
8. Match de operadora por substring — falso positivo silencioso
9. **Tolerância arbitrária** (`> 0.01`) com TODO admitindo que o limiar oficial
   não foi confirmado → **pendência nova**
10. Tabela de log inexistente e não confirmada
11. Camada de banco paralela e desligada, com resíduos da Receita
12. **Sem `MANIFESTO_IMAGENS.md` nem `LEIA-ME_VALIDACAO.md`** — regressão em
    relação ao P7: não há registro de quais imagens foram validadas em qual VM
13. **4 imagens referenciadas e ausentes** — herança das constantes do P7; nenhuma
    é usada no caminho executado
14. `drop_box_export.png` diverge do unificado (745 B × 825 B) — só um dos
    recortes é o certo
15. `print()` em vez de logger
16. **Nenhum teste**
17. `dotenv` 0.9.9 e `mysql-connector` no requirements — terceira ocorrência
18. `.pyc` e 20,6 MB de dado real versionados
19. Duplo entrypoint — o segundo dispara login em produção
20. Caminhos absolutos de máquina no `.env`

### 🟢 Observações

- **`_comparar_com_encontro_de_contas` é código maduro.** Os comentários
  documentam dois bugs reais já apanhados: `None` virando dtype `object` e
  quebrando o `.abs()`, e o sinal invertido do EC (negativo) contra o AGI
  (positivo). **Isso rodou.**
- **Tratar `NaN` como inconsistente** é a escolha segura — operadora sem EC gera
  alerta em vez de passar batido. Mantida.
- As duas planilhas em `data/inconsistencias/` são **evidência de execução real**
  contra o AGI de produção.
- `load_dotenv` com caminho explícito, com o motivo documentado — melhor que o
  padrão do MVP1.

---

## 8. Conclusão

**Escopo real: metade do projeto, e a metade menor.**

| | Situação |
|---|---|
| HU-21 / RPA 4 | ❌ **zero linhas** |
| HU-20 — navegação e export | ✅ pronto, com 2 melhorias sobre o unificado |
| HU-20 — comparação AGI × EC | ✅ implementado e exercitado, mas sobre **planilha** |
| HU-20 — CBS/IBS | ❌ ausente, com o dado em mãos |
| HU-20 — sinalização | ❌ esqueleto |

**Complexidade: baixa para o código, alta para as decisões.** Mecanicamente é o
trabalho mais barato da leva. O que travava eram quatro decisões de negócio —
três resolvidas em 2026-08-05 (EC por banco, CBS/IBS incluídas, sinalização por
`.xlsx` em logs), e uma que **continua aberta**:

> ¶706 — *"Esse processo trata-se de uma **dupla checagem**, conferir com o
> solicitante se esse processo vale a pena ou não ser mantido."*

É a **Q7**. Esse parágrafo é **acréscimo da V2** — não existe no bloco antigo. A
HU foi migrada assim mesmo, atrás de kill-switch: é barata, e se for descartada
sai inteira sem arrastar nada junto.
