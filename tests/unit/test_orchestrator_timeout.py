"""
Testes de threading do Orchestrator.

Cobrem:
- Thread encerra em < 3s quando _evento_parar é setado com fila vazia
- Thread consome SENTINEL e encerra normalmente
- Thread processa item e chama callback
"""

import threading
import unittest.mock as mock

import pytest

from src.core.asset_queue import SENTINEL, AssetBruto, FilasPipeline


@pytest.fixture
def filas_teste():
    return FilasPipeline()


@pytest.fixture
def mock_glib(monkeypatch):
    """Mock GLib.idle_add para chamar a função diretamente."""
    mock_idle_add = mock.MagicMock(side_effect=lambda fn, *args: fn(*args))
    monkeypatch.setattr("src.ai_vision.orchestrator.GLib.idle_add", mock_idle_add)
    return mock_idle_add


@pytest.fixture
def mock_analisar(monkeypatch):
    """Mock analisar_imagem para retornar resultado fixo."""
    resultado = {"tipo": "icon", "descricao": "ícone de teste", "tags": ["test"]}
    mock_fn = mock.MagicMock(return_value=resultado)
    monkeypatch.setattr("src.ai_vision.orchestrator.analisar_imagem", mock_fn)
    return mock_fn


@pytest.fixture
def mock_paleta(monkeypatch):
    """Mock extrair_paleta para retornar cores fixas."""
    mock_fn = mock.MagicMock(return_value=["#bd93f9", "#ff79c6"])
    monkeypatch.setattr("src.ai_vision.orchestrator.extrair_paleta", mock_fn)
    return mock_fn


def test_cancelamento_encerra_em_3s(filas_teste, mock_glib, monkeypatch):
    """Orchestrator deve encerrar em < 3s quando cancelado com fila vazia."""
    monkeypatch.setattr("src.ai_vision.orchestrator.filas", filas_teste)

    from src.ai_vision.orchestrator import Orchestrator

    log_msgs = []
    concluido = threading.Event()

    orch = Orchestrator(
        on_log=lambda msg: log_msgs.append(msg),
        on_asset=lambda a: None,
        on_concluido=lambda n: concluido.set(),
    )
    orch.iniciar()
    orch.cancelar()

    encerrou = concluido.wait(timeout=3.0)
    assert encerrou, "Orchestrator não encerrou em 3 segundos após cancelamento"


def test_sentinel_encerra_normalmente(filas_teste, mock_glib, monkeypatch):
    """Orchestrator encerra ao receber SENTINEL."""
    monkeypatch.setattr("src.ai_vision.orchestrator.filas", filas_teste)

    from src.ai_vision.orchestrator import Orchestrator

    filas_teste.scraper.put(SENTINEL)
    concluido = threading.Event()
    total_ref = [0]

    orch = Orchestrator(
        on_log=lambda msg: None,
        on_asset=lambda a: None,
        on_concluido=lambda n: (total_ref.__setitem__(0, n), concluido.set()),
    )
    orch.iniciar()

    encerrou = concluido.wait(timeout=5.0)
    assert encerrou
    assert total_ref[0] == 0


def test_processa_asset_antes_de_sentinel(
    filas_teste, mock_glib, mock_analisar, mock_paleta, monkeypatch, tmp_path
):
    """Orchestrator processa asset e chama on_asset."""
    monkeypatch.setattr("src.ai_vision.orchestrator.filas", filas_teste)

    from src.ai_vision.orchestrator import Orchestrator

    img_path = tmp_path / "icon.png"
    img_path.write_bytes(b"\x89PNG fake")

    asset = AssetBruto(
        url="https://example.com/icon.png",
        caminho_local=str(img_path),
        tipo="icon",
        origem="https://example.com",
    )
    filas_teste.scraper.put(asset)
    filas_teste.scraper.put(SENTINEL)

    assets_recebidos = []
    concluido = threading.Event()

    orch = Orchestrator(
        on_log=lambda msg: None,
        on_asset=lambda a: assets_recebidos.append(a),
        on_concluido=lambda n: concluido.set(),
    )
    orch.iniciar()
    concluido.wait(timeout=10.0)

    assert len(assets_recebidos) == 1
    assert assets_recebidos[0].tipo == "icon"
    mock_analisar.assert_called_once()
