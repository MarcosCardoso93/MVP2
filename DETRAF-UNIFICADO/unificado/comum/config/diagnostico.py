"""Verificações de ambiente — as que o robô faria tarde, feitas cedo.

Escrito em 2026-08-06, para a homologação manual.

## O problema

Quase toda falha de infraestrutura deste repositório aparecia **no meio da
execução**, e com pouca informação:

- a conexão com o MySQL só é aberta na primeira leitura de tabela, e credencial
  errada, host inacessível e tabela inexistente chegavam com a mesma cara —
  a mensagem crua do SQLAlchemy dentro de um `RuntimeError`;
- pasta de rede sem permissão de escrita só se descobre na hora de gravar, que é
  depois de o robô já ter aberto o AGI, logado e baixado;
- variável ausente e variável apontando para lugar inexistente se confundem.

Numa homologação manual, sem ninguém a quem perguntar, isso custa a tarde.

## A regra das mensagens

Toda verificação diz **o quê**, **onde**, **o que se encontrou** e **o que
fazer**. "Falha ao conectar" não é mensagem; "usuário recusado pelo MySQL —
confira `USUARIO_BD`/`SENHA_BD` no `.env`" é.

## O que nunca sai daqui

Valor de credencial. As verificações dizem se a senha **existe** e quantos
caracteres tem — nunca o conteúdo. O `LOG_DIAGNOSE` já grava variáveis locais em
traceback fora de produção; não faz sentido acrescentar mais um caminho de
vazamento.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Situacao = Literal["ok", "aviso", "falha"]


@dataclass
class Resultado:
    """Uma verificação e o que ela achou."""

    grupo: str
    item: str
    situacao: Situacao
    detalhe: str
    #: O que fazer. Vazio quando está tudo certo.
    correcao: str = ""

    @property
    def simbolo(self) -> str:
        return {"ok": "OK   ", "aviso": "AVISO", "falha": "FALHA"}[self.situacao]


def _ok(grupo: str, item: str, detalhe: str) -> Resultado:
    return Resultado(grupo, item, "ok", detalhe)


def _aviso(grupo: str, item: str, detalhe: str, correcao: str) -> Resultado:
    return Resultado(grupo, item, "aviso", detalhe, correcao)


def _falha(grupo: str, item: str, detalhe: str, correcao: str) -> Resultado:
    return Resultado(grupo, item, "falha", detalhe, correcao)


# ---------------------------------------------------------------------------
# Pastas
# ---------------------------------------------------------------------------


def verificar_pasta(
    grupo: str,
    variavel: str,
    caminho: Path | None,
    obrigatoria: bool = True,
    precisa_escrever: bool = False,
) -> Resultado:
    """
    Confere uma pasta configurada, distinguindo as três causas que se confundem.

    "Não configurada", "não existe" e "sem permissão" produzem o mesmo sintoma no
    robô — *nenhum arquivo encontrado* — e exigem correções completamente
    diferentes. Separá-las é o ganho principal desta função.

    Args:
        grupo: Rótulo da seção no relatório.
        variavel: Nome da variável de ambiente, para citar na correção.
        caminho: O valor lido da configuração.
        obrigatoria: Se ausente é falha (`True`) ou apenas aviso.
        precisa_escrever: Se o robô grava aqui. Quando `True`, a permissão de
            escrita é testada **de verdade**, criando e apagando um arquivo — é
            a única forma de saber antes da hora.
    """

    # `Path("")` vira `Path(".")` — o diretório atual, que existe e é
    # diretório, então toda guarda passa e o robô varre o lugar errado em
    # silêncio. A configuração já usa `_caminho_opcional` para evitar isso, mas
    # `_primeiro_caminho` tem `padrao=""`, e é assim que o `.` reaparece.
    if caminho is not None and str(caminho).strip() in {".", "./", ".\\"}:
        return _falha(
            grupo, variavel, "resolve para o diretório atual (Path(\"\") -> Path(\".\"))",
            f"{variavel} não está configurada. O diretório atual EXISTE, então "
            f"o robô não acusa erro — ele varre o lugar errado e conclui "
            f"'nenhum arquivo encontrado'.",
        )

    if caminho is None or not str(caminho).strip():
        if obrigatoria:
            return _falha(
                grupo, variavel, "não configurada",
                f"Defina {variavel} no .env.",
            )
        return _aviso(
            grupo, variavel, "não configurada",
            f"Opcional. Sem ela, a etapa que a usa é pulada com aviso no log.",
        )

    pasta = Path(caminho)

    if not pasta.exists():
        return _falha(
            grupo, variavel, f"não existe: [{pasta}]",
            "Crie a pasta, ou corrija o caminho no .env. Se for pasta de rede, "
            "confira se o compartilhamento está montado.",
        )

    if not pasta.is_dir():
        return _falha(
            grupo, variavel, f"existe, mas é arquivo, não pasta: [{pasta}]",
            f"Aponte {variavel} para um diretório.",
        )

    try:
        list(pasta.iterdir())
    except PermissionError:
        return _falha(
            grupo, variavel, f"sem permissão de leitura: [{pasta}]",
            "Peça acesso de leitura ao responsável pelo compartilhamento.",
        )
    except OSError as erro:
        return _falha(
            grupo, variavel, f"não pôde ser lida: [{pasta}] — {erro}",
            "Confira se o compartilhamento de rede está acessível.",
        )

    if not precisa_escrever:
        return _ok(grupo, variavel, f"[{pasta}]")

    # Escrever de fato: `os.access(W_OK)` mente em compartilhamento de rede
    # Windows, que é justamente onde este repositório grava.
    teste = pasta / ".rpa-detraf-teste-de-escrita.tmp"
    try:
        teste.write_text("teste", encoding="utf-8")
        teste.unlink()
    except PermissionError:
        return _falha(
            grupo, variavel, f"SEM PERMISSÃO DE ESCRITA: [{pasta}]",
            "O robô grava aqui. Peça acesso de escrita — senão a falha só "
            "aparece no meio da execução, depois do trabalho já feito.",
        )
    except OSError as erro:
        return _falha(
            grupo, variavel, f"escrita falhou em [{pasta}]: {erro}",
            "Confira espaço em disco e o estado do compartilhamento.",
        )

    return _ok(grupo, variavel, f"[{pasta}] — leitura e escrita")


# ---------------------------------------------------------------------------
# Credenciais
# ---------------------------------------------------------------------------


def verificar_lista_de_filtro(
    grupo: str, variavel: str, valor, o_que_filtra: str
) -> Resultado:
    """
    Confere uma lista usada como **filtro de arquivo**. Vazia é falha.

    ## Por que isto merece uma verificação própria

    Três variáveis do repositório são lidas assim::

        any(sub in nome_arquivo for sub in LISTA)

    Com a lista **vazia**, `any(...)` é `False` e o filtro **rejeita tudo**. E o
    modo de falha é o pior possível: nenhum erro, nenhum aviso, a execução
    termina com **sucesso** tendo processado zero arquivos. Quem vê o log
    conclui que não havia nada a fazer.

    Foi achado em 2026-08-06, comparando o `.env.example` com os `.env` dos
    projetos de origem: o `ARQUIVOS_VALIDADOS` estava em branco aqui e valia
    ``_ENV`` lá — e sem ele o batimento do RPA 2 não processa arquivo nenhum.

    Args:
        grupo: Rótulo da seção no relatório.
        variavel: Nome da variável, para citar na correção.
        valor: A lista lida da configuração.
        o_que_filtra: O que ela decide, em uma frase — é o que transforma
            "lista vazia" em "o batimento não vai ler nada".
    """

    itens = [str(item).strip() for item in (valor or []) if str(item).strip()]

    if not itens:
        return _falha(
            grupo,
            variavel,
            "VAZIA — e ela é usada como filtro",
            f"{o_que_filtra} Com a lista vazia nada passa no filtro, e a "
            f"execução termina COM SUCESSO tendo processado zero arquivos. "
            f"Preencha {variavel} no .env.",
        )

    return _ok(grupo, variavel, ", ".join(itens))


def verificar_credencial(
    grupo: str, variavel: str, valor: str, obrigatoria: bool = True
) -> Resultado:
    """
    Confere que uma credencial existe, **sem revelar o valor**.

    O comprimento entra no detalhe de propósito: é o que permite dizer "a senha
    tem 28 caracteres, é a mesma que estava no `.env` do Projeto 7" sem imprimir
    nada — e foi assim que a duplicação de credencial entre P6 e P7 foi
    identificada.
    """

    if not valor:
        situacao = _falha if obrigatoria else _aviso
        return situacao(
            grupo, variavel, "AUSENTE",
            f"Defina {variavel} no ambiente da máquina (não no .env versionado).",
        )

    if valor.strip() != valor:
        return _aviso(
            grupo, variavel, f"definida ({len(valor)} caracteres) — com espaço nas pontas",
            "Espaço no começo ou no fim quase sempre é erro de cópia, e o "
            "servidor vai recusar sem dizer por quê.",
        )

    return _ok(grupo, variavel, f"definida ({len(valor)} caracteres)")


# ---------------------------------------------------------------------------
# Banco
# ---------------------------------------------------------------------------

#: Trechos que o driver devolve, e o que cada um significa em português. O
#: `pymysql` já diz a causa, mas embrulhada em ruído — e a mesma exceção pode
#: vir de quatro problemas com correções diferentes.
_CAUSAS_DE_BANCO = (
    (
        ("access denied",),
        "usuário ou senha recusados pelo servidor",
        "Confira USUARIO_BD e SENHA_BD. Se a senha tem caracteres especiais, "
        "confira também se o .env não a cortou.",
    ),
    (
        ("unknown database",),
        "o servidor respondeu, mas a base não existe",
        "Confira DATABASE_RPA — o nome da base, não o do servidor.",
    ),
    (
        ("can't connect", "timed out", "timeout", "getaddrinfo"),
        "não foi possível alcançar o servidor",
        "Confira HOST_BD_RPA e PORT_BD_RPA, e se a máquina tem rota até o "
        "servidor (VPN, firewall).",
    ),
    (
        ("doesn't exist", "no such table"),
        "conectou, mas a tabela não existe",
        "Confira o nome com o DBA — é a pendência N1 (o log de arquivos mudou "
        "de nome entre o código legado e a V2).",
    ),
    (
        ("unknown column", "no such column"),
        "conectou, mas falta uma coluna",
        "Rode `python espelhar_banco.py --somente-schema` para ver o schema "
        "real e comparar. É a pendência Q22.",
    ),
)


def explicar_erro_de_banco(erro: BaseException) -> tuple[str, str]:
    """
    Traduz a exceção do driver em causa e correção.

    Returns:
        ``(causa, correção)``. Quando não reconhece, devolve a mensagem original
        — melhor um texto cru do que uma explicação inventada.
    """

    texto = str(erro).lower()

    for marcadores, causa, correcao in _CAUSAS_DE_BANCO:
        if any(marcador in texto for marcador in marcadores):
            return causa, correcao

    return (
        f"falha não reconhecida: {erro}",
        "Rode com --log-nivel DEBUG e guarde o traceback completo.",
    )


def verificar_banco(grupo: str = "Banco") -> list[Resultado]:
    """
    Conecta, lista as tabelas e confere as colunas que o código usa.

    É a verificação mais valiosa do conjunto: ela responde, em segundos, a
    pergunta que hoje só se responde falhando — *o banco tem o que o robô
    precisa?*
    """

    from comum.config import configuration as cfg
    from comum.dados import tabelas as tbl

    resultados: list[Resultado] = []

    if cfg.ENV == "dev":
        caminho = Path(cfg.CAMINHO_SQLITE) if cfg.CAMINHO_SQLITE else None
        if caminho is None:
            resultados.append(
                _aviso(
                    grupo, "modo", "dev, com CAMINHO_SQLITE vazio",
                    "O repositório de cache vai cair no SQLite padrão do "
                    "projeto. Para homologar contra dados reais, gere um "
                    "espelho: python espelhar_banco.py",
                )
            )
        elif not caminho.is_file():
            resultados.append(
                _falha(
                    grupo, "CAMINHO_SQLITE", f"arquivo não existe: [{caminho}]",
                    "Gere o banco com `python preparar_banco_dev.py` ou "
                    "`python espelhar_banco.py`.",
                )
            )
            return resultados
        else:
            resultados.append(_ok(grupo, "modo", f"dev — SQLite [{caminho}]"))
    else:
        resultados.append(
            _ok(
                grupo,
                "modo",
                f"{cfg.ENV} — MySQL [{cfg.HOST_BD_RPA}:{cfg.PORT_BD_RPA}/"
                f"{cfg.DATABASE_RPA}]",
            )
        )
        for variavel, valor in (
            ("HOST_BD_RPA", cfg.HOST_BD_RPA),
            ("DATABASE_RPA", cfg.DATABASE_RPA),
            ("USUARIO_BD", cfg.USUARIO_BD),
        ):
            if not valor:
                resultados.append(
                    _falha(grupo, variavel, "AUSENTE", f"Defina {variavel} no .env.")
                )
        resultados.append(
            verificar_credencial(grupo, "SENHA_BD", cfg.SENHA_BD)
        )

    # --- conexão de verdade ---------------------------------------------
    from comum.dados.repositorio_cache import RepositorioCache

    try:
        engine = RepositorioCache._obter_engine()
        with engine.connect():
            pass
        resultados.append(_ok(grupo, "conexão", "estabelecida"))
    except Exception as erro:
        causa, correcao = explicar_erro_de_banco(erro)
        resultados.append(_falha(grupo, "conexão", causa, correcao))
        return resultados

    # --- tabelas e colunas ----------------------------------------------
    from sqlalchemy import inspect

    try:
        inspetor = inspect(engine)
        existentes = set(inspetor.get_table_names())
    except Exception as erro:
        resultados.append(
            _falha(grupo, "tabelas", f"não foi possível listar: {erro}",
                   "Confira as permissões do usuário do banco.")
        )
        return resultados

    for tabela in sorted(tbl.TODAS):
        if tabela not in existentes:
            resultados.append(
                _falha(
                    grupo, tabela, "TABELA NÃO EXISTE",
                    "O código a usa. Confirme o nome com o DBA (Q22/N1).",
                )
            )
            continue

        colunas = [coluna["name"] for coluna in inspetor.get_columns(tabela)]
        faltando = tbl.conferir_colunas(tabela, colunas)

        if not faltando:
            resultados.append(_ok(grupo, tabela, f"{len(colunas)} coluna(s)"))
            continue

        # Ausência CONHECIDA e tratada (`vb_contestacao`) é diferente de ausência
        # nova. A primeira já tem pedido de `ALTER TABLE` no DBA e o código
        # degrada em volta dela — grava as demais colunas e avisa. Tratar as duas
        # como falha deixaria o `verificar_ambiente.py` permanentemente vermelho
        # num gap já resolvido, e vermelho constante ninguém lê.
        pendentes = set(tbl.COLUNAS_PENDENTES_NO_BANCO.get(tabela, ()))
        inesperadas = [coluna for coluna in faltando if coluna not in pendentes]

        if not inesperadas:
            resultados.append(
                _aviso(
                    grupo,
                    tabela,
                    f"faltam as colunas: {', '.join(faltando)} (pendente no DBA)",
                    "Ausência conhecida e tratada: a escrita segue sem estas "
                    "colunas, com aviso no log. Um único ALTER TABLE resolve — "
                    "ver pendencias-para-o-cliente.md (Q24).",
                )
            )
            continue

        resultados.append(
            _falha(
                grupo,
                tabela,
                f"faltam as colunas: {', '.join(inesperadas)}",
                "Divergência NÃO prevista entre o código e o banco. Rode "
                "`python espelhar_banco.py --somente-schema` e compare com "
                "`tabelas.DDL_CONFIRMADO`.",
            )
        )

    return resultados


# ---------------------------------------------------------------------------
# Variáveis de ambiente
# ---------------------------------------------------------------------------


#: Nomes que o código conhece e que **não devem** estar no `.env.example`.
#: Sinalizá-los seria ruído que ensina a ignorar o relatório.
_SEM_DOCUMENTACAO = {
    # Definido pelo `main.py` de cada robô, não por quem configura a máquina.
    "NOME_RPA",
    # Aliases de `CAMINHO_OPERADORAS`, mantidos para os `.env` dos projetos de
    # origem continuarem valendo. O `.env.example` documenta só o nome canônico.
    "CAMINHO_DETRAF_RECEBIDO",
    "DIRETORIO_SAIDA",
}


def verificar_variaveis(caminho_env_example: Path, grupo: str = "Configuração") -> list[Resultado]:
    """
    Cruza o `.env` da máquina com o `.env.example` e com o que o código lê.

    Pega a classe de erro mais chata de diagnosticar: **o nome digitado errado**.
    Uma variável escrita `PERMITIR_UPLOAD_AGY` não causa erro nenhum — ela
    simplesmente não existe, o default vale, e o robô se comporta como se a linha
    nunca tivesse sido escrita.
    """

    from comum.config import configuration as cfg

    resultados: list[Resultado] = []

    if not caminho_env_example.is_file():
        return [
            _aviso(
                grupo, ".env.example", "não encontrado",
                "Sem ele não dá para conferir nomes de variável.",
            )
        ]

    documentadas = {
        linha.split("=", 1)[0].strip()
        for linha in caminho_env_example.read_text(encoding="utf-8").splitlines()
        if "=" in linha and not linha.lstrip().startswith("#")
    }

    lidas = set(cfg.ORIGEM_DAS_VARIAVEIS) | _SEM_DOCUMENTACAO

    # Nomes que o ambiente tem, parecem do projeto, e ninguém lê. O prefixo
    # restringe a busca ao que é nosso — a máquina tem centenas de variáveis.
    prefixos = ("CAMINHO_", "DIRETORIO_", "PERMITIR_", "OUTLOOK_", "SUBPASTA_",
                "EXTENSOES_", "LOG_", "DETRAF_", "PASTAS_", "NOTIFICAR_",
                "EXPECTATIVA_", "IGNORAR_", "ARQUIVOS_", "TOLERANCIA_", "CT_",
                "NOME_", "RAIZ_", "AGI_", "ENV", "HOST_BD", "PORT_BD",
                "DATABASE_", "USUARIO_", "SENHA_", "RASTREAMENTO_",
                "DEBUG_", "COMPETENCIA")

    def _do_projeto(nome: str) -> bool:
        return nome.startswith(prefixos)

    #: Sufixos por robô (`ENV_RPA3`) são legítimos e não estão no `.env.example`.
    def _sem_sufixo(nome: str) -> str:
        for sufixo in ("_RPA1", "_RPA2", "_RPA3", "_RPA4"):
            if nome.endswith(sufixo):
                return nome[: -len(sufixo)]
        return nome

    desconhecidas = sorted(
        nome
        for nome in os.environ
        if _do_projeto(nome)
        and _sem_sufixo(nome) not in documentadas
        and _sem_sufixo(nome) not in lidas
    )

    for nome in desconhecidas:
        resultados.append(
            _aviso(
                grupo, nome, "definida no ambiente e não lida por nada",
                "Provavelmente erro de digitação. Uma variável com nome errado "
                "não dá erro: o default vale e o robô ignora a linha.",
            )
        )

    # `_SEM_DOCUMENTACAO` entra em `lidas` para não virar "desconhecida" acima,
    # mas sai daqui: por definição, estes nomes não pertencem ao `.env.example`.
    nao_documentadas = sorted(lidas - documentadas - _SEM_DOCUMENTACAO)
    for nome in nao_documentadas:
        resultados.append(
            _aviso(
                grupo, nome, "lida pelo código e ausente do .env.example",
                "Acrescente ao .env.example, senão quem for configurar a "
                "máquina não vai saber que ela existe.",
            )
        )

    if not resultados:
        resultados.append(
            _ok(grupo, "nomes de variável", f"{len(documentadas)} documentadas, sem divergência")
        )

    return resultados
