# Responsabilidades dos Quatro RPAs

> ⚠️ **Fotografia da etapa documental (2026-07-30).** Este documento foi escrito
> **antes** de qualquer código chegar, e descreve o entendimento daquele momento.
> Vários pontos já mudaram — em especial: o Épico 5 **tem** projeto (o P7, entregue
> em 2026-08-04), e as HUs 12 a 19 estão implementadas e orquestradas.
>
> **Fonte do estado atual:** `docs/04-relatorios/duvidas-pendentes.md` (pendências),
> `matriz-de-rastreabilidade.md` (HUs) e `unificado/README.md` (código).

> Fonte: `Relatorio_Separacao_RPAs_Detraf_MVP2.docx`, ancorado na V2.

A V2 antecipa que "a automação será composta entre **3 e 4 RPA's**". O relatório de separação opta por **4**: os três primeiros cobrem o fluxo linear do processo e o quarto isola a exceção de retificação.

---

## Critério de corte: o gatilho

Os cortes **não** foram feitos por afinidade temática, e sim por **natureza do gatilho de execução**. Isso importa para a unificação: é o critério que decide onde cada pedaço de código pertence.

| RPA | Gatilho | Natureza |
|---|---|---|
| RPA 1 | Chegada de e-mail + janela até a data de corte | **Evento externo + espera** |
| RPA 2 | Após a data de corte, todos os arquivos recebidos | **Lote agendado** |
| RPA 3 | Sinalização do analista no WebFat | **Decisão humana** |
| RPA 4 | Identificação de tráfego recuperado no mês seguinte | **Condição de negócio assíncrona** |

Código que atravessa dois gatilhos é candidato à base compartilhada ou à cisão. Ver [`../02-planejamento/criterios-de-compartilhamento.md`](../02-planejamento/criterios-de-compartilhamento.md).

---

## RPA 1 — Captura de Arquivos das Operadoras

**Recebimento e organização dos arquivos de Detraf enviados por e-mail.**

**Gatilho.** Chegada de e-mail na caixa `detrafTBRA.br@telefonica.com`, dentro da janela de tempo definida até a data de corte do mês. ⚠️ A data de corte não está definida.

**Responsabilidades.**
1. Acessar a caixa de e-mail e localizar mensagens do mês de referência que **não** contenham a palavra "CONTESTAÇÃO"
2. Baixar apenas os anexos `.csv`/Excel
3. Organizar os e-mails na pasta "Detraf Despesas" do Outlook
4. Salvar os arquivos na pasta de rede da operadora/mês **e também no servidor do WebFat**
5. Identificar o nome da operadora pela **EOT da Credora no Anexo 5**
6. Sinalizar no WebFat como "não validado" quando a operadora enviar arquivos divergentes

**Entrega.** Arquivos de Detraf salvos na pasta de rede e replicados no servidor do WebFat, prontos para o RPA 2 processar.

**Por que foi separado.** Responde a um gatilho de evento e precisa **aguardar** uma janela de tempo antes que o processamento seguinte possa iniciar. Colocar esse comportamento de espera no mesmo robô que faz o processamento em lote faria o lote ficar bloqueado esperando e-mail, ou rodar de forma incompleta.

**HUs.** HU-01, HU-02, HU-03. **Projeto de origem:** P1 (único caso 1:1).

**Sistemas.** Outlook Desktop Classic, rede Lagoa, servidor WebFat, banco WebFat, Anexo 5.

---

## RPA 2 — Validação e Apuração de Contestação

**Comparação Detraf × expectativa e cálculo da necessidade de contestação.**

**Gatilho.** Execução em lote, disparada **após a data de corte** — quando todos os arquivos do mês já foram recebidos pelo RPA 1.

**Responsabilidades.**
1. Abrir os arquivos de "Detraf Recebidos" e da pasta de convertidos, filtrando pelos que contêm **`_D_`** no nome
2. Validar conforme as regras de layout e tarifa, gravando o resultado (`EXPECTATIVA` ou `ERRO`) em `tbl_rpa_log_detraf_despesa_arquivos`
3. Consolidar os dados da operadora com `tipo_registro = "DETRAF"`
4. Montar a base de contestação e os resumos por operadora, populando `tbl_rpa_log_detraf_despesa_contestacao`
5. Aplicar a regra de variação de 1% para decidir se o tráfego segue sem contestação ou precisa ser contestado
6. Gerar os arquivos `_BK` e `_ERRO` conforme as regras
7. Acionar a operadora por e-mail quando o erro for do arquivo dela

