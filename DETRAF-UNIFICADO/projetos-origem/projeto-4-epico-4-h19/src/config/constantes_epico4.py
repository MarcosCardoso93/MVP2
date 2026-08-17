"""Constantes de domínio do Épico 4 (valores fixos e índices de layout).

Centraliza todos os "números/textos mágicos" para que regras que podem mudar
fiquem configuráveis num único lugar (AI/02 §6). Nada de literais repetidos
espalhados pelos services.

Fontes: AI/09-Regras-Negocio-Epico4.md (§0, §2–§6, §9) e AI/02-Convencoes.md (§7).
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
SUFIXO_ENV: str = "ENV"
SUFIXO_MODELO_BASE: str = "M"  # Base_Contestação_..._M (modelo do _ENV)

PREFIXO_AGI: str = "DE_AGI_D"
INFIXO_AGI: str = "TBRA_X"
PREFIXO_BASE_CONTESTACAO: str = "Base_Contestação"
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
# Layout do arquivo Detraf (índices de coluna, 0-based) — AI/09 §6
#
# D-8 — DECISÃO DO USUÁRIO (2026-07-23): usar os índices documentados aqui como
# o CONTRATO/DEFAULT em todo o código (funções de consolidação leem estas
# constantes por padrão). Isso não apaga a observação de campo (L-008): nas
# amostras reais (fixtures ALGAR/Vivo) a coluna de total aparece em índices
# diferentes do documentado (5 e 6, respectivamente, vs. 4 aqui) — por isso as
# funções continuam aceitando os índices como PARÂMETRO OPCIONAL (para o
# caso real conhecido), mas o valor documentado é sempre o default e a
# validação de nº de colunas permanece obrigatória (fail-fast).
# ---------------------------------------------------------------------------
COL_CREDORA: int = 0  # EOT da operadora (credora)
COL_DEVEDORA: int = 1  # EOT da Vivo (devedora)
COL_REFERENCIA: int = 2  # AAAAMM (mês corrente - 1)
COL_TRAFEGO: int = 3  # AAAAMM (mês do tráfego)
COL_REL: int = 4  # linha de total quando == "1" (remover)
COL_DESCRITOR: int = 6  # "campo DESC (descritor) ou 7ª coluna" (V2 pág. 7) — AI/09 §7
COL_GH: int = 7  # Grupo Horário (S/R/N/D)
COL_CHAMADAS: int = 8
COL_MINUTOS: int = 9
COL_TARIFA: int = 10
COL_R_LIQ: int = 11
COL_PIS_COFINS: int = 12
COL_ICMS: int = 13
COL_R_BRUTO: int = 14  # última coluna copiada para o EXT/INT

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

# Chave de identificação da linha. A mesma usada na leitura do sinal por
# `RepositorioTabelas.obter_tipo_contestacao` (T-024/D-6 + `remuneracao` desde
# 2026-07-28).
COLUNAS_CHAVE_DESPESA_CONTESTACAO: list[str] = [
    "eot_operadora",
    "eot_tbra",
    "referencia",
    "trafego",
    "remuneracao",
]

# Campos atualizados pela HU-19 — exatamente os seis nomeados na V2 pág. 38 (D-20).
COLUNAS_ATUALIZADAS_DESPESA_CONTESTACAO: list[str] = [
    "minutos_operadora",
    "vb_operadora",
    "minutos_diferenca",
    "vb_diferenca",
    "minutos_variacao_perc",
    "vb_variacao_perc",
]
