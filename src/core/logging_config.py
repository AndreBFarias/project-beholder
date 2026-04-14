"""
Configuração centralizada de logging para o Project Beholder.

- Arquivo: logs/beholder.log — DEBUG+, RotatingFileHandler (10MB × 3 backups)
- Console: INFO+
- Loggers ruidosos silenciados: httpx, urllib3, asyncio, PIL, playwright
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = _PROJECT_ROOT / "logs"
LOG_FILE = LOGS_DIR / "beholder.log"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 3

_LOGGERS_RUIDOSOS = ["httpx", "urllib3", "asyncio", "PIL", "playwright", "charset_normalizer"]


def setup_logging() -> None:
    """
    Configura o sistema de logging do projeto.

    Deve ser chamado uma única vez na inicialização, antes de qualquer
    outro módulo usar logging.getLogger().
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    for nome in _LOGGERS_RUIDOSOS:
        logging.getLogger(nome).setLevel(logging.WARNING)

    logging.getLogger("beholder").info("Sistema de logging iniciado")
