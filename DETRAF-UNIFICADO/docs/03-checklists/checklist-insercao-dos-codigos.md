# Checklist — Inserção dos Códigos

> ⚠️ **Fotografia da etapa documental (2026-07-30).** Este documento foi escrito
> **antes** de qualquer código chegar, e descreve o entendimento daquele momento.
> Vários pontos já mudaram — em especial: o Épico 5 **tem** projeto (o P7, entregue
> em 2026-08-04), e as HUs 12 a 19 estão implementadas e orquestradas.
>
> **Fonte do estado atual:** `docs/04-relatorios/duvidas-pendentes.md` (pendências),
> `matriz-de-rastreabilidade.md` (HUs) e `unificado/README.md` (código).

Aplicar a **cada projeto** ao recebê-lo, antes de qualquer análise. Marco **M1**.

**Objetivo:** garantir que o projeto está completo e utilizável antes de investir tempo analisando algo incompleto.

---

## Antes de tudo

- [ ] O projeto foi colocado na pasta correta de `projetos-origem/`
- [ ] **Nada foi alterado** — nem formatação, nem `.gitignore`, nem renomeação de arquivo
- [ ] O `.gitkeep` da pasta pode ser removido agora que há conteúdo real

| Pasta | Recebe |
|---|---|
| `projeto-1-epico-1-captura/` | Épico 1 — HU-01, 02, 03 |
| `projeto-2-epico-2-validacao/` | Épico 2 — HU-04 a 08 |
| `projeto-3-epico-3-batimento/` | Épico 3 — HU-09, 10, 11 |
| `projeto-4-epico-4-h19/` | Épico 4 (exceto HU-15) + HU-19 |
| `projeto-5-h15/` | HU-15 |
| `projeto-6-h20-h21/` | HU-20 + HU-21 |
| `projeto-7-epico-5-carga-agi/` | ⚠️ reservado — HU-17, HU-18 |

---

## 1. Integridade do que chegou

- [ ] O código veio **completo** — não é um recorte nem um diretório parcial
- [ ] Veio com histórico de versionamento (`.git`)? Registrar sim/não — o histórico ajuda a datar a implementação contra a V2
- [ ] Não há arquivos truncados ou corrompidos
- [ ] Não há dependência de caminho absoluto da máquina de origem que impeça sequer abrir o projeto

**Registrar:** tamanho, número de arquivos, data do último commit (se houver).

---

## 2. Ponto de entrada

- [ ] Existe um ponto de entrada identificável (`main.py` ou equivalente)
- [ ] Está claro **como o projeto é executado** — comando, agendador, gatilho manual
- [ ] Se houver mais de um ponto de entrada, todos foram identificados

⚠️ Se não houver ponto de entrada claro, registrar como achado. Um projeto sem forma óbvia de executar dificulta a comprovação de equivalência funcional em F6.

---

## 3. Dependências

- [ ] Há declaração de dependências (`requirements.txt`, `pyproject.toml`, `Pipfile`, ou equivalente)
- [ ] As versões estão fixadas ou pelo menos delimitadas
- [ ] Há dependência de biblioteca específica de Windows/COM (Outlook, Excel)? Listar
- [ ] Há dependência de ferramenta externa não-Python? Listar
- [ ] Há dependência de rede (Lagoa, banco WebFat, AGI) que precisa de acesso para sequer rodar? Listar

⚠️ Se não houver declaração de dependências, registrar. Reconstruir isso depois custa mais do que perguntar agora a quem entregou.

---

## 4. Configuração

- [ ] Foi identificado onde ficam caminhos de rede, strings de conexão e endereços
- [ ] Foi identificado como as credenciais são obtidas
- [ ] Há arquivo de configuração de exemplo, ou apenas o real?

### 4.1 🔴 Segurança — verificação obrigatória

- [ ] **Não há credencial, senha, token ou string de conexão com senha commitada no código**

⚠️ **Se houver, reportar imediatamente ao GP antes de prosseguir.** Não é achado para o relatório final — é incidente. Não commite o projeto no repositório unificado até que isso seja resolvido com quem tem autoridade para decidir sobre rotação de credencial.

---

## 5. Documentação que veio junto

