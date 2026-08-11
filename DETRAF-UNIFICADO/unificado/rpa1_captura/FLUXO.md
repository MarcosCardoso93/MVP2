# RPA 1 — fluxo de execução

**Captura e validação dos arquivos das operadoras · HU-01, HU-04, HU-02, HU-03**

---

## O que este robô faz

**Gatilho:** chegada de e-mail na caixa de Detraf, a partir do dia
`DETRAF_DIA_LIBERACAO` (dia 5).

**Entrega:** os arquivos de Detraf **que passaram na validação**, salvos em
`{operadora}/{ano}/{aaaamm}/Detrafs Recebidos/`, prontos para o RPA 2. O que não
passa vai para a quarentena, e a operadora recebe a resposta com o motivo.

No banco, este robô registra **só o que o RPA 2 nunca vai ver**: o recusado e o
que ficou sem operadora. O arquivo válido é registrado pelo RPA 2 — ver 2.8.

```
 Caixa "Detraf Despesas"
         │
         ▼
 ┌─────────────────┐   anexos em DIRETORIO_ENTRADA/{entry_id}/
 │ 1. CAPTURA      │   + vínculo arquivo→remetente no rastreamento
 │    HU-01        │   + e-mail movido para PROCESSADOS
 └────────┬────────┘
          │
          ▼
 ┌─────────────────┐          ┌──────────────────────────────────┐
 │ 2. PROCESSAMENTO│─reprovou→│ _QUARENTENA/{aaaamm}/{entry_id}/ │
 │    HU-02, HU-03 │          │ + _RECUSADO.md                   │
 │    HU-04        │          │ + resposta à operadora (HU-04)   │
 └────────┬────────┘          │ + log "Não validado"             │
          │ passou            └──────────────────────────────────┘
          ▼                              (beco sem saída)
 {operadora}/{ano}/{aaaamm}/Detrafs Recebidos/
          │
          ▼
      RPA 2
```

> **Mudou em 2026-08-06.** Antes, este robô copiava o arquivo sem olhar o
> conteúdo, e quem validava e respondia à operadora era o **RPA 2** — uma
> execução depois, com o arquivo ruim já dentro da árvore. Agora o portão é
> aqui. O RPA 2 continua validando, como rede de segurança, mas não responde
> mais e-mail.

---

# Etapa 1 — `captura` (HU-01)

`OutlookController.capturar_arquivos`

### 1.1 Guarda da data de corte

**Onde:** `outlook_controller.deve_processar_hoje`

Antes do dia `DETRAF_DIA_LIBERACAO` (5), a captura **não roda** — devolve lista
vazia e registra no log.

> A V1 dizia *"varredura diária após o dia 05"*; a V2 removeu a regra e não pôs
> nada no lugar. O dia 5 é decisão do GP/dev de 2026-08-05, configurável.

### 1.2 Ler a pasta `Detraf Despesas`

**Onde:** `comum/integracoes/outlook.py::fetch_emails_from_folder`
**Sai:** lista de e-mails, ordenados por data de recebimento

**Como falha:** sem Outlook Desktop Classic aberto e com perfil, levanta
`OutlookError` nomeando `OUTLOOK_ACCOUNT`. O "Novo Outlook" do Windows 11 **não
expõe COM** e não serve.

### 1.3 Filtrar o que interessa

**Onde:** `services/email_filter_service.py::deve_processar`

Passa o e-mail que **não** contém "CONTESTAÇÃO" no assunto **e** tem anexo
`.csv`/Excel. O resto é ignorado, com o motivo em `DEBUG`.

### 1.4 Descartar e-mail já capturado

**Onde:** `rastreamento.existe_entry_id`

O `entry_id` do Outlook é a chave. É a primeira das duas proteções contra
recaptura — a segunda é mover o e-mail (1.6).

### 1.5 Baixar os anexos e registrar o rastreamento

**Onde:** `outlook.download_attachments`
**Sai:** arquivos em `DIRETORIO_ENTRADA/{entry_id}/`, e um registro
`caminho → entry_id + remetente` no `RastreamentoRepository`

⚠️ **O rastreamento é o acoplamento real entre o RPA 1 e o RPA 2**, e não está
descrito na V2. É por ele que o RPA 2 sabe a quem responder quando um arquivo é
inválido. Os dois robôs precisam apontar para o **mesmo**
`RASTREAMENTO_ARQUIVO_PATH`; se o RPA 2 não o encontrar, ele registra "nenhum
e-mail de origem encontrado" e **nenhuma operadora é notificada** — sem erro
visível.

