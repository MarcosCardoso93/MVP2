# Registro de Duplicações — P1 a P4

> Consolidado num documento em vez de um arquivo por par: os pares se referenciam entre si (a mesma família de arquivos aparece em três projetos), e separá-los tornaria a leitura pior. Segue [`criterios-de-unificacao.md`](../../docs/02-planejamento/criterios-de-unificacao.md); veredictos e sub-classificações são os de lá.

**Nota metodológica:** a primeira comparação por hash foi enganada por fim de linha — P3 usa **LF**, os demais **CRLF**. Todos os veredictos abaixo usam hash **normalizado** (`tr -d '\r'`).

---

## Sumário

| # | Responsabilidade | Ocorrências | Veredicto |
|---|---|---|---|
| D-01 | `utils/utils.py` | P2, P3, P4 | **IDÊNTICO** |
| D-02 | `utils/decoradores.py` | P2, P3, P4 | **IDÊNTICO** |
| D-03 | `utils/historico_arquivos.py` | P2, P3, P4 | **IDÊNTICO** |
| D-04 | `config/logger_config.py` | P1, P2, P3, P4 | **EQUIVALENTE-PARAMETRIZÁVEL** |
| D-05 | `utils/gerenciador_arquivos.py` | P2, P3, P4 | **IDÊNTICO** (núcleo) + união |
| D-06 | `models/repository/repositorio_cache.py` | P1, P2, P3, P4 | **EQUIVALENTE-PARAMETRIZÁVEL** |
| D-07 | Normalização de EOT | P1, P2, P3, P4 | **DIVERGENTE-DEFEITO** (P1) |
| D-08 | Consulta ao Anexo 5 | P1, P2, P3, P4 | **EQUIVALENTE-PARAMETRIZÁVEL** |
| D-09 | Validação de tarifa | P2, P3 | **IDÊNTICO** |
| D-10 | Classificação de descritor | P2, P4 | **EQUIVALENTE-PARAMETRIZÁVEL** |
| D-11 | Escrita do log de despesa | P1, P2, P3 | **EQUIVALENTE-PARAMETRIZÁVEL** |
| D-12 | **Consolidação Detraf × expectativa** | P3, P4 | 🔴 **DIVERGENTE-INTERPRETAÇÃO** |
| D-13 | **Regra de variação / flag S-N** | P3, P4 | 🔴 **DIVERGENTE-INTERPRETAÇÃO** |
| D-14 | Índices de coluna do layout Detraf | P2, P3, P4 | 🔴 **DIVERGENTE-DEFEITO** |
| D-15 | Contrato de `tbl_..._contestacao` | P3, P4 | 🔴 **DIVERGENTE-DEFEITO** |
| D-16 | Resposta por e-mail à operadora | P1, P2 | **FALSO PAR** |
| D-17 | Cálculo do mês de referência | P1, P2, P3, P4 | **EQUIVALENTE-PARAMETRIZÁVEL** |
| D-18 | Construção de caminho de saída | P1, P4 | **EQUIVALENTE-PARAMETRIZÁVEL** |

---

## D-01 · D-02 · D-03 — `utils.py`, `decoradores.py`, `historico_arquivos.py`

**Ocorrências:** P2, P3, P4 — mesma responsabilidade, mesmo caminho.

**Comparação:** hash normalizado **idêntico nos três**. Zero deriva.

**Veredicto: IDÊNTICO.** → Unificar. Base: qualquer uma (uso P2, CRLF como os demais).

---

## D-04 — `config/logger_config.py`

**Ocorrências:** P1, P2, P3, P4. P2 e P4 idênticos; P1 e P3 divergem.

**Diferenças:**

| | P1 | P2/P4 | P3 |
|---|---|---|---|
| Nível de log | `DEBUG` | `INFO` | `INFO` |
| `opt(depth=)` em info/debug/warning/critical | **1** | 2 | 2 |
| `opt(depth=)` em error | 1 | 1 | 1 |
| Suporte a `%`-args | não | não | **sim** (`_formatar`) |

**Análise:** P3 é **superset** — `_formatar(message, args)` devolve a mensagem intacta quando não há args, então aceita todas as chamadas de P1/P2/P4. E o P3 já usa `%`-args (`logger.warning("...'%s'.", operadora)`), que nos outros sairia literal.

O `depth=1` do P1 é **defeito**: faz o log reportar `logger_config.py` como origem em vez do código chamador. O `depth=1` em `error`, presente nos quatro, é a mesma inconsistência.

