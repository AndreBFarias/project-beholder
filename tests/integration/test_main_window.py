"""
Testes de integração — main_window wiring (Sprint 22.7).

Garante que o wiring entre páginas continua íntegro:
- BeholderWindow instancia sem erro.
- Córtex está conectado ao Espólio (bug histórico BUG-05).
- Busca está conectada ao Córtex (pipeline automático).
- Todas as páginas recebem conectar_status_bar.
- ListBox de assets do Espólio existe e aceita cards novos via registrar_asset.
- Mudar de página via sidebar funciona.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

import pytest  # noqa: E402
from gi.repository import Adw  # noqa: E402

from src.core.asset_queue import AssetProcessado  # noqa: E402

Adw.init()


@pytest.fixture
def window():
    from src.gui.main_window import BeholderWindow

    return BeholderWindow()


@pytest.mark.integration
def test_main_window_instancia(window):
    assert window is not None
    assert set(window._paginas.keys()) == {"cacada", "cortex", "espolio", "protocolo", "grimorio"}


@pytest.mark.integration
def test_cortex_conectado_ao_espolio(window):
    cortex = window._paginas["cortex"]
    espolio = window._paginas["espolio"]
    assert cortex._espolio is espolio, "BUG-05 reapareceu: Córtex não está conectado ao Espólio"


@pytest.mark.integration
def test_busca_conectada_ao_cortex(window):
    busca = window._paginas["cacada"]
    cortex = window._paginas["cortex"]
    assert busca._cortex_page is cortex, "Pipeline automático quebrado: Busca sem referência ao Córtex"


@pytest.mark.integration
def test_status_bar_conectada_em_todas_paginas(window):
    status_bar = window._status_bar
    for nome, pagina in window._paginas.items():
        if hasattr(pagina, "_status_bar"):
            assert pagina._status_bar is status_bar, f"{nome} sem status bar conectada"


@pytest.mark.integration
def test_registrar_asset_propaga_do_cortex_ao_espolio(window):
    """Quando Cortex chama registrar_asset, Espólio recebe e exibe o card."""
    cortex = window._paginas["cortex"]
    espolio = window._paginas["espolio"]

    asset = AssetProcessado(
        url_original="https://pinterest.com/pin",
        caminho_local="/tmp/nonexistent.png",
        tipo="icon",
        descricao="um ícone de teste para validar integração",
        tags=["teste", "integração", "main_window"],
        paleta_hex=["#fff"],
        timestamp="",
        site_origem="pinterest",
    )
    # Chamada real do caminho do Cortex (_cb_asset_processado encaminha para espolio)
    cortex._cb_asset_processado(asset)

    assert len(espolio._assets) == 1
    assert espolio._row_placeholder_assets is None, "Placeholder deveria ter sido removido"

    # Descrição aparece no listbox
    filho = espolio._listbox_assets.get_first_child()
    assert filho is not None, "Nenhum card adicionado ao listbox do Espólio"


@pytest.mark.integration
def test_troca_de_pagina_via_sidebar(window):
    window._on_modulo_selecionado("espolio")
    assert window._stack.get_visible_child_name() == "espolio"

    window._on_modulo_selecionado("grimorio")
    assert window._stack.get_visible_child_name() == "grimorio"

    # Nome inválido não troca nem lança
    atual = window._stack.get_visible_child_name()
    window._on_modulo_selecionado("inexistente")
    assert window._stack.get_visible_child_name() == atual


# "Arquitetura é a decisão de onde colocar o remendo para que o tecido inteiro sustente." — adaptado
