"""Área de trabalho temporária: o robô escreve na cópia, nunca no insumo.

## O defeito que isto fecha

A validação de expectativa do RPA 2 sobrescreve o arquivo com as linhas que
passaram (``_validar_colunas_expectativa`` → ``salvar_dados(df_validas, arquivo)``).
Quando **tudo** reprova — e basta o banco estar com uma coluna fora do lugar para
isso acontecer —, o que sobra no disco é o cabeçalho. O insumo é destruído por um
problema que não tem nada a ver com ele, e em produção esse arquivo é o da rede,
não uma cópia que se refaz.

Aconteceu em 2026-08-10, na primeira execução ponta a ponta: os quatro arquivos
de expectativa foram reduzidos a uma linha cada, e foi preciso semeá-los de novo.

## Como funciona

O robô não trabalha mais sobre o insumo. Cada arquivo é copiado para
``{DIRETORIO_TEMP}/{aaaamm}/{pasta}-{marca}/`` e **toda** a escrita da etapa
acontece lá: a regravação das linhas válidas, o ``_ERRO`` de linha, o ``_BK``, o
``_RECUSADO.md`` e a renomeação para ``_EXP``. No fim, os artefatos são copiados
de volta para a pasta de origem.

O insumo continua exatamente como chegou. Se a etapa morrer no meio, ele
continua lá — e a área de trabalho fica no disco, com o estado parcial, que é
justamente o que se quer olhar depois de uma falha.

⚠️ **O que NÃO volta é a cópia de trabalho.** Promover um arquivo com o mesmo
nome do original seria refazer a sobrescrita que este módulo existe para
impedir. Só sobe o que tem nome diferente — que é, por construção, o que a etapa
produziu.

A área é preservada por mês de referência: ela é evidência de homologação, e
permite refazer um cenário sem semear de novo. Quem a limpa é o
``resetar_homologacao.py``.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Callable

from comum.config.logger_config import logger


class AreaDeTrabalho:
    """Cópias de trabalho de uma execução, e o caminho de volta para a origem."""

    def __init__(
        self,
        raiz: Path,
        referencia: str,
        destino_de: Callable[[Path], Path | None] | None = None,
    ):
        """
        Args:
            raiz: Raiz da área de trabalho (``DIRETORIO_TEMP``).
            referencia: Mês ``AAAAMM``, que separa as áreas entre si.
            destino_de: Dada a pasta de ORIGEM de um insumo, devolve para onde
                os artefatos dele devem ir. ``None`` (o default) entrega de
                volta na própria pasta de origem — que é o comportamento
                anterior a 2026-08-10, e o que os testes de unidade usam.
                O RPA 2 passa `estrutura_pastas.caminho_de_saida`, e é o que faz
                os artefatos aterrissarem em `DIRETORIO_SAIDA`.
        """
        self.raiz = Path(raiz) / referencia
        self._destino_de = destino_de
        #: cópia de trabalho -> insumo original.
        self._origem_por_copia: dict[Path, Path] = {}
        #: pasta de trabalho -> pasta de origem, para promover os artefatos.
        self._destino_por_pasta: dict[Path, Path] = {}

    @staticmethod
    def _marca(pasta: Path) -> str:
        """
        Sufixo curto e estável do caminho da pasta de origem.

        Duas operadoras podem ter arquivo de mesmo nome, e `Vivo` e `TLF` moram
        em pastas homônimas em árvores diferentes. Sem a marca, uma cópia
        sobrescreveria a outra dentro da área de trabalho — e o robô validaria o
        arquivo de outra operadora sem nada indicar.
        """
        return hashlib.sha1(str(pasta.resolve()).encode("utf-8")).hexdigest()[:6]

    def _pasta_de_trabalho(self, origem: Path) -> Path:
        pasta_origem = origem.parent
        destino = self.raiz / f"{pasta_origem.name}-{self._marca(pasta_origem)}"
        destino.mkdir(parents=True, exist_ok=True)
        self._destino_por_pasta[destino] = pasta_origem
        return destino

    def acolher(self, caminhos: list[Path]) -> list[Path]:
        """
        Copia cada insumo para a área e devolve os caminhos das cópias.

        O que não puder ser copiado sai da lista, com o motivo no log: seguir com
        o caminho original faria a etapa escrever no insumo — exatamente o que
        não pode acontecer.
        """
        copias: list[Path] = []

        for origem in caminhos:
            try:
                copia = self._pasta_de_trabalho(origem) / origem.name
                shutil.copy2(origem, copia)
            except OSError as erro:
                logger.error(
                    f"Não foi possível copiar [{origem.name}] para a área de "
                    f"trabalho: {erro}. O arquivo fica FORA desta execução — "
                    f"processá-lo na origem arriscaria o insumo."
                )
                continue

            self._origem_por_copia[copia.resolve()] = origem
            copias.append(copia)

        if copias:
            logger.info(
                f"Área de trabalho em [{self.raiz}]: {len(copias)} arquivo(s) "
                f"copiado(s). O insumo original não será tocado."
            )
        return copias

    def origem_de(self, copia: Path) -> Path:
        """O insumo de onde a cópia veio — ou a própria cópia, se não for uma."""
        return self._origem_por_copia.get(Path(copia).resolve(), Path(copia))

    def origens(self, copias) -> list[Path]:
        """`origem_de` para uma coleção, preservando a ordem de entrada."""
        return [self.origem_de(copia) for copia in copias]

    def _pasta_de_destino(self, pasta_origem: Path) -> Path | None:
        """
        Para onde vão os artefatos desta pasta de origem.

        Sem `destino_de`, é a própria pasta de origem. Com ele, um caminho que
        pode não existir — e `None` significa "não sei onde isto vai". Nesse
        caso o artefato **fica na área de trabalho**: entregá-lo num palpite o
        colocaria numa pasta que ninguém lê, o que é pior do que deixá-lo onde
        se sabe procurar.
        """
        if self._destino_de is None:
            return pasta_origem

        destino = self._destino_de(pasta_origem)
        if destino is None:
            logger.error(
                f"Não sei para onde entregar os artefatos de [{pasta_origem}]: "
                f"ela não está sob nenhuma das raízes conhecidas. Eles ficam em "
                f"[{self.raiz}] — nada foi perdido, mas ninguém vai lê-los."
            )
        return destino

    def promover(self) -> list[Path]:
        """
        Copia os artefatos produzidos de volta para as pastas de origem.

        Returns:
            Os caminhos gravados na origem.
        """
        nomes_de_trabalho = {
            copia.name for copia in self._origem_por_copia
        } | {origem.name for origem in self._origem_por_copia.values()}

        promovidos: list[Path] = []

        for pasta_trabalho, pasta_origem in self._destino_por_pasta.items():
            pasta_destino = self._pasta_de_destino(pasta_origem)
            if pasta_destino is None:
                continue

            for artefato in sorted(pasta_trabalho.iterdir()):
                if not artefato.is_file():
                    continue

                # A cópia de trabalho intacta não volta — ver o aviso no módulo.
                if artefato.name in nomes_de_trabalho:
                    continue

                destino = pasta_destino / artefato.name
                try:
                    pasta_destino.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(artefato, destino)
                except OSError as erro:
                    logger.error(
                        f"Não foi possível promover [{artefato.name}] para "
                        f"[{pasta_destino}]: {erro}. O arquivo continua na área "
                        f"de trabalho."
                    )
                    continue

                promovidos.append(destino)

        if promovidos:
            logger.info(
                f"{len(promovidos)} artefato(s) promovido(s) da área de trabalho "
                f"para as pastas de origem."
            )
        else:
            logger.info(
                "Nenhum artefato a promover — a etapa não produziu arquivo novo."
            )
        return promovidos