**Entrega.** Tabelas do WebFat atualizadas com o resultado da validação e a indicação de quais operadoras/remunerações precisam de contestação — **aguardando decisão do analista**.

**Por que foi separado.** Processa em lote e **termina num ponto de decisão humana**. Um robô que depende de decisão humana no meio do fluxo tem perfil de execução diferente de um robô 100% automático: precisa de um mecanismo de espera/consulta ao WebFat que não faz sentido misturar com a geração de carta e carga no AGI, que só devem rodar depois da decisão.

**HUs.** HU-04 a HU-11. **Projetos de origem:** **P2 + P3 convergem aqui.**

**Sistemas.** Rede Lagoa, banco WebFat (`tbl_detraf_tarifas`, `tbl_detraf_mapeamento_descritores`, `tbl_rpa_log_detraf_despesa_arquivos`, `tbl_rpa_log_detraf_despesa_contestacao`), Anexo 5, Outlook (envio de crítica à operadora).

⚠️ **Nota.** O RPA 2 também envia e-mail (crítica à operadora, HU-04), assim como o RPA 1 lê e-mail e o RPA 3 envia contestação (HU-15). A camada de e-mail toca três RPAs — forte candidata a componente compartilhado, mas isso depende da análise do código.

---

## RPA 3 — Contestação, Carga no AGI e Encontro de Contas

**Formalização da contestação e atualização dos sistemas financeiros.**

**Gatilho.** Sinalização do analista no WebFat, informando a decisão de contestação (com ou sem retenção) para a operadora/remuneração.

**Responsabilidades.**
1. Definir a **modalidade** da contestação (Referência ou Tráfego) e o **tipo** (com ou sem retenção)
2. Gerar o arquivo de tráfego da operadora (`_EXT`) e o arquivo interno de expectativa Vivo (`_INT`) para carga no AGI
3. Gerar o arquivo `_ENV`, a carta de contestação numerada e o e-mail para a operadora
4. Atualizar o campo `tipo_contestacao` em `tbl_rpa_log_detraf_despesa_contestacao`
5. Fazer a carga dos arquivos no AGI (Detraf e Contestação) e atualizar o campo `carga_agi`
6. Atualizar o Encontro de Contas (`minutos_operadora`, `vb_operadora`, `minutos_diferenca`, `vb_diferenca`, `minutos_variacao_perc`, `vb_variacao_perc`)
7. Gerar e conferir o Relatório de Receitas e Despesas

**Entrega.** Carta e e-mail enviados à operadora; arquivos carregados no AGI; Encontro de Contas e Relatório de Receitas e Despesas atualizados; tabela de contestação atualizada com `tipo_contestacao` e `carga_agi`.

**Por que foi separado.** É um fluxo sequencial e coeso — todos os passos dependem da decisão do analista e seguem em cadeia (gerar carta → enviar e-mail → montar arquivo AGI → carregar → atualizar EC). Não há mudança de gatilho no meio do trecho, então mantê-lo num único robô reduz a complexidade de orquestração.

**⚠️ Alternativa em aberto (levantada pelo próprio relatório).** *"Caso a carga no AGI se mostre historicamente instável, vale considerar isolá-la em uma etapa própria dentro do mesmo RPA, para permitir reprocessamento sem repetir o envio da carta."*

Isso merece atenção porque a cadeia mistura passos **irreversíveis e externos** (enviar e-mail para a operadora) com passos **reexecutáveis** (carga no AGI). Se a carga falhar depois do envio da carta, reprocessar tudo significaria enviar a carta de novo. Onde colocar o ponto de retomada é ⚠️ **decisão que depende da análise do código** e do histórico de estabilidade do AGI.

