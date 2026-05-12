"""
Testes de recuperação de site_origem em ANALISAR PASTA (Sprint 21).

Valida:
- AssetBruto.site_origem_hint preserva o site ao reprocessar pasta.
- _construir_mapa_sites lê metadata.csv antigo e mapeia caminho_local → site.
- Prioridade: CSV > subpasta > "local" (vira generic).
- Orchestrator respeita o hint em vez de resolver_strategy("local").
"""

import copy
import csv
import threading
import unittest.mock as mock
from pathlib import Path

import pytest

from src.core.asset_queue import SENTINEL, FilasPipeline
from src.core.config.defaults import DEFAULTS


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
    resultado = {
        "tipo": "icon",
        "descricao": "ícone de teste",
        "tags": ["a", "b", "c", "d", "e"],
    }
    monkeypatch.setattr(
        "src.ai_vision.orchestrator.analisar_imagem",
        mock.MagicMock(return_value=resultado),
    )


@pytest.fixture
def mock_paleta(monkeypatch):
    monkeypatch.setattr(
        "src.ai_vision.orchestrator.extrair_paleta",
        mock.MagicMock(return_value=["#fff"]),
    )


@pytest.fixture
def cfg_saida_backup():
    snap = copy.deepcopy(DEFAULTS["Saida"])
    yield
    DEFAULTS["Saida"].clear()
    DEFAULTS["Saida"].update(copy.deepcopy(snap))


# ------------------------------------------------------------------
# Parte 1: AssetBruto + orchestrator respeitam hint
# ------------------------------------------------------------------


@pytest.mark.integration
def test_hint_preservado_em_asset_processado(
    filas_teste, mock_glib, mock_analisar, mock_paleta, monkeypatch, tmp_path
):
    """Orchestrator deve usar site_origem_hint em vez de resolver_strategy('local')."""
    monkeypatch.setattr("src.ai_vision.orchestrator.filas", filas_teste)

    from src.ai_vision.orchestrator import Orchestrator
    from src.core.asset_queue import AssetBruto

    arq = tmp_path / "icon.png"
    arq.write_bytes(b"fake")

    asset = AssetBruto(
        url=arq.as_uri(),
        caminho_local=str(arq),
        tipo="image",
        origem="local",
        site_origem_hint="pinterest",
    )
    filas_teste.scraper.put(asset)
    filas_teste.scraper.put(SENTINEL)

    recebidos: list = []
    concluido = threading.Event()

    orch = Orchestrator(
        on_log=lambda _m: None,
        on_asset=lambda a: recebidos.append(a),
        on_concluido=lambda _n: concluido.set(),
    )
    orch.iniciar()
    assert concluido.wait(timeout=10.0)

    assert len(recebidos) == 1
    assert recebidos[0].site_origem == "pinterest"


@pytest.mark.integration
def test_sem_hint_usa_resolver_strategy(
    filas_teste, mock_glib, mock_analisar, mock_paleta, monkeypatch, tmp_path
):
    """Sem hint, fallback para resolver_strategy(origem). 'local' vira 'generic'."""
    monkeypatch.setattr("src.ai_vision.orchestrator.filas", filas_teste)

    from src.ai_vision.orchestrator import Orchestrator
    from src.core.asset_queue import AssetBruto

    arq = tmp_path / "x.png"
    arq.write_bytes(b"fake")

    asset = AssetBruto(
        url=arq.as_uri(),
        caminho_local=str(arq),
        tipo="image",
        origem="local",
        site_origem_hint=None,
    )
    filas_teste.scraper.put(asset)
    filas_teste.scraper.put(SENTINEL)

    recebidos: list = []
    concluido = threading.Event()

    orch = Orchestrator(
        on_log=lambda _m: None,
        on_asset=lambda a: recebidos.append(a),
        on_concluido=lambda _n: concluido.set(),
    )
    orch.iniciar()
    assert concluido.wait(timeout=10.0)

    assert recebidos[0].site_origem == "generic"


# ------------------------------------------------------------------
# Parte 2: _construir_mapa_sites
# ------------------------------------------------------------------


@pytest.mark.integration
def test_construir_mapa_sites_le_csv_na_pasta(filas_teste, tmp_path):
    """CSV na mesma pasta vira fonte de site_origem."""
    from src.ai_vision.orchestrator import Orchestrator

    # Cria estrutura: tmp/arq.png + tmp/antigo.csv
    arq = tmp_path / "shot.jpg"
    arq.write_bytes(b"fake")

    csv_path = tmp_path / "antigo.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["caminho_local", "site_origem", "url_original", "tipo", "descricao", "tags", "paleta_hex", "timestamp"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "caminho_local": str(arq),
                "site_origem": "dribbble",
                "url_original": "https://dribbble.com/shot/x",
                "tipo": "photo",
                "descricao": "teste",
                "tags": "a|b",
                "paleta_hex": "#fff",
                "timestamp": "",
            }
        )

    orch = Orchestrator(
        on_log=lambda _m: None,
        on_asset=lambda _a: None,
        on_concluido=lambda _n: None,
    )
    mapa = orch._construir_mapa_sites(tmp_path)
    assert str(arq.resolve()) in mapa
    assert mapa[str(arq.resolve())] == "dribbble"


@pytest.mark.integration
def test_construir_mapa_sites_ignora_generic(tmp_path):
    """Linhas com site_origem='generic' não poluem o mapa."""
    from src.ai_vision.orchestrator import Orchestrator

    arq = tmp_path / "x.png"
    arq.write_bytes(b"fake")

    csv_path = tmp_path / "meta.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["caminho_local", "site_origem"],
        )
        writer.writeheader()
        writer.writerow({"caminho_local": str(arq), "site_origem": "generic"})

    orch = Orchestrator(
        on_log=lambda _m: None,
        on_asset=lambda _a: None,
        on_concluido=lambda _n: None,
    )
    assert orch._construir_mapa_sites(tmp_path) == {}


