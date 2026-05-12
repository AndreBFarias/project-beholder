"""
Estratégia Pinterest.

Atualmente usa a extração genérica com refinamento de URL para pegar imagens
em alta resolução quando o padrão de thumbnail for detectável.
Pinterest serve imagens em vários tamanhos pela URL (ex: /236x/ → /originals/).
"""

from __future__ import annotations

import re

from src.core.asset_queue import AssetBruto
from src.scraper.site_strategies.generic import GenericStrategy

_THUMB_PATTERN = re.compile(r"/(236x|474x|564x|736x)/")


def _promover_para_original(url: str) -> str:
    """Substitui prefixo de thumbnail por /originals/ quando aplicável."""
    return _THUMB_PATTERN.sub("/originals/", url)


class PinterestStrategy(GenericStrategy):
    nome = "pinterest"
    dominios = ("pinterest.com", "pin.it")

    def extrair_assets(self, html: str, base_url: str) -> list[AssetBruto]:
        assets = super().extrair_assets(html, base_url)
        return [
            AssetBruto(
                url=_promover_para_original(a.url),
                caminho_local=a.caminho_local,
                tipo=a.tipo,
                origem=a.origem,
            )
            for a in assets
        ]


# "Vista é arte; arte é memória." — provérbio
