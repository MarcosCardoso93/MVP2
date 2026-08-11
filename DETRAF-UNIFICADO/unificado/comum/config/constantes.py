"""Constantes de domínio do Detraf — base comum dos RPAs.

Centraliza os "números e textos mágicos" para que regras que podem mudar fiquem
num único lugar. Nada de literais repetidos espalhados pelos services.

Origem: ``src/config/constantes_epico4.py`` do Projeto 4, que era o único dos
quatro com as constantes centralizadas — os demais tinham índices e textos
inline. Ver ``trabalho/inventarios/candidatos-componentes.md`` #12.

⚠️ Uma correção foi aplicada na unificação: ``COL_REL`` passou de 4 para 5.
Ver o bloco de layout adiante.

⚠️ Constantes exclusivas do RPA 3 (textos da carta, ``ID_MODALIDADE``) foram
mantidas aqui por virem do mesmo arquivo de origem, mas só têm um consumidor.
Se um segundo RPA nunca as usar, migram para ``rpa3_contestacao_agi_ec``.

As decisões D-3, D-4, D-5, D-7 e D-8 citadas nos comentários vêm da pasta
``AI/``/``TODO/`` do Projeto 4, que **não foi entregue** (pendência N5).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Textos fixos preenchidos nos artefatos AGI (HU-12 EXT / HU-13 INT)
# ---------------------------------------------------------------------------
ORIGEM: str = "E"
INSERCAO: str = "EXTERNO"

# Flag de expectativa por linha.
EXPECTATIVA_SIM: str = "S"  # linhas contestadas COM retenção (no EXT)
EXPECTATIVA_NAO: str = "N"  # demais linhas (e todo o INT)

# ---------------------------------------------------------------------------
# CONT_PROC (HU-16)
# ---------------------------------------------------------------------------
DEBIT_CREDIT_DESPESA: str = "D"  # coluna G — sempre despesa no Épico 4

# Coluna H (FLAG_PAG_REC): "P" com retenção, "R" sem retenção.
FLAG_PAG_REC_COM_RETENCAO: str = "P"
FLAG_PAG_REC_SEM_RETENCAO: str = "R"

# ---------------------------------------------------------------------------
# Cenários de contestação (sinal do analista — AI/09 §0, contrato AI/10 §1.3)
# ---------------------------------------------------------------------------
CENARIO_SEM_CONTESTACAO: str = "sem contestação"
CENARIO_SEM_RETENCAO: str = "SEM retenção"
CENARIO_COM_RETENCAO: str = "COM retenção"

# ---------------------------------------------------------------------------
# Tipos de operação / abas do Base_Contestação
# ---------------------------------------------------------------------------
TIPO_OPERACAO_SMP: str = "SMP"  # Vivo móvel
TIPO_OPERACAO_STFC: str = "STFC"  # Vivo fixa

ABA_CONTEST: str = "Contest"
ABA_TBRA: str = "TBRA"
PREFIXO_ABA_RESUMO: str = "RESUMO"

# D-4 RESOLVIDA (2026-07-23): o usuário confirmou, a partir dos 2 exemplos reais da
# máscara CONT_PROC_MASCARA_OPERADORA_202510_TESTE.xls (ambos com ID_MODALIDADE="00",
# apesar de remunerações diferentes — PTL e VU-M), que o valor é fixo para os casos que
# o Épico 4 cobre. Não é uma tabela de lookup (a máscara real não tem a aba
# "Remuneração" com colunas I/J/K que a documentação original previa).
ID_MODALIDADE_PADRAO: str = "00"

# ---------------------------------------------------------------------------
# Sufixos e componentes de nomenclatura de artefatos (AI/02 §7)
# ---------------------------------------------------------------------------
SUFIXO_EXT: str = "EXT"
SUFIXO_INT: str = "INT"
#: Renomeado de "ENV" para "EXP" (decisão registrada nesta troca). O ¶599 da V2
#: e o AI/09 §4.1 citam "_ENV" literalmente — ver a nota em
#: `nomenclatura.nome_env` e em `geracao_env_carta`.
SUFIXO_EXP: str = "EXP"

PREFIXO_AGI: str = "DE_AGI_D"
INFIXO_AGI: str = "TBRA_X"
PREFIXO_CONT_PROC: str = "CONT_PROC_MASCARA"
PREFIXO_CARTA: str = "CT"

# Extensões de saída por artefato.
EXTENSAO_EXCEL: str = ".xlsx"
EXTENSAO_XLS: str = ".xls"  # exigida pelo CONT_PROC (HU-16) — ver D-7
EXTENSAO_DOCX: str = ".docx"  # carta (HU-14, T-082/T-083) — ver D-3

# ---------------------------------------------------------------------------
# Carta (HU-14, T-082) — textos fixos confirmados pelos exemplos reais
# CT 251-2026/CT 252-2026 (D-3, 2026-07-27). Cenário COM retenção assumido por
# substituição simples de CENARIO_SEM_RETENCAO -> CENARIO_COM_RETENCAO (sem
# exemplo real ainda).
# ---------------------------------------------------------------------------
CARTA_ASSUNTO_TEMPLATE: str = "CONTESTAÇÃO DETRAF – {aaaamm}"
CARTA_CORPO_TEMPLATE: str = (
    "Estamos encaminhando contestação {tipo_contestacao} no mês de {aaaamm} do "
    "DETRAF entre as operações TBRA e a {operadora}."
)
CARTA_SAUDACAO: str = "Prezada,"
# Cidade da data — RESOLVIDO (2026-07-27): usuário confirmou São Paulo como padrão fixo
# (os 2 exemplos reais divergiam: Rio de Janeiro na CT 251, São Paulo na CT 252).
CARTA_CIDADE_PADRAO: str = "São Paulo"
CARTA_FECHO: str = (
    "Colocamo-nos a disposição para quaisquer esclarecimentos que se façam "
    "necessária.\n\nAtenciosamente."
)
CARTA_COLUNA_CONTESTACAO_A_ENVIAR: str = "contestacao_a_enviar"  # removida da tabela

# Assinatura — RESOLVIDO (2026-07-27): usuário confirmou usar sempre a assinatura da
# carta real CT 252-2026-DIR-A1-tbrasilxserctel-Contestação_202606.docx (Angélica),
# fixa para todas as operadoras (não varia como nos 2 exemplos reais).
CARTA_ASSINATURA_NOME: str = "ANGELICA GUIMARAES PEREIRA"
CARTA_ASSINATURA_CARGO: str = "Gerente da Divisão Operação de Interconexão"

# ---------------------------------------------------------------------------
# Layout do arquivo da OPERADORA (índices de coluna, 0-based)
#
# CORREÇÃO DA UNIFICAÇÃO — `COL_REL` era 4 no Projeto 4 e passou a 5.
#
# A V2 numera as colunas a partir de 1: "6ª coluna ou 'Rel'" = índice 5, e
# "7ª coluna ou 'DESC'" = índice 6. O Projeto 4 tinha COL_REL = 4 (que aponta
# para o POI) e COL_DESCRITOR = 6 — internamente inconsistente, porque se o Rel
# estivesse em 4 o DESC estaria em 5.
#
# A fixture real com cabeçalho (`algar_stfc_reduzido.csv`) confirma a V2:
#   0 cd_eot_bil · 1 cd_eot_rel · 2 mes_ref · 3 mes_traf · 4 poi
#   5 tipo_relatorio(Rel) · 6 descritor · 7 grupo_horario · 8 qtde · 9 minutos
#   10 tarifa · 11 valor_liq · 12 valor_piscofins · 13 valor_icms · 14 valor_total
#
# Com COL_REL = 4 o filtro de linhas de total agia sobre o POI e nada era
# removido. Ver `trabalho/inventarios/inventario-projeto-4.md` §4.
#
# Consequência: a "variação de layout" registrada na decisão D-8 do Projeto 4
# não existe para o arquivo da operadora — o índice documentado é que estava
# errado. A variação REAL é entre o arquivo da operadora e o da expectativa
# Vivo, que é outro arquivo (ver PERFIL_EXPECTATIVA_VIVO abaixo).
#
# As funções continuam aceitando os índices como parâmetro opcional.
# ---------------------------------------------------------------------------
COL_CREDORA: int = 0  # EOT da operadora (credora)
COL_DEVEDORA: int = 1  # EOT da Vivo (devedora)
COL_REFERENCIA: int = 2  # AAAAMM (mês corrente - 1)
COL_TRAFEGO: int = 3  # AAAAMM (mês do tráfego)
COL_POI: int = 4  # escrita livre, não obrigatório
COL_REL: int = 5  # linha de total quando == "1" (remover)
COL_DESCRITOR: int = 6  # "campo DESC (descritor) ou 7ª coluna" (V2 pág. 7)
COL_GH: int = 7  # Grupo Horário (S/R/N/D)
COL_CHAMADAS: int = 8
COL_MINUTOS: int = 9
COL_TARIFA: int = 10
COL_R_LIQ: int = 11
COL_PIS_COFINS: int = 12
COL_ICMS: int = 13
COL_R_BRUTO: int = 14  # última coluna copiada para o EXT/INT


# ---------------------------------------------------------------------------
# Colunas 16 a 21 — o layout completo (confirmado em 2026-08-06, pendência Q6)
#
# A V2 publicava só as 15 primeiras e apontava o resto para um "isnumos" nunca
# fornecido. O layout completo é:
#
#   1  Credora            8  GH          15  R$_Bruto
#   2  Devedora           9  Chamadas    16  CN_RELACIONAMENTO
#   3  Referencia        10  Minutos     17  CBS
#   4  Trafego           11  Tarifa      18  IBS_Municipal
#   5  POI               12  R$_Liq      19  IBS_Estadual
#   6  Rel               13  PIS_Cofins  20  EOT_Ponta
#   7  DESC              14  ICMS        21  Corredor
#
# ✅ **A notícia importante: as 15 primeiras NÃO se mexem.** CBS e IBS entram
# DEPOIS do `R$_Bruto`, não no bloco de impostos. Toda a leitura posicional que
# este repositório faz (índices 0 a 14) continua válida, e o `R$_Bruto` segue no
# índice 14.
#
# ⚠️ **Estes índices ainda NÃO são validados**, de propósito. O que os arquivos
# reais têm hoje depois da 15ª coluna **não é este layout**: a ALGAR entrega 18
# colunas em que a 16ª é `valor_total_real`, a 17ª `OPERATOR_TYPE` e a 18ª
# `cd_eot`. Validar por estas posições passaria a rejeitar arquivos que hoje
# passam — e que estão certos para o layout vigente deles.
#
# Servem para: (1) saber onde CBS/IBS estarão quando os arquivos migrarem;
# (2) documentar que `Corredor` (índice 20) existe de verdade — ele aparecia em
# `layout_detraf.py` sem fonte, e a Q12 chegou a registrar isso como suposição
# nossa; (3) `EOT_Ponta`, que não tinha nome em lugar nenhum.
# ---------------------------------------------------------------------------
COL_CN_RELACIONAMENTO: int = 15
COL_CBS: int = 16
COL_IBS_MUNICIPAL: int = 17
COL_IBS_ESTADUAL: int = 18
COL_EOT_PONTA: int = 19
COL_CORREDOR: int = 20

#: Quantas colunas o layout completo tem. O mínimo obrigatório continua sendo
#: 15 (`layout_detraf.COLUNAS_MINIMAS`) — arquivo com 15 é válido.
COLUNAS_LAYOUT_COMPLETO: int = 21


# ---------------------------------------------------------------------------
# Layout do arquivo de EXPECTATIVA VIVO (`_D_`) — genuinamente diferente
#
# ⚠️ ACHADO DA UNIFICAÇÃO, PENDENTE DE CONFIRMAÇÃO (pendência N3).
#
# A fixture real `vivo_d_reduzido.csv` tem cabeçalho próprio e outra ordem:
#   0 GROUP_CREDORA · 1 EOT_CREDORA · 2 EOT_DEVEDORA · 3 PERIODO_REFERENCIA
#   4 PERIODO_TRAFEGO · 5 POI · 6 REL · 7 PARTE_TARIFADA · 8 DESCRITOR
#   9 GRUPO_HORARIO · 10 TARIFA_APLICAVEL · 11 CORREDOR_TRANSPORTE
#   12 TIPO_TRANSPORTE · 13 QTDE_CHAMADAS · 14 MINUTOS_TARIFADOS · 15 VALOR_LIQUIDO
#
# Nenhum campo coincide com o layout da operadora, e **não existe coluna de
# R$_Bruto** — o arquivo termina em VALOR_LIQUIDO. Como a comparação da HU-10 é
# sobre R$_Bruto, isso precisa ser resolvido com a área cliente antes de a
# apuração ser considerada correta.
#
# Estas constantes existem para que o código NOMEIE o problema em vez de
# aplicar silenciosamente os índices da operadora ao arquivo da expectativa —
# que é o que o Projeto 3 fazia.
# ---------------------------------------------------------------------------
EXPECTATIVA_COL_CREDORA: int = 1
EXPECTATIVA_COL_DEVEDORA: int = 2
EXPECTATIVA_COL_REFERENCIA: int = 3
EXPECTATIVA_COL_TRAFEGO: int = 4
EXPECTATIVA_COL_POI: int = 5
EXPECTATIVA_COL_REL: int = 6
EXPECTATIVA_COL_DESCRITOR: int = 8
EXPECTATIVA_COL_GH: int = 9
EXPECTATIVA_COL_TARIFA: int = 10
EXPECTATIVA_COL_CHAMADAS: int = 13
EXPECTATIVA_COL_MINUTOS: int = 14
EXPECTATIVA_COL_R_LIQ: int = 15
# EXPECTATIVA_COL_R_BRUTO — não existe no arquivo. Ver pendência N3.
EXPECTATIVA_COL_R_BRUTO: int | None = None

# Valor textual que marca a linha de total na coluna Rel (ver L-006: lê-se str).
VALOR_REL_TOTAL: str = "1"

# ---------------------------------------------------------------------------
# Regra de variação de R$_Bruto na aba Contest (AI/09 §1)
# < 1% => N (não contesta); >= 1% => S (contesta).
# ---------------------------------------------------------------------------
LIMIAR_VARIACAO_CONTESTACAO: float = 0.01

# ---------------------------------------------------------------------------
# Escrita em `tbl_rpa_log_detraf_despesa_contestacao` (AI/10 §1.3)
#
# Ficam aqui (e não no serviço) porque são consumidas pelas duas pontas — o
# serviço que prepara as linhas e o repositório que as grava —, e o repositório
# não pode importar de `src/services` (inversão de camada, AI/01 §1).
# ---------------------------------------------------------------------------

# Chave de identificação da linha, em NOMES DE COLUNA DO BANCO. A mesma usada na
# leitura do sinal por `RepositorioTabelas.obter_tipo_contestacao` (T-024/D-6 + a
# remuneração desde 2026-07-28).
#
# ⚠️ `remuneracoes` é PLURAL — é como a coluna se chama no banco. O nome da mesma
# coisa no DataFrame de domínio e no parâmetro de `obter_tipo_contestacao` é
# `remuneracao`, singular, e está certo assim. Até 2026-08-06 esta lista dizia
# `remuneracao`, e a coluna era tratada como pendente no DBA — a primeira leitura
# do banco real mostrou que ela sempre existiu no plural. Ver
# `tabelas.COL_CONTESTACAO_REMUNERACOES`.
COLUNAS_CHAVE_DESPESA_CONTESTACAO: list[str] = [
    "eot_operadora",
    "eot_tbra",
    "referencia",
    "trafego",
    "remuneracoes",
]

# Campos atualizados pela HU-19 — exatamente os seis nomeados na V2 pág. 38 (D-20).
COLUNAS_ATUALIZADAS_DESPESA_CONTESTACAO: list[str] = [
    "minutos_operadora",
    "vb_operadora",
    "minutos_diferenca",
    "vb_diferenca",
    "minutos_variacao_perc",
    "vb_variacao_perc",
    # 🔴 ESTA COLUNA NÃO EXISTE NO BANCO — confirmado em 2026-08-06 (Q24).
    #
    # É a única de fato ausente: a `remuneracao` que a acompanhava neste
    # comentário acabou sendo só divergência de nome (é `remuneracoes`).
    #
    # Ela FICA nesta lista de propósito. `RepositorioTabelas` filtra as colunas
    # inexistentes antes do UPDATE, grava as demais e avisa no log — o `UPDATE` é
    # uma instrução só, e sem esse filtro a coluna ausente derrubaria os outros
    # seis campos para todas as operadoras. No dia do `ALTER TABLE` ela volta a
    # gravar sem tocar em código.
    #
    # V2 ¶942 (bloco antigo) e V1 HU-19: *"Quando acontece a contestação com
    # retenção, o robô também preenche a coluna de contestação da remuneração no
    # EC [...] com o valor bruto da Diferença apresentada aba Contest."* O
    # `vb_diferenca` ao lado é gravado para **todas** as linhas; este só para as
    # COM retenção, e é o que separa "diferença apurada" de "diferença retida".
    "vb_contestacao",
]


# ---------------------------------------------------------------------------
# Retificação / recuperação (HU-21 — RPA 4)
# ---------------------------------------------------------------------------

#: Fração do valor bruto que sobra como valor **líquido**, depois do PIS/Cofins.
#:
#: PIS/Cofins de 3,65% → 0,9635. Regra do To Be MVP2, ¶369-372, usada ao lançar o
#: evento de Recuperação no AGI.
#:
#: 🔴 **Está aqui, e não no código, de propósito.** Na origem era um literal no
#: meio do cálculo, e o README do RPA 4 já apontava por quê isso não pode ser:
#: as premissas 10.3/10.4 da V2 dizem que a solução não pode ficar condicionada a
#: regra de negócio que muda — e esta muda. Com CBS/IBS entrando em 2027, a
#: alíquota deixa de valer, e quem for corrigir precisa achar **um** lugar.
FATOR_LIQUIDO_PIS_COFINS: float = 0.9635
