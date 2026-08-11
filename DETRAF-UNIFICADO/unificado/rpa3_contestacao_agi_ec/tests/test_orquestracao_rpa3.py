"""A orquestração do RPA 3 — ponta a ponta, sem tocar em AGI nem Outlook.

Até 2026-08-04 `gerar_artefatos()` emitia sete `logger.info` de "etapa pendente"
e nada mais: **2.276 linhas de service implementado e testado, sem chamador.**
Estes testes fixam o que passou a ser encadeado, e — mais importante — o que
acontece quando alguma etapa não pode acontecer.

Nenhum teste aqui abre o AGI ou o Outlook: os dois são injetados como dublês que
**explodem** em qualquer chamada. Provar que a execução completa não os toca é
mais forte do que verificar uma flag.
"""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from comum.arquivos import estrutura_pastas as ep
from comum.config import configuration
from comum.config import constantes as const
from src.services import geracao_env_carta as gec
from src.controllers.geracao_agi_controller import (
    GeracaoAgiController,
    ResultadoOperadora,
)

#: Layout das fixtures: descritor na 7ª coluna (índice 6), como a V2 descreve.
INDICE_DESCRITOR = 6


# ---------------------------------------------------------------------------
# Dublês
# ---------------------------------------------------------------------------


class _AGIProibido:
    """Qualquer toque no AGI é falha de teste."""

    def __getattr__(self, nome):
        def _explodir(*args, **kwargs):
            raise AssertionError(f"O AGI foi acionado ('{nome}').")

        return _explodir


class _OutlookProibido:
    def __getattr__(self, nome):
        def _explodir(*args, **kwargs):
            raise AssertionError(f"O Outlook foi acionado ('{nome}').")

        return _explodir


class _UploaderEspiao:
    """Registra as chamadas de upload sem tocar em nada."""

    def __init__(self, nome: str, diario: list):
        self.nome = nome
        self.diario = diario

    def executar(self, operadoras, aaaamm, raiz_operadoras=None, **kwargs):
        self.diario.append((self.nome, list(operadoras), aaaamm))


# ---------------------------------------------------------------------------
# Fixtures de dados
# ---------------------------------------------------------------------------


def _linha_detraf(credora, devedora, trafego, descritor, minutos, r_bruto):
    """Uma linha no layout de 15 colunas da V2."""
    linha = ["0"] * 15
    linha[0] = credora
    linha[1] = devedora
    linha[2] = "202507"
    linha[3] = trafego
    linha[5] = "0"  # Rel: linha de tráfego, não total
    linha[6] = descritor
    linha[9] = minutos
    linha[14] = r_bruto
    return linha


def _escrever_csv(caminho: Path, linhas: list[list[str]]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        "\n".join(";".join(linha) for linha in linhas) + "\n", encoding="utf-8"
    )


@pytest.fixture()
def operadora_com_divergencia(raiz_operadoras):
    """
    CLARO com Detraf e expectativa que divergem muito acima de 1%.

    A seed do conftest tem `(021, 011, 202507, 202507, TU-RL)` como
    "com retenção" — descritor final "L" mapeia para TU-RL.
    """
    _escrever_csv(
        ep.caminho_detrafs_recebidos("CLARO", "202507", raiz_operadoras, criar=True)
        / "DETRAF_D_CLARO_202507.csv",
        [_linha_detraf("021", "011", "202507", "LL", "5000,0", "300,00")],
    )
    _escrever_csv(
        ep.caminho_detrafs_enviados("CLARO", "202507", raiz_operadoras, criar=True)
        / "DE_D_TBRA_CLARO_202507.csv",
        [_linha_detraf("021", "011", "202507", "LL", "1000,0", "50,00")],
    )
    return "CLARO"


@pytest.fixture()
def controller(repo_tabelas, raiz_controle_ct):
    """Controller com AGI e Outlook proibidos, e data fixa para a carta."""
    diario: list = []
    instancia = GeracaoAgiController(
        repositorio=repo_tabelas,
        uploader_detraf=_UploaderEspiao("EXT/INT", diario),
        uploader_contestacao=_UploaderEspiao("CONT_PROC", diario),
        servico_outlook=_OutlookProibido(),
        hoje=date(2026, 8, 4),
    )
    instancia.diario_de_upload = diario
    return instancia


