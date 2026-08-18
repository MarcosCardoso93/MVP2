"""HU-15 — envio do e-mail de contestação (Projeto 5).

O Projeto 5 veio sem nenhum teste. O que se cobre aqui é o que é determinístico:
assunto, corpo, localização dos dois anexos na estrutura de pastas real, e o
kill-switch — que é a única proteção contra disparar e-mail para a operadora
enquanto as duas pontas de banco ainda não estão ligadas.
"""

from pathlib import Path

import pytest

from comum.arquivos import estrutura_pastas as ep
from comum.arquivos import nomenclatura as nom
from comum.config import configuration
from src.services import envio_email_contestacao as envio


@pytest.fixture()
def pasta_contestacoes(raiz_operadoras: Path) -> Path:
    return ep.caminho_contestacoes("CLARO", "202507", raiz_operadoras, criar=True)


@pytest.fixture()
def anexos_prontos(pasta_contestacoes: Path) -> tuple[Path, Path]:
    """Simula o que a HU-14 deixa na pasta: a carta CT e o `_EXP`."""
    carta = pasta_contestacoes / "CT - 363.docx"
    env = pasta_contestacoes / f"{nom.nome_env('CLARO', '202507')}.xlsx"
    carta.write_text("carta", encoding="utf-8")
    env.write_text("env", encoding="utf-8")
    return carta, env


@pytest.fixture()
def mock_contatos_bd(monkeypatch):
    """Substitui a consulta a `tbl_detraf_destinatarios` por um resultado fixo."""

    def _definir(para=None, copia=None):
        resultado = {"para": list(para or []), "copia": list(copia or [])}
        monkeypatch.setattr(
            envio.bd_tabelas, "obter_contatos_operadora", lambda *a, **k: resultado
        )
        return resultado

    return _definir


class _OutlookFalso:
    def __init__(self):
        self.enviados: list[dict] = []

    def send_email_com_anexos(self, to, subject, body, anexos=None, cc=None):
        self.enviados.append(
            {
                "to": to,
                "cc": list(cc or []),
                "subject": subject,
                "body": body,
                "anexos": list(anexos or []),
            }
        )


class TestAssuntoECorpo:
    def test_assunto_segue_o_criterio_de_aceite(self):
        assert envio.montar_assunto("CLARO", "202507") == "CONTESTAÇÃO_TBRA|CLARO_202507"

    def test_corpo_traz_o_texto_da_v2_com_o_mes(self):
        corpo = envio.montar_corpo("202507")

        assert corpo.startswith("Prezados,")
        assert "referente ao mês 202507" in corpo


class TestLocalizacaoDosAnexos:
    def test_encontra_carta_e_env_na_pasta_da_operadora(
        self, raiz_operadoras, anexos_prontos
    ):
        carta_esperada, env_esperado = anexos_prontos

        cartas, env = envio.localizar_anexos("CLARO", "202507", raiz_operadoras)

        assert (cartas, env) == ([carta_esperada], env_esperado)

    def test_pasta_inexistente_devolve_nada_sem_levantar(self, raiz_operadoras):
        """
        O original varria uma pasta plana e retornava `(None, None)` calado. Aqui a
        ausência continua não sendo exceção — quem decide é `enviar_contestacao`.
        """
        assert envio.localizar_anexos("OPERADORA_SEM_PASTA", "202507", raiz_operadoras) == (
            [],
            None,
        )

    def test_env_de_outro_mes_nao_e_confundido(self, raiz_operadoras, pasta_contestacoes):
        """O nome do `_EXP` é determinístico — não vale casar por substring."""
        (pasta_contestacoes / f"{nom.nome_env('CLARO', '202506')}.xlsx").write_text(
            "mes errado", encoding="utf-8"
        )

        _, env = envio.localizar_anexos("CLARO", "202507", raiz_operadoras)

        assert env is None

    def test_duas_cartas_vao_as_duas(
        self, raiz_operadoras, pasta_contestacoes, anexos_prontos
    ):
        """
        Desde a Q25 (2026-08-05), duas cartas são o caso **normal** da operadora
        com linhas COM e SEM retenção no mesmo mês — uma por cenário, cada uma
        com o seu número CT. Antes o código pegava a mais recente e descartava a
        outra, o que deixaria um cenário sem carta na caixa da operadora.
        """
        outra = pasta_contestacoes / "CT - 364.docx"
        outra.write_text("carta do outro cenário", encoding="utf-8")

        cartas, _ = envio.localizar_anexos("CLARO", "202507", raiz_operadoras)

        assert sorted(cartas) == sorted([anexos_prontos[0], outra])

    def test_as_duas_cartas_e_o_env_sao_anexados(
        self, raiz_operadoras, pasta_contestacoes, anexos_prontos, monkeypatch
    ):
        """Duas cartas + **um** `_EXP` — a decisão de desenho registrada na Q25."""
        outra = pasta_contestacoes / "CT - 364.docx"
        outra.write_text("carta do outro cenário", encoding="utf-8")
        monkeypatch.setattr(
            envio, "buscar_destinatarios",
            lambda op: envio.Destinatarios(para=["op@exemplo.com"]),
        )
        monkeypatch.setattr(configuration, "PERMITIR_ENVIO_EMAIL", True)
        outlook = _OutlookFalso()

        envio.enviar_contestacao("CLARO", "202507", outlook, raiz_operadoras)

        anexos = outlook.enviados[0]["anexos"]
        assert len(anexos) == 3
        assert anexos[-1] == anexos_prontos[1], "o _EXP vai por último"