**Veredicto: EQUIVALENTE-PARAMETRIZÁVEL.** → Unificar sobre a versão do **P3**, com o nível por variável de ambiente (`LOG_LEVEL`, default `INFO`).

**Alterações intencionais registradas:**
- P1 passa de `DEBUG` para `INFO` por default → configurável
- `depth` uniformizado em 2 (inclui corrigir `error` nos quatro) → muda a atribuição de origem nos logs, não o comportamento funcional

---

## D-05 — `utils/gerenciador_arquivos.py`

**Ocorrências:** P2 (503), P3 (592), P4 (523).

**Comparação:** as **17 funções comuns são byte a byte idênticas** entre P2 e P4 (diff normalizado retorna apenas o bloco extra). Cada projeto acrescentou uma função:

| Projeto | Função exclusiva |
|---|---|
| P2 | `separar_e_salvar_por_mascara` — separa válidas/inválidas e grava o `_ERRO` |
| P3 | `exportar_dataframe_para_excel` |
| P4 | `salvar_planilhas` |

**Veredicto: IDÊNTICO no núcleo.** → Unificar como **união**: as 17 comuns + as 3 exclusivas. Nenhuma conflita.

**Bordas verificadas:** `carregar_dados` e `salvar_dados` são as mesmas nos três, então tratamento de separador, encoding, cabeçalho e `dtype` é comum. As fixtures do P4 exercitam vírgula/sem cabeçalho, ponto e vírgula/com cabeçalho e decimal com vírgula — a suíte do P4 protege a migração.

---

## D-06 — `repositorio_cache.py`

**Ocorrências:** P1 (225), P2 (257), P3 (303), P4 (360). Singleton que carrega tabelas de consulta em memória uma vez por execução.

**Diferença central — a lista de tabelas cacheadas:**

| Projeto | `TABELAS_CACHE` |
|---|---|
| P1 | `tbl_anexo5_processado`, `tbl_detraf_despesa_arquivos` |
| P2 | + `tbl_detraf_tarifas`, `tbl_detraf_mapeamento_descritores`, `tbl_anexo5` |
| P3 | `tbl_anexo5_processado`, `tbl_detraf_tarifas`, `tbl_detraf_mapeamento_descritores` |
| P4 | + `tbl_contestacao`, `tbl_mapeamento_descritores` |

**Veredicto: EQUIVALENTE-PARAMETRIZÁVEL.** A diferença é **dado** — a lista de tabelas. O corpo (singleton, engine SQLAlchemy, MySQL em prod / SQLite em dev, carga preguiçosa) é o mesmo.

→ Unificar com `TABELAS_CACHE` recebida por parâmetro. Cada RPA declara o seu conjunto.

**Alteração intencional obrigatória:** remover o caminho absoluto de `P2:82`.

---

## D-07 — Normalização de EOT

**Ocorrências:** P1 `operadora_service.py::_normalizar_eot` · P2/P3/P4 `repositorio_tabelas.py::_tratar_eot`.

P2, P3 e P4 são funcionalmente idênticos. P1 difere:

```python
# P1 — NÃO remove a parte decimal
if texto.isdigit(): return texto.zfill(3)

# P2/P3/P4
if "." in eot: eot = eot.split(".")[0]
if eot.isdigit() and int(eot) < 100: return eot.zfill(3)
```

**Borda que separa:** EOT lida de Excel como float → `"11.0"`. P1 devolve `"11.0"` (não casa com o Anexo 5); os demais devolvem `"011"`.

**Veredicto: DIVERGENTE-DEFEITO** (P1 incorreto). → Migrar a versão de P2/P3/P4. Alteração intencional registrada: no P1 isso muda o resultado nos casos em que hoje cai no fallback por domínio.

---

## D-08 — Consulta ao Anexo 5

**Ocorrências:** os quatro, em `repositorio_tabelas.py` (P1: `buscar_nome_fantasia`, `buscar_nome_fantasia_por_eot`; P2/P3: + `validar_eot`, `validar_regiao`, `obter_tipo_servico_por_eot`, `obter_concessao_por_eot`; P4: + `obter_endereco_por_eot`).

**Veredicto: EQUIVALENTE-PARAMETRIZÁVEL** — é uma família coesa sobre a mesma tabela. → Unificar em `comum/dados/anexo5.py` como união dos métodos.

⚠️ P2 consulta `tbl_anexo5` **e** `tbl_anexo5_processado`; os demais só a processada. Confirmar se são a mesma coisa em estágios diferentes.

