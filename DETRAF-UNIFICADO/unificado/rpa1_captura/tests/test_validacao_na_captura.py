"""O portão de validação na captura (2026-08-06).

Até aqui o RPA 1 copiava o arquivo para a pasta da operadora sem olhar o
conteúdo, e quem descobria que ele estava errado era o RPA 2 — uma execução
depois, com o arquivo ruim já dentro da árvore. Agora a captura valida antes de
salvar, põe o reprovado em quarentena e responde à operadora com os motivos.

O que estes testes protegem, em ordem de importância:

1. **nada reprovado entra na raiz das operadoras**. É a razão de a mudança
   existir; se isso falhar, tudo o mais é decoração;
2. **a ordem "validar antes de identificar"**. Um arquivo quebrado costuma
   falhar também na leitura da EOT: identificando primeiro, ele cairia em
   `_NAO_IDENTIFICADOS` e ninguém seria avisado;
3. **"não consegui validar" não é "reprovado"**. Banco fora do ar não pode virar
   acusação enviada a todas as operadoras.
"""

import pandas as pd
import pytest

from comum.config import configuration
from comum.dados import tabelas
from src.models.dto.arquivo_para_processar import ArquivoParaProcessar
from src.services.processamento_service import ProcessamentoService

from test_processamento_service import (
    CABECALHO,
    _escrever_detraf,
    _ler_log,
    _preparar_diretorios,
)


@pytest.fixture()
def ambiente(tmp_path, monkeypatch):
    """Diretórios do RPA 1 mais a quarentena, todos sob `tmp_path`."""
    entrada, operadoras, nao_identificados = _preparar_diretorios(tmp_path, monkeypatch)
    quarentena = tmp_path / "_QUARENTENA"
    monkeypatch.setattr(configuration, "DIRETORIO_QUARENTENA", quarentena)
    monkeypatch.setattr(configuration, "NOTIFICAR_OPERADORA_ENVIAR", False)
    return entrada, operadoras, nao_identificados, quarentena


class _Notificador:
    """
    Registra as chamadas em vez de falar com o Outlook.

    Uma chamada por **e-mail de origem**, não por arquivo: cada uma traz a lista
    de recusas daquele envio.
    """

    def __init__(self, resultado: bool = True, erro: Exception | None = None):
        self.chamadas: list[tuple[str, list]] = []
        self._resultado = resultado
        self._erro = erro

    def __call__(self, pacote, recusas) -> bool:
        self.chamadas.append((pacote.caminho.name, list(recusas)))
        if self._erro is not None:
            raise self._erro
        return self._resultado

    @property
    def motivos_do_primeiro(self) -> list[str]:
        """Atalho para o caso de um arquivo só, que é o comum nos testes."""
        return list(self.chamadas[0][1][0].motivos)

    def nomes_recusados(self) -> list[str]:
        return sorted(
            recusa.nome for _, recusas in self.chamadas for recusa in recusas
        )


def _pacote(caminho, **extras) -> ArquivoParaProcessar:
    extras.setdefault("sender_email", "ops@megatelecom.com.br")
    extras.setdefault("entry_id", "ENTRY-1")
    return ArquivoParaProcessar(caminho=caminho, **extras)


def _arquivos_em(pasta) -> list[str]:
    return sorted(p.name for p in pasta.rglob("*") if p.is_file())


class TestNadaReprovadoEntraNaArvore:
    """O teste que justifica a mudança inteira."""

    def test_layout_quebrado_nao_cria_nada_em_operadoras(self, ambiente):
        entrada, operadoras, _, _ = ambiente
        caminho = entrada / "quebrado.csv"
        caminho.write_text("Credora;Devedora\n112;010\n", encoding="utf-8")

        ProcessamentoService(notificar=_Notificador()).executar([_pacote(caminho)])

        assert list(operadoras.iterdir()) == []

    def test_regra_de_coluna_quebrada_tambem_nao(self, ambiente):
        """
        Layout certo, valor errado: tarifa zero.

        A tarifa zerada é o desvio que separa as duas camadas — para o layout ela
        é um número como qualquer outro (posição válida), e só a regra de coluna
        sabe que "não existe tarifa zero".
        """
        entrada, operadoras, _, _ = ambiente
        caminho = entrada / "tarifa_zero.csv"
        _escrever_detraf(caminho, tarifa="0")

        ProcessamentoService(notificar=_Notificador()).executar([_pacote(caminho)])

        assert list(operadoras.iterdir()) == []

    def test_arquivo_valido_continua_entrando(self, ambiente):
        """A rede não pode ser apertada a ponto de barrar o que está certo."""
        entrada, operadoras, _, quarentena = ambiente
        caminho = entrada / "bom.csv"
        _escrever_detraf(caminho)

        ProcessamentoService(notificar=_Notificador()).executar([_pacote(caminho)])

        assert _arquivos_em(operadoras) == ["bom.csv"]
        assert not quarentena.exists() or _arquivos_em(quarentena) == []


