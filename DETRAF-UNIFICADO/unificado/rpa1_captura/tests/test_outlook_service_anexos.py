"""Filtro de extensão no download de anexos (HU-01).

A V2 é explícita: *"baixar apenas os csv ou excel"*. O filtro por e-mail
(``DetrafEmailFilterService``) só garante que existe **pelo menos um** anexo
csv/Excel — sem um filtro por anexo, PDF, Word e imagens de assinatura eram
baixados junto, ganhavam registro de rastreamento e acabavam copiados para a
pasta de rede da operadora.

O Outlook é substituído por dublês: o COM real exigiria Outlook instalado com
perfil configurado, e o que se quer testar aqui é a regra, não a integração.
"""

from pathlib import Path

import pytest

from comum.config import configuration
from comum.integracoes.outlook import OutlookService


class _AnexoFalso:
    """Dublê de um anexo do Outlook."""

    def __init__(self, nome: str, inline: bool = False):
        self.FileName = nome
        self._inline = inline
        self.salvo_em: Path | None = None

    def SaveAsFile(self, caminho: str) -> None:
        destino = Path(caminho)
        destino.write_text("conteudo", encoding="utf-8")
        self.salvo_em = destino


class _ColecaoAnexos:
    def __init__(self, anexos: list[_AnexoFalso]):
        self._anexos = anexos

    @property
    def Count(self) -> int:
        return len(self._anexos)

    def Item(self, indice: int) -> _AnexoFalso:
        # A coleção do Outlook é 1-based.
        return self._anexos[indice - 1]


class _EmailFalso:
    def __init__(self, anexos: list[_AnexoFalso]):
        self.Attachments = _ColecaoAnexos(anexos)


@pytest.fixture()
def servico(monkeypatch):
    """`OutlookService` sem passar pelo `__init__`, que abriria conexão COM."""
    instancia = OutlookService.__new__(OutlookService)
    monkeypatch.setattr(
        OutlookService, "_is_inline", lambda self, anexo: anexo._inline
    )
    return instancia


def _preparar_namespace(servico, monkeypatch, anexos):
    class _Namespace:
        def GetItemFromID(self, entry_id):
            return _EmailFalso(anexos)

    monkeypatch.setattr(servico, "_ns", _Namespace(), raising=False)


def test_baixa_apenas_csv_e_excel(servico, monkeypatch, tmp_path):
    anexos = [
        _AnexoFalso("DETRAF_ALGAR_202605.csv"),
        _AnexoFalso("planilha.xlsx"),
        _AnexoFalso("carta_apresentacao.pdf"),
        _AnexoFalso("contrato.docx"),
        _AnexoFalso("assinatura.png"),
    ]
    _preparar_namespace(servico, monkeypatch, anexos)

    baixados = servico.download_attachments("ABC123", tmp_path)

    nomes = sorted(caminho.name for caminho in baixados)
    assert nomes == ["DETRAF_ALGAR_202605.csv", "planilha.xlsx"]


def test_anexos_ignorados_nao_chegam_ao_disco(servico, monkeypatch, tmp_path):
    anexos = [
        _AnexoFalso("detraf.csv"),
        _AnexoFalso("carta.pdf"),
    ]
    _preparar_namespace(servico, monkeypatch, anexos)

    servico.download_attachments("ABC123", tmp_path)

    assert (tmp_path / "detraf.csv").exists()
    assert not (tmp_path / "carta.pdf").exists()


def test_anexos_inline_continuam_ignorados(servico, monkeypatch, tmp_path):
    anexos = [
        _AnexoFalso("detraf.csv"),
        _AnexoFalso("logo_rodape.csv", inline=True),
    ]
    _preparar_namespace(servico, monkeypatch, anexos)

    baixados = servico.download_attachments("ABC123", tmp_path)

    assert [caminho.name for caminho in baixados] == ["detraf.csv"]


def test_email_so_com_anexos_irrelevantes_devolve_lista_vazia(
    servico, monkeypatch, tmp_path
):
    """
    Cenário real: o e-mail passou no filtro por causa de um anexo csv, mas o
    robô já o processou antes e agora só restam anexos irrelevantes.
    """
    _preparar_namespace(servico, monkeypatch, [_AnexoFalso("apenas_um_pdf.pdf")])

    assert servico.download_attachments("ABC123", tmp_path) == []


def test_extensao_e_avaliada_sem_distinguir_caixa(servico, monkeypatch, tmp_path):
    anexos = [_AnexoFalso("DETRAF.CSV"), _AnexoFalso("PLANILHA.XLSX")]
    _preparar_namespace(servico, monkeypatch, anexos)

    baixados = servico.download_attachments("ABC123", tmp_path)

    assert len(baixados) == 2


def test_o_filtro_usa_a_configuracao_e_nao_uma_lista_fixa(
    servico, monkeypatch, tmp_path
):
    monkeypatch.setattr(configuration, "EXTENSOES_PERMITIDAS", {".csv"})
    anexos = [_AnexoFalso("detraf.csv"), _AnexoFalso("planilha.xlsx")]
    _preparar_namespace(servico, monkeypatch, anexos)

    baixados = servico.download_attachments("ABC123", tmp_path)

    assert [caminho.name for caminho in baixados] == ["detraf.csv"]
