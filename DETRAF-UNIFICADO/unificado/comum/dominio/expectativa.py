"""O que o nome de um arquivo de expectativa diz sobre ele.

Origem: `preparar_ambiente._pasta_de_expectativa`, que trazia esta heurística com
o comentário *"ela vive aqui de propósito... O robô não usa isto"*. Deixou de ser
verdade em 2026-08-10: a captação por SFTP precisa dela para o modo `--de-pasta`,
quando a origem é um diretório plano e não a árvore remota espelhada.

Dois consumidores reais em lugares diferentes — é o critério de promoção do
projeto, e a alternativa era a segunda cópia de uma classificação, que é o
defeito A4 que este repositório já pagou duas vezes.
"""

from __future__ import annotations

from pathlib import Path


def pasta_por_nome(nome_arquivo: str, pastas: list[str]) -> str | None:
    """
    Em qual das `pastas` este arquivo de expectativa entra, pelo nome.

    Os arquivos reais dizem no **penúltimo campo**::

        DETRAF_FINAL_VIVO_202603_N_ALGAR_SMP_VIVO_D.csv  ->  Vivo
        DETRAF_FINAL_VIVO_202603_N_ALGAR_STF_TLF_D.csv   ->  TLF

    ⚠️ A varredura é **de trás para frente**, e isso não é detalhe: `VIVO`
    aparece também no começo de todos eles (`DETRAF_FINAL_VIVO_...`), e procurar
    do início mandaria os arquivos da TLF para a pasta da Vivo. Foi o que
    aconteceu na primeira versão disto.

    Returns:
        O nome da pasta, como veio em `pastas`, ou `None` quando nenhuma casa —
        e aí quem chama decide o que fazer, porque escolher uma seria pior.
    """
    campos = [campo.upper() for campo in Path(nome_arquivo).stem.split("_")]
    por_nome = {pasta.upper(): pasta for pasta in pastas}

    for campo in reversed(campos):
        if campo in por_nome:
            return por_nome[campo]

    return None
