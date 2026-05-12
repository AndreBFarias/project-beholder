"""Estratégias de scraping por site (Sprint 19).

Cada site pode ter regras de extração HTML e mapeamento de categorias próprias.
O `site_registry` resolve o domínio da URL para a estratégia correta,
recorrendo a `GenericStrategy` como fallback.
"""

from src.scraper.site_strategies.base import SiteStrategy
from src.scraper.site_strategies.behance import BehanceStrategy
from src.scraper.site_strategies.dribbble import DribbbleStrategy
from src.scraper.site_strategies.freepik import FreepikStrategy
from src.scraper.site_strategies.generic import GenericStrategy
from src.scraper.site_strategies.pinterest import PinterestStrategy

__all__ = [
    "SiteStrategy",
    "BehanceStrategy",
    "DribbbleStrategy",
    "FreepikStrategy",
    "GenericStrategy",
    "PinterestStrategy",
]