class TestPendenciasBloqueadas:
    """As pontas que dependem do banco devolvem vazio — de propósito."""

    def test_operadora_sem_linha_na_tabela_nao_envia(self, mock_contatos_bd):
        """Q16 resolvida (2026-08-18): a fonte agora é o banco, não mais o CSV."""
        mock_contatos_bd(para=[], copia=[])

        assert envio.buscar_destinatarios("ALGAR").para == []

    def test_busca_de_sinalizadas_nao_devolve_nada_sem_controle_de_reenvio(self):
        assert envio.buscar_contestacoes_sinalizadas() == []


class TestContatosPorBanco:
    """
    Q16 resolvida em 2026-08-18 — os contatos por operadora vêm de
    `tbl_detraf_destinatarios` (banco webfat, produto Detraf), via
    `bd_tabelas.obter_contatos_operadora`. `envio_email_contestacao` só traduz o
    resultado para `Destinatarios`; a normalização de nome (case/espaço) e o
    split por vírgula da coluna `operadora` moram na camada de dados
    (`comum.dados.repositorio_tabelas`), cobertos em separado.

    ⚠️ Com destinatário em `Para` **e** `PERMITIR_ENVIO_EMAIL=true`, o robô envia
    de verdade. O kill-switch é a única proteção.
    """

    def test_le_os_emails_da_operadora(self, mock_contatos_bd):
        mock_contatos_bd(
            para=["contestacao@claro.com.br", "faturamento@claro.com.br"]
        )

        assert envio.buscar_destinatarios("CLARO").para == [
            "contestacao@claro.com.br",
            "faturamento@claro.com.br",
        ]

    def test_operadora_ausente_no_banco_nao_envia(self, mock_contatos_bd, caplog):
        mock_contatos_bd(para=[])

        with caplog.at_level("WARNING"):
            assert envio.buscar_destinatarios("ALGAR").para == []

        assert "ALGAR" in caplog.text

    def test_com_contato_e_kill_switch_ligado_o_envio_acontece(
        self, mock_contatos_bd, raiz_operadoras, anexos_prontos, monkeypatch
    ):
        """De ponta a ponta: banco -> Destinatarios -> Outlook."""
        mock_contatos_bd(para=["contestacao@claro.com.br"])
        monkeypatch.setattr(configuration, "PERMITIR_ENVIO_EMAIL", True)
        outlook = _OutlookFalso()

        envio.enviar_contestacao("CLARO", "202507", outlook, raiz_operadoras)

        assert len(outlook.enviados) == 1
        assert outlook.enviados[0]["to"] == ["contestacao@claro.com.br"]


