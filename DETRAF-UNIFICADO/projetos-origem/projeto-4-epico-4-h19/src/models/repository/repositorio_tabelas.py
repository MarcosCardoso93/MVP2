from __future__ import annotations

from typing import Optional

import pandas as pd
from loguru import logger

from src.config.constantes_epico4 import (
    COLUNAS_ATUALIZADAS_DESPESA_CONTESTACAO,
    COLUNAS_CHAVE_DESPESA_CONTESTACAO,
)
from src.models.repository.repositorio_cache import RepositorioCache


class RepositorioTabelas:
    """
    Centraliza as consultas sobre as tabelas de referência carregadas em cache
    pelo :class:`RepositorioCache` (única camada que fala com o banco).

    Nota de arquitetura: diferente da referência do Épico 2, este módulo **não**
    instancia um objeto global no import (evita quebra de import quando o banco
    está indisponível — lição L-004). Instancie sob demanda no service/controller
    e, nos testes, garanta o SQLite de teste antes de instanciar.

    As consultas específicas do Épico 4 (sinal COM/SEM retenção, consolidação)
    serão adicionadas nas tarefas T-024+ conforme os contratos forem confirmados.
    """

    def __init__(self) -> None:
        """
        Inicializa acesso às tabelas em memória.
        """

        self.cache = RepositorioCache()

        self.tbl_anexo5_processado: pd.DataFrame = self.cache.obter_tabela(
            "tbl_anexo5_processado"
        )
        # Tarifa regulada — contexto de variação (AI/10 §1.4). Ainda sem consumidor no
        # Épico 4: a comparação com a tarifa é da HU-05 (Épico 2, fora de escopo).
        self.tbl_detraf_tarifas: pd.DataFrame = self.cache.obter_tabela(
            "tbl_detraf_tarifas"
        )
        self.tbl_mapeamento_descritores: pd.DataFrame = self.cache.obter_tabela(
            "tbl_detraf_mapeamento_descritores"
        )
        self.tbl_contestacao: pd.DataFrame = self.cache.obter_tabela(
            "tbl_rpa_log_detraf_despesa_contestacao"
        )

    @staticmethod
    def _tratar_eot(eot: str) -> str:
        """
        Normaliza o valor do EOT antes da pesquisa.

        Regras:
        - Remove espaços e sempre retorna string.
        - Remove qualquer parte decimal sem arredondar.
        - Se numérico e menor que 100, preenche com zeros à esquerda (3 dígitos).
        """

        eot = str(eot).strip()

        if "." in eot:
            eot = eot.split(".")[0]

        if eot.isdigit() and int(eot) < 100:
            return eot.zfill(3)

        return eot

    def validar_eot(self, eot: str) -> Optional[str]:
        """
        Procura o EOT na tabela ``tbl_anexo5_processado``.

        Args:
            eot: Código EOT a ser pesquisado.

        Returns:
            O ``Nome Fantasia`` correspondente, ou ``None`` se não encontrado.
        """

        eot_tratado: str = self._tratar_eot(eot)

        resultado: pd.DataFrame = self.tbl_anexo5_processado[
            self.tbl_anexo5_processado["EOT"].astype(str).str.strip() == eot_tratado
        ]

        if resultado.empty:
            logger.info(f"EOT não encontrado [{eot_tratado}]")
            return None

        return resultado.iloc[0]["Nome Fantasia"]

    def obter_endereco_por_eot(self, eot: str) -> Optional[str]:
        """
        Procura o endereço de correspondência da operadora na tabela ``tbl_anexo5_processado``.

        Coluna confirmada pelo usuário (2026-07-23): **"Endereço de Correspondência"**.
        Usada no cabeçalho da carta de contestação (HU-14, T-082 — campo "A:").

        Args:
            eot: Código EOT da operadora.

        Returns:
            O endereço correspondente, ou ``None`` se o EOT não for encontrado.
        """

        eot_tratado: str = self._tratar_eot(eot)

        resultado: pd.DataFrame = self.tbl_anexo5_processado[
            self.tbl_anexo5_processado["EOT"].astype(str).str.strip() == eot_tratado
        ]

        if resultado.empty:
            logger.info(f"EOT não encontrado para busca de endereço [{eot_tratado}]")
            return None

        return resultado.iloc[0]["Endereço de Correspondência"]

    def _filtrar_contestacao_por_chave(
        self,
        eot_operadora: str,
        eot_tbra: str,
        referencia: str,
        trafego: str,
        remuneracao: str,
    ) -> pd.DataFrame:
        """
        Seleciona em ``tbl_contestacao`` as linhas da chave de negócio (AI/10 §1.3).

        Chave: ``eot_operadora`` × ``eot_tbra`` × ``referencia`` × ``trafego`` ×
        ``remuneracao``. Os EOTs são comparados **normalizados** dos dois lados
        (:meth:`_tratar_eot`), pois o Detraf e o banco divergem em zero-padding e
        parte decimal. Ponto único de verdade da chave: usado tanto pela leitura do
        sinal (:meth:`obter_tipo_contestacao`) quanto pelas escritas (D-19/D-20).
        """

        eot_operadora_tratado = self._tratar_eot(eot_operadora)
        eot_tbra_tratado = self._tratar_eot(eot_tbra)

        tabela = self.tbl_contestacao
        filtro = (
            (tabela["eot_operadora"].astype(str).apply(self._tratar_eot) == eot_operadora_tratado)
            & (tabela["eot_tbra"].astype(str).apply(self._tratar_eot) == eot_tbra_tratado)
            & (tabela["referencia"].astype(str).str.strip() == str(referencia).strip())
            & (tabela["trafego"].astype(str).str.strip() == str(trafego).strip())
            & (tabela["remuneracao"].astype(str).str.strip() == str(remuneracao).strip())
        )

        return tabela[filtro]

    def obter_tipo_contestacao(
        self,
        eot_operadora: str,
        eot_tbra: str,
        referencia: str,
        trafego: str,
        remuneracao: str,
    ) -> Optional[str]:
        """
        Consulta o sinal COM/SEM retenção (decisão do analista, T-024/D-6).

        Fonte: ``tbl_rpa_log_detraf_despesa_contestacao`` (schema base confirmado em
        ``DOCS/Outros arquivos auxiliares/Tabelas para o RPA alimentar o Webfat -
        despesa.xlsx``, aba "Contestação", **mais a coluna ``remuneracao``** — decisão
        do usuário, 2026-07-28: o sinal pode variar por remuneração dentro do mesmo par
        de EOT, então a chave de busca precisa incluí-la; ver D-16 revisada). O sinal é
        a coluna ``tipo_contestacao`` (``"com retenção"`` / ``"sem retenção"``), gravada
        pelo Webfat após ação do analista (HU-11).

        Args:
            eot_operadora: EOT credora (coluna ``eot_operadora``).
            eot_tbra: EOT devedora / Vivo (coluna ``eot_tbra``).
            referencia: Mês de referência do Detraf (``AAAAMM``).
            trafego: Mês de tráfego contestado (``AAAAMM``).
            remuneracao: Remuneração resolvida pelo descritor (D-5) — parte da chave.

        Returns:
            O texto de ``tipo_contestacao`` (ex.: ``"com retenção"``), ou ``None`` se
            não houver sinalização para a combinação (ainda **sem contestação**).
        """

        resultado = self._filtrar_contestacao_por_chave(
            eot_operadora=eot_operadora,
            eot_tbra=eot_tbra,
            referencia=referencia,
            trafego=trafego,
            remuneracao=remuneracao,
        )

        if resultado.empty:
            eot_operadora_tratado = self._tratar_eot(eot_operadora)
            eot_tbra_tratado = self._tratar_eot(eot_tbra)
            logger.info(
                f"Sinal de contestação não encontrado para "
                f"[operadora={eot_operadora_tratado}, tbra={eot_tbra_tratado}, "
                f"referencia={referencia}, trafego={trafego}, remuneracao={remuneracao}] "
                f"— tratado como sem contestação."
            )
            return None

        return resultado.iloc[0]["tipo_contestacao"]

    def _atualizar_contestacao_em_lote(
        self, linhas: pd.DataFrame, colunas_atualizadas: list[str], rotulo: str
    ) -> dict:
        """
        Aplica um lote de ``UPDATE`` em ``tbl_rpa_log_detraf_despesa_contestacao``.

        A linha alvo é localizada pela chave de negócio em memória
        (:meth:`_filtrar_contestacao_por_chave`, que normaliza os EOTs) e o ``UPDATE``
        vai por ``id``, garantindo que a semântica de casamento seja **idêntica** à da
        leitura do sinal e que a SQL use a chave primária.

        Chave ausente **não aborta o lote** (D-20): vira WARNING e entra no resumo — a
        linha-base é inserida pelo Épico 3, fora deste projeto (bloqueio B-D20).

        Args:
            linhas: Chave (``COLUNAS_CHAVE_DESPESA_CONTESTACAO``) + colunas a atualizar.
            colunas_atualizadas: Subconjunto de colunas de ``linhas`` a gravar.
            rotulo: Prefixo de log identificando a HU chamadora.

        Returns:
            ``{"atualizadas": int, "ausentes": list[dict]}`` — ``ausentes`` lista as
            chaves que não casaram com nenhuma linha do banco.
        """

        tabela = "tbl_rpa_log_detraf_despesa_contestacao"
        atualizadas: int = 0
        ausentes: list[dict] = []

        if linhas is None or linhas.empty:
            logger.info(f"{rotulo} Nada a atualizar (lote vazio).")
            return {"atualizadas": 0, "ausentes": []}

        for linha in linhas.to_dict(orient="records"):

            chave = {
                coluna: linha[coluna] for coluna in COLUNAS_CHAVE_DESPESA_CONTESTACAO
            }

            alvos = self._filtrar_contestacao_por_chave(**chave)

            if alvos.empty:
                logger.warning(
                    f"{rotulo} Chave sem linha correspondente no banco {chave} — "
                    f"ignorada (a linha-base é inserida pelo Épico 3, B-D20)."
                )
                ausentes.append(chave)
                continue

            valores = {coluna: linha[coluna] for coluna in colunas_atualizadas}

            for id_linha in alvos["id"].tolist():
                atualizadas += self.cache.atualizar_dados(
                    nome_tabela=tabela,
                    valores=valores,
                    chave={"id": id_linha},
                    sincronizar_cache=False,
                )

        # Uma única releitura ao final do lote (em vez de um SELECT * por linha).
        self.cache.recarregar_cache_local(nome_tabela=tabela)
        self.tbl_contestacao = self.cache.obter_tabela(tabela)

        logger.info(
            f"{rotulo} {atualizadas} linha(s) atualizada(s), "
            f"{len(ausentes)} chave(s) ausente(s)."
        )
        return {"atualizadas": atualizadas, "ausentes": ausentes}

    def atualizar_despesa_contestacao(self, linhas: pd.DataFrame) -> dict:
        """
        Atualiza a despesa da contestação (HU-19) em
        ``tbl_rpa_log_detraf_despesa_contestacao``.

        **D-20 (2026-07-30, adequação à V2 pág. 38):** a escrita da HU-19 é um
        ``UPDATE`` dos seis campos de despesa da operadora, não mais um ``INSERT`` da
        linha inteira (D-16). A linha-base é inserida pelo Épico 3 (V2 pág. 19), fora
        do escopo deste projeto.

        Args:
            linhas: Saída de
                :func:`src.services.encontro_contas.preparar_atualizacoes_despesa_contestacao`.

        Returns:
            Resumo do lote: ``{"atualizadas": int, "ausentes": list[dict]}``.
        """

        return self._atualizar_contestacao_em_lote(
            linhas=linhas,
            colunas_atualizadas=COLUNAS_ATUALIZADAS_DESPESA_CONTESTACAO,
            rotulo="[HU-19 Despesa Contestação]",
        )

    def atualizar_tipo_contestacao(self, linhas: pd.DataFrame) -> dict:
        """
        Regrava ``tipo_contestacao`` após a geração do CONT_PROC (HU-16).

        **D-19 (2026-07-30, adequação à V2 pág. 34):** *"O robô atualiza o campo
        'tipo_contestacao' da tabela do banco webfat – 'tbl_rpa_log_detraf_despesa_
        contestacao'"*. Semântica definida com o usuário: **eco do sinal aplicado** — o
        robô regrava, nas linhas efetivamente contestadas, o mesmo valor que usou para
        montar o CONT_PROC, confirmando no Webfat o que foi para o AGI.

        Args:
            linhas: Saída de
                :func:`src.services.geracao_cont_proc.selecionar_linhas_contestadas`
                — chave + coluna ``tipo_contestacao``.

        Returns:
            Resumo do lote: ``{"atualizadas": int, "ausentes": list[dict]}``.
        """

        return self._atualizar_contestacao_em_lote(
            linhas=linhas,
            colunas_atualizadas=["tipo_contestacao"],
            rotulo="[HU-16 Writeback tipo_contestacao]",
        )

    def obter_mapa_descritores(self) -> pd.DataFrame:
        """
        Retorna a relação descritor → remuneração (D-21).

        Fonte: ``tbl_detraf_mapeamento_descritores`` do banco Webfat (V2 pág. 7). Antes
        de 2026-07-30 esta relação vinha de uma planilha/CSV
        (``Mapeamento_Descritores.xlsx``); o CSV em ``tests/fixtures`` passou a ser
        apenas o seed do SQLite de teste.

        Returns:
            DataFrame com as colunas ``id``, ``final_descritor``, ``remuneracao_fixa``,
            ``observacao`` e ``produto`` — insumo de
            :func:`src.services.mapa_remuneracao.construir_indice_remuneracao`.
        """

        return self.tbl_mapeamento_descritores
