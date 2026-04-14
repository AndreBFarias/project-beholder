"""
Parser HTML para extração de assets de interface.

Extrai URLs de imagens, ícones, SVGs e backgrounds a partir do HTML de uma página.
Normaliza URLs relativas para absolutas usando base_url e deduplica por URL.
"""

import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from src.core.asset_queue import AssetBruto

logger = logging.getLogger("beholder.scraper.html_parser")

EXTENSOES_IMAGEM = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"})
EXTENSOES_VETOR = frozenset({".svg", ".ico"})
EXTENSOES_VALIDAS = EXTENSOES_IMAGEM | EXTENSOES_VETOR


def _classificar_tipo(url: str) -> str:
    """Classifica o tipo de asset pela URL."""
    lower = url.lower()
    if ".svg" in lower:
        return "svg"
    if ".ico" in lower or "icon" in lower or "favicon" in lower:
        return "icon"
    if any(kw in lower for kw in ("background", "/bg/", "-bg.", "_bg.", "cover", "banner", "hero")):
        return "background"
    return "image"


def _url_valida(url: str) -> bool:
    """Retorna True se a URL aponta para um asset de interface suportado."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https", ""):
        return False
    if not parsed.netloc and not parsed.path:
        return False
    path = parsed.path.lower().split("?")[0]
    return any(path.endswith(ext) for ext in EXTENSOES_VALIDAS)


def extrair_assets(html: str, base_url: str) -> list[AssetBruto]:
    """
    Extrai assets de interface a partir do HTML de uma página.

    Fontes varridas:
    - <img src> e <img data-src> (lazy load)
    - <link rel="icon|apple-touch-icon|...">
    - Atributo style com background-image: url(...)
    - <use href> e <image href> em SVG inline

    Args:
        html: Conteúdo HTML da página.
        base_url: URL base para normalizar endereços relativos.

    Returns:
        Lista de AssetBruto sem duplicatas, na ordem de descoberta.
    """
    soup = BeautifulSoup(html, "html.parser")
    urls_vistas: set[str] = set()
    assets: list[AssetBruto] = []

    def _registrar(url_relativa: str, tipo_hint: str | None = None) -> None:
        url_abs = urljoin(base_url, url_relativa.strip())
        if url_abs in urls_vistas:
            return
        if not _url_valida(url_abs):
            return
        urls_vistas.add(url_abs)
        tipo = tipo_hint or _classificar_tipo(url_abs)
        assets.append(AssetBruto(url=url_abs, caminho_local="", tipo=tipo, origem=base_url))

    # <img src> e <img data-src>
    for tag in soup.find_all("img"):
        for attr in ("src", "data-src", "data-lazy-src"):
            src = tag.get(attr, "")
            if src:
                _registrar(src)

    # <link rel="icon|apple-touch-icon|shortcut icon|...">
    for tag in soup.find_all("link"):
        rel = " ".join(tag.get("rel", [])).lower()
        if "icon" in rel:
            href = tag.get("href", "")
            if href:
                _registrar(href, tipo_hint="icon")

    # Atributo style com background-image: url(...)
    for tag in soup.find_all(style=True):
        estilo = tag.get("style", "")
        for match in re.finditer(r'url\(\s*["\']?([^"\')\s]+)["\']?\s*\)', estilo):
            _registrar(match.group(1), tipo_hint="background")

    # <use href> e <image href> em SVG inline (exclui âncoras internas #id)
    for tag in soup.find_all(["use", "image"]):
        for attr in ("href", "xlink:href"):
            href = tag.get(attr, "")
            if href and not href.startswith("#"):
                _registrar(href, tipo_hint="svg")

    logger.debug("Extraídos %d assets de %s", len(assets), base_url)
    return assets
