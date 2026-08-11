# Recebimento — Projetos 1 a 4

> Consolidado num único documento porque os quatro projetos chegaram no mesmo evento e a maior parte das respostas é comum. Aplica [`checklist-insercao-dos-codigos.md`](../../docs/03-checklists/checklist-insercao-dos-codigos.md).

- **Recebido em:** 2026-07-31
- **Projetos ausentes:** P5 (HU-15), P6 (HU-20/HU-21), P7 (Épico 5 — HU-17/HU-18). Serão adicionados depois.

---

## 1. Integridade

| Projeto | Arquivos | Fonte (linhas) | Testes | Histórico git |
|---|---|---|---|---|
| P1 — Épico 1 | 41 | ~1.200 | 8 arquivos | não veio |
| P2 — Épico 2 | 28 | ~2.900 | nenhum | não veio |
| P3 — Épico 3 | 24 | ~2.000 | nenhum | não veio |
| P4 — Épico 4 + HU-19 | 52 | ~2.800 | 14 arquivos + fixtures reais | não veio |

Nenhum projeto veio com `.git`, então não há como datar a implementação contra a V2 pelo histórico. A datação teve de ser inferida do conteúdo.

**Nenhum projeto trouxe README próprio** — os `README.md` nas pastas são os desta unificação, escritos na etapa anterior.

⚠️ **P4 referencia documentação que não foi entregue:** `AI/01-Arquitetura.md`, `AI/02-Convencoes.md`, `AI/09-Regras-Negocio-Epico4.md`, `AI/10-*`, `TODO/bloqueios.md`, `TODO/decisoes.md`. Essas fontes contêm as decisões D-1 a D-21 e os bloqueios B-D20/B-D21 citados no código. **Vale pedir**, porque várias resolvem pendências que a documentação oficial deixou abertas.

---

## 2. Execução

**Nenhum projeto tem `main.py`.** O ponto de entrada é `src/main/process_handle.py::run()`, que precisa ser chamado por algo que não veio no pacote.

| Projeto | Controller disparado | Método |
|---|---|---|
| P1 | `ProcessamentoController` | `processar()` |
| P2 | `ValidacaoDetrafsController` | `validar_detrafs()` |
| P3 | `BatimentoDetrafController` | `batimento_detraf()` |
| P4 | `GeracaoAgiController` | `gerar_artefatos()` ⚠️ **stub** |

⚠️ **P4 não executa nada.** `gerar_artefatos()` apenas emite logs de "etapa pendente" para cada HU. Os services existem, estão implementados e testados, mas nenhum é chamado. Registrado como lacuna funcional — ver inventário do P4.

---

## 3. Dependências

Nenhum projeto trouxe `requirements.txt`, `pyproject.toml` ou equivalente. As dependências tiveram de ser inferidas dos imports:

`pandas`, `numpy`, `sqlalchemy`, `pymysql`, `loguru`, `python-dotenv`, `python-dateutil`, `openpyxl`, `pywin32` (P1 — Outlook COM), `pytest` (P1/P4).

⚠️ **Falta a declaração de dependências.** Reconstruir versões depois custa mais do que pedir agora.

**Python:** os `__pycache__` são `cpython-314` — Python 3.14.

---

## 4. Configuração

Todos usam `.env` + `src/config/configuration.py`. P1, P3 e P4 chamam `load_dotenv()`; **P2 não chama** — depende do ambiente já carregado.

| Projeto | Arquivo | Banco em dev |
|---|---|---|
| P1 | `.env` | SQLite (`banco_de_dados/TABELAS_DETRAF.db`) |
| P2 | `.env` | SQLite (`banco de dados/TABELAS_DETRAF.db`) |
| P3 | `.env` | SQLite (`banco de dados/TABELAS_DETRAF.db`) |
| P4 | `.env.example` | SQLite (caminho por env, vazio = padrão) |

Note que P2 e P3 usam `banco de dados/` **com espaços**; P1 usa `banco_de_dados/`.

### 4.1 🔴 Segurança

