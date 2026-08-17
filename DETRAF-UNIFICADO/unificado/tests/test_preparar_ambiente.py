"""O script que monta o ambiente de homologação (2026-08-07).

Não existia nada que criasse a árvore de pastas: o `resetar_homologacao.py` só
apaga artefatos. A estrutura era montada à mão, e por isso a primeira execução
sempre esbarrava numa pasta faltando — no meio do fluxo, depois de o robô já ter
aberto o Outlook ou o AGI.

O que estes testes protegem é o roteamento dos insumos, que tem uma armadilha
real, e a decisão de **não** adivinhar a operadora.
"""

import sys
from pathlib import Path

import pytest

_RAIZ = Path(__file__).resolve().parents[1]
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

import preparar_ambiente as pa


class TestRoteamentoDaExpectativa:
    """
    O campo que decide a pasta é o **penúltimo** do nome:

        DETRAF_FINAL_VIVO_202603_N_ALGAR_SMP_VIVO_D.csv  ->  Vivo
        DETRAF_FINAL_VIVO_202603_N_ALGAR_STF_TLF_D.csv   ->  TLF
    """

    PASTAS = ["Vivo", "TLF"]

    def test_arquivo_da_vivo_vai_para_vivo(self):
        assert (
            pa._pasta_de_expectativa(
                "DETRAF_FINAL_VIVO_202603_N_ALGAR_SMP_VIVO_D.csv", self.PASTAS
            )
            == "Vivo"
        )

    def test_arquivo_da_tlf_vai_para_tlf(self):
        """
        🔴 Regressão. `VIVO` aparece também no COMEÇO de todos os nomes
        (`DETRAF_FINAL_VIVO_...`), e a primeira versão procurava do início — o
        que mandava os arquivos da TLF para a pasta da Vivo. A varredura é de
        trás para frente por causa disto.
        """
        assert (
            pa._pasta_de_expectativa(
                "DETRAF_FINAL_VIVO_202603_N_ALGAR_STF_TLF_D.csv", self.PASTAS
            )
            == "TLF"
        )

    def test_devolve_a_grafia_configurada_e_nao_a_do_arquivo(self):
        """O `.env` diz `Vivo`; o arquivo diz `VIVO`. A pasta é a do `.env`."""
        assert (
            pa._pasta_de_expectativa("X_202603_VIVO_D.csv", ["Vivo"]) == "Vivo"
        )

    def test_nome_sem_nenhuma_das_pastas_nao_e_roteado(self):
        """Melhor deixar de fora, e dizer, do que chutar uma pasta."""
        assert pa._pasta_de_expectativa("QUALQUER_COISA.csv", self.PASTAS) is None


class TestSemeadura:
    @pytest.fixture()
    def ambiente(self, tmp_path, monkeypatch):
        from comum.config import configuration

        origem = tmp_path / "Insumos"
        (origem / "Detrafs recebidos").mkdir(parents=True)
        (origem / "Expectativa").mkdir(parents=True)
        (origem / "Detrafs recebidos" / "DETRAT_ALGAR_202603.csv").write_text(
            "x", encoding="utf-8"
        )
        (origem / "Expectativa" / "DETRAF_FINAL_VIVO_202603_ALGAR_VIVO_D.csv").write_text(
            "y", encoding="utf-8"
        )

        monkeypatch.setattr(configuration, "DIRETORIO_ENTRADA", tmp_path / "Entrada")
        monkeypatch.setattr(
            configuration, "CAMINHO_EXPECTATIVA_DETRAF", tmp_path / "Expectativa"
        )
        monkeypatch.setattr(configuration, "PASTAS_EXPECTATIVAS", ["Vivo", "TLF"])
        monkeypatch.setattr(configuration, "EXPECTATIVA_SUBSTRING", ["_D"])
        return configuration, origem, tmp_path

    def test_o_detraf_vai_para_a_ENTRADA(self, ambiente):
        """
        E **não** para a árvore da operadora. Pôr o arquivo direto em
        `{operadora}/{ano}/{aaaamm}/Detrafs Recebidos/` exigiria descobrir a
        operadora aqui — que é a HU-02, e já existe no RPA 1. Uma segunda
        implementação seria a segunda fonte de verdade que este repositório já
        pagou duas vezes.
        """
        cfg, origem, tmp_path = ambiente

        pa._semear(cfg, origem)

        assert (tmp_path / "Entrada" / "DETRAT_ALGAR_202603.csv").is_file()

    def test_a_expectativa_vai_para_a_subpasta_certa(self, ambiente):
        cfg, origem, tmp_path = ambiente

        pa._semear(cfg, origem)

        assert (
            tmp_path
            / "Expectativa"
            / "Vivo"
            / "DETRAF_FINAL_VIVO_202603_ALGAR_VIVO_D.csv"
        ).is_file()

    def test_nao_sobrescreve_o_que_ja_esta_la(self, ambiente):
        """
        O uso normal é rodar antes de cada rodada, sem lembrar se já rodou. Um
        arquivo já semeado pode ter sido editado à mão para provocar um cenário.
        """
        cfg, origem, tmp_path = ambiente
        destino = tmp_path / "Entrada" / "DETRAT_ALGAR_202603.csv"
        destino.parent.mkdir(parents=True)
        destino.write_text("editado à mão", encoding="utf-8")

        linhas = pa._semear(cfg, origem)

        assert destino.read_text(encoding="utf-8") == "editado à mão"
        assert any("já estava lá" in linha for linha in linhas)

    def test_acusa_quando_o_filtro_nao_casa_com_nenhum_arquivo(self, ambiente):
        """
        🔴 A armadilha que motivou o aviso: com `EXPECTATIVA_SUBSTRING` errada, o
        RPA 2 encontra ZERO arquivos, registra um aviso e **termina com
        sucesso** — o batimento compara o Detraf com o nada.

        Aconteceu de verdade: `_D_` (o da V2) não casa com nenhum dos arquivos
        reais, que terminam em `_D.csv`.
        """
        cfg, origem, _ = ambiente
        cfg.EXPECTATIVA_SUBSTRING = ["_XYZ_"]

        linhas = "\n".join(pa._semear(cfg, origem))

        assert "NENHUM arquivo de expectativa casa" in linhas
        assert "TERMINAR COM SUCESSO" in linhas

    def test_pasta_de_origem_sem_as_subpastas_nao_estoura(self, ambiente, tmp_path):
        cfg, _, _ = ambiente
        vazia = tmp_path / "vazia"
        vazia.mkdir()

        linhas = "\n".join(pa._semear(cfg, vazia))

        assert "sem pasta 'Detrafs recebidos'" in linhas
        assert "sem pasta 'Expectativa'" in linhas
