# Matriz de Rastreabilidade

HU → item da V2 → projeto de origem → RPA de destino → status → **código**.

**Atualizada em 2026-08-10**, depois da auditoria de cobertura das 21 HUs. O Projeto 6 chegou completo: a HU-20 em 05/08 e a **HU-21 em 10/08**, que deu origem ao **RPA 4**. Os quatro robôs existem.

⚠️ Esta matriz esteve desatualizada entre 05/08 e 10/08 — dizia que o RPA 4 não existia e que a HU-09 gravava planilha. Ao mexer num robô, **atualize a linha dele aqui**: é o documento que alguém consulta para decidir o que já está pronto.

As HUs 12 a 19 deixaram de ser "implementada mas não orquestrada": `GeracaoAgiController.gerar_artefatos()` as encadeia na ordem da V2.

Fonte da coluna Código: [`../../trabalho/inventarios/`](../../trabalho/inventarios/).

---

## Matriz principal

| HU | Título | Épico | Item da V2 | Projeto | RPA | Status | Código |
|---|---|---|---|---|---|---|---|
| HU-01 | Leitura e organização do inbox | 1 | 4.1.1–4.1.4 | P1 | 1 | 🟡 | ✅ `comum/integracoes/outlook.py`, `rpa1_captura/src/services/email_filter_service.py`. **Sem filtro por mês de referência** — decisão de 2026-08-10 (A7): tolerância deliberada com atraso da operadora |
| HU-02 | Identificação da operadora | 1 | 4.1.6 | P1 | 1 | 🔴 mecanismo mudou | ⚠️ **híbrida** `services/operadora_service.py` — V2 primário, **fallback V1** por domínio |
| HU-03 | Salvamento em pastas de rede | 1 | 4.1.5, 4.1.7, 2.7, 2.13 | P1 | 1 | 🟢 | ✅ `rpa1_captura/src/services/processamento_service.py`. Servidor do WebFat **fora do escopo** — só local (reconfirmado 2026-08-10, C1). **Reenvio com o mesmo nome volta a ser processado**: o histórico compara tamanho e data, não só o caminho (A1) |
| HU-04 | Validação estrutural das colunas | 2 | 3.2 (15 colunas), regra `_ERRO` | P2 | 1 e 2 | 🟡 | ✅ `comum/dominio/validacao_colunas.py` + `comum/dominio/layout_detraf.py`. **12 das 15 regras**: a col. 7 (descritor × remuneração do nome) não é validada por decisão (C2). `_ERRO` por registro é **só da expectativa** (C3) |
| HU-05 | Validação da tarifa regulada | 2 | 3.2.11, `tbl_detraf_tarifas` | P2 | 1 e 2 | 🟡 | ✅ `comum/dominio/validacao_colunas.py`, `repositorio_tabelas.py::validar_tarifas_na_tabela`. **`eot_vivo`/`eot_operadora` ignorados por decisão** (C4) — aceita a tarifa de qualquer par de EOTs |
| HU-06 | Arquivo `_BK` (SMP não-PMS) | 2 | 3.2.7 (L…V, SMP, não-PMS) | P2 | 2 | 🟢 | ✅ `rpa2_.../validacao_inicial/limpeza_trafegos.py::separar_linhas_bk`. **Passou a valer para os dois arquivos** — operadora e expectativa — em 2026-08-10 (A4) |
| HU-07 | Erro L-L (STFC) | 2 | absorvida pela regra geral | P2 | 2 | 🟢 **já fundida** | ✅ `limpeza_trafegos.py::separar_linhas_ll` — caso de um mecanismo genérico de fluxos |
| HU-08 | Registro dos arquivos no WebFat | 2 | 4.3.2, `tipo_registro` | P2 | 2 | 🟢 | ✅ `rpa2_.../services/resultado_validacao.py`. **Uma linha por arquivo** desde 2026-08-10 (A2): o RPA 1 deixou de gravar o válido e só registra o que só ele sabe — o recusado e o **não identificado**, este último novo (A6) |
| HU-09 | Consolidação da Base Contestação | 3 | 4.3.7.1.3 | P3 | 2 | 🟢 planilha→banco | ✅ `rpa2_.../services/criacao_arquivo_contestacao.py` — **só banco**; o `.xlsx` foi removido em 2026-08-04, a base de contestação é a tabela |
| HU-10 | Análise de contestação por EOT | 3 | 2.10.1, aba Contest | P3 | 2 | 🟡 | ✅ `criacao_arquivo_contestacao.py::_comparar_e_persistir`, `_aplicar_analise_contestacao`. A flag `S`/`N` é calculada e **não persistida**, por decisão (B1): a tela do WebFat aplica o 1% sobre `vb_variacao_perc` |
| HU-11 | Exibição no WebFat (analista) | 3 | aba Contestação | P3 | 2 | 🟢 | ➖ **N/A ao RPA** — é tela do WebFat; o RPA só popula a tabela |
| HU-12 | Arquivo `_EXT` | 4 | 5.4.6.1 | P4 | 3 | 🟢 | ✅ `services/geracao_ext.py` |
| HU-13 | Arquivo `_INT` | 4 | 5.4.6.2 | P4 | 3 | 🟢 | ✅ `services/geracao_int.py` |
| HU-14 | Arquivo `_ENV` + carta | 4 | 5.4.6.3 | P4 | 3 | 🟡 | ✅ `services/geracao_env_carta.py` — a carta com **modelo único** para todas as operadoras (decisão de 2026-08-04; a V2 ¶601 pedia um por operadora). Pré-requisito: `CAMINHO_CONTROLE_CT` |
| HU-15 | E-mail de contestação | 4 | 5.4.6.3.2 (e-mail) | P5 | 3 | 🟡 | ⚠️ **parcial** `rpa3_.../services/envio_email_contestacao.py`. Destinatários vêm de um CSV de ponte, mantido por decisão (C7). O disparo **a partir do sinal do analista** não existe: falta controle de reenvio (**Q30**) |
| HU-16 | Arquivo `CONT_PROC` | 4 | 5.4.6.4, `tipo_contestacao` | P4 | 3 | 🟡 | ✅ `rpa3_.../services/geracao_cont_proc.py`. Sai `.xlsx` e **sem usar a máscara**, mantido por decisão (C6). `VLR_BRUTO` recebe minutagem (Q11) |
| HU-17 | Upload `_EXT`/`_INT` no AGI | 5 | 4.3.7.3 (Detraf > Importar) | P7 | 3 | 🟡 | ⚠️ `rpa3_.../services/upload_detraf_agi.py`. **Sem confirmação de sucesso** pós-upload; `detectar_linhas_vermelhas` é do processo de **Receita** e não deve ser ligada (A3). Imagens não validadas na VM |
| HU-18 | Upload contestação no AGI | 5 | 4.3.7.3, `carga_agi` | P7 | 3 | 🟡 | ⚠️ `services/upload_contestacao_agi.py` + `carga_agi` gravado; **nunca executada** contra o AGI (Q20) |
| HU-19 | Preenchimento do Encontro de Contas | 6 | 4.3.7.4 | P4 | 3 | 🟢 planilha→banco | ✅ **V2** `rpa3_.../services/encontro_contas.py`. O consolidado do EC **é a tabela**, não uma planilha — reconfirmado em 2026-08-10 (C11) |
| HU-20 | Verificação Relatório Rec. e Desp. | 6 | ¶689–¶706, CBS/IBS | P6 | 3 | 🟡 | ⚠️ **parcial** `rpa3_.../services/verificacao_relatorio.py` — EC do banco; CBS/IBS **somadas e registradas, não comparadas**, mantido por decisão (B4, junto com a Q6) |
| HU-21 | Tráfego recuperado e retificação | 6 | ¶710–¶738 | **P6** | **4** | 🟡 | ✅ `rpa4_retificacao/` (2026-08-10) — `services/deteccao_recuperacao.py`, `services/retificacao_agi.py`, `comum/dominio/retificacao.py`, `comum/integracoes/agi.py`. ⚠️ **`carga_agi` compartilhado com a HU-18 por decisão (Q26)**: a linha já carregada pelo RPA 3 fica invisível aqui. Automação de tela **não calibrada** |
| HU-22 | Tratamento CBS/IBS | — | 2.10.2–2.10.3 | ⚠️ **nenhum** | ⚠️ ? | 🆕 | ❌ **não implementada** em nenhum dos quatro |