---

## D-09 — Validação de tarifa

**Ocorrências:** P2 e P3, `repositorio_tabelas.py::validar_tarifas_na_tabela` + `buscar_dados_tarifa_linha`.

**Bordas verificadas — ambos tratam:** dupla convivência em fevereiro (filtro por `data_inicio`/`data_fim` com o **mês do tráfego**), `gh` nulo valendo para todos os grupos (inclusive a string literal `"NULL"` vinda do banco), e exceções por `eot_vivo`/`eot_operadora`.

**Veredicto: IDÊNTICO.** → ~~Unificar em `comum/dados/tarifas.py`~~ — **decisão revista:** o candidato 17 foi **rejeitado por C1** (só o RPA 2 valida tarifa). Fica em `rpa2_validacao_apuracao/`; `comum/dados/tarifas.py` não existe.

---

## D-10 — Classificação de descritor

**Ocorrências:** P2 `utils/classificadores.py` (`classificar_regra_inicio_fim_desc`, `classificar_descritor_remuneracao`) · P4 `services/mapa_remuneracao.py`.

**Diferença:** P4 desambigua pela coluna `produto` (decisão D-5) — o caractere final `T` mapeia tanto `TU-RIU` quanto `VU-T`. P2 e P3 não desambiguam; o P3 chega a registrar o aviso *"caractere final é ambíguo... usando a primeira ocorrência"*.

**Veredicto: EQUIVALENTE-PARAMETRIZÁVEL**, com o P4 mais completo. → Unificar sobre o **P4**, que resolve a ambiguidade.

**Alteração intencional:** onde P2/P3 pegavam a primeira ocorrência, passa a desambiguar por `produto`. Muda resultado nos descritores terminados em `T`.

---

## D-11 — Escrita do log de despesa

**Ocorrências:** P1, P2, P3 — `salvar_dados_tabela_despesa`.

**Divergência de nome de tabela:** os três usam `tbl_detraf_despesa_arquivos`; a V2 documenta `tbl_rpa_log_detraf_despesa_arquivos`.

**Veredicto: EQUIVALENTE-PARAMETRIZÁVEL.** → Unificar com o nome da tabela em constante única.

⚠️ **Qual nome vale — o do código ou o da V2 — é pergunta para o PO** (o banco real é a autoridade). ~~Adota-se o do código~~ — **decidido em 2026-07-31 (N1): vale o nome da V2**, `tbl_rpa_log_detraf_despesa_arquivos`. `preparar_banco_dev.py` renomeia a tabela do SQLite de origem.

---

## D-12 — 🔴 Consolidação Detraf × expectativa

**Ocorrências:** P3 `criacao_arquivo_contestacao.py` (HU-09) · P4 `consolidacao_contestacao.py` ("dependência D-2").

**São a mesma responsabilidade**: agrupar os dois lados por EOT × remuneração × mês de tráfego, calcular diferença e variação, marcar S/N.

O P4 reimplementou porque precisava da consolidação e o P3 é outro projeto. Duas implementações independentes da mesma HU.

**Diferenças de comportamento:**

| Aspecto | P3 | P4 |
|---|---|---|
| Dimensões | `Devedora, tipo_operacao, tipo_produto, Trafego, GH` | por EOT + remuneração + mês de tráfego |
| Origem da remuneração | POI (idx 4) 🔴 | descritor (idx 6) ✅ |
| `tipo_operacao` | Credora 🔴 | — |
| Layout da expectativa | mesmo índice da operadora 🔴 | índices parametrizáveis |
| Saída | banco **+ planilha** | apenas dados |

**Veredicto: DIVERGENTE-INTERPRETAÇÃO**, com defeitos de implementação no P3.

→ **Base: P4**, por resolver descritor e permitir override de índice. A geração da planilha `Base_Contestação` (exclusiva do P3) é preservada — é insumo da HU-14.

**Encaminhar ao PO:** confirmação de que a `Base_Contestação` continua sendo gerada como arquivo (Q4).

---

## D-13 — 🔴 Regra de variação e flag S/N

**Ocorrências:** P3 `_aplicar_analise_contestacao` · P4 `consolidacao_contestacao.py::_variacao`.

**Bordas comparadas:**

| Borda | P3 | P4 |
|---|---|---|
| Base do percentual | expectativa (`RS_tbra`) | operadora |
| Sinal | com sinal | `abs()` |
| Par ausente | `NA` → `"N"` | 100% → `"S"` |
| Limiar | `>= 1.0` | `>= 0.01` (fração) |
| Divisão por zero | `replace(0, NA)` | `np.where` com fallback |

