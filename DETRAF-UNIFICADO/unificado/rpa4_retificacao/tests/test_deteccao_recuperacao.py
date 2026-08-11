"""A detecção do tráfego recuperado — o que o robô pega e o que ele deixa.

🔴 Na origem, nada disto tinha teste. As quatro funções puras da HU-21 decidem
**quanto** é lançado num evento irreversível do AGI, e nenhuma era exercitada.
"""

from __future__ import annotations

import pytest

from conftest import REFERENCIA_CONTESTACAO
from src.services import deteccao_recuperacao as deteccao


class TestMesAnterior:
    """A recuperação é vista no mês seguinte ao da contestação."""

    @pytest.mark.parametrize(
        "processamento, esperado",
        [
            ("202607", "202606"),
            ("202601", "202512"),  # vira o ano
            ("202603", "202602"),
        ],
    )
    def test_recua_um_mes(self, processamento, esperado):
        assert deteccao.mes_anterior(processamento) == esperado


class TestDeteccao:
    def test_pega_apenas_a_variacao_negativa(self, repo_tabelas):
        """
        Variação positiva é contestação (RPA 3), negativa é recuperação (RPA 4).

        É a regra de `comum/dominio/variacao.py`, que já apontava para cá.
        """
        recuperacoes = deteccao.detectar(repo_tabelas, referencia="202507")

        assert {item.id_contestacao for item in recuperacoes} == {1, 2}

    def test_ignora_o_que_ja_foi_marcado(self, repo_tabelas):
        """
        O freio de idempotência: o evento no AGI não se desfaz.

        ⚠️ Este mesmo campo é escrito pelo RPA 3 com outro sentido — ver
        `obter_trafego_recuperado`. A linha 4 da fixture é negativa e mesmo assim
        não entra, e é isso que o teste trava.
        """
        recuperacoes = deteccao.detectar(repo_tabelas, referencia="202507")

        assert 4 not in {item.id_contestacao for item in recuperacoes}

    def test_mes_sem_recuperacao_devolve_lista_vazia(self, repo_tabelas):
        """Vazio é resultado legítimo, não falha — a HU-21 não roda todo mês."""
        assert deteccao.detectar(repo_tabelas, referencia="209912") == []

    def test_procura_no_mes_anterior_ao_de_processamento(self, repo_tabelas):
        """
        Passar o mês da contestação em vez do de processamento não acha nada.

        Parece detalhe e não é: errar isto faz o robô terminar com sucesso e zero
        recuperações, que é indistinguível de "não houve recuperação".
        """
        assert deteccao.detectar(repo_tabelas, referencia=REFERENCIA_CONTESTACAO) == []

    def test_minutos_e_valor_vem_absolutos(self, repo_tabelas):
        """
        A diferença é negativa por definição; o AGI recebe **quanto** foi
        recuperado, sem sinal.
        """
        (primeira,) = [
            item
            for item in deteccao.detectar(repo_tabelas, referencia="202507")
            if item.id_contestacao == 1
        ]

        assert primeira.minutos == 1000.0
        assert primeira.valor_bruto == 100.0

    def test_traz_as_quatro_chaves_do_cruzamento(self, repo_tabelas):
        """
        EOT, referência e tráfego saem daqui para achar o processo no CSV — sem
        eles o passo seguinte não tem como identificar a linha certa na grid.
        """
        (primeira,) = [
            item
            for item in deteccao.detectar(repo_tabelas, referencia="202507")
            if item.id_contestacao == 1
        ]

        assert primeira.eot_operadora == "021"
        assert primeira.periodo == REFERENCIA_CONTESTACAO
        assert primeira.periodo_trafego == "202506"
        assert primeira.operadora == "CLARO"

    def test_ja_vem_com_os_valores_do_evento_calculados(self, repo_tabelas):
        (primeira,) = [
            item
            for item in deteccao.detectar(repo_tabelas, referencia="202507")
            if item.id_contestacao == 1
        ]

        assert primeira.valores_evento["valor_bruto_negociado"] == 100.0
        assert primeira.valores_evento["duracao"] == 1000.0


class TestFechamentoDoCiclo:
    def test_marcar_tira_a_linha_da_proxima_deteccao(self, repo_tabelas):
        """O ciclo completo: detecta, marca, e da segunda vez não aparece mais."""
        antes = deteccao.detectar(repo_tabelas, referencia="202507")
        assert 1 in {item.id_contestacao for item in antes}

        repo_tabelas.marcar_retificacao_no_agi(1)

        depois = deteccao.detectar(repo_tabelas, referencia="202507")
        assert 1 not in {item.id_contestacao for item in depois}

    def test_marcar_id_inexistente_avisa_e_nao_quebra(self, repo_tabelas, caplog):
        """
        Zero linhas atualizadas significa que a recuperação vai voltar na próxima
        execução — e o evento seria lançado de novo. Precisa aparecer no log.
        """
        assert repo_tabelas.marcar_retificacao_no_agi(9999) == 0
        assert "9999" in caplog.text
