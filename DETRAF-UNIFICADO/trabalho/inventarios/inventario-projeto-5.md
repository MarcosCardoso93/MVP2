# Inventário — Projeto 5: HU-15 (Envio do E-mail de Contestação)

- **Pasta:** `projetos-origem/projeto-5-h15/`
- **HU:** HU-15 (Épico 4)
- **RPA de destino:** RPA 3
- **Recebido em:** 2026-08-04

---

## 1. Estrutura e execução

```
main.py                                    4 linhas
src/
├── config/     config.py (60) · conexao.py (160)
├── main/       process_handle.py (15)
├── services/
│   ├── Contestacao/  Envio_Email_Contestacao.py (203)
│   └── Outlook/      outlook_standalone_original.py (1191)
│                     outlook_standalone_com_anexo.py (59)
└── utils/      utils.py (24)
```

**Total: 1.716 linhas — mas 1.191 delas (69%) são o RPA 1 replicado.** Ver §3.

| Item | Valor |
|---|---|
| Ponto de entrada | `main.py` → `process_handle.run()` → `Envio_Email_Contestacao.Fluxo_Envio_Email_Contestacao()` |
| Testes | **nenhum** |
| Kill-switch | ✅ `PERMITIR_ENVIO_EMAIL`, default seguro |

---

## 2. 🔴 Arquitetura diferente da dos Projetos 1 a 4

O P5 foi montado a partir do **`RPA_DETRAF_RECEITA`** (MVP1 de Receita), não do
esqueleto que P1–P4 compartilham.

| | P1–P4 | P5 |
|---|---|---|
| Configuração | `configuration.py` | `config.py` |
| Banco | SQLAlchemy + repositório | `conexao.py`, mysql-connector, SQL cru |
| Log | `loguru` via `comum` | `print()` |
| Pastas | `services/` minúsculo | `services/Contestacao/`, `services/Outlook/` |
| Nomes de classe | `PascalCase` | `Envio_Email_Contestacao` (snake com maiúsculas) |

---

## 3. 🔴 O `outlook_standalone_original.py` é o RPA 1 replicado

1.191 linhas contendo `Attachment`, `EmailMessage`, `OutlookConfig`,
`_sanitize_filename`, `_safe_dir_name`, `_to_datetime`, `OutlookError`,
`OutlookService`, `EmailFilterService` e `FileOrganizerService` — ou seja, o
Projeto 1 inteiro achatado num arquivo.

**Mas as duas versões divergiram**, e cada uma tem algo que a outra não tem:

| Método | P5 standalone | RPA 1 unificado |
|---|---|---|
| `send_email` | ✅ | ❌ **falta** |
| `fetch_emails` + `fetch_emails_from_subfolder` | ✅ (inbox-cêntrico) | — |
| `fetch_emails_from_folder` | — | ✅ (pasta nomeada — **modelo da V2**) |
| `move_to_folder` + `move_back_to_inbox` | ✅ | — |
| `move_to_subfolder` | — | ✅ |
| `_listar_contas_disponiveis` | ❌ | ✅ (diagnóstico) |

O P5 traz justamente a peça que faltava (`send_email`), sobre a base **mais
antiga**: a navegação por inbox é a regra anterior; a V2 exige a pasta
"Detraf Despesas".

**Decisão (2026-08-04):** promover a camada para `comum/integracoes/`, com a base
do RPA 1 e o `send_email` do P5. O standalone não é migrado.

Isso fecha o candidato que estava **ADIADO** no catálogo desde a primeira
unificação, esperando exatamente o P5 como teste de confirmação — e a chegada
confirmou a hipótese: a abstração serve, mas precisava dos dois lados.

### `outlook_standalone_com_anexo.py` — o que é genuinamente novo

59 linhas. `OutlookServiceComAnexo` **herda** de `OutlookService` e acrescenta um
único método, `send_email_com_anexos()`: mesma lógica do `send_email`, com
`mail.Attachments.Add(caminho)` para cada anexo antes do `Send()`.

É a única contribuição de código nova da camada de Outlook do P5, e é a que a
HU-15 exige (carta + `_ENV`).

---

## 4. Mapeamento HU → código

| Critério de aceite (HU-15) | Status |
|---|---|
| Assunto `CONTESTAÇÃO_TBRA\|{operadora}_{mês}` | ✅ `_montar_assunto` |
| Corpo com o texto da V2 | ✅ `CORPO_EMAIL_TEMPLATE` — texto exato |
| Anexos: carta + `_ENV` | ⚠️ `_localizar_arquivos_contestacao` — ver §5 |
| Destinatários da tabela de contatos do WebFat | ❌ **esqueleto** — devolve `[]` |
| Disparo automático após sinalização do analista | ❌ **esqueleto** — devolve `[]` |