# ---------------------------------------------------------------------------
# Descoberta de operadoras
# ---------------------------------------------------------------------------


class TestDescobertaDeOperadoras:
    def test_varre_a_raiz_quando_nenhuma_e_informada(
        self, controller, raiz_operadoras, operadora_com_divergencia
    ):
        resultados = controller.gerar_artefatos(
            referencia="202507", raiz_operadoras=raiz_operadoras
        )

        assert [r.operadora for r in resultados] == ["CLARO"]

    def test_mes_sem_nenhuma_operadora_nao_e_erro(self, controller, raiz_operadoras):
        """Um mês vazio é estado possível, não incidente."""
        assert (
            controller.gerar_artefatos(
                referencia="202507", raiz_operadoras=raiz_operadoras
            )
            == []
        )

    def test_lista_explicita_permite_reprocessar_uma_operadora(
        self, controller, raiz_operadoras, operadora_com_divergencia
    ):
        outra = ep.caminho_detrafs_recebidos("ALGAR", "202507", raiz_operadoras, criar=True)
        _escrever_csv(
            outra / "DETRAF_D_ALGAR_202507.csv",
            [_linha_detraf("021", "011", "202507", "LL", "1,0", "1,00")],
        )

        resultados = controller.gerar_artefatos(
            operadoras=["CLARO"], referencia="202507", raiz_operadoras=raiz_operadoras
        )

        assert [r.operadora for r in resultados] == ["CLARO"]


# ---------------------------------------------------------------------------
# Fase A — artefatos
# ---------------------------------------------------------------------------


class TestGeracaoDeArtefatos:
    def test_cenario_com_retencao_gera_os_cinco_artefatos(
        self, controller, raiz_operadoras, raiz_controle_ct, operadora_com_divergencia
    ):
        (raiz_controle_ct / "2025").mkdir(parents=True)
        (raiz_controle_ct / "2025" / "CT - 362.docx").write_text("x", encoding="utf-8")

        resultado = controller.gerar_artefatos(
            referencia="202507",
            raiz_operadoras=raiz_operadoras,
            raiz_controle_ct=raiz_controle_ct,
            indice_descritor=INDICE_DESCRITOR,
        )[0]

        assert resultado.erro is None, resultado.erro
        assert resultado.ext and resultado.ext.is_file()
        assert resultado.env and resultado.env.is_file()
        assert resultado.cartas and all(c.is_file() for c in resultado.cartas)
        assert resultado.cont_proc and resultado.cont_proc.is_file()

    def test_a_carta_recebe_o_proximo_numero_ct(
        self, controller, raiz_operadoras, raiz_controle_ct, operadora_com_divergencia
    ):
        (raiz_controle_ct / "2025").mkdir(parents=True)
        (raiz_controle_ct / "2025" / "CT - 362.docx").write_text("x", encoding="utf-8")

        resultado = controller.gerar_artefatos(
            referencia="202507",
            raiz_operadoras=raiz_operadoras,
            raiz_controle_ct=raiz_controle_ct,
            indice_descritor=INDICE_DESCRITOR,
        )[0]

        assert [c for c in resultado.cartas if "363" in c.name]

    def test_operadora_sem_detraf_e_pulada_sem_gerar_ext_vazio(
        self, controller, raiz_operadoras
    ):
        """
        `gerar_arquivo_ext` **não tem guarda de vazio**, ao contrário do
        INT/_ENV/CONT_PROC: sem o short-circuit ele gravaria um `.xlsx` vazio, que
        a HU-17 depois tentaria subir no AGI.
        """
        ep.caminho_detrafs_recebidos("VAZIA", "202507", raiz_operadoras, criar=True)

        resultado = controller.gerar_artefatos(
            referencia="202507", raiz_operadoras=raiz_operadoras
        )[0]

        assert resultado.ext is None
        assert "sem Detraf recebido" in resultado.pulos
        assert not list(
            ep.caminho_agi("VAZIA", "202507", raiz_operadoras).glob("*")
        ) or not ep.caminho_agi("VAZIA", "202507", raiz_operadoras).is_dir()


