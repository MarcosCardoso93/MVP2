"""HU-17 e HU-18 — carga no AGI (Projeto 7).

O Projeto 7 veio sem nenhum teste, e **não há ambiente de teste do AGI**
(pendência Q20). Nada aqui toca a interface: o que se cobre é a lista de upload
— que passou a sair da estrutura de pastas real, e não mais de duas pastas
planas — e o kill-switch `PERMITIR_UPLOAD_AGI`, que é o que impede o fluxo de ir
direto para produção.

O `AGI` real nem chega a ser instanciado nos testes de kill-switch: um dublê que
levanta em qualquer chamada prova que nenhum caminho escapa.
"""

from pathlib import Path

import pytest

from comum.arquivos import estrutura_pastas as ep
from comum.config import configuration
from src.services import upload_contestacao_agi as uc
from src.services import upload_detraf_agi as ud


class _AGIProibido:
    """Qualquer toque na interface do AGI é falha de teste."""

    def __getattr__(self, nome):
        def _explodir(*args, **kwargs):
            raise AssertionError(
                f"O AGI foi acionado ('{nome}') com PERMITIR_UPLOAD_AGI desligado."
            )

        return _explodir


@pytest.fixture()
def pasta_agi(raiz_operadoras: Path) -> Path:
    return ep.caminho_agi("CLARO", "202507", raiz_operadoras, criar=True)


@pytest.fixture()
def ext_e_int(pasta_agi: Path) -> tuple[Path, Path]:
    ext = pasta_agi / "DE_AGI_D_202507_TBRA_X_CLARO_EXT.txt"
    interno = pasta_agi / "DE_AGI_D_202507_TBRA_X_CLARO_INT.txt"
    ext.write_text("ext", encoding="utf-8")
    interno.write_text("int", encoding="utf-8")
    return ext, interno


class TestListaDeUpload:
    def test_ext_sobe_antes_do_int(self, raiz_operadoras, ext_e_int):
        """V2, parágrafo 313: um de cada vez, EXT antes de INT."""
        ext, interno = ext_e_int

        pendencias = ud.montar_lista_upload(["CLARO"], "202507", raiz_operadoras)

        assert [caminho for _, caminho in pendencias] == [ext, interno]

    def test_a_operadora_vem_junto_de_cada_arquivo(self, raiz_operadoras, ext_e_int):
        """
        Era o que a versão de pasta plana perdia: sem operadora não há como
        aplicar a regra de cenário, que é por operadora.
        """
        pendencias = ud.montar_lista_upload(["CLARO"], "202507", raiz_operadoras)

        assert {operadora for operadora, _ in pendencias} == {"CLARO"}

    def test_so_ext_quando_nao_ha_int(self, raiz_operadoras, pasta_agi):
        ext = pasta_agi / "DE_AGI_D_202507_TBRA_X_CLARO_EXT.txt"
        ext.write_text("ext", encoding="utf-8")

        pendencias = ud.montar_lista_upload(["CLARO"], "202507", raiz_operadoras)

        assert [caminho for _, caminho in pendencias] == [ext]

    def test_operadora_sem_pasta_nao_quebra(self, raiz_operadoras):
        assert ud.montar_lista_upload(["INEXISTENTE"], "202507", raiz_operadoras) == []

    def test_arquivo_de_outro_tipo_na_pasta_e_ignorado(self, raiz_operadoras, pasta_agi):
        (pasta_agi / "rascunho.xlsx").write_text("x", encoding="utf-8")

        assert ud.montar_lista_upload(["CLARO"], "202507", raiz_operadoras) == []

    def test_varias_operadoras_ficam_agrupadas(self, raiz_operadoras, ext_e_int):
        outra = ep.caminho_agi("ALGAR", "202507", raiz_operadoras, criar=True)
        (outra / "DE_AGI_D_202507_TBRA_X_ALGAR_EXT.txt").write_text("x", encoding="utf-8")

        pendencias = ud.montar_lista_upload(["CLARO", "ALGAR"], "202507", raiz_operadoras)

        assert [operadora for operadora, _ in pendencias] == ["CLARO", "CLARO", "ALGAR"]