**Legenda da coluna Código:** ✅ implementada · ⚠️ parcial ou com ressalva · ❌ não implementada · ⬜ projeto ainda não entregue · ➖ não aplicável ao RPA

---

## Cobertura consolidada (todos os projetos recebidos)

| Situação | HUs | Qtd |
|---|---|---|
| Implementada | 01, 04, 05, 06, 07, 08, 12, 13, 16, 19 | 10 |
| Implementada com ressalva | 02, 03, 09, 10, 14, 15, 17, 18, **20** | 9 |
| Não aplicável ao RPA | 11 | 1 |
| **Não implementada** | **22** | **1** |

**Das 21 HUs, as 21 têm código.** A única ausente da lista é a **HU-22** (CBS/IBS),
que não está em nenhum dos sete projetos e depende da Q6.

A HU-21 mudou nesta rodada, de "não entregue" para **implementada**: o Projeto 6
chegou com ela em 2026-08-10 e deu origem ao RPA 4. O marco M7 deixou de estar
bloqueado por falta de código — o que resta ali é calibrar a automação de tela na
VM e decidir a Q26.

⚠️ **"Tem código" não é o mesmo que "está pronto".** A auditoria de 2026-08-10
mostrou que a diferença entre as duas coisas mora **dentro** das HUs, não entre
elas: nenhuma estava ausente, e mesmo assim havia sete defeitos e uma dúzia de
critérios não atendidos. As ressalvas de cada linha da tabela acima são o que
importa ler.