# ---------------------------------------------------------------------------
# Fase B — ordem e agrupamento da carga
# ---------------------------------------------------------------------------


class TestCargaNoAGI:
    def test_ext_int_sobem_antes_do_cont_proc(
        self, controller, raiz_operadoras, raiz_controle_ct, operadora_com_divergencia
    ):
        """Ordem da V2: `Detraf > Importar Dados`, depois `Contestação > Gerenciar`."""
        controller.gerar_artefatos(
            referencia="202507",
            raiz_operadoras=raiz_operadoras,
            raiz_controle_ct=raiz_controle_ct,
            indice_descritor=INDICE_DESCRITOR,
        )

        assert [nome for nome, _, _ in controller.diario_de_upload] == [
            "EXT/INT",
            "CONT_PROC",
        ]

    def test_a_carga_recebe_o_lote_inteiro_de_uma_vez(
        self, controller, raiz_operadoras, operadora_com_divergencia
    ):
        """
        Abrir e logar no AGI custa minutos. Os uploaders recebem a **lista** e
        abrem uma vez só — por isso a carga fica fora do laço por operadora.
        """
        _escrever_csv(
            ep.caminho_detrafs_recebidos("ALGAR", "202507", raiz_operadoras, criar=True)
            / "DETRAF_D_ALGAR_202507.csv",
            [_linha_detraf("021", "011", "202507", "LL", "9000,0", "800,00")],
        )

        controller.gerar_artefatos(
            referencia="202507", raiz_operadoras=raiz_operadoras,
            indice_descritor=INDICE_DESCRITOR,
        )

        chamadas_ext = [c for c in controller.diario_de_upload if c[0] == "EXT/INT"]
        assert len(chamadas_ext) == 1, "o AGI deve ser aberto uma vez, não por operadora"
        assert set(chamadas_ext[0][1]) == {"ALGAR", "CLARO"}

    def test_sem_artefato_o_agi_nao_e_aberto(self, controller, raiz_operadoras):
        ep.caminho_detrafs_recebidos("VAZIA", "202507", raiz_operadoras, criar=True)

        controller.gerar_artefatos(
            referencia="202507", raiz_operadoras=raiz_operadoras
        )

        assert controller.diario_de_upload == []


# ---------------------------------------------------------------------------
# Kill-switches
# ---------------------------------------------------------------------------


class TestKillSwitches:
    def test_execucao_completa_nao_toca_agi_nem_outlook(
        self, repo_tabelas, raiz_operadoras, raiz_controle_ct,
        operadora_com_divergencia, monkeypatch,
    ):
        """
        Com os dois kill-switches desligados — o default —, a execução inteira
        roda e **nada** externo é acionado. Os dublês explodem ao primeiro toque.
        """
        monkeypatch.setattr(configuration, "PERMITIR_UPLOAD_AGI", False)
        monkeypatch.setattr(configuration, "PERMITIR_ENVIO_EMAIL", False)

        from src.services.upload_contestacao_agi import UploadContestacaoAGI
        from src.services.upload_detraf_agi import UploadDetrafAGI

        controller = GeracaoAgiController(
            repositorio=repo_tabelas,
            uploader_detraf=UploadDetrafAGI(agi=_AGIProibido()),
            uploader_contestacao=UploadContestacaoAGI(
                agi=_AGIProibido(), repositorio=repo_tabelas
            ),
            servico_outlook=_OutlookProibido(),
            hoje=date(2026, 8, 4),
        )

        resultados = controller.gerar_artefatos(
            referencia="202507",
            raiz_operadoras=raiz_operadoras,
            raiz_controle_ct=raiz_controle_ct,
            indice_descritor=INDICE_DESCRITOR,
        )

        assert resultados and resultados[0].erro is None


# ---------------------------------------------------------------------------
# Etapas bloqueadas
# ---------------------------------------------------------------------------


