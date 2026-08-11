"""Validação do layout dos arquivos de Detraf.

Os casos que importam são exercitados contra as **fixtures reais** do Projeto 4,
derivadas de arquivos de produção — é a única massa disponível com as variações
que existem de verdade: com e sem cabeçalho, vírgula e ponto e vírgula, decimal
com vírgula e com zero-padding.
"""

from pathlib import Path

import pandas as pd
import pytest

from comum.arquivos.gerenciador import carregar_dados
from comum.dominio.layout_detraf import (
    COLUNAS_MINIMAS,
    ResultadoLayout,
    validar_layout,
)

_RAIZ = Path(__file__).resolve().parents[2]
_FIXTURES = (
    _RAIZ / "projetos-origem" / "projeto-4-epico-4-h19" / "tests" / "fixtures"
)

pytestmark = pytest.mark.skipif(
    not _FIXTURES.is_dir(), reason="fixtures do Projeto 4 não disponíveis"
)


# ---------------------------------------------------------------------------
# Arquivos reais
# ---------------------------------------------------------------------------


def test_arquivo_da_operadora_com_cabecalho_e_conforme():
    """ALGAR STFC: ponto e vírgula, com cabeçalho, 18 colunas."""
    df = carregar_dados(_FIXTURES / "detraf" / "algar_stfc_reduzido.csv")

    resultado = validar_layout(df)

    assert resultado.conforme, resultado.mensagem()
    assert resultado.total_colunas == 18


def test_arquivo_da_operadora_sem_cabecalho_e_conforme():
    """ALGAR SMP: vírgula, sem cabeçalho, decimais entre aspas com vírgula."""
    df = carregar_dados(_FIXTURES / "detraf" / "algar_smp_reduzido.csv")

    resultado = validar_layout(df)

    assert resultado.conforme, resultado.mensagem()


def test_colunas_extras_a_direita_sao_aceitas():
    """
    A V2 documenta 15 colunas; a ALGAR entrega 18. As 3 extras no fim são
    aceitas — a regra é "no mínimo 15", usando as 15 primeiras.
    """
    df = carregar_dados(_FIXTURES / "detraf" / "algar_stfc_reduzido.csv")

    assert df.shape[1] > COLUNAS_MINIMAS
    assert validar_layout(df).conforme


# ---------------------------------------------------------------------------
# O caso que motivou esta camada
# ---------------------------------------------------------------------------


def test_expectativa_vivo_e_rejeitada():
    """
    O arquivo de expectativa Vivo tem layout próprio e não conforma com a V2.

    Antes desta validação ele passava direto e era lido por posição: o código
    pegava o índice 14 achando que era `R$_Bruto` e recebia MINUTOS_TARIFADOS —
    a comparação que decide a contestação saía de dados desalinhados, em
    silêncio.
    """
    df = carregar_dados(_FIXTURES / "expectativa" / "vivo_d_reduzido.csv")

    resultado = validar_layout(df)

    assert not resultado.conforme


def test_a_rejeicao_da_expectativa_aponta_as_posicoes_erradas():
    """A mensagem precisa dizer O QUE se esperava e O QUE veio, por posição."""
    caminho = _FIXTURES / "expectativa" / "vivo_d_reduzido.csv"
    resultado = validar_layout(carregar_dados(caminho))

    indices = {divergencia.indice for divergencia in resultado.divergencias}

    # O descritor caiu na posição do GH, e o Rel na do descritor.
    assert 6 in indices  # DESC recebeu o Rel
    assert 7 in indices  # GH recebeu PARTE_TARIFADA
    assert 8 in indices  # Chamadas recebeu o descritor

    mensagem = resultado.mensagem(caminho)
    assert "vivo_d_reduzido.csv" in mensagem
    assert "GH" in mensagem
    assert "esperado" in mensagem


def test_a_rejeicao_da_expectativa_traz_o_diagnostico():
    """
    Reconhecer o layout de expectativa poupa quem opera de investigar do zero —
    e diz onde está a causa real (a geração no ICT).
    """
    df = carregar_dados(_FIXTURES / "expectativa" / "vivo_d_reduzido.csv")

    mensagem = validar_layout(df).mensagem()

    assert "expectativa Vivo" in mensagem
    assert "R$_Bruto" in mensagem
    assert "ICT" in mensagem


# ---------------------------------------------------------------------------
# Contagem de colunas
# ---------------------------------------------------------------------------


def test_arquivo_curto_demais_e_rejeitado():
    df = pd.DataFrame([["a"] * 10])

    resultado = validar_layout(df)

    assert not resultado.conforme
    assert "ao menos 15" in resultado.motivo


def test_arquivo_vazio_e_rejeitado():
    resultado = validar_layout(pd.DataFrame())

    assert not resultado.conforme
    assert "vazio" in resultado.motivo


def test_dataframe_nulo_e_rejeitado():
    assert not validar_layout(None).conforme


# ---------------------------------------------------------------------------
# Tolerância a linha ruim
#
# Um arquivo com algumas linhas sujas não está no layout errado — essas linhas
# são separadas depois, pela validação por coluna, e vão para o `_ERRO`.
# ---------------------------------------------------------------------------