class TestALinhaDeTotalNaoReprovaOArquivo:
    """
    🔴 Regressão do defeito mais caro desta série (2026-08-07).

    Todo Detraf real termina com uma **linha de total**: `Rel = 1` e os demais
    campos VAZIOS — inclusive as EOTs. O RPA 2 sempre a removeu antes de validar
    as colunas (`manter_linhas_por_lista_valores`, índice 5); o portão que subiu
    para o RPA 1 em 2026-08-06 **não removia**.

    O efeito: a EOT vazia da linha de total reprovava em "há códigos de operadora
    que não constam do Anexo 5", e o portão recusava **100% dos arquivos
    válidos** — respondendo a todas as operadoras.

    Só apareceu ao rodar contra arquivos reais pela primeira vez. Os dois Detrafs
    da ALGAR foram recusados por uma única linha cada.
    """

    def _escrever_com_total(self, caminho) -> None:
        from tests_apoio import linha

        boa = linha(credora="112", devedora="010")
        # A linha de total como ela vem de verdade: Rel preenchido, resto vazio.
        total = [""] * 15
        total[5] = "01"

        caminho.write_text(
            "\n".join(
                [";".join(CABECALHO), ";".join(boa), ";".join(total)]
            )
            + "\n",
            encoding="utf-8",
        )

    def test_arquivo_com_linha_de_total_e_APROVADO(self, ambiente):
        entrada, operadoras, _, quarentena = ambiente
        caminho = entrada / "com_total.csv"
        self._escrever_com_total(caminho)

        servico = ProcessamentoService(notificar=_Notificador())
        servico.executar([_pacote(caminho)])

        assert servico._reprovados == [], (
            "a linha de total reprovou o arquivo — o portão recusaria todo "
            "Detraf real"
        )
        assert _arquivos_em(operadoras) == ["com_total.csv"]

    def test_a_operadora_nao_e_notificada_por_causa_do_total(self, ambiente):
        entrada, _, _, _ = ambiente
        caminho = entrada / "com_total.csv"
        self._escrever_com_total(caminho)

        notificador = _Notificador()
        ProcessamentoService(notificar=notificador).executar([_pacote(caminho)])

        assert notificador.chamadas == []

    def test_uma_linha_de_dados_ruim_continua_reprovando(self, ambiente):
        """
        A remoção é só das linhas de TOTAL. Ignorar linha de dados ruim
        esvaziaria o portão.
        """
        from tests_apoio import linha

        entrada, operadoras, _, _ = ambiente
        caminho = entrada / "ruim_com_total.csv"
        ruim = linha(credora="112", devedora="010", tarifa="0")
        total = [""] * 15
        total[5] = "01"
        caminho.write_text(
            "\n".join([";".join(CABECALHO), ";".join(ruim), ";".join(total)]) + "\n",
            encoding="utf-8",
        )

        servico = ProcessamentoService(notificar=_Notificador())
        servico.executar([_pacote(caminho)])

        assert len(servico._reprovados) == 1
        assert list(operadoras.iterdir()) == []