| Item | Situação |
|---|---|
| Senha de banco real nos `.env` | **Sim, em P2 e P3** (16 caracteres, MySQL de produção) |
| Commitada no repositório | **Não** — `/projetos-origem` está no `.gitignore` |
| Caminho absoluto da máquina do desenvolvedor | **Sim** — ver abaixo |

**Não é vazamento de repositório**, porque o `.gitignore` cobre `projetos-origem/`. Mas duas consequências práticas:

1. O código unificado **não pode** herdar esse padrão — credencial só por variável de ambiente, com `.env.example` sem valores.
2. P1 e P4 já entregam `.env` sem senha (P4 inclusive como `.env.example`). É o padrão a adotar.

**Caminhos absolutos embutidos:**
- `projeto-2/src/models/repository/repositorio_cache.py:82`
- `projeto-2/src/utils/geradores_tabelas_homo.py` — linhas 94, 102, 111, 120, 128

Todos apontam para `C:\Users\btime\Desktop\Projetos\detraf 2 - ...`. Não funcionam em outra máquina.

---

## 5. Escopo aparente

| Verificação | Resultado |
|---|---|
| Cobre as HUs esperadas | P1 ✅ · P2 ✅ · P3 ✅ · P4 ⚠️ (services sim, orquestração não) |
| Código de outro épico | Não |
| **Código do fluxo de Receita** (fora deste MVP) | **Não** — nada encontrado |
| Código morto / utilitário de bancada | P2: `src/utils/geradores_tabelas_homo.py` (gerador de massa de homologação, com caminhos absolutos e blocos comentados) |

### 5.1 🔴 Verificação específica do P4 — onde está o Épico 5

Conforme §7.1 do checklist:

| Procurado | Encontrado? |
|---|---|
| Automação de UI para `Detraf > Importar Dados` | **Não** |
| Automação de UI para `Contestação > Gerenciar` | **Não** |
| Escrita no campo `carga_agi` | **Não** |

**Conclusão: o Épico 5 não está no P4.** O P4 não tem nenhuma automação de interface — nem `pyautogui`, nem `pywinauto`, nem Selenium. Ele para na geração dos arquivos.

Isso elimina a hipótese 1 registrada em [`projeto-7-epico-5-carga-agi/README.md`](../../projetos-origem/projeto-7-epico-5-carga-agi/README.md). Restam:
- **hipótese 2** — existe um sétimo projeto ainda não entregue;
- **hipótese 3** — HU-17/HU-18 não foram implementadas.

**A pasta `projeto-7-epico-5-carga-agi/` permanece reservada.** Atualiza a pergunta **Q3** de `duvidas-pendentes.md`.

---

## 6. Impedimentos de ambiente

| Item | Situação |
|---|---|
| Banco de teste | ✅ SQLite local em cada projeto (`TABELAS_DETRAF.db`) |
| Massa de dados | ✅ P4 tem fixtures reais (`tests/fixtures/detraf/`, `expectativa/`) |
| Ambiente de teste do AGI | ⚠️ **não se aplica ainda** — nenhum dos quatro projetos toca o AGI |
| Caixa de e-mail de teste | ⚠️ **necessário** — P1 lê e P2 responde e-mails via Outlook COM |
| Contador de numeração CT | ⚠️ **necessário** para o P4 (HU-14) |
| Acesso às pastas de rede Lagoa | ⚠️ desconhecido — os `.env` apontam para pastas locais em dev |

O impedimento do AGI, levantado na etapa anterior, **ainda não bloqueia**: ele só aparece quando P6 e o Épico 5 chegarem.

---

## 7. Veredicto

| Projeto | Pronto para análise |
|---|---|
| P1 | ✅ |
| P2 | ✅ |
| P3 | ✅ |
| P4 | ✅ (com a lacuna de orquestração registrada) |

**Pendências de entrega a solicitar:**
1. Declaração de dependências dos quatro projetos
2. A pasta `AI/` e o `TODO/` do P4 (contêm decisões D-1 a D-21 já tomadas)
3. Confirmação sobre o Épico 5 — existe um sétimo projeto?
