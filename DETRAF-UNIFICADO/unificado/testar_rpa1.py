"""Teste de ponta a ponta do RPA 1 — captura, identificação e salvamento.

Exercita o robô **de verdade**: monta uma pasta de entrada com casos conhecidos,
chama `rpa1_captura/main.py` como subprocesso e confere no disco onde cada
arquivo foi parar. Não é a suíte de unidade (`rpa1_captura/tests`) — é o roteiro
do checklist `docs/03-checklists/homologacao-rpa1-e-rpa2.md` automatizado.

## Por que roda em caixa de areia

Tudo — árvore das operadoras, quarentena, não identificados, logs e **o banco** —
é redirecionado para `arquivos/_TESTE_RPA1/`, via variáveis de ambiente passadas
ao subprocesso. `load_dotenv()` não sobrescreve o que já está no ambiente, então
essas variáveis vencem o `.env` sem que ele precise ser tocado.

Isso importa por dois motivos: rodar o teste não suja a árvore de homologação
(que é evidência), e o `.env` não é reescrito entre execuções — reescrever o
`.env` durante a homologação é como se esquece um kill-switch ligado.

O SQLite é **copiado** para a caixa de areia antes da execução. O RPA 1 grava em
`tbl_rpa_log_detraf_despesa_arquivos` o que recusou e o que não identificou; sem
a cópia, cada rodada de teste deixaria linhas no espelho.

## O que cobre

| Caso | Espera |
|---|---|
| Detraf real da ALGAR (SMP e STFC) | salvo em `Algar/2026/{aaaamm}/Detrafs Recebidos`, byte a byte igual |
| Estrutura do mês | as quatro subpastas, clonadas do mês anterior |
| Layout com 5 colunas | quarentena + `_RECUSADO.md`, e **fora** da árvore das operadoras |
| EOT fora do Anexo 5 | recusado, e fora da árvore das operadoras |
| Grupo horário inválido | quarentena, com o motivo da coluna 8 |
| Referência de outro mês | quarentena, com o motivo da coluna 3 |
| Arquivo vazio | quarentena, sem derrubar o lote |
| Extensão não permitida (`.pdf`) | ignorado: nenhum rastro em lugar nenhum |
| Efeitos externos | nenhum e-mail — a execução é `--dry-run` e sem Outlook |

Uso::

    .venv\\Scripts\\python testar_rpa1.py
    .venv\\Scripts\\python testar_rpa1.py --referencia 202603 --verboso
    .venv\\Scripts\\python testar_rpa1.py --preflight     # roda verificar_ambiente antes
    .venv\\Scripts\\python testar_rpa1.py --manter        # não apaga a caixa de areia

Código de saída: 0 se todos os casos passaram, 1 se algum falhou.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

RAIZ = Path(__file__).resolve().parent
SANDBOX = RAIZ / "arquivos" / "_TESTE_RPA1"
INSUMOS_DETRAF = RAIZ / "Insumos" / "Detrafs recebidos"
BANCO_ESPELHO = RAIZ / "banco_de_dados" / "TABELAS_DETRAF_espelho.db"

#: Mês de tráfego padrão. É o dos Detrafs reais que vieram em `Insumos/` — trocar
#: sem trocar os insumos faz a coluna 3 reprovar todos eles, que é correto e
#: confuso de ler.
REFERENCIA_PADRAO = "202603"

#: EOT da ALGAR no Anexo 5 (`tbl_anexo5_processado`), e o nome de pasta que ela
#: gera. É o que os Detrafs reais de `Insumos/` trazem na coluna 1.
EOT_ALGAR = "025"
OPERADORA_ALGAR = "Algar"

#: EOT da Vivo, exigida na coluna 2 (devedora) pela regra `v_col2_vivo`.
EOT_VIVO = "010"

#: EOT que não consta do Anexo 5 — é o gatilho da regra `v_col1_2`.
EOT_FORA_DO_ANEXO5 = "997"

#: As quatro subpastas do mês (`SUBPASTA_*` no `.env`). O robô as cria clonando o
#: mês anterior; sem mês anterior, só a de recebidos nasce.
SUBPASTAS_DO_MES = ("AGI", "Contestações", "Detrafs Enviados", "Detrafs Recebidos")

SUFIXO_RECUSA = "_RECUSADO.md"


# ---------------------------------------------------------------------------
# Construção dos insumos sintéticos
# ---------------------------------------------------------------------------
#: Descritor cuja última letra (`L`) mapeia para a remuneração `TU-RL` — é o que
#: liga a linha à tabela de tarifas (`classificar_descritor_remuneracao`).
DESCRITOR_REMUNERADO = "LENL"

#: Descritor **fora** do conjunto remunerado (não termina em V, L, C ou I). As
#: linhas com ele saem do escopo da regra de tarifa, mas continuam válidas no
#: layout — descritores assim existem nos arquivos reais (`_NSN5`).
DESCRITOR_NAO_REMUNERADO = "LENX"

#: Tarifa de recheio para os casos que já vão ser recusados por outro motivo.
#: Não pode ser zero (regra da coluna 11) nem ter mais de 5 casas.
TARIFA_QUALQUER = "0,00631"


#: Separador dos Detrafs reais que a ALGAR entrega. Os decimais também são
#: vírgula, então os campos numéricos saem entre aspas — como no arquivo real.
SEPARADOR_REAL = ","


def campos_detraf(
    referencia: str,
    trafego: str | None = None,
    credora: str = EOT_ALGAR,
    devedora: str = EOT_VIVO,
    gh: str = "N",
    desc: str = DESCRITOR_NAO_REMUNERADO,
    tarifa: str = TARIFA_QUALQUER,
) -> list[str]:
    """As 15 colunas da V2, na ordem, para uma linha de tráfego."""
    return [
        credora,                # 1  Credora
        devedora,               # 2  Devedora
        referencia,             # 3  Referência — precisa ser a competência
        trafego or referencia,  # 4  Tráfego
        "SPOX_0001",            # 5  POI — escrita livre
        "0",                    # 6  Rel — 0 nas linhas de tráfego
        desc,                   # 7  DESC
        gh,                     # 8  GH — S, R, N ou D
        "1",                    # 9  Chamadas
        "2,0",                  # 10 Minutos
        tarifa,                 # 11 Tarifa
        "0,01",                 # 12 R$_Liq
        "0,00",                 # 13 PIS_Cofins
        "0,00",                 # 14 ICMS
        "0,01",                 # 15 R$_Bruto
    ]


def arquivo_detraf(
    destino: Path,
    referencia: str,
    linhas: int = 5,
    separador: str = SEPARADOR_REAL,
    **campos,
) -> Path:
    """
    Grava um Detraf sintético com `linhas` linhas iguais.

    Sem cabeçalho, como os Detrafs reais — `carregar_dados` detecta a ausência.

    O `separador` é parâmetro porque **ele muda o resultado**: a leitura para
    validar (`carregar_dados`) conta separadores para escolher, e a leitura para
    identificar a operadora (`_extrair_eot_csv`) usa o `csv.Sniffer`. Com
    decimais em vírgula as duas podem discordar — ver o caso
    `identificacao_com_ponto_e_virgula`.
    """
    with destino.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(
            arquivo, delimiter=separador, quoting=csv.QUOTE_MINIMAL, lineterminator="\n"
        )
        for _ in range(linhas):
            escritor.writerow(campos_detraf(referencia, **campos))
    return destino


def tarifa_regulada(banco: Path, referencia: str) -> str | None:
    """
    A tarifa regulada vigente para a ALGAR no mês, lida do próprio espelho.

    🔴 **É por isto que o caso do arquivo válido não usa um Detraf real.** A
    regra `v_tarifas_remuneradas` compara a tarifa da linha com a da tabela para
    a região, o GH, a regra do descritor e o mês de tráfego. Uma tarifa
    escolhida à mão só passa por coincidência — e quando a vigência do espelho
    mudar, o caso do caminho feliz começa a falhar por um motivo que não é
    defeito do robô.

    Lendo a tarifa da tabela, o insumo acompanha o espelho que estiver em uso.
    O filtro é o mesmo de `RepositorioTabelas.validar_tarifas_na_tabela`: GH
    (nulo aceita qualquer), região, `regra_desc`, `tipo_remuneracao` e a
    vigência que contém o mês de tráfego.

    Returns:
        A tarifa em formato brasileiro (`0,0061`), ou `None` quando o espelho
        não tem vigência para o mês — caso em que o insumo cai para um descritor
        não remunerado, que fica fora desta regra.
    """
    primeiro_dia_do_mes = f"{referencia[:4]}-{referencia[4:]}-01"

    with sqlite3.connect(banco) as conexao:
        regiao = conexao.execute(
            'SELECT "Regiao" FROM tbl_anexo5_processado WHERE TRIM(EOT) = ?',
            (EOT_ALGAR,),
        ).fetchone()
        if not regiao or not str(regiao[0]).strip():
            return None

        tarifas = conexao.execute(
            """
            SELECT tarifa FROM tbl_detraf_tarifas
             WHERE (TRIM(COALESCE(gh, '')) = ? OR TRIM(COALESCE(gh, '')) = '')
               AND TRIM(regiao) = ?
               AND regra_desc = ?
               AND tipo_remuneracao = ?
               AND date(data_inicio) <= ?
               AND ? <= date(data_fim)
            """,
            ("N", str(regiao[0]).strip(), 'DESC final L""', "TU-RL",
             primeiro_dia_do_mes, primeiro_dia_do_mes),
        ).fetchall()

    for (valor,) in tarifas:
        if not valor:  # a coluna 11 recusa tarifa zero
            continue
        # No máximo 5 casas decimais (regra da coluna 11), e o valor escrito
        # precisa voltar ao mesmo float — a comparação do robô é por igualdade.
        texto = f"{float(valor):.5f}".rstrip("0")
        if float(texto) == float(valor):
            return texto.replace(".", ",")

    return None


def sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Casos
# ---------------------------------------------------------------------------
@dataclass
class Caso:
    """Um cenário: o que entra, e o que precisa ser verdade depois."""

    nome: str
    descricao: str
    verificar: Callable[["Ambiente"], tuple[bool, str]]
    #: Preenchido pelo `preparar`, para a verificação saber o que procurar.
    dados: dict = field(default_factory=dict)


@dataclass
class Ambiente:
    """Os caminhos da caixa de areia, já resolvidos para a referência do teste."""

    referencia: str
    entrada: Path
    operadoras: Path
    quarentena: Path
    nao_identificados: Path
    banco: Path
    logs: Path
    casos: dict[str, Caso] = field(default_factory=dict)

    @property
    def ano(self) -> str:
        return self.referencia[:4]

    def mes_da_operadora(self, operadora: str, referencia: str | None = None) -> Path:
        return self.operadoras / operadora / (referencia or self.referencia)[:4] / (
            referencia or self.referencia
        )

    def recebidos(self, operadora: str) -> Path:
        return self.mes_da_operadora(operadora) / "Detrafs Recebidos"

    def pasta_de_quarentena(self, nome_arquivo: str) -> Path:
        """
        Onde a recusa de um arquivo vai parar.

        Numa pasta preparada à mão não há `entry_id`, então o robô usa o nome do
        arquivo como subpasta de evidência — ver `_pasta_da_evidencia`.
        """
        return self.quarentena / self.referencia / Path(nome_arquivo).stem

    def esta_na_arvore_das_operadoras(self, nome_arquivo: str) -> bool:
        if not self.operadoras.is_dir():
            return False
        return any(self.operadoras.rglob(nome_arquivo))


def _verificar_detraf_valido(nome: str) -> Callable[[Ambiente], tuple[bool, str]]:
    def verificar(ambiente: Ambiente) -> tuple[bool, str]:
        origem = ambiente.casos[nome].dados["origem"]
        destino = ambiente.recebidos(OPERADORA_ALGAR) / origem.name

        if not destino.is_file():
            return False, (
                f"não foi salvo em [{destino.relative_to(SANDBOX)}]. "
                f"{_onde_foi_parar(ambiente, origem.name)}"
            )

        if sha256(destino) != ambiente.casos[nome].dados["hash"]:
            return False, "foi salvo, mas o conteúdo mudou — a captura não pode transformar o arquivo."

        return True, f"salvo intacto em [{destino.parent.relative_to(SANDBOX)}]"

    return verificar


def _verificar_detraf_real(nome: str) -> Callable[[Ambiente], tuple[bool, str]]:
    """
    Um Detraf real da operadora tem **um dos dois destinos**, nunca nenhum.

    Não se pode afirmar que ele é salvo: se a tarifa que a operadora cobrou não
    corresponder à regulada do mês, a recusa é o comportamento CORRETO — e é o
    que acontece com os arquivos de `Insumos/` contra o espelho atual. Afirmar
    "tem de ser salvo" tornaria este caso um alarme que dispara quando o robô
    acerta.

    O que sempre vale, e é o que se afirma aqui: ou o arquivo é salvo **byte a
    byte igual** na pasta da operadora, ou é recusado **com o diagnóstico ao
    lado**. Sumir, ou chegar alterado, é defeito nos dois casos. O relatório diz
    qual dos dois aconteceu, e por quê.
    """

    def verificar(ambiente: Ambiente) -> tuple[bool, str]:
        origem = ambiente.casos[nome].dados["origem"]
        esperado = ambiente.casos[nome].dados["hash"]
        salvo = ambiente.recebidos(OPERADORA_ALGAR) / origem.name

        if salvo.is_file():
            if sha256(salvo) != esperado:
                return False, (
                    "foi salvo, mas o conteúdo mudou — a captura não transforma "
                    "arquivo, ela copia."
                )
            return True, f"aceito e salvo intacto em [{salvo.parent.relative_to(SANDBOX)}]"

        pasta = ambiente.pasta_de_quarentena(origem.name)
        em_quarentena = pasta / origem.name
        if not em_quarentena.is_file():
            return False, (
                f"não foi salvo nem posto em quarentena. "
                f"{_onde_foi_parar(ambiente, origem.name)}"
            )

        if sha256(em_quarentena) != esperado:
            return False, "está na quarentena com o conteúdo alterado — a evidência não serve."

        md = pasta / (origem.stem + SUFIXO_RECUSA)
        if not md.is_file():
            return False, f"em quarentena, mas sem o {SUFIXO_RECUSA} — sem o motivo, a recusa não é auditável."

        return True, (
            f"recusado (íntegro, com diagnóstico ao lado) — "
            f"{_resumir_motivos(md.read_text(encoding='utf-8'))}"
        )

    return verificar


def _onde_foi_parar(ambiente: Ambiente, nome_arquivo: str) -> str:
    """Onde o arquivo está, para a mensagem de falha não exigir uma caça."""
    achados = []
    for rotulo, raiz in (
        ("árvore das operadoras", ambiente.operadoras),
        ("quarentena", ambiente.quarentena),
        ("não identificados", ambiente.nao_identificados),
    ):
        if raiz.is_dir() and any(raiz.rglob(nome_arquivo)):
            achados.append(rotulo)
    return f"Encontrado em: {', '.join(achados)}." if achados else "Não está em lugar nenhum."


def _verificar_operadora_correta(nome: str) -> Callable[[Ambiente], tuple[bool, str]]:
    """
    O arquivo foi para a pasta da operadora **certa**.

    Diferente de `_verificar_detraf_valido`, que só olha o caminho esperado:
    aqui interessa o caminho ERRADO, porque o modo de falha é o arquivo ser
    salvo com sucesso na pasta de outra operadora. Ninguém percebe — não há
    erro, não há recusa, e o Detraf entra na apuração de quem não o mandou.
    """

    def verificar(ambiente: Ambiente) -> tuple[bool, str]:
        arquivo = ambiente.casos[nome].dados["origem"]
        certo = ambiente.recebidos(OPERADORA_ALGAR) / arquivo.name

        if certo.is_file():
            return True, f"identificado como {OPERADORA_ALGAR}, pela EOT credora"

        if not ambiente.operadoras.is_dir():
            return False, "não foi salvo em operadora nenhuma"

        errados = sorted(
            achado.relative_to(ambiente.operadoras).parts[0]
            for achado in ambiente.operadoras.rglob(arquivo.name)
        )
        if errados:
            return False, (
                f"salvo na pasta de {', '.join(errados)} — a operadora ERRADA "
                f"(a credora do arquivo é a EOT {EOT_ALGAR}, {OPERADORA_ALGAR}). "
                f"O arquivo entra na apuração de quem não o mandou, sem erro "
                f"nenhum no log."
            )

        return False, (
            f"não chegou à pasta de {OPERADORA_ALGAR}. "
            f"{_onde_foi_parar(ambiente, arquivo.name)}"
        )

    return verificar


def _verificar_estrutura_do_mes(ambiente: Ambiente) -> tuple[bool, str]:
    mes = ambiente.mes_da_operadora(OPERADORA_ALGAR)
    if not mes.is_dir():
        return False, f"a pasta do mês não foi criada em [{mes.relative_to(SANDBOX)}]"

    faltando = [sub for sub in SUBPASTAS_DO_MES if not (mes / sub).is_dir()]
    if faltando:
        return False, (
            f"faltam as subpastas {faltando} em [{mes.relative_to(SANDBOX)}] — "
            f"a clonagem do mês anterior não aconteceu."
        )
    return True, f"as {len(SUBPASTAS_DO_MES)} subpastas foram clonadas do mês anterior"


def _verificar_recusa(
    nome: str, motivo_esperado: str, exigir_md: bool = True
) -> Callable[[Ambiente], tuple[bool, str]]:
    """
    O arquivo foi recusado, ficou fora da árvore das operadoras e o motivo é o
    esperado.

    `motivo_esperado` é procurado como substring no `_RECUSADO.md`. Outros
    motivos podem aparecer junto — a validação coleta todas as regras que
    falharam, e exigir que só uma falhe tornaria o caso frágil.
    """

    def verificar(ambiente: Ambiente) -> tuple[bool, str]:
        arquivo = ambiente.casos[nome].dados["origem"]

        if ambiente.esta_na_arvore_das_operadoras(arquivo.name):
            return False, (
                "ENTROU na árvore das operadoras. Um arquivo recusado não pode "
                "chegar lá — o RPA 2 o encontraria e responderia à operadora "
                "uma segunda vez."
            )

        pasta = ambiente.pasta_de_quarentena(arquivo.name)
        if not (pasta / arquivo.name).is_file():
            return False, f"não está na quarentena ([{pasta.relative_to(SANDBOX)}])"

        if not exigir_md:
            return True, f"em quarentena, em [{pasta.relative_to(SANDBOX)}]"

        md = pasta / (arquivo.stem + SUFIXO_RECUSA)
        if not md.is_file():
            return False, (
                f"está na quarentena, mas sem o {SUFIXO_RECUSA} ao lado — "
                f"o diagnóstico é o entregável da recusa."
            )

        texto = md.read_text(encoding="utf-8")
        if motivo_esperado.lower() not in texto.lower():
            return False, (
                f"recusado, mas o motivo não menciona '{motivo_esperado}'. "
                f"O {SUFIXO_RECUSA} diz: {_resumir_motivos(texto)}"
            )

        return True, f"recusado por '{motivo_esperado}', com diagnóstico ao lado"

    return verificar


def _resumir_motivos(texto_md: str) -> str:
    """
    Os motivos do `_RECUSADO.md`, numa linha.

    Lê as três formas que o `.md` usa, porque cada portão escreve de um jeito:
    o motivo solto (layout com colunas de menos), a lista `- ` (regras de
    coluna) e a tabela por posição (layout deslocado).
    """
    motivos: list[str] = []
    dentro_da_secao = False

    for linha in texto_md.splitlines():
        crua = linha.strip()

        if crua.startswith("## "):
            dentro_da_secao = crua == "## Por que foi recusado"
            continue
        if not dentro_da_secao or not crua:
            continue

        if crua.startswith("- "):
            motivos.append(crua[2:])
        elif crua.startswith("|") and not crua.startswith("|---") and "Posição" not in crua:
            celulas = [celula.strip() for celula in crua.strip("|").split("|")]
            if len(celulas) >= 4:
                motivos.append(
                    f"posição {celulas[0]} ({celulas[1]}): esperado {celulas[2]}, "
                    f"encontrado {celulas[3]}"
                )
        elif not crua.startswith("|"):
            motivos.append(crua)

    return "; ".join(motivos[:3]) or "(sem motivo legível)"


def _verificar_fora_da_arvore(nome: str) -> Callable[[Ambiente], tuple[bool, str]]:
    """
    O arquivo não entrou na árvore das operadoras.

    É a invariante que vale para os dois destinos de exceção — quarentena e
    `_NAO_IDENTIFICADOS` — e por isso serve para o caso em que qual dos dois vai
    receber depende de o EOT constar do Anexo 5.
    """

    def verificar(ambiente: Ambiente) -> tuple[bool, str]:
        arquivo = ambiente.casos[nome].dados["origem"]

        if ambiente.esta_na_arvore_das_operadoras(arquivo.name):
            return False, "ENTROU na árvore das operadoras"

        for rotulo, raiz in (
            ("quarentena", ambiente.quarentena),
            ("não identificados", ambiente.nao_identificados),
        ):
            if raiz.is_dir() and any(raiz.rglob(arquivo.name)):
                return True, f"fora da árvore, em {rotulo}"

        return False, (
            "sumiu: não está na árvore das operadoras, nem na quarentena, nem "
            "em _NAO_IDENTIFICADOS. Um arquivo que chega precisa deixar rastro."
        )

    return verificar


def _verificar_extensao_ignorada(nome: str) -> Callable[[Ambiente], tuple[bool, str]]:
    def verificar(ambiente: Ambiente) -> tuple[bool, str]:
        arquivo = ambiente.casos[nome].dados["origem"]
        for raiz in (ambiente.operadoras, ambiente.quarentena, ambiente.nao_identificados):
            if raiz.is_dir() and any(raiz.rglob(arquivo.name)):
                return False, (
                    f"foi processado, e não devia: `{arquivo.suffix}` não está em "
                    f"EXTENSOES_PERMITIDAS. Encontrado sob [{raiz.name}]."
                )
        return True, f"ignorado, como esperado para `{arquivo.suffix}`"

    return verificar


def _verificar_sem_efeito_externo(ambiente: Ambiente) -> tuple[bool, str]:
    """
    Nenhuma operadora foi notificada.

    Duas afirmações, e as duas precisam valer. A primeira é sobre a intenção — o
    resumo de arranque tem de mostrar o kill-switch desligado. A segunda é sobre
    o fato: nenhuma recusa pode ter saído com "operadora notificada: sim".

    Numa pasta preparada à mão não há e-mail de origem, então o robô não teria
    como responder de qualquer forma. Isso **não** substitui a verificação: é
    justamente com o switch ligado e um rastreamento presente que o envio
    aconteceria, e é esse par que se quer ver desarmado.
    """
    saida = ambiente.casos["efeitos_externos"].dados["saida_do_robo"]

    if "e-mail à operadora (RPA 1): LIGADO" in saida:
        return False, "o resumo de arranque mostra o kill-switch de e-mail LIGADO"

    if "operadora notificada: sim" in saida.lower():
        return False, (
            "alguma operadora foi notificada. Numa execução --dry-run isso não "
            "pode acontecer — confira o log antes de repetir o teste."
        )

    if "reprovado" not in saida.lower() and "Reprovados: 0" in saida:
        return False, (
            "nenhum arquivo foi reprovado nesta execução, então esta verificação "
            "não provou nada. Os casos de recusa precisam estar falhando também."
        )

    return True, "kill-switch desligado e nenhuma operadora notificada"


# ---------------------------------------------------------------------------
# Montagem da caixa de areia
# ---------------------------------------------------------------------------
def preparar(referencia: str) -> Ambiente:
    """Cria a caixa de areia do zero e devolve os caminhos e os casos."""

    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)

    entrada = SANDBOX / "Entrada"
    entrada.mkdir(parents=True)

    ambiente = Ambiente(
        referencia=referencia,
        entrada=entrada,
        operadoras=SANDBOX / "Operadoras",
        quarentena=SANDBOX / "_QUARENTENA",
        nao_identificados=SANDBOX / "_NAO_IDENTIFICADOS",
        banco=SANDBOX / "banco.db",
        logs=SANDBOX / "logs",
    )

    if not BANCO_ESPELHO.is_file():
        raise SystemExit(
            f"O espelho do banco não existe em [{BANCO_ESPELHO}]. "
            f"Gere-o com `python espelhar_banco.py` (ou `preparar_banco_dev.py`) "
            f"antes de rodar este teste — sem Anexo 5 o robô não identifica "
            f"operadora nenhuma e todos os casos falham pelo mesmo motivo."
        )
    shutil.copy2(BANCO_ESPELHO, ambiente.banco)
    _conferir_anexo5(ambiente.banco)

    casos: list[Caso] = []

    # --- 1. O caminho feliz ----------------------------------------------
    # Sintético, e não um Detraf real, por um motivo específico: a tarifa. Ver
    # `tarifa_regulada` — um arquivo real só passa se a tarifa que a operadora
    # cobrou for a regulada daquele mês, e isso é o que o robô existe para
    # conferir, não algo que o teste possa pressupor.
    tarifa = tarifa_regulada(ambiente.banco, referencia)
    if tarifa:
        descritor, nota = DESCRITOR_REMUNERADO, f"tarifa regulada {tarifa}"
    else:
        # Sem vigência no espelho, a saída é sair do escopo da regra — não
        # inventar uma tarifa que seria recusada.
        descritor, tarifa = DESCRITOR_NAO_REMUNERADO, TARIFA_QUALQUER
        nota = "linha não remunerada (o espelho não tem tarifa vigente no mês)"

    arquivo = arquivo_detraf(
        entrada / "VALIDO_algar.csv", referencia, desc=descritor, tarifa=tarifa
    )
    casos.append(
        Caso(
            nome="detraf_valido",
            descricao=f"Detraf válido da ALGAR — {nota}",
            verificar=_verificar_detraf_valido("detraf_valido"),
            dados={"origem": arquivo, "hash": sha256(arquivo)},
        )
    )

    # --- 2. O mesmo arquivo, separado por `;` ----------------------------
    # Mesmo conteúdo do caso acima, só que com `;`. Existe porque o robô lê o
    # arquivo DUAS vezes, com detectores de separador diferentes:
    # `carregar_dados` conta separadores (e acerta o `;`), enquanto
    # `_extrair_eot_csv` usa o `csv.Sniffer` (que, com decimais em vírgula,
    # escolhe `,`). Divergindo, o arquivo é validado certo e identificado
    # errado — e o efeito não é uma recusa, é ir para a pasta de outra
    # operadora.
    arquivo = arquivo_detraf(
        entrada / "VALIDO_ponto_e_virgula.csv",
        referencia,
        separador=";",
        desc=descritor,
        tarifa=tarifa,
    )
    casos.append(
        Caso(
            nome="identificacao_com_ponto_e_virgula",
            descricao="Detraf válido separado por `;` — vai para a operadora certa?",
            verificar=_verificar_operadora_correta("identificacao_com_ponto_e_virgula"),
            dados={"origem": arquivo},
        )
    )

    # --- 3 e 4. Os Detrafs reais da ALGAR --------------------------------
    # Vêm de `Insumos/`, sem uma vírgula alterada. O que se afirma sobre eles é
    # a invariante dos dois destinos — ver `_verificar_detraf_real`.
    reais = sorted(INSUMOS_DETRAF.glob("*.csv")) if INSUMOS_DETRAF.is_dir() else []
    if not reais:
        raise SystemExit(
            f"Nenhum Detraf real em [{INSUMOS_DETRAF}]. Este teste depende deles "
            f"para exercitar o robô contra um arquivo que a operadora mandou de "
            f"verdade — o sintético não tem as 18 colunas nem a linha de total."
        )

    for indice, origem in enumerate(reais, start=1):
        destino = entrada / origem.name
        shutil.copy2(origem, destino)
        nome = f"detraf_real_{indice}"
        casos.append(
            Caso(
                nome=nome,
                descricao=f"Detraf real da ALGAR — {origem.name[:44]}…",
                verificar=_verificar_detraf_real(nome),
                dados={"origem": destino, "hash": sha256(destino)},
            )
        )

    # --- 5. Estrutura do mês, clonada do anterior ------------------------
    # O mês anterior é criado com as quatro subpastas ANTES da execução. Sem
    # ele, `clonar_estrutura_mes_anterior` degrada para uma pasta vazia — o que
    # é correto e faria este caso falhar por um motivo que não é defeito.
    mes_anterior = _mes_anterior(referencia)
    for subpasta in SUBPASTAS_DO_MES:
        (
            ambiente.mes_da_operadora(OPERADORA_ALGAR, mes_anterior) / subpasta
        ).mkdir(parents=True, exist_ok=True)

    casos.append(
        Caso(
            nome="estrutura_do_mes",
            descricao=f"As quatro subpastas do mês, clonadas de {mes_anterior}",
            verificar=_verificar_estrutura_do_mes,
        )
    )

    # --- 6. Layout fora do padrão ----------------------------------------
    arquivo = entrada / "RECUSA_layout_5_colunas.csv"
    arquivo.write_text(
        "\n".join(f"{EOT_ALGAR};{EOT_VIVO};{referencia};N;1" for _ in range(5)) + "\n",
        encoding="utf-8",
    )
    casos.append(
        Caso(
            nome="layout_quebrado",
            descricao="Arquivo com 5 colunas (o layout da V2 exige 15)",
            verificar=_verificar_recusa("layout_quebrado", "ao menos 15 colunas"),
            dados={"origem": arquivo},
        )
    )

    # --- 7. EOT fora do Anexo 5 ------------------------------------------
    # O destino depende de qual portão pega primeiro: a validação da coluna 1
    # (quarentena) ou a identificação da operadora (_NAO_IDENTIFICADOS). A
    # invariante que vale nos dois casos é não entrar na árvore — é o que se
    # afirma aqui.
    arquivo = arquivo_detraf(
        entrada / "RECUSA_eot_desconhecida.csv", referencia, credora=EOT_FORA_DO_ANEXO5
    )
    casos.append(
        Caso(
            nome="eot_fora_do_anexo5",
            descricao=f"Credora EOT {EOT_FORA_DO_ANEXO5}, que não consta do Anexo 5",
            verificar=_verificar_fora_da_arvore("eot_fora_do_anexo5"),
            dados={"origem": arquivo},
        )
    )

    # --- 8. Grupo horário inválido ---------------------------------------
    # Quem pega é o LAYOUT, não a regra da coluna 8: a posição 7 (GH) tem
    # verificador próprio, e o layout roda antes. Por isso o motivo esperado é o
    # texto da tabela de posições, e não a frase da regra — as duas dizem
    # "S, R, N ou D", que é o que se procura.
    arquivo = arquivo_detraf(entrada / "RECUSA_gh_invalido.csv", referencia, gh="X")
    casos.append(
        Caso(
            nome="gh_invalido",
            descricao="Coluna 8 com grupo horário 'X' (válidos: S, R, N, D)",
            verificar=_verificar_recusa("gh_invalido", "S, R, N ou D"),
            dados={"origem": arquivo},
        )
    )

    # --- 9. Referência de outro mês --------------------------------------
    arquivo = arquivo_detraf(
        entrada / "RECUSA_referencia_errada.csv", _mes_anterior(referencia, meses=6)
    )
    casos.append(
        Caso(
            nome="referencia_errada",
            descricao="Coluna 3 com referência de seis meses atrás",
            verificar=_verificar_recusa("referencia_errada", "a referência precisa ser"),
            dados={"origem": arquivo},
        )
    )

    # --- 10. Arquivo vazio -------------------------------------------------
    # Ilegível é recusa, não erro: se virasse erro o arquivo ficaria preso na
    # entrada, retentado para sempre, sem ninguém ser avisado. O `.md` pode não
    # sair aqui, porque não há conteúdo para amostrar — por isso não é exigido.
    arquivo = entrada / "RECUSA_vazio.csv"
    arquivo.write_text("", encoding="utf-8")
    casos.append(
        Caso(
            nome="arquivo_vazio",
            descricao="Arquivo vazio — precisa ser recusado sem derrubar o lote",
            verificar=_verificar_recusa("arquivo_vazio", "", exigir_md=False),
            dados={"origem": arquivo},
        )
    )

    # --- 11. Extensão não permitida ---------------------------------------
    arquivo = entrada / "IGNORAR_anexo_qualquer.pdf"
    arquivo.write_bytes(b"%PDF-1.4\n% nao e um Detraf\n")
    casos.append(
        Caso(
            nome="extensao_ignorada",
            descricao="Anexo `.pdf` — fora de EXTENSOES_PERMITIDAS",
            verificar=_verificar_extensao_ignorada("extensao_ignorada"),
            dados={"origem": arquivo},
        )
    )

    # --- 12. Nenhum efeito externo ---------------------------------------
    casos.append(
        Caso(
            nome="efeitos_externos",
            descricao="Nenhum e-mail enviado (execução --dry-run e sem Outlook)",
            verificar=_verificar_sem_efeito_externo,
        )
    )

    ambiente.casos = {caso.nome: caso for caso in casos}
    return ambiente


def _mes_anterior(aaaamm: str, meses: int = 1) -> str:
    ano, mes = int(aaaamm[:4]), int(aaaamm[4:])
    total = ano * 12 + (mes - 1) - meses
    return f"{total // 12:04d}{total % 12 + 1:02d}"


def _conferir_anexo5(banco: Path) -> None:
    """
    Falha cedo se o Anexo 5 do espelho não tiver as EOTs que os casos usam.

    Sem isto, um espelho gerado de outra base faria **todos** os casos falharem
    de uma vez, e a mensagem de cada um apontaria para o robô em vez de para o
    banco.
    """
    with sqlite3.connect(banco) as conexao:
        presentes = {
            str(linha[0]).strip()
            for linha in conexao.execute(
                "SELECT EOT FROM tbl_anexo5_processado WHERE TRIM(EOT) IN (?, ?, ?)",
                (EOT_ALGAR, EOT_VIVO, EOT_FORA_DO_ANEXO5),
            )
        }

    if EOT_FORA_DO_ANEXO5 in presentes:
        raise SystemExit(
            f"A EOT {EOT_FORA_DO_ANEXO5}, que este teste usa como 'desconhecida', "
            f"consta do Anexo 5 deste espelho. Escolha outra em "
            f"EOT_FORA_DO_ANEXO5."
        )

    faltando = {EOT_ALGAR, EOT_VIVO} - presentes
    if faltando:
        raise SystemExit(
            f"O Anexo 5 do espelho não tem as EOTs {sorted(faltando)}. "
            f"O teste as usa como credora ({EOT_ALGAR}, ALGAR) e devedora "
            f"({EOT_VIVO}, Vivo) — sem elas nenhum arquivo passa na validação. "
            f"Regere o espelho com `python espelhar_banco.py`."
        )


# ---------------------------------------------------------------------------
# Execução do robô
# ---------------------------------------------------------------------------
def montar_ambiente_do_subprocesso(ambiente: Ambiente) -> dict[str, str]:
    """
    O ambiente do subprocesso — a caixa de areia inteira, por variável.

    `load_dotenv()` **não sobrescreve** o que já existe em `os.environ`, então
    estas vencem o `.env` sem que ele seja tocado. As variantes com sufixo por
    robô (`ENV_RPA1`, `CAMINHO_OPERADORAS_RPA1`) são apagadas: elas venceriam
    estas, e o teste rodaria contra a árvore de verdade sem avisar.
    """
    variaveis = {
        "ENV": "dev",
        "CAMINHO_SQLITE": str(ambiente.banco),
        "CAMINHO_SQLITE_DEV": "",
        "CAMINHO_OPERADORAS": str(ambiente.operadoras),
        # Aliases da MESMA pasta, herdados dos projetos de origem. Se ficarem
        # apontando para o `.env`, o RPA 2 lido depois olharia outra árvore.
        "CAMINHO_DETRAF_RECEBIDO": str(ambiente.operadoras),
        "DIRETORIO_SAIDA": str(ambiente.operadoras),
        "DIRETORIO_NAO_IDENTIFICADOS": str(ambiente.nao_identificados),
        "DIRETORIO_QUARENTENA": str(ambiente.quarentena),
        "DIRETORIO_TEMP": str(SANDBOX / "_TEMP"),
        "DIRETORIO_SAIDA_VALIDACAO": str(SANDBOX / "_SAIDA"),
        "DIRETORIO_HISTORICO_ARQUIVOS": str(SANDBOX / "historico"),
        "RASTREAMENTO_ARQUIVO_PATH": str(ambiente.entrada / "_rastreamento.json"),
        "RAIZ_LOGS": str(ambiente.logs),
        # Kill-switches. O `--dry-run` já os desarma; ficam explícitos porque
        # este script escreve o ambiente inteiro, e um switch herdado do `.env`
        # da máquina é exatamente o que não se quer descobrir depois.
        "NOTIFICAR_OPERADORA_ENVIAR": "false",
        "PERMITIR_ENVIO_EMAIL": "false",
        "PERMITIR_UPLOAD_AGI": "false",
        "PERMITIR_ACESSO_AGI": "false",
        "PERMITIR_DOWNLOAD_SFTP": "false",
        # A parada interativa travaria o subprocesso esperando um clique.
        "PAUSA_ENTRE_ETAPAS": "false",
    }

    do_processo = dict(os.environ)
    for nome in list(do_processo):
        if any(nome == f"{base}_RPA1" for base in variaveis):
            del do_processo[nome]
    do_processo.update(variaveis)
    return do_processo


def executar_robo(ambiente: Ambiente, verboso: bool) -> tuple[int, str]:
    """Roda `rpa1_captura/main.py` sobre a caixa de areia e devolve (código, saída)."""

    comando = [
        sys.executable,
        str(RAIZ / "rpa1_captura" / "main.py"),
        "--pasta-entrada", str(ambiente.entrada),
        "--referencia", ambiente.referencia,
        "--etapa", "processamento",
        "--dry-run",
    ]

    print(f"  $ {' '.join(comando[1:])}\n")

    processo = subprocess.run(
        comando,
        cwd=RAIZ,
        env=montar_ambiente_do_subprocesso(ambiente),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    saida = (processo.stdout or "") + (processo.stderr or "")
    if verboso:
        print(saida)

    return processo.returncode, saida


def executar_preflight() -> int:
    """`verificar_ambiente.py --rpa rpa1`, contra o `.env` REAL da máquina."""
    print("\n--- Pré-condições (verificar_ambiente.py --rpa rpa1) ---\n")
    processo = subprocess.run(
        [sys.executable, str(RAIZ / "verificar_ambiente.py"), "--rpa", "rpa1"],
        cwd=RAIZ,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return processo.returncode


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------
def relatar(ambiente: Ambiente, codigo_do_robo: int) -> bool:
    resultados: list[tuple[str, bool, str, str]] = []

    for caso in ambiente.casos.values():
        try:
            passou, detalhe = caso.verificar(ambiente)
        except Exception as erro:  # a verificação não pode derrubar o relatório
            passou, detalhe = False, f"a verificação falhou: {erro!r}"
        resultados.append((caso.nome, passou, caso.descricao, detalhe))

    largura = max(len(nome) for nome, *_ in resultados)

    print(f"\n{'=' * 78}")
    print("RESULTADO POR CASO")
    print("=" * 78)
    for nome, passou, descricao, detalhe in resultados:
        marca = "OK  " if passou else "FALHA"
        print(f"\n[{marca}] {nome.ljust(largura)}  {descricao}")
        print(f"         -> {detalhe}")

    falhas = [nome for nome, passou, *_ in resultados if not passou]

    print(f"\n{'=' * 78}")
    print(
        f"{len(resultados) - len(falhas)}/{len(resultados)} casos OK  |  "
        f"código de saída do robô: {codigo_do_robo}"
    )
    if falhas:
        print(f"Falharam: {', '.join(falhas)}")
    print(f"Evidência em: {SANDBOX}")
    print("=" * 78)

    # O código do robô entra no veredito: com `--dry-run` e insumos preparados,
    # uma recusa é caminho normal e ele precisa terminar em 0. Sair 1 significa
    # exceção não tratada; 2, cancelamento pelo operador.
    return not falhas and codigo_do_robo == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="testar_rpa1.py",
        description=(
            "Teste de ponta a ponta do RPA 1, em caixa de areia. Nada fora de "
            "arquivos/_TESTE_RPA1/ é tocado — nem a árvore de homologação, nem "
            "o banco, nem o .env."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "A caixa de areia é recriada do zero a cada execução, então repetir "
            "o teste não exige resetar_homologacao.py."
        ),
    )
    parser.add_argument(
        "--referencia",
        default=REFERENCIA_PADRAO,
        metavar="AAAAMM",
        help=(
            f"Mês de tráfego (default: {REFERENCIA_PADRAO}). Os Detrafs reais de "
            f"Insumos/ são de {REFERENCIA_PADRAO}; com outro mês eles são "
            f"recusados pela coluna 3, corretamente."
        ),
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Roda verificar_ambiente.py --rpa rpa1 antes (contra o .env real).",
    )
    parser.add_argument(
        "--verboso",
        action="store_true",
        help="Mostra a saída completa do robô, e não só o veredito dos casos.",
    )
    parser.add_argument(
        "--manter",
        action="store_true",
        help=(
            "Mantém a caixa de areia ao final (o default já a mantém; a flag "
            "existe para deixar a intenção explícita no comando)."
        ),
    )
    args = parser.parse_args(argv)

    # O console do Windows é cp1252, e tanto o log do robô quanto os nomes de
    # pasta (`Contestações`) saem daqui. Sem isto, o relatório morre com
    # UnicodeEncodeError DEPOIS de o teste ter rodado — e o resultado se perde.
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8", errors="replace")

    if not args.referencia.isdigit() or len(args.referencia) != 6:
        parser.error(f"'{args.referencia}' não é AAAAMM — ex.: {REFERENCIA_PADRAO}.")

    if args.preflight and executar_preflight() != 0:
        print(
            "\nO pré-flight acusou falhas. Elas são do .env REAL, e este teste "
            "roda em caixa de areia — ele continua valendo, mas a homologação "
            "manual não vai passar até que sejam corrigidas.\n"
        )

    print(f"\n--- Preparando a caixa de areia em {SANDBOX} ---\n")
    ambiente = preparar(args.referencia)
    print(f"  {len(ambiente.casos)} casos montados, referência {args.referencia}\n")

    print("--- Executando o RPA 1 ---\n")
    codigo, saida = executar_robo(ambiente, args.verboso)

    # A verificação de efeitos externos lê a saída do robô; os demais casos leem
    # o disco.
    ambiente.casos["efeitos_externos"].dados["saida_do_robo"] = saida

    if codigo != 0 and not args.verboso:
        print("A execução terminou com código != 0. Saída do robô:\n")
        print(saida[-4000:])

    return 0 if relatar(ambiente, codigo) else 1


if __name__ == "__main__":
    raise SystemExit(main())
