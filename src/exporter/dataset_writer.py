"""
Dataset Writer — escreve CSV de metadados de assets processados.

Colunas: url_original, caminho_local, tipo, descricao, tags, paleta_hex, timestamp.
ADR-02: colunas e mapa de pastas lidos dinamicamente de DEFAULTS a cada chamada
(mudanças em Grimório propagam sem reiniciar a aplicação).
"""

import csv
import logging
from pathlib import Path

from src.core.asset_queue import AssetProcessado
from src.core.config.defaults import DEFAULTS

logger = logging.getLogger("beholder.exporter.dataset_writer")


def _colunas() -> list[str]:
    return DEFAULTS["Saida"]["colunas_csv"].split(",")


def subpasta_tipo(tipo: str) -> str:
    """Retorna o nome da subpasta em PT-BR (ícones/fundos/outros) para o tipo dado.

    Lê `DEFAULTS["Espolio"]["mapa_pastas"]` dinamicamente — mudanças em
    Grimório propagam sem reiniciar.
    """
    cfg = DEFAULTS["Espolio"]
    mapa = cfg["mapa_pastas"]
    fallback = cfg["pasta_fallback"]
    return mapa.get(tipo.lower(), fallback)


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
        writer = csv.DictWriter(f, fieldnames=_colunas())
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
                    "site_origem": asset.site_origem,
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
