"""
Estratégia Behance.

Projetos Behance têm galeria de imagens em mosaico. A extração genérica já
pega a maioria dos assets; esta estratégia apenas identifica a origem para o
layout híbrido do ZIP e reserva ponto de extensão para refinamento futuro
(ex: seguir paginação de projetos).
"""

from __future__ import annotations

from src.scraper.site_strategies.generic import GenericStrategy


class BehanceStrategy(GenericStrategy):
    nome = "behance"
    dominios = ("behance.net",)


# "A paciência é amarga, mas seu fruto é doce." — Aristóteles
