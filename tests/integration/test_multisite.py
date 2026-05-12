"""
Testes de integração — protocolo multi-site (Sprint 19).

Valida:
- site_registry resolve domínios conhecidos para suas estratégias.
- Fallback para GenericStrategy em domínios desconhecidos.
- PinterestStrategy promove thumbnails para /originals/.
- DribbbleStrategy remove sufixos _1x/_2x.
- Packer gera layout híbrido {categoria}/{site}/ no ZIP.
- CSV contém coluna site_origem.
"""

import csv
import zipfile
from queue import Queue
from unittest.mock import MagicMock, patch

import pytest

from src.core.asset_queue import SENTINEL, AssetProcessado


@pytest.mark.integration
def test_registry_resolve_pinterest():
    from src.scraper.site_registry import resolver_strategy
    from src.scraper.site_strategies import PinterestStrategy

    strategy = resolver_strategy("https://www.pinterest.com/pin/123")
    assert isinstance(strategy, PinterestStrategy)
    assert strategy.nome == "pinterest"


@pytest.mark.integration
def test_registry_resolve_dribbble():
    from src.scraper.site_registry import resolver_strategy
    from src.scraper.site_strategies import DribbbleStrategy

    strategy = resolver_strategy("https://dribbble.com/shots/42")
    assert isinstance(strategy, DribbbleStrategy)


@pytest.mark.integration
def test_registry_resolve_behance():
    from src.scraper.site_registry import resolver_strategy
    from src.scraper.site_strategies import BehanceStrategy

    strategy = resolver_strategy("https://www.behance.net/gallery/abc")
    assert isinstance(strategy, BehanceStrategy)


@pytest.mark.integration
def test_registry_resolve_freepik():
    from src.scraper.site_registry import resolver_strategy
    from src.scraper.site_strategies import FreepikStrategy

    strategy = resolver_strategy("https://flaticon.com/free-icon/menu_123")
    assert isinstance(strategy, FreepikStrategy)


@pytest.mark.integration
def test_registry_fallback_generic():
    from src.scraper.site_registry import resolver_strategy
    from src.scraper.site_strategies import GenericStrategy

    strategy = resolver_strategy("https://meu-site-pessoal.dev/galeria")
    assert isinstance(strategy, GenericStrategy)
    assert strategy.nome == "generic"


@pytest.mark.integration
def test_registry_fallback_url_invalida():
    from src.scraper.site_registry import resolver_strategy
    from src.scraper.site_strategies import GenericStrategy

    strategy = resolver_strategy("")
    assert isinstance(strategy, GenericStrategy)


@pytest.mark.integration
def test_pinterest_promove_thumbnail():
    from src.scraper.site_strategies import PinterestStrategy

    html = '<html><body><img src="https://i.pinimg.com/236x/aa/bb/cc/pin.jpg"></body></html>'
    assets = PinterestStrategy().extrair_assets(html, "https://pinterest.com/")
    assert len(assets) == 1
    assert "/originals/" in assets[0].url
    assert "/236x/" not in assets[0].url


@pytest.mark.integration
def test_dribbble_remove_sufixo_thumb():
    from src.scraper.site_strategies import DribbbleStrategy

    html = '<html><body><img src="https://cdn.dribbble.com/shot_1x.png"></body></html>'
    assets = DribbbleStrategy().extrair_assets(html, "https://dribbble.com/")
    assert len(assets) == 1
    assert "_1x" not in assets[0].url
    assert assets[0].url.endswith("shot.png")


@pytest.mark.integration
def test_freepik_sugere_categoria_icon():
    from src.core.asset_queue import AssetBruto
    from src.scraper.site_strategies import FreepikStrategy

    asset = AssetBruto(
        url="https://cdn.flaticon.com/png/512/menu.png",
        caminho_local="",
        tipo="image",
        origem="https://flaticon.com/search",
    )
    assert FreepikStrategy().categoria_sugerida(asset) == "icon"


@pytest.mark.integration
def test_packer_gera_layout_hibrido(tmp_path, monkeypatch):
    """ZIP final organiza em {categoria}/{site}/arquivo.ext."""
    from src.core.asset_queue import FilasPipeline

    filas_teste = FilasPipeline()
    monkeypatch.setattr("src.exporter.packer.filas", filas_teste)

    # Força output para dentro do tmp_path
    from src.core.config.defaults import DEFAULTS

    orig_output = DEFAULTS["Saida"]["diretorio_output"]
    DEFAULTS["Saida"]["diretorio_output"] = str(tmp_path / "output")

    try:
        # Cria arquivos fonte
        src_dir = tmp_path / "fontes"
        src_dir.mkdir()
        arq_pinterest = src_dir / "pin.png"
        arq_pinterest.write_bytes(b"fake-png")
        arq_dribbble = src_dir / "shot.jpg"
        arq_dribbble.write_bytes(b"fake-jpg")

        assets = [
            AssetProcessado(
                url_original="https://pinterest.com/pin",
                caminho_local=str(arq_pinterest),
                tipo="icon",
                descricao="ícone de teste",
                tags=["teste"],
                paleta_hex=["#fff"],
                timestamp="2026-04-17T00:00:00+00:00",
                site_origem="pinterest",
            ),
            AssetProcessado(
                url_original="https://dribbble.com/shot",
                caminho_local=str(arq_dribbble),
                tipo="background",
                descricao="fundo de teste",
                tags=["fundo"],
                paleta_hex=["#000"],
                timestamp="2026-04-17T00:00:00+00:00",
                site_origem="dribbble",
            ),
        ]

        for a in assets:
            filas_teste.processada.put(a)
        filas_teste.processada.put(SENTINEL)

        from src.exporter.packer import Packer

        concluido_caminhos: list[str] = []

        # Mock GLib para chamar callbacks diretamente
        monkeypatch.setattr(
            "src.exporter.packer.GLib.idle_add",
            lambda fn, *args: fn(*args),
        )

        packer = Packer(
            on_log=lambda _m: None,
            on_concluido=lambda caminho: concluido_caminhos.append(caminho),
        )
        # Força _PROJECT_ROOT dentro do tmp — DEFAULTS já aponta para tmp/output
        packer._dir_output = tmp_path / "output"
        packer.iniciar()
        packer._thread.join(timeout=10.0)

        assert concluido_caminhos, "Packer não chamou on_concluido"
        zip_path = concluido_caminhos[0]
        assert zip_path, "Packer retornou caminho vazio"

        with zipfile.ZipFile(zip_path, "r") as zf:
            nomes = zf.namelist()
            # Layout híbrido: categoria/site/arquivo
            assert "ícones/pinterest/pin.png" in nomes, f"Nomes no ZIP: {nomes}"
            assert "fundos/dribbble/shot.jpg" in nomes, f"Nomes no ZIP: {nomes}"
            assert "metadata.csv" in nomes

            # CSV contém site_origem
            with zf.open("metadata.csv") as f:
                linhas = list(csv.DictReader(f.read().decode("utf-8").splitlines()))
            assert linhas[0]["site_origem"] in {"pinterest", "dribbble"}
            assert {linha["site_origem"] for linha in linhas} == {"pinterest", "dribbble"}

    finally:
        DEFAULTS["Saida"]["diretorio_output"] = orig_output


# "Pertencer a um lugar é também dar-lhe um nome." — Martin Heidegger
