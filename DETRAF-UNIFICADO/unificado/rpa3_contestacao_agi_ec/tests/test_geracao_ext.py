"""Testes da HU-12 — geração do arquivo EXT (T-040..T-043).

Cobre os 3 cenários exigidos por AI/05 §3: sem contestação, SEM retenção, COM retenção.
"""

from pathlib import Path

import pandas as pd
import pytest

from src.services import geracao_ext as ge
from src.services import mapa_remuneracao as mr

INDICE_DESCRITOR_TESTE = 6


def _linha_operadora(credora, devedora, referencia, trafego, descritor, minutos, r_bruto):
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
    """Callable de teste para `obter_tipo_contestacao` (injeção — service não fala com banco)."""

    def __init__(self, respostas: dict[tuple, str | None]):
        self._respostas = respostas

    def __call__(self, eot_operadora, eot_tbra, referencia, trafego, remuneracao):
        return self._respostas.get((eot_operadora, eot_tbra, referencia, trafego, remuneracao))


def test_montar_linhas_ext_vazio_retorna_vazio(indice_remuneracao):
    resultado = ge.montar_linhas_ext(
        pd.DataFrame(), INDICE_DESCRITOR_TESTE, indice_remuneracao, _SinalFake({})
    )
    assert resultado.empty


def test_montar_linhas_ext_cenario_sem_contestacao(indice_remuneracao):
    df = _df([_linha_operadora("021", "011", "202507", "202507", "XPTO_L", "100,0", "10,00")])
    sinal = _SinalFake({})  # nenhuma sinalização => sem contestação

    resultado = ge.montar_linhas_ext(df, INDICE_DESCRITOR_TESTE, indice_remuneracao, sinal)

    linha = resultado.iloc[0]
    assert linha[ge.COL_EXPECTATIVA] == "N"
    assert linha[ge.COL_ORIGEM] == "E"
    assert linha[ge.COL_INSERCAO] == "EXTERNO"
    assert linha[ge.COL_AJUSTE] == ""
    assert linha[ge.COL_OBS] == ""
    assert linha[ge.COL_REMUNERACAO] == "TU-RL"


def test_montar_linhas_ext_cenario_sem_retencao(indice_remuneracao):
    df = _df([_linha_operadora("021", "011", "202507", "202507", "XPTO_V", "100,0", "10,00")])
    sinal = _SinalFake({("021", "011", "202507", "202507", "VU-M"): "sem retenção"})

    resultado = ge.montar_linhas_ext(df, INDICE_DESCRITOR_TESTE, indice_remuneracao, sinal)

    linha = resultado.iloc[0]
    assert linha[ge.COL_EXPECTATIVA] == "N"
    assert linha[ge.COL_REMUNERACAO] == "VU-M"


def test_montar_linhas_ext_cenario_com_retencao(indice_remuneracao):
    df = _df([_linha_operadora("021", "011", "202507", "202507", "XPTO_C", "100,0", "10,00")])
    sinal = _SinalFake({("021", "011", "202507", "202507", "TU-COM"): "com retenção"})

    resultado = ge.montar_linhas_ext(df, INDICE_DESCRITOR_TESTE, indice_remuneracao, sinal)

    linha = resultado.iloc[0]
    assert linha[ge.COL_EXPECTATIVA] == "S"
    assert linha[ge.COL_REMUNERACAO] == "TU-COM"


def test_montar_linhas_ext_descritor_nao_mapeado_mantem_linha(indice_remuneracao):
    # Final 'I' não existe no mapa real — REMUNERACAO fica vazia, mas a linha permanece
    # (diferente do Contest: o EXT cobre TODOS os cenários, nunca descarta).
    df = _df([_linha_operadora("021", "011", "202507", "202507", "2NENI", "100,0", "10,00")])
    sinal = _SinalFake({})

    resultado = ge.montar_linhas_ext(df, INDICE_DESCRITOR_TESTE, indice_remuneracao, sinal)

    assert resultado.shape[0] == 1
    assert pd.isna(resultado.iloc[0][ge.COL_REMUNERACAO])


def test_montar_linhas_ext_mesmo_grupo_compartilha_expectativa(indice_remuneracao):
    # Duas linhas da mesma combinação EOT/referência/tráfego devem ter a mesma EXPECTATIVA.
    df = _df(
        [
            _linha_operadora("021", "011", "202507", "202507", "XPTO_L", "10,0", "1,00"),
            _linha_operadora("021", "011", "202507", "202507", "XPTO_V", "20,0", "2,00"),
        ]
    )
    sinal = _SinalFake(
        {
            ("021", "011", "202507", "202507", "TU-RL"): "com retenção",
            ("021", "011", "202507", "202507", "VU-M"): "com retenção",
        }
    )

    resultado = ge.montar_linhas_ext(df, INDICE_DESCRITOR_TESTE, indice_remuneracao, sinal)

    assert (resultado[ge.COL_EXPECTATIVA] == "S").all()


def test_gerar_arquivo_ext_grava_no_caminho_e_nome_corretos(tmp_path: Path, indice_remuneracao):
    df = _df([_linha_operadora("021", "011", "202507", "202507", "XPTO_L", "10,0", "1,00")])
    linhas_ext = ge.montar_linhas_ext(
        df, INDICE_DESCRITOR_TESTE, indice_remuneracao, _SinalFake({})
    )

    caminho = ge.gerar_arquivo_ext(
        linhas_ext, operadora="Claro", aaaamm="202507", raiz_operadoras=tmp_path
    )

    assert caminho.name == "DE_AGI_D_202507_TBRA_X_CLARO_EXT.xlsx"
    assert caminho.parent == tmp_path / "Claro" / "2025" / "202507" / "AGI"
    assert caminho.is_file()

    # Reabre e confere que o conteúdo essencial foi preservado.
    recarregado = pd.read_excel(caminho, engine="openpyxl", dtype=str)
    assert recarregado.shape[0] == 1
    assert "REMUNERACAO" in recarregado.columns
