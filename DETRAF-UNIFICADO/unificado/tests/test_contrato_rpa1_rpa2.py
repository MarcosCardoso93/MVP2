"""Contrato entre o RPA 1 e o RPA 2.

Sobrou **um** canal: os arquivos em disco. O RPA 1 grava onde o RPA 2 varre — e,
desde 2026-08-06, grava lá **só o que passou na validação**.

O segundo canal saiu neste mesmo dia. Era o ``_rastreamento.json``: o RPA 1
registrava de qual e-mail viera cada arquivo, e o RPA 2 procurava lá **pelo nome
do arquivo** para responder à operadora. A busca por nome existia porque o
arquivo mudava de lugar entre os dois robôs, e era ambígua por construção — dois
e-mails com anexos de mesmo nome empatavam. Como quem responde passou a ser o
RPA 1, que tem o ``entry_id`` em mãos, o rastreamento voltou a ser interno a ele.

O que este arquivo protege agora:

1. o RPA 1 grava exatamente onde o RPA 2 procura;
2. as pastas de exceção ficam FORA da raiz das operadoras — senão o RPA 2 as
   trata como operadoras;
3. **os dois robôs validam com a mesma classe.** Sem isto, os dois portões
   divergem em silêncio: o RPA 2 passaria a recusar o que o RPA 1 aprovou, ou,
   pior, a aprovar o que ele recusou.

Cada teste aqui trava um defeito que já existiu, e todos falham em silêncio: o
RPA 2 não acha os arquivos, ou a operadora nunca é notificada.
"""

import importlib.util
from pathlib import Path

import pytest

_RAIZ = Path(__file__).resolve().parents[1]


def _carregar_por_caminho(nome: str, caminho: Path):
    """
    Carrega um módulo pelo caminho do arquivo, sem passar pelo pacote.

    Necessário porque os três RPAs têm um pacote chamado ``src``: uma vez que o
    ``src`` de um deles esteja em ``sys.modules``, ``import src.x`` resolve
    sempre contra aquele. Este teste precisa tocar os dois RPAs no mesmo
    processo — daí a carga direta.
    """
    especificacao = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)
    return modulo


# ---------------------------------------------------------------------------
# Tipos da configuração
#
# O `RASTREAMENTO_ARQUIVO_PATH` era `str`, e o RPA 2 chama `.exists()` nele.
# A exceção resultante era engolida pelo try/except da notificação e virava uma
# linha de log: nenhuma operadora notificada, robô reportando sucesso.
# ---------------------------------------------------------------------------


def test_rastreamento_e_path_e_nao_str():
    from comum.config.configuration import RASTREAMENTO_ARQUIVO_PATH

    assert isinstance(RASTREAMENTO_ARQUIVO_PATH, Path)
    # As duas operações que o RPA 2 faz, e que um `str` não suporta.
    assert RASTREAMENTO_ARQUIVO_PATH.exists() in (True, False)
    assert hasattr(RASTREAMENTO_ARQUIVO_PATH, "read_text")


def test_template_de_email_nao_configurado_e_none(monkeypatch):
    """
    `Path("")` vira `Path(".")`, o diretório atual: a guarda `if not
    caminho.exists()` passava e o `read_text()` seguinte estourava com
    PermissionError — fora do try por arquivo, abortando o RPA 2 inteiro.
    """
    import comum.config.configuration as cfg

    monkeypatch.delenv("CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO", raising=False)
    caminho = cfg._caminho_opcional("CAMINHO_TEMPLATE_EMAIL_DETRAF_INVALIDO")

    assert caminho is None
    assert caminho != Path("")
    assert caminho != Path(".")


def test_caminho_opcional_nao_devolve_diretorio_atual(monkeypatch):
    import comum.config.configuration as cfg

    monkeypatch.setenv("_VARIAVEL_DE_TESTE", "   ")
    assert cfg._caminho_opcional("_VARIAVEL_DE_TESTE") is None

    monkeypatch.setenv("_VARIAVEL_DE_TESTE", "C:/algum/caminho")
    assert cfg._caminho_opcional("_VARIAVEL_DE_TESTE") == Path("C:/algum/caminho")


