"""Uma linha de Detraf válida, e a fábrica que a estraga numa posição por vez."""

from __future__ import annotations

#: Linha válida no layout de 15 colunas da V2, para servir de base.
#:
#: Os testes alteram **uma** posição por vez, e é isso que localiza a regra
#: quebrada: se dois campos mudassem juntos, a reprovação não diria qual falhou.
LINHA_VALIDA: list[str] = [
    "021",       # 1  Credora (EOT da operadora, no Anexo 5)
    "011",       # 2  Devedora (EOT da Vivo)
    "202507",    # 3  Referência = mês corrente -1
    "202507",    # 4  Tráfego
    "",          # 5  POI — livre, não obrigatório
    "0",         # 6  Rel = 0 nas linhas de tráfego
    "LL",        # 7  DESC — descritor final "L" => TU-RL
    "N",         # 8  GH — uma de (S, R, N, D)
    "100",       # 9  Chamadas — inteiro
    "500,0",     # 10 Minutos — até 1 casa decimal
    "0,01500",   # 11 Tarifa — até 5 casas, nunca zero
    "7,50",      # 12 R$_Liq
    "0,69",      # 13 PIS_Cofins
    "1,27",      # 14 ICMS
    "9,46",      # 15 R$_Bruto
]

#: Nome do campo -> índice posicional. O código sempre lê por índice.
POSICOES: dict[str, int] = {
    "credora": 0, "devedora": 1, "referencia": 2, "trafego": 3, "poi": 4,
    "rel": 5, "desc": 6, "gh": 7, "chamadas": 8, "minutos": 9,
    "tarifa": 10, "r_liq": 11, "pis_cofins": 12, "icms": 13, "r_bruto": 14,
}


def linha(**alteracoes) -> list[str]:
    """
    Uma linha válida com as posições indicadas trocadas.

    Uso: ``linha(gh="X")`` devolve a linha padrão com a 8ª coluna inválida.
    """
    nova = list(LINHA_VALIDA)
    for campo, valor in alteracoes.items():
        nova[POSICOES[campo]] = valor
    return nova