A HU-20 mudou na rodada anterior, de "projeto não entregue" para **parcial**. A V2
(¶706) pedia confirmação de que ela deveria existir — **o GP/dev confirmou em
2026-08-05 que fica no escopo**, e a Q7 foi fechada.

O kill-switch `PERMITIR_ACESSO_AGI` continua, com outra justificativa: a HU-20
abre o AGI e faz login em produção, e não há ambiente de teste (Q20). É proteção
de ambiente, não dúvida de escopo.

---

## ⚠️ Achados que a análise acrescentou

| Achado | Onde | Efeito |
|---|---|---|
| ~~**P4 não executa** — orquestração stub~~ | `geracao_agi_controller.py::gerar_artefatos` | ✅ **resolvido (2026-08-04)** — as HUs 12 a 19 são encadeadas na ordem da V2 |
| **`COL_REL = 4`** (correto: 5) | P4 `constantes_epico4.py` | Linhas de total não removidas no default |
| **Remuneração derivada do POI** (correto: descritor, idx 6) | P3 `_enriquecer_com_tipo` | `tipo_produto` nulo em dados reais |
| **`tipo_operacao` derivado da Credora** (correto: Devedora) | P3 `_enriquecer_com_tipo` | Contraria a V2 e a HU-10 |
| **Índices da operadora aplicados à expectativa** | P3 `_gerar_aba_contest` | 🔴 comparação central desalinhada — *a confirmar contra arquivo real* |
| **`remuneracao` na chave do P4, não gravada pelo P3** | P3 × P4 | P4 não casa linhas do P3 |

Detalhes em [`../../trabalho/inventarios/inventario-projeto-3.md`](../../trabalho/inventarios/inventario-projeto-3.md) e [`inventario-projeto-4.md`](../../trabalho/inventarios/inventario-projeto-4.md).

**Legenda de status:** 🟢 mantida · 🟡 atualizada · 🔴 impactada estruturalmente · ⚠️ risco/pendência · 🆕 escopo novo sem HU

---

## Cobertura por projeto de origem

| Projeto | HUs | Qtd | RPA(s) | Transformação |
|---|---|---|---|---|
| P1 — Épico 1 | 01, 02, 03 | 3 | 1 | **Direta** (1:1) |
| P2 — Épico 2 | 04, 05, 06, 07, 08 | 5 | 2 | Convergência com P3 |
| P3 — Épico 3 | 09, 10, 11 | 3 | 2 | Convergência com P2 |
| P4 — Épico 4 + H19 | 12, 13, 14, 16, 19 | 5 | 3 | Convergência com P5, P6, P7 |
| P5 — H15 | 15 | 1 | 3 | Convergência |
| P6 — H20 + H21 | 20, 21 | 2 | **3 e 4** | **Cisão** |
| P7 — reservado | 17, 18 | 2 | 3 | ⚠️ Existência a confirmar |
| — | 22 (CBS/IBS) | 1 | ? | ⚠️ Órfã |

**Total mapeado:** 21 HUs. **Sem projeto de origem confirmado:** HU-22 (CBS/IBS).
A HU-17 e a HU-18 vieram no **Projeto 7**, entregue em 2026-08-04.

---

## Cobertura por RPA de destino

| RPA | HUs | Qtd | Origens | Complexidade |
|---|---|---|---|---|
| RPA 1 — Captura | 01, 02, 03 | 3 | P1 | Baixa |
| RPA 2 — Validação e apuração | 04–11 | 8 | P2, P3 | Média |
| RPA 3 — Contestação, AGI e EC | 12–20 | 9 | P4, P5, P6(20), P7? | **Alta** |
| RPA 4 — Retificação | 21 | 1 | P6(21) | Baixa em volume |

---

## Tabelas do banco por HU

| Tabela | HUs que escrevem | HUs que leem |
|---|---|---|
| `tbl_rpa_log_detraf_despesa_arquivos` | HU-03, HU-08 | HU-09 |
| `tbl_rpa_log_detraf_despesa_contestacao` | HU-09, HU-10, HU-16 (`tipo_contestacao`), HU-18 (`carga_agi`), HU-19 (campos do EC) | HU-11, HU-12, HU-13, HU-14, HU-20, HU-21 |
| `tbl_detraf_tarifas` | — | HU-05 |
| `tbl_detraf_mapeamento_descritores` | — | HU-05, HU-10, HU-12, HU-13, HU-19 |