**Veredicto: DIVERGENTE-INTERPRETAÇÃO.** As duas leram a mesma V2 e chegaram a comportamentos incompatíveis, porque o texto é ambíguo (Q2).

**Resolução (decidida pela documentação, conforme o plano aprovado):** híbrido — **base = operadora** (P4), **com sinal** (P3), **limiar `>=`** (ambos). Fundamentação em [`../../docs/04-relatorios/duvidas-pendentes.md`](../../docs/04-relatorios/duvidas-pendentes.md) Q2.

→ Implementar uma única vez em `comum/dominio/variacao.py`, com teste para as três bordas.

**Pendência residual ao PO:** `>` vs `>=` em exatamente 1%.

---

## D-14 — 🔴 Índices de coluna do layout Detraf

**Ocorrências:** P2 `validacao_colunas.py` (inline) · P3 `criacao_arquivo_contestacao.py` (inline) · P4 `constantes_epico4.py` (constantes nomeadas).

**Confronto com a V2 e com as fixtures reais:**

| Campo | V2 | ALGAR real | P2 | P3 | P4 |
|---|---|---|---|---|---|
| Rel | idx 5 | 5 | **5 ✅** | — | **4 🔴** |
| DESC | idx 6 | 6 | — | **4 🔴** (usa POI) | **6 ✅** |
| GH | idx 7 | 7 | 7 ✅ | 7 ✅ | 7 ✅ |
| Minutos | idx 9 | 9 | 9 ✅ | 9 ✅ | 9 ✅ |
| R$_Bruto | idx 14 | 14 | 14 ✅ | 14 ✅ | 14 ✅ |

**Veredicto: DIVERGENTE-DEFEITO** — dois defeitos independentes: `COL_REL = 4` no P4 e o uso do POI como descritor no P3. O P2 está correto.

→ Base comum com constantes nomeadas (modelo do P4), **com `COL_REL = 5`**, e override por parâmetro.

⚠️ **Separado disto**, o layout da **expectativa Vivo é genuinamente outro** (ver inventário do P3 §4) — precisa de perfil próprio, não de override pontual.

---

## D-15 — 🔴 Contrato de `tbl_rpa_log_detraf_despesa_contestacao`

**Ocorrências:** P3 escreve (16 colunas) · P4 lê e atualiza (chave de 5 colunas).

**A chave do P4 inclui `remuneracao`; o P3 não grava essa coluna.** O P4 não casa nenhuma linha escrita pelo P3.

**Veredicto: DIVERGENTE-DEFEITO.** → Definir o contrato da tabela num ponto único da base comum. O P3 tem a informação (`tipo_produto`) — passa a gravá-la como `remuneracao`.

**Alteração intencional:** o P3 passa a gravar uma coluna a mais.

---

## D-16 — Resposta por e-mail à operadora

**Ocorrências:** P1 `outlook_controller.py::responder_por_arquivo` · P2 `services/notificacao_email.py`.

**Veredicto: FALSO PAR.** Mesmo verbo, propósitos distintos: o P1 expõe um utilitário genérico de resposta (não é chamado no fluxo dele); o P2 implementa a crítica da HU-04, com template e regra própria.

→ Não unificar o comportamento. **Unificar apenas a camada de acesso ao Outlook** por baixo (D-08 do catálogo de candidatos). Renomear no destino para evitar a confusão.

---

## D-17 — Cálculo do mês de referência

**Ocorrências:** P1 `competencia_service.py` + `filesystem.mes_anterior` · P2/P3/P4 `configuration.ANO_MES_REFERENCIA`.

**Mesma regra** (mês corrente − 1, com override por env e virada de ano). Diferença de forma: o P1 devolve um `dataclass` com `ano` e `competencia`; os demais uma string.

**Veredicto: EQUIVALENTE-PARAMETRIZÁVEL.** → Unificar, expondo as duas formas.

⚠️ Nome da variável de override diverge: `COMPETENCIA` (P1) vs `DEBUG_ANO_MES_ATUAL` (P2/P3/P4). Padronizar e documentar no `.env.example`.

---

## D-18 — Construção de caminho de saída

**Ocorrências:** P1 `filesystem.construir_caminho_saida` · P4 `utils/estrutura_pastas.py`.

O P4 é mais completo: conhece as subpastas (`AGI`, `Contestações`, `Detrafs Recebidos`, `Detrafs Enviados`), todas por variável de ambiente. O P1 só monta `{raiz}/{operadora}/{ano}/{aaaamm}`.

