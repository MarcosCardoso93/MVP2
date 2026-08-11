"""Caminho relativo do `.env` vale a partir de `unificado/` (2026-08-07).

🔴 O modo de falha que isto impede é mudo, e por isso caro.

`Path("arquivos/Operadoras")` é resolvido contra o **diretório de trabalho do
processo**, no momento de cada operação de I/O. Enquanto todo mundo lança de
`unificado/` — como o README manda — funciona. No dia em que alguém agenda pelo
Agendador de Tarefas do Windows sem preencher "Iniciar em", o CWD vira
`C:\\Windows\\System32`, e nasce uma segunda árvore de dados lá.

Aí o RPA 1 grava numa árvore, o RPA 2 varre a outra, não acha nada, **termina com
sucesso** e registra "nenhum arquivo encontrado".

Não é hipótese: foi o que fez `RAIZ_LOGS` virar absoluto (três árvores de log no
disco, uma por diretório de lançamento) e o que criou
`unificado/historico_arquivos_processados/` — pasta que existe no repositório,
vazia, porque uma execução resolveu o default `.` contra o CWD.

Os testes abaixo rodam o import da configuração **em subprocesso**, com CWD
diferente, porque é a única forma de exercitar o que de fato acontece.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from comum.config import configuration

_RAIZ_UNIFICADO = Path(__file__).resolve().parents[1]

#: As variáveis que apontam para onde o robô lê e escreve. Se qualquer uma delas
#: for relativa, ela se parte em duas árvores conforme quem lança o processo.
VARIAVEIS_DE_CAMINHO = [
    "RAIZ_LOGS",
    "CAMINHO_OPERADORAS",
    "DIRETORIO_ENTRADA",
    "DIRETORIO_NAO_IDENTIFICADOS",
    "DIRETORIO_QUARENTENA",
    "DIRETORIO_HISTORICO_ARQUIVOS",
    "RASTREAMENTO_ARQUIVO_PATH",
    "DIRETORIO_RELATORIO_AGI",
    "DIRETORIO_INCONSISTENCIAS",
]


def _resolver_em(cwd: Path, ambiente: dict[str, str]) -> dict[str, str]:
    """Importa a configuração num processo com o CWD e o ambiente dados."""
    programa = (
        "import sys, json;"
        f"sys.path.insert(0, {str(_RAIZ_UNIFICADO)!r});"
        "from comum.config import configuration as c;"
        f"print(json.dumps({{n: str(getattr(c, n)) for n in {VARIAVEIS_DE_CAMINHO!r}}}))"
    )
    # ⚠️ O subprocesso NÃO roda sob pytest, então ele lê o `.env` — e
    # `load_dotenv()` o procura subindo a árvore a partir do CWD. Rodando de
    # dentro de `unificado/` ele acha; de `tmp_path`, não.
    #
    # Isso não invalida o teste porque o `load_dotenv` do python-dotenv **não
    # sobrescreve** o que já está em `os.environ`: as variáveis passadas aqui
    # vencem nas duas execuções. Por isso a comparação é só sobre elas.
    completo = {**os.environ, **ambiente}

    resultado = subprocess.run(
        [sys.executable, "-c", programa],
        cwd=str(cwd),
        env=completo,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert resultado.returncode == 0, resultado.stderr

    import json

    return json.loads(resultado.stdout.strip().splitlines()[-1])


class TestOndeQuerQueSejaLancado:
    """A prova: o mesmo `.env`, dois CWDs, os mesmos caminhos."""

    def test_relativo_resolve_igual_de_qualquer_diretorio(self, tmp_path):
        ambiente = {
            "CAMINHO_OPERADORAS": "arquivos/Operadoras",
            "DIRETORIO_ENTRADA": "arquivos/Entrada",
        }

        de_dentro = _resolver_em(_RAIZ_UNIFICADO, ambiente)
        de_fora = _resolver_em(tmp_path, ambiente)

        for variavel in ambiente:
            assert de_dentro[variavel] == de_fora[variavel], (
                f"{variavel} mudou conforme o diretório de lançamento — é assim "
                "que nascem duas árvores de dados, sem erro nenhum"
            )

    def test_e_resolve_dentro_de_unificado(self, tmp_path):
        resolvidos = _resolver_em(tmp_path, {"CAMINHO_OPERADORAS": "arquivos/Operadoras"})

        assert resolvidos["CAMINHO_OPERADORAS"] == str(
            _RAIZ_UNIFICADO / "arquivos" / "Operadoras"
        )

    def test_absoluto_passa_intacto(self, tmp_path):
        """Produção usa caminho de rede; ancorar um absoluto o destruiria."""
        alvo = tmp_path / "rede" / "Operadoras"

        resolvidos = _resolver_em(tmp_path, {"CAMINHO_OPERADORAS": str(alvo)})

        assert resolvidos["CAMINHO_OPERADORAS"] == str(alvo)


class TestNenhumCaminhoRelativoSobra:
    @pytest.mark.parametrize("variavel", VARIAVEIS_DE_CAMINHO)
    def test_e_absoluto_com_o_default_do_codigo(self, variavel):
        """
        Mesmo sem nada no `.env`. O default de `DIRETORIO_HISTORICO_ARQUIVOS`
        era `Path("")` -> `Path(".")` — e é dele que veio a pasta órfã.
        """
        assert getattr(configuration, variavel).is_absolute()

    def test_o_ancoramento_e_o_unico_ponto_que_sabe_a_raiz(self):
        assert configuration.RAIZ_UNIFICADO == _RAIZ_UNIFICADO
        assert configuration.RAIZ_UNIFICADO.is_absolute()


class TestAsPastasDeExcecaoFicamForaDaArvore:
    """
    Regra de negócio, não de organização: o RPA 2 varre a raiz das operadoras
    tratando **todo diretório como uma operadora**. E, no caso da quarentena, ele
    acharia o arquivo reprovado e responderia à operadora uma segunda vez.

    Aqui contra caminhos ANCORADOS — antes, o `.resolve()` do teste de contrato
    ancorava no CWD do pytest, o que mascarava a comparação.
    """

    @pytest.mark.parametrize(
        "variavel", ["DIRETORIO_NAO_IDENTIFICADOS", "DIRETORIO_QUARENTENA"]
    )
    def test_fora_da_raiz_das_operadoras(self, variavel):
        raiz = configuration.CAMINHO_OPERADORAS
        excecao = getattr(configuration, variavel)

        assert raiz not in excecao.parents
        assert excecao != raiz
