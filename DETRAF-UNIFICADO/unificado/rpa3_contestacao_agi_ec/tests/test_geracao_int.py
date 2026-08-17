"""Testes da HU-13 — geração do arquivo INT (T-060..T-062).

Critério central: o INT **só existe** no cenário COM retenção. Nos demais (sem
contestação, SEM retenção), nenhum arquivo é criado (AI/09 §3, matriz §0).
"""

from pathlib import Path

import pandas as pd
import pytest

from src.services import geracao_int as gi
from src.services import mapa_remuneracao as mr

INDICE_DESCRITOR_TESTE = 6


def _linha_tbra(credora, devedora, referencia, trafego, descritor, minutos, r_bruto):
    linha = ["0"] * 15
    linha[0] = credora
    linha[1] = devedora
    linha[2] = referencia
    linha[3] = trafego
    linha[6] = descritor
    linha[9] = minutos
    linha[14] = r_bruto
    return linha


def _df(linhas: list[list[str]]) -> pd.DataFrame:
    return pd.DataFrame(linhas)


class _SinalFake:
    def __init__(self, respostas: dict[tuple, str | None]):
        self._respostas = respostas

    def __call__(self, eot_operadora, eot_tbra, referencia, trafego, remuneracao):
        return self._respostas.get((eot_operadora, eot_tbra, referencia, trafego, remuneracao))


def test_montar_linhas_int_vazio_retorna_vazio(indice_remuneracao):
    resultado = gi.montar_linhas_int(
        pd.DataFrame(), INDICE_DESCRITOR_TESTE, indice_remuneracao, _SinalFake({})
    )
    assert resultado.empty


def test_montar_linhas_int_cenario_sem_contestacao_fica_vazio(indice_remuneracao):
    df = _df([_linha_tbra("021", "011", "202507", "202507", "XPTO_L", "100,0", "10,00")])
    sinal = _SinalFake({})  # nenhuma sinalização

    resultado = gi.montar_linhas_int(df, INDICE_DESCRITOR_TESTE, indice_remuneracao, sinal)

    assert resultado.empty


def test_montar_linhas_int_cenario_sem_retencao_fica_vazio(indice_remuneracao):
    df = _df([_linha_tbra("021", "011", "202507", "202507", "XPTO_L", "100,0", "10,00")])
    sinal = _SinalFake({("021", "011", "202507", "202507", "TU-RL"): "sem retenção"})

    resultado = gi.montar_linhas_int(df, INDICE_DESCRITOR_TESTE, indice_remuneracao, sinal)

    assert resultado.empty


def test_montar_linhas_int_cenario_com_retencao_preenche_linhas(indice_remuneracao):
    df = _df([_linha_tbra("021", "011", "202507", "202507", "XPTO_C", "100,0", "10,00")])
    sinal = _SinalFake({("021", "011", "202507", "202507", "TU-COM"): "com retenção"})

    resultado = gi.montar_linhas_int(df, INDICE_DESCRITOR_TESTE, indice_remuneracao, sinal)

    assert resultado.shape[0] == 1
    linha = resultado.iloc[0]
    assert linha[gi.COL_EXPECTATIVA] == "N"  # fixo, não calculado
    assert linha[gi.COL_ORIGEM] == "E"
    assert linha[gi.COL_INSERCAO] == "EXTERNO"
    assert linha[gi.COL_REMUNERACAO] == "TU-COM"


def test_montar_linhas_int_filtra_apenas_com_retencao(indice_remuneracao):
    df = _df(
        [
            _linha_tbra("021", "011", "202507", "202507", "XPTO_L", "10,0", "1,00"),  # SEM
            _linha_tbra("022", "012", "202507", "202507", "XPTO_V", "20,0", "2,00"),  # COM
        ]
    )
    sinal = _SinalFake(
        {
            ("021", "011", "202507", "202507", "TU-RL"): "sem retenção",
            ("022", "012", "202507", "202507", "VU-M"): "com retenção",
        }
    )

    resultado = gi.montar_linhas_int(df, INDICE_DESCRITOR_TESTE, indice_remuneracao, sinal)

    assert resultado.shape[0] == 1
    assert resultado.iloc[0, 0] == "022"


def test_gerar_arquivo_int_nao_grava_quando_vazio(tmp_path: Path):
    caminho = gi.gerar_arquivo_int(pd.DataFrame(), operadora="Claro", aaaamm="202507", raiz_operadoras=tmp_path)
    assert caminho is None
    assert not any(tmp_path.rglob("*.xlsx"))


def test_gerar_arquivo_int_grava_no_caminho_e_nome_corretos(tmp_path: Path, indice_remuneracao):
    df = _df([_linha_tbra("021", "011", "202507", "202507", "XPTO_L", "10,0", "1,00")])
    sinal = _SinalFake({("021", "011", "202507", "202507", "TU-RL"): "com retenção"})
    linhas_int = gi.montar_linhas_int(df, INDICE_DESCRITOR_TESTE, indice_remuneracao, sinal)

    caminho = gi.gerar_arquivo_int(
        linhas_int, operadora="Claro", aaaamm="202507", raiz_operadoras=tmp_path
    )

    assert caminho.name == "DE_AGI_D_202507_TBRA_X_CLARO_INT.xlsx"
    assert caminho.parent == tmp_path / "Claro" / "2025" / "202507" / "AGI"
    assert caminho.is_file()
