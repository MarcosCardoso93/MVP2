"""Nomes das tabelas do banco WebFat — ponto único de definição.

Os quatro projetos referenciavam os nomes como literais espalhados pelo código.
Centralizar aqui permite trocar um nome num lugar só.

Verificação feita na unificação: os quatro projetos usam **os mesmos nomes de
tabela**. O que parecia divergência (``tbl_mapeamento_descritores`` e
``tbl_contestacao`` no Projeto 4) eram nomes de **atributo** da classe, não de
tabela — os atributos apontam para ``tbl_detraf_mapeamento_descritores`` e
``tbl_rpa_log_detraf_despesa_contestacao``.

⚠️ **Divergência resolvida (pendência N1):** o log de arquivos chamava-se
``tbl_detraf_despesa_arquivos`` nos quatro projetos, mas a V2 documenta
``tbl_rpa_log_detraf_despesa_arquivos``. **Decisão do cliente (2026-07-31):
vale o nome da V2.**

✅ **Risco encerrado em 2026-08-06.** O banco real foi lido pela primeira vez
(``espelhar_banco.py``) e a tabela existe com o nome da V2 e com o schema que
este código presume. O nome antigo (``tbl_rpa_log_detraf_despesa``, sem sufixo)
também existe, vazio — ver ``TABELAS_NAO_DOCUMENTADAS``.

Para o ambiente de desenvolvimento, ``preparar_banco_dev.py`` gera um SQLite com
a tabela já renomeada, sem tocar em ``projetos-origem/``.

🔴 **O que a mesma leitura do banco real derrubou.** Três suposições deste
módulo estavam erradas, e cada uma quebrava em execução — nenhuma aparecia na
suíte, porque os *fixtures* declaravam o schema suposto, não o real:

1. ``tbl_anexo5_processado`` **não tem acento em nome de coluna nenhum**
   (``Regiao``, ``Tipo de Servico``, ``Concessao``,
   ``Endereco de Correspondencia``). O código lia com acento: ``KeyError``.
2. A tabela de contestação tem ``remuneracoes`` (**plural**), não
   ``remuneracao``. Era tratada aqui como coluna a ser criada pelo DBA; é o
   mesmo campo com outro nome, e criá-la geraria duplicata.
3. ``vb_contestacao`` é a única de fato ausente — ver
   ``COLUNAS_PENDENTES_NO_BANCO``.

O DDL real está versionado em ``banco_de_dados/schema-real-*.sql`` e é a fonte
de ``DDL_CONFIRMADO``. **Fecha a pendência Q22.**
"""

# ---------------------------------------------------------------------------
# Tabelas de consulta (somente leitura)
# ---------------------------------------------------------------------------
ANEXO5: str = "tbl_anexo5_processado"
TARIFAS: str = "tbl_detraf_tarifas"
MAPEAMENTO_DESCRITORES: str = "tbl_detraf_mapeamento_descritores"

# ---------------------------------------------------------------------------
# Tabelas de log (escrita)
# ---------------------------------------------------------------------------
#: Nome da V2 (decisão do cliente, 2026-07-31). Os projetos de origem usavam
#: `tbl_detraf_despesa_arquivos` — ver o risco no docstring do módulo.
LOG_DESPESA_ARQUIVOS: str = "tbl_rpa_log_detraf_despesa_arquivos"

#: Nome usado no código de origem **e** na V2 — sem divergência.
LOG_DESPESA_CONTESTACAO: str = "tbl_rpa_log_detraf_despesa_contestacao"


# ---------------------------------------------------------------------------
# Nomes de coluna que não dá para adivinhar
#
# A maioria das colunas é `snake_case` e se escreve sozinha. Estas não: têm
# espaço, e a grafia **sem acento** contraria o português de quem as digita.
#
# 🔴 Elas estavam como literais espalhados por seis pontos de chamada, escritos
# COM acento — e o banco real não tem acento em nenhuma. Toda leitura do Anexo 5
# levantava `KeyError` contra o MySQL de verdade, nos três RPAs. Os `fixtures`
# criavam as colunas acentuadas, então a suíte passava.
#
# Constantes em vez de literais para que exista **uma** declaração: quem
# escrever `Região` por reflexo agora recebe `NameError` no import, não
# `KeyError` no meio de uma execução desassistida.
#
# ⚠️ Nada é renomeado na leitura: o nome em memória é byte a byte o do banco.
# É isso que mantém `conferir_colunas` significando o que diz e deixa
# `repositorio_cache` como um `SELECT *` burro — o que torna o espelho um dublê
# honesto do banco real.
#
# Fonte: `banco_de_dados/schema-real-20260806.sql`.
# ---------------------------------------------------------------------------
COL_ANEXO5_EOT: str = "EOT"
COL_ANEXO5_NOME_FANTASIA: str = "Nome Fantasia"
COL_ANEXO5_REGIAO: str = "Regiao"
COL_ANEXO5_TIPO_SERVICO: str = "Tipo de Servico"
COL_ANEXO5_CONCESSAO: str = "Concessao"
COL_ANEXO5_ENDERECO_CORRESP: str = "Endereco de Correspondencia"

