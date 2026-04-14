"""
Smoke tests: verifica o módulo de logging.
"""

import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.smoke
def test_logging_config_importa() -> None:
    """logging_config.py importa sem erro."""
    from src.core.logging_config import setup_logging

    assert callable(setup_logging)


@pytest.mark.smoke
def test_setup_logging_cria_diretorio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """setup_logging() cria o diretório logs/ se não existir."""
    import src.core.logging_config as lc

    logs_dir = tmp_path / "logs"
    monkeypatch.setattr(lc, "LOGS_DIR", logs_dir)

    # Resetar handlers para não acumular entre testes
    root = logging.getLogger()
    root.handlers.clear()

    lc.setup_logging()
    assert logs_dir.exists(), "Diretório logs/ deve ser criado por setup_logging()"


@pytest.mark.smoke
def test_setup_logging_silencia_barulhentos() -> None:
    """Loggers ruidosos devem ser silenciados para WARNING ou acima."""
    from src.core.logging_config import setup_logging

    root = logging.getLogger()
    root.handlers.clear()

    setup_logging()

    ruidosos = ["httpx", "urllib3", "PIL", "playwright"]
    for nome in ruidosos:
        nivel = logging.getLogger(nome).level
        assert nivel >= logging.WARNING, f"Logger '{nome}' deveria ser WARNING+, está em {logging.getLevelName(nivel)}"
