"""
Estratégia Dribbble.

Dribbble hospeda shots em cdn.dribbble.com; URLs de thumbnail contêm
sufixos como `_1x.png` — a versão em alta resolução remove o sufixo.
"""

from __future__ import annotations

import re

from src.core.asset_queue import AssetBruto
from src.scraper.site_strategies.generic import GenericStrategy

_SUFIXO_THUMB = re.compile(r"_(1x|2x|teaser|small|medium)\.")


def _promover_para_maxima(url: str) -> str:
    return _SUFIXO_THUMB.sub(".", url)


class DribbbleStrategy(GenericStrategy):
    nome = "dribbble"
    dominios = ("dribbble.com",)

    def extrair_assets(self, html: str, base_url: str) -> list[AssetBruto]:
        assets = super().extrair_assets(html, base_url)
        return [
            AssetBruto(
                url=_promover_para_maxima(a.url),
                caminho_local=a.caminho_local,
                tipo=a.tipo,
                origem=a.origem,
            )
            for a in assets
        ]


# "Design é iteração." — adaptado de Bret Victor
