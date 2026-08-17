"""O `--rpa` do verificar_ambiente.py só cobra o que aquele robô usa (2026-08-06).

Sem o recorte, quem homologa o RPA 1 recebe uma falha de `DIRETORIO_AGI` — e
código de saída não-zero — por causa de um sistema que aquele robô nunca abre.
Uma lista de falhas com item irrelevante dentro é uma lista que se aprende a
ignorar, e é assim que uma falha real passa despercebida.

O que se protege aqui é a correspondência entre o recorte declarado e o que o
código dos robôs de fato importa. Ela se desfaz em silêncio: basta alguém
acrescentar um envio de e-mail ao RPA 3 e o pre-flight deixa de conferir o
Outlook para ele, sem nada quebrar.
"""

import verificar_ambiente as va


class TestRecorteDeclarado:
    def test_todo_robo_tem_escopo(self):
        assert set(va.GRUPOS_POR_ROBO) == set(va.ROBOS)

    def test_o_que_ninguem_dispensa(self):
        """
        Configuração, pastas e banco valem para todos.

        "Validação" saiu desta lista com o RPA 4 (2026-08-10): ele lê a
        contestação já apurada no banco e não abre arquivo de Detraf nenhum, então
        `NOME_FANTASIA_VIVO` — a única variável do grupo — não diz respeito a ele.
        Cobrá-la seria a falha irrelevante que este recorte existe para tirar.
        """
        for grupos in va.GRUPOS_POR_ROBO.values():
            assert {"Configuração", "Pastas", "Banco"} <= grupos

    def test_quem_processa_arquivo_confere_a_validacao(self):
        """O grupo continua obrigatório para os três que leem Detraf."""
        for robo in ("rpa1", "rpa2", "rpa3"):
            assert "Validação" in va.GRUPOS_POR_ROBO[robo]

    def test_validacao_e_filtros_sao_grupos_distintos(self):
        """
        Os dois já foram um só. Quando o RPA 1 passou a validar (2026-08-06), ele
        passou a precisar de UMA das quatro variáveis de "Filtros" — as outras
        três filtram arquivos que ele nunca lê. Dar o grupo inteiro devolveria o
        ruído que este recorte existe para tirar.
        """
        assert "Validação" in va.GRUPOS_POR_ROBO["rpa1"]
        assert "Filtros" not in va.GRUPOS_POR_ROBO["rpa1"]

    def test_so_o_rpa3_confere_o_agi(self):
        """
        É o que destrava o provisionamento em ordem: banco e pastas bastam para
        o RPA 1 e o RPA 2 inteiros, sem depender da rotação do R20.
        """
        assert "AGI" in va.GRUPOS_POR_ROBO["rpa3"]
        assert "AGI" not in va.GRUPOS_POR_ROBO["rpa1"]
        assert "AGI" not in va.GRUPOS_POR_ROBO["rpa2"]

    def test_o_rpa3_confere_outlook(self):
        """
        Ele manda o e-mail de contestação (`envio_email_contestacao.py`). O
        recorte nasceu errado aqui, tratando o Outlook como coisa só do RPA 1 e
        do RPA 2 — foi `TestOEscopoBateComOCodigo` que acusou.
        """
        assert "Outlook" in va.GRUPOS_POR_ROBO["rpa3"]

    def test_o_rpa2_nao_confere_mais_outlook(self):
        """
        Ele deixou de responder à operadora em 2026-08-06 — quem responde é o
        RPA 1, na captura —, e com isso não sobrou nenhuma linha de código do
        RPA 2 que fale com o Outlook. Foi `TestOEscopoBateComOCodigo` que acusou
        a inconsistência assim que a remoção foi feita.
        """
        assert "Outlook" not in va.GRUPOS_POR_ROBO["rpa2"]

    def test_todo_grupo_dispensado_tem_motivo_escrito(self):
        """
        Omissão sem explicação na tela se lê como esquecimento de quem escreveu
        o verificador — e alguém vai reintroduzir a verificação achando que
        faltou.
        """
        todos = set().union(*va.GRUPOS_POR_ROBO.values())
        for robo, grupos in va.GRUPOS_POR_ROBO.items():
            for dispensado in todos - grupos:
                assert dispensado in va.MOTIVO_FORA_DE_ESCOPO, (
                    f"{robo} dispensa {dispensado} sem motivo em MOTIVO_FORA_DE_ESCOPO"
                )


class TestOEscopoBateComOCodigo:
    """
    Confere o recorte contra os robôs, e não contra si mesmo — um teste que só
    lê `GRUPOS_POR_ROBO` continuaria verde depois de o RPA 3 passar a mandar
    e-mail.
    """

    def _usa_outlook(self, robo: str) -> bool:
        pasta = va.RAIZ / va.ROBOS[robo]
        for arquivo in pasta.rglob("*.py"):
            if "test" in arquivo.parts[-1] or "tests" in arquivo.parts:
                continue
            texto = arquivo.read_text(encoding="utf-8", errors="ignore").lower()
            if "outlook" in texto or "win32com" in texto:
                return True
        return False

    def test_quem_dispensa_outlook_realmente_nao_o_usa(self):
        for robo, grupos in va.GRUPOS_POR_ROBO.items():
            if "Outlook" not in grupos:
                assert not self._usa_outlook(robo), (
                    f"{robo} usa Outlook mas o pre-flight não o confere"
                )

    def test_quem_confere_outlook_realmente_o_usa(self):
        """O recorte errado para o outro lado devolve o ruído que ele veio tirar."""
        for robo, grupos in va.GRUPOS_POR_ROBO.items():
            if "Outlook" in grupos:
                assert self._usa_outlook(robo), (
                    f"{robo} não usa Outlook — conferi-lo só produz falha irrelevante"
                )
