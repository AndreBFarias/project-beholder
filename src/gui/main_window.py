"""
Janela principal do Project Beholder.

Estrutura:
- Adw.ApplicationWindow
- Gtk.Box vertical: HeaderBar + NavigationSplitView + StatusBar
- NavigationSplitView: Sidebar (esquerda) + Stack de páginas (direita)

Regra ADR-01: NUNCA atualizar widgets diretamente de threads.
Sempre usar GLib.idle_add(callback, dados).
"""

import logging

from gi.repository import Adw, Gtk

from src.gui.pages.busca import CacadaPage
from src.gui.pages.cortex import CortexPage
from src.gui.pages.espolio import EspolioPage
from src.gui.pages.grimorio import GrimorioPage
from src.gui.pages.protocolo import ProtocoloPage
from src.gui.sidebar import Sidebar
from src.gui.theme import apply_theme
from src.gui.widgets import StatusBar

logger = logging.getLogger("beholder.gui.main_window")


class BeholderWindow(Adw.ApplicationWindow):
    """Janela principal do Beholder."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_title("Project Beholder")
        self.set_default_size(1100, 700)
        apply_theme()
        self._definir_icone()
        self._build_ui()
        logger.info("Janela principal iniciada")

    def _definir_icone(self) -> None:
        """Define o ícone da janela via icon name (instalado pelo install.sh)."""
        self.set_icon_name("com.beholder.app")

    def _build_ui(self) -> None:
        # Container principal vertical
        caixa_principal = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Header bar
        headerbar = Adw.HeaderBar()
        headerbar.set_show_end_title_buttons(True)
        caixa_principal.append(headerbar)

        # Área central: sidebar + conteúdo
        area_central = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        area_central.set_vexpand(True)

        # Páginas do conteúdo
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP_DOWN)
        self._stack.set_transition_duration(150)

        self._paginas: dict[str, Gtk.Widget] = {
            "cacada": CacadaPage(),
            "cortex": CortexPage(),
            "espolio": EspolioPage(),
            "protocolo": ProtocoloPage(),
            "grimorio": GrimorioPage(),
        }

        # Conectar Córtex → Espólio (BUG-05)
        self._paginas["cortex"].conectar_espolio(self._paginas["espolio"])
        # Conectar Busca → Córtex (pipeline automático)
        self._paginas["cacada"].conectar_cortex(self._paginas["cortex"])

        for modulo_id, pagina in self._paginas.items():
            self._stack.add_named(pagina, modulo_id)

        # Sidebar
        self._sidebar = Sidebar(on_modulo_selecionado=self._on_modulo_selecionado)

        area_central.append(self._sidebar)
        area_central.append(self._stack)

        caixa_principal.append(area_central)

        # Barra de status no rodapé
        self._status_bar = StatusBar()
        caixa_principal.append(self._status_bar)

        self.set_content(caixa_principal)

        # Conectar StatusBar a todas as páginas que a utilizam
        for pagina in self._paginas.values():
            if hasattr(pagina, "conectar_status_bar"):
                pagina.conectar_status_bar(self._status_bar)

        # Selecionar Caçada como página inicial
        self._stack.set_visible_child_name("cacada")

    def _on_modulo_selecionado(self, modulo_id: str) -> None:
        """Troca a página visível no stack ao selecionar item da sidebar."""
        if self._stack.get_child_by_name(modulo_id):
            self._stack.set_visible_child_name(modulo_id)
            logger.debug("Módulo selecionado: %s", modulo_id)