class TestEtapasBloqueadas:
    def test_numeracao_ct_indisponivel_desabilita_a_carta_e_nao_o_resto(
        self, controller, raiz_operadoras, tmp_path, operadora_com_divergencia
    ):
        """
        A numeração CT é **global e serial**: se falha para a primeira operadora,
        falha para todas. Insistir arriscaria emitir número duplicado, o que a
        decisão do cliente de 2026-07-31 proíbe.
        """
        controle_vazio = tmp_path / "CT_inexistente"

        resultado = controller.gerar_artefatos(
            referencia="202507",
            raiz_operadoras=raiz_operadoras,
            raiz_controle_ct=controle_vazio,
            indice_descritor=INDICE_DESCRITOR,
        )[0]

        assert resultado.cartas == []
        assert resultado.env is not None, "o _ENV não depende da numeração"
        assert resultado.ext is not None
        assert resultado.cont_proc is not None
        assert any("numeração CT" in pulo for pulo in resultado.pulos)

    def test_a_carta_fica_desabilitada_para_a_execucao_inteira(
        self, controller, raiz_operadoras, tmp_path
    ):
        for operadora in ("CLARO", "ALGAR"):
            _escrever_csv(
                ep.caminho_detrafs_recebidos(operadora, "202507", raiz_operadoras, criar=True)
                / f"DETRAF_D_{operadora}_202507.csv",
                [_linha_detraf("021", "011", "202507", "LL", "5000,0", "300,00")],
            )
            _escrever_csv(
                ep.caminho_detrafs_enviados(operadora, "202507", raiz_operadoras, criar=True)
                / f"DE_D_TBRA_{operadora}_202507.csv",
                [_linha_detraf("021", "011", "202507", "LL", "1000,0", "50,00")],
            )

        resultados = controller.gerar_artefatos(
            referencia="202507",
            raiz_operadoras=raiz_operadoras,
            raiz_controle_ct=tmp_path / "CT_inexistente",
            indice_descritor=INDICE_DESCRITOR,
        )

        assert all(r.cartas == [] for r in resultados)
        assert controller._carta_habilitada is False

    def test_sem_destinatario_o_outlook_nem_e_aberto(
        self, repo_tabelas, raiz_operadoras, raiz_controle_ct,
        operadora_com_divergencia, monkeypatch,
    ):
        """
        🐛 Corrigido em 2026-08-04. `self.servico_outlook` era avaliado no
        argumento da chamada — ou seja, **antes** de `enviar_contestacao` olhar os
        destinatários. Numa máquina sem perfil Outlook a conexão COM estourava, e
        a operadora era reportada como "e-mail falhou" em vez de "não enviado",
        escondendo que a causa real é a Q16.

        O `_OutlookProibido` explode em qualquer chamada — inclusive na
        construção, se ela acontecesse.
        """
        monkeypatch.setattr(configuration, "PERMITIR_ENVIO_EMAIL", True)
        (raiz_controle_ct / "2025").mkdir(parents=True)
        (raiz_controle_ct / "2025" / "CT - 362.docx").write_text("x", encoding="utf-8")

        controller = GeracaoAgiController(
            repositorio=repo_tabelas,
            uploader_detraf=_UploaderEspiao("EXT/INT", []),
            uploader_contestacao=_UploaderEspiao("CONT_PROC", []),
            # Sem `servico_outlook`: se o controller tentar construir um, o
            # `OutlookService` real seria instanciado e falharia aqui.
            hoje=date(2026, 8, 4),
        )

        resultado = controller.gerar_artefatos(
            referencia="202507",
            raiz_operadoras=raiz_operadoras,
            raiz_controle_ct=raiz_controle_ct,
            indice_descritor=INDICE_DESCRITOR,
        )[0]

        assert "e-mail de contestação não enviado" in resultado.pulos
        assert resultado.erro is None

    def test_email_bloqueado_vira_pulo_e_nao_derruba_a_fase(
        self, controller, raiz_operadoras, raiz_controle_ct, operadora_com_divergencia,
        monkeypatch,
    ):
        """
        `buscar_destinatarios` devolve `[]` porque a tabela de contatos do WebFat
        nunca foi informada (Q16). Isso é bloqueio conhecido, não falha de execução.
        """
        monkeypatch.setattr(configuration, "PERMITIR_ENVIO_EMAIL", True)
        (raiz_controle_ct / "2025").mkdir(parents=True)
        (raiz_controle_ct / "2025" / "CT - 362.docx").write_text("x", encoding="utf-8")

        resultado = controller.gerar_artefatos(
            referencia="202507",
            raiz_operadoras=raiz_operadoras,
            raiz_controle_ct=raiz_controle_ct,
            indice_descritor=INDICE_DESCRITOR,
        )[0]

        assert "e-mail de contestação não enviado" in resultado.pulos
        assert resultado.erro is None