**HUs.** HU-12, HU-13, HU-14, HU-15, HU-16, HU-17, HU-18, HU-19, HU-20.
**Projetos de origem:** **P4 + P5 + parte do P6 (HU-20) + o Épico 5 órfão (P7 reservado) convergem aqui.** É o RPA com a maior fragmentação de origem.

**Sistemas.** Rede Lagoa (pastas AGI, Contestações, Correspondências Enviadas), Outlook, AGI (UI), banco WebFat, modelos de carta e planilhas-máscara.

---

## RPA 4 — Retificação de Contestação

**Correção de contestações lançadas em meses anteriores.**

**Gatilho.** Condição de negócio assíncrona: identificação de que um tráfego contestado foi recuperado no mês seguinte. **Não segue o calendário mensal padrão** do restante do processo.

**Responsabilidades.**
1. Identificar tráfego contestado que foi recuperado pela Vivo no mês seguinte
2. Entrar no AGI em `Contestação > Gerenciar` e filtrar pela contestação já inserida (período e empresa)
3. Registrar o evento **"Recuperação"** com os valores de diferença entre o Detraf Vivo e o Detraf da operadora

**Entrega.** Contestação retificada no AGI, com os campos Duração, Valor Líquido, Valor PIS/Cofins e Valor Bruto Negociado preenchidos.

**Por que foi separado.** Não roda todo mês nem segue o mesmo gatilho do fluxo principal — só existe *"no momento que o robô identificar que um tráfego contestado foi recuperado no mês seguinte"*. Manter essa lógica condicional dentro do RPA 3 tornaria aquele robô mais complexo de manter, com um desvio que só se aplica a um subconjunto de casos. Separado, o RPA 3 fica linear e a retificação roda de forma independente sempre que a condição for detectada.

**HUs.** HU-21. **Projeto de origem:** **parte do P6** — o mesmo projeto que contém a HU-20 (RPA 3).

**Sistemas.** AGI (UI), banco WebFat.

⚠️ **Ponto de atenção.** A **detecção** da necessidade de retificação está descrita no Épico 4 (fluxo do RPA 3), mas a **execução** é o RPA 4. Se a detecção acontece no RPA 3, como o RPA 4 é acionado? Por flag em banco? Por agendamento que reavalia? A documentação não define o mecanismo de disparo. ⚠️ Decisão que depende da análise do código.

---

## Como os projetos de origem se distribuem

```
P1 ──────────────────────────────────────────►  RPA 1

P2 ──┐
     ├───────────────────────────────────────►  RPA 2
P3 ──┘

P4 ──┐
P5 ──┤
P6 ──┼─ (HU-20) ──────────────────────────────►  RPA 3
P7? ─┘  (Épico 5, órfão)

P6 ─── (HU-21) ───────────────────────────────►  RPA 4
```

Apenas o **P1** mapeia 1:1 num RPA. Todos os demais convergem ou se dividem. O **P6 é o único que precisa ser cindido** entre dois RPAs.

Detalhamento completo em [`mapa-projetos-epicos-historias-rpas.md`](mapa-projetos-epicos-historias-rpas.md).

---

## O que a documentação **não** define sobre os RPAs

Registrado aqui para não virar suposição silenciosa. Tudo abaixo ⚠️ **depende da análise do código** ou de decisão da área cliente:

| Questão em aberto | Impacto |
|---|---|
| Como o RPA 2 é disparado após a data de corte | A data de corte não existe ainda |
| Como o RPA 3 detecta a sinalização do analista — polling no banco, fila, agendamento? | Define o mecanismo de espera do RPA 3 |
| Como o RPA 4 é acionado | A detecção está no RPA 3, a execução no RPA 4 |
| Granularidade de execução — por operadora, por lote, por arquivo? | Afeta paralelismo, reprocessamento e a trava da numeração CT |
| O que acontece quando um RPA falha no meio | Não há política de retomada definida |
| Se os quatro RPAs rodam na mesma máquina | A V2 fala em "memória da máquina local"; concorrência de recursos (Outlook, AGI, pastas de rede) não está tratada |
| Onde e como as credenciais são geridas | A V2 cita "usuário robótico — vide tabela interna GSA" |