**Veredicto: EQUIVALENTE-PARAMETRIZÁVEL.** → Base: **P4**; o caso do P1 é a mesma função sem subpasta.

**Fecha um vazio do P1:** a HU-03 exige salvar em `Detrafs Recebidos`, que hoje o P1 não acrescenta.

---

---

# Segunda leva — Projetos 5 e 7 (2026-08-04)

## D-19 — Camada de acesso ao Outlook

**Ocorrências:** P1 `outlook_service.py` + `outlook_config.py` · P2
`notificacao_email.py` (`win32com.client.Dispatch` inline) · P5
`outlook_standalone_original.py` (**1.191 linhas**).

O standalone do P5 é o Projeto 1 inteiro achatado num arquivo: `Attachment`,
`EmailMessage`, `OutlookConfig`, `OutlookError`, `OutlookService`,
`EmailFilterService`, `FileOrganizerService`. Mas as duas versões **divergiram**,
e cada uma tinha algo que a outra não tinha:

| Método | P5 standalone | P1 |
|---|---|---|
| `send_email` / `send_email_com_anexos` | ✅ | ❌ |
| `fetch_emails_from_folder` (pasta nomeada — **modelo da V2**) | ❌ | ✅ |
| `fetch_emails` (inbox-cêntrico — modelo antigo) | ✅ | ❌ |
| `_listar_contas_disponiveis` (diagnóstico) | ❌ | ✅ |

**Veredicto: DIVERGENTE (VERSÃO).** O P5 partiu de uma cópia mais antiga do P1 e
evoluiu em paralelo.

→ **Unificado** em `comum/integracoes/outlook.py`, com a **base do P1** — é a
aderente à V2, que exige a pasta "Detraf Despesas" — mais o `send_email` e o
`send_email_com_anexos` do P5. O standalone não foi migrado.

Foi a chegada do P5 que fechou o critério C1: o candidato estava **ADIADO** no
catálogo desde a primeira unificação, esperando exatamente a segunda ocorrência
de *envio*. Ver a ficha #08 em `candidatos-componentes.md`.

O `Dispatch` inline do P2 virou `OutlookService.responder_email`, que generaliza
o antigo `create_reply_draft` com o parâmetro `enviar`.

---

## D-20 — Camada de acesso ao banco

**Ocorrências:** P5 `src/config/conexao.py` (160 linhas) · P7 `src/config/conexao.py`
(160 linhas) · P1–P4 `comum/dados/repositorio_cache.py` + `repositorio_tabelas.py`.

Os dois `conexao.py` diferem em **duas linhas**: o rótulo do RPA no log e o nome
da tabela (`..._contestacao` no P5, `..._arquivos` no P7). Ambos usam
`mysql-connector` e SQL cru, herdados do `RPA_DETRAF_RECEITA`.

**Veredicto: DIVERGENTE (VERSÃO)** em relação à camada unificada — mesma
finalidade, arquitetura anterior.

→ **Não migrados.** P5 e P7 passam a usar `comum/dados/`. Os dois nomes de tabela
já estavam em `comum/dados/tabelas.py` com os mesmos valores, então a troca é
direta.

**Não migram junto:** `inserir_nota_cancelada`, `atualizar_envio` e
`marcar_enviado_agi` — resíduos da Receita. O último aponta para
`tbl_encontro_contas`, que não pertence a este fluxo.

---

## D-21 — Captura de evidência do upload

**Ocorrências:** P7 `Upload_Detraf_EXT_INT._capturar_evidencia_sucesso` ·
P7 `Upload_Contestacao._capturar_evidencia_sucesso`.

Idênticos, exceto pelo prefixo do nome do arquivo. Os dois eram esqueleto: criavam
a pasta e imprimiam um TODO, sem tirar o print.

**Veredicto: IDÊNTICO.**

→ Unificado em `upload_detraf_agi.capturar_evidencia_sucesso(nome, prefixo)`, que
a HU-18 importa. Fica no RPA 3 — não há ocorrência fora dele, falha C1.

---

## D-22 — Caminho de arquivo plano, ignorando a estrutura de pastas

**Ocorrências:** P5 `_localizar_arquivos_contestacao` (varre `DIRETORIO_CONTESTACOES`)
· P7 `_montar_lista_upload` (varre `data/AGI/EXT` e `data/AGI/INT`) · P7
`_listar_arquivos_contestacao`.

