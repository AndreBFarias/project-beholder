"""
Loader de configuração com fallback para defaults.py.

Hierarquia de resolução (ADR-02):
1. defaults.py — constantes puras (este arquivo faz fallback para lá)
2. ~/.config/beholder/config.ini — overrides persistidos do usuário (XDG)
3. Este módulo — loader com fallback transparente
"""

import configparser
import logging
from pathlib import Path
from typing import Any

from src.core.config.defaults import DEFAULTS

logger = logging.getLogger("beholder.config")

XDG_CONFIG_PATH = Path.home() / ".config" / "beholder" / "config.ini"


class Config:
    """Gerenciador de configuração com fallback para defaults."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._path = config_path or XDG_CONFIG_PATH
        self._parser = configparser.ConfigParser()
        self._carregar()

    def _carregar(self) -> None:
        """Carrega config.ini se existir; silencioso se ausente."""
        if self._path.exists():
            self._parser.read(self._path, encoding="utf-8")
            logger.debug("Configuração carregada de %s", self._path)
        else:
            logger.debug("config.ini ausente — usando apenas defaults")

    def get(self, secao: str, chave: str) -> Any:
        """
        Retorna valor da configuração com fallback para defaults.

        Tenta config.ini primeiro; se ausente, usa defaults.py.
        Preserva o tipo do valor em defaults.py.
        """
        default_valor = DEFAULTS.get(secao, {}).get(chave)

        if self._parser.has_option(secao, chave):
            valor_raw = self._parser.get(secao, chave)
            return self._converter_tipo(valor_raw, default_valor)

        return default_valor

    def set(self, secao: str, chave: str, valor: Any) -> None:
        """Define um valor em memória (não persiste até chamar save())."""
        if not self._parser.has_section(secao):
            self._parser.add_section(secao)
        self._parser.set(secao, chave, str(valor))

    def save(self) -> None:
        """Persiste a configuração atual em ~/.config/beholder/config.ini."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            self._parser.write(f)
        logger.info("Configuração salva em %s", self._path)

    def restaurar_padroes(self) -> None:
        """Remove config.ini do usuário, restaurando todos os defaults."""
        if self._path.exists():
            self._path.unlink()
            logger.info("Configuração do usuário removida — defaults restaurados")
        self._parser = configparser.ConfigParser()

    @staticmethod
    def _converter_tipo(valor_raw: str, referencia: Any) -> Any:
        """Converte string do configparser para o tipo do valor de referência."""
        if referencia is None:
            return valor_raw
        tipo = type(referencia)
        if tipo is bool:
            return valor_raw.lower() in ("true", "1", "yes", "sim")
        try:
            return tipo(valor_raw)
        except (ValueError, TypeError):
            return valor_raw