class TestEnvio:
    def test_sem_destinatario_nao_envia_e_acusa(
        self, raiz_operadoras, anexos_prontos, monkeypatch
    ):
        """Operadora sem contato em tbl_detraf_destinatarios ⇒ recusa, não manda pra ninguém."""
        monkeypatch.setattr(configuration, "PERMITIR_ENVIO_EMAIL", True)
        monkeypatch.setattr(
            envio, "buscar_destinatarios", lambda op: envio.Destinatarios()
        )
        outlook = _OutlookFalso()

        with pytest.raises(envio.EnvioEmailContestacaoIncompleto, match="destinatários"):
            envio.enviar_contestacao("CLARO", "202507", outlook, raiz_operadoras)

        assert outlook.enviados == []

    def test_falta_de_anexo_e_nomeada_no_erro(
        self, raiz_operadoras, pasta_contestacoes, monkeypatch
    ):
        monkeypatch.setattr(configuration, "PERMITIR_ENVIO_EMAIL", True)
        monkeypatch.setattr(
            envio, "buscar_destinatarios",
            lambda op: envio.Destinatarios(para=["op@exemplo.com"]),
        )

        with pytest.raises(envio.EnvioEmailContestacaoIncompleto) as erro:
            envio.enviar_contestacao("CLARO", "202507", _OutlookFalso(), raiz_operadoras)

        assert "carta CT" in str(erro.value) and "_EXP" in str(erro.value)

    def test_kill_switch_desligado_monta_e_nao_envia(
        self, raiz_operadoras, anexos_prontos, monkeypatch
    ):
        monkeypatch.setattr(configuration, "PERMITIR_ENVIO_EMAIL", False)
        monkeypatch.setattr(
            envio, "buscar_destinatarios",
            lambda op: envio.Destinatarios(para=["op@exemplo.com"]),
        )
        outlook = _OutlookFalso()

        envio.enviar_contestacao("CLARO", "202507", outlook, raiz_operadoras)

        assert outlook.enviados == []

    def test_com_tudo_pronto_envia_carta_e_env(
        self, raiz_operadoras, anexos_prontos, monkeypatch
    ):
        monkeypatch.setattr(configuration, "PERMITIR_ENVIO_EMAIL", True)
        monkeypatch.setattr(
            envio, "buscar_destinatarios",
            lambda op: envio.Destinatarios(para=["op@exemplo.com"]),
        )
        outlook = _OutlookFalso()

        envio.enviar_contestacao("CLARO", "202507", outlook, raiz_operadoras)

        enviado = outlook.enviados[0]
        assert enviado["to"] == ["op@exemplo.com"]
        assert enviado["subject"] == "CONTESTAÇÃO_TBRA|CLARO_202507"
        assert enviado["anexos"] == list(anexos_prontos)


class TestParaECopiaPorBanco:
    """
    Para/Cc vêm de `tbl_detraf_destinatarios` — `tipo_destinatario` distingue
    os dois. O split e o dedup de "mesmo e-mail em Para e Cc" moram na camada
    de dados (`comum.dados.repositorio_tabelas.obter_contatos_operadora`); aqui
    testa-se só que `buscar_destinatarios` repassa a distinção sem embaralhar.
    """

    def test_para_e_cc_sao_separados(self, mock_contatos_bd):
        mock_contatos_bd(
            para=["contestacao@claro.com.br", "fiscal@claro.com.br"],
            copia=["gestor@claro.com.br"],
        )

        destinatarios = envio.buscar_destinatarios("CLARO")

        assert destinatarios.para == ["contestacao@claro.com.br", "fiscal@claro.com.br"]
        assert destinatarios.copia == ["gestor@claro.com.br"]

    def test_endereco_em_cc_que_tambem_esta_no_para_nao_duplica(self, mock_contatos_bd):
        """Alguém cadastrado como PARA e CC ao mesmo tempo — o Para prevalece."""
        mock_contatos_bd(
            para=["contestacao@claro.com.br"],
            copia=["contestacao@claro.com.br", "gestor@claro.com.br"],
        )

        destinatarios = envio.buscar_destinatarios("CLARO")

        assert destinatarios.para == ["contestacao@claro.com.br"]
        assert destinatarios.copia == ["gestor@claro.com.br"]