#: Coluna da remuneração na tabela de contestação — **plural**, como no banco.
#:
#: 🔴 O código usava `remuneracao` (singular) e este módulo a declarava como
#: "acrescentada pela unificação, pendente no DBA". A leitura do banco real
#: mostrou que ela sempre existiu como `remuneracoes`, guardando **um** código
#: por linha (`'VU-M'`), igual à irmã em `LOG_DESPESA_ARQUIVOS`. Criar
#: `remuneracao` produziria coluna duplicada, e o pedido ao DBA foi retirado.
#:
#: ⚠️ `remuneracao` (singular) continua existindo e **está certo** — é o nome da
#: coluna no DataFrame de domínio, e o nome do parâmetro de
#: `RepositorioTabelas.obter_tipo_contestacao`. Só o que fala com o banco usa o
#: plural. Um replace cego de um pelo outro quebra o projeto.
COL_CONTESTACAO_REMUNERACOES: str = "remuneracoes"


# ---------------------------------------------------------------------------
# Conjuntos de tabelas a carregar em cache, por RPA
#
# Cada RPA precisa de um conjunto diferente. Era a única diferença real entre
# as quatro versões do repositório de cache (duplicação D-06).
# ---------------------------------------------------------------------------
CACHE_RPA1: list[str] = [ANEXO5]

CACHE_RPA2: list[str] = [ANEXO5, TARIFAS, MAPEAMENTO_DESCRITORES]

CACHE_RPA3: list[str] = [ANEXO5, MAPEAMENTO_DESCRITORES, LOG_DESPESA_CONTESTACAO]

#: O RPA 4 (HU-21) lê e escreve **uma** tabela: a da contestação. Ele não
#: consulta Anexo 5 nem tarifas — o que precisa saber da operadora (nome e EOT)
#: já está gravado na linha pelo RPA 2.
CACHE_RPA4: list[str] = [LOG_DESPESA_CONTESTACAO]


# ---------------------------------------------------------------------------
# Lista branca de escrita
#
# Origem: o Projeto 4 validava toda escrita contra a sua ``TABELAS_CACHE``, para
# que um nome de tabela errado falhasse cedo em vez de gerar SQL contra algo
# inesperado. Como aqui a lista de cache virou parâmetro por RPA, a validação
# passa a usar este conjunto — todas as tabelas conhecidas do domínio.
# ---------------------------------------------------------------------------
TODAS: frozenset[str] = frozenset(
    {
        ANEXO5,
        TARIFAS,
        MAPEAMENTO_DESCRITORES,
        LOG_DESPESA_ARQUIVOS,
        LOG_DESPESA_CONTESTACAO,
    }
)


# ---------------------------------------------------------------------------
# Valores da coluna `carga_agi` de `tbl_rpa_log_detraf_despesa_contestacao`
#
# Ficam aqui porque **dois RPAs escrevem nesta coluna**: o RPA 2 grava o valor
# inicial ao criar a linha (HU-09/HU-10) e o RPA 3 o atualiza após a carga
# (HU-18, exigida pela V2: *"O robô atualiza o campo 'carga_agi' com o status da
# carga"*).
#
# Antes eram literais repetidos nos dois lados, e uma divergência de acento ou
# caixa passaria despercebida — o RPA 3 atualizaria linhas que o RPA 2 marcou de
# outro jeito, sem ninguém notar.
# ---------------------------------------------------------------------------

#: Valor inicial, gravado pelo RPA 2 ao criar a linha.
CARGA_AGI_NAO_CARREGADO: str = "não carregado"

#: Gravado pelo RPA 3 após o upload bem-sucedido.
CARGA_AGI_CARREGADO: str = "carregado"

#: Gravado pelo RPA 3 quando o upload falha. É informação: deixar
#: `CARGA_AGI_NAO_CARREGADO` faria a falha parecer uma execução que nunca houve.
CARGA_AGI_ERRO: str = "erro na carga"