class TestListaDeContestacao:
    """
    A HU-18 lê da pasta **AGI** — que é onde a HU-16 grava
    (`geracao_cont_proc.py:263`).

    Este era o ponto do defeito: a versão anterior procurava em ``Contestações``,
    e o teste repetia a mesma suposição errada, então passava. O
    `test_le_da_mesma_pasta_em_que_a_hu16_grava` abaixo existe para não deixar as
    duas pontas divergirem de novo em silêncio.
    """

    def test_encontra_o_cont_proc_da_operadora(self, raiz_operadoras):
        pasta = ep.caminho_agi("CLARO", "202507", raiz_operadoras, criar=True)
        arquivo = pasta / "CONT_PROC_MASCARA_CLARO_202507.xlsx"
        arquivo.write_text("x", encoding="utf-8")

        pendencias = uc.listar_arquivos_contestacao(["CLARO"], "202507", raiz_operadoras)

        assert pendencias == [("CLARO", arquivo)]

    def test_le_da_mesma_pasta_em_que_a_hu16_grava(self, raiz_operadoras):
        """Amarra as duas HUs: o gerador é a autoridade sobre o destino."""
        import pandas as pd

        from src.services import geracao_cont_proc as gcp

        caminho_gravado = gcp.gerar_arquivo_cont_proc(
            linhas_cont_proc=pd.DataFrame([{"EOT": "021", "VALOR": 1.0}]),
            operadora="CLARO",
            aaaamm="202507",
            raiz_operadoras=raiz_operadoras,
        )
        assert caminho_gravado is not None, "a HU-16 precisa ter gravado algo"

        pendencias = uc.listar_arquivos_contestacao(["CLARO"], "202507", raiz_operadoras)

        assert [caminho for _, caminho in pendencias] == [caminho_gravado]

    def test_o_ext_e_o_int_da_mesma_pasta_nao_entram(self, raiz_operadoras):
        """A pasta `AGI` também guarda os arquivos da HU-12 e da HU-13."""
        pasta = ep.caminho_agi("CLARO", "202507", raiz_operadoras, criar=True)
        (pasta / "DE_AGI_D_202507_TBRA_X_CLARO_EXT.xlsx").write_text("x", encoding="utf-8")
        (pasta / "DE_AGI_D_202507_TBRA_X_CLARO_INT.xlsx").write_text("x", encoding="utf-8")

        assert uc.listar_arquivos_contestacao(["CLARO"], "202507", raiz_operadoras) == []

    def test_a_carta_e_o_env_nao_entram(self, raiz_operadoras):
        """A carta e o `_ENV` da HU-14 ficam em `Contestações`, e não são para o AGI."""
        pasta = ep.caminho_contestacoes("CLARO", "202507", raiz_operadoras, criar=True)
        (pasta / "CT - 363.docx").write_text("x", encoding="utf-8")
        (pasta / "Base Contestação_CLARO_202507_ENV.xlsx").write_text("x", encoding="utf-8")

        assert uc.listar_arquivos_contestacao(["CLARO"], "202507", raiz_operadoras) == []


