"""
Sistema de checkpoint para serialização e restauração de estado de sessão.

Permite pausar e retomar lotes de URLs (Módulo Protocolo).
O arquivo .checkpoint.json registra o estado completo das filas.
"""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger("beholder.checkpoint")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CHECKPOINT_PATH = _PROJECT_ROOT / "data" / "sessao_atual" / ".checkpoint.json"


@dataclass
class EstadoCheckpoint:
    """Representa o estado serializável de uma sessão em andamento."""

    urls_pendentes: list[str]
    urls_concluidas: list[str]
    urls_com_erro: list[str]
    url_atual: str | None
    timestamp: str


def salvar(estado: EstadoCheckpoint) -> None:
    """Serializa o estado da sessão para .checkpoint.json."""
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    dados = json.dumps(asdict(estado), ensure_ascii=False, indent=2)
    CHECKPOINT_PATH.write_text(dados, encoding="utf-8")
    logger.debug("Checkpoint salvo: %s URLs pendentes", len(estado.urls_pendentes))


def carregar() -> EstadoCheckpoint | None:
    """
    Lê o checkpoint do disco.

    Retorna None se o arquivo não existir ou estiver corrompido.
    """
    if not CHECKPOINT_PATH.exists():
        return None
    try:
        dados = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
        estado = EstadoCheckpoint(**dados)
        logger.info(
            "Checkpoint restaurado: %s pendentes, %s concluídas",
            len(estado.urls_pendentes),
            len(estado.urls_concluidas),
        )
        return estado
    except (json.JSONDecodeError, TypeError, KeyError) as exc:
        logger.error("Checkpoint corrompido, ignorando: %s", exc)
        return None


def existe() -> bool:
    """Verifica se há um checkpoint salvo."""
    return CHECKPOINT_PATH.exists()


def remover() -> None:
    """Remove o checkpoint após conclusão ou cancelamento da sessão."""
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()
        logger.debug("Checkpoint removido")
