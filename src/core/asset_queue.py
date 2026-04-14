"""
Filas compartilhadas do pipeline produtor-consumidor (ADR-01).

As filas são singletons de módulo — importadas diretamente pelos workers.

Diagrama:
    Thread A (Scraper) → fila_scraper → Thread B (AI Worker) → fila_processada → Thread C (Exporter)

Regras:
- maxsize=50 em ambas as filas (backpressure para evitar consumo ilimitado de memória)
- SENTINEL = None sinaliza fim da fila para o consumidor encerrar graciosamente
"""

from dataclasses import dataclass, field
from queue import Queue

SENTINEL = None  # Sinal de fim de fila (put None → consumidor encerra)


@dataclass
class AssetBruto:
    """Asset extraído pelo scraper, ainda sem processamento de IA."""

    url: str
    caminho_local: str
    tipo: str  # "icon" | "image" | "svg" | "background" | "other"
    origem: str  # URL da página onde foi encontrado


@dataclass
class AssetProcessado:
    """Asset após análise de IA e extração de paleta."""

    url_original: str
    caminho_local: str
    tipo: str
    descricao: str
    tags: list[str] = field(default_factory=list)
    paleta_hex: list[str] = field(default_factory=list)
    timestamp: str = ""


# Fila Thread A → Thread B (assets brutos do scraper)
fila_scraper: Queue = Queue(maxsize=50)

# Fila Thread B → Thread C (assets processados com tags e paleta)
fila_processada: Queue = Queue(maxsize=50)
