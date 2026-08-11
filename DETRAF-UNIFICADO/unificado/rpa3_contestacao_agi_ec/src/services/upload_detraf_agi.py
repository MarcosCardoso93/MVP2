"""Serviço da HU-17 — upload dos arquivos EXT/INT no AGI (Detraf > Importar Dados).

Origem: `projeto-7-epico-5-carga-agi/src/services/AGI/Upload_Detraf_EXT_INT.py`,
adaptado lá do `Upload_DI_DE.py` do `RPA_DETRAF_RECEITA`. Ver
`trabalho/inventarios/inventario-projeto-7.md` §4.

Sobe no AGI os arquivos que a HU-12 (`geracao_ext.py`) e a HU-13
(`geracao_int.py`) deixaram na subpasta ``AGI`` de cada operadora, um de cada
vez, EXT antes de INT (V2, parágrafo 313).

## O que mudou na migração

- as pastas planas ``data/AGI/EXT`` e ``data/AGI/INT`` deram lugar a
  `estrutura_pastas.caminho_agi`, que é onde a HU-12/13 de fato grava. Sem isso,
  não havia como saber de que operadora era cada arquivo — e a regra de negócio
  que falta é justamente por operadora;
- `print()` → `logger`;
- a evidência de sucesso, que era só um TODO com um `print`, passou a de fato
  tirar o screenshot. ⚠️ Não é requisito da V2 — ver `capturar_evidencia_sucesso`.

## Quem aplica a regra de cenário — e por que não é aqui

Registrei antes que "falta a regra: EXT sempre, INT só COM retenção". Relendo a
V2, ela é explícita sobre por que a regra aqui é simples (seção *Carga no AGI*):

    "O robô seleciona os arquivos final EXT e INT (um de cada vez) e clica em
    Abrir. O arquivo final INT existirá apenas para o caso de contestação com
    retenção. **Para os cenários sem contestação e contestação sem retenção, o
    arquivo INT não chegou nem a ser criado**, então o robô sobe apenas no AGI o
    arquivo final EXT."

Ou seja: quem aplica a regra é a **HU-13** (`geracao_int.py`, que só gera COM
retenção). Subir o que está na pasta **é** o comportamento descrito.

O que sobra é uma guarda contra **sobra de execução anterior**: um INT de um mês
em que houve retenção, ainda na pasta quando o cenário mudou. Por isso
`montar_lista_upload` aceita `desde`.

⚠️ A **ordem EXT antes de INT** é escolha nossa. A V2 só diz "um de cada vez";
a ordem vem da V1 (*"Um arquivo por vez, aguardando confirmação antes de
prosseguir"*), e é a que faz sentido — o EXT existe em todo cenário.

## Sobre `detectar_linhas_vermelhas`

Ela **não é código morto, e não deve ser ligada aqui** (decisão de 2026-08-10).
É uma função do processo de **Receita**, de onde este módulo veio, e ficou junto
por herança da migração. A conferência pós-upload da Despesa, se vier a existir,
é outra coisa e será decidida à parte.

Quem for "consertar o código que ninguém chama": não chame. A confirmação de
sucesso do upload continua sendo uma lacuna conhecida da HU-17, registrada em
`docs/04-relatorios/duvidas-pendentes.md`, e a resposta para ela não é esta
função.
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pyautogui

from comum.arquivos import estrutura_pastas as ep
from comum.config import configuration
from comum.config import constantes as const
from comum.config.logger_config import logger
from comum.utils.decoradores import log_execucao
from comum.integracoes.agi import AGI, AGIError, RAIZ_IMAGENS

_IMAGENS = RAIZ_IMAGENS / "AGI_Upload_Detraf"

img_bnt_detraf = str(_IMAGENS / "bnt_detraf.png")
img_bnt_submenu_importar_dados = str(_IMAGENS / "bnt_submenu_importar_dados.png")
img_bnt_upload = str(_IMAGENS / "bnt_upload.png")
img_tab_regs_erro = str(_IMAGENS / "tab_regs_Erro.png")
img_bnt_export_erro = str(_IMAGENS / "bnt_export_erro.png")
img_bnt_voltar = str(_IMAGENS / "bnt_voltar.png")

#: Área da grade de resultados na tela, em pixels. ⚠️ Herdada da tela de Receita
#: — depende da resolução da VM e precisa ser conferida na de Despesa.
REGION = (20, 241, 1880, 740)


def montar_lista_upload(
    operadoras: list[str],
    aaaamm: str,
    raiz_operadoras: Path | None = None,
    desde: float | None = None,
) -> list[tuple[str, Path]]:
    """
    Lista os arquivos a subir, na ordem: por operadora, EXT antes de INT.

    Args:
        operadoras: Operadoras a processar.
        aaaamm: Mês de referência.
        raiz_operadoras: Raiz alternativa, para teste.
        desde: Instante (`time.time()`) a partir do qual o arquivo conta como
            desta execução. Arquivos mais antigos são **descartados com aviso**:
            são sobra de uma execução anterior, e o caso perigoso é o `_INT` de um
            mês em que houve retenção continuar na pasta quando o cenário mudou.
            `None` desliga a guarda — é o default, para quem chama só querendo
            listar o que está lá.

    Returns:
        Lista de ``(operadora, caminho)`` na ordem de upload.
    """

    pendencias: list[tuple[str, Path]] = []

    for operadora in operadoras:
        pasta = ep.caminho_agi(operadora, aaaamm, raiz_operadoras)
        if not pasta.is_dir():
            logger.info(f"[HU-17] Sem pasta AGI para {operadora}/{aaaamm}: [{pasta}].")
            continue

        encontrados = 0
        for sufixo in (const.SUFIXO_EXT, const.SUFIXO_INT):
            for caminho in sorted(pasta.glob(f"*_{sufixo}.*")):
                if not caminho.is_file():
                    continue

                if desde is not None and caminho.stat().st_mtime < desde:
                    logger.warning(
                        f"[HU-17] [{caminho.name}] é anterior a esta execução — "
                        f"sobra de uma rodada passada, não será enviado ao AGI. "
                        f"Um _INT antigo subiria num cenário que talvez não tenha "
                        f"mais retenção."
                    )
                    continue

                pendencias.append((operadora, caminho))
                encontrados += 1

        if not encontrados:
            logger.info(f"[HU-17] Nenhum EXT/INT em [{pasta}].")

    return pendencias


def capturar_evidencia_sucesso(nome_arquivo: str, prefixo: str = "evidencia") -> Path | None:
    """
    Salva um print da tela como evidência do upload.

    ⚠️ **Requisito herdado do Projeto 7, sem âncora na V2.** O código de origem
    citava "To Be MVP2, item 4.7.3"; a V2 não tem numeração no texto e as palavras
    "evidência", "print" e "screenshot" não ocorrem nela. A confirmação de carga
    que a V2 de fato exige é gravar `carga_agi` — feito em `subir()`.

    Devolve `None` — sem gravar nada — quando `DIRETORIO_EVIDENCIAS` não está
    configurado: evidência é desejável, mas não é motivo para derrubar o upload.
    """

    if not configuration.DIRETORIO_EVIDENCIAS:
        logger.warning(
            "[HU-17] DIRETORIO_EVIDENCIAS não configurado — evidência não capturada."
        )
        return None

    pasta = Path(configuration.DIRETORIO_EVIDENCIAS)
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{prefixo}_{nome_arquivo}_{datetime.now():%Y%m%d_%H%M%S}.png"

    try:
        pyautogui.screenshot().save(caminho)
    except Exception as exc:
        logger.warning(f"[HU-17] Falha ao capturar evidência em [{caminho}]: {exc}")
        return None

    logger.info(f"[HU-17] Evidência salva em [{caminho}].")
    return caminho


class UploadDetrafAGI:
    """Sobe os EXT/INT do mês no AGI."""

    def __init__(self, agi: AGI | None = None) -> None:
        self.agi = agi or AGI()

    @log_execucao
    def executar(
        self,
        operadoras: list[str],
        aaaamm: str,
        raiz_operadoras: Path | None = None,
        desde: float | None = None,
    ) -> None:
        """
        Fluxo completo: monta a lista, abre o AGI, navega e sobe cada arquivo.

        Com `PERMITIR_UPLOAD_AGI` desligado (o default), registra o que subiria e
        **não abre o AGI**. É o único jeito de exercitar o fluxo sem tocar em
        produção — não há ambiente de teste do AGI (pendência Q20).

        Args:
            desde: Repassado a `montar_lista_upload` — descarta sobra de execução
                anterior. Quem orquestra passa o início da execução.
        """

        pendencias = montar_lista_upload(operadoras, aaaamm, raiz_operadoras, desde)
        if not pendencias:
            logger.info("[HU-17] Nada pendente em EXT/INT; nada a fazer.")
            return

        if not configuration.PERMITIR_UPLOAD_AGI:
            logger.info(
                f"[MODO SEGURO] PERMITIR_UPLOAD_AGI=false — {len(pendencias)} arquivo(s) "
                "pendente(s), nada enviado ao AGI:"
            )
            for operadora, caminho in pendencias:
                logger.info(f"  {operadora}: {caminho.name}")
            return

        self.agi.inicializar()
        try:
            self.agi.acessar_ambiente()
            self.agi.login()
            self.navegar_importar_dados()
            self.subir(pendencias)
        finally:
            self.agi.fechar()

    def navegar_importar_dados(self, tentativas: int = 10) -> None:
        """Menu ``Detraf > Importar Dados``."""

        for _ in range(tentativas):
            if not self.agi._wait_appear(img_bnt_detraf, timeout=130):
                continue
            if not self.agi._click(img_bnt_detraf):
                continue
            pyautogui.moveRel(0, 70)
            if not self.agi._wait_appear(img_bnt_submenu_importar_dados, timeout=15):
                continue
            if self.agi._click(img_bnt_submenu_importar_dados):
                return

        raise AGIError(
            f"Não foi possível chegar a 'Detraf > Importar Dados' em {tentativas} tentativas."
        )

    def subir(self, pendencias: list[tuple[str, Path]]) -> None:
        """
        Sobe cada arquivo, um de cada vez.

        A falha de um arquivo não interrompe os demais — é registrada e o fluxo
        segue, para que uma operadora com problema não bloqueie o mês inteiro.
        """

        for operadora, caminho in pendencias:
            try:
                self.upload_um_arquivo(caminho)
                capturar_evidencia_sucesso(caminho.stem)
                logger.info(f"[HU-17] Upload concluído: {operadora} / {caminho.name}.")
            except Exception as exc:
                logger.excecao(f"[HU-17] Falha no upload de {operadora} / {caminho.name}: {exc}")
            time.sleep(1)

    def upload_um_arquivo(self, caminho: Path) -> None:
        """Clica em Upload e entrega o caminho ao diálogo nativo do Windows."""

        if not self.agi._wait_appear(img_bnt_upload, timeout=40):
            raise AGIError(f"Botão de upload não apareceu para [{caminho.name}].")
        if not self.agi._click(img_bnt_upload):
            raise AGIError(f"Falha ao clicar em upload para [{caminho.name}].")

        self.agi.janela_salvar(
            caminho,
            nome_janela=(
                "(Select location for download by|Selecionar local para download de) "
                f"{configuration.AGI_JANELA_HOST}"
            ),
        )


def detectar_linhas_vermelhas() -> list[tuple[int, int]]:
    """
    Coordenadas das linhas em vermelho na grade — as que o AGI rejeitou.

    ⚠️ **É do processo de Receita**, não da Despesa (decisão de 2026-08-10). Veio
    junto na migração, com `REGION`, e continua aqui por isso — não por
    esquecimento de ligá-la. Ninguém neste repositório a chama, e é o esperado.

    Um limiar de cor errado não levantaria erro: devolveria lista vazia, e o
    upload passaria por bem-sucedido. Ou seja, ligá-la sem calibrar seria pior do
    que não ter conferência nenhuma.
    """

    imagem = np.array(pyautogui.screenshot(region=REGION))
    r, g, b = imagem[:, :, 0], imagem[:, :, 1], imagem[:, :, 2]
    vermelhos_por_linha = ((r > 180) & (g < 130) & (b < 130)).sum(axis=1)

    linhas: list[int] = []
    ultimo_y = -100
    for y in np.where(vermelhos_por_linha > 50)[0]:
        if y - ultimo_y > 10:
            linhas.append(int(y))
            ultimo_y = y

    return [(REGION[0] + REGION[2] // 2, REGION[1] + y) for y in linhas]
