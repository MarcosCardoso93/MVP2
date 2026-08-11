"""A garantia de que o insumo não é tocado.

🔴 Estes testes existem por causa de 2026-08-10: a primeira execução ponta a
ponta do RPA 2 reduziu os quatro arquivos de expectativa ao cabeçalho. A
validação regrava o arquivo com as linhas que passaram, nenhuma passou — o banco
estava com uma coluna fora do lugar —, e o insumo foi destruído por um problema
que não tinha nada a ver com ele.

O que cada teste aqui cobre é uma das três coisas que precisam valer juntas:
o original não muda, o artefato volta, e a cópia de trabalho **não** volta.
"""

from pathlib import Path

import pytest

from comum.arquivos.area_de_trabalho import AreaDeTrabalho


@pytest.fixture
def insumo(tmp_path: Path) -> Path:
    origem = tmp_path / "Expectativa" / "Vivo"
    origem.mkdir(parents=True)
    arquivo = origem / "DETRAF_D.csv"
    arquivo.write_text("linha1\nlinha2\nlinha3\n", encoding="utf-8")
    return arquivo


@pytest.fixture
def area(tmp_path: Path) -> AreaDeTrabalho:
    return AreaDeTrabalho(tmp_path / "_TEMP", "202603")


class TestOInsumoNaoEhTocado:
    def test_a_copia_tem_o_mesmo_conteudo_e_fica_fora_da_origem(self, area, insumo):
        (copia,) = area.acolher([insumo])

        assert copia != insumo
        assert copia.read_text(encoding="utf-8") == insumo.read_text(encoding="utf-8")
        assert insumo.parent not in copia.parents

    def test_escrever_na_copia_nao_altera_o_original(self, area, insumo):
        """O caso exato de 2026-08-10, reduzido: a etapa esvazia o que recebeu."""
        (copia,) = area.acolher([insumo])

        copia.write_text("", encoding="utf-8")  # tudo reprovou

        assert insumo.read_text(encoding="utf-8") == "linha1\nlinha2\nlinha3\n"

    def test_renomear_a_copia_nao_renomeia_o_original(self, area, insumo):
        (copia,) = area.acolher([insumo])

        copia.rename(copia.with_name("DETRAF_D_EXP.csv"))

        assert insumo.exists()
        assert insumo.name == "DETRAF_D.csv"

    def test_o_que_nao_pode_ser_copiado_fica_de_fora_da_execucao(self, area, tmp_path):
        """
        Devolver o caminho original seria pior que perder o arquivo da rodada: a
        etapa escreveria nele.
        """
        inexistente = tmp_path / "Vivo" / "sumiu.csv"
        inexistente.parent.mkdir(parents=True)

        assert area.acolher([inexistente]) == []


class TestPromocao:
    def test_o_artefato_volta_para_a_pasta_de_origem(self, area, insumo):
        (copia,) = area.acolher([insumo])
        (copia.parent / "DETRAF_D_ERRO.csv").write_text("ruim\n", encoding="utf-8")

        promovidos = area.promover()

        destino = insumo.parent / "DETRAF_D_ERRO.csv"
        assert destino.exists()
        assert destino.read_text(encoding="utf-8") == "ruim\n"
        assert promovidos == [destino]

    def test_a_copia_de_trabalho_nao_volta(self, area, insumo):
        """
        O coração da proteção. Promover um arquivo de mesmo nome do original
        refaria exatamente a sobrescrita que esta classe existe para impedir.
        """
        (copia,) = area.acolher([insumo])
        copia.write_text("esvaziado pela etapa\n", encoding="utf-8")

        area.promover()

        assert insumo.read_text(encoding="utf-8") == "linha1\nlinha2\nlinha3\n"

    def test_a_copia_renomeada_volta_com_o_nome_novo(self, area, insumo):
        (copia,) = area.acolher([insumo])
        copia.write_text("so as validas\n", encoding="utf-8")
        copia.rename(copia.with_name("DETRAF_D_EXP.csv"))

        area.promover()

        assert (insumo.parent / "DETRAF_D_EXP.csv").read_text(
            encoding="utf-8"
        ) == "so as validas\n"
        assert insumo.read_text(encoding="utf-8") == "linha1\nlinha2\nlinha3\n"

    def test_sem_artefato_nada_volta(self, area, insumo):
        area.acolher([insumo])

        assert area.promover() == []
        assert sorted(p.name for p in insumo.parent.iterdir()) == ["DETRAF_D.csv"]


class TestVoltaParaAOrigem:
    def test_origem_de_devolve_o_insumo(self, area, insumo):
        (copia,) = area.acolher([insumo])

        assert area.origem_de(copia) == insumo

    def test_caminho_desconhecido_volta_ele_mesmo(self, area, tmp_path):
        """
        O histórico é indexado por caminho absoluto. Inventar um caminho aqui
        faria o insumo sumir do filtro anti-reprocessamento.
        """
        estranho = tmp_path / "outro.csv"

        assert area.origem_de(estranho) == estranho

    def test_origens_preserva_a_ordem(self, area, insumo, tmp_path):
        outro = insumo.parent / "OUTRO_D.csv"
        outro.write_text("a\n", encoding="utf-8")

        copias = area.acolher([insumo, outro])

        assert area.origens(copias) == [insumo, outro]


