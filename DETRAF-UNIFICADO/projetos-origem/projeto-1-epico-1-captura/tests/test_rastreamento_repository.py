from pathlib import Path

from src.models.dto.registro_rastreamento import RegistroRastreamento
from src.models.repository.rastreamento_repository import RastreamentoRepository


def _repositorio(tmp_path):
    return RastreamentoRepository(tmp_path / "rastreamento.json")


def test_registrar_e_buscar_por_arquivo(tmp_path):
    repo = _repositorio(tmp_path)
    caminho = Path("C:/entrada/arquivo.csv")

    repo.registrar(RegistroRastreamento(
        caminho_arquivo=str(caminho),
        entry_id="E1",
        subject="Assunto",
        sender_email="a@b.com",
        received_at=None,
    ))

    registro = repo.buscar_por_arquivo(caminho)
    assert registro is not None
    assert registro.entry_id == "E1"


def test_buscar_por_arquivo_inexistente_retorna_none(tmp_path):
    repo = _repositorio(tmp_path)

    assert repo.buscar_por_arquivo(Path("C:/nao/existe.csv")) is None


def test_existe_entry_id(tmp_path):
    repo = _repositorio(tmp_path)
    repo.registrar(RegistroRastreamento(
        caminho_arquivo="C:/entrada/arquivo.csv",
        entry_id="E1",
        subject="",
        sender_email="a@b.com",
        received_at=None,
    ))

    assert repo.existe_entry_id("E1") is True
    assert repo.existe_entry_id("E2") is False


def test_registrar_mesmo_caminho_atualiza_sem_duplicar(tmp_path):
    repo = _repositorio(tmp_path)
    caminho = Path("C:/entrada/arquivo.csv")

    repo.registrar(RegistroRastreamento(
        caminho_arquivo=str(caminho), entry_id="E1", subject="", sender_email="a@b.com", received_at=None,
    ))
    repo.registrar(RegistroRastreamento(
        caminho_arquivo=str(caminho), entry_id="E2", subject="", sender_email="a@b.com", received_at=None,
    ))

    assert len(repo._carregar()) == 1
    assert repo.buscar_por_arquivo(caminho).entry_id == "E2"