class TestCopiaFixa:
    """
    A cópia fixa não tem equivalente em `tbl_detraf_destinatarios` — continua
    vindo do CSV opcional de `CAMINHO_CONTATOS_OPERADORAS`, linha `*`.

    Um print do e-mail de contestação em composição, embutido no `.docx`
    normativo, mostrou o endereço interno que aparece em Cc de todo envio, e
    que não é da operadora. Sem isso, ou a cópia fixa some (e alguém deixa de
    ser avisado), ou vai para o `Para` — e a operadora vê um endereço interno
    da Vivo entre os destinatários diretos.
    """

    @pytest.fixture()
    def copia_fixa_csv(self, tmp_path, monkeypatch):
        def _escrever(conteudo: str):
            caminho = tmp_path / "contatos.csv"
            caminho.write_text(conteudo, encoding="utf-8")
            monkeypatch.setattr(configuration, "CAMINHO_CONTATOS_OPERADORAS", caminho)
            return caminho

        return _escrever

    def test_sem_arquivo_configurado_nao_aplica_nem_falha(self, mock_contatos_bd, monkeypatch):
        mock_contatos_bd(para=["contestacao@claro.com.br"])
        monkeypatch.setattr(configuration, "CAMINHO_CONTATOS_OPERADORAS", None)

        assert envio.buscar_destinatarios("CLARO").copia == []

    def test_a_copia_fixa_entra_em_todos(self, mock_contatos_bd, copia_fixa_csv):
        mock_contatos_bd(para=["contestacao@claro.com.br"])
        copia_fixa_csv("*;;atacado@exemplo.com.br\n")

        assert envio.buscar_destinatarios("CLARO").copia == ["atacado@exemplo.com.br"]

    def test_a_copia_fixa_nunca_vai_para_o_para(self, mock_contatos_bd, copia_fixa_csv):
        """
        A operadora não pode ver um endereço interno da Vivo entre os
        destinatários diretos. Mesmo escrito na coluna `para` da linha `*`, o
        sentido da cópia fixa é sempre "em cópia".
        """
        mock_contatos_bd(para=["contestacao@claro.com.br"])
        copia_fixa_csv("*;atacado@exemplo.com.br;\n")

        destinatarios = envio.buscar_destinatarios("CLARO")

        assert destinatarios.para == ["contestacao@claro.com.br"]
        assert destinatarios.copia == ["atacado@exemplo.com.br"]

    def test_comentario_e_linha_em_branco_sao_ignorados(self, mock_contatos_bd, copia_fixa_csv):
        """O arquivo é editado à mão por quem opera."""
        mock_contatos_bd(para=["contestacao@claro.com.br"])
        copia_fixa_csv(
            """# revisado em 2026-08

*;;atacado@exemplo.com.br
"""
        )

        assert envio.buscar_destinatarios("CLARO").copia == ["atacado@exemplo.com.br"]

    def test_endereco_repetido_nao_duplica(self, mock_contatos_bd, copia_fixa_csv):
        """Receber o mesmo e-mail duas vezes é ruído, não redundância útil."""
        mock_contatos_bd(para=["contestacao@claro.com.br"])
        copia_fixa_csv("*;;atacado@exemplo.com.br,atacado@exemplo.com.br\n")

        assert envio.buscar_destinatarios("CLARO").copia == ["atacado@exemplo.com.br"]

    def test_arquivo_configurado_mas_inexistente_nao_bloqueia_o_envio(
        self, mock_contatos_bd, tmp_path, monkeypatch, caplog
    ):
        """
        Diferente do CSV antigo (obrigatório): a cópia fixa é um extra. Um
        caminho errado no `.env` vira aviso, não impede o envio principal.
        """
        mock_contatos_bd(para=["contestacao@claro.com.br"])
        monkeypatch.setattr(
            configuration, "CAMINHO_CONTATOS_OPERADORAS", tmp_path / "nao-existe.csv"
        )

        with caplog.at_level("WARNING"):
            destinatarios = envio.buscar_destinatarios("CLARO")

        assert destinatarios.para == ["contestacao@claro.com.br"]
        assert destinatarios.copia == []
        assert "CAMINHO_CONTATOS_OPERADORAS" in caplog.text

    def test_so_copia_fixa_nao_basta_para_enviar(self, mock_contatos_bd, copia_fixa_csv):
        """
        Sem ninguém em `Para` (vindo do banco), não há e-mail: mandar a
        contestação só para a cópia interna seria pior do que não mandar.
        """
        mock_contatos_bd(para=[])
        copia_fixa_csv("*;;atacado@exemplo.com.br\n")

        assert bool(envio.buscar_destinatarios("CLARO")) is False

    def test_o_cc_chega_ao_outlook(
        self, mock_contatos_bd, copia_fixa_csv, raiz_operadoras, anexos_prontos, monkeypatch
    ):
        mock_contatos_bd(
            para=["contestacao@claro.com.br"], copia=["gestor@claro.com.br"]
        )
        copia_fixa_csv("*;;atacado@exemplo.com.br\n")
        monkeypatch.setattr(configuration, "PERMITIR_ENVIO_EMAIL", True)
        outlook = _OutlookFalso()

        envio.enviar_contestacao("CLARO", "202507", outlook, raiz_operadoras)

        enviado = outlook.enviados[0]
        assert enviado["to"] == ["contestacao@claro.com.br"]
        assert enviado["cc"] == ["gestor@claro.com.br", "atacado@exemplo.com.br"]