# ---------------------------------------------------------------------------
# Colunas que o código lê ou escreve, por tabela
#
# Acrescentado em 2026-08-06, para a homologação manual. Serve ao
# `espelhar_banco.py` e ao `verificar_ambiente.py`: os dois conferem o schema
# real contra esta lista e **acusam por nome** o que estiver faltando.
#
# ⚠️ **Isto não é o DDL — é o que o código presume.** A V2 cita as quatro
# tabelas e alguns campos, mas nunca publica o DDL (pendência Q22). A lista
# abaixo foi levantada das leituras e escritas reais do repositório, e cada
# divergência entre ela e o banco de produção vira erro em execução.
#
# Não pretende ser exaustiva: são as colunas **usadas**. Uma coluna a mais no
# banco real é irrelevante; uma a menos quebra.
#
# ✅ **As cinco foram confirmadas em 2026-08-06**, contra o DDL do MySQL real
# (`banco_de_dados/schema-real-20260806.sql`). Até então duas vinham de prints do
# Workbench embutidos no `.docx` e três eram suposição — e as três estavam
# erradas. Ver `DDL_CONFIRMADO` abaixo.
# ---------------------------------------------------------------------------

#: Tipo real de cada coluna, **na ordem do banco**. Transcrito do DDL real.
#:
#: Serve a três coisas: dizer no `verificar_ambiente.py` o que está confirmado;
#: sustentar decisões de leitura — `tarifa` ser `float` é o que fechou a N10 e
#: permitiu tirar o `replace(",", ".")` do lado do banco; e ser a **declaração
#: única** de onde os `fixtures` de teste derivam o `CREATE TABLE`
#: (`tests_apoio.banco.ddl_sqlite`), para as duas não voltarem a divergir.
#:
#: ⚠️ Não pretende ser exaustivo em COMENTÁRIOS, mas é exaustivo em COLUNAS: se
#: uma coluna existe no banco, existe aqui. `test_espelho_do_banco` confere
#: contra `schema-real-*.sql`.
DDL_CONFIRMADO: dict[str, dict[str, str]] = {
    # As quatro com espaço no nome e sem acento — ver `COL_ANEXO5_*`.
    ANEXO5: {
        "id": "int AI PK",
        "EOT": "varchar(10) NOT NULL",
        "Nome Fantasia": "varchar(100)",
        "Razao Social": "varchar(150)",
        "CSP": "varchar(10)",
        "Tipo de Servico": "varchar(10)",
        "Modalidade / Banda": "varchar(30)",
        "Area de Prestacao": "varchar(60)",
        "Holding": "varchar(100)",
        "CNPJ": "varchar(200)",
        "Inscricao Estadual": "varchar(200)",
        "Endereco de Emissao Nota Fiscal": "varchar(250)",
        "Endereco de Correspondencia": "varchar(250)",
        "UF": "varchar(5)",
        "Regiao": "varchar(10)",
        "Concessao": "varchar(30)",
        "RN1": "int",
        "SPID": "int",
    },
    TARIFAS: {
        "id": "int AI PK",
        "sentido": "text NOT NULL",
        "tipo_remuneracao": "text NOT NULL",
        "regiao": "text",
        "gh": "text",
        # ✅ N10: `float`, com ponto. Valores observados: 0.00602, 0.00421.
        "tarifa": "float",
        "data_inicio": "datetime NOT NULL",
        "data_fim": "datetime NOT NULL",
        "regra_desc": "text",
        "tipo_dado": "text",
        "ativa": "text NOT NULL",
        "created_at": "datetime NOT NULL",
        "created_by": "text",
        "updated_at": "datetime",
        "updated_by": "text",
        "observacao": "text",
        # ⚠️ As cinco abaixo apareceram na leitura de 2026-08-06 e o código
        # **não as usa**. `eot_vivo` está preenchida em 64 das 127 linhas, e
        # ignorá-las faz o casamento de tarifa devolver mais de uma candidata
        # para a mesma região/GH/regra/vigência — ver o aviso em
        # `repositorio_tabelas.validar_tarifas_na_tabela`. Manter a regra atual
        # foi decisão de 2026-08-06; a precedência foi perguntada ao DBA.
        "eot_devedora": "text",
        "eot_vivo": "varchar(10)",
        "eot_operadora": "varchar(10)",
        "tipo_servico_vivo": "varchar(10)",
        "tipo_servico_oper": "varchar(10)",
    },
    MAPEAMENTO_DESCRITORES: {
        "id": "int AI PK",
        "final_descritor": "varchar(10) NOT NULL",
        "remuneracao_fixa": "varchar(50) NOT NULL",
        "observacao": "varchar(100)",
        # ⚠️ O código não filtra por `ativo` — hoje as 26 linhas estão ativas,
        # então é no-op. Vira divergência muda no dia em que alguém desativar
        # uma. Semântica perguntada ao DBA antes de mexer.
        "ativo": "tinyint(1)",
        "created_at": "datetime NOT NULL",
        "updated_at": "datetime",
        "produto": "varchar(150)",
    },
    LOG_DESPESA_ARQUIVOS: {
        # `int AI PK` — as CINCO tabelas têm `id int NOT NULL AUTO_INCREMENT` +
        # `PRIMARY KEY (id)`. Aqui dizia só `int NOT NULL`, e `ddl_sqlite` gerava
        # uma coluna obrigatória sem auto-incremento: todo INSERT do RPA 1 e do
        # RPA 2, que não informam `id`, quebrava com NOT NULL constraint.
        "id": "int AI PK",
        # ✅ N4: enum **fechado**. Gravar outro valor falha o INSERT com
        # STRICT_TRANS_TABLES — ou grava string vazia em silêncio sem ele.
        "tipo_registro": "enum('DETRAF','EXPECTATIVA','ERRO') NOT NULL",
        "nome_arquivo": "varchar(255)",
        "periodo": "varchar(20)",
        "empresa": "varchar(150)",
        "tipo_servico_operadora": "varchar(100)",
        "tipo_servico_vivo": "varchar(100)",
        "remuneracoes": "varchar(255)",
        "minuto_desp": "decimal(18,6)",
        "valor_bruto_desp": "decimal(18,6)",
        "status": "varchar(50)",
        "codigo_erro": "varchar(100)",
        "created_at": "datetime DEFAULT CURRENT_TIMESTAMP",
    },
    LOG_DESPESA_CONTESTACAO: {
        "id": "int AI PK",
        "tipo_servico_vivo": "varchar(100)",
        # Plural, como na irmã acima. Ver `COL_CONTESTACAO_REMUNERACOES`.
        "remuneracoes": "varchar(255)",
        "eot_tbra": "varchar(100)",
        "eot_operadora": "varchar(100)",
        "empresa": "varchar(100)",
        "referencia": "varchar(50)",
        "trafego": "varchar(100)",
        "minutos_tbra": "decimal(18,6)",
        "vb_tbra": "decimal(18,6)",
        "minutos_operadora": "decimal(18,6)",
        "vb_operadora": "decimal(18,6)",
        "minutos_diferenca": "decimal(18,6)",
        "vb_diferenca": "decimal(18,6)",
        "minutos_variacao_perc": "decimal(10,4)",
        "vb_variacao_perc": "decimal(10,4)",
        # `vb_contestacao` entraria aqui, entre `vb_variacao_perc` e
        # `carga_agi` — NÃO existe no banco. Ver `COLUNAS_PENDENTES_NO_BANCO`.
        "carga_agi": "varchar(50)",
        "tipo_contestacao": "varchar(100)",
        "created_at": "datetime DEFAULT CURRENT_TIMESTAMP",
    },
}

