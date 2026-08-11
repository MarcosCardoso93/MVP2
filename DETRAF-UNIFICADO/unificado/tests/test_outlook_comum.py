"""Camada comum de Outlook — envio, anexos e resposta.

Três implementações de acesso ao Outlook foram unificadas em
`comum/integracoes/outlook.py`: a do RPA 1 (leitura), o `Dispatch` inline do
RPA 2 (resposta) e o `outlook_standalone_original.py` do Projeto 5 (envio). Estes
testes cobrem justamente as partes que **vieram de fora** do RPA 1 e portanto não
estavam cobertas por `rpa1_captura/tests/`.

O COM é substituído por dublês: exercitá-lo de verdade exigiria Outlook Desktop
instalado com perfil configurado, e o que se testa aqui é a regra — que os anexos
são conferidos antes do envio, que `Send()` só acontece quando pedido.
"""

from pathlib import Path

import pytest

from comum.integracoes.outlook import OutlookError, OutlookService


class _MailFalso:
    """Dublê de um MailItem do Outlook."""

    def __init__(self):
        self.Subject = None
        self.Body = None
        self.To = None
        self.CC = None
        self.enviado = False
        self.salvo = False
        self.Attachments = _ColecaoAnexos()

    def Send(self):
        self.enviado = True

    def Save(self):
        self.salvo = True

    def Reply(self):
        resposta = _MailFalso()
        resposta.Subject = self.Subject
        self.resposta = resposta
        return resposta


class _ColecaoAnexos:
    def __init__(self):
        self.adicionados: list[str] = []

    def Add(self, caminho):
        self.adicionados.append(str(caminho))


class _AppFalso:
    def __init__(self):
        self.criados: list[_MailFalso] = []

    def CreateItem(self, tipo):
        assert tipo == 0, "olMailItem é 0"
        mail = _MailFalso()
        self.criados.append(mail)
        return mail


@pytest.fixture()
def servico():
    """`OutlookService` sem passar pelo `__init__`, que abriria conexão COM."""
    instancia = OutlookService.__new__(OutlookService)
    instancia._app = _AppFalso()
    return instancia


@pytest.fixture()
def anexos(tmp_path: Path) -> list[Path]:
    carta = tmp_path / "CT - 363.docx"
    env = tmp_path / "Base Contestação_CLARO_202507_ENV.xlsx"
    carta.write_text("carta", encoding="utf-8")
    env.write_text("env", encoding="utf-8")
    return [carta, env]


class TestEnvio:
    def test_envia_com_assunto_corpo_e_destinatarios(self, servico):
        servico.send_email(to="operadora@exemplo.com", subject="Assunto", body="Corpo")

        mail = servico._app.criados[0]
        assert (mail.To, mail.Subject, mail.Body) == (
            "operadora@exemplo.com", "Assunto", "Corpo",
        )
        assert mail.enviado

    def test_lista_de_destinatarios_vira_string_separada_por_ponto_e_virgula(self, servico):
        servico.send_email(to=["a@x.com", "b@x.com"], subject="s", body="c")

        assert servico._app.criados[0].To == "a@x.com; b@x.com"

    def test_copia_segue_a_mesma_regra(self, servico):
        servico.send_email(to="a@x.com", subject="s", body="c", cc=["c@x.com", "d@x.com"])

        assert servico._app.criados[0].CC == "c@x.com; d@x.com"

    def test_sem_copia_o_campo_nao_e_tocado(self, servico):
        servico.send_email(to="a@x.com", subject="s", body="c")

        assert servico._app.criados[0].CC is None


class TestAnexos:
    def test_anexa_cada_arquivo_antes_de_enviar(self, servico, anexos):
        servico.send_email_com_anexos(
            to="a@x.com", subject="s", body="c", anexos=anexos
        )

        mail = servico._app.criados[0]
        assert [Path(c).name for c in mail.Attachments.adicionados] == [
            "CT - 363.docx",
            "Base Contestação_CLARO_202507_ENV.xlsx",
        ]
        assert mail.enviado

    def test_anexo_inexistente_impede_o_envio(self, servico, anexos, tmp_path):
        """
        O e-mail é irreversível: se um anexo falta, é melhor não sair.

        Sem esta guarda, a operadora receberia a contestação sem a carta — e não
        há como cancelar depois.
        """
        faltando = tmp_path / "nao_existe.xlsx"

        with pytest.raises(OutlookError, match="Anexo"):
            servico.send_email_com_anexos(
                to="a@x.com", subject="s", body="c", anexos=[*anexos, faltando]
            )

        assert servico._app.criados == []

    def test_a_mensagem_de_erro_nomeia_o_anexo_que_falta(self, servico, tmp_path):
        with pytest.raises(OutlookError, match="nao_existe.xlsx"):
            servico.send_email_com_anexos(
                to="a@x.com", subject="s", body="c", anexos=[tmp_path / "nao_existe.xlsx"]
            )

    def test_diretorio_nao_conta_como_anexo(self, servico, tmp_path):
        """`is_file()`, não `exists()`: uma pasta existe e não pode ser anexada."""
        pasta = tmp_path / "Contestações"
        pasta.mkdir()

        with pytest.raises(OutlookError):
            servico.send_email_com_anexos(
                to="a@x.com", subject="s", body="c", anexos=[pasta]
            )

    def test_envio_sem_anexo_e_valido(self, servico):
        servico.send_email_com_anexos(to="a@x.com", subject="s", body="c")

        assert servico._app.criados[0].Attachments.adicionados == []


class TestResposta:
    """Substitui o `win32com.client.Dispatch` inline que o RPA 2 tinha."""

    @pytest.fixture()
    def servico_com_ns(self, servico):
        original = _MailFalso()
        original.Subject = "DETRAF 202507 - CLARO"

        class _Namespace:
            def GetItemFromID(self, entry_id):
                assert entry_id == "ABC123"
                return original

        servico._ns = _Namespace()
        servico.original = original
        return servico

    def test_rascunho_e_o_default(self, servico_com_ns):
        servico_com_ns.responder_email("ABC123", "Arquivo inválido.")

        resposta = servico_com_ns.original.resposta
        assert resposta.salvo and not resposta.enviado

    def test_envia_quando_pedido_explicitamente(self, servico_com_ns):
        servico_com_ns.responder_email("ABC123", "Arquivo inválido.", enviar=True)

        resposta = servico_com_ns.original.resposta
        assert resposta.enviado and not resposta.salvo

    def test_assunto_prefixado_e_corpo_preenchido(self, servico_com_ns):
        servico_com_ns.responder_email("ABC123", "Arquivo inválido.")

        resposta = servico_com_ns.original.resposta
        assert resposta.Subject == "RES: DETRAF 202507 - CLARO"
        assert resposta.Body == "Arquivo inválido."

    def test_create_reply_draft_continua_valendo_e_nunca_envia(self, servico_com_ns):
        """O RPA 1 chama pelo nome antigo — não pode virar envio por acidente."""
        servico_com_ns.create_reply_draft("ABC123", "corpo")

        assert not servico_com_ns.original.resposta.enviado

    def test_email_inexistente_vira_OutlookError(self, servico):
        class _NamespaceVazio:
            def GetItemFromID(self, entry_id):
                raise RuntimeError("não encontrado")

        servico._ns = _NamespaceVazio()

        with pytest.raises(OutlookError, match="não encontrado|não foi"):
            servico.responder_email("SUMIU", "corpo")