**Como falha:** falha de download conta no resumo e **não interrompe** os demais
e-mails.

### 1.6 Mover o e-mail para `PROCESSADOS`

**Onde:** `outlook.move_to_subfolder`

**Como falha:** o e-mail foi capturado mas não movido — vira `ERROR` no log e
entra no resumo. Não perde dado: o `entry_id` já está rastreado (1.4), então a
próxima execução o ignora de qualquer forma.

---

# Etapa 2 — `processamento` (HU-04, HU-02 e HU-03)

`ProcessamentoService.executar`, um arquivo de cada vez, com **erro isolado**:
falha num arquivo não interrompe os outros.

### 2.1 Montar a lista de trabalho

Quando a etapa roda **junto** com a captura, a lista vem dela pronta.

Quando roda **sozinha**, é reconstruída do disco —
`ProcessamentoService._varrer_pasta_de_entrada`:

- **busca recursiva**, porque a captura grava em subpasta por e-mail;
- **o remetente vem do rastreamento**, para não perder o fallback de
  identificação.

É o que faz a execução dividida dar o mesmo resultado da execução única.

### 2.2 Resolver a competência

**Onde:** `services/competencia_service.py`

O robô processa sempre o **mês anterior** à competência. `--referencia 202507`
faz a conta sozinho.

### 2.3 Validar o arquivo (HU-04)

**Onde:** `processamento_service._ler` e `._validar`
**Sai:** aprovado, ou um `Diagnostico` com os motivos

Uma leitura só do arquivo (`carregar_dados`), reaproveitada pelas duas camadas:

1. **layout** — `comum/dominio/layout_detraf.py::validar_layout`. Responde *"este
   arquivo não é o que eu esperava"*: 15 colunas, EOT numérica, AAAAMM,
   descritor, GH, números. Amostra 200 linhas e só reprova a posição quando a
   **maioria** falha — assim distingue "layout trocado" de "linha ruim";
2. **regras de coluna** — `comum/dominio/validacao_colunas.py::ValidadorColunas`.
   Responde *"é um Detraf, mas com valor fora da regra"*: referência do mês, EOT
   no Anexo 5, EOT da Vivo na devedora, tarifa contra a tabela regulada.

É **a mesma classe** que o RPA 2 usa — se cada robô tivesse a sua, os dois
portões divergiriam em silêncio.

⚠️ **A validação vem ANTES da identificação da operadora, e a ordem é a decisão
que importa.** Um arquivo com layout quebrado costuma falhar também na leitura da
EOT; se a identificação viesse primeiro, ele cairia em `_NAO_IDENTIFICADOS` e
**ninguém seria notificado**. Validando antes, a resposta sai sempre — ela
depende só do `entry_id`, que veio do Outlook e não do conteúdo do arquivo.

#### Reprovado → `_reprovar`

Nesta ordem, e **nada é copiado para a árvore das operadoras**:

1. identificação da operadora em **melhor esforço**, só para o campo `empresa`
   do log. Falhar aqui não cancela nada;
2. cópia para `DIRETORIO_QUARENTENA/{aaaamm}/{entry_id}/`. A subpasta por e-mail
   existe porque duas operadoras que mandem `DETRAF.csv` no mesmo mês se
   sobrescreveriam;
3. `_RECUSADO.md` **ao lado da cópia** — o original está em `DIRETORIO_ENTRADA`,
   que é transitória e a captura repovoa;
4. linha no log com `tipo_registro = "DETRAF"` e `status = "Não validado"`. É um
   dos dois casos que só este robô conhece: o arquivo vai para a quarentena, fora
   da árvore que o RPA 2 varre, então sem este registro o lote `DETRAF_ERRO` do
   WebFat iria a zero e quem lê o relatório leria como *"melhorou"*;
5. a recusa fica **anotada** — a resposta sai no fim da execução, agrupada por
   e-mail de origem. Ver 2.4.

#### "Não consegui validar" ≠ "reprovado"

`ValidacaoIndisponivel` é levantada quando o banco não responde. O arquivo **fica
onde está**, entra na contagem de erros e é retentado na próxima execução.
Nenhuma operadora é notificada.