class TestSobraDeExecucaoAnterior:
    """
    A regra de cenário é da HU-13, não desta HU — a V2 diz que "o arquivo final
    INT não chegou nem a ser criado" nos cenários sem retenção. O risco real é
    outro: um `_INT` de um mês em que houve retenção continuar na pasta depois que
    o cenário mudou, e subir indevidamente.
    """

    def test_arquivo_anterior_a_execucao_e_descartado(
        self, raiz_operadoras, ext_e_int
    ):
        import os
        import time

        ext, interno = ext_e_int
        inicio_da_execucao = time.time()
        # O EXT é desta execução; o INT ficou de uma rodada anterior.
        os.utime(ext, (inicio_da_execucao + 1, inicio_da_execucao + 1))
        os.utime(interno, (inicio_da_execucao - 3600, inicio_da_execucao - 3600))

        pendencias = ud.montar_lista_upload(
            ["CLARO"], "202507", raiz_operadoras, desde=inicio_da_execucao
        )

        assert [caminho for _, caminho in pendencias] == [ext]

    def test_o_descarte_e_anunciado(self, raiz_operadoras, ext_e_int, caplog):
        import os
        import time

        agora = time.time()
        for caminho in ext_e_int:
            os.utime(caminho, (agora - 3600, agora - 3600))

        with caplog.at_level("WARNING"):
            ud.montar_lista_upload(["CLARO"], "202507", raiz_operadoras, desde=agora)

        assert "sobra de uma rodada passada" in caplog.text

    def test_sem_o_parametro_a_guarda_fica_desligada(self, raiz_operadoras, ext_e_int):
        """O default é listar o que está lá — quem orquestra é que passa `desde`."""
        assert len(ud.montar_lista_upload(["CLARO"], "202507", raiz_operadoras)) == 2


class TestRegistroDaCarga:
    """
    A V2 exige, logo após o Salvar: *"O robô atualiza o campo 'carga_agi' com o
    status da carga"*. Não existia método para isso — o RPA 2 gravava "não
    carregado" e ninguém tocava no campo depois.
    """

    class _RepositorioEspiao:
        def __init__(self):
            self.chamadas = []

        def atualizar_carga_agi(self, operadora, referencia, status):
            self.chamadas.append((operadora, referencia, status))
            return 1

    def test_upload_bem_sucedido_grava_carregado(self, monkeypatch):
        monkeypatch.setattr(configuration, "PERMITIR_UPLOAD_AGI", True)
        espiao = self._RepositorioEspiao()
        servico = uc.UploadContestacaoAGI(agi=_AGIMudo(), repositorio=espiao)
        monkeypatch.setattr(servico, "upload_um_arquivo", lambda caminho: None)
        monkeypatch.setattr(servico, "navegar_contestacao_gerenciar", lambda: None)
        monkeypatch.setattr(uc, "capturar_evidencia_sucesso", lambda *a, **k: None)
        monkeypatch.setattr(
            uc, "listar_arquivos_contestacao",
            lambda *a, **k: [("CLARO", Path("CONT_PROC_MASCARA_CLARO_202507.xlsx"))],
        )

        servico.executar(["CLARO"], "202507")

        assert espiao.chamadas == [("CLARO", "202507", uc.CARGA_AGI_CARREGADO)]

    def test_falha_no_upload_grava_erro_em_vez_de_deixar_nao_carregado(
        self, monkeypatch
    ):
        """
        "erro na carga" é informação; deixar "não carregado" faria a falha
        parecer uma execução que nunca aconteceu.
        """
        monkeypatch.setattr(configuration, "PERMITIR_UPLOAD_AGI", True)
        espiao = self._RepositorioEspiao()
        servico = uc.UploadContestacaoAGI(agi=_AGIMudo(), repositorio=espiao)

        def _explodir(caminho):
            raise RuntimeError("botão Salvar não apareceu")

        monkeypatch.setattr(servico, "upload_um_arquivo", _explodir)
        monkeypatch.setattr(servico, "navegar_contestacao_gerenciar", lambda: None)
        monkeypatch.setattr(
            uc, "listar_arquivos_contestacao",
            lambda *a, **k: [("CLARO", Path("CONT_PROC_MASCARA_CLARO_202507.xlsx"))],
        )

        servico.executar(["CLARO"], "202507")

        assert espiao.chamadas == [("CLARO", "202507", uc.CARGA_AGI_ERRO)]

    def test_banco_fora_nao_derruba_o_lote(self, monkeypatch, caplog):
        """O upload já aconteceu no AGI e não se desfaz — abortar aqui é pior."""
        monkeypatch.setattr(configuration, "PERMITIR_UPLOAD_AGI", True)

        class _RepositorioQuebrado:
            def atualizar_carga_agi(self, *a, **k):
                raise RuntimeError("conexão recusada")

        servico = uc.UploadContestacaoAGI(
            agi=_AGIMudo(), repositorio=_RepositorioQuebrado()
        )
        monkeypatch.setattr(servico, "upload_um_arquivo", lambda caminho: None)
        monkeypatch.setattr(servico, "navegar_contestacao_gerenciar", lambda: None)
        monkeypatch.setattr(uc, "capturar_evidencia_sucesso", lambda *a, **k: None)
        monkeypatch.setattr(
            uc, "listar_arquivos_contestacao",
            lambda *a, **k: [("CLARO", Path("CONT_PROC.xlsx"))],
        )

        with caplog.at_level("ERROR"):
            servico.executar(["CLARO"], "202507")

        assert "fora de sincronia" in caplog.text