# ---------------------------------------------------------------------------
# Raiz única das operadoras
#
# Três nomes para a mesma pasta física, sem nada garantindo que apontassem
# para o mesmo lugar. Divergindo, o RPA 2 só registrava "nenhum arquivo
# encontrado".
# ---------------------------------------------------------------------------


def test_os_tres_nomes_apontam_para_a_mesma_raiz():
    from comum.config.configuration import (
        CAMINHO_DETRAF_RECEBIDO,
        CAMINHO_OPERADORAS,
        DIRETORIO_SAIDA,
    )

    assert CAMINHO_OPERADORAS == DIRETORIO_SAIDA == CAMINHO_DETRAF_RECEBIDO


def test_pasta_de_nao_identificados_fica_fora_da_raiz_das_operadoras():
    """
    O RPA 2 varre a raiz tratando TODO diretório como uma operadora. A pasta de
    exceção do RPA 1 não pode ficar lá dentro.
    """
    from comum.config.configuration import (
        CAMINHO_OPERADORAS,
        DIRETORIO_NAO_IDENTIFICADOS,
    )

    raiz = CAMINHO_OPERADORAS.resolve()
    excecao = DIRETORIO_NAO_IDENTIFICADOS.resolve()

    assert raiz not in excecao.parents
    assert excecao != raiz


# ---------------------------------------------------------------------------
# O caminho dos arquivos — o RPA 1 grava exatamente onde o RPA 2 procura
# ---------------------------------------------------------------------------


def test_rpa1_grava_na_subpasta_que_o_rpa2_varre(tmp_path):
    """
    O RPA 1 monta o destino com `caminho_detrafs_recebidos`; o RPA 2 monta a
    pasta alvo com `raiz / operadora / ano / aaaamm / SUBPASTA_DETRAFS_RECEBIDOS`.
    Este teste reproduz os dois e exige que coincidam.
    """
    from comum.arquivos.estrutura_pastas import caminho_detrafs_recebidos
    from comum.config.configuration import SUBPASTA_DETRAFS_RECEBIDOS

    operadora, aaaamm, ano = "ALGAR", "202605", "2026"

    destino_rpa1 = caminho_detrafs_recebidos(
        operadora=operadora, aaaamm=aaaamm, raiz_operadoras=tmp_path
    )
    alvo_rpa2 = tmp_path / operadora / ano / aaaamm / SUBPASTA_DETRAFS_RECEBIDOS

    assert destino_rpa1 == alvo_rpa2


def test_a_subpasta_de_entrada_e_a_exigida_pela_v2():
    from comum.config.configuration import SUBPASTA_DETRAFS_RECEBIDOS

    assert SUBPASTA_DETRAFS_RECEBIDOS == "Detrafs Recebidos"


def test_pasta_do_mes_e_a_pai_da_subpasta_de_entrada(tmp_path):
    """
    O RPA 1 clona a estrutura do mês anterior sobre a pasta do MÊS (que carrega
    as subpastas), não sobre a subpasta de entrada.
    """
    from comum.arquivos.estrutura_pastas import (
        caminho_detrafs_recebidos,
        caminho_mes_operadora,
    )

    pasta_mes = caminho_mes_operadora("ALGAR", "202605", raiz_operadoras=tmp_path)
    entrada = caminho_detrafs_recebidos("ALGAR", "202605", raiz_operadoras=tmp_path)

    assert entrada.parent == pasta_mes


# ---------------------------------------------------------------------------
# A quarentena — o outro lugar que o RPA 2 não pode enxergar
# ---------------------------------------------------------------------------


def test_quarentena_fica_fora_da_raiz_das_operadoras():
    """
    Espelho do teste de `_NAO_IDENTIFICADOS`, e por um motivo A MAIS.

    O conhecido: o RPA 2 varre a raiz tratando todo diretório como operadora.

    O outro, mais grave: se a quarentena ficasse lá dentro, o RPA 2 acharia o
    arquivo REPROVADO, o validaria de novo e responderia à operadora uma SEGUNDA
    vez — sobre um arquivo que o RPA 1 já recusou e já avisou.
    """
    from comum.config.configuration import CAMINHO_OPERADORAS, DIRETORIO_QUARENTENA

    raiz = CAMINHO_OPERADORAS.resolve()
    quarentena = DIRETORIO_QUARENTENA.resolve()

    assert raiz not in quarentena.parents
    assert quarentena != raiz


