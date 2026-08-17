from pathlib import Path
from datetime import datetime


def salvar_debug_log(nome_arquivo: str, conteudo: str) -> str:

    agora = datetime.now()

    ano = agora.strftime("%Y")
    mes = agora.strftime("%m")
    timestamp = agora.strftime("%Y%m%d_%H%M%S")

    # Caminho da raiz do projeto
    raiz_projeto = Path(__file__).resolve().parent.parent.parent

    # projeto/data/debug_logs/<ano>/<mes>
    pasta_destino = raiz_projeto / "data" / "debug_logs" / ano / mes

    pasta_destino.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho_arquivo = pasta_destino / f"{nome_arquivo}_{timestamp}.txt"

    with open(
        caminho_arquivo,
        "w",
        encoding="utf-8",
    ) as arquivo:
        arquivo.write(str(conteudo))

    return str(caminho_arquivo)
