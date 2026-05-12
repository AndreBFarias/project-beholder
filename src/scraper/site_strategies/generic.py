"""
Estratégia genérica — encapsula o parser HTML atual.

Funciona para qualquer site e serve como fallback do registry quando o domínio
da URL não bate com nenhuma estratégia específica.
"""

from __future__ import annotations

from src.core.asset_queue import AssetBruto
from src.scraper.html_parser import extrair_assets as _extrair_generico
from src.scraper.site_strategies.base import SiteStrategy


class GenericStrategy(SiteStrategy):
    nome = "generic"
    dominios: tuple[str, ...] = ()

    def extrair_assets(self, html: str, base_url: str) -> list[AssetBruto]:
        return _extrair_generico(html, base_url)


# "O mais simples é o mais eficaz." — Leonardo da Vinci
