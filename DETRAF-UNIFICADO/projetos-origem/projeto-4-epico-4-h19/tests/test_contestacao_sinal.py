"""Testes da leitura do sinal COM/SEM retenção (T-024, D-6 resolvida).

Consulta `tbl_rpa_log_detraf_despesa_contestacao` (schema — ver conftest.py, incluindo a
coluna `remuneracao` adicionada em 2026-07-28, D-16 revisada: o sinal pode variar por
remuneração dentro do mesmo par de EOT) via `RepositorioTabelas.obter_tipo_contestacao`.
"""

from src.models.repository.repositorio_tabelas import RepositorioTabelas


def test_encontra_com_retencao(repo_cache):
    repo = RepositorioTabelas()
    resultado = repo.obter_tipo_contestacao(
        eot_operadora="021", eot_tbra="011", referencia="202507", trafego="202507",
        remuneracao="TU-RL",
    )
    assert resultado == "com retenção"


def test_encontra_sem_retencao(repo_cache):
    repo = RepositorioTabelas()
    resultado = repo.obter_tipo_contestacao(
        eot_operadora="021", eot_tbra="012", referencia="202507", trafego="202507",
        remuneracao="VU-M",
    )
    assert resultado == "sem retenção"


def test_nao_encontrado_retorna_none(repo_cache):
    repo = RepositorioTabelas()
    resultado = repo.obter_tipo_contestacao(
        eot_operadora="999", eot_tbra="011", referencia="202507", trafego="202507",
        remuneracao="TU-RL",
    )
    assert resultado is None


def test_remuneracao_diferente_nao_encontra(repo_cache):
    # Mesmo par de EOT/referência/tráfego do seed "com retenção", mas remuneração
    # diferente (TU-RL é a do seed) — não deve casar (D-16 revisada, 2026-07-28).
    repo = RepositorioTabelas()
    resultado = repo.obter_tipo_contestacao(
        eot_operadora="021", eot_tbra="011", referencia="202507", trafego="202507",
        remuneracao="OUTRA-REMUNERACAO",
    )
    assert resultado is None


def test_normaliza_eot_com_zeros_a_esquerda(repo_cache):
    # EOT "21" (sem zero à esquerda) deve resolver igual a "021" (_tratar_eot).
    repo = RepositorioTabelas()
    resultado = repo.obter_tipo_contestacao(
        eot_operadora="21", eot_tbra="11", referencia="202507", trafego="202507",
        remuneracao="TU-RL",
    )
    assert resultado == "com retenção"
