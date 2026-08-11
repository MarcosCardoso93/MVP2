"""Serviço da HU-20 — verificação do Relatório de Receitas e Despesas.

Origem: `projeto-6-h20-h21/H20/src/services/AGI/Verificacao_Relatorio.py`. Ver
`trabalho/inventarios/inventario-projeto-6.md`.

O que a V2 pede (seção *Geração do Relatório Receitas e Despesas*):

    ¶690 — "Este relatório é gerado para conferir os valores carregados no AGI e
            no EC."
    ¶691 — "O robô entra no AGI e acessa Relatórios >> Detraf >> Receitas e
            Despesas."
    ¶696 — "Após o resultado, o robô filtra pela Natureza 'D' e pelo nome da
            operadora."
    ¶698 — "O robô sumariza a coluna Vlr. Bruto."
    ¶701 — "Compara com os valores totalizados no EC no Subtotal despesa (célula
            O87). Repete essa verificação para todas as operadoras."
    ¶702 — "Comparar colunas CBS, IBS MUNICIPAL E IBS ESTADUAL."

## A V2 questionava se esta HU deveria existir — e a resposta veio

    ¶706 — "Esse processo trata-se de uma **dupla checagem**, conferir com o
            solicitante se esse processo vale a pena ou não ser mantido."

Esse parágrafo é **acréscimo da V2** — não existe no bloco antigo. **O GP/dev
confirmou em 2026-08-05 que a HU-20 fica no escopo**, e a Q7 foi fechada.

O `PERMITIR_ACESSO_AGI` continua, com outra justificativa: esta HU **abre o AGI e
faz login em produção**, e não existe ambiente de teste (Q20). É proteção de
ambiente, não dúvida de escopo — e é o que permite rodar a conferência sobre um
relatório já baixado, sem tocar no aplicativo.

## O que mudou na migração

- **O Encontro de Contas vem do banco.** O Projeto 6 lia um `.xlsx` pela célula
  fixa `O87`, achando a aba por substring do nome da operadora. Ver
  `repositorio_tabelas.obter_subtotal_despesa_por_operadora`;
- **CBS, IBS Municipal e IBS Estadual entram no relatório.** O original somava só
  `Vlr. Bruto` — uma tupla de um elemento —, mas o CSV que veio no próprio pacote
  já traz as três colunas novas. Ver `_COLUNAS_VALOR` e a ressalva abaixo;
- **O kill-switch passou a existir de verdade.** O Projeto 6 declarava
  `PERMITIR_ACAO_AGI` e nunca o lia;
- `print()` → `logger`.

## ⚠️ As três colunas de imposto ainda não têm contra-parte no EC

A V2 manda compará-las, mas `tbl_rpa_log_detraf_despesa_contestacao` só tem
`vb_operadora` — não há coluna de CBS nem de IBS. Então elas são **somadas e
reportadas**, e a comparação segue só sobre o valor bruto.

Isso não é omissão: é o limite do dado que existe — e não corre: a V2 (¶367) diz
que os impostos são *"apenas como informativo nesse primeiro ano, a partir de 2027
será feito o devido recolhimento"*.

**Desde 2026-08-06 elas são registradas no log todo mês** (ver
`_registrar_totais_de_imposto`), mesmo sem divergência. Antes disso a soma só
existia quando havia inconsistência, e um mês limpo não deixava rastro nenhum —
em 2027 a pergunta "quanto foi de CBS em julho de 2026?" ficaria sem resposta.

Quando a contra-parte no EC existir, acrescentar a comparação é incluir as colunas no
`_comparar` — a soma já está pronta.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from comum.config import configuration
from comum.config.logger_config import logger
from comum.dados.repositorio_tabelas import RepositorioTabelas
from comum.utils.decoradores import log_execucao

#: Nome da coluna de operadora no export do AGI. A grafia é a do relatório —
#: espaço antes do ponto incluído.
COL_OPERADORA = "Grp. Oper .Prest"

#: Coluna que separa despesa de receita. A HU-20 é só despesa.
COL_NATUREZA = "Natureza"

#: Colunas de valor somadas por operadora.
#:
#: As três de imposto vieram do export real do AGI, que hoje tem 22 colunas. O
#: `README.md` do Projeto 6 afirmava que as colunas eram "idênticas às usadas no
#: exemplo de Receita" e listava 17 — **contrariado pelo arquivo entregue no
#: próprio pacote**.
COL_VALOR_BRUTO = "Vlr. Bruto"
COL_CBS = "Vlr. CBS"
COL_IBS_ESTADUAL = "Vlr. IBS Estadual"
COL_IBS_MUNICIPAL = "Vlr. IBS Municipal"

_COLUNAS_VALOR = (COL_VALOR_BRUTO, COL_CBS, COL_IBS_ESTADUAL, COL_IBS_MUNICIPAL)

#: Nome do arquivo baixado do AGI.
NOME_RELATORIO = "remessa_baixada.csv"


class RelatorioAgiIndisponivel(RuntimeError):
    """Não há relatório do AGI para verificar."""


def _para_numero(serie: pd.Series) -> pd.Series:
    """
    Converte a coluna de valor do AGI, que vem no formato brasileiro.

    O export traz ``"1.234,56"`` — ponto de milhar e vírgula decimal. Remove o
    ponto **antes** de trocar a vírgula; a ordem importa.
    """
    return pd.to_numeric(
        serie.astype(str)
        .str.strip()
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce",
    )


def carregar_relatorio(caminho: Path) -> pd.DataFrame:
    """
    Lê o CSV exportado do AGI e devolve **só as linhas de despesa**.

    Raises:
        RelatorioAgiIndisponivel: Se o arquivo não existir ou não tiver as colunas
            esperadas. Falhar aqui é melhor do que comparar contra um DataFrame
            vazio e concluir que está tudo certo.
    """

    caminho = Path(caminho)
    if not caminho.is_file():
        raise RelatorioAgiIndisponivel(
            f"Relatório do AGI não encontrado em [{caminho}]. Com "
            f"PERMITIR_ACESSO_AGI desligado, é preciso baixá-lo antes."
        )

    df = pd.read_csv(caminho, sep=";", encoding="utf-8")

    faltando = [
        coluna
        for coluna in (COL_OPERADORA, COL_NATUREZA, COL_VALOR_BRUTO)
        if coluna not in df.columns
    ]
    if faltando:
        raise RelatorioAgiIndisponivel(
            f"O relatório em [{caminho.name}] não tem a(s) coluna(s) "
            f"{faltando}. O layout do export do AGI mudou?"
        )

    despesa = df[df[COL_NATUREZA].astype(str).str.strip().str.upper() == "D"].copy()

    ausentes_imposto = [c for c in _COLUNAS_VALOR[1:] if c not in despesa.columns]
    if ausentes_imposto:
        logger.warning(
            f"[HU-20] O relatório não traz {ausentes_imposto} — a V2 (¶702) manda "
            f"comparar CBS e IBS. Export antigo do AGI?"
        )

    logger.info(
        f"[HU-20] Relatório lido: {len(df)} linha(s), {len(despesa)} de despesa."
    )
    return despesa


def somar_por_operadora(df_despesa: pd.DataFrame) -> pd.DataFrame:
    """
    Soma os valores por operadora — o *"sumariza a coluna Vlr. Bruto"* do ¶698.

    O agrupamento cobre o *"repete essa verificação para todas as operadoras"* do
    ¶701 sem precisar de laço.
    """

    if df_despesa.empty:
        return pd.DataFrame(columns=["operadora", *_COLUNAS_VALOR])

    trabalho = df_despesa.copy()
    trabalho["operadora"] = (
        trabalho[COL_OPERADORA].astype(str).str.strip().str.upper()
    )

    presentes = [c for c in _COLUNAS_VALOR if c in trabalho.columns]
    for coluna in presentes:
        trabalho[coluna] = _para_numero(trabalho[coluna]).fillna(0.0)

    return trabalho.groupby("operadora", as_index=False)[presentes].sum()


def comparar_com_encontro_de_contas(
    somas_agi: pd.DataFrame,
    subtotais_ec: dict[str, float],
    tolerancia: float | None = None,
) -> pd.DataFrame:
    """
    Compara o somatório do AGI com o subtotal de despesa do Encontro de Contas.

    **Sinal:** o EC guarda a despesa como valor negativo e o AGI a soma como
    positivo — a comparação é entre os módulos.

    **Operadora sem EC conta como divergente**, não como zero. É a escolha do
    Projeto 6 e é a certa: uma operadora que aparece no AGI e não no EC é
    exatamente o que esta HU existe para pegar.

    Args:
        somas_agi: Saída de :func:`somar_por_operadora`.
        subtotais_ec: Saída de
            `RepositorioTabelas.obter_subtotal_despesa_por_operadora`.
        tolerancia: Diferença em reais aceita. Default: `TOLERANCIA_VERIFICACAO`.
    """

    limiar = (
        tolerancia if tolerancia is not None else configuration.TOLERANCIA_VERIFICACAO
    )

    if somas_agi.empty:
        return pd.DataFrame(
            columns=["operadora", "vb_agi", "vb_ec", "diferenca", "inconsistente"]
        )

    comparado = somas_agi.copy()
    comparado["vb_agi"] = comparado[COL_VALOR_BRUTO]
    # `to_numeric` com `coerce`: a operadora ausente do EC vira NaN, não `None`.
    # Com `None` a coluna fica com dtype `object` e o `.abs()` abaixo estoura com
    # "bad operand type for abs()" — bug real, apanhado no Projeto 6.
    comparado["vb_ec"] = pd.to_numeric(
        comparado["operadora"].map(subtotais_ec), errors="coerce"
    )

    comparado["diferenca"] = (
        comparado["vb_agi"].abs() - comparado["vb_ec"].abs()
    ).round(2)
    comparado["inconsistente"] = comparado["diferenca"].isna() | (
        comparado["diferenca"].abs() > limiar
    )

    return comparado


def gravar_inconsistencias(
    comparado: pd.DataFrame,
    referencia: str,
    diretorio: Path | None = None,
) -> Optional[Path]:
    """
    Grava o `.xlsx` das operadoras divergentes, na pasta comum de logs.

    Decisão de 2026-08-05: o relatório é um arquivo, junto do log. É a mesma
    natureza — registro do que o robô viu, para alguém conferir depois — e herda a
    organização por host e a retenção que já existem.

    O carimbo de tempo no nome evita que uma reexecução apague a evidência da
    anterior.

    Returns:
        Caminho do arquivo, ou `None` quando não há divergência.
    """

    if comparado.empty:
        return None

    _registrar_totais_de_imposto(comparado, referencia)

    divergentes = comparado[comparado["inconsistente"]]
    if divergentes.empty:
        logger.info(
            f"[HU-20] {len(comparado)} operadora(s) conferida(s) em {referencia}: "
            f"nenhuma divergência entre o AGI e o Encontro de Contas."
        )
        return None

    pasta = Path(diretorio or configuration.DIRETORIO_INCONSISTENCIAS)
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / (
        f"inconsistencias_{referencia}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    )

    divergentes.to_excel(caminho, index=False)

    for linha in divergentes.itertuples():
        if pd.isna(linha.diferenca):
            logger.warning(
                f"[HU-20] {linha.operadora}: presente no AGI "
                f"(R$ {linha.vb_agi:,.2f}) e **ausente no Encontro de Contas**."
            )
        else:
            logger.warning(
                f"[HU-20] {linha.operadora}: AGI R$ {linha.vb_agi:,.2f} × "
                f"EC R$ {linha.vb_ec:,.2f} — diferença de R$ {linha.diferenca:,.2f}."
            )

    logger.error(
        f"[HU-20] {len(divergentes)} de {len(comparado)} operadora(s) divergente(s) "
        f"em {referencia}. Detalhe em [{caminho}]."
    )
    return caminho


def _registrar_totais_de_imposto(comparado: pd.DataFrame, referencia: str) -> None:
    """
    Registra no log os totais de CBS e IBS do mês (decisão de 2026-08-06, Q6).

    ## Por que só registrar, e não comparar

    A V2 (¶702) manda comparar as três colunas, mas
    ``tbl_rpa_log_detraf_despesa_contestacao`` **não tem coluna de imposto** —
    não há contra o que comparar. Não é omissão do código: é o limite do dado.

    E não corre: a própria V2 (¶367) diz que os impostos são *"apenas como
    informativo nesse primeiro ano, a partir de 2027 será feito o devido
    recolhimento"*. Conferir só o valor bruto está adequado ao ano corrente.

    ## Por que registrar mesmo assim

    Porque até esta mudança as somas **só existiam quando havia divergência**:
    elas iam junto no `.xlsx` de inconsistências, e num mês sem divergência
    nenhum arquivo era gravado. Em 2027, quando o recolhimento começar, a
    pergunta "quanto foi de CBS em julho de 2026?" não teria resposta.

    Uma linha de log por mês custa nada e cria a série histórica. Quando a
    contra-parte no EC existir, o que muda é acrescentar a comparação — o dado
    já vai estar sendo lido.
    """

    presentes = [c for c in _COLUNAS_VALOR[1:] if c in comparado.columns]
    if not presentes:
        return

    totais = {coluna: float(comparado[coluna].sum()) for coluna in presentes}
    if not any(totais.values()):
        return

    resumo = " | ".join(f"{nome}: R$ {valor:,.2f}" for nome, valor in totais.items())
    logger.info(
        f"[HU-20] Impostos somados do relatório do AGI em {referencia} — {resumo}. "
        f"**Informativo**: o Encontro de Contas não tem coluna de imposto, então "
        f"não há comparação (pendência Q6). A V2 (¶367) trata os impostos como "
        f"informativos até 2027."
    )


class VerificacaoRelatorio:
    """Confere o relatório do AGI contra o Encontro de Contas (HU-20)."""

    def __init__(
        self,
        agi=None,
        repositorio: RepositorioTabelas | None = None,
    ) -> None:
        """
        Args:
            agi: `AGI` já construído. **Injetado**, não criado aqui: o construtor
                real resolve o executável, o que tornaria a HU intestável sem a VM.
            repositorio: Acesso ao Encontro de Contas no banco.
        """
        self._agi = agi
        self.repositorio = repositorio or RepositorioTabelas()

    @property
    def agi(self):
        if self._agi is None:
            # Import tardio: `agi.py` traz `pyautogui`, que só faz sentido na
            # máquina que opera o AGI.
            from comum.integracoes.agi import AGI

            self._agi = AGI()
        return self._agi

    @log_execucao
    def executar(
        self,
        referencia: str,
        caminho_relatorio: Path | None = None,
        diretorio_inconsistencias: Path | None = None,
    ) -> Optional[Path]:
        """
        Baixa o relatório (se permitido), compara com o EC e grava as divergências.

        Com `PERMITIR_ACESSO_AGI` desligado — o default — **o AGI não é aberto** e
        a verificação roda sobre um relatório já baixado. Se não houver nenhum, a
        execução falha dizendo isso, em vez de concluir que está tudo certo.

        Returns:
            Caminho do `.xlsx` de divergências, ou `None` se não houver nenhuma.
        """

        caminho = Path(
            caminho_relatorio
            or (configuration.DIRETORIO_RELATORIO_AGI / NOME_RELATORIO)
        )

        if configuration.PERMITIR_ACESSO_AGI:
            self._baixar(caminho)
        else:
            logger.info(
                f"[MODO SEGURO] PERMITIR_ACESSO_AGI=false — o AGI não será aberto. "
                f"A verificação usa o relatório já em [{caminho}]."
            )

        despesa = carregar_relatorio(caminho)
        somas = somar_por_operadora(despesa)
        subtotais = self.repositorio.obter_subtotal_despesa_por_operadora(referencia)

        comparado = comparar_com_encontro_de_contas(somas, subtotais)
        return gravar_inconsistencias(
            comparado, referencia, diretorio_inconsistencias
        )

    def _baixar(self, destino: Path) -> None:
        """Abre o AGI, faz login e exporta o relatório para `destino`."""
        destino.parent.mkdir(parents=True, exist_ok=True)

        self.agi.inicializar()
        try:
            self.agi.acessar_ambiente()
            self.agi.login()
            self.agi.baixar_remessa(destino)
        finally:
            self.agi.fechar()