class _AGIMudo:
    """Dublê que aceita qualquer chamada de interface sem fazer nada."""

    def __getattr__(self, nome):
        return lambda *args, **kwargs: None


class TestKillSwitch:
    def test_hu17_nao_abre_o_agi_com_o_switch_desligado(
        self, raiz_operadoras, ext_e_int, monkeypatch
    ):
        monkeypatch.setattr(configuration, "PERMITIR_UPLOAD_AGI", False)

        ud.UploadDetrafAGI(agi=_AGIProibido()).executar(
            ["CLARO"], "202507", raiz_operadoras
        )

    def test_hu18_nao_abre_o_agi_com_o_switch_desligado(
        self, raiz_operadoras, monkeypatch
    ):
        monkeypatch.setattr(configuration, "PERMITIR_UPLOAD_AGI", False)
        pasta = ep.caminho_contestacoes("CLARO", "202507", raiz_operadoras, criar=True)
        (pasta / "CONT_PROC_MASCARA_CLARO_202507.xlsx").write_text("x", encoding="utf-8")

        uc.UploadContestacaoAGI(agi=_AGIProibido()).executar(
            ["CLARO"], "202507", raiz_operadoras
        )

    def test_sem_pendencia_o_agi_nao_e_aberto_nem_com_o_switch_ligado(
        self, raiz_operadoras, monkeypatch
    ):
        """Abrir o AGI custa minutos; não se abre para não subir nada."""
        monkeypatch.setattr(configuration, "PERMITIR_UPLOAD_AGI", True)

        ud.UploadDetrafAGI(agi=_AGIProibido()).executar(
            ["CLARO"], "202507", raiz_operadoras
        )


class TestEvidencia:
    def test_sem_diretorio_configurado_nao_grava_e_nao_quebra(self, monkeypatch):
        monkeypatch.setattr(configuration, "DIRETORIO_EVIDENCIAS", None)

        assert ud.capturar_evidencia_sucesso("arquivo") is None

    def test_falha_na_captura_nao_derruba_o_upload(self, tmp_path, monkeypatch):
        """A evidência é desejável; o upload já aconteceu e não se desfaz."""
        monkeypatch.setattr(configuration, "DIRETORIO_EVIDENCIAS", tmp_path / "evidencias")
        monkeypatch.setattr(
            ud.pyautogui,
            "screenshot",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("sem display")),
        )

        assert ud.capturar_evidencia_sucesso("arquivo") is None


class TestImagensDeReferencia:
    """As imagens são artefatos versionados: um caminho errado só apareceria na VM."""

    @pytest.mark.parametrize(
        "caminho",
        [
            ud.img_bnt_detraf,
            ud.img_bnt_submenu_importar_dados,
            ud.img_bnt_upload,
            uc.img_bnt_contestacao,
            uc.img_bnt_submenu_gerenciar,
            uc.img_bnt_upload_contestacao,
            uc.img_bnt_salvar_contestacao,
        ],
    )
    def test_imagem_existe_no_repositorio(self, caminho):
        assert Path(caminho).is_file(), f"Imagem ausente: {caminho}"
