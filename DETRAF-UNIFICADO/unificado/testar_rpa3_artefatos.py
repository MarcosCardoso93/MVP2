"""Teste de ponta a ponta da etapa `artefatos` do RPA 3 (HU-12 a HU-16, HU-19).

Mesmo espírito de `testar_rpa1.py`: monta um cenário sintético, chama
`rpa3_contestacao_agi_ec/main.py` como subprocesso de verdade e confere no disco
o que saiu — mas **só a etapa `artefatos`**. As outras três (`carga`, `email`,
`verificacao`) escrevem para fora (AGI, e-mail da operadora) e não têm como ser
exercitadas com segurança fora de um ambiente real — ver
`docs/03-checklists/homologacao-rpa3.md`. Este script nunca passa `--etapa`
diferente de `artefatos`, e por isso nunca abre o AGI nem toca no Outlook.

## Por que roda em caixa de areia

Igual ao RPA 1: árvore de operadoras, controle de numeração CT, logs e **uma
cópia do banco** ficam em `arquivos/_TESTE_RPA3/`, via variáveis de ambiente
passadas ao subprocesso. Nada na árvore de homologação, no `.env` ou no banco
real é tocado.

O banco precisa de um ajuste que o do RPA 1 não precisa: este script **grava**
uma linha em `tbl_rpa_log_detraf_despesa_contestacao` antes de rodar — é o
"sinal do analista" (`tipo_contestacao`) que, em produção, vem do WebFat depois
da HU-11. Sem essa linha, o RPA 3 gera os artefatos que não dependem de
contestação (EXT) e pula os que dependem (INT, `_EXP`, carta, CONT_PROC) — é o
próprio comportamento documentado, não uma falha do teste. Ver a seção
"pré-condição que não é técnica" do checklist de homologação.

## O que cobre

| Operadora sintética | Cenário | Espera |
|---|---|---|
| `Algar` | Detraf + expectativa divergentes, sinal "COM retenção" gravado | EXT, INT, `_EXP`, 1 carta e CONT_PROC — os cinco artefatos |
| `SemExpectativa` | Detraf sem nenhum arquivo de expectativa Vivo | só EXT; pulo "sem expectativa Vivo" |
| `SemDetraf` | Pasta "Detrafs Recebidos" vazia | nada gerado; pulo "sem Detraf recebido" |
| `SemContestacao` | Detraf e expectativa **iguais** (variação 0%) | só EXT; sem pulo — é "nada a contestar", não falta de insumo |

A leitura do que saiu é dupla, como no RPA 1: os arquivos no disco (prova
definitiva) e o relatório `.md` que o próprio robô grava por execução
(`logs/{host}/rpa3_contestacao_agi_ec/execucoes/`), que traz o "pulo" com o
motivo — é o mesmo relatório que a homologação manual usa.

Uso::

    .venv\\Scripts\\python testar_rpa3_artefatos.py
    .venv\\Scripts\\python testar_rpa3_artefatos.py --referencia 202603 --verboso

Código de saída: 0 se todos os casos passaram, 1 se algum falhou.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

RAIZ = Path(__file__).resolve().parent
SANDBOX = RAIZ / "arquivos" / "_TESTE_RPA3"
BANCO_ESPELHO = RAIZ / "banco_de_dados" / "TABELAS_DETRAF_espelho.db"

REFERENCIA_PADRAO = "202603"

#: Descritor cujo último caractere ("L") mapeia para "TU-RL" em
#: `tbl_detraf_mapeamento_descritores` — confirmado no espelho (linha do
#: caractere final "L", produto "DETRAF"). É a MESMA regra usada no teste do
#: RPA 1 (`testar_rpa1.py`), por isso a coincidência de sufixo não é acidente.
DESCRITOR_REMUNERADO = "LENL"
REMUNERACAO_ESPERADA = "TU-RL"

#: EOT sintéticas — não precisam constar do Anexo 5: o RPA 3 não identifica
#: operadora por EOT (isso é HU-02, do RPA 1); aqui a "operadora" é só o nome
#: da pasta, e a EOT dentro do arquivo serve unicamente para agrupar e casar
#: com o sinal do analista.
EOT_OPERADORA = "025"
EOT_VIVO = "010"


class Falha(Exception):
    """Uma checagem de preparo falhou. A mensagem já é o que vai para o console."""


# ---------------------------------------------------------------------------
# Construção dos insumos sintéticos
# ---------------------------------------------------------------------------
def campos_detraf(
    referencia: str,
    r_bruto: str,
    credora: str = EOT_OPERADORA,
    devedora: str = EOT_VIVO,
    minutos: str = "100,0",
) -> list[str]:
    """As 15 colunas da V2, na ordem — mesmo layout usado por `testar_rpa1.py`."""
    return [
        credora,               # 1  Credora
        devedora,               # 2  Devedora
        referencia,             # 3  Referência
        referencia,             # 4  Tráfego
        "SPOX_0001",            # 5  POI
        "0",                    # 6  Rel — 0 nas linhas de tráfego
        DESCRITOR_REMUNERADO,   # 7  DESC — final "L" -> TU-RL
        "N",                    # 8  GH
        "10",                   # 9  Chamadas
        minutos,                # 10 Minutos
        "0,01",                 # 11 Tarifa
        "50,00",                # 12 R$_Liq
        "4,50",                 # 13 PIS_Cofins
        "8,00",                 # 14 ICMS
        r_bruto,                # 15 R$_Bruto — é o que o Contest compara
    ]


def escrever_csv(destino: Path, linhas: list[list[str]]) -> Path:
    """Grava linhas de Detraf sintéticas, sem cabeçalho — `carregar_dados` detecta a ausência."""
    destino.write_text(
        "\n".join(";".join(campos) for campos in linhas) + "\n", encoding="utf-8"
    )
    return destino


# ---------------------------------------------------------------------------
# Casos
# ---------------------------------------------------------------------------
@dataclass
class Caso:
    nome: str
    operadora: str
    descricao: str
    verificar: Callable[["Ambiente"], tuple[bool, str]]


@dataclass
class Ambiente:
    referencia: str
    operadoras: Path
    banco: Path
    raiz_logs: Path
    linhas_relatorio: dict[str, dict] = field(default_factory=dict)
    casos: dict[str, Caso] = field(default_factory=dict)

    @property
    def ano(self) -> str:
        return self.referencia[:4]

    def pasta_mes(self, operadora: str) -> Path:
        return self.operadoras / operadora / self.ano / self.referencia

    def pasta_agi(self, operadora: str) -> Path:
        return self.pasta_mes(operadora) / "AGI"

    def pasta_contestacoes(self, operadora: str) -> Path:
        return self.pasta_mes(operadora) / "Contestações"

    def existe_na_agi(self, operadora: str, sufixo_glob: str) -> bool:
        pasta = self.pasta_agi(operadora)
        return pasta.is_dir() and any(pasta.glob(sufixo_glob))


# ---------------------------------------------------------------------------
# Leitura do relatório de execução — a mesma fonte que a homologação manual usa
# ---------------------------------------------------------------------------
def ler_ultimo_relatorio(raiz_logs: Path) -> dict[str, dict]:
    """
    Lê o `.md` mais recente em `{raiz_logs}/{host}/rpa3_contestacao_agi_ec/execucoes/`
    e devolve ``{operadora: {"situacao": ..., "pulos": ..., "produzidos": {...}}}``.

    Fonte: `comum/config/relatorio_execucao.py`. As colunas do meio variam
    (são as chaves de `produzidos` que apareceram naquela execução), então a
    leitura é posicional a partir do cabeçalho, não por índice fixo.
    """
    candidatos = sorted(raiz_logs.rglob("rpa3_contestacao_agi_ec/execucoes/*.md"))
    if not candidatos:
        return {}

    linhas_md = candidatos[-1].read_text(encoding="utf-8").splitlines()

    inicio = next(
        (i for i, linha in enumerate(linhas_md) if linha.startswith("| Operadora")),
        None,
    )
    if inicio is None:
        return {}

    cabecalho = [celula.strip() for celula in linhas_md[inicio].strip("|").split("|")]
    resultado: dict[str, dict] = {}

    for linha in linhas_md[inicio + 2:]:
        if not linha.startswith("|"):
            break
        celulas = [celula.strip() for celula in linha.strip("|").split("|")]
        if len(celulas) != len(cabecalho):
            continue
        registro = dict(zip(cabecalho, celulas))
        operadora = registro.pop("Operadora")
        resultado[operadora] = {
            "situacao": registro.pop("Situação", ""),
            "pulos": registro.pop("Pulos e erros", ""),
            "produzidos": registro,
        }

    return resultado


# ---------------------------------------------------------------------------
# Verificadores
# ---------------------------------------------------------------------------
def _verificar_algar(ambiente: Ambiente) -> tuple[bool, str]:
    operadora = "Algar"
    faltando = []

    if not ambiente.existe_na_agi(operadora, "*_EXT.xlsx"):
        faltando.append("EXT")
    if not ambiente.existe_na_agi(operadora, "*_INT.xlsx"):
        faltando.append("INT")
    if not ambiente.existe_na_agi(operadora, "CONT_PROC_MASCARA_*.xlsx"):
        faltando.append("CONT_PROC")

    pasta_cont = ambiente.pasta_contestacoes(operadora)
    if not (pasta_cont.is_dir() and any(pasta_cont.glob("*_EXP.xlsx"))):
        faltando.append("_EXP")
    cartas = list(pasta_cont.glob("CT - *.docx")) if pasta_cont.is_dir() else []
    if not cartas:
        faltando.append("carta")

    if faltando:
        return False, f"faltou: {', '.join(faltando)} — ver {ambiente.pasta_mes(operadora)}"

    registro = ambiente.linhas_relatorio.get(operadora, {})
    if registro.get("pulos", "-") not in ("-", ""):
        return False, f"gerou os cinco artefatos, mas o relatório registra pulo: {registro['pulos']}"

    return True, f"os cinco artefatos saíram, com {len(cartas)} carta(s) ({cartas[0].name})"


def _verificar_sem_expectativa(ambiente: Ambiente) -> tuple[bool, str]:
    operadora = "SemExpectativa"

    if not ambiente.existe_na_agi(operadora, "*_EXT.xlsx"):
        return False, "o EXT não saiu — ele não deveria depender da expectativa"

    saiu_demais = [
        nome
        for nome, existe in (
            ("INT", ambiente.existe_na_agi(operadora, "*_INT.xlsx")),
            ("CONT_PROC", ambiente.existe_na_agi(operadora, "CONT_PROC_MASCARA_*.xlsx")),
            (
                "_EXP",
                ambiente.pasta_contestacoes(operadora).is_dir()
                and any(ambiente.pasta_contestacoes(operadora).glob("*_EXP.xlsx")),
            ),
        )
        if existe
    ]
    if saiu_demais:
        return False, (
            f"{', '.join(saiu_demais)} saíram sem expectativa Vivo — sem o outro "
            f"lado da comparação, não há como confiar no valor contestado."
        )

    registro = ambiente.linhas_relatorio.get(operadora, {})
    pulos = registro.get("pulos", "")
    if "sem expectativa" not in pulos.lower():
        return False, (
            f"faltou registrar o pulo 'sem expectativa Vivo' no relatório da "
            f"execução (registrado: {pulos!r})."
        )

    return True, f"só o EXT saiu, com o pulo registrado: {pulos}"


def _verificar_sem_detraf(ambiente: Ambiente) -> tuple[bool, str]:
    operadora = "SemDetraf"
    pasta = ambiente.pasta_mes(operadora)

    if pasta.is_dir() and any(pasta.rglob("*.xlsx")):
        return False, f"algo foi gerado em [{pasta}] sem nenhum Detraf de entrada"

    registro = ambiente.linhas_relatorio.get(operadora, {})
    pulos = registro.get("pulos", "")
    if "sem detraf" not in pulos.lower():
        return False, (
            f"faltou registrar o pulo 'sem Detraf recebido' (registrado: {pulos!r})."
        )

    return True, f"nada gerado, com o pulo registrado: {pulos}"


def _verificar_sem_contestacao(ambiente: Ambiente) -> tuple[bool, str]:
    operadora = "SemContestacao"

    if not ambiente.existe_na_agi(operadora, "*_EXT.xlsx"):
        return False, "o EXT não saiu — ele sai em todos os cenários, contestado ou não"

    saiu_demais = [
        nome
        for nome, existe in (
            ("INT", ambiente.existe_na_agi(operadora, "*_INT.xlsx")),
            ("CONT_PROC", ambiente.existe_na_agi(operadora, "CONT_PROC_MASCARA_*.xlsx")),
        )
        if existe
    ]
    if saiu_demais:
        return False, (
            f"{', '.join(saiu_demais)} saíram com variação 0% — não havia nada a "
            f"contestar."
        )

    registro = ambiente.linhas_relatorio.get(operadora, {})
    pulos = registro.get("pulos", "-")
    if pulos not in ("-", ""):
        return False, (
            f"só o EXT deveria sair, mas SEM pulo — 'nada a contestar' não é "
            f"falta de insumo. Registrado: {pulos!r}."
        )

    return True, "só o EXT saiu, sem pulo — variação 0%, nada a contestar"


# ---------------------------------------------------------------------------
# Montagem da caixa de areia
# ---------------------------------------------------------------------------
def preparar(referencia: str) -> Ambiente:
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)

    operadoras = SANDBOX / "Operadoras"
    banco = SANDBOX / "banco.db"
    raiz_logs = SANDBOX / "logs"
    caminho_ct = SANDBOX / "CT" / referencia[:4]
    caminho_ct.mkdir(parents=True)

    if not BANCO_ESPELHO.is_file():
        raise SystemExit(
            f"O espelho do banco não existe em [{BANCO_ESPELHO}]. Gere-o com "
            f"`python espelhar_banco.py` antes de rodar este teste."
        )
    shutil.copy2(BANCO_ESPELHO, banco)
    _conferir_mapeamento_descritores(banco)
    _gravar_sinal_do_analista(banco, referencia)

    ambiente = Ambiente(
        referencia=referencia, operadoras=operadoras, banco=banco, raiz_logs=raiz_logs
    )

    # --- Algar: cenário rico, com sinal gravado -------------------------
    entrada_algar = ambiente.pasta_mes("Algar") / "Detrafs Recebidos"
    entrada_algar.mkdir(parents=True)
    escrever_csv(
        entrada_algar / "DETRAF_ALGAR.csv",
        [campos_detraf(referencia, r_bruto="100,00") for _ in range(3)],
    )
    enviados_algar = ambiente.pasta_mes("Algar") / "Detrafs Enviados"
    enviados_algar.mkdir(parents=True)
    # R$_Bruto bem menor: gera variação de 50%, folgada acima do limiar de 1%.
    escrever_csv(
        enviados_algar / "EXPECTATIVA_D.csv",
        [campos_detraf(referencia, r_bruto="50,00") for _ in range(3)],
    )
    ambiente.casos["Algar"] = Caso(
        "Algar", "Algar",
        "Detraf + expectativa divergentes, sinal COM retenção gravado",
        _verificar_algar,
    )

    # --- SemExpectativa: só o lado da operadora -------------------------
    entrada_sem_exp = ambiente.pasta_mes("SemExpectativa") / "Detrafs Recebidos"
    entrada_sem_exp.mkdir(parents=True)
    escrever_csv(
        entrada_sem_exp / "DETRAF_SEM_EXPECTATIVA.csv",
        [campos_detraf(referencia, r_bruto="80,00", credora="031")],
    )
    ambiente.casos["SemExpectativa"] = Caso(
        "SemExpectativa", "SemExpectativa",
        "Detraf sem nenhum arquivo de expectativa Vivo",
        _verificar_sem_expectativa,
    )

    # --- SemDetraf: pasta de entrada vazia ------------------------------
    (ambiente.pasta_mes("SemDetraf") / "Detrafs Recebidos").mkdir(parents=True)
    ambiente.casos["SemDetraf"] = Caso(
        "SemDetraf", "SemDetraf",
        "Pasta 'Detrafs Recebidos' existe e está vazia",
        _verificar_sem_detraf,
    )

    # --- SemContestacao: os dois lados iguais, variação 0% --------------
    entrada_sem_cont = ambiente.pasta_mes("SemContestacao") / "Detrafs Recebidos"
    entrada_sem_cont.mkdir(parents=True)
    escrever_csv(
        entrada_sem_cont / "DETRAF_SEM_CONTESTACAO.csv",
        [campos_detraf(referencia, r_bruto="60,00", credora="032")],
    )
    enviados_sem_cont = ambiente.pasta_mes("SemContestacao") / "Detrafs Enviados"
    enviados_sem_cont.mkdir(parents=True)
    escrever_csv(
        enviados_sem_cont / "EXPECTATIVA_D.csv",
        [campos_detraf(referencia, r_bruto="60,00", credora="032")],
    )
    ambiente.casos["SemContestacao"] = Caso(
        "SemContestacao", "SemContestacao",
        "Detraf e expectativa iguais — variação 0%",
        _verificar_sem_contestacao,
    )

    return ambiente


def _conferir_mapeamento_descritores(banco: Path) -> None:
    with sqlite3.connect(banco) as conexao:
        linha = conexao.execute(
            "SELECT remuneracao_fixa FROM tbl_detraf_mapeamento_descritores "
            "WHERE TRIM(final_descritor) = 'L' AND UPPER(TRIM(produto)) = 'DETRAF'"
        ).fetchone()

    if not linha or str(linha[0]).strip() != REMUNERACAO_ESPERADA:
        raise SystemExit(
            f"O espelho não mapeia o descritor final 'L' para "
            f"'{REMUNERACAO_ESPERADA}' (encontrado: {linha}). Este teste depende "
            f"desse mapeamento para o Contest reconhecer a remuneração — "
            f"regere o espelho com `python espelhar_banco.py`."
        )


def _gravar_sinal_do_analista(banco: Path, referencia: str) -> None:
    """
    Grava o "sinal do analista" que, em produção, vem do WebFat após a HU-11.

    Sem esta linha em `tbl_rpa_log_detraf_despesa_contestacao`, o RPA 3 trata a
    combinação como "ainda sem contestação" — o mesmo bypass que
    `docs/03-checklists/homologacao-rpa3.md` recomenda via `UPDATE` manual para
    homologar sem depender do WebFat.
    """
    with sqlite3.connect(banco) as conexao:
        conexao.execute(
            """
            INSERT INTO tbl_rpa_log_detraf_despesa_contestacao
                (eot_operadora, eot_tbra, referencia, trafego, remuneracoes,
                 tipo_contestacao)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (EOT_OPERADORA, EOT_VIVO, referencia, referencia, REMUNERACAO_ESPERADA,
             "COM retenção"),
        )
        conexao.commit()