**Na prática, o fluxo não executa:** `_buscar_contestacoes_sinalizadas()` devolve
lista vazia, então `Fluxo_Envio_Email_Contestacao` sempre sai no primeiro `if`.

---

## 5. ⚠️ Um TODO que já tem resposta

O código registra que o gatilho da sinalização do analista *"não existe hoje
nenhuma tabela/coluna mapeada"*. **Isso está desatualizado.**

Na rodada de decisões de 2026-07-31 confirmou-se que o gatilho é a coluna
`tipo_contestacao` de `tbl_rpa_log_detraf_despesa_contestacao`, gravada pelo
WebFat — e `comum/dados/repositorio_tabelas.py` **já tem**
`obter_tipo_contestacao()` lendo exatamente isso, com comparação
case-insensitive.

Na migração, o TODO é reescrito apontando para o método existente. Ligar de fato
é desenvolvimento, e fica fora desta rodada.

## 6. ⚠️ Caminho de arquivo plano, de novo

`_localizar_arquivos_contestacao` varre `DIRETORIO_CONTESTACOES` como **pasta
plana**, filtrando por nome. A estrutura real é
`{operadora}/{ano}/{aaaamm}/Contestações/`, e `comum/arquivos/estrutura_pastas.py`
já tem `caminho_contestacoes()`.

É a **terceira** ocorrência do mesmo problema — a primeira foi entre RPA 1 e
RPA 2 (`Detrafs Recebidos`), a segunda no P7 (`AGI/`). Reconciliar pelo helper
comum, como nas anteriores.

---

## 7. Camada de banco — `conexao.py`

160 linhas, `mysql-connector`, SQL cru. Métodos: `selecionar_dados`,
`_inserir_banco`, `_atualizar_banco`, `log`, e três resíduos da Receita —
`inserir_nota_cancelada`, `atualizar_envio`, `marcar_enviado_agi` (este aponta
para `tbl_encontro_contas`, que não pertence a este fluxo).

**Decisão:** migrar para `comum/dados/`. O `conexao.py` não é levado.

O nome de tabela que ele usa no `log()` —
`tbl_rpa_log_detraf_despesa_contestacao` — **já está** em `comum/dados/tabelas.py`
com o mesmo valor. A migração é direta.

---

## 8. Configuração e segredos

`config.py` expõe: `CONFIG_RPA`, `CONFIG_WEBFAT`, `DIRETORIO_CONTESTACOES`,
`DIRETORIO_TEMP`, `OUTLOOK_ACCOUNT`, `PERIODO`, `PERIODO_REF`,
`PERMITIR_ENVIO_EMAIL`, `SENHA_BD`, `USUARIO_BD`.

| Item | Situação |
|---|---|
| `.env` versionado | ✅ presente, mas **sem credencial preenchida** |
| `.env.example` | ✅ presente |
| Credencial no código | ✅ nenhuma — vem de variável de ambiente do Windows |

Melhor que P2/P3, que traziam a senha do MySQL preenchida.

---

## 9. Achados

### 🔴 Críticos
1. **1.191 linhas duplicando o RPA 1**, com divergência de comportamento (§3)
2. **O fluxo não executa** — os dois métodos de busca devolvem `[]`

### 🟡 Relevantes
3. TODO do gatilho **desatualizado** — a resposta já existe (§5)
4. Caminho de arquivo plano, ignorando a estrutura de pastas (§6)
5. `print()` em vez de logger, em todo o service
6. Camada de banco paralela, com resíduos da Receita (§7)
7. **Sem nenhum teste**
8. `root_folder="DETRAF-DESPESA-CONTESTACAO"` — TODO; para *envio* o `root_folder`
   é irrelevante (só afeta leitura)

### 🟢 Observações
- Kill-switch `PERMITIR_ENVIO_EMAIL` no padrão certo, alinhado com
  `NOTIFICAR_OPERADORA_ENVIAR` que já adotamos
- O corpo do e-mail traz o texto **exato** da V2
- A subclasse `OutlookServiceComAnexo` é enxuta e bem feita: herda em vez de
  copiar

---

## 10. Conclusão

**Escopo real:** o esqueleto está montado e as partes determinísticas (assunto,
corpo, anexação) estão prontas. As duas pontas que dependem do banco estão
vazias.

**Complexidade de migração:** **baixa para o código útil** — são ~200 linhas de
service. O grosso do trabalho é *descartar* as 1.191 linhas duplicadas e
reconciliar a camada de Outlook, que beneficia os três RPAs.
