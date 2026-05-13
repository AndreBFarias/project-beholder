"""
Testes de integração — modo "analisar pasta já baixada" (Sprint 16).

Valida:
- Orchestrator.analisar_pasta_local injeta AssetBruto na fila a partir de
  imagens em disco sem precisar rescrapar.
- Pipeline consome os assets até SENTINEL e chama on_asset para cada um.
- Aviso de fila vazia é emitido quando diretório existe mas não tem imagens.
- Diretório inexistente retorna 0 e loga erro, sem derrubar o pipeline.
"""

import threading
import unittest.mock as mock

import pytest

from src.core.asset_queue import FilasPipeline


@pytest.fixture
def filas_teste():
    return FilasPipeline()


@pytest.fixture
def mock_glib(monkeypatch):
    mock_idle_add = mock.MagicMock(side_effect=lambda fn, *args: fn(*args))
    monkeypatch.setattr("src.ai_vision.orchestrator.GLib.idle_add", mock_idle_add)
    return mock_idle_add


@pytest.fixture
def mock_analisar(monkeypatch):
    resultado = {"tipo": "icon", "descricao": "ícone de teste", "tags": ["local"]}
    mock_fn = mock.MagicMock(return_value=resultado)
    monkeypatch.setattr("src.ai_vision.orchestrator.analisar_imagem", mock_fn)
    return mock_fn


@pytest.fixture
def mock_paleta(monkeypatch):
    mock_fn = mock.MagicMock(return_value=["#bd93f9"])
    monkeypatch.setattr("src.ai_vision.orchestrator.extrair_paleta", mock_fn)
    return mock_fn


@pytest.mark.integration
def test_reanalise_processa_imagens_locais(filas_teste, mock_glib, mock_analisar, mock_paleta, monkeypatch, tmp_path):
    """Reanálise lê imagens do disco e as processa pelo pipeline completo."""
    monkeypatch.setattr("src.ai_vision.orchestrator.filas", filas_teste)

    from src.ai_vision.orchestrator import Orchestrator

    (tmp_path / "icone1.png").write_bytes(b"\x89PNG fake-1")
    (tmp_path / "icone2.jpg").write_bytes(b"\xff\xd8\xff fake-2")
    (tmp_path / "ignorar.txt").write_text("nao deve ser enfileirado")

    assets_recebidos: list = []
    concluido = threading.Event()
    total_ref = [0]

    orch = Orchestrator(
        on_log=lambda msg: None,
        on_asset=lambda a: assets_recebidos.append(a),
        on_concluido=lambda n: (total_ref.__setitem__(0, n), concluido.set()),
    )

    enfileirados = orch.analisar_pasta_local(tmp_path)
    assert enfileirados == 2, "Deve enfileirar .png e .jpg, ignorando .txt"

    orch.iniciar()
    assert concluido.wait(timeout=10.0), "Pipeline não encerrou em 10s"

    assert total_ref[0] == 2
    assert len(assets_recebidos) == 2
    assert all(a.tipo == "icon" for a in assets_recebidos)
    assert all(a.descricao == "ícone de teste" for a in assets_recebidos)


@pytest.mark.integration
def test_reanalise_pasta_vazia_emite_aviso(filas_teste, mock_glib, monkeypatch, tmp_path):
    """Pasta existe mas sem imagens — não enfileira nada, ainda envia SENTINEL."""
    monkeypatch.setattr("src.ai_vision.orchestrator.filas", filas_teste)

    from src.ai_vision.orchestrator import Orchestrator

    log_msgs: list[str] = []
    concluido = threading.Event()

    orch = Orchestrator(
        on_log=lambda msg: log_msgs.append(msg),
        on_asset=lambda a: None,
        on_concluido=lambda n: concluido.set(),
    )

    enfileirados = orch.analisar_pasta_local(tmp_path)
    assert enfileirados == 0

    orch.iniciar()
    assert concluido.wait(timeout=5.0)

    assert any("Nenhum asset para analisar" in m for m in log_msgs), f"Esperava aviso de fila vazia. Logs: {log_msgs}"


@pytest.mark.integration
def test_reanalise_diretorio_inexistente(filas_teste, mock_glib, monkeypatch, tmp_path):
    """Diretório inexistente retorna 0 e loga erro, sem crash."""
    monkeypatch.setattr("src.ai_vision.orchestrator.filas", filas_teste)

    from src.ai_vision.orchestrator import Orchestrator

    log_msgs: list[str] = []
    orch = Orchestrator(
        on_log=lambda msg: log_msgs.append(msg),
        on_asset=lambda a: None,
        on_concluido=lambda n: None,
    )

    inexistente = tmp_path / "nao-existe"
    enfileirados = orch.analisar_pasta_local(inexistente)

    assert enfileirados == 0
    assert any("Diretório inexistente" in m for m in log_msgs), log_msgs


@pytest.mark.integration
def test_reanalise_varredura_recursiva(filas_teste, mock_glib, mock_analisar, mock_paleta, monkeypatch, tmp_path):
    """rglob deve encontrar imagens em subpastas."""
    monkeypatch.setattr("src.ai_vision.orchestrator.filas", filas_teste)

    from src.ai_vision.orchestrator import Orchestrator

    sub = tmp_path / "subpasta"
    sub.mkdir()
    (tmp_path / "topo.png").write_bytes(b"fake")
    (sub / "filho.webp").write_bytes(b"fake")

    orch = Orchestrator(
        on_log=lambda msg: None,
        on_asset=lambda a: None,
        on_concluido=lambda n: None,
    )
    enfileirados = orch.analisar_pasta_local(tmp_path)
    assert enfileirados == 2


# "Quem observa com paciência vê o que os apressados perdem." — Sêneca
