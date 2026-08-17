"""O template que vai no repositório, conferido contra o código que o usa.

Este é o único artefato do projeto cujo conteúdo **sai da empresa**: ele vira,
inteiro, o corpo de um e-mail para a operadora. Um erro aqui não quebra nada —
`_PlaceholderAusente` devolve o placeholder cru de propósito, para que uma chave
desconhecida não impeça o aviso de sair. O preço disso é que um `{motivo}` no
singular chegaria à operadora **como texto literal**, sem nenhum sintoma.

Daí um teste de conteúdo, e não de código: ele lê o arquivo de verdade e o
renderiza com os mesmos dados que `notificacao_operadora` monta.
"""

from pathlib import Path

import pytest

from comum.integracoes.corpo_email import renderizar
from src.models.dto.arquivo_recusado import ArquivoRecusado
from src.services.notificacao_operadora import formatar_arquivos

_CAMINHO = (
    Path(__file__).resolve().parents[2] / "configuracao" / "email-detraf-invalido.txt"
)

#: Os mesmos nomes que `notificar_arquivo_invalido` passa ao renderizador. Se um
#: deles for renomeado lá e não aqui, o teste de placeholder desconhecido acusa.
_RECUSAS = [
    ArquivoRecusado(
        nome="DETRAF_202507.csv",
        motivos=["Coluna 8 (GH): o grupo horário precisa ser S, R, N ou D."],
    ),
    ArquivoRecusado(
        nome="DETRAF_202507_B.csv",
        motivos=["Coluna 11 (Tarifa): a tarifa não pode ser zero."],
    ),
]

DADOS = {
    "assunto_original": "Detraf julho",
    "remetente": "faturamento@operadora.com.br",
    "data_recebimento": "2026-08-03T09:14:00",
    "quantidade": str(len(_RECUSAS)),
    "arquivos": formatar_arquivos(_RECUSAS),
}


@pytest.fixture()
def template() -> str:
    return _CAMINHO.read_text(encoding="utf-8")


class TestOArquivoExiste:
    def test_esta_no_repositorio(self):
        assert _CAMINHO.is_file()

    def test_nao_tem_linha_de_comentario(self, template):
        """
        Diferente do `contatos-operadoras.csv`, que usa `#` no topo. Aqui um
        cabeçalho explicativo seria lido pela operadora — o arquivo inteiro é o
        corpo do e-mail.
        """
        for linha in template.splitlines():
            assert not linha.lstrip().startswith("#"), linha


class TestRenderizacao:
    def test_nenhum_placeholder_sobra(self, template):
        """
        🔴 O modo de falha que este arquivo tem e o código não pega. Uma chave
        desconhecida não levanta: ela sai literal no e-mail.
        """
        corpo = renderizar(template, DADOS)

        assert "{" not in corpo, (
            "sobrou placeholder no corpo — confira se o nome bate com os que "
            "`notificacao_operadora.notificar_arquivo_invalido` passa"
        )

    def test_o_corpo_diz_quais_arquivos(self, template):
        corpo = renderizar(template, DADOS)

        assert "DETRAF_202507.csv" in corpo
        assert "DETRAF_202507_B.csv" in corpo

    def test_o_corpo_diz_os_motivos(self, template):
        """Sem isto o e-mail é "seu arquivo está inválido" — e não dá para agir."""
        corpo = renderizar(template, DADOS)

        assert "Coluna 8 (GH)" in corpo
        assert "Coluna 11 (Tarifa)" in corpo

    def test_cada_motivo_fica_sob_o_seu_arquivo(self, template):
        """
        Com vários arquivos no mesmo e-mail, um motivo solto não diz a qual
        deles pertence — e a operadora corrigiria o arquivo errado.
        """
        corpo = renderizar(template, DADOS)
        primeiro = corpo.index("DETRAF_202507.csv")
        segundo = corpo.index("DETRAF_202507_B.csv")

        assert primeiro < corpo.index("Coluna 8 (GH)") < segundo
        assert segundo < corpo.index("Coluna 11 (Tarifa)")

    def test_diz_quantos_foram(self, template):
        corpo = renderizar(template, DADOS)

        assert "2" in corpo


class TestOsCincoCamposDocumentados:
    """
    O `.env.example` promete cinco placeholders. O template não é obrigado a usar
    todos — mas `{arquivos}`, que diz **quais** foram recusados e **por quê**, é o
    motivo de o e-mail existir.
    """

    @pytest.mark.parametrize("campo", ["arquivos"])
    def test_os_indispensaveis_estao_no_template(self, template, campo):
        assert "{" + campo + "}" in template

    def test_todo_placeholder_usado_e_conhecido(self, template):
        """
        O contrário do teste de renderização: pega um placeholder inventado no
        arquivo que ninguém preenche.
        """
        import re

        usados = set(re.findall(r"\{(\w+)\}", template))

        assert usados <= set(DADOS), f"placeholder sem origem no código: {usados - set(DADOS)}"


class TestNaoVazaNadaQueOOperadorNaoDeveVer:
    def test_nao_menciona_caminho_interno(self, template):
        """
        A quarentena, o `_RECUSADO.md` e a árvore de pastas são assunto nosso.
        Mandá-los para a operadora exporia a estrutura interna sem ajudá-la.
        """
        proibidos = ["QUARENTENA", "RECUSADO", "C:\\", "Detrafs Recebidos", "WebFat"]

        for termo in proibidos:
            assert termo not in template, termo