class TestSemExpectativaVivo:
    """
    O EXT depende só do lado da operadora e sai; o `_ENV` é a comparação lado a
    lado e não tem como existir. Antes disto o fluxo estourava com
    "single positional indexer is out-of-bounds" no meio da HU-14.
    """

    @pytest.fixture()
    def so_detraf(self, raiz_operadoras):
        _escrever_csv(
            ep.caminho_detrafs_recebidos("CLARO", "202507", raiz_operadoras, criar=True)
            / "DETRAF_D_CLARO_202507.csv",
            [_linha_detraf("021", "011", "202507", "LL", "5000,0", "300,00")],
        )

    def test_ext_sai_e_env_nao(self, controller, raiz_operadoras, so_detraf):
        resultado = controller.gerar_artefatos(
            referencia="202507", raiz_operadoras=raiz_operadoras,
            indice_descritor=INDICE_DESCRITOR,
        )[0]

        assert resultado.erro is None
        assert resultado.ext is not None
        assert resultado.env is None and resultado.cartas == []

    def test_a_ausencia_e_nomeada_no_resultado(
        self, controller, raiz_operadoras, so_detraf
    ):
        resultado = controller.gerar_artefatos(
            referencia="202507", raiz_operadoras=raiz_operadoras,
            indice_descritor=INDICE_DESCRITOR,
        )[0]

        assert any("expectativa Vivo" in pulo for pulo in resultado.pulos)


class TestResiliencia:
    def test_operadora_com_erro_nao_impede_a_seguinte(
        self, controller, raiz_operadoras, monkeypatch
    ):
        """O mês tem dezenas de operadoras; uma pasta ruim não bloqueia o resto."""
        for operadora in ("AAA_QUEBRA", "BBB_OK"):
            _escrever_csv(
                ep.caminho_detrafs_recebidos(operadora, "202507", raiz_operadoras, criar=True)
                / f"DETRAF_D_{operadora}_202507.csv",
                [_linha_detraf("021", "011", "202507", "LL", "5000,0", "300,00")],
            )

        original = controller._gerar_ext

        def _quebrar_na_primeira(df, operadora, referencia, raiz, indice):
            if operadora == "AAA_QUEBRA":
                raise RuntimeError("disco cheio")
            return original(df, operadora, referencia, raiz, indice)

        monkeypatch.setattr(controller, "_gerar_ext", _quebrar_na_primeira)

        resultados = controller.gerar_artefatos(
            referencia="202507", raiz_operadoras=raiz_operadoras,
            indice_descritor=INDICE_DESCRITOR,
        )

        por_nome = {r.operadora: r for r in resultados}
        assert "disco cheio" in por_nome["AAA_QUEBRA"].erro
        assert por_nome["BBB_OK"].erro is None
        assert por_nome["BBB_OK"].ext is not None

    def test_o_resumo_final_nomeia_quem_falhou(
        self, controller, raiz_operadoras, monkeypatch, caplog
    ):
        _escrever_csv(
            ep.caminho_detrafs_recebidos("CLARO", "202507", raiz_operadoras, criar=True)
            / "DETRAF_D_CLARO_202507.csv",
            [_linha_detraf("021", "011", "202507", "LL", "5000,0", "300,00")],
        )
        monkeypatch.setattr(
            controller,
            "_gerar_ext",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("falhou")),
        )

        with caplog.at_level("ERROR"):
            controller.gerar_artefatos(
                referencia="202507", raiz_operadoras=raiz_operadoras
            )

        assert "CLARO" in caplog.text


