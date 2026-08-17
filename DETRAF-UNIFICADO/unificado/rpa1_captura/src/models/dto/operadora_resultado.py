from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OperadoraResultado:
    """Resultado da identificação da operadora a partir do arquivo/remetente."""

    dominio: str
    nome: Optional[str]
    identificada: bool
    origem: str = ""  # "eot" (identificado pelo EOT do arquivo) ou "dominio" (fallback)
