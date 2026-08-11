"""Verificações de ambiente (2026-08-06).

Estas funções existem para transformar "o robô falhou no meio do teste" em "falta
X, faça Y". O que se cobre aqui é o que elas **distinguem** — porque o valor todo
está na distinção: "não configurada", "não existe" e "sem permissão" produzem o
mesmo sintoma no robô (*nenhum arquivo encontrado*) e exigem correções
completamente diferentes.

E o que elas **não** revelam: valor de credencial nenhum sai daqui.
"""

from pathlib import Path

import pytest

from comum.config import diagnostico as diag


class TestVerificacaoDePasta:
    def test_pasta_boa_passa(self, tmp_path):
        resultado = diag.verificar_pasta("g", "VAR", tmp_path)

        assert resultado.situacao == "ok"

    def test_nao_configurada_e_obrigatoria_e_falha(self):
        resultado = diag.verificar_pasta("g", "VAR", None)

        assert resultado.situacao == "falha"
        assert "VAR" in resultado.correcao

    def test_nao_configurada_e_opcional_e_so_aviso(self):
        resultado = diag.verificar_pasta("g", "VAR", None, obrigatoria=False)

        assert resultado.situacao == "aviso"

    def test_ponto_e_tratado_como_nao_configurada(self):
        """
        `Path("")` vira `Path(".")`, o diretório atual **existe e é diretório**
        — então toda guarda passa e o robô varre o lugar errado em silêncio. Foi
        exatamente o defeito corrigido em 2026-08-04, e ele volta sempre que
        alguém usa `padrao=""`.
        """
        resultado = diag.verificar_pasta("g", "VAR", Path("."))

        assert resultado.situacao == "falha"
        assert "diretório atual" in resultado.detalhe
        assert "não acusa erro" in resultado.correcao

    def test_inexistente_diz_que_nao_existe(self, tmp_path):
        resultado = diag.verificar_pasta("g", "VAR", tmp_path / "nao-existe")

        assert resultado.situacao == "falha"
        assert "não existe" in resultado.detalhe

    def test_arquivo_no_lugar_de_pasta_e_distinguido(self, tmp_path):
        arquivo = tmp_path / "isto-e-um-arquivo.txt"
        arquivo.write_text("x", encoding="utf-8")

        resultado = diag.verificar_pasta("g", "VAR", arquivo)

        assert resultado.situacao == "falha"
        assert "é arquivo" in resultado.detalhe

    def test_escrita_e_testada_de_verdade(self, tmp_path):
        """
        `os.access(W_OK)` mente em compartilhamento de rede Windows, que é
        justamente onde este repositório grava. Só criar e apagar prova.
        """
        resultado = diag.verificar_pasta("g", "VAR", tmp_path, precisa_escrever=True)

        assert resultado.situacao == "ok"
        assert "escrita" in resultado.detalhe

    def test_o_teste_de_escrita_nao_deixa_lixo(self, tmp_path):
        diag.verificar_pasta("g", "VAR", tmp_path, precisa_escrever=True)

        assert list(tmp_path.iterdir()) == []


class TestVerificacaoDeCredencial:
    def test_credencial_presente_passa(self):
        resultado = diag.verificar_credencial("g", "SENHA", "abc123")

        assert resultado.situacao == "ok"

    def test_o_valor_nunca_aparece(self):
        """
        O relatório vai para a tela e para o log de quem homologa. O
        comprimento basta para identificar uma credencial sem revelá-la — foi
        assim que a duplicação entre os `.env` do P6 e do P7 foi identificada.
        """
        segredo = "senha-muito-secreta"

        resultado = diag.verificar_credencial("g", "SENHA", segredo)

        assert segredo not in resultado.detalhe
        assert segredo not in resultado.correcao
        assert str(len(segredo)) in resultado.detalhe

    def test_ausente_e_obrigatoria_e_falha(self):
        assert diag.verificar_credencial("g", "SENHA", "").situacao == "falha"

    def test_ausente_e_opcional_e_aviso(self):
        resultado = diag.verificar_credencial("g", "SENHA", "", obrigatoria=False)

        assert resultado.situacao == "aviso"

    def test_espaco_nas_pontas_e_avisado(self):
        """Erro de cópia que o servidor recusa sem dizer por quê."""
        resultado = diag.verificar_credencial("g", "SENHA", " abc123 ")

        assert resultado.situacao == "aviso"
        assert "espaço" in resultado.detalhe


class TestTraducaoDoErroDeBanco:
    @pytest.mark.parametrize(
        "mensagem, esperado_no_detalhe, esperado_na_correcao",
        [
            ("(1045, \"Access denied for user 'rpa'@'host'\")", "recusados", "USUARIO_BD"),
            ("(1049, \"Unknown database 'webfat'\")", "base não existe", "DATABASE_RPA"),
            ("Can't connect to MySQL server on 'srv' (timed out)", "alcançar", "HOST_BD_RPA"),
            ("(1146, \"Table 'w.tbl_x' doesn't exist\")", "tabela não existe", "N1"),
            ("(1054, \"Unknown column 'vb_contestacao'\")", "falta uma coluna", "Q22"),
        ],
    )
    def test_cada_causa_tem_a_sua_correcao(
        self, mensagem, esperado_no_detalhe, esperado_na_correcao
    ):
        """
        As cinco chegam como a mesma exceção do driver, e cada uma pede uma
        ação diferente. Sem a tradução, todas viravam a mesma linha crua dentro
        de um `RuntimeError`.
        """
        causa, correcao = diag.explicar_erro_de_banco(Exception(mensagem))

        assert esperado_no_detalhe in causa
        assert esperado_na_correcao in correcao

    def test_erro_desconhecido_devolve_a_mensagem_original(self):
        """Melhor um texto cru do que uma explicação inventada."""
        causa, correcao = diag.explicar_erro_de_banco(Exception("algo muito estranho"))

        assert "algo muito estranho" in causa
        assert "DEBUG" in correcao


