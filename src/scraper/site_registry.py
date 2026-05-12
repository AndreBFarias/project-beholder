"""
Registry de estratégias de site (Sprint 19).

Resolve URL → SiteStrategy com base no domínio. Fallback para GenericStrategy
quando nenhum domínio registrado bate.

Uso:
    strategy = resolver_strategy("https://dribbble.com/shots/123")
    assets = strategy.extrair_assets(html, base_url)
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from src.scraper.site_strategies import (
    BehanceStrategy,
    DribbbleStrategy,
    FreepikStrategy,
    GenericStrategy,
    PinterestStrategy,
    SiteStrategy,
)

logger = logging.getLogger("beholder.scraper.site_registry")

# Ordem importa: domínios mais específicos primeiro.
_STRATEGIES: tuple[SiteStrategy, ...] = (
    PinterestStrategy(),
    DribbbleStrategy(),
    BehanceStrategy(),
    FreepikStrategy(),
)

_FALLBACK = GenericStrategy()


def resolver_strategy(url: str) -> SiteStrategy:
    """Retorna a estratégia apropriada para a URL dada.

    Usa correspondência por sufixo de netloc (ex: "www.pinterest.com" casa
    com o domínio "pinterest.com"). Sem match → GenericStrategy.
    """
    netloc = urlparse(url).netloc.lower()
    if not netloc:
        return _FALLBACK

    for strategy in _STRATEGIES:
        for dominio in strategy.dominios:
            if netloc == dominio or netloc.endswith(f".{dominio}"):
                return strategy

    return _FALLBACK


def listar_sites_suportados() -> list[str]:
    """Lista os slugs das estratégias concretas registradas."""
    return [s.nome for s in _STRATEGIES]


# "Cada coisa tem seu lugar, e cada lugar tem sua coisa." — provérbio latino