class TestCenarioMistoDaCarta:
    """
    Q25, decidida em 2026-08-05 — **uma carta por cenário**.

    O sinal do analista é por chave ``(eot_operadora, eot_tbra, referência,
    tráfego, remuneração)``, então a mesma operadora pode ter linhas COM e SEM
    retenção no mesmo mês. A carta é um documento com **um** texto de cenário;
    antes desta decisão o código emitia uma só, com "prevalece COM retenção".

    A seed do conftest dá as duas linhas: ``(021, 011, TU-RL)`` com retenção e
    ``(021, 012, VU-M)`` sem.
    """

    @pytest.fixture(autouse=True)
    def _controle_ct_semeado(self, raiz_controle_ct):
        """A numeração parte de um CT existente — sem ele, ela é indeterminada."""
        pasta = raiz_controle_ct / "2025"
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "CT - 362.docx").write_text("x", encoding="utf-8")

    @pytest.fixture()
    def operadora_com_os_dois_cenarios(self, raiz_operadoras):
        recebidos = ep.caminho_detrafs_recebidos(
            "CLARO", "202507", raiz_operadoras, criar=True
        )
        enviados = ep.caminho_detrafs_enviados(
            "CLARO", "202507", raiz_operadoras, criar=True
        )
        # Descritor final "L" -> TU-RL (com retenção); final "V" -> VU-M (sem).
        _escrever_csv(
            recebidos / "DETRAF_D_CLARO_202507.csv",
            [
                _linha_detraf("021", "011", "202507", "LL", "5000,0", "300,00"),
                _linha_detraf("021", "012", "202507", "LV", "5000,0", "300,00"),
            ],
        )
        _escrever_csv(
            enviados / "DE_D_TBRA_CLARO_202507.csv",
            [
                _linha_detraf("021", "011", "202507", "LL", "1000,0", "50,00"),
                _linha_detraf("021", "012", "202507", "LV", "1000,0", "50,00"),
            ],
        )
        return "CLARO"

    def test_saem_duas_cartas_com_numeros_ct_consecutivos(
        self, controller, raiz_operadoras, raiz_controle_ct,
        operadora_com_os_dois_cenarios,
    ):
        resultado = controller.gerar_artefatos(
            referencia="202507",
            raiz_operadoras=raiz_operadoras,
            raiz_controle_ct=raiz_controle_ct,
            indice_descritor=INDICE_DESCRITOR,
        )[0]

        assert resultado.erro is None, resultado.erro
        assert len(resultado.cartas) == 2, [c.name for c in resultado.cartas]
        assert all(caminho.is_file() for caminho in resultado.cartas)

        # Consecutivos: a Fase A consome dois números da sequência global na
        # mesma execução — que é o que a trava da Q18 protege.
        numeros = sorted(
            int(gec._PADRAO_NUMERO_CT.search(caminho.name).group(1))
            for caminho in resultado.cartas
        )
        assert numeros == [363, 364]

    def test_o_env_continua_unico(
        self, controller, raiz_operadoras, raiz_controle_ct,
        operadora_com_os_dois_cenarios,
    ):
        """
        Decisão de desenho do desenvolvedor, registrada junto com a Q25: o nome
        do `_ENV` (`Base Contestação_{op}_{mes}_ENV`) não tem cenário, e ele é o
        anexo de dados da contestação inteira. Duas cartas, um `_ENV`.
        """
        resultado = controller.gerar_artefatos(
            referencia="202507",
            raiz_operadoras=raiz_operadoras,
            raiz_controle_ct=raiz_controle_ct,
            indice_descritor=INDICE_DESCRITOR,
        )[0]

        assert resultado.env is not None and resultado.env.is_file()
        assert len(resultado.cartas) == 2

    def test_cenario_unico_gera_uma_carta_so(
        self, controller, raiz_operadoras, raiz_controle_ct,
        operadora_com_divergencia,
    ):
        resultado = controller.gerar_artefatos(
            referencia="202507",
            raiz_operadoras=raiz_operadoras,
            raiz_controle_ct=raiz_controle_ct,
            indice_descritor=INDICE_DESCRITOR,
        )[0]

        assert len(resultado.cartas) == 1