def _linha_valida():
    return [
        "025",  # 0 Credora
        "010",  # 1 Devedora
        "202605",  # 2 Referencia
        "202603",  # 3 Tráfego
        "SPOX_1007",  # 4 POI
        "0",  # 5 Rel
        "LENL",  # 6 DESC
        "N",  # 7 GH
        "1",  # 8 Chamadas
        "2",  # 9 Minutos
        "0,00631",  # 10 Tarifa
        "0,01",  # 11 R$_Liq
        "0",  # 12 PIS_Cofins
        "0",  # 13 ICMS
        "0,01",  # 14 R$_Bruto
    ]


def test_poucas_linhas_ruins_nao_reprovam_o_layout():
    linhas = [_linha_valida() for _ in range(9)]
    ruim = _linha_valida()
    ruim[7] = "XPTO"  # GH inválido numa única linha
    linhas.append(ruim)

    assert validar_layout(pd.DataFrame(linhas)).conforme


def test_maioria_das_linhas_ruins_reprova_o_layout():
    linhas = []
    for indice in range(10):
        linha = _linha_valida()
        if indice < 6:
            linha[7] = "XPTO"
        linhas.append(linha)

    resultado = validar_layout(pd.DataFrame(linhas))

    assert not resultado.conforme
    assert any(d.indice == 7 for d in resultado.divergencias)


# ---------------------------------------------------------------------------
# Formatos numéricos reais
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tarifa", ["0,00631", "0.00631", ".00787", "000000.061386", "0"])
def test_formatos_numericos_aceitos(tarifa):
    """
    Vírgula decimal (ALGAR), ponto, parte inteira ausente (`.00787`, que aparece
    no arquivo Vivo) e zero-padding — todos são números válidos.
    """
    linha = _linha_valida()
    linha[10] = tarifa

    assert validar_layout(pd.DataFrame([linha] * 5)).conforme


def test_eot_vinda_de_excel_como_float_e_aceita():
    """Lendo de Excel, uma EOT chega como `11.0`."""
    linha = _linha_valida()
    linha[0] = "11.0"

    assert validar_layout(pd.DataFrame([linha] * 5)).conforme


def test_rel_vazia_e_aceita():
    """A V2 diz que a coluna Rel pode estar vazia."""
    linha = _linha_valida()
    linha[5] = ""

    assert validar_layout(pd.DataFrame([linha] * 5)).conforme


def test_poi_livre_nao_e_validada():
    """A coluna POI é de escrita livre e preenchimento não obrigatório."""
    linha = _linha_valida()
    linha[4] = "qualquer coisa !@#"

    assert validar_layout(pd.DataFrame([linha] * 5)).conforme


# ---------------------------------------------------------------------------
# Mensagem
# ---------------------------------------------------------------------------


def test_mensagem_de_layout_conforme():
    resultado = ResultadoLayout(conforme=True, total_colunas=15)

    assert "conforme" in resultado.mensagem().lower()


def test_descritor_precisa_conter_letra():
    """
    É o que separa um descritor (`LENL`, `_NSN5`) de um número que caiu ali por
    o layout estar deslocado.
    """
    linha = _linha_valida()
    linha[6] = "0"

    resultado = validar_layout(pd.DataFrame([linha] * 5))

    assert not resultado.conforme
    assert any(d.indice == 6 for d in resultado.divergencias)


class TestGrafiaDoCabecalhoNaoImporta:
    """
    Resposta à hipótese levantada em 2026-08-05 sobre a **N3**.

    A sugestão era que a rejeição da expectativa Vivo pudesse ser só
    normalização de nome: a V2 escreve a mesma coluna de duas formas —
    ``R$_Bruto`` no layout de 15 colunas e ``R$ Bruto`` ao descrever a cópia do
    arquivo —, e um parser que casasse por nome falharia com a grafia errada.

    **Não é o caso aqui.** A validação de layout é **posicional** e descarta o
    cabeçalho antes de olhar qualquer coisa (decisão do cliente, 2026-07-31: os
    nomes reais não batem com os da V2 e variam por operadora). Os nomes em
    ``LAYOUT_V2`` são rótulo de mensagem de erro, não critério.

    Ou seja: normalizar ``_`` e espaço não mudaria nada. A N3 continua sendo o
    que estava registrado — o arquivo tem **uma coluna a mais no início**
    (GROUP_CREDORA) e **outra no meio** (PARTE_TARIFADA), o que desloca tudo, e
    **termina em VALOR_LIQUIDO**, sem coluna de valor bruto alguma.

    Estes testes existem para que a hipótese não volte: se alguém introduzir
    casamento por nome de coluna, eles falham.
    """

    def test_cabecalho_com_espaco_ou_underscore_da_no_mesmo(self):
        """As duas grafias da V2 produzem o mesmo veredito."""
        linhas = [_linha_valida() for _ in range(3)]

        com_underscore = pd.DataFrame(linhas)
        com_underscore.columns = [f"col_{i}" for i in range(com_underscore.shape[1])]

        com_espaco = pd.DataFrame(linhas)
        com_espaco.columns = [f"col {i}" for i in range(com_espaco.shape[1])]

        assert (
            validar_layout(com_underscore).conforme
            == validar_layout(com_espaco).conforme
        )

    def test_nome_de_coluna_sem_nenhuma_relacao_nao_reprova(self):
        """
        O critério é a **forma do valor na posição**, não o rótulo. Um arquivo
        com colunas chamadas `a`, `b`, `c` e conteúdo certo é conforme.
        """
        df = pd.DataFrame([_linha_valida() for _ in range(3)])
        df.columns = [f"nome_irrelevante_{i}" for i in range(df.shape[1])]

        assert validar_layout(df).conforme is True