⚠️ **`tbl_rpa_log_detraf_despesa_contestacao` é escrita por cinco responsabilidades**, distribuídas entre RPA 2 e RPA 3, em momentos diferentes. A mesma linha é atualizada por RPAs distintos. Ver [`../01-entendimento/dependencias-funcionais.md`](../01-entendimento/dependencias-funcionais.md), §6.2.

---

## Artefatos de arquivo por HU

| Artefato | Produz | Consome |
|---|---|---|
| Arquivo da operadora (Detrafs Recebidos) | HU-03 | HU-04, HU-09 |
| Arquivo de expectativa (`_D_`) | ICT (externo) | HU-04, HU-09, HU-13 |
| `_BK` | HU-06 | — |
| `_ERRO` | HU-04 | — |
| `Base_Contestação` (⚠️ ver Q4) | HU-09? | HU-14 |
| `_ENV` | HU-14 | HU-15 |
| Carta CT | HU-14 | HU-15 |
| `_EXT` | HU-12 | HU-17 |
| `_INT` | HU-13 | HU-17 |
| `CONT_PROC` | HU-16 | HU-18 |
| `DE_EBT_..._MODELO.xlsx` | ⚠️ desconhecido | HU-17 |

---

## Sistemas externos por HU

| Sistema | HUs |
|---|---|
| **Outlook** — leitura | HU-01 |
| **Outlook** — movimentação | HU-01 |
| **Outlook** — envio | HU-04 (crítica), HU-15 (contestação) |
| **Rede Lagoa** | HU-03, HU-04, HU-06, HU-09, HU-12, HU-13, HU-14, HU-17, HU-18 |
| **Servidor WebFat (arquivos)** | HU-03, HU-04 |
| **Banco WebFat** | HU-03, HU-05, HU-08, HU-09, HU-10, HU-11, HU-16, HU-18, HU-19, HU-21 |
| **Anexo 5** | HU-02, HU-04, HU-05, HU-06, HU-10, HU-21 |
| **AGI (UI)** | HU-17, HU-18, HU-20, HU-21 |

---

## Pendências por HU

| HU | Pergunta | Severidade |
|---|---|---|
| HU-01 | Q1 — data de corte | 🔴 |
| HU-02 | Q16 — casos de exceção | 🟡 |
| HU-03 | Q1, Q15 — data de corte, local×WebFat×Lagoa | 🔴 / 🟡 |
| HU-04 | Q6 — CBS/IBS no layout | 🔴 |
| HU-05 | Q9, Q12 — tarifas não reguladas, descritores de transporte | 🟡 |
| HU-06 | Q10 — recálculo do total | 🟡 |
| HU-08 | Q13 — correção automática | 🟡 |
| HU-09 | Q4 — `_ENV` × `Base_Contestação` | 🔴 |
| HU-10 | Q2, Q6 — regra de 1%, CBS/IBS | 🔴 |
| HU-11 | Q19 — escopo do WebFat | 🟡 |
| HU-14 | Q4, Q18 — origem do `_ENV`, numeração CT | 🔴 / 🟡 |
| HU-15 | ~~Q5~~ resolvida (kill-switch); Q16 — tabela de contatos do WebFat | 🔴 |
| HU-16 | Q11 — coluna W | 🟡 |
| HU-17 | ~~Q3~~ resolvida; ~~Q14~~ fechada em 2026-08-05 — o `DE_EBT_..._MODELO` fica fora de escopo | 🟢 |
| HU-18 | ~~Q3~~ resolvida; falta validar a tela na VM (sem ambiente de teste — Q20) | 🟡 |
| HU-19 | Q8 — EC no RPA 2 ou 3 | 🟡 |
| HU-20 | ~~Q7~~ fechada (fica no escopo); ~~N11~~ fechada (0,01 configurável); Q6 — falta a contra-parte de imposto no EC | 🟡 |
| HU-21 | Q17 — nome de operadora muda; **N12** — não entregue, adiada por decisão de 2026-08-05 | 🟡 |
| HU-22 | Q6 — CBS/IBS | 🔴 |

**HUs sem pendência:** HU-07 (só precisa ser fundida na HU-04), HU-12, HU-13.

Detalhamento em [`duvidas-pendentes.md`](duvidas-pendentes.md).

---

## Como manter esta matriz

1. **Em M1**, ao receber cada projeto: confirmar se as HUs esperadas estão lá.
2. **Em M2**, ao analisar: preencher a coluna **Código** com arquivo e linha. HU sem código → marcar "não implementada" **explicitamente**.
3. **Em M2**, adicionar uma coluna **Versão** (V1/V2) para as HUs 🔴.
4. **Em M3**, atualizar as colunas Projeto/RPA se o mapa real divergir do documental.
5. **Em M5–M8**, marcar cada HU como migrada e validada.

**Gate de M2:** nenhuma linha da matriz com a coluna Código vazia e sem marcação de ausência.
