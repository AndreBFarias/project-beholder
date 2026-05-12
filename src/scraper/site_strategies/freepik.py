"""
Estratégia Freepik / Flaticon.

Flaticon tem URLs que deixam o tipo explícito (ex: /free-icon/). Esta
estratégia usa esse sinal para sugerir categoria antes da IA rodar.
"""

from __future__ import annotations

from src.core.asset_queue import AssetBruto
from src.scraper.site_strategies.generic import GenericStrategy


class FreepikStrategy(GenericStrategy):
    nome = "freepik"
    dominios = ("freepik.com", "flaticon.com")

    def categoria_sugerida(self, asset: AssetBruto) -> str | None:
        url = asset.url.lower()
        if "/icon" in url or "flaticon" in url:
            return "icon"
        if "vector" in url or url.endswith(".svg"):
            return "vector"
        if "background" in url or "wallpaper" in url:
            return "background"
        return None


# "O todo é maior que a soma das partes — mas cada parte importa." — Aristóteles