#: Valores aceitos por `tipo_registro`. Enum fechado, confirmado pelo DDL.
#:
#: ⚠️ Não confundir com o `tipo_lote` de `resultado_validacao.preparar_lote`,
#: que tem **quatro** valores e é parâmetro interno — ele é mapeado para estes
#: três antes de qualquer escrita. Ver `TestEnumDoTipoRegistro`.
TIPO_REGISTRO_VALIDOS: frozenset[str] = frozenset({"DETRAF", "EXPECTATIVA", "ERRO"})

#: Tabelas do schema `webfat` que a V2 **não cita** e que apareceram no
#: navigator do Workbench. Nenhuma é usada pelo código; ficam registradas
#: porque uma delas (`tbl_rpa_log_detraf_despesa`, sem sufixo) é provavelmente o
#: nome legado do log — e saber para qual das duas o WebFat aponta é o que
#: sobrou da pendência N1.
TABELAS_NAO_DOCUMENTADAS: tuple[str, ...] = (
    "tbl_detraf_operadoras",
    "tbl_detraf_regras_icms",
    "tbl_detraf_tarifas_transformacao",
    "tbl_encontro_contas",
    "tbl_rpa_log_detraf_despesa",
)

#: Colunas que o código usa e o banco real **não tem** — pendentes no DBA.
#:
#: 🔴 Esta constante já afirmou o contrário. Até 2026-08-06 ela se chamava
#: `COLUNAS_ACRESCENTADAS`, listava `remuneracao` **e** `vb_contestacao`, e
#: trazia um "✅ Confirmadas presentes no MySQL real" que nunca foi verificado
#: contra o banco. A primeira leitura real derrubou as duas metades: `remuneracao`
#: não é coluna nova (é `remuneracoes`, sempre esteve lá) e `vb_contestacao` não
#: está presente. Ficam as duas lições no nome novo — são as **pendentes**, e a
#: lista existe para ser conferida, não para tranquilizar.
#:
#: Sem `vb_contestacao`, o `UPDATE` da HU-19 falharia inteiro (`no such column`)
#: e a despesa não seria escrita para operadora alguma — nem os campos que
#: existem, porque é uma instrução só. Por isso
#: `RepositorioTabelas._atualizar_contestacao_em_lote` filtra as colunas
#: ausentes e grava o resto, avisando no log. **No dia do `ALTER TABLE` a coluna
#: volta a gravar sem tocar em código.**
COLUNAS_PENDENTES_NO_BANCO: dict[str, tuple[str, ...]] = {
    LOG_DESPESA_CONTESTACAO: ("vb_contestacao",),
}

