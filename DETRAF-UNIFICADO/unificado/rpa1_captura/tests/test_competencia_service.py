from datetime import datetime

from comum.config import configuration
from comum.dominio import competencia as competencia_comum
from src.services.competencia_service import CompetenciaService


def test_competencia_mes_normal(monkeypatch):
    monkeypatch.setattr(configuration, "COMPETENCIA", "202606")

    resultado = CompetenciaService.obter_competencia()

    assert resultado.ano == "2026"
    assert resultado.competencia == "202605"


def test_competencia_virada_de_ano(monkeypatch):
    monkeypatch.setattr(configuration, "COMPETENCIA", "202601")

    resultado = CompetenciaService.obter_competencia()

    assert resultado.ano == "2025"
    assert resultado.competencia == "202512"


def test_competencia_sem_env_usa_data_atual(monkeypatch):
    monkeypatch.setattr(configuration, "COMPETENCIA", "")

    class DataFixa(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 3, 15)

    # O cálculo mudou de lugar na unificação: saiu de `src.services.
    # competencia_service` para `comum.dominio.competencia` (duplicação D-17).
    # O `datetime` a substituir é o do módulo comum.
    monkeypatch.setattr(competencia_comum, "datetime", DataFixa)

    resultado = CompetenciaService.obter_competencia()

    assert resultado.ano == "2026"
    assert resultado.competencia == "202602"