A distinção existe porque colapsá-la seria caro: uma queda do WebFat durante a
captura poria o lote inteiro em quarentena e responderia a **todas** as
operadoras dizendo que os arquivos delas estão errados — com
`NOTIFICAR_OPERADORA_ENVIAR` ligado, irreversível.

### 2.4 Responder à operadora (HU-04)

**Onde:** `services/notificacao_operadora.py` → `OutlookController.responder`

Responde ao e-mail de origem pelo `entry_id` — resolução exata, porque a captura
acabou de baixar aquele anexo. O corpo vem de
`CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO`, com os placeholders **`{arquivos}`**,
`{quantidade}`, `{assunto_original}`, `{remetente}` e `{data_recebimento}`.

⚠️ **Uma resposta por E-MAIL, não por arquivo.** Um e-mail pode trazer vários
anexos, e vários deles podem cair. Três mensagens sobre o mesmo envio fariam a
operadora agir só na primeira — e, com o envio ligado, um e-mail com dez anexos
viraria dez e-mails enviados.

Por isso a notificação roda **depois** do laço de processamento, em
`_notificar_reprovados`: antes do fim não se sabe quantos anexos daquele envio
foram recusados. O agrupamento é pelo `entry_id`; sem ele (pasta preparada à
mão), cada arquivo é o seu próprio grupo.

`{arquivos}` é a lista dos recusados, cada um com os seus motivos — numerada
quando há mais de um. Sem ela a operadora recebe *"seu arquivo está inválido"* e
não tem como corrigir nada.

| | |
|---|---|
| `NOTIFICAR_OPERADORA_ENVIAR=false` (default) | só cria o **rascunho** no Outlook |
| `NOTIFICAR_OPERADORA_ENVIAR=true` | **envia** |

🔴 **Não há limite de notificações por execução** (decisão de 2026-08-06). Se a
causa da reprovação for nossa — mês de referência errado, Anexo 5 desatualizado,
tabela de tarifas vencida — todas as operadoras recebem um e-mail indevido de uma
vez. Com a chave em `false`, tudo para no rascunho.

**Sem template configurado**, o arquivo vai para a quarentena do mesmo jeito e o
erro fica no log. A falta de template nunca impede a recusa; só impede o aviso.

### 2.5 Identificar a operadora (HU-02)

**Onde:** `services/operadora_service.py::obter_operadora`
**Sai:** nome-fantasia + a origem da identificação (`eot` ou `dominio`)

1. **EOT credora lida dentro do arquivo** → `Nome Fantasia` no Anexo 5. É o
   caminho principal, e o que a V2 define;
2. **domínio do remetente** → só se a EOT não resolver.

**Não identificada** → o arquivo vai para `DIRETORIO_NAO_IDENTIFICADOS/{aaaamm}/`
e **não entra na tabela de log** (ele não foi salvo na estrutura definitiva).

⚠️ Essa pasta fica **fora** da raiz das operadoras de propósito: o RPA 2 varre
aquela raiz tratando **todo diretório como uma operadora**, e a de exceção
entraria na varredura como se fosse uma.

> **EOT que não existe no Anexo 5** cai aqui. Ficou assim por decisão de
> 2026-08-06 (pendência Q16b).

### 2.6 Garantir a estrutura do mês

**Onde:** `repositorio.clonar_estrutura_mes_anterior`

Se a pasta do mês não existe, ela é **clonada do mês anterior** — é o que carrega
as quatro subpastas (`Detrafs Recebidos`, `Detrafs Enviados`, `AGI`,
`Contestações`) sem recriá-las à mão.

### 2.7 Copiar o arquivo (HU-03)

**Onde:** `processamento_service._processar_arquivo`
**Sai:** `{operadora}/{ano}/{aaaamm}/Detrafs Recebidos/{nome original}`

⚠️ **A captura não TRANSFORMA o arquivo.** O que a operadora mandou é o que vai
para a pasta dela, byte a byte — e é o que permite reprocessar sem voltar ao
e-mail. O que mudou em 2026-08-06 é que ela **decide se o arquivo entra**: o
tratamento (limpeza de tráfegos, separação de linhas ruins) continua sendo do
RPA 2, mas a recusa é aqui.

### 2.8 Registrar na tabela de log — **só o que só este robô sabe**

**Onde:** `_registrar_log_despesa` → `tbl_rpa_log_detraf_despesa_arquivos`.

