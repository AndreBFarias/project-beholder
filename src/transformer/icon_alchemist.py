"""
Icon Alchemist — transformações visuais de assets.

- extrair_paleta(): K-Means sobre pixels RGB (nunca RGBA — GSD.md)
- criar_icone_circular(): recorte circular com canal alpha
"""

import logging
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from sklearn.cluster import KMeans

logger = logging.getLogger("beholder.transformer.icon_alchemist")

_SUBSAMPLE_MAX = 10_000  # pixels máximos para K-Means (performance)


def extrair_paleta(caminho: str | Path, n_cores: int = 4) -> list[str]:
    """
    Extrai as N cores dominantes da imagem via K-Means.

    Sempre converte para RGB antes de processar (nunca 4 canais, GSD.md).
    Faz subsample para imagens com mais de 10.000 pixels.

    Args:
        caminho: Caminho para o arquivo de imagem.
        n_cores: Número de cores a extrair.

    Returns:
        Lista de strings hexadecimais, ex: ["#bd93f9", "#ff79c6", ...].
    """
    img = Image.open(caminho).convert("RGB")
    pixels = np.array(img, dtype=np.uint8).reshape(-1, 3)

    if len(pixels) > _SUBSAMPLE_MAX:
        rng = np.random.default_rng(42)
        indices = rng.choice(len(pixels), _SUBSAMPLE_MAX, replace=False)
        pixels = pixels[indices]

    # Nunca pedir mais cores do que pixels disponíveis
    n_cores = min(n_cores, len(pixels))

    kmeans = KMeans(n_clusters=n_cores, random_state=42, n_init="auto")
    kmeans.fit(pixels)

    centros = kmeans.cluster_centers_.round().astype(int)
    return [f"#{int(r):02x}{int(g):02x}{int(b):02x}" for r, g, b in centros]


def criar_icone_circular(caminho: str | Path, tamanho: int = 64) -> Image.Image:
    """
    Recorta a imagem em formato circular com canal alpha.

    Args:
        caminho: Caminho para o arquivo de imagem.
        tamanho: Lado do quadrado resultante em pixels.

    Returns:
        Imagem RGBA com fundo transparente e conteúdo circular.
    """
    img = Image.open(caminho).convert("RGBA").resize((tamanho, tamanho), Image.LANCZOS)

    mascara = Image.new("L", (tamanho, tamanho), 0)
    draw = ImageDraw.Draw(mascara)
    draw.ellipse((0, 0, tamanho - 1, tamanho - 1), fill=255)

    resultado = Image.new("RGBA", (tamanho, tamanho), (0, 0, 0, 0))
    resultado.paste(img, mask=mascara)
    return resultado