class TestAQuarentena:
    def test_o_arquivo_vai_para_a_quarentena_do_mes(self, ambiente):
        entrada, _, _, quarentena = ambiente
        caminho = entrada / "gh_invalido.csv"
        _escrever_detraf(caminho, gh="X")

        ProcessamentoService(notificar=_Notificador()).executar([_pacote(caminho)])

        assert (quarentena / "202507" / "ENTRY-1" / "gh_invalido.csv").is_file()

    def test_o_diagnostico_fica_ao_lado_da_copia(self, ambiente):
        """
        E **não** ao lado do original: o original está em DIRETORIO_ENTRADA, que
        é transitória e a captura repovoa. Quem investiga olha a quarentena.
        """
        entrada, _, _, quarentena = ambiente
        caminho = entrada / "tarifa_zero.csv"
        _escrever_detraf(caminho, tarifa="0")

        ProcessamentoService(notificar=_Notificador()).executar([_pacote(caminho)])

        recusa = quarentena / "202507" / "ENTRY-1" / "tarifa_zero_RECUSADO.md"
        assert recusa.is_file()
        assert "Coluna 11" in recusa.read_text(encoding="utf-8")
        assert not (entrada / "tarifa_zero_RECUSADO.md").exists()

    def test_o_diagnostico_de_layout_traz_a_posicao(self, ambiente):
        """
        As duas camadas descrevem a recusa em vocabulários diferentes, e é
        deliberado: o layout fala em **posição** ("posição 7 (GH)"), porque o que
        ele suspeita é que as colunas estão deslocadas; a regra de coluna fala em
        **coluna** ("Coluna 8 (GH)"), porque ali a posição já está confirmada.
        """
        entrada, _, _, quarentena = ambiente
        caminho = entrada / "quebrado.csv"
        caminho.write_text("Credora;Devedora\n112;010\n", encoding="utf-8")

        ProcessamentoService(notificar=_Notificador()).executar([_pacote(caminho)])

        recusa = quarentena / "202507" / "ENTRY-1" / "quebrado_RECUSADO.md"
        assert "15 colunas" in recusa.read_text(encoding="utf-8")

    def test_dois_arquivos_de_mesmo_nome_nao_se_sobrescrevem(self, ambiente):
        """
        Duas operadoras mandando `DETRAF.csv` no mesmo mês é o caso normal, não a
        exceção. Sem a subpasta por e-mail, a evidência de uma delas sumiria.
        """
        entrada, _, _, quarentena = ambiente
        primeiro = entrada / "a" / "DETRAF.csv"
        segundo = entrada / "b" / "DETRAF.csv"
        for caminho in (primeiro, segundo):
            caminho.parent.mkdir(parents=True)
            _escrever_detraf(caminho, gh="X")

        ProcessamentoService(notificar=_Notificador()).executar([
            _pacote(primeiro, entry_id="ENTRY-A"),
            _pacote(segundo, entry_id="ENTRY-B"),
        ])

        mes = quarentena / "202507"
        assert (mes / "ENTRY-A" / "DETRAF.csv").is_file()
        assert (mes / "ENTRY-B" / "DETRAF.csv").is_file()

    def test_o_reprovado_entra_no_log_de_despesa(self, ambiente):
        """
        O registro que o RPA 2 deixou de fazer. Sem ele, o lote DETRAF_ERRO do
        WebFat iria a zero e quem lê o relatório leria como "melhorou".
        """
        entrada, _, _, _ = ambiente
        caminho = entrada / "reprovado_log.csv"
        _escrever_detraf(caminho, gh="X")

        ProcessamentoService(notificar=_Notificador()).executar([_pacote(caminho)])

        log = _ler_log("reprovado_log.csv")
        assert len(log) == 1
        assert log.iloc[0]["status"] == "Não validado"


