"""
Módulo Caçada — Sprint 1: estrutura visual completa, sem backend conectado.

Controles:
- Campo URL + botão INICIAR + toggle FURTIVO
- Log em tempo real (LogTerminal)
- Barra de progresso
- Botões PAUSAR e CANCELAR (aparecem durante scraping)
"""

import logging

from gi.repository import Gtk

from src.gui.widgets import LogTerminal

logger = logging.getLogger("beholder.gui.cacada")


class CacadaPage(Gtk.Box):
    """Página do módulo Caçada."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self._build_ui()

    def _build_ui(self) -> None:
        # Título da página
        titulo = Gtk.Label(label="CACADA")
        titulo.add_css_class("page-title")
        titulo.set_xalign(0)
        self.append(titulo)

        subtitulo = Gtk.Label(label="EXTRAÇÃO DE ASSETS")
        subtitulo.add_css_class("section-title")
        subtitulo.set_xalign(0)
        self.append(subtitulo)

        self.append(Gtk.Separator())

        # URL + controles de execução
        url_frame = Gtk.Frame(label="ALVO")
        url_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        url_box.set_margin_top(8)
        url_box.set_margin_bottom(8)
        url_box.set_margin_start(8)
        url_box.set_margin_end(8)

        # Campo URL
        url_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._entry_url = Gtk.Entry()
        self._entry_url.set_placeholder_text("https://exemplo.com")
        self._entry_url.set_hexpand(True)
        url_row.append(self._entry_url)
        url_box.append(url_row)

        # Botões de ação
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self._btn_iniciar = Gtk.Button(label="INICIAR")
        self._btn_iniciar.add_css_class("btn-primary")
        self._btn_iniciar.connect("clicked", self._on_iniciar)

        self._btn_pausar = Gtk.Button(label="PAUSAR")
        self._btn_pausar.add_css_class("btn-warning")
        self._btn_pausar.set_visible(False)

        self._btn_cancelar = Gtk.Button(label="CANCELAR")
        self._btn_cancelar.add_css_class("btn-danger")
        self._btn_cancelar.set_visible(False)

        # Toggle FURTIVO
        furtivo_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        furtivo_label = Gtk.Label(label="FURTIVO")
        furtivo_label.add_css_class("section-title")
        self._toggle_furtivo = Gtk.Switch()
        self._toggle_furtivo.set_valign(Gtk.Align.CENTER)
        furtivo_box.append(furtivo_label)
        furtivo_box.append(self._toggle_furtivo)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)

        btn_row.append(self._btn_iniciar)
        btn_row.append(self._btn_pausar)
        btn_row.append(self._btn_cancelar)
        btn_row.append(spacer)
        btn_row.append(furtivo_box)
        url_box.append(btn_row)

        url_frame.set_child(url_box)
        self.append(url_frame)

        # Barra de progresso
        prog_frame = Gtk.Frame(label="PROGRESSO")
        prog_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        prog_box.set_margin_top(8)
        prog_box.set_margin_bottom(8)
        prog_box.set_margin_start(8)
        prog_box.set_margin_end(8)

        self._progresso = Gtk.ProgressBar()
        self._progresso.set_fraction(0.0)
        self._progresso.set_show_text(True)
        self._progresso.set_text("Aguardando...")

        prog_box.append(self._progresso)
        prog_frame.set_child(prog_box)
        self.append(prog_frame)

        # Terminal de log
        log_frame = Gtk.Frame(label="LOG")
        self._log_terminal = LogTerminal()
        log_frame.set_child(self._log_terminal)
        self.append(log_frame)

    def _on_iniciar(self, _btn: Gtk.Button) -> None:
        """Placeholder — backend será conectado na Sprint 3."""
        url = self._entry_url.get_text().strip()
        if not url:
            self._log_terminal.append_line("[AVISO] Insira uma URL antes de iniciar.")
            return
        self._log_terminal.append_line(f"[INFO] Iniciando caçada: {url}")
        self._btn_iniciar.set_visible(False)
        self._btn_pausar.set_visible(True)
        self._btn_cancelar.set_visible(True)
        self._progresso.set_text("Conectando...")
