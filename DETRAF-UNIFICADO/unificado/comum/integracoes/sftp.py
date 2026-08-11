"""Integração com o SFTP do ClickHub, de onde vem a expectativa Vivo.

Origem: o script autônomo `Baixa só os arquivos _D (Detalhado).txt`, entregue em
2026-08-10. Ele fazia tudo num `main()` — conexão, filtro, download e `print` —,
com o destino apontando para `../downloads` e as credenciais coladas no fim do
arquivo.

Aqui ficou só o **transporte**. As regras (que período, que arquivo, para qual
pasta) vivem em `rpa2_validacao_apuracao/src/services/captacao_expectativa.py`,
onde dá para testá-las sem rede.

## Esta camada não decide se pode baixar

Igual ao `outlook.py`: a credencial chega **por parâmetro**, e o kill-switch
(`PERMITIR_DOWNLOAD_SFTP`) é conferido pelo chamador, antes de instanciar. Uma
integração que lê `configuration` sozinha não dá para exercitar em teste sem
mexer em variável global, e a decisão de agir para fora deixa de estar num lugar
só.

## As credenciais

`CLICKHUB_SFTP_HOST`, `CLICKHUB_SFTP_USER` e `CLICKHUB_SFTP_PASSWORD`, lidas do
ambiente por `configuration` — nunca daqui.

🔴 **A senha que veio no script precisa ser rotacionada.** Ela circulou em texto
claro dentro de um arquivo (`vivo@2023`), e remover o arquivo não desfaz isso.

## ⚠️ A chave do host é aceita cegamente

`AutoAddPolicy` veio do script e ficou. É o que permite conectar num host cuja
chave ninguém registrou — e também o que deixa um man-in-the-middle passar
despercebido. Numa rede interna com host fixo o risco é baixo, mas a correção
existe e é barata: fixar o fingerprint quando alguém puder fornecê-lo.
"""

from __future__ import annotations

from pathlib import Path

from comum.config.logger_config import logger


#: Pasta remota no ClickHub -> subpasta local em `CAMINHO_EXPECTATIVA_DETRAF`.
#:
#: Veio do `FOLDER_MAPPING` do script de origem. São **cinco origens para quatro
#: destinos**: `SMS_ITF` e `VIVO` caem os dois em `Vivo`.
#:
#: Mora aqui, e não no serviço que a usa, porque descreve a **forma do servidor
#: remoto** — é conhecimento da integração. E porque o `verificar_ambiente.py`
#: precisa dela para conferir, antes de rodar, se todo destino está em
#: `PASTAS_EXPECTATIVAS`: baixar para uma pasta que o RPA 2 não lê é trabalho
#: jogado fora, e o sintoma seria "a expectativa não apareceu".
MAPA_PASTAS: dict[str, str] = {
    "/interfaces/GERACAO_DETRAF_SMS_ITF": "Vivo",
    "/interfaces/GERACAO_DETRAF_VIVO": "Vivo",
    "/interfaces/GERACAO_DETRAF_TELEFONICA": "TLF",
    "/interfaces/MVNO/NEXTEL/DESMP": "MVNO",
    "/interfaces/GERACAO_DETRAF_TRP": "Detraf TRP",
}


class SFTPError(RuntimeError):
    """Falha ao falar com o SFTP."""


