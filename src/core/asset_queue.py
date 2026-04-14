"""
Filas compartilhadas do pipeline produtor-consumidor (ADR-01).

FilasPipeline gerencia as filas do pipeline. Chamar nova_sessao() antes de
iniciar cada pipeline para evitar deadlock por estado residual (BUG-02/BUG-10).

Diagrama:
    Thread A (Scraper) → filas.scraper → Thread B (AI Worker) → filas.processada → Thread C (Exporter)

Regras:
- maxsize=50 em ambas as filas (backpressure para evitar consumo ilimitado de memória)
- SENTINEL = None sinaliza fim da fila para o consumidor encerrar graciosamente
"""

from dataclasses import dataclass, field
from queue import Queue

from src.core.config.defaults import DEFAULTS

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


class FilasPipeline:
    """Gerencia as filas do pipeline produtor-consumidor.

    Chamar nova_sessao() antes de cada execução do pipeline para
    garantir filas limpas e evitar deadlock por estado residual.
    """

    def __init__(self) -> None:
        self._maxsize_scraper: int = DEFAULTS["Fila"]["maxsize_scraper"]
        self._maxsize_processada: int = DEFAULTS["Fila"]["maxsize_processada"]
        self.nova_sessao()

    def nova_sessao(self) -> None:
        """Cria filas novas e vazias para uma nova sessão do pipeline."""
        self.scraper: Queue = Queue(maxsize=self._maxsize_scraper)
        self.processada: Queue = Queue(maxsize=self._maxsize_processada)


filas = FilasPipeline()
