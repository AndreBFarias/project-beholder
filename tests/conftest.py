"""
Configuração global de fixtures do pytest para o Project Beholder.
"""

import sys
from pathlib import Path

import pytest

# Garantir que src/ está no path para imports nos testes
sys.path.insert(0, str(Path(__file__).parent.parent))


def pytest_configure(config: pytest.Config) -> None:
    """Registra marcadores customizados para evitar avisos do pytest."""
    config.addinivalue_line("markers", "smoke: testes rápidos de sanidade (sem deps externas)")
    config.addinivalue_line("markers", "unit: testes isolados de unidades individuais")
    config.addinivalue_line("markers", "integration: testes multi-componente")
    config.addinivalue_line("markers", "requires_display: precisa de display GTK (não roda em CI headless)")
    config.addinivalue_line("markers", "requires_gpu: precisa de GPU NVIDIA com VRAM disponível")
