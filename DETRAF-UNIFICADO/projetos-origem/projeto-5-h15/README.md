# HU-15 - Envio do e-mail de contestação à operadora

Pacote isolado para a HU-15 (Épico 4 - Geração de Arquivos para Contestação e Carga AGI),
montado seguindo a mesma estrutura dos pacotes anteriores (Épico 5, HU-20, HU-21), agora
reaproveitando o módulo `outlook_standalone.py` fornecido.

Legenda: ✅ Pronto (reaproveitado)  |  🔄 Adaptado  |  🆕 A criar/confirmar

## Critérios de aceite x status

| Critério | Status |
|---|---|
| Destinatários da tabela de contatos do WebFat | 🆕 A confirmar (tabela/coluna real não mapeada) |
| Assunto: CONTESTAÇÃO_TBRA\|{operadora}_{mês} | ✅ Pronto (`_montar_assunto`) |
| Anexos: carta de contestação + arquivo _ENV | 🔄 Adaptado (localização de arquivo pronta; upstream que gera os arquivos é de outra etapa) |
| Disparo automático após sinalização do analista — sem aprovação manual | 🆕 A criar (gatilho de banco ainda não mapeado) |

## ✅ / 🔄 O que veio do `outlook_standalone.py` fornecido

- **`outlook_standalone_original.py`** — é o arquivo que você enviou, copiado **sem
  nenhuma alteração**. Toda a conexão COM com o Outlook (`OutlookService`), configuração
  (`OutlookConfig`), tratamento de erro (`OutlookError`) e utilitários (filtro de e-mail,
  organização de arquivos) continuam exatamente como estavam.
- **Única adaptação**: o método `OutlookService.send_email()` original só aceita
  `to/subject/body/cc` — **sem anexos**. Como a HU-15 exige 2 anexos obrigatórios (carta +
  `_ENV`), criei `outlook_standalone_com_anexo.py` com a classe `OutlookServiceComAnexo`,
  que **herda** de `OutlookService` (não copia nem reescreve o arquivo original) e adiciona
  só o método novo `send_email_com_anexos()` — mesma lógica do `send_email` original, com
  `mail.Attachments.Add(caminho)` para cada anexo antes de `mail.Send()`.
- `conexao.py`, `utils.py`, `requirements.txt` (já inclui `pywin32`, usado pelo
  `outlook_standalone.py`) — copiados sem alteração do projeto principal.
- O **padrão de kill-switch** (`PERMITIR_ENVIO_EMAIL`) segue a mesma convenção usada em
  todos os outros pacotes (`PERMITIR_UPLOAD_AGI`, `PERMITIR_ACAO_AGI`): dá pra rodar tudo
  em modo seguro (monta o e-mail em memória, mas não chama `Send()`) antes de operar de
  verdade.
- O **corpo do e-mail** já está com o texto exato do To Be MVP2 (parágrafos 278-283):
  *"Prezados, Segue a contestação para a sua análise e validação, referente ao mês
  {mês} ... Att,"*.

## 🆕 O que precisa ser confirmado/criado

1. **Tabela de contatos do WebFat** (`_buscar_destinatarios`): o To Be MVP2 menciona essa
   tabela (parágrafo 136) mas sem especificar nome/colunas. O exemplo de Receita
   (`Criacao_Remessa._tratativa_remessa`) busca e-mail responsável via `tbl_carteirizacao`
   — usei essa consulta como **inspiração de padrão** (mesmo jeito de fazer
   `db.selecionar_dados(sql, params)`), mas a query em si está comentada como esqueleto:
   falta confirmar o nome real da tabela de **contatos da operadora** (provavelmente
   diferente de `tbl_carteirizacao`, que é carteirização interna, não contato externo).
2. **Gatilho "sinalização do analista"** (`_buscar_contestacoes_sinalizadas`): é a condição
   que substitui a aprovação manual — precisa ser uma coluna/flag no banco que o WebFat
   grava quando o analista escolhe "com retenção" ou "sem retenção". Essa tabela/coluna
   ainda não existe mapeada neste pacote; sem ela, o robô não tem como saber quando disparar.
3. **Localização dos 2 anexos** (`_localizar_arquivos_contestacao`): esqueleto por
   convenção de nome de arquivo (contém operadora + mês, termina em `_ENV`, carta é
   `.doc/.docx/.pdf`) — **confirmar o padrão de nome real** gerado pelas etapas anteriores
   do Épico 4 (HU-14, geração do arquivo `_ENV` e carta).
4. Gravação do resultado do envio (`_marcar_email_enviado`) — mesma pendência de tabela de
   log específica da Despesa já registrada nos pacotes anteriores.

## Nenhuma imagem necessária

Diferente dos pacotes anteriores (Épico 5, HU-20, HU-21), esta HU **não usa automação por
imagem/pyautogui** — é 100% integração via Outlook COM (API do próprio Outlook), então não
há nada para capturar em `src/view/imagens/`.

## Checklist antes de rodar

1. Confirmar a tabela de contatos da operadora e ajustar `_buscar_destinatarios`.
2. Confirmar a tabela/coluna que registra a sinalização do analista e ajustar
   `_buscar_contestacoes_sinalizadas`.
3. Confirmar o padrão de nome de arquivo da carta/`_ENV` gerado nas HUs anteriores.
4. Copiar `.env.example` para `.env` e ajustar `OUTLOOK_ACCOUNT` e os caminhos.
5. Rodar primeiro com `PERMITIR_ENVIO_EMAIL=False` para conferir destinatário/assunto/corpo/
   anexos montados, antes de liberar o envio real.