class TestModoSoLeitura:
    """
    Q20, decidida em 2026-08-05 — validar contra produção, com cuidado.

    **Não existe ambiente de teste do AGI.** A validação vai ter que acontecer
    contra produção, e a proteção é a combinação de kill-switches::

        PERMITIR_ACESSO_AGI=true      # abre o AGI e baixa o relatório
        PERMITIR_UPLOAD_AGI=false     # não sobe nada
        PERMITIR_ENVIO_EMAIL=false    # não envia e-mail

    O roteiro está em `docs/03-checklists/checklist-validacao-agi.md`. O que se
    prova aqui é a premissa dele: **nessa combinação, nada é escrito para fora.**
    Sem este teste o checklist seria só uma promessa.
    """

    @pytest.fixture()
    def controller_com_agi_proibido(self, repo_tabelas, monkeypatch):
        """
        Os uploaders são os **reais**, ligados a um AGI que explode ao primeiro
        toque. É de propósito: a guarda mora dentro do uploader, e substituí-lo
        por um dublê testaria o dublê, não a proteção.
        """
        from src.services.upload_contestacao_agi import UploadContestacaoAGI
        from src.services.upload_detraf_agi import UploadDetrafAGI

        monkeypatch.setattr(configuration, "PERMITIR_ACESSO_AGI", True)
        monkeypatch.setattr(configuration, "PERMITIR_UPLOAD_AGI", False)
        monkeypatch.setattr(configuration, "PERMITIR_ENVIO_EMAIL", False)

        return GeracaoAgiController(
            repositorio=repo_tabelas,
            uploader_detraf=UploadDetrafAGI(agi=_AGIProibido()),
            uploader_contestacao=UploadContestacaoAGI(
                agi=_AGIProibido(), repositorio=repo_tabelas
            ),
            servico_outlook=_OutlookProibido(),
            hoje=date(2026, 8, 4),
        )

    def test_nenhum_upload_e_nenhum_envio(
        self, controller_com_agi_proibido, raiz_operadoras, raiz_controle_ct,
        operadora_com_divergencia,
    ):
        """
        O fluxo inteiro roda — EXT, INT, `_ENV`, carta, CONT_PROC saem —, e nem o
        uploader nem o Outlook são tocados. Qualquer chamada a eles é
        `AssertionError`.
        """
        (raiz_controle_ct / "2025").mkdir(parents=True)
        (raiz_controle_ct / "2025" / "CT - 362.docx").write_text("x", encoding="utf-8")

        resultado = controller_com_agi_proibido.gerar_artefatos(
            referencia="202507",
            raiz_operadoras=raiz_operadoras,
            raiz_controle_ct=raiz_controle_ct,
            indice_descritor=INDICE_DESCRITOR,
        )[0]

        assert resultado.erro is None, resultado.erro
        assert resultado.gerou_algo, "os artefatos locais continuam sendo gerados"

    def test_o_upload_para_antes_de_tocar_no_agi(self, monkeypatch, raiz_operadoras):
        """
        A guarda está **no uploader**, não no controller — é ela que garante que
        ligar `PERMITIR_ACESSO_AGI` para a HU-20 não abre a porta para a carga.
        """
        from src.services import upload_detraf_agi as ud

        monkeypatch.setattr(configuration, "PERMITIR_ACESSO_AGI", True)
        monkeypatch.setattr(configuration, "PERMITIR_UPLOAD_AGI", False)
        pasta = ep.caminho_agi("CLARO", "202507", raiz_operadoras, criar=True)
        (pasta / "EXT_CLARO_202507.csv").write_text("x", encoding="utf-8")

        ud.UploadDetrafAGI(agi=_AGIProibido()).executar(
            ["CLARO"], "202507", raiz_operadoras
        )