class TestAOrdemValidarAntesDeIdentificar:
    def test_invalido_e_nao_identificavel_ainda_gera_resposta(self, ambiente):
        """
        🔴 A regressão que a ordem existe para evitar.

        EOT credora fora do Anexo 5 **e** domínio de remetente desconhecido: se a
        identificação viesse primeiro, este arquivo cairia em
        `_NAO_IDENTIFICADOS` e a operadora nunca saberia de nada.
        """
        entrada, operadoras, nao_identificados, quarentena = ambiente
        caminho = entrada / "orfao.csv"
        _escrever_detraf(caminho, credora="999", gh="X")

        notificador = _Notificador()
        ProcessamentoService(notificar=notificador).executar(
            [_pacote(caminho, sender_email="x@dominio-desconhecido-999.com")]
        )

        assert notificador.nomes_recusados() == ["orfao.csv"]
        assert (quarentena / "202507" / "ENTRY-1" / "orfao.csv").is_file()
        assert not (nao_identificados / "202507" / "orfao.csv").exists()
        assert list(operadoras.iterdir()) == []

    def test_valido_e_nao_identificado_NAO_gera_resposta(self, ambiente, monkeypatch):
        """
        Dizer "seu arquivo está inválido" a quem mandou um arquivo correto ensina
        a operadora a ignorar o robô. `_NAO_IDENTIFICADOS` significa uma coisa
        só: arquivo íntegro, cadastro NOSSO faltando.
        """
        from src.models.dto.operadora_resultado import OperadoraResultado
        from src.services import processamento_service as ps

        entrada, _, nao_identificados, _ = ambiente
        caminho = entrada / "sem_cadastro.csv"
        _escrever_detraf(caminho)
        monkeypatch.setattr(
            ps.OperadoraService,
            "obter_operadora",
            staticmethod(
                lambda *a, **k: OperadoraResultado(
                    identificada=False, dominio="", nome=""
                )
            ),
        )

        notificador = _Notificador()
        ProcessamentoService(notificar=notificador).executar([_pacote(caminho)])

        assert notificador.chamadas == []
        assert (nao_identificados / "202507" / "sem_cadastro.csv").is_file()


class TestAResposta:
    def test_os_motivos_chegam_a_notificacao(self, ambiente):
        entrada, _, _, _ = ambiente
        caminho = entrada / "tarifa_zero.csv"
        _escrever_detraf(caminho, tarifa="0")

        notificador = _Notificador()
        ProcessamentoService(notificar=notificador).executar([_pacote(caminho)])

        motivos = notificador.motivos_do_primeiro
        assert any("Coluna 11" in motivo for motivo in motivos)
        assert any("zero" in motivo for motivo in motivos), (
            "o motivo precisa dizer o que corrigir, e não só qual coluna"
        )

    def test_falha_ao_notificar_nao_impede_o_proximo_email(self, ambiente):
        """Uma exceção do Outlook num e-mail não pode calar o robô nos outros."""
        entrada, _, _, quarentena = ambiente
        for nome in ("um.csv", "dois.csv"):
            _escrever_detraf(entrada / nome, gh="X")

        servico = ProcessamentoService(
            notificar=_Notificador(erro=RuntimeError("COM caiu"))
        )
        servico.executar([
            _pacote(entrada / "um.csv", entry_id="E1"),
            _pacote(entrada / "dois.csv", entry_id="E2"),
        ])

        assert len(servico._reprovados) == 2
        assert (quarentena / "202507" / "E2" / "dois.csv").is_file()

    def test_sem_notificador_o_arquivo_ainda_vai_para_a_quarentena(self, ambiente):
        """Modo standalone (`--pasta-entrada`), sem Outlook: recusa continua valendo."""
        entrada, operadoras, _, quarentena = ambiente
        caminho = entrada / "gh_invalido.csv"
        _escrever_detraf(caminho, gh="X")

        servico = ProcessamentoService(notificar=None)
        servico.executar([_pacote(caminho)])

        assert (quarentena / "202507" / "ENTRY-1" / "gh_invalido.csv").is_file()
        assert list(operadoras.iterdir()) == []
        assert servico._reprovados[0]["notificada"] == "NÃO"


