"""A metade da HU-01 que faltava (2026-08-13): organizar a Caixa de Entrada.

Até aqui o robô só lia a pasta 'Detraf Despesas', como se algo de fora a
alimentasse. A V2 diz o contrário: é o próprio robô quem filtra a Caixa de
Entrada e organiza os e-mails ali — e a Vivo confirmou, por e-mail, que não
criou regra nenhuma para isso. Sem este passo, a pasta nunca recebe nada.

`OutlookService` é substituído por um dublê simples: o que se testa aqui é a
orquestração (quem é movido, quem não é, o que acontece se uma falhar), não a
integração COM — essa já é dublada em `test_outlook_service_anexos.py`.
"""

from pathlib import Path

import pytest

from comum.integracoes.outlook import OutlookError
from comum.integracoes.outlook_config import Attachment, EmailMessage, OutlookConfig
from src.controllers.outlook_controller import OutlookController


class _OutlookFalso:
    """Dublê de `OutlookService`: só os dois métodos que a organização usa."""

    def __init__(self, emails: list[EmailMessage], falha_para: set[str] = frozenset()):
        self._emails = emails
        self._falha_para = falha_para
        self.movidos: list[tuple[str, str]] = []

    def fetch_emails_from_inbox(self) -> list[EmailMessage]:
        return self._emails

    def move_to_top_level_folder(self, entry_id: str, folder_name: str) -> None:
        if entry_id in self._falha_para:
            raise OutlookError(f"falha simulada ao mover '{entry_id}'")
        self.movidos.append((entry_id, folder_name))


def _anexo(nome: str, inline: bool = False) -> Attachment:
    extensao = nome.rsplit(".", 1)[-1]
    return Attachment(
        index=1, file_name=nome, display_name=nome, file_size=100,
        file_type=extensao, is_inline=inline,
    )


def _email(entry_id: str, subject: str = "", body: str = "", anexos=None) -> EmailMessage:
    return EmailMessage(
        entry_id=entry_id, subject=subject, sender_name="Operadora",
        sender_email="op@exemplo.com", body=body, received_at=None,
        attachments=anexos or [], attachment_count=len(anexos or []),
    )


@pytest.fixture()
def controller(tmp_path: Path) -> OutlookController:
    """`OutlookController` sem `__init__` — evita `RastreamentoRepository` real."""
    instancia = OutlookController.__new__(OutlookController)
    instancia._config = OutlookConfig(
        account="detrafTBRA",
        detraf_despesas_folder="Detraf Despesas",
        processados_folder="PROCESSADOS",
        dest_root=tmp_path,
        max_retry=3,
        dia_liberacao=5,
    )
    return instancia


class TestOrganizarCaixaDeEntrada:
    def test_email_de_despesa_e_movido_para_detraf_despesas(self, controller):
        outlook = _OutlookFalso([
            _email("e1", subject="Detraf março", anexos=[_anexo("detraf.csv")]),
        ])

        controller.organizar_caixa_de_entrada(outlook)

        assert outlook.movidos == [("e1", "Detraf Despesas")]

    def test_email_de_contestacao_nao_e_movido(self, controller):
        """Mesmo filtro de `DetrafEmailFilterService` — assunto com 'CONTESTAÇÃO' fica de fora."""
        outlook = _OutlookFalso([
            _email("e1", subject="CONTESTAÇÃO TIM x Vivo", anexos=[_anexo("detraf.csv")]),
        ])

        controller.organizar_caixa_de_entrada(outlook)

        assert outlook.movidos == []

    def test_email_sem_anexo_relevante_nao_e_movido(self, controller):
        outlook = _OutlookFalso([
            _email("e1", subject="Aviso", anexos=[_anexo("assinatura.png", inline=True)]),
            _email("e2", subject="Relatório em PDF", anexos=[_anexo("relatorio.pdf")]),
        ])

        controller.organizar_caixa_de_entrada(outlook)

        assert outlook.movidos == []

    def test_uma_falha_ao_mover_nao_impede_as_seguintes(self, controller):
        """Igual ao resto do robô: um item ruim não trava o lote inteiro."""
        outlook = _OutlookFalso(
            [
                _email("e1", subject="Detraf 1", anexos=[_anexo("d1.csv")]),
                _email("e2", subject="Detraf 2", anexos=[_anexo("d2.csv")]),
            ],
            falha_para={"e1"},
        )

        controller.organizar_caixa_de_entrada(outlook)

        assert outlook.movidos == [("e2", "Detraf Despesas")]

    def test_caixa_de_entrada_vazia_nao_move_nada(self, controller):
        outlook = _OutlookFalso([])

        controller.organizar_caixa_de_entrada(outlook)

        assert outlook.movidos == []