# ---------------------------------------------------------------------------
# Execução do robô
# ---------------------------------------------------------------------------
def montar_ambiente_do_subprocesso(ambiente: Ambiente) -> dict[str, str]:
    import os

    variaveis = {
        "ENV": "dev",
        "CAMINHO_SQLITE": str(ambiente.banco),
        "CAMINHO_SQLITE_DEV": "",
        "CAMINHO_OPERADORAS": str(ambiente.operadoras),
        "CAMINHO_DETRAF_RECEBIDO": str(ambiente.operadoras),
        "DIRETORIO_SAIDA": str(ambiente.operadoras),
        "CAMINHO_CONTROLE_CT": str(SANDBOX / "CT"),
        "CT_NUMERO_INICIAL": "1",
        "RAIZ_LOGS": str(ambiente.raiz_logs),
        "DIRETORIO_HISTORICO_ARQUIVOS": str(SANDBOX / "historico"),
        # Kill-switches: `--etapa artefatos` já não toca em AGI nem Outlook,
        # mas ficam explícitos pelo mesmo motivo do script do RPA 1 — este
        # script escreve o ambiente inteiro, e um switch herdado da máquina
        # não é o que se quer descobrir depois.
        "PERMITIR_ENVIO_EMAIL": "false",
        "PERMITIR_UPLOAD_AGI": "false",
        "PERMITIR_ACESSO_AGI": "false",
        "PAUSA_ENTRE_ETAPAS": "false",
    }

    do_processo = dict(os.environ)
    for nome in list(do_processo):
        if any(nome == f"{base}_RPA3" for base in variaveis):
            del do_processo[nome]
    do_processo.update(variaveis)
    return do_processo