| Desfecho | Registra? | `tipo_registro` |
|---|---|---|
| Arquivo **válido**, salvo na árvore | **não** | — |
| Arquivo **recusado** na validação | sim | `DETRAF`, status "Não validado" |
| Operadora **não identificada** | sim | `ERRO`, status "Não validado" |

🔴 **O arquivo válido não é registrado aqui** (desde 2026-08-10). Era, e o RPA 2
registrava o mesmo arquivo de novo — duas linhas por Detraf válido, sem chave de
deduplicação, a daqui com seis campos zerados porque nesta etapa eles não são
conhecidos. Somar valores não denunciava (a linha daqui era zero); contar
arquivos no WebFat dava o dobro. Quem registra o válido é o RPA 2, que apurou.

Os outros dois continuam aqui porque **vão para fora da árvore que o RPA 2
varre** — quarentena e `_NAO_IDENTIFICADOS`. Sem este registro, eles sumiriam do
WebFat: o arquivo chegou e o analista não ficaria sabendo. O da operadora não
identificada é novo na mesma data; antes ele não era registrado em lugar nenhum.

### 2.9 Resumo

Sucessos, **reprovados**, não identificados e erros, com o nome de cada arquivo.

Os quatro são contados separadamente de propósito: têm causas e ações
diferentes, e somá-los esconderia justamente o que a validação passou a fazer.

---

## Rodando cada etapa

```bash
python main.py                              # as duas, como na agenda
python main.py --etapa captura              # só baixa os anexos
python main.py --etapa processamento        # reprocessa o que já baixou
python main.py --pasta-entrada C:\temp\x    # processa uma pasta, sem Outlook
python main.py --referencia 202507 --dry-run
```

`--pasta-entrada` **implica** `--etapa processamento`.

**Por que a divisão é útil:** capturar consome e-mail — depois de movido para
`PROCESSADOS`, ele não volta. Com as etapas separadas dá para capturar **uma
vez** e reprocessar quantas vezes for preciso.

### Parar entre as etapas para conferir

```bash
python main.py --pausar --dry-run
```

Ao fim de cada etapa abre uma caixa com o que ela produziu, e a execução só
segue no **Continuar**. Há também **Cancelar** (aborta, com código de saída 2) e
**Abrir pasta**.

🔴 Só funciona com `ENV=dev`, em sessão gráfica, e **nunca** em produção — a
caixa espera indefinidamente, e num robô desassistido isso travaria o processo.
Ver [`../../docs/03-checklists/homologacao-guia-de-partida.md`](../../docs/03-checklists/homologacao-guia-de-partida.md).

---

## O que parece defeito e não é

| O que acontece | Por quê |
|---|---|
| Nada foi capturado, e o robô terminou bem | Antes do dia 5 a captura não roda (1.1) |
| E-mail ignorado sem aviso claro | Não passou no filtro (1.3). O motivo está em `DEBUG` — use `--log-nivel DEBUG` |
| Segunda execução não captura nada | O `entry_id` já está rastreado e o e-mail já está em `PROCESSADOS`. É a proteção contra recaptura |
| Arquivo em `_QUARENTENA` | Reprovado na validação (2.3). O `_RECUSADO.md` ao lado diz o motivo |
| Arquivo em `_NAO_IDENTIFICADOS` | EOT não reconhecida e domínio sem correspondência (2.5). **Ficou raro**: um arquivo que passa na validação tem a EOT no Anexo 5, e é justamente lá que a identificação procura |
| Reprovado sem a operadora ser notificada | Falta `CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO`, ou a execução é `--pasta-entrada` (sem e-mail de origem). O arquivo continua em quarentena |
| Contado como erro, e não como reprovado | `ValidacaoIndisponivel` — o banco não respondeu. O arquivo fica na entrada e será retentado (2.3) |
| A captura ficou mais lenta | Ela passou a ler o arquivo **inteiro** para validar; antes lia duas linhas |
| `--etapa processamento` não achou nada | A captura grava em subpasta; confira se `DIRETORIO_ENTRADA` é a mesma das duas execuções |
| Operadora identificada "por domínio" | A EOT dentro do arquivo não resolveu — vale conferir o arquivo |

---

## Ver também

- [`../../docs/03-checklists/homologacao-rpa1-e-rpa2.md`](../../docs/03-checklists/homologacao-rpa1-e-rpa2.md) — roteiro de homologação
- [`../../docs/01-entendimento/responsabilidades-dos-rpas.md`](../../docs/01-entendimento/responsabilidades-dos-rpas.md) — por que o corte é este
