"""Leitura centralizada de variáveis de ambiente — base comum dos RPAs do Detraf.

Único ponto autorizado a chamar ``os.getenv``. Cada variável é lida uma vez e
exposta como constante tipada.

Origem: união dos quatro ``src/config/configuration.py`` dos projetos 1 a 4
(ver ``trabalho/inventarios/duplicacoes.md`` D-14 e ``candidatos-componentes.md`` #14).

Alterações intencionais em relação às origens, registradas na unificação:

1. ``load_dotenv()`` é sempre chamado. O Projeto 2 era o único que não chamava e
   dependia de o ambiente já estar carregado por fora.
2. O caminho do SQLite vem **somente** de variável de ambiente. O Projeto 2 tinha
   um caminho absoluto da máquina do desenvolvedor embutido no repositório de
   cache; ele foi removido.
3. ``DEBUG_ANO_MES_ATUAL`` e ``COMPETENCIA`` são aceitos como sinônimos — os
   projetos usavam nomes diferentes para a mesma coisa (D-17).
4. ``LOG_LEVEL`` passa a ser configurável. O Projeto 1 usava ``DEBUG`` fixo e os
   demais ``INFO``; o default é ``INFO``.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Set

from dateutil.relativedelta import relativedelta

# Carrega o `.env` se existir. Opcional em testes — por isso o `try`.
#
# ⚠️ **Sob pytest o `.env` NÃO é lido** (2026-08-06). A suíte tem que ser
# hermética: se ela lê o `.env` da máquina, ela deixa de testar o código e passa
# a testar a configuração de quem a roda.
#
# Isso não era teórico. Enquanto nenhum `.env` existia neste repositório a suíte
# passava; assim que o `.env` unificado foi criado, quatro testes quebraram —
# porque o `CAMINHO_SQLITE` de lá aponta para um espelho que a máquina de
# desenvolvimento não tem. Ou seja: **configurar o projeto quebrava os testes**,
# e o sintoma não apontava para a causa.
#
# As suítes montam o ambiente de que precisam nos seus `conftest.py`.
#
# A detecção é por `sys.modules`, e não pela variável `PYTEST_CURRENT_TEST`:
# este módulo é importado na **coleta**, e naquele momento a variável ainda não
# existe — ela só é definida quando um teste começa a rodar.
if "pytest" not in sys.modules:
    try:  # pragma: no cover - dependência opcional
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:  # pragma: no cover
        pass


# ---------------------------------------------------------------------------
# Ambiente
#
# ## Variável por robô (2026-08-06)
#
# Os quatro RPAs são agendados separadamente e podem estar em fases diferentes:
# o RPA 1 já em produção enquanto o RPA 3 ainda aponta para um espelho local. Até
# aqui `ENV` era global — um só valor para os três —, e alternar exigia reescrever
# o `.env` entre execuções, com o risco óbvio de esquecer de voltar.
#
# Agora **qualquer** variável aceita um sufixo por robô, e o específico vence:
#
#     ENV_RPA3=dev      # vale só para o RPA 3
#     ENV=prod          # vale para quem não tiver o específico
#
# O sufixo sai do `NOME_RPA` que cada `main.py` define antes de importar este
# módulo — `rpa3_contestacao_agi_ec` vira `RPA3`. Sem `NOME_RPA` (teste, script
# solto) não há sufixo, e tudo se comporta como antes.
# ---------------------------------------------------------------------------

#: Raiz de `unificado/`, resolvida a partir deste arquivo.
#:
#: Já era calculada aqui dentro, inline, só para o `RAIZ_LOGS`. Virou constante
#: em 2026-08-07 porque passou a ancorar **todo** caminho relativo do `.env` —
#: ver `_ancorar`. É o único ponto do projeto que sabe onde o `unificado/` fica.
RAIZ_UNIFICADO: Path = Path(__file__).resolve().parents[2]


def _ancorar(valor: str) -> Path:
    """
    Caminho relativo do `.env` vale a partir de `unificado/`, e não do CWD.

    🔴 **Sem isto, o `.env` depende de onde o robô foi lançado.** `Path()` de um
    caminho relativo é resolvido contra o diretório de trabalho do processo, no
    momento de cada operação de I/O. Enquanto todo mundo lança de `unificado/` —
    como o README manda — funciona. No dia em que alguém agenda pelo Agendador
    de Tarefas do Windows sem preencher "Iniciar em", o CWD vira
    `C:\\Windows\\System32` e nasce **uma segunda árvore de dados lá**.

    E o modo de falha é mudo: o RPA 1 grava numa árvore, o RPA 2 varre a outra,
    não acha nada e termina com sucesso.

    Não é hipótese. É o mesmo bug que fez `RAIZ_LOGS` virar absoluto — três
    árvores de log separadas no disco, uma por diretório de lançamento — e é a
    origem da pasta `unificado/historico_arquivos_processados/`, criada por uma
    execução em que a variável estava vazia e o default resolveu para `.`.

    Caminho absoluto passa intacto.
    """
    caminho = Path(valor)
    return caminho if caminho.is_absolute() else RAIZ_UNIFICADO / caminho


#: Nome do robô, usado no caminho do log e como origem do sufixo por robô. Cada
#: `main.py` define o seu; sem isso os três escrevem no mesmo arquivo de log e
#: não dá para isolar uma execução.
NOME_RPA: str = os.getenv("NOME_RPA", "")

#: `rpa3_contestacao_agi_ec` -> `RPA3`. Vazio fora de um robô.
SUFIXO_RPA: str = NOME_RPA.split("_")[0].upper() if NOME_RPA else ""

#: De qual variável cada valor veio — `{"ENV": "ENV_RPA3"}`. Alimenta o log de
#: arranque e o `verificar_ambiente.py`: "o RPA 3 está em dev" é metade da
#: informação; a outra metade é **qual linha do `.env` mandou nisso**.
ORIGEM_DAS_VARIAVEIS: dict[str, str] = {}


def _por_rpa(nome_variavel: str, padrao: str = "") -> str:
    """
    Lê uma variável de ambiente, deixando o sufixo do robô vencer o valor geral.

    Registra em `ORIGEM_DAS_VARIAVEIS` qual das duas respondeu — sem isso,
    descobrir por que um robô rodou no modo errado exige ler o `.env` inteiro
    procurando as duas grafias.
    """

    if SUFIXO_RPA:
        especifica = f"{nome_variavel}_{SUFIXO_RPA}"
        valor = os.getenv(especifica)
        if valor is not None and valor.strip():
            ORIGEM_DAS_VARIAVEIS[nome_variavel] = especifica
            return valor

    valor = os.getenv(nome_variavel)
    if valor is not None and valor.strip():
        ORIGEM_DAS_VARIAVEIS[nome_variavel] = nome_variavel
        return valor

    ORIGEM_DAS_VARIAVEIS[nome_variavel] = "(default do código)"
    return padrao


# HOSTNAME foi REMOVIDA (2026-08-04): estava declarada e nenhum módulo a lia. O
# caminho do log usa `socket.gethostname()` diretamente, não esta variável — o
# nome enganava quem procurasse por ela.
ENV: str = _por_rpa("ENV", "dev").lower()


# ---------------------------------------------------------------------------
# Log
#
# O log é a única testemunha do que o robô fez: ele roda desassistido, e boa
# parte das falhas (um clique que não achou o botão no AGI, um e-mail que não
# casou com a pasta) não deixa outro rastro.
# ---------------------------------------------------------------------------
LOG_LEVEL: str = _por_rpa("LOG_LEVEL", "INFO").upper()

#: Raiz dos arquivos de log. **Absoluta**, resolvida a partir de `unificado/`.
#:
#: Era `"logs/..."` relativo — e como cada robô é lançado do seu próprio
#: diretório, nasceram três árvores de log separadas no disco
#: (`unificado/logs/`, `rpa1_captura/logs/`, `rpa3_.../logs/`). Procurar uma
#: execução virava adivinhação.
RAIZ_LOGS: Path = _ancorar(os.getenv("RAIZ_LOGS") or "logs")

#: Por quanto tempo os logs ficam. Eram **7 dias** — mas o ciclo do Detraf é
#: mensal: uma contestação de julho é questionada em agosto, e o log que
#: explicaria o número já teria sido apagado.
LOG_RETENCAO: str = os.getenv("LOG_RETENCAO", "90 days")

#: `diagnose` do loguru: inclui os **valores das variáveis locais** no traceback.
#:
#: Ajuda muito a diagnosticar, e é exatamente por isso que grava dado sensível em
#: arquivo — senha de banco, credencial do AGI, conteúdo de e-mail. O default
#: segue o ambiente: ligado fora de produção. Um valor explícito sempre vence.
_log_diagnose = (os.getenv("LOG_DIAGNOSE") or "").strip().lower()
LOG_DIAGNOSE: bool = (
    _log_diagnose in {"1", "true", "sim", "yes", "on"}
    if _log_diagnose
    else ENV != "prod"
)


# ---------------------------------------------------------------------------
# Período de referência (AAAAMM)
#
# Regra de negócio do Detraf: processa-se sempre o mês ANTERIOR à referência.
# O override existe para teste; se vazio, usa o mês corrente como referência.
#
# Os projetos usavam nomes diferentes para o mesmo override — ``COMPETENCIA``
# no Projeto 1, ``DEBUG_ANO_MES_ATUAL`` nos demais (duplicação D-17). Ambos são
# aceitos e expostos como ``COMPETENCIA``.
#
# ``COMPETENCIA`` é o override **cru**, e existe para que
# ``comum.dominio.competencia.obter_competencia()`` possa resolvê-lo em tempo de
# chamada — que era o comportamento do Projeto 1, e é o que permite testar sem
# reimportar o módulo. ``ANO_MES_REFERENCIA`` é o valor
# já resolvido no import, como faziam os Projetos 2, 3 e 4.
# ---------------------------------------------------------------------------
COMPETENCIA: str = _por_rpa("DEBUG_ANO_MES_ATUAL") or _por_rpa("COMPETENCIA")

if COMPETENCIA:
    _data_referencia = datetime.strptime(COMPETENCIA, "%Y%m")
else:
    _data_referencia = datetime.now().replace(day=1)

_data_anterior = _data_referencia - relativedelta(months=1)

ANO_MES_REFERENCIA: str = _data_anterior.strftime("%Y%m")

# ANO_REFERENCIA foi REMOVIDA (2026-08-04): declarada e nunca lida. Quem precisa
# do ano usa `estrutura_pastas.ano_de(aaaamm)`, que valida o formato.


# ---------------------------------------------------------------------------
# Extensões de arquivo aceitas
# ---------------------------------------------------------------------------
_env_csv: str = os.getenv("EXTENSOES_CSV", "csv,txt")

EXTENSOES_CSV: Set[str] = {
    f".{ext.strip().lstrip('.')}".lower() for ext in _env_csv.split(",") if ext.strip()
}

_env_excel: str = os.getenv("EXTENSOES_EXCEL", "xlsx,xls")

EXTENSOES_EXCEL: Set[str] = {
    f".{ext.strip().lstrip('.')}".lower()
    for ext in _env_excel.split(",")
    if ext.strip()
}

EXTENSOES_PERMITIDAS: Set[str] = EXTENSOES_CSV.union(EXTENSOES_EXCEL)


# ---------------------------------------------------------------------------
# Banco de dados — MySQL em prod, SQLite local em dev
#
# CAMINHO_SQLITE não tem default: quando vazio, o repositório de cache resolve
# um SQLite relativo ao projeto.
#
# É `str`, e não `Path`, porque vira URL do SQLAlchemy (`sqlite:///{caminho}`) —
# mas passa por `_ancorar` como todos os outros: `banco_de_dados/espelho.db`
# lançado de fora de `unificado/` apontava para um arquivo que não existe, e o
# erro dizia "gere o espelho" quando o espelho já estava lá.
# ---------------------------------------------------------------------------
_sqlite = _por_rpa("CAMINHO_SQLITE") or _por_rpa("CAMINHO_SQLITE_DEV")
CAMINHO_SQLITE: str = str(_ancorar(_sqlite)) if _sqlite else ""

HOST_BD_RPA: str = _por_rpa("HOST_BD_RPA")
PORT_BD_RPA: str = _por_rpa("PORT_BD_RPA")
DATABASE_RPA: str = _por_rpa("DATABASE_RPA")
USUARIO_BD: str = _por_rpa("USUARIO_BD")
SENHA_BD: str = _por_rpa("SENHA_BD")


# ---------------------------------------------------------------------------
# Caminhos
#
# ATENÇÃO: `Path("")` NÃO é um caminho vazio — o pathlib o normaliza para
# `Path(".")`, o diretório atual. Com isso, uma guarda como
# `if not caminho.exists()` passa mesmo sem o caminho estar configurado, e a
# leitura seguinte estoura com PermissionError. Era o que acontecia com
# CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO, e abortava o RPA 2 no fim da execução.
#
# Por isso todo caminho opcional usa `_caminho_opcional`, que devolve `None`
# quando não configurado — obrigando quem consome a tratar a ausência.
# ---------------------------------------------------------------------------


def _caminho_opcional(nome_variavel: str) -> Path | None:
    """
    Lê uma variável de caminho, devolvendo ``None`` quando não configurada.

    Evita a armadilha de ``Path("")`` virar ``Path(".")``. Passa por
    `_por_rpa`, então aceita o sufixo do robô — é o que permite apontar o RPA 3
    para um espelho de teste enquanto os outros usam a pasta real.

    Relativo é ancorado em `unificado/` — ver `_ancorar`.
    """
    valor = _por_rpa(nome_variavel).strip()
    return _ancorar(valor) if valor else None


def _flag(nome_variavel: str, padrao: bool = False) -> bool:
    """
    Lê uma variável booleana do ambiente.

    Aceita ``1``, ``true``, ``sim``, ``yes`` e ``on`` (sem distinguir caixa)
    como verdadeiro; qualquer outro valor é falso. Também aceita o sufixo do
    robô — os kill-switches são justamente o que se quer ligar num robô de cada
    vez durante a homologação.
    """
    valor = _por_rpa(nome_variavel).strip().lower()
    if not valor:
        return padrao
    return valor in {"1", "true", "sim", "yes", "on"}


def _primeiro_caminho(*nomes_variaveis: str, padrao: str = "") -> Path:
    """
    Devolve o primeiro dos nomes que estiver configurado.

    Existe para os casos em que a mesma pasta física tinha nomes diferentes em
    cada projeto de origem: mantém os `.env` antigos funcionando enquanto o
    nome canônico é adotado. Cada nome é tentado **com o sufixo do robô antes
    do geral**, para que a precedência por robô valha também aqui.

    Relativo é ancorado em `unificado/` — ver `_ancorar`.
    """
    for nome in nomes_variaveis:
        valor = _por_rpa(nome).strip()
        if valor:
            return _ancorar(valor)
    return _ancorar(padrao) if padrao else Path(padrao)


# --- Raiz das operadoras -----------------------------------------------------
# "...\Operadoras", que contém {operadora}\{ano}\{aaaamm}\{subpasta}.
#
# Os três projetos davam nomes diferentes a esta MESMA pasta: `DIRETORIO_SAIDA`
# (Projeto 1, onde grava), `CAMINHO_DETRAF_RECEBIDO` (Projetos 2 e 3, de onde
# leem) e `CAMINHO_OPERADORAS` (Projeto 4). Nada garantia que apontassem para o
# mesmo lugar — e, se divergissem, o RPA 2 apenas registrava "nenhum arquivo
# encontrado" e seguia, sem erro.
#
# `CAMINHO_OPERADORAS` é o nome canônico: é como a V2 chama a pasta e já era
# usado por `comum/arquivos/estrutura_pastas.py`. Os outros dois viram alias.
CAMINHO_OPERADORAS: Path = _primeiro_caminho(
    "CAMINHO_OPERADORAS",
    "CAMINHO_DETRAF_RECEBIDO",
    "DIRETORIO_SAIDA",
    padrao="operadoras",
)

#: Alias de CAMINHO_OPERADORAS — o nome que o Projeto 1 usava.
#:
#: ⚠️ Não confundir com `DIRETORIO_SAIDA_VALIDACAO`, criada em 2026-08-10: esta
#: aqui é a raiz das operadoras (entrada do RPA 2); aquela é a pasta de saída dos
#: artefatos da validação. O nome quase colidiu — o
#: `test_contrato_rpa1_rpa2.test_os_tres_nomes_apontam_para_a_mesma_raiz` foi
#: quem pegou, e é por isso que a nova tem sufixo.
DIRETORIO_SAIDA: Path = CAMINHO_OPERADORAS

#: Alias de CAMINHO_OPERADORAS — o nome que os Projetos 2 e 3 usavam.
CAMINHO_DETRAF_RECEBIDO: Path = CAMINHO_OPERADORAS

# --- Demais caminhos ---------------------------------------------------------
# RPA 1 — pasta local onde os anexos são baixados antes de irem para a rede.
DIRETORIO_ENTRADA: Path = _ancorar(os.getenv("DIRETORIO_ENTRADA") or "entrada")

# Pasta de exceção do RPA 1, para arquivos cuja operadora não foi identificada.
# Fica FORA da raiz das operadoras: o RPA 2 varre essa raiz tratando todo
# diretório como uma operadora, e a pasta de exceção poluiria a varredura.
DIRETORIO_NAO_IDENTIFICADOS: Path = _ancorar(
    os.getenv("DIRETORIO_NAO_IDENTIFICADOS")
    or str(CAMINHO_OPERADORAS.parent / "_NAO_IDENTIFICADOS")
)

# Pasta de exceção do RPA 1, para arquivos REPROVADOS na validação (2026-08-06).
#
# É distinta da de não identificados, e a diferença importa para quem investiga:
# lá o arquivo está íntegro e o que falta é cadastro NOSSO; aqui o arquivo é que
# está errado, e a operadora já foi avisada.
#
# Fica FORA da raiz das operadoras por dois motivos. O primeiro é o mesmo do
# `_NAO_IDENTIFICADOS`: o RPA 2 varre a raiz tratando todo diretório como uma
# operadora. O segundo é mais grave — se estivesse dentro, o RPA 2 encontraria o
# arquivo reprovado, o validaria de novo e responderia à operadora uma SEGUNDA
# vez. A pasta ficar fora é o que garante que a reprovação é um beco sem saída.
DIRETORIO_QUARENTENA: Path = _ancorar(
    os.getenv("DIRETORIO_QUARENTENA")
    or str(CAMINHO_OPERADORAS.parent / "_QUARENTENA")
)

# RPA 2 — área de trabalho onde a validação escreve, para não tocar no insumo
# (2026-08-10).
#
# A validação de expectativa regrava o arquivo com as linhas que passaram. Se
# nenhuma passar — e basta o banco estar com uma coluna fora do lugar —, o que
# sobra é o cabeçalho, e em produção esse arquivo é o da rede. Desde esta data o
# robô copia o insumo para cá, escreve na cópia e devolve só os artefatos.
#
# Fica FORA de CAMINHO_OPERADORAS pelo mesmo motivo das duas de cima: o RPA 2
# varre aquela raiz tratando todo diretório como operadora, e encontraria as
# próprias cópias de trabalho como se fossem Detraf de alguém.
#
# É preservada por mês: serve de evidência de homologação e de estado parcial
# para investigar uma etapa que morreu no meio. Quem limpa é o
# `resetar_homologacao.py`.
DIRETORIO_TEMP: Path = _ancorar(
    os.getenv("DIRETORIO_TEMP") or str(CAMINHO_OPERADORAS.parent / "_TEMP")
)

# RPA 2 — onde os artefatos da validação são entregues (2026-08-10).
#
# Até esta data eles ficavam ao lado do insumo, e as pastas de entrada
# acumulavam entrada e saída misturadas. Pior: o RPA 3 lista TUDO que tem
# extensão válida em `Detrafs Recebidos` (`consolidacao_contestacao.
# listar_arquivos_detraf`), sem filtro de sufixo — o `_BK` e o `_ERRO` deixados
# ao lado entravam na consolidação e duplicavam linha.
#
# A estrutura espelha a origem, com `Operadoras/` e `Expectativa/` separados —
# ver `comum.arquivos.estrutura_pastas.caminho_de_saida`. Os dois lados da
# cadeia usam aquela função: quem grava (`AreaDeTrabalho.promover`) e quem lê
# (`batimento_detraf`). É o que impede o par escrever-num-lugar-ler-noutro que
# existia antes.
#
# Fica FORA de CAMINHO_OPERADORAS, como `_TEMP` e `_QUARENTENA`: o RPA 2 varre
# aquela raiz tratando todo diretório como operadora.
DIRETORIO_SAIDA_VALIDACAO: Path = _ancorar(
    os.getenv("DIRETORIO_SAIDA_VALIDACAO") or str(CAMINHO_OPERADORAS.parent / "_SAIDA")
)

# RPA 2 — árvore da expectativa Vivo, que é outra (Detrafs Enviados).
#
# `None` quando não configurado. Com `Path(".")` a guarda de
# `validacao_detrafs._preparar_arquivos_expectativa` — que testa `.exists()` e
# `.is_dir()` — passava, porque o diretório atual existe e é um diretório. O robô
# então varria o CWD procurando pastas de operadora, não achava nada, e seguia
# sem comparação nenhuma: a validação inteira virava no-op sem um único erro.
CAMINHO_EXPECTATIVA_DETRAF: Path | None = _caminho_opcional("CAMINHO_EXPECTATIVA_DETRAF")
# DIRETORIO_BASE_CONTESTACAO foi REMOVIDA (2026-08-04): era a pasta do arquivo
# `Base_Contestação_{OP}_{aaaamm}.xlsx`, que deixou de ser gerado. A base de
# contestação é a tabela `tbl_rpa_log_detraf_despesa_contestacao` — decisão do
# cliente, e o que a V2 já dizia: "Não é necessário gerar o arquivo, mas usar a
# lógica e popular a tabela".

# RPA 3 — controle de numeração de carta: "...\Correspondências Enviadas\CT\{ano}".
#
# `None` quando não configurado, e não `Path(".")`: é desta pasta que sai o último
# número CT emitido. Com `Path(".")` o robô procurava `./{ano}`, não achava, e
# acusava "pasta não encontrada" apontando para um caminho que ninguém configurou
# — escondendo que o problema era a variável ausente.
CAMINHO_CONTROLE_CT: Path | None = _caminho_opcional("CAMINHO_CONTROLE_CT")

# RPA 3 — contatos das operadoras para o e-mail da HU-15 (CSV `operadora;emails`).
#
# **Ponte da pendência Q16, decidida em 2026-08-05.** A V2 (¶136) manda buscar os
# destinatários "na tabela de contatos do WebFat", mas não diz qual tabela nem
# quais colunas, e nenhum dos sete projetos de origem chegou a consultá-la. Até a
# resposta vir, os contatos saem deste arquivo.
#
# ⚠️ Com ele preenchido **e** `PERMITIR_ENVIO_EMAIL=true`, o robô envia de
# verdade para as operadoras. `None` (o default) mantém a HU-15 recusando o envio.
CAMINHO_CONTATOS_OPERADORAS: Path | None = _caminho_opcional(
    "CAMINHO_CONTATOS_OPERADORAS"
)

# Comum — onde o RPA 1 e o RPA 2 guardam o índice anti-reprocessamento.
#
# 🔴 O default era `""`, e `Path("")` é `Path(".")` — o diretório atual. Foi
# assim que nasceu `unificado/historico_arquivos_processados/`: uma execução com
# a variável vazia, lançada de `unificado/`, criou a pasta na raiz do
# repositório. Lançada de outro lugar, criaria noutro — e o histórico
# anti-reprocessamento deixaria de proteger, em silêncio.
#
# Agora o default é explícito e fica junto dos demais dados.
DIRETORIO_HISTORICO_ARQUIVOS: Path = _primeiro_caminho(
    "DIRETORIO_HISTORICO_ARQUIVOS", padrao="arquivos/historico"
)


# ---------------------------------------------------------------------------
# Nomes das subpastas da estrutura de rede (configuráveis)
# ---------------------------------------------------------------------------
SUBPASTA_AGI: str = os.getenv("SUBPASTA_AGI", "AGI")
SUBPASTA_CONTESTACOES: str = os.getenv("SUBPASTA_CONTESTACOES", "Contestações")
SUBPASTA_DETRAFS_RECEBIDOS: str = os.getenv(
    "SUBPASTA_DETRAFS_RECEBIDOS", "Detrafs Recebidos"
)
SUBPASTA_DETRAFS_ENVIADOS: str = os.getenv(
    "SUBPASTA_DETRAFS_ENVIADOS", "Detrafs Enviados"
)


# ---------------------------------------------------------------------------
# Seleção de arquivos
# ---------------------------------------------------------------------------
# Substrings que o nome do arquivo de expectativa deve conter (o "_D_" da V2).
EXPECTATIVA_SUBSTRING: list[str] = [
    sub.strip()
    for sub in os.getenv("EXPECTATIVA_SUBSTRING", "").split(",")
    if sub.strip()
]

# Pastas onde os arquivos de expectativa devem estar (VIVO / TLF).
PASTAS_EXPECTATIVAS: list[str] = [
    pasta.strip()
    for pasta in os.getenv("PASTAS_EXPECTATIVAS", "").split(",")
    if pasta.strip()
]

# Substrings de nome de arquivo que devem ser ignoradas (ex.: _BK, _ERRO).
IGNORAR_ARQUIVOS: list[str] = [
    sub.strip() for sub in os.getenv("IGNORAR_ARQUIVOS", "").split(",") if sub.strip()
]

# Sufixos dos arquivos já validados pela etapa anterior.
ARQUIVOS_VALIDADOS: list[str] = [
    sub.strip() for sub in os.getenv("ARQUIVOS_VALIDADOS", "").split(",") if sub.strip()
]


# ---------------------------------------------------------------------------
# Identificação da Vivo no Anexo 5
# ---------------------------------------------------------------------------
# Usada pela validação da 2ª coluna do Detraf: a V2 diz que ela "deve estar
# preenchida com uma das EOTs da Vivo", e o casamento é por nome fantasia no
# Anexo 5.
#
# ⚠️ Até 2026-08-04 esta variável estava declarada e **não era lida**: a lista
# `["Vivo", "Telefônica"]` estava embutida em dois pontos de
# `validacao_colunas.py`, com o comentário "Adicionar aqui caso haja outros".
# Configurar exigiria mexer no código, em dois lugares — e a Q17 (nome de
# operadora que muda) vive exatamente nesse território.
NOME_FANTASIA_VIVO: list[str] = [
    nome.strip()
    for nome in os.getenv("NOME_FANTASIA_VIVO", "Vivo,Telefônica").split(",")
    if nome.strip()
]


# CABECARIO_PLANILHA foi REMOVIDA (2026-08-04): era o cabeçalho do `.xlsx`
# `Base_Contestação`, que deixou de ser gerado. A base de contestação é a
# tabela `tbl_rpa_log_detraf_despesa_contestacao`.


# ---------------------------------------------------------------------------
# Notificação da operadora (HU-04) e rastreamento arquivo -> e-mail
#
# **Quem responde é o RPA 1, desde 2026-08-06.** Ele valida o arquivo ANTES de
# salvá-lo na pasta que o RPA 2 lê; o que reprova vai para a quarentena e gera a
# resposta na mesma execução. O RPA 2 continua validando, como rede de
# segurança, mas não responde mais e-mail.
#
# Com isso, o rastreamento deixou de ser acoplamento entre os dois robôs e
# voltou a ser interno ao RPA 1 — que, aliás, nunca precisou procurar nada nele
# para responder: ele tem o `entry_id` em mãos, porque acabou de baixar o anexo.
# O que resta ligando os dois robôs é o sistema de arquivos.
#
# `RASTREAMENTO_ARQUIVO_PATH` é `Path`, não `str`. O Projeto 1 o definia como
# `str` (e convertia no consumidor) e o Projeto 2 como `Path` (e chamava
# `.exists()`/`.read_text()` direto). A unificação adotou o `str` do Projeto 1,
# o que fazia a notificação estourar com AttributeError — engolido por um
# try/except e reduzido a uma linha de log. Nenhuma operadora era notificada, e
# o robô reportava sucesso.
# ---------------------------------------------------------------------------
RASTREAMENTO_ARQUIVO_PATH: Path = _ancorar(
    os.getenv("RASTREAMENTO_ARQUIVO_PATH")
    or str(DIRETORIO_ENTRADA / "_rastreamento.json")
)

#: `None` quando não configurado — nunca `Path(".")`. Ver o bloco de caminhos.
CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO: Path | None = _caminho_opcional(
    "CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO"
)

# Se `True`, o RPA 1 ENVIA a resposta à operadora; se `False`, apenas cria o
# rascunho no Outlook para revisão humana.
#
# Default `False` de propósito: o envio é irreversível e externo, e a caixa de
# e-mail de teste ainda não foi confirmada (pendência Q20). A V2 determina que
# "a notificação deve ser encaminhada por e-mail" — ligar em produção, depois
# de validar em homologação.
NOTIFICAR_OPERADORA_ENVIAR: bool = _flag("NOTIFICAR_OPERADORA_ENVIAR", padrao=False)


# ---------------------------------------------------------------------------
# Kill-switches do RPA 3 (Projetos 5 e 7)
#
# Mesma convenção do `NOTIFICAR_OPERADORA_ENVIAR` acima: default `False`, porque
# os dois efeitos são externos e irreversíveis. Com eles desligados, o fluxo roda
# inteiro, decide tudo e registra no log — só não age para fora.
# ---------------------------------------------------------------------------

# Se `True`, o RPA 3 ENVIA o e-mail de contestação à operadora (HU-15); se
# `False`, monta o e-mail e registra no log sem chamar `Send()`.
PERMITIR_ENVIO_EMAIL: bool = _flag("PERMITIR_ENVIO_EMAIL", padrao=False)

# Se `True`, o RPA 3 executa a carga de arquivos no AGI (HU-17/HU-18); se
# `False`, monta a lista de upload e para antes de tocar na interface.
#
# É o kill-switch mais importante do repositório: **não existe ambiente de teste
# do AGI** (pendência Q20). Sem ele, a única forma de exercitar o fluxo seria
# contra produção.
PERMITIR_UPLOAD_AGI: bool = _flag("PERMITIR_UPLOAD_AGI", padrao=False)

# Se `True`, o RPA 3 abre o AGI para **baixar** o relatório da HU-20; se `False`,
# a verificação só roda sobre um relatório já baixado.
#
# A HU-20 é leitura, não escreve nada no AGI — mas **abre o aplicativo e faz login
# em produção**, e não há ambiente de teste (Q20). Separado do
# `PERMITIR_UPLOAD_AGI` de propósito: dá para conferir o relatório sem liberar a
# carga, que é o que altera dado.
#
# O Projeto 6 declarava um `PERMITIR_ACAO_AGI` e **nunca o lia** — era decorativo.
PERMITIR_ACESSO_AGI: bool = _flag("PERMITIR_ACESSO_AGI", padrao=False)

# Download da expectativa pelo SFTP do ClickHub (RPA 2, etapa `expectativa`).
#
# Desligado é o modo de teste, e ele é útil: o robô não conecta e a etapa segue
# com o que já estiver em `CAMINHO_EXPECTATIVA_DETRAF`. Foi assim que a
# expectativa chegou até 2026-08-10 — alguém a punha na pasta.
#
# É efeito externo mais brando que os outros (só lê o SFTP, não escreve lá), mas
# entra na mesma lista por dois motivos: escreve na árvore de arquivos que os
# robôs leem, e exige credencial de um sistema de terceiro.
PERMITIR_DOWNLOAD_SFTP: bool = _flag("PERMITIR_DOWNLOAD_SFTP", padrao=False)


# ---------------------------------------------------------------------------
# Parada interativa entre etapas (2026-08-06)
#
# 🔴 **Só tem efeito com ENV=dev.** Um robô desassistido que abre caixa de
# diálogo trava para sempre — e a caixa foi desenhada para esperar
# indefinidamente, porque na homologação conduzida a pessoa está ali.
#
# `comum/utils/pausa.py` exige QUATRO condições simultâneas, e esta é só uma
# delas. As outras três: ENV=dev, sessão gráfica utilizável e estar fora do
# pytest. Qualquer uma que falhe faz o robô seguir sem parar.
# ---------------------------------------------------------------------------
PAUSA_ENTRE_ETAPAS: bool = _flag("PAUSA_ENTRE_ETAPAS", padrao=False)


# ---------------------------------------------------------------------------
# Outlook Desktop Classic (RPA 1, RPA 2 e RPA 3)
# ---------------------------------------------------------------------------
OUTLOOK_ACCOUNT: str = os.getenv("OUTLOOK_ACCOUNT", "")
OUTLOOK_DETRAF_DESPESAS_FOLDER: str = os.getenv(
    "OUTLOOK_DETRAF_DESPESAS_FOLDER", "Detraf Despesas"
)
OUTLOOK_PROCESSADOS_FOLDER: str = os.getenv("OUTLOOK_PROCESSADOS_FOLDER", "PROCESSADOS")
OUTLOOK_DEST_ROOT: str = str(
    _ancorar(os.getenv("OUTLOOK_DEST_ROOT") or str(DIRETORIO_ENTRADA))
)
OUTLOOK_MAX_RETRY: int = int(os.getenv("OUTLOOK_MAX_RETRY", "3"))


# ---------------------------------------------------------------------------
# Regra de liberação do RPA 1
#
# **Decisão do GP/dev, 2026-08-05 (fecha a Q1): o dia 5, configurável aqui.**
#
# A V1 dizia "varredura diária após o dia 05". A V2 **removeu** o parágrafo de
# periodicidade e não colocou nada no lugar — deixar sem regra faria o RPA 1
# varrer desde o dia 1º, quando ainda não há Detraf publicado para o mês. Entre
# herdar a V1 e inventar, herdamos: o dia 5 é o que a V1 registrava e o que a
# operação já praticava.
#
# Não é placeholder: é escolha nossa, registrada como tal, e ajustável pelo
# `.env` sem tocar no código se a área cliente definir outra data.
# ---------------------------------------------------------------------------
DETRAF_DIA_LIBERACAO: int = int(os.getenv("DETRAF_DIA_LIBERACAO", "5"))


# ---------------------------------------------------------------------------
# Modelos externos — REMOVIDOS (2026-08-04)
#
# `CAMINHO_MODELO_CARTA` e `CAMINHO_MASCARA_CONT_PROC` existiam aqui e **nenhum
# módulo os lia**. A presença sugeria que a HU-14 estava bloqueada esperando um
# `.docx` externo — não está: `geracao_env_carta.renderizar_carta` monta o
# documento do zero com `python-docx` e os textos de `constantes.py`, a partir das
# duas cartas reais analisadas (CT 251/252-2026).
#
# O que falta na carta é fidelidade visual (logo, rodapé, fontes), gap aceito em
# D-12 — não é bloqueio funcional. O pré-requisito real da HU-14 é
# `CAMINHO_CONTROLE_CT`, acima.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Numeração das cartas de contestação (HU-14)
#
# Não pode haver duplicação: o número sai do último encontrado na pasta de
# controle, mais 1. Quando o último não puder ser identificado, o robô acusa
# erro em vez de assumir um valor (decisão do cliente, 2026-07-31).
#
# Esta variável é a exceção deliberada: em janeiro a pasta do ano é
# legitimamente nova e vazia. Definida, ela inicia a sequência — mas **apenas**
# quando a pasta existe e não tem nenhuma carta. Deixe vazia em operação normal,
# para que o bootstrap nunca aconteça por acidente.
# ---------------------------------------------------------------------------
_ct_numero_inicial = (os.getenv("CT_NUMERO_INICIAL") or "").strip()
CT_NUMERO_INICIAL: int | None = (
    int(_ct_numero_inicial) if _ct_numero_inicial.isdigit() else None
)


# ---------------------------------------------------------------------------
# AGI — Portal Triad (RPA 3, HU-17/HU-18; RPA 4 quando existir)
#
# O AGI não tem API: a integração é por automação de interface. Ver
# `rpa3_contestacao_agi_ec/src/integracoes/agi.py`.
#
# ⚠️ Credencial **nunca** no `.env` do repositório — só variável de ambiente da
# máquina. O `.env` do Projeto 7 vinha com usuário e senha preenchidos; esse
# padrão não é herdado aqui. Ver `inventario-projeto-7.md` §3.
# ---------------------------------------------------------------------------
USUARIO_AGI: str = os.environ.get("RPA_DETRAF_DESPESA_AGI_USER", "")
SENHA_AGI: str = os.environ.get("RPA_DETRAF_DESPESA_AGI_PASSWORD", "")


# ---------------------------------------------------------------------------
# SFTP do ClickHub — de onde a expectativa Vivo passa a vir (2026-08-10)
#
# Até esta data os arquivos `_D` chegavam à pasta por fora do repositório (ICT,
# outra demanda). Agora o RPA 2 os baixa, na etapa `expectativa`.
#
# Host e porta não são segredo e aceitam sufixo por robô, como o banco. Usuário e
# senha seguem a mesma regra do AGI, logo acima: **variável de ambiente da
# máquina**, não `.env` do repositório.
#
# 🔴 A senha que veio no script de referência (`vivo@2023`) circulou em texto
# claro num arquivo e **precisa ser rotacionada**.
# ---------------------------------------------------------------------------
SFTP_HOST: str = _por_rpa("CLICKHUB_SFTP_HOST", "")
SFTP_PORT: int = int(_por_rpa("CLICKHUB_SFTP_PORT") or _por_rpa("SFTP_PORT") or 22)
SFTP_USUARIO: str = os.environ.get("CLICKHUB_SFTP_USER", "")
SFTP_SENHA: str = os.environ.get("CLICKHUB_SFTP_PASSWORD", "")

#: Executável do AGI. `None` quando não configurado — nunca `Path(".")`.
DIRETORIO_AGI: Path | None = _caminho_opcional("DIRETORIO_AGI")

#: Ambientes que o Portal AIR oferece, e que o RPA 3 sabe abrir.
AMBIENTES_AGI: tuple[str, ...] = ("producao", "homologacao")

#: Qual dos dois o robô abre. Default `producao`, que é o comportamento que
#: existia antes de esta variável passar a existir (2026-08-06): até aqui
#: `acessar_producao()` clicava sempre no botão de produção, e a imagem
#: `bnt_homo_ini.png` estava capturada e sem uso.
AGI_AMBIENTE: str = _por_rpa("AGI_AMBIENTE").strip().lower() or "producao"

#: Host/IP do AGI **do ambiente escolhido**, que aparece no **título** dos
#: diálogos nativos de upload/download. É como o `pywinauto` acha a janela — se
#: estiver errado, o robô fica esperando um diálogo que nunca casa.
#:
#: Derivado de `AGI_AMBIENTE` de propósito. Como variável independente, dá para
#: logar em homologação e esperar o diálogo de produção; e o sintoma disso é um
#: timeout de 220s **depois** de o robô já ter aberto o AGI e logado.
#:
#: `AGI_JANELA_HOST` sem sufixo continua aceita: é a grafia dos `.env` dos
#: Projetos 6 e 7, que não conheciam ambiente.
AGI_JANELA_HOST: str = (
    _por_rpa(f"AGI_JANELA_HOST_{AGI_AMBIENTE.upper()}").strip()
    or _por_rpa("AGI_JANELA_HOST").strip()
)

#: Onde salvar os prints de evidência do upload.
#:
#: ⚠️ NÃO é requisito da V2. A citação "item 4.7.3" veio dos comentários do
#: Projeto 7 e não resolve: a V2 não tem numeração no texto, e as palavras
#: "evidência", "print" e "screenshot" não ocorrem no documento. O que a V2
#: exige como confirmação de carga é gravar `carga_agi` no banco.
DIRETORIO_EVIDENCIAS: Path | None = _caminho_opcional("DIRETORIO_EVIDENCIAS")


# ---------------------------------------------------------------------------
# HU-20 — verificação do Relatório de Receitas e Despesas
#
# O relatório baixado e o de inconsistências ficam sob `RAIZ_LOGS` porque são da
# mesma natureza do log: registro do que o robô viu, para alguém conferir depois.
# Herdam a organização por host e a política de retenção que já existem.
# ---------------------------------------------------------------------------

#: Onde o CSV exportado do AGI é gravado.
DIRETORIO_RELATORIO_AGI: Path = _ancorar(
    os.getenv("DIRETORIO_RELATORIO_AGI") or str(RAIZ_LOGS / "relatorio_agi")
)

#: Onde o `.xlsx` de divergências entre o AGI e o Encontro de Contas é gravado.
DIRETORIO_INCONSISTENCIAS: Path = _ancorar(
    os.getenv("DIRETORIO_INCONSISTENCIAS") or str(RAIZ_LOGS / "inconsistencias")
)

#: Diferença em reais a partir da qual a operadora é considerada divergente.
#:
#: ⚠️ O valor veio do Projeto 6, que o registrava com um TODO admitindo que **o
#: limiar oficial não foi confirmado** com a área cliente. Configurável para não
#: exigir mexer no código quando a resposta vier.
TOLERANCIA_VERIFICACAO: float = float(os.getenv("TOLERANCIA_VERIFICACAO", "0.01"))


# ---------------------------------------------------------------------------
# Resumo de arranque
#
# Acrescentado em 2026-08-06, para a homologação manual. Quem conduz o teste não
# tem como perguntar a ninguém em que modo o robô está — e "por que o RPA 3
# escreveu no banco de produção?" é a pergunta que se quer nunca ter que
# investigar depois.
# ---------------------------------------------------------------------------


def resumo_do_ambiente() -> list[str]:
    """
    Linhas legíveis com o modo em que este processo está e **de onde isso veio**.

    Cada `main.py` registra isto no arranque, e o `verificar_ambiente.py` o
    reaproveita. O nome da variável de origem é tão importante quanto o valor:
    com o sufixo por robô, o mesmo `.env` produz modos diferentes, e sem a
    origem descobrir qual linha mandou exige ler o arquivo inteiro.

    ⚠️ Nenhum valor de credencial aparece aqui — só se está presente ou não.
    """

    def origem(*nomes: str) -> str:
        """
        Qual variável respondeu, entre sinônimos.

        Vários valores aceitam mais de um nome (`COMPETENCIA` e
        `DEBUG_ANO_MES_ATUAL`; `CAMINHO_SQLITE` e `CAMINHO_SQLITE_DEV`), e o
        `or` entre eles faz o segundo nem ser consultado quando o primeiro
        responde. Ganha o primeiro que tiver origem de verdade.
        """
        for nome in nomes:
            registrada = ORIGEM_DAS_VARIAVEIS.get(nome, "")
            if registrada and not registrada.startswith("("):
                return registrada
        return "(default do código)"

    linhas = [
        f"robô: {NOME_RPA or '(nenhum — execução fora de um main.py)'}",
        f"modo: {ENV.upper()}  (de {origem('ENV')})",
        f"log: nível {LOG_LEVEL} (de {origem('LOG_LEVEL')}), "
        f"diagnose {'ligado' if LOG_DIAGNOSE else 'desligado'}",
        f"competência: {ANO_MES_REFERENCIA}"
        + (
            f"  (forçada por {origem('DEBUG_ANO_MES_ATUAL', 'COMPETENCIA')})"
            if COMPETENCIA
            else "  (mês anterior ao corrente)"
        ),
    ]

    if ENV == "dev":
        linhas.append(
            f"banco: SQLite [{CAMINHO_SQLITE or '(padrão do projeto)'}] "
            f"(de {origem('CAMINHO_SQLITE', 'CAMINHO_SQLITE_DEV')})"
        )
    else:
        linhas.append(
            f"banco: MySQL [{HOST_BD_RPA}:{PORT_BD_RPA}/{DATABASE_RPA}] "
            f"usuário [{USUARIO_BD or '(vazio)'}], "
            f"senha {'definida' if SENHA_BD else 'AUSENTE'}"
        )

    # O ambiente do AGI vem junto dos kill-switches porque é da mesma natureza:
    # decide ONDE o efeito externo acontece. "upload AGI: LIGADO" sozinho não
    # diz se o robô vai escrever em produção ou em homologação.
    linhas.append(
        f"AGI: ambiente [{AGI_AMBIENTE}] host [{AGI_JANELA_HOST or '(vazio)'}] "
        f"(de {origem('AGI_AMBIENTE')}) | executável "
        f"[{DIRETORIO_AGI or '(não configurado)'}]"
    )

    # Os kill-switches vêm por último e em caixa alta: são eles que decidem se a
    # execução escreve para fora, e é a linha que quem homologa precisa achar
    # sem procurar.
    linhas.append(
        "EFEITOS EXTERNOS -> "
        f"e-mail: {'LIGADO' if PERMITIR_ENVIO_EMAIL else 'desligado'} | "
        f"upload AGI: {'LIGADO' if PERMITIR_UPLOAD_AGI else 'desligado'} | "
        f"acesso AGI: {'LIGADO' if PERMITIR_ACESSO_AGI else 'desligado'} | "
        f"e-mail à operadora (RPA 1): "
        f"{'LIGADO' if NOTIFICAR_OPERADORA_ENVIAR else 'desligado'} | "
        f"download SFTP: {'LIGADO' if PERMITIR_DOWNLOAD_SFTP else 'desligado'}"
    )
    return linhas
