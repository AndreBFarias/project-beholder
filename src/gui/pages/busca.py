"""
Módulo Busca — Extração de assets de interface.

Controles:
- Campo URL + botão INICIAR + toggle FURTIVO
- Log em tempo real (LogTerminal) via GLib.idle_add
- Barra de progresso
- PAUSAR (toggle) e CANCELAR durante scraping

ADR-01: todos os callbacks de UI chamados via GLib.idle_add pelo StealthSpider.
"""

import logging

from gi.repository import Gtk

from src.gui.widgets import LogTerminal
from src.scraper.stealth_spider import StealthSpider

logger = logging.getLogger("beholder.gui.cacada")


class CacadaPage(Gtk.Box):
    """Página do módulo Caçada."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self._spider = StealthSpider(
            on_log=self._cb_log,
            on_progresso=self._cb_progresso,
            on_concluido=self._cb_concluido,
        )
        self._build_ui()

    def _build_ui(self) -> None:
        # Título da página
        titulo = Gtk.Label(label="Busca")
        titulo.add_css_class("page-title")
        titulo.set_xalign(0)
        self.append(titulo)

        subtitulo = Gtk.Label(label="Extração de Assets")
        subtitulo.add_css_class("section-title")
        subtitulo.set_xalign(0)
        self.append(subtitulo)

        self.append(Gtk.Separator())

        # URL + controles de execução
        url_frame = Gtk.Frame(label="Alvo")
        url_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        url_box.set_margin_top(8)
        url_box.set_margin_bottom(8)
        url_box.set_margin_start(8)
        url_box.set_margin_end(8)

        url_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._entry_url = Gtk.Entry()
        self._entry_url.set_placeholder_text("https://exemplo.com")
        self._entry_url.set_hexpand(True)
        url_row.append(self._entry_url)
        url_box.append(url_row)

        # Botões de ação
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_row.set_margin_top(4)

        self._btn_iniciar = Gtk.Button(label="INICIAR")
        self._btn_iniciar.add_css_class("btn-primary")
        self._btn_iniciar.connect("clicked", self._on_iniciar)

        self._btn_pausar = Gtk.Button(label="PAUSAR")
        self._btn_pausar.add_css_class("btn-warning")
        self._btn_pausar.set_visible(False)
        self._btn_pausar.connect("clicked", self._on_pausar)

        self._btn_cancelar = Gtk.Button(label="CANCELAR")
        self._btn_cancelar.add_css_class("btn-danger")
        self._btn_cancelar.set_visible(False)
        self._btn_cancelar.connect("clicked", self._on_cancelar)

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
        prog_frame = Gtk.Frame(label="Progresso")
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
        log_frame = Gtk.Frame(label="Log")
        self._log_terminal = LogTerminal()
        log_frame.set_child(self._log_terminal)
        self.append(log_frame)

    # ------------------------------------------------------------------
    # Handlers de botão
    # ------------------------------------------------------------------

    def _on_iniciar(self, _btn: Gtk.Button) -> None:
        """Valida URL e inicia o StealthSpider."""
        url = self._entry_url.get_text().strip()
        if not url:
            self._log_terminal.append_line("[AVISO] Insira uma URL antes de iniciar.")
            return
        if not url.startswith(("http://", "https://")):
            self._log_terminal.append_line("[AVISO] URL deve começar com http:// ou https://")
            return

        self._log_terminal.limpar()
        self._progresso.set_fraction(0.0)
        self._progresso.set_text("Iniciando...")
        self._btn_iniciar.set_visible(False)
        self._btn_iniciar.set_sensitive(False)
        self._btn_pausar.set_visible(True)
        self._btn_pausar.set_label("PAUSAR")
        self._btn_cancelar.set_visible(True)
        self._entry_url.set_sensitive(False)

        modo_furtivo = self._toggle_furtivo.get_active()
        self._spider.iniciar(url, modo_furtivo=modo_furtivo)
        logger.info("Caçada iniciada: %s (furtivo=%s)", url, modo_furtivo)

    def _on_pausar(self, _btn: Gtk.Button) -> None:
        """Alterna entre pausar e retomar o spider."""
        if self._spider.esta_pausado():
            self._spider.retomar()
            self._btn_pausar.set_label("PAUSAR")
        else:
            self._spider.pausar()
            self._btn_pausar.set_label("RETOMAR")

    def _on_cancelar(self, _btn: Gtk.Button) -> None:
        """Cancela o spider e restaura o estado inicial da UI."""
        self._spider.cancelar()
        # A UI é restaurada pelo callback _cb_concluido quando a thread encerrar

    # ------------------------------------------------------------------
    # Callbacks de UI — chamados via GLib.idle_add pelo StealthSpider (ADR-01)
    # ------------------------------------------------------------------

    def _cb_log(self, msg: str) -> None:
        """Recebe linha de log da thread e atualiza o terminal."""
        self._log_terminal.append_line(msg)

    def _cb_progresso(self, fracao: float, texto: str) -> None:
        """Recebe atualização de progresso da thread."""
        self._progresso.set_fraction(max(0.0, min(1.0, fracao)))
        self._progresso.set_text(texto)

    def _cb_concluido(self, total: int) -> None:
        """Restaura a UI ao estado inicial após o término do scraping."""
        self._btn_iniciar.set_visible(True)
        self._btn_iniciar.set_sensitive(True)
        self._btn_pausar.set_visible(False)
        self._btn_cancelar.set_visible(False)
        self._entry_url.set_sensitive(True)
        logger.info("Caçada concluída — %d assets", total)