class TestVerificacaoDasVariaveis:
    def _env_example(self, tmp_path, conteudo: str) -> Path:
        caminho = tmp_path / ".env.example"
        caminho.write_text(conteudo, encoding="utf-8")
        return caminho

    def test_nome_digitado_errado_e_acusado(self, tmp_path, monkeypatch):
        """
        A classe de erro mais chata de diagnosticar: `PERMITIR_UPLOAD_AGY` não
        causa erro nenhum. O default vale, e o robô se comporta como se a linha
        nunca tivesse sido escrita.
        """
        monkeypatch.setenv("PERMITIR_UPLOAD_AGY", "true")
        arquivo = self._env_example(tmp_path, "PERMITIR_UPLOAD_AGI=false\n")

        resultados = diag.verificar_variaveis(arquivo)

        acusadas = [r.item for r in resultados if r.situacao == "aviso"]
        assert "PERMITIR_UPLOAD_AGY" in acusadas

    def test_sufixo_por_robo_nao_e_acusado(self, tmp_path, monkeypatch):
        """`ENV_RPA3` é legítimo e nunca vai estar no `.env.example`."""
        monkeypatch.setenv("ENV_RPA3", "dev")
        arquivo = self._env_example(tmp_path, "ENV=prod\n")

        resultados = diag.verificar_variaveis(arquivo)

        assert "ENV_RPA3" not in [r.item for r in resultados]

    def test_comentario_no_env_example_nao_vira_variavel(self, tmp_path):
        arquivo = self._env_example(
            tmp_path, "# LOG_LEVEL=DEBUG era o padrão antigo\nLOG_LEVEL=INFO\n"
        )

        resultados = diag.verificar_variaveis(arquivo)

        assert "# LOG_LEVEL" not in [r.item for r in resultados]

    def test_env_example_ausente_vira_aviso_e_nao_estoura(self, tmp_path):
        resultados = diag.verificar_variaveis(tmp_path / "nao-existe")

        assert len(resultados) == 1
        assert resultados[0].situacao == "aviso"


class TestListaDeFiltroVazia:
    """
    🔴 O modo de falha mais traiçoeiro do repositório.

    Três variáveis são lidas como `any(sub in nome for sub in LISTA)`. Com a
    lista **vazia**, `any(...)` é `False` e o filtro **rejeita tudo** — sem erro,
    sem aviso. A execução termina com **sucesso** tendo processado zero
    arquivos, e quem lê o log conclui que não havia nada a fazer.

    Achado em 2026-08-06 comparando o `.env.example` com os `.env` dos projetos
    de origem: `ARQUIVOS_VALIDADOS` estava em branco aqui e valia `_ENV` lá — e
    sem ele o batimento do RPA 2 não lê arquivo nenhum.
    """

    def test_lista_preenchida_passa(self):
        resultado = diag.verificar_lista_de_filtro(
            "g", "ARQUIVOS_VALIDADOS", ["_EXP"], "É o filtro do batimento."
        )

        assert resultado.situacao == "ok"
        assert "_EXP" in resultado.detalhe

    def test_lista_vazia_e_falha_nao_aviso(self):
        """
        Aviso não basta: o efeito é a apuração inteira do mês não acontecer, e o
        robô reportar sucesso. Isso é falha.
        """
        resultado = diag.verificar_lista_de_filtro(
            "g", "ARQUIVOS_VALIDADOS", [], "É o filtro do batimento."
        )

        assert resultado.situacao == "falha"

    def test_a_mensagem_diz_o_efeito_real(self):
        """
        "Lista vazia" não comunica nada. "A execução termina com sucesso tendo
        processado zero arquivos" comunica.
        """
        resultado = diag.verificar_lista_de_filtro(
            "g", "ARQUIVOS_VALIDADOS", [], "É o filtro do batimento do RPA 2."
        )

        assert "SUCESSO" in resultado.correcao
        assert "zero arquivos" in resultado.correcao
        assert "batimento do RPA 2" in resultado.correcao, (
            "sem dizer o que a lista filtra, quem lê não sabe o que vai parar"
        )

    def test_lista_so_com_espaco_conta_como_vazia(self):
        """`ARQUIVOS_VALIDADOS=  ` no .env produz `['']`, que filtra tudo igual."""
        resultado = diag.verificar_lista_de_filtro("g", "X", ["", "  "], "algo")

        assert resultado.situacao == "falha"

    def test_none_nao_quebra(self):
        assert diag.verificar_lista_de_filtro("g", "X", None, "algo").situacao == "falha"