def test_quarentena_e_nao_identificados_sao_pastas_diferentes():
    """
    Os dois significam coisas diferentes, e juntá-los apagaria a distinção que
    orienta quem investiga: em `_NAO_IDENTIFICADOS` o arquivo está íntegro e
    falta cadastro NOSSO; na quarentena o arquivo é que está errado, e a
    operadora já foi avisada.
    """
    from comum.config.configuration import (
        DIRETORIO_NAO_IDENTIFICADOS,
        DIRETORIO_QUARENTENA,
    )

    assert DIRETORIO_QUARENTENA.resolve() != DIRETORIO_NAO_IDENTIFICADOS.resolve()


# ---------------------------------------------------------------------------
# O portão — os dois robôs precisam validar a MESMA coisa
# ---------------------------------------------------------------------------


def test_os_dois_robos_usam_a_mesma_classe_de_validacao():
    """
    A cláusula mais importante do contrato desde 2026-08-06.

    O RPA 1 virou o portão e o RPA 2 virou a rede de segurança. Se cada um
    tivesse a sua cópia da validação, elas divergiriam na primeira correção feita
    de um lado só — e o sintoma seria mudo: arquivos aprovados na captura sendo
    marcados `_ERRO` depois, ou arquivos recusados que o RPA 2 aceitaria.
    """
    import ast

    def _importa_validador(caminho: Path) -> bool:
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.ImportFrom) and no.module:
                nomes = {alias.name for alias in no.names}
                if "ValidadorColunas" in nomes:
                    assert no.module == "comum.dominio.validacao_colunas", (
                        f"{caminho.name} importa ValidadorColunas de "
                        f"'{no.module}' — só pode vir de comum/"
                    )
                    return True
        return False

    rpa1 = _RAIZ / "rpa1_captura" / "src" / "services" / "processamento_service.py"
    rpa2 = (
        _RAIZ
        / "rpa2_validacao_apuracao"
        / "src"
        / "services"
        / "validacao_detrafs.py"
    )

    assert _importa_validador(rpa1), "o RPA 1 deixou de validar"
    assert _importa_validador(rpa2), "o RPA 2 deixou de ser a rede de segurança"


def test_ninguem_importa_o_classificador_do_lugar_antigo():
    """`src/utils/classificadores.py` subiu para `comum/dominio/` e foi apagado."""
    # Montado em pedaços: escrito por extenso, este arquivo se acusaria.
    alvo = "src.utils." + "classificadores"

    culpados = [
        caminho
        for caminho in _RAIZ.rglob("*.py")
        if ".venv" not in caminho.parts
        and caminho != Path(__file__)
        and alvo in caminho.read_text(encoding="utf-8", errors="ignore")
    ]

    assert culpados == []


# ---------------------------------------------------------------------------
# Envio configurável
# ---------------------------------------------------------------------------


def test_envio_desligado_por_padrao():
    from comum.config.configuration import NOTIFICAR_OPERADORA_ENVIAR

    assert NOTIFICAR_OPERADORA_ENVIAR is False


@pytest.mark.parametrize(
    "valor,esperado",
    [
        ("true", True),
        ("True", True),
        ("1", True),
        ("sim", True),
        ("YES", True),
        ("on", True),
        ("false", False),
        ("0", False),
        ("nao", False),
        ("qualquer coisa", False),
    ],
)
def test_leitura_do_flag_de_envio(monkeypatch, valor, esperado):
    import comum.config.configuration as cfg

    monkeypatch.setenv("_FLAG_DE_TESTE", valor)
    assert cfg._flag("_FLAG_DE_TESTE") is esperado


def test_flag_ausente_usa_o_padrao(monkeypatch):
    import comum.config.configuration as cfg

    monkeypatch.delenv("_FLAG_DE_TESTE", raising=False)
    assert cfg._flag("_FLAG_DE_TESTE") is False
    assert cfg._flag("_FLAG_DE_TESTE", padrao=True) is True