def executar_robo(ambiente: Ambiente, verboso: bool) -> tuple[int, str]:
    comando = [
        sys.executable,
        str(RAIZ / "rpa3_contestacao_agi_ec" / "main.py"),
        "--referencia", ambiente.referencia,
        "--operadoras", ",".join(ambiente.casos),
        "--etapa", "artefatos",
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


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------
def relatar(ambiente: Ambiente, codigo_do_robo: int) -> bool:
    resultados = []
    for caso in ambiente.casos.values():
        try:
            passou, detalhe = caso.verificar(ambiente)
        except Exception as erro:
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

    return not falhas and codigo_do_robo == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="testar_rpa3_artefatos.py",
        description=(
            "Teste de ponta a ponta da etapa 'artefatos' do RPA 3, em caixa de "
            "areia. Nunca chama --etapa carga/email/verificacao — nada abre o "
            "AGI nem toca no Outlook."
        ),
    )
    parser.add_argument(
        "--referencia", default=REFERENCIA_PADRAO, metavar="AAAAMM",
        help=f"Mês de tráfego a simular (default: {REFERENCIA_PADRAO}).",
    )
    parser.add_argument(
        "--verboso", action="store_true",
        help="Mostra a saída completa do robô, e não só o veredito dos casos.",
    )
    args = parser.parse_args(argv)

    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8", errors="replace")

    if not args.referencia.isdigit() or len(args.referencia) != 6:
        parser.error(f"'{args.referencia}' não é AAAAMM — ex.: {REFERENCIA_PADRAO}.")

    print(f"\n--- Preparando a caixa de areia em {SANDBOX} ---\n")
    ambiente = preparar(args.referencia)
    print(f"  {len(ambiente.casos)} operadora(s) sintética(s) montada(s), referência {args.referencia}\n")

    print("--- Executando o RPA 3 (só a etapa 'artefatos') ---\n")
    codigo, saida = executar_robo(ambiente, args.verboso)

    ambiente.linhas_relatorio = ler_ultimo_relatorio(ambiente.raiz_logs)
    if not ambiente.linhas_relatorio:
        print(
            "AVISO: não encontrei o relatório .md da execução — os casos que "
            "dependem dele vão falhar. Rode com --verboso para investigar.\n"
        )

    if codigo != 0 and not args.verboso:
        print("A execução terminou com código != 0. Saída do robô:\n")
        print(saida[-4000:])

    return 0 if relatar(ambiente, codigo) else 1


if __name__ == "__main__":
    raise SystemExit(main())