class TestPastasHomonimas:
    def test_arquivos_de_mesmo_nome_em_pastas_diferentes_nao_colidem(
        self, area, tmp_path
    ):
        """
        `Vivo` e `TLF` têm arquivos com o mesmo nome, e duas operadoras também
        podem ter. Sem a marca no nome da pasta de trabalho, uma cópia
        sobrescreveria a outra e o robô validaria o arquivo errado.
        """
        primeiro = tmp_path / "A" / "Detrafs Recebidos" / "IGUAL.csv"
        segundo = tmp_path / "B" / "Detrafs Recebidos" / "IGUAL.csv"
        for caminho, conteudo in ((primeiro, "de A\n"), (segundo, "de B\n")):
            caminho.parent.mkdir(parents=True)
            caminho.write_text(conteudo, encoding="utf-8")

        copia_a, copia_b = area.acolher([primeiro, segundo])

        assert copia_a != copia_b
        assert copia_a.read_text(encoding="utf-8") == "de A\n"
        assert copia_b.read_text(encoding="utf-8") == "de B\n"

    def test_cada_artefato_volta_para_a_sua_pasta(self, area, tmp_path):
        primeiro = tmp_path / "A" / "Detrafs Recebidos" / "IGUAL.csv"
        segundo = tmp_path / "B" / "Detrafs Recebidos" / "IGUAL.csv"
        for caminho in (primeiro, segundo):
            caminho.parent.mkdir(parents=True)
            caminho.write_text("x\n", encoding="utf-8")

        copia_a, copia_b = area.acolher([primeiro, segundo])
        (copia_a.parent / "IGUAL_ERRO.csv").write_text("erro de A\n", encoding="utf-8")
        (copia_b.parent / "IGUAL_ERRO.csv").write_text("erro de B\n", encoding="utf-8")

        area.promover()

        assert (primeiro.parent / "IGUAL_ERRO.csv").read_text(
            encoding="utf-8"
        ) == "erro de A\n"
        assert (segundo.parent / "IGUAL_ERRO.csv").read_text(
            encoding="utf-8"
        ) == "erro de B\n"


class TestEntregaNumaPastaDeSaida:
    """Com `destino_de`, o artefato não volta para a pasta de entrada."""

    def test_o_artefato_vai_para_a_saida_e_nao_para_a_origem(
        self, tmp_path, insumo
    ):
        saida = tmp_path / "_SAIDA" / "202603" / "Vivo"
        area = AreaDeTrabalho(
            tmp_path / "_TEMP", "202603", destino_de=lambda _: saida
        )
        (copia,) = area.acolher([insumo])
        (copia.parent / "DETRAF_D_ERRO.csv").write_text("ruim\n", encoding="utf-8")

        area.promover()

        assert (saida / "DETRAF_D_ERRO.csv").read_text(encoding="utf-8") == "ruim\n"
        assert sorted(p.name for p in insumo.parent.iterdir()) == ["DETRAF_D.csv"]

    def test_a_pasta_de_saida_e_criada_se_nao_existir(self, tmp_path, insumo):
        saida = tmp_path / "nao" / "existe" / "ainda"
        area = AreaDeTrabalho(
            tmp_path / "_TEMP", "202603", destino_de=lambda _: saida
        )
        (copia,) = area.acolher([insumo])
        (copia.parent / "DETRAF_D_EXP.csv").write_text("ok\n", encoding="utf-8")

        area.promover()

        assert (saida / "DETRAF_D_EXP.csv").exists()

    def test_destino_desconhecido_deixa_o_artefato_na_area(self, tmp_path, insumo):
        """
        `None` significa "não sei onde isto vai". Entregar num palpite poria o
        artefato numa pasta que ninguém lê — pior do que deixá-lo onde se sabe
        procurar.
        """
        area = AreaDeTrabalho(tmp_path / "_TEMP", "202603", destino_de=lambda _: None)
        (copia,) = area.acolher([insumo])
        artefato = copia.parent / "DETRAF_D_ERRO.csv"
        artefato.write_text("ruim\n", encoding="utf-8")

        assert area.promover() == []
        assert artefato.exists()
        assert sorted(p.name for p in insumo.parent.iterdir()) == ["DETRAF_D.csv"]


class TestPreservacao:
    def test_a_area_fica_no_disco_depois_da_promocao(self, area, insumo):
        """
        É evidência de homologação, e o estado parcial de uma etapa que morreu no
        meio. Quem a limpa é o `resetar_homologacao.py`, por referência.
        """
        (copia,) = area.acolher([insumo])
        (copia.parent / "DETRAF_D_ERRO.csv").write_text("ruim\n", encoding="utf-8")

        area.promover()

        assert copia.exists()
        assert (copia.parent / "DETRAF_D_ERRO.csv").exists()

    def test_a_area_separa_por_referencia(self, tmp_path, insumo):
        raiz = tmp_path / "_TEMP"
        (copia,) = AreaDeTrabalho(raiz, "202603").acolher([insumo])

        assert (raiz / "202603") in copia.parents