Todos varrem uma pasta **plana** e filtram por substring do nome. A estrutura real
é `{operadora}/{ano}/{aaaamm}/{subpasta}/`, e `comum/arquivos/estrutura_pastas.py`
já a conhece.

É a mesma classe de desvio já vista entre RPA 1 e RPA 2 (`Detrafs Recebidos`) na
primeira leva — agora com mais três ocorrências.

**Veredicto: DEFEITO.** Além de não achar os arquivos onde eles de fato estão,
perde a informação de **qual operadora** é cada arquivo — que é exatamente a chave
da regra de negócio que falta na HU-17.

→ Os três reescritos sobre `caminho_contestacoes()` / `caminho_agi()`.

---

---

# Terceira leva — Projeto 6 (2026-08-05)

## D-23 — `AGI_config.py`, terceira ocorrência — e o P6 trouxe correções

**Ocorrências:** P7 (286 linhas) · **P6** (286) · `rpa3/src/integracoes/agi.py`.

**283 das 286 linhas são idênticas** entre P6 e P7. A API pública é a mesma —
nenhuma função nova. Mas as três divergências são **melhorias**, de quem rodou
contra o AGI de produção:

| Ponto | P7 / unificado | P6 |
|---|---|---|
| Título do diálogo de download | literal em inglês | **regex bilíngue** — o idioma da VM varia |
| Reescrita do CSV pós-download | `open("w")` direto | `chmod` + **retry 5×** tratando `PermissionError` |

**Veredicto: DIVERGENTE (VERSÃO), com o P6 melhor nos dois pontos.**

→ As duas correções foram **portadas** para `agi.py`. O `_corrigir_aspas_impares`
unificado tinha exatamente o bug de permissão que o P6 aprendeu a contornar: logo
após o download, o antivírus ou o processo que salvou ainda seguram o arquivo, e o
`open("w")` estoura com `PermissionError` **transitório** — depois de o robô já ter
aberto o AGI, logado e baixado.

⚠️ **A promoção para `comum/` continua rejeitada.** O P6 era o teste de
confirmação, e o resultado é misto: a abstração serviu a um **terceiro** caso de
uso sem alteração de API, mas a **HU-21 não veio** — o AGI segue com um consumidor
só, e o critério C1 continua falhando. Gatilho de reavaliação: **quando a HU-21
chegar**.

---

## D-24 — `conexao.py`, `utils.py` e `config.py`, terceira ocorrência

**Ocorrências:** P5 · P7 · **P6**.

- `utils.py` — **diff vazio** contra o P7;
- `conexao.py` — difere do P7 em **duas linhas**: o rótulo do RPA e o nome da
  tabela (`tbl_rpa_log_detraf_despesa_verificacao`);
- `config.py` — replica `comum/config/configuration.py`.

**Veredicto: IDÊNTICO / DIVERGENTE (VERSÃO).** → Nenhum migrado, como nas duas
levas anteriores.

⚠️ Diferente do P5 e do P7, a tabela do `conexao.py` **não existe** em
`comum/dados/tabelas.py`, e o próprio comentário do P6 admite que o nome é
*sugerido, não confirmado*. Com a decisão de gravar o relatório de inconsistência
como `.xlsx` na pasta de logs, **a tabela não foi criada**.

---

## D-25 — Fonte do Encontro de Contas

**Ocorrências:** P6 `_ler_subtotal_despesa_ec` (planilha, célula `O87`) ·
`rpa3/src/services/encontro_contas.py` + `repositorio_tabelas` (banco).

Não é duplicação de código — é **conflito de fonte de verdade**. O P6 é o único
componente da leva que ainda lê `.xlsx`.

**Veredicto: DIVERGENTE (VERSÃO).** → Resolvido pelo cliente em 2026-08-05: **o EC
é banco**. Novo `obter_subtotal_despesa_por_operadora`; a célula `O87` não migra.

---

## Duplicações deliberadamente **não** unificadas

| Item | Motivo |
|---|---|
| `geradores_tabelas_homo.py` (P2) | Ferramenta de bancada, não produto. **Não migrar** |
| Mecanismo de fluxos `_BK`/`_LL` (P2) | Uma única ocorrência — falha o critério C1. Fica no RPA 2 |
| `separar_linhas_bk` / `separar_linhas_ll` | Idem |
| Regra do dia de liberação (P1) | Regra em pendência aberta (Q1) — falha C3. Fica no RPA 1 |
| Textos e assinatura da carta (P4) | Exclusivos do RPA 3 — falha C1 |
