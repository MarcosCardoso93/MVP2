"""Renderização do corpo de um e-mail a partir de um template (2026-08-06).

Veio de `rpa2/src/services/notificacao_email.py`, onde nasceu junto com a busca
do e-mail de origem. Só o renderizador subiu: a busca **por nome de arquivo**
existia porque o RPA 2 recebia o arquivo já movido e renomeado, e tinha de
adivinhar de qual e-mail ele viera. O RPA 1 não adivinha — ele tem o `entry_id`
em mãos, porque acabou de baixar o anexo.

A assinatura ficou mais geral do que era (`dados: dict`, e não um registro de
rastreamento): quem monta os dados agora é o robô, e o RPA 1 acrescenta os
motivos da recusa.
"""

from __future__ import annotations


class _PlaceholderAusente(dict):
    """Faz `str.format_map` deixar literal o que não souber substituir."""

    def __missing__(self, chave):
        return "{" + chave + "}"


def renderizar(template: str, dados: dict[str, str]) -> str:
    """
    Substitui os placeholders do template pelos dados informados.

    Um placeholder desconhecido **fica literal**, em vez de levantar. É
    deliberado: melhor um `{campo_novo}` visível no rascunho — que quem revisa vê
    e corrige — do que uma exceção que impede o aviso inteiro de existir. O robô
    responde a operadora; ele não é o dono do texto.

    Args:
        template: O texto com `{placeholders}`.
        dados: Nome do placeholder -> valor.
    """
    return template.format_map(_PlaceholderAusente(dados))
