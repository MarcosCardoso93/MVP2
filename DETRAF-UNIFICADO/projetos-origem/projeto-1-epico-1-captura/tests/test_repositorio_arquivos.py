import pytest

from src.models.repository.repositorio_arquivos import RepositorioArquivos


@pytest.fixture
def repositorio():
    return RepositorioArquivos()


def test_listar_arquivos_filtra_por_extensao(tmp_path, repositorio):
    (tmp_path / "valido.csv").write_text("a")
    (tmp_path / "valido.xlsx").write_text("b")
    (tmp_path / "invalido.pdf").write_text("c")

    arquivos = repositorio.listar_arquivos(tmp_path)

    nomes = {a.name for a in arquivos}
    assert nomes == {"valido.csv", "valido.xlsx"}


def test_listar_arquivos_diretorio_inexistente_lanca_erro(tmp_path, repositorio):
    with pytest.raises(FileNotFoundError):
        repositorio.listar_arquivos(tmp_path / "nao_existe")


def test_criar_diretorio_idempotente(tmp_path, repositorio):
    destino = tmp_path / "a" / "b"

    repositorio.criar_diretorio(destino)
    repositorio.criar_diretorio(destino)  # não deve lançar erro na segunda vez

    assert destino.is_dir()


def test_copiar_arquivo(tmp_path, repositorio):
    origem = tmp_path / "origem.csv"
    origem.write_text("conteudo")
    destino = tmp_path / "destino" / "copia.csv"
    repositorio.criar_diretorio(destino.parent)

    repositorio.copiar_arquivo(origem, destino)

    assert destino.read_text() == "conteudo"


def test_clonar_estrutura_mes_anterior_com_subpastas(tmp_path, repositorio):
    origem = tmp_path / "202605"
    (origem / "sub1").mkdir(parents=True)
    (origem / "sub2" / "sub2a").mkdir(parents=True)
    destino = tmp_path / "202606"

    repositorio.clonar_estrutura_mes_anterior(origem, destino)

    assert (destino / "sub1").is_dir()
    assert (destino / "sub2" / "sub2a").is_dir()


def test_clonar_estrutura_mes_anterior_nao_copia_arquivos(tmp_path, repositorio):
    origem = tmp_path / "202605"
    origem.mkdir()
    (origem / "arquivo.csv").write_text("x")
    destino = tmp_path / "202606"

    repositorio.clonar_estrutura_mes_anterior(origem, destino)

    assert not (destino / "arquivo.csv").exists()


def test_clonar_estrutura_mes_anterior_origem_inexistente_degrada(tmp_path, repositorio):
    origem = tmp_path / "nao_existe"
    destino = tmp_path / "202606"

    repositorio.clonar_estrutura_mes_anterior(origem, destino)

    assert destino.is_dir()
    assert list(destino.iterdir()) == []
