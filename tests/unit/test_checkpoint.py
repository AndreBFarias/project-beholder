"""
Unit tests: verifica o módulo de checkpoint.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.unit
def test_checkpoint_importa() -> None:
    """checkpoint.py importa sem erro."""
    from src.core.checkpoint import EstadoCheckpoint, carregar, existe, salvar

    assert EstadoCheckpoint is not None
    assert callable(salvar)
    assert callable(carregar)
    assert callable(existe)


@pytest.mark.unit
def test_checkpoint_salvar_carregar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Salvar e carregar checkpoint preserva todos os campos."""
    import src.core.checkpoint as cp

    caminho_teste = tmp_path / "sessao" / ".checkpoint.json"
    monkeypatch.setattr(cp, "CHECKPOINT_PATH", caminho_teste)

    from src.core.checkpoint import EstadoCheckpoint, carregar, salvar

    estado = EstadoCheckpoint(
        urls_pendentes=["https://example.com", "https://test.com"],
        urls_concluidas=["https://done.com"],
        urls_com_erro=[],
        url_atual="https://example.com",
        timestamp="2026-04-13T12:00:00",
    )
    salvar(estado)
    assert caminho_teste.exists()

    carregado = carregar()
    assert carregado is not None
    assert carregado.urls_pendentes == estado.urls_pendentes
    assert carregado.urls_concluidas == estado.urls_concluidas
    assert carregado.url_atual == estado.url_atual
    assert carregado.timestamp == estado.timestamp


@pytest.mark.unit
def test_checkpoint_existe_false(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """existe() retorna False quando arquivo não existe."""
    import src.core.checkpoint as cp

    monkeypatch.setattr(cp, "CHECKPOINT_PATH", tmp_path / ".checkpoint.json")

    from src.core.checkpoint import existe

    assert existe() is False


@pytest.mark.unit
def test_checkpoint_carregar_ausente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """carregar() retorna None quando arquivo não existe."""
    import src.core.checkpoint as cp

    monkeypatch.setattr(cp, "CHECKPOINT_PATH", tmp_path / ".checkpoint.json")

    from src.core.checkpoint import carregar

    assert carregar() is None