class TestVariosAnexosNoMesmoEmail:
    """
    Um e-mail pode trazer vários anexos, e vários deles podem ser reprovados.

    Antes de 2026-08-06 saía **uma mensagem por arquivo**: três avisos sobre o
    mesmo envio, e a operadora agiria só no primeiro. Com
    `NOTIFICAR_OPERADORA_ENVIAR` ligado, um e-mail com dez anexos viraria dez
    e-mails enviados.

    O agrupamento é pelo `entry_id`, que é o mesmo para todos os anexos de um
    e-mail. Ele só pode acontecer **depois** do laço de processamento — antes do
    fim, não se sabe quantos anexos daquele envio vão cair.
    """

    def _tres_anexos(self, entrada, **desvios):
        caminhos = []
        for nome in ("A.csv", "B.csv", "C.csv"):
            caminho = entrada / nome
            _escrever_detraf(caminho, **desvios)
            caminhos.append(caminho)
        return caminhos

    def test_tres_reprovados_geram_UMA_resposta(self, ambiente):
        entrada, _, _, _ = ambiente
        caminhos = self._tres_anexos(entrada, tarifa="0")

        notificador = _Notificador()
        ProcessamentoService(notificar=notificador).executar(
            [_pacote(c, entry_id="MESMO-EMAIL") for c in caminhos]
        )

        assert len(notificador.chamadas) == 1
        assert notificador.nomes_recusados() == ["A.csv", "B.csv", "C.csv"]

    def test_a_resposta_traz_os_motivos_de_cada_arquivo(self, ambiente):
        """
        Um motivo solto não diz a qual arquivo pertence — a operadora corrigiria
        o errado. Cada recusa carrega o nome junto dos seus motivos.
        """
        entrada, _, _, _ = ambiente
        bom_e_ruins = []
        for nome, desvio in (("A.csv", {"tarifa": "0"}), ("B.csv", {"gh": "X"})):
            caminho = entrada / nome
            _escrever_detraf(caminho, **desvio)
            bom_e_ruins.append(caminho)

        notificador = _Notificador()
        ProcessamentoService(notificar=notificador).executar(
            [_pacote(c, entry_id="MESMO-EMAIL") for c in bom_e_ruins]
        )

        _, recusas = notificador.chamadas[0]
        por_nome = {recusa.nome: recusa.motivos for recusa in recusas}

        assert any("Coluna 11" in m for m in por_nome["A.csv"])
        assert any("GH" in m for m in por_nome["B.csv"])

    def test_emails_diferentes_geram_respostas_diferentes(self, ambiente):
        """O agrupamento é por envio — não pode juntar operadoras distintas."""
        entrada, _, _, _ = ambiente
        caminhos = self._tres_anexos(entrada, tarifa="0")

        notificador = _Notificador()
        ProcessamentoService(notificar=notificador).executar([
            _pacote(caminhos[0], entry_id="EMAIL-1"),
            _pacote(caminhos[1], entry_id="EMAIL-1"),
            _pacote(caminhos[2], entry_id="EMAIL-2"),
        ])

        assert len(notificador.chamadas) == 2
        por_chamada = sorted(len(recusas) for _, recusas in notificador.chamadas)
        assert por_chamada == [1, 2]

    def test_o_anexo_valido_do_mesmo_email_nao_entra_na_resposta(self, ambiente):
        """
        Um envio misto — parte aceita, parte recusada — é caso normal. A resposta
        fala só dos recusados; o aceito seguiu para a pasta da operadora.
        """
        entrada, operadoras, _, _ = ambiente
        bom = entrada / "bom.csv"
        ruim = entrada / "ruim.csv"
        _escrever_detraf(bom)
        _escrever_detraf(ruim, tarifa="0")

        notificador = _Notificador()
        ProcessamentoService(notificar=notificador).executar([
            _pacote(bom, entry_id="MESMO-EMAIL"),
            _pacote(ruim, entry_id="MESMO-EMAIL"),
        ])

        assert notificador.nomes_recusados() == ["ruim.csv"]
        assert _arquivos_em(operadoras) == ["bom.csv"]

    def test_todos_do_grupo_ficam_marcados_no_resumo(self, ambiente):
        """
        A notificação é uma só, mas o resumo tem uma linha por arquivo. Se a
        marcação não se propagasse, dois dos três apareceriam como não avisados.
        """
        entrada, _, _, _ = ambiente
        caminhos = self._tres_anexos(entrada, tarifa="0")

        servico = ProcessamentoService(notificar=_Notificador())
        servico.executar([_pacote(c, entry_id="MESMO-EMAIL") for c in caminhos])

        assert [r["notificada"] for r in servico._reprovados] == ["sim"] * 3

    def test_falha_no_envio_marca_os_tres_como_nao_avisados(self, ambiente):
        entrada, _, _, _ = ambiente
        caminhos = self._tres_anexos(entrada, tarifa="0")

        servico = ProcessamentoService(
            notificar=_Notificador(erro=RuntimeError("COM caiu"))
        )
        servico.executar([_pacote(c, entry_id="MESMO-EMAIL") for c in caminhos])

        assert [r["notificada"] for r in servico._reprovados] == ["NÃO"] * 3

    def test_sem_entry_id_cada_arquivo_e_o_seu_proprio_grupo(self, ambiente):
        """
        Pasta preparada à mão (`--pasta-entrada`): não há e-mail de origem, e o
        `entry_id` vem vazio. Agrupar tudo num só grupo juntaria arquivos de
        operadoras diferentes — o caminho do arquivo vira a chave.
        """
        entrada, _, _, _ = ambiente
        caminhos = self._tres_anexos(entrada, tarifa="0")

        servico = ProcessamentoService(notificar=_Notificador())
        servico.executar([_pacote(c, entry_id="") for c in caminhos])

        assert len(servico._recusas_por_email) == 3


