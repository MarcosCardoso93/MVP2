from pathlib import Path

from src.utils.filesystem import construir_caminho_saida, formatar_tamanho, mes_anterior


def test_mes_anterior_mes_normal():
    assert mes_anterior("202506") == "202505"


def test_mes_anterior_virada_de_ano():
    assert mes_anterior("202601") == "202512"


def test_construir_caminho_saida():
    caminho = construir_caminho_saida(Path("Saida"), "Vivo", "2026", "202605")

    assert caminho == Path("Saida") / "Vivo" / "2026" / "202605"


def test_formatar_tamanho_bytes():
    assert formatar_tamanho(500) == "500.00 B"


def test_formatar_tamanho_kb():
    assert formatar_tamanho(1024) == "1.00 KB"


def test_formatar_tamanho_mb():
    assert formatar_tamanho(1_048_576) == "1.00 MB"
