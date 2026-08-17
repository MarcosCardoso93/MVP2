"""Etapa 1 do RPA 2 — traz a expectativa Vivo do SFTP do ClickHub.

Até 2026-08-10 os arquivos `_D` chegavam à pasta por fora do repositório: o
`FLUXO.md` dizia, no diagrama, `← ICT (outra demanda)`, e o checklist de acessos
registrava `CAMINHO_EXPECTATIVA_DETRAF` como **somente leitura**. Agora o robô os
baixa.

As regras vivem aqui — que período, qual arquivo, para qual pasta —, e são
funções puras, testáveis sem rede. O transporte está em
`comum/integracoes/sftp.py`.

## Como testar sem SFTP

Duas formas, e as duas rodam a etapa inteira:

- **`PERMITIR_DOWNLOAD_SFTP` desligado** (o padrão, e o que o `--dry-run` força):
  não conecta, e a etapa segue com o que já estiver na pasta. É exatamente como a
  expectativa chegava antes.
- **`--de-pasta CAMINHO`**: lê de um diretório local como se fosse o SFTP, com os
  mesmos filtros e o mesmo destino. Exercita a filtragem e o roteamento de pasta,
  que é onde mora a regra.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from comum.config import configuration
from comum.config.logger_config import logger
from comum.dominio.competencia import obter_competencia
from comum.dominio.expectativa import pasta_por_nome
from comum.integracoes.sftp import MAPA_PASTAS, SFTPError, SFTPService

# O mapa de pastas remotas mora em `comum.integracoes.sftp`: ele descreve a forma
# do servidor, e o `verificar_ambiente.py` precisa dele para conferir que todo
# destino está em `PASTAS_EXPECTATIVAS`. Aqui ficam as regras de negócio.

#: Marca dos arquivos que NÃO devem ser baixados.
#:
#: O `_L_` é o resumido; o robô quer o Detalhado. A regra veio do script e **não**
#: existe em `IGNORAR_ARQUIVOS` — aquela lista filtra o que o próprio robô
#: produziu (`_BK`, `_ERRO`, `_EXP`), e esta filtra o que o ClickHub oferece.
MARCA_RESUMIDO = "_L_"


@dataclass
class ResultadoCaptacao:
    """O que a etapa fez, para o diagnóstico e a parada entre etapas."""

    periodo: str = ""
    baixados: list[str] = field(default_factory=list)
    falhas: list[str] = field(default_factory=list)
    origem: str = "SFTP"

    def resumo(self) -> list[str]:
        linhas = [
            f"Origem:                   {self.origem}",
            f"Período procurado:        {self.periodo}",
            f"Arquivos baixados:        {len(self.baixados)}",
        ]
        if self.baixados:
            linhas += [f"  {nome}" for nome in sorted(self.baixados)]
        if self.falhas:
            linhas += ["", f"Falhas ({len(self.falhas)}):"]
            linhas += [f"  {falha}" for falha in self.falhas]
        return linhas


def eh_detalhado_do_periodo(nome: str, periodo: str) -> bool:
    """
    Se este arquivo remoto é o Detalhado do período procurado.

    Três condições, todas do script de origem:

    1. o período (`AAAAMM`) aparece no nome;
    2. o nome **não** contém `_L_` — esse é o resumido;
    3. o nome, sem extensão, **termina** em `_D`.

    ⚠️ A terceira é mais estrita que o `EXPECTATIVA_SUBSTRING` do `.env`, que é
    *substring* (`_D` em qualquer posição). São filtros de coisas diferentes:
    aquele decide o que o robô lê da pasta, este decide o que ele traz do
    ClickHub. Unificar os dois afrouxaria este aqui.
    """
    if periodo not in nome:
        return False
    if MARCA_RESUMIDO in nome:
        return False
    return Path(nome).stem.upper().endswith("_D")


class _OrigemEmDisco:
    """
    Um diretório local com a cara de um SFTP, para o `--de-pasta`.

    Serve a etapa inteira sem rede: mesma filtragem, mesmo roteamento, mesmo
    destino. Procura o nome da subpasta remota dentro do diretório dado e, se não
    achar, cai na raiz — assim tanto `Insumos/Expectativa/` (tudo junto) quanto
    uma cópia da árvore remota funcionam.
    """

    def __init__(self, raiz: Path):
        self.raiz = Path(raiz)

    def _pasta(self, caminho_remoto: str) -> Path:
        candidata = self.raiz / caminho_remoto.strip("/").split("/")[-1]
        return candidata if candidata.is_dir() else self.raiz

    def origens(self) -> list[tuple[str, str | None]]:
        """
        As origens a percorrer, e o destino de cada uma.

        Quando o diretório **espelha** a árvore remota, vale o mapa de sempre.
        Quando é **plano** — que é o caso de `Insumos/Expectativa/`, com tudo
        junto —, uma passada só, com o destino decidido pelo NOME de cada
        arquivo. Sem isso, todo arquivo casaria com as cinco origens e seria
        copiado quatro vezes, cada uma para uma pasta diferente e errada.
        """
        espelhada = [
            (remoto, destino)
            for remoto, destino in MAPA_PASTAS.items()
            if (self.raiz / remoto.strip("/").split("/")[-1]).is_dir()
        ]
        if espelhada:
            return espelhada

        logger.info(
            "[Expectativa] A origem é um diretório plano — o destino de cada "
            "arquivo sai do nome dele."
        )
        return [(str(self.raiz), None)]

    def conectar(self) -> None:
        if not self.raiz.is_dir():
            raise SFTPError(f"[--de-pasta] O diretório [{self.raiz}] não existe.")
        logger.info(f"[Expectativa] Origem simulada em disco: [{self.raiz}]")

    def fechar(self) -> None:
        return None

    def listar(self, caminho_remoto: str) -> list[str]:
        pasta = self._pasta(caminho_remoto)
        return [item.name for item in pasta.iterdir() if item.is_file()]

    def baixar(self, caminho_remoto: str, destino: Path) -> Path:
        origem = self._pasta(caminho_remoto.rsplit("/", 1)[0]) / Path(caminho_remoto).name
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)
        return destino


class CaptacaoExpectativaService:
    """Baixa os arquivos de expectativa do período para a árvore local."""

    def __init__(self, sftp=None, de_pasta: str | Path | None = None):
        """
        Args:
            sftp: Cliente já pronto — o teste passa um dublê. `None` constrói o
                real a partir da configuração, **na hora de usar**.
            de_pasta: Diretório local a usar como origem, no lugar do SFTP.
        """
        self._sftp = sftp
        self._de_pasta = Path(de_pasta) if de_pasta else None
        self.resultado = ResultadoCaptacao()

    # ------------------------------------------------------------------

    def executar(self, referencia: str | None = None) -> ResultadoCaptacao:
        """
        Traz o que houver do período. Nunca levanta por falha de origem.

        Uma pasta remota indisponível não pode impedir as outras quatro — são
        cinco origens independentes, e o script de referência já se comportava
        assim.
        """
        periodo = referencia or obter_competencia().competencia
        self.resultado = ResultadoCaptacao(periodo=periodo)

        origem = self._resolver_origem()
        if origem is None:
            return self.resultado

        logger.info(
            f"[Expectativa] Procurando os arquivos _D de {periodo} em "
            f"{len(MAPA_PASTAS)} pasta(s) de origem."
        )

        try:
            origem.conectar()
        except SFTPError as erro:
            logger.error(f"[Expectativa] {erro}")
            self.resultado.falhas.append(str(erro))
            return self.resultado

        try:
            for caminho_remoto, subpasta in self._origens_de(origem):
                self._trazer_pasta(origem, caminho_remoto, subpasta, periodo)
        finally:
            origem.fechar()

        if not self.resultado.baixados:
            logger.warning(
                f"[Expectativa] Nenhum arquivo _D de {periodo} foi trazido. A "
                f"validação vai seguir com o que já estiver na pasta — confira se "
                f"o período está certo antes de tratar como defeito."
            )

        return self.resultado

    # ------------------------------------------------------------------

    @staticmethod
    def _origens_de(origem) -> list[tuple[str, str | None]]:
        """As origens que esta origem oferece — o SFTP usa o mapa remoto."""
        if hasattr(origem, "origens"):
            return origem.origens()
        return list(MAPA_PASTAS.items())

    def _resolver_origem(self):
        """A origem a usar, ou `None` quando a etapa não deve buscar nada."""
        if self._de_pasta is not None:
            self.resultado.origem = f"disco [{self._de_pasta}]"
            return _OrigemEmDisco(self._de_pasta)

        if self._sftp is not None:
            return self._sftp

        # O kill-switch é conferido AQUI, antes de construir o cliente — assim o
        # `paramiko` nem chega a ser importado numa execução que não vai baixar.
        if not configuration.PERMITIR_DOWNLOAD_SFTP:
            logger.warning(
                "[MODO SEGURO] PERMITIR_DOWNLOAD_SFTP está desligado — nada foi "
                "baixado. A validação segue com o que já está em "
                f"[{configuration.CAMINHO_EXPECTATIVA_DETRAF}]."
            )
            self.resultado.origem = "nenhuma (PERMITIR_DOWNLOAD_SFTP desligado)"
            return None

        return SFTPService(
            host=configuration.SFTP_HOST,
            usuario=configuration.SFTP_USUARIO,
            senha=configuration.SFTP_SENHA,
            porta=configuration.SFTP_PORT,
        )

    def _trazer_pasta(
        self, origem, caminho_remoto: str, subpasta: str | None, periodo: str
    ):
        """
        Baixa o que casar numa pasta de origem. Falha aqui não sobe.

        `subpasta` em `None` significa "decida pelo nome do arquivo" — é o caso
        do `--de-pasta` sobre um diretório plano.
        """
        nomes = origem.listar(caminho_remoto)
        alvos = [nome for nome in nomes if eh_detalhado_do_periodo(nome, periodo)]

        logger.info(
            f"[Expectativa] {caminho_remoto} -> {subpasta or 'pelo nome'}: "
            f"{len(alvos)} de {len(nomes)} arquivo(s) casam com o filtro."
        )
        if not alvos:
            return

        raiz_destino = Path(configuration.CAMINHO_EXPECTATIVA_DETRAF)

        for nome in sorted(alvos):
            pasta = subpasta or pasta_por_nome(
                nome, list(configuration.PASTAS_EXPECTATIVAS)
            )
            if pasta is None:
                logger.error(
                    f"[Expectativa] Não sei em qual pasta [{nome}] entra — "
                    f"nenhuma de {list(configuration.PASTAS_EXPECTATIVAS)} aparece "
                    f"no nome. Não foi copiado."
                )
                self.resultado.falhas.append(f"{nome}: destino indefinido")
                continue

            destino = raiz_destino / pasta / nome
            try:
                origem.baixar(f"{caminho_remoto}/{nome}", destino)
            except Exception as erro:  # noqa: BLE001 - um arquivo não derruba os outros
                logger.error(f"[Expectativa] Falhou [{nome}]: {erro}")
                self.resultado.falhas.append(f"{pasta}/{nome}: {erro}")
                continue

            # Sobrescreve o que estiver lá: o ClickHub é a fonte de verdade, e
            # quem decide se o arquivo será reprocessado é o histórico, que
            # compara tamanho e data — não o nome.
            self.resultado.baixados.append(f"{pasta}/{nome}")
            logger.info(f"[Expectativa] Baixado: {pasta}/{nome}")