@pytest.mark.integration
def test_construir_mapa_sites_ignora_csv_sem_coluna(tmp_path):
    """CSV sem coluna 'caminho_local' é ignorado silenciosamente."""
    from src.ai_vision.orchestrator import Orchestrator

    csv_path = tmp_path / "errado.csv"
    csv_path.write_text("a,b,c\n1,2,3\n", encoding="utf-8")

    orch = Orchestrator(
        on_log=lambda _m: None,
        on_asset=lambda _a: None,
        on_concluido=lambda _n: None,
    )
    assert orch._construir_mapa_sites(tmp_path) == {}


# ------------------------------------------------------------------
# Parte 3: prioridade CSV > subpasta > local
# ------------------------------------------------------------------


@pytest.mark.integration
def test_prioridade_csv_sobre_subpasta(filas_teste, monkeypatch, tmp_path):
    """Arquivo em subpasta 'pinterest/' mas mapeado no CSV como 'behance' → vale CSV."""
    monkeypatch.setattr("src.ai_vision.orchestrator.filas", filas_teste)

    from src.ai_vision.orchestrator import Orchestrator

    sub = tmp_path / "pinterest"
    sub.mkdir()
    arq = sub / "a.png"
    arq.write_bytes(b"fake")

    csv_path = tmp_path / "meta.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["caminho_local", "site_origem"])
        writer.writeheader()
        writer.writerow({"caminho_local": str(arq), "site_origem": "behance"})

    orch = Orchestrator(
        on_log=lambda _m: None,
        on_asset=lambda _a: None,
        on_concluido=lambda _n: None,
    )
    orch.analisar_pasta_local(tmp_path)

    # Pega o primeiro AssetBruto da fila (antes do SENTINEL)
    item = filas_teste.scraper.get(timeout=1.0)
    assert item.site_origem_hint == "behance", "CSV deve ter prioridade sobre subpasta"


@pytest.mark.integration
def test_subpasta_como_fallback(filas_teste, monkeypatch, tmp_path):
    """Sem CSV relevante, nome da subpasta vira o hint."""
    monkeypatch.setattr("src.ai_vision.orchestrator.filas", filas_teste)

    from src.ai_vision.orchestrator import Orchestrator

    sub = tmp_path / "dribbble"
    sub.mkdir()
    arq = sub / "shot.png"
    arq.write_bytes(b"fake")

    orch = Orchestrator(
        on_log=lambda _m: None,
        on_asset=lambda _a: None,
        on_concluido=lambda _n: None,
    )
    orch.analisar_pasta_local(tmp_path)

    item = filas_teste.scraper.get(timeout=1.0)
    assert item.site_origem_hint == "dribbble"


@pytest.mark.integration
def test_arquivo_no_topo_sem_csv_sem_hint(filas_teste, monkeypatch, tmp_path):
    """Arquivo direto no diretório raiz (sem subpasta) e sem CSV → hint=None."""
    monkeypatch.setattr("src.ai_vision.orchestrator.filas", filas_teste)

    from src.ai_vision.orchestrator import Orchestrator

    arq = tmp_path / "topo.png"
    arq.write_bytes(b"fake")

    orch = Orchestrator(
        on_log=lambda _m: None,
        on_asset=lambda _a: None,
        on_concluido=lambda _n: None,
    )
    orch.analisar_pasta_local(tmp_path)

    item = filas_teste.scraper.get(timeout=1.0)
    assert item.site_origem_hint is None


# ------------------------------------------------------------------
# Parte 4: Packer preserva cópia do CSV em output/
# ------------------------------------------------------------------


@pytest.mark.integration
def test_packer_preserva_csv_externo(tmp_path, monkeypatch, cfg_saida_backup):
    """Packer salva cópia do CSV em output/metadata_{timestamp}.csv para recuperação."""
    from src.core.asset_queue import AssetProcessado, FilasPipeline
    from src.exporter.packer import Packer

    filas_pkg = FilasPipeline()
    monkeypatch.setattr("src.exporter.packer.filas", filas_pkg)
    monkeypatch.setattr("src.exporter.packer.GLib.idle_add", lambda fn, *a: fn(*a))

    DEFAULTS["Saida"]["diretorio_output"] = str(tmp_path / "saida")

    src_img = tmp_path / "src.png"
    src_img.write_bytes(b"fake")

    asset = AssetProcessado(
        url_original="https://pinterest.com/pin",
        caminho_local=str(src_img),
        tipo="icon",
        descricao="teste",
        tags=["t"],
        paleta_hex=["#fff"],
        timestamp="2026-04-17T00:00:00+00:00",
        site_origem="pinterest",
    )
    filas_pkg.processada.put(asset)
    filas_pkg.processada.put(SENTINEL)

    concluido: list[str] = []
    packer = Packer(
        on_log=lambda _m: None,
        on_concluido=lambda c: concluido.append(c),
    )
    packer._dir_output = tmp_path / "saida"
    packer.iniciar()
    packer._thread.join(timeout=10.0)

    assert concluido
    # Deve existir algum metadata_*.csv em saida/
    csvs_externos = list((tmp_path / "saida").glob("metadata_*.csv"))
    assert csvs_externos, "Packer deve salvar cópia do CSV fora do ZIP"

    # Esse CSV deve ter o site_origem correto
    with csvs_externos[0].open(encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    assert linhas[0]["site_origem"] == "pinterest"


# "Lembrar é outra forma de viver." — Clarice Lispector
