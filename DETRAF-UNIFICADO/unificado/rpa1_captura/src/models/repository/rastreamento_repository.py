"""Rastreamento arquivo baixado -> e-mail de origem (HU-01)."""

import json
from pathlib import Path
from typing import Optional

from comum.config import configuration
from comum.config.logger_config import logger
from src.models.dto.registro_rastreamento import RegistroRastreamento


class RastreamentoRepository:
    """
    Persiste, em um arquivo JSON, o vínculo entre cada arquivo baixado do
    Outlook e o e-mail de origem — permite localizar o e-mail original a
    partir do arquivo baixado (ex.: para responder por e-mail).
    """

    def __init__(self, caminho_arquivo: Optional[Path] = None) -> None:
        self._caminho = caminho_arquivo or Path(configuration.RASTREAMENTO_ARQUIVO_PATH)

    def registrar(self, registro: RegistroRastreamento) -> None:
        """Adiciona ou substitui (por caminho_arquivo) um registro de rastreamento."""
        registros = self._carregar()
        registros = [r for r in registros if r["caminho_arquivo"] != registro.caminho_arquivo]
        registros.append(registro.__dict__)
        self._salvar(registros)
        logger.debug(f"Rastreamento registrado: '{registro.caminho_arquivo}' -> {registro.entry_id}")

    def buscar_por_arquivo(self, caminho: Path) -> Optional[RegistroRastreamento]:
        """Retorna o registro de rastreamento de um arquivo, se existir."""
        caminho_str = str(caminho)
        for registro in self._carregar():
            if registro["caminho_arquivo"] == caminho_str:
                return RegistroRastreamento(**registro)
        return None

    def existe_entry_id(self, entry_id: str) -> bool:
        """True se já existe algum arquivo rastreado para esse entry_id."""
        return any(r["entry_id"] == entry_id for r in self._carregar())

    def _carregar(self) -> list[dict]:
        if not self._caminho.exists():
            return []
        try:
            return json.loads(self._caminho.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error(f"Falha ao ler rastreamento '{self._caminho}': {exc}")
            return []

    def _salvar(self, registros: list[dict]) -> None:
        self._caminho.parent.mkdir(parents=True, exist_ok=True)
        self._caminho.write_text(
            json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8"
        )
