"""
Dataset Writer — escreve CSV de metadados de assets processados.

Colunas: url_original, caminho_local, tipo, descricao, tags, paleta_hex, timestamp.
ADR-02: colunas lidas de DEFAULTS["Saida"]["colunas_csv"].
"""

import csv
import logging
from pathlib import Path

from src.core.asset_queue import AssetProcessado
from src.core.config.defaults import DEFAULTS

logger = logging.getLogger("beholder.exporter.dataset_writer")

_COLUNAS = DEFAULTS["Saida"]["colunas_csv"].split(",")

# Mapeamento de tipo de asset para subpasta no .zip
_MAPA_TIPO: dict[str, str] = {
    "icon": "icons",
    "logo": "icons",
    "svg": "icons",
    "vector": "icons",
    "background": "backgrounds",
    "photo": "backgrounds",
    "ui_element": "outros",
    "other": "outros",
}


def subpasta_tipo(tipo: str) -> str:
    """Retorna o nome da subpasta (icons/backgrounds/outros) para o tipo dado."""
    return _MAPA_TIPO.get(tipo.lower(), "outros")


def escrever_csv(assets: list[AssetProcessado], destino: str | Path) -> Path:
    """
    Serializa lista de AssetProcessado em CSV.

    Args:
        assets: Lista de assets já processados.
        destino: Caminho do arquivo .csv a criar (ou sobrescrever).

    Returns:
        Path do arquivo CSV gerado.
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    with destino.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_COLUNAS)
        writer.writeheader()
        for asset in assets:
            writer.writerow(
                {
                    "url_original": asset.url_original,
                    "caminho_local": asset.caminho_local,
                    "tipo": asset.tipo,
                    "descricao": asset.descricao,
                    "tags": "|".join(asset.tags),
                    "paleta_hex": "|".join(asset.paleta_hex),
                    "timestamp": asset.timestamp,
                }
            )

    logger.info("CSV exportado: %s (%d linhas)", destino, len(assets))
    return destino


def ler_csv(origem: str | Path) -> list[dict]:
    """
    Lê um CSV gerado por escrever_csv e retorna lista de dicts.

    Args:
        origem: Caminho do arquivo .csv.

    Returns:
        Lista de dicts com as colunas do CSV.
    """
    origem = Path(origem)
    if not origem.exists():
        logger.warning("CSV não encontrado: %s", origem)
        return []

    with origem.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))
