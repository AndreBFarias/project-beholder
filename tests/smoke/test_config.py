"""
Smoke tests: verifica o módulo de configuração.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.smoke
def test_defaults_importa() -> None:
    """defaults.py importa sem erro."""
    from src.core.config.defaults import DEFAULTS

    assert isinstance(DEFAULTS, dict)


@pytest.mark.smoke
def test_defaults_secoes_obrigatorias() -> None:
    """defaults.py contém todas as seções obrigatórias."""
    from src.core.config.defaults import DEFAULTS

    secoes_obrigatorias = ["Scraper", "IA", "Saida", "Interface"]
    for secao in secoes_obrigatorias:
        assert secao in DEFAULTS, f"Seção '{secao}' ausente em defaults.py"


@pytest.mark.smoke
def test_defaults_valores_criticos() -> None:
    """Valores críticos presentes e com tipos corretos."""
    from src.core.config.defaults import DEFAULTS

    assert isinstance(DEFAULTS["Scraper"]["timeout"], int)
    assert isinstance(DEFAULTS["IA"]["ollama_port"], int)
    assert DEFAULTS["IA"]["ollama_port"] == 11435, "Porta Ollama deve ser 11435 (ADR-03)"
    assert isinstance(DEFAULTS["Saida"]["kmeans_cores"], int)


@pytest.mark.smoke
def test_config_loader_importa() -> None:
    """config.py importa sem erro."""
    from src.core.config.config import Config

    assert Config is not None


@pytest.mark.smoke
def test_config_get_com_fallback() -> None:
    """Config.get() retorna valor padrão de defaults quando config.ini não existe."""
    from src.core.config.config import Config

    config = Config()
    timeout = config.get("Scraper", "timeout")
    assert timeout == 30, f"Timeout padrão deve ser 30, obtido: {timeout}"