class SFTPService:
    """Sessão SFTP: lista e baixa. Nada além disso."""

    def __init__(
        self,
        host: str,
        usuario: str,
        senha: str,
        porta: int = 22,
        timeout: int = 30,
    ) -> None:
        self._host = host
        self._usuario = usuario
        self._senha = senha
        self._porta = porta
        self._timeout = timeout
        self._ssh = None
        self._sftp = None

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def conectar(self) -> None:
        """
        Abre a sessão. `SFTPError` com o que conferir quando não der.

        O `import paramiko` é **tardio**, dentro do método: ele puxa
        `cryptography`, `bcrypt` e `pynacl`, e nada disso precisa ser carregado
        numa execução que não vai baixar arquivo nenhum — que é o caso sempre
        que `PERMITIR_DOWNLOAD_SFTP` está desligado.
        """
        import paramiko

        faltando = [
            nome
            for nome, valor in (
                ("CLICKHUB_SFTP_HOST", self._host),
                ("CLICKHUB_SFTP_USER", self._usuario),
                ("CLICKHUB_SFTP_PASSWORD", self._senha),
            )
            if not valor
        ]
        if faltando:
            raise SFTPError(
                f"[SFTP] Faltam credenciais no ambiente: {', '.join(faltando)}.\n"
                f"  -> Elas são variáveis de ambiente da máquina, não do `.env` "
                f"do repositório.\n"
                f"  -> Para testar SEM SFTP, o RPA 2 aceita "
                f"`main.py --etapa expectativa --de-pasta CAMINHO`: ele lê de um "
                f"diretório local aplicando os mesmos filtros."
            )

        logger.info(f"[SFTP] Conectando em {self._usuario}@{self._host}:{self._porta}")

        ssh = paramiko.SSHClient()
        # Ver o aviso sobre AutoAddPolicy no docstring do módulo.
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(
                hostname=self._host,
                port=self._porta,
                username=self._usuario,
                password=self._senha,
                timeout=self._timeout,
            )
            self._sftp = ssh.open_sftp()
        except Exception as erro:
            raise SFTPError(
                f"[SFTP] Não foi possível conectar em {self._host}:{self._porta} "
                f"como '{self._usuario}': {erro}\n"
                f"  -> Confira a rede/VPN até o host e se a credencial ainda vale.\n"
                f"  -> Nada foi baixado; a pasta de expectativa continua como estava."
            ) from erro

        self._ssh = ssh
        logger.info("[SFTP] Conectado.")

    def fechar(self) -> None:
        """Fecha o que estiver aberto. Seguro de chamar duas vezes."""
        for recurso in (self._sftp, self._ssh):
            if recurso is None:
                continue
            try:
                recurso.close()
            except Exception as erro:  # noqa: BLE001 - fechar não pode derrubar
                logger.warning(f"[SFTP] Falha ao fechar a sessão: {erro}")

        self._sftp = None
        self._ssh = None

    def __enter__(self) -> SFTPService:
        self.conectar()
        return self

    def __exit__(self, *_) -> None:
        self.fechar()

    # ------------------------------------------------------------------
    # Operações
    # ------------------------------------------------------------------

    def listar(self, caminho_remoto: str) -> list[str]:
        """
        Nomes dos arquivos de uma pasta remota.

        **Devolve lista vazia** quando a pasta não existe ou não pode ser lida,
        com o motivo no log — em vez de levantar. São cinco pastas por execução, e
        uma indisponível não pode impedir as outras quatro de serem baixadas. É o
        comportamento do script de origem, e é o certo aqui.
        """
        if self._sftp is None:
            raise SFTPError("[SFTP] `listar` chamado sem sessão aberta.")

        try:
            return self._sftp.listdir(caminho_remoto)
        except Exception as erro:  # noqa: BLE001 - uma pasta não derruba as outras
            logger.error(
                f"[SFTP] Não foi possível listar [{caminho_remoto}]: {erro}. "
                f"As demais pastas continuam."
            )
            return []

    def baixar(self, caminho_remoto: str, destino: Path) -> Path:
        """Baixa um arquivo. `SFTPError` quando falha — quem chama decide seguir."""
        if self._sftp is None:
            raise SFTPError("[SFTP] `baixar` chamado sem sessão aberta.")

        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._sftp.get(caminho_remoto, str(destino))
        except Exception as erro:
            raise SFTPError(
                f"[SFTP] Falha ao baixar [{caminho_remoto}] para [{destino}]: {erro}"
            ) from erro

        return destino