class TestValidacaoIndisponivelNaCaptura:
    """
    🔴 O risco mais grave da mudança. Se uma queda do WebFat virasse reprovação,
    o RPA 1 poria o lote inteiro em quarentena e responderia a **todas** as
    operadoras dizendo que os arquivos delas estão errados — com
    NOTIFICAR_OPERADORA_ENVIAR ligado, irreversível.
    """

    @pytest.fixture()
    def banco_fora(self, monkeypatch):
        from comum.dominio import validacao_colunas as vc

        def _estourar(*args, **kwargs):
            raise RuntimeError("Can't connect to MySQL server")

        monkeypatch.setattr(vc.bd_tabelas, "validar_coluna_eot_df", _estourar)

    def test_nao_notifica_ninguem(self, ambiente, banco_fora):
        entrada, _, _, _ = ambiente
        caminho = entrada / "bom.csv"
        _escrever_detraf(caminho)

        notificador = _Notificador()
        ProcessamentoService(notificar=notificador).executar([_pacote(caminho)])

        assert notificador.chamadas == []

    def test_nao_poe_em_quarentena_e_conta_como_erro(self, ambiente, banco_fora):
        entrada, operadoras, _, quarentena = ambiente
        caminho = entrada / "bom.csv"
        _escrever_detraf(caminho)

        servico = ProcessamentoService(notificar=_Notificador())
        servico.executar([_pacote(caminho)])

        assert not quarentena.exists()
        assert list(operadoras.iterdir()) == []
        assert servico._reprovados == []
        assert len(servico._erros) == 1
        assert "indisponível" in servico._erros[0]["erro"]

    def test_o_arquivo_continua_na_entrada_para_a_proxima_execucao(
        self, ambiente, banco_fora
    ):
        entrada, _, _, _ = ambiente
        caminho = entrada / "bom.csv"
        _escrever_detraf(caminho)

        ProcessamentoService(notificar=_Notificador()).executar([_pacote(caminho)])

        assert caminho.is_file()


class TestArquivoIlegivel:
    def test_vira_recusa_com_motivo_e_nao_erro(self, ambiente):
        """
        Se virasse erro, ficaria preso na entrada e seria retentado a cada
        execução, para sempre, sem ninguém ser avisado. Um arquivo que não abre
        não vai abrir na próxima vez.
        """
        entrada, _, _, quarentena = ambiente
        caminho = entrada / "corrompido.csv"
        caminho.write_bytes(b"\x00\x01\x02 isto nao e um csv \xff\xfe")

        servico = ProcessamentoService(notificar=_Notificador())
        servico.executar([_pacote(caminho)])

        assert len(servico._erros) == 0
        assert len(servico._reprovados) == 1
        assert (quarentena / "202507" / "ENTRY-1" / "corrompido.csv").is_file()


class TestOResumo:
    def test_conta_os_reprovados_separadamente(self, ambiente):
        """
        Reprovado não é erro nem não identificado: são três desfechos com causas
        e ações diferentes, e somá-los esconderia justamente o que mudou.
        """
        entrada, _, _, _ = ambiente
        _escrever_detraf(entrada / "bom.csv")
        _escrever_detraf(entrada / "ruim.csv", gh="X")

        servico = ProcessamentoService(notificar=_Notificador())
        servico.executar([
            _pacote(entrada / "bom.csv", entry_id="E1"),
            _pacote(entrada / "ruim.csv", entry_id="E2"),
        ])

        texto = "\n".join(servico.resumo)
        assert "Reprovados na validação:  1" in texto
        assert "Arquivos salvos:          1" in texto
        assert "ruim.csv" in texto