- [ ] Existe README ou documentação própria do projeto? Registrar
- [ ] Existem comentários que expliquem decisões não óbvias?
- [ ] Existe algum registro de qual versão da especificação (V1 ou V2) o projeto seguiu? ⚠️ Raro, mas de altíssimo valor se existir
- [ ] Existe massa de dados de exemplo, fixtures ou arquivos de teste?

---

## 6. Testes

- [ ] Existem testes automatizados? Registrar quantos e de que tipo
- [ ] Os testes rodam? (Só executar; não corrigir)
- [ ] Existe massa de dados que permita exercitar o projeto sem acesso a produção?

---

## 7. Escopo aparente

Inspeção superficial, sem análise profunda — isso é M2. Aqui só se procura por surpresa:

- [ ] O projeto parece cobrir as HUs esperadas
- [ ] ⚠️ **O projeto contém código de outro épico?** Registrar
- [ ] ⚠️ **O projeto contém código do fluxo de Receita?** (escopo das demandas irmãs ATA0000571/567/572, explicitamente fora deste MVP)
- [ ] Há indício visível de código morto ou funcionalidade abandonada?

### 7.1 🔴 Verificação específica do Projeto 4 — onde está o Épico 5

Ao receber o **P4**, executar esta verificação **antes de seguir**:

- [ ] Existe automação de UI apontando para `Detraf > Importar Dados` no AGI?
- [ ] Existe automação de UI apontando para `Contestação > Gerenciar` no AGI?
- [ ] Existe escrita no campo `carga_agi` de `tbl_rpa_log_detraf_despesa_contestacao`?

**Se sim** → o Épico 5 está no P4. Registrar, descartar `projeto-7-epico-5-carga-agi/`, atualizar o mapa.
**Se não** → verificar se chegou um sétimo projeto. Se não chegou, ⚠️ **HU-17/HU-18 provavelmente não estão implementadas** — escalar ao GP, porque isso transforma parte de M8 em desenvolvimento, não migração.

---

## 8. Impedimentos de ambiente

Levantar **agora**, não na validação:

- [ ] Existe **ambiente de teste do AGI**?
- [ ] Existe **caixa de e-mail de teste** para o Outlook?
- [ ] Existe **banco WebFat de teste**?
- [ ] Existe forma de isolar o **contador de numeração CT** dos números reais?
- [ ] Há acesso às **pastas de rede Lagoa** (ou a uma réplica de teste)?

⚠️ Resposta "não" a qualquer um destes é **impedimento**, não inconveniente. Sem ambiente de teste do AGI e caixa de e-mail de teste, os marcos M7 e M8 não podem ser validados sem tocar produção — e tocar produção significa enviar contestações reais a operadoras e lançar valores no sistema financeiro. Escalar ao GP no ato.

---

## 9. Registro de recebimento

Preencher e salvar em `trabalho/inventarios/recebimento-projeto-N.md`:

```markdown
# Recebimento — Projeto N

- **Data:**
- **Recebido de:**
- **Pasta:**
- **Escopo esperado:** HU-xx a HU-yy

## Integridade
- Completo: sim/não
- Histórico de versionamento: sim/não — último commit:
- Arquivos: N | Tamanho:

## Execução
- Ponto de entrada:
- Como executa:

## Dependências
- Declaração: sim/não — arquivo:
- Dependências de SO/COM:
- Dependências de rede:

## Configuração
- Onde fica:
- Credenciais:
- 🔴 Credencial commitada: sim/não  ← se sim, ESCALAR

## Documentação e testes
- README: sim/não
- Testes: N | rodam: sim/não
- Massa de dados: sim/não

## Escopo aparente
- Cobre o esperado: sim/não
- Código de outro épico:
- Código de Receita (fora de escopo):

## Achados imediatos
-

## Impedimentos
-

## Veredicto
[ ] Pronto para análise (M2)
[ ] Pendente — falta:
```

---

## Gate para M2

O projeto só entra em análise quando:

- [ ] Ponto de entrada identificado
- [ ] Dependências listadas
- [ ] Registro de recebimento preenchido
- [ ] Nenhuma credencial exposta pendente de resolução

Projeto que não chegou: registrar explicitamente como **ausente**, com a data em que foi solicitado. Ausência silenciosa vira suposição na fase seguinte.
