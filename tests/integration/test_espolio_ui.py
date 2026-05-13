"""
Testes da UI do Espólio (Sprint 20).

Valida:
- Helper `_criar_card_asset_espolio` gera widget com descrição e tags.
- `registrar_asset` substitui placeholder por card real.
- LIMPAR SESSÃO restaura placeholder.
- Tags aparecem como chips individuais.
"""

import gi

gi.require_version("Gtk", "4.0")

import pytest  # noqa: E402
from gi.repository import Gtk  # noqa: E402

from src.core.asset_queue import AssetProcessado  # noqa: E402


def _coletar_texto(widget):
    """Coleta recursivamente text labels de um widget para inspeção."""
    textos = []
    if isinstance(widget, Gtk.Label):
        textos.append(widget.get_label())
    filho = widget.get_first_child() if hasattr(widget, "get_first_child") else None
    while filho is not None:
        textos.extend(_coletar_texto(filho))
        filho = filho.get_next_sibling()
    return textos


@pytest.mark.integration
def test_card_asset_mostra_descricao_completa():
    from src.gui.pages.espolio import _criar_card_asset_espolio

    asset = AssetProcessado(
        url_original="https://pinterest.com/pin/abc",
        caminho_local="/tmp/engrenagem.png",
        tipo="icon",
        descricao=(
            "Ícone vetorial de engrenagem em traço fino monocromático. "
            "Representa configurações em interfaces mobile minimalistas."
        ),
        tags=["engrenagem", "configuração", "minimalista", "monocromático", "interface", "mobile"],
        paleta_hex=["#000000", "#ffffff"],
        timestamp="2026-04-17T12:00:00+00:00",
        site_origem="pinterest",
    )

    row = _criar_card_asset_espolio(asset)
    textos = _coletar_texto(row)
    textos_join = " ".join(textos)

    # Descrição completa presente (não truncada)
    assert "Representa configurações" in textos_join
    assert "minimalista" in textos_join

    # Todas as 6 tags aparecem como chips
    for tag in asset.tags:
        assert f"#{tag}" in textos, f"Tag '{tag}' não apareceu como chip"

    # Badge de tipo e site
    assert "[ICON]" in textos_join
    assert "@pinterest" in textos_join


@pytest.mark.integration
def test_card_sem_tags_mostra_placeholder():
    from src.gui.pages.espolio import _criar_card_asset_espolio

    asset = AssetProcessado(
        url_original="x",
        caminho_local="/tmp/x.png",
        tipo="other",
        descricao="sem tags neste",
        tags=[],
        paleta_hex=[],
        timestamp="",
        site_origem="generic",
    )
    row = _criar_card_asset_espolio(asset)
    textos = " ".join(_coletar_texto(row))
    assert "(sem tags)" in textos


@pytest.mark.integration
def test_registrar_asset_remove_placeholder_e_adiciona_card():
    from src.gui.pages.espolio import EspolioPage

    page = EspolioPage()

    # Antes: placeholder presente
    placeholder_inicial = page._row_placeholder_assets
    assert placeholder_inicial is not None

    asset = AssetProcessado(
        url_original="https://dribbble.com/shot",
        caminho_local="/tmp/shot.jpg",
        tipo="background",
        descricao="fundo gradiente em tons púrpura e rosa para uso em hero section.",
        tags=["gradiente", "púrpura", "rosa", "hero", "fundo", "abstrato"],
        paleta_hex=["#bd93f9", "#ff79c6"],
        timestamp="",
        site_origem="dribbble",
    )
    page.registrar_asset(asset)

    # Placeholder deve ter sido removido
    assert page._row_placeholder_assets is None
    # Pelo menos um filho no listbox
    assert page._listbox_assets.get_first_child() is not None

    # Texto do asset deve aparecer
    textos = " ".join(_coletar_texto(page._listbox_assets))
    assert "gradiente" in textos
    assert "@dribbble" in textos


@pytest.mark.integration
def test_limpar_lista_assets_restaura_placeholder():
    from src.gui.pages.espolio import EspolioPage

    page = EspolioPage()
    asset = AssetProcessado(
        url_original="x",
        caminho_local="/tmp/x.png",
        tipo="icon",
        descricao="teste",
        tags=["a"],
        paleta_hex=[],
        timestamp="",
        site_origem="generic",
    )
    page.registrar_asset(asset)
    assert page._row_placeholder_assets is None

    page._limpar_lista_assets()

    assert page._row_placeholder_assets is not None
    # Placeholder deve ter texto que menciona Córtex
    textos = " ".join(_coletar_texto(page._listbox_assets))
    assert "Córtex" in textos or "Nenhum asset" in textos


# "Os detalhes fazem a perfeição, e perfeição não é um detalhe." — Leonardo da Vinci