COLUNAS_ESPERADAS: dict[str, tuple[str, ...]] = {
    # Montado a partir das constantes, não de literais redigitados — é o que
    # impede o acento de voltar por reflexo.
    ANEXO5: (
        COL_ANEXO5_EOT,
        COL_ANEXO5_NOME_FANTASIA,
        COL_ANEXO5_REGIAO,
        COL_ANEXO5_TIPO_SERVICO,
        COL_ANEXO5_CONCESSAO,
        COL_ANEXO5_ENDERECO_CORRESP,
    ),
    TARIFAS: (
        "regiao",
        "gh",
        "regra_desc",
        "tipo_remuneracao",
        "tarifa",
        "data_inicio",
        "data_fim",
    ),
    # ✅ Q22 fechada: o banco real usa os nomes de baixo. O SQLite que veio no
    # Projeto 2 tem `FINAL_DO_DESCRITOR`, `REMUNERACAO_FIXA` e `DS_OBS` —
    # `preparar_banco_dev.py` os renomeia, e é só o banco de dev que precisa
    # disso. `mapa_remuneracao.carregar_mapa_descritores` exige os de baixo e
    # levanta `ValueError` nomeando os que faltam (D-21/B-D21).
    MAPEAMENTO_DESCRITORES: (
        "id",
        "final_descritor",
        "remuneracao_fixa",
        "observacao",
        "produto",
    ),
    LOG_DESPESA_ARQUIVOS: (
        "tipo_registro",
        "nome_arquivo",
        "periodo",
        "empresa",
        "tipo_servico_operadora",
        "tipo_servico_vivo",
        "remuneracoes",
        "minuto_desp",
        "valor_bruto_desp",
        "status",
        "codigo_erro",
    ),
    LOG_DESPESA_CONTESTACAO: (
        "id",
        "tipo_servico_vivo",
        "eot_tbra",
        "eot_operadora",
        "empresa",
        "referencia",
        "trafego",
        COL_CONTESTACAO_REMUNERACOES,
        "minutos_tbra",
        "vb_tbra",
        "minutos_operadora",
        "vb_operadora",
        "minutos_diferenca",
        "vb_diferenca",
        "minutos_variacao_perc",
        "vb_variacao_perc",
        "vb_contestacao",
        "carga_agi",
        "tipo_contestacao",
    ),
}


def conferir_colunas(nome_tabela: str, colunas_reais) -> list[str]:
    """
    Quais colunas esperadas estão faltando numa tabela real.

    Compara **ignorando espaços nas pontas**, mas **distinguindo maiúsculas** —
    porque o MySQL distingue, e uma tabela com `FINAL_DO_DESCRITOR` onde o
    código procura `final_descritor` falha do mesmo jeito que se não existisse.

    Args:
        nome_tabela: Uma das tabelas de `COLUNAS_ESPERADAS`.
        colunas_reais: Nomes das colunas encontradas no banco.

    Returns:
        As esperadas que não estão lá, na ordem em que foram declaradas. Lista
        vazia significa que o código consegue operar sobre essa tabela.
    """

    presentes = {str(coluna).strip() for coluna in colunas_reais}
    return [
        coluna
        for coluna in COLUNAS_ESPERADAS.get(nome_tabela, ())
        if coluna not in presentes
    ]
