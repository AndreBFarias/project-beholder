"""
Contrato das estratégias de scraping por site.

Cada site (Pinterest, Dribbble, Behance, Freepik) tem sua própria subclasse de
SiteStrategy que especializa extração de HTML e mapeamento de categorias.
O site_registry usa o `nome` como slug de pasta no ZIP híbrido.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.asset_queue import AssetBruto


class SiteStrategy(ABC):
    """Interface que toda estratégia de site deve implementar."""

    #: Slug usado como nome de subpasta no ZIP (ex: "pinterest", "generic").
    nome: str = "generic"

    #: Domínios aceitos pela estratégia (sufixos — ex: "pinterest.com").
    #: O registry faz match por `url.netloc.endswith(d)`.
    dominios: tuple[str, ...] = ()

    @abstractmethod
    def extrair_assets(self, html: str, base_url: str) -> list[AssetBruto]:
        """Extrai AssetBruto a partir do HTML da página."""

    def categoria_sugerida(self, asset: AssetBruto) -> str | None:
        """Override opcional para sugerir categoria antes da análise IA.

        Útil quando o site expõe metadados explícitos (ex: Freepik classifica
        por tipo na URL). Retornar None delega a decisão à IA.
        """
        return None


# "A forma segue a função." — Louis Sullivan