class TestRecortePorEtapa:
    """
    `--etapa`, acrescentado em 2026-08-06 para a homologação manual.

    O ponto é poder **repetir a etapa que falhou sem refazer as anteriores**.
    Isso só é legítimo porque as três últimas fases leem o disco e o banco, não
    o resultado da primeira: o uploader varre a pasta AGI, a HU-15 varre a pasta
    Contestações e a HU-20 lê o relatório baixado.
    """

    def test_sem_etapa_roda_tudo(
        self, controller, raiz_operadoras, raiz_controle_ct, operadora_com_divergencia
    ):
        resultado = controller.gerar_artefatos(
            referencia="202507",
            raiz_operadoras=raiz_operadoras,
            raiz_controle_ct=raiz_controle_ct,
            indice_descritor=INDICE_DESCRITOR,
        )[0]

        assert resultado.gerou_algo
        assert controller.diario_de_upload, "a carga deve ter sido chamada"

    def test_etapa_artefatos_nao_chama_a_carga(
        self, controller, raiz_operadoras, raiz_controle_ct, operadora_com_divergencia
    ):
        resultado = controller.gerar_artefatos(
            referencia="202507",
            raiz_operadoras=raiz_operadoras,
            raiz_controle_ct=raiz_controle_ct,
            indice_descritor=INDICE_DESCRITOR,
            etapa="artefatos",
        )[0]

        assert resultado.gerou_algo, "os artefatos continuam saindo"
        assert controller.diario_de_upload == []

    def test_etapa_carga_nao_regera_os_artefatos(
        self, controller, raiz_operadoras, raiz_controle_ct, operadora_com_divergencia
    ):
        """
        A carga vale para a operadora **mesmo sem ter gerado nada agora** — é o
        caso de uso: os arquivos já estão em disco da rodada anterior. Filtrar
        por `gerou_algo` aqui deixaria a lista vazia e a etapa não faria nada,
        que é exatamente o que se quer evitar.

        O que ela olha é o **disco**, e não a lista de operadoras do mês — ver
        `test_etapa_carga_ignora_quem_nao_tem_artefato`.
        """
        (
            ep.caminho_agi("CLARO", "202507", raiz_operadoras, criar=True)
            / "DETRAF_EXT_CLARO_202507.csv"
        ).write_text("de uma rodada anterior", encoding="utf-8")

        resultado = controller.gerar_artefatos(
            referencia="202507",
            raiz_operadoras=raiz_operadoras,
            raiz_controle_ct=raiz_controle_ct,
            indice_descritor=INDICE_DESCRITOR,
            etapa="carga",
        )[0]

        assert not resultado.gerou_algo, "nenhum artefato foi regerado"
        assert controller.diario_de_upload, "mas a carga rodou para a operadora"

    def test_etapa_carga_ignora_quem_nao_tem_artefato(
        self, controller, raiz_operadoras, raiz_controle_ct, operadora_com_divergencia
    ):
        """
        🔴 Regressão de um defeito real (2026-08-07).

        Com `--etapa carga`, a fase de artefatos não roda e devolve resultados
        vazios. O código antigo caía em `list(operadoras)` e mandava para o AGI
        **todas** as operadoras do mês — inclusive as que nunca geraram nada.

        A pasta AGI da CLARO está vazia aqui: nada deve subir.
        """
        controller.gerar_artefatos(
            referencia="202507",
            raiz_operadoras=raiz_operadoras,
            raiz_controle_ct=raiz_controle_ct,
            indice_descritor=INDICE_DESCRITOR,
            etapa="carga",
        )

        assert not controller.diario_de_upload, (
            "operadora sem artefato em disco foi mandada para o AGI"
        )

    def test_a_etapa_pulada_e_anunciada(
        self, controller, raiz_operadoras, raiz_controle_ct,
        operadora_com_divergencia, caplog,
    ):
        """Quem homologa precisa ver que a etapa não rodou por opção, não por falha."""
        with caplog.at_level("INFO"):
            controller.gerar_artefatos(
                referencia="202507",
                raiz_operadoras=raiz_operadoras,
                raiz_controle_ct=raiz_controle_ct,
                indice_descritor=INDICE_DESCRITOR,
                etapa="artefatos",
            )

        assert "'carga' pulada" in caplog.text
        assert "--etapa=artefatos" in caplog.text
