"""
Módulo Grimório — Sprint 1: estrutura visual completa, sem backend conectado.

Seções:
- Scraper: timeouts, delays, jitter, retries
- IA: porta Ollama, modelo, timeout de análise
- Saída: diretório output, K-Means cores
- Ações: SALVAR, TESTAR OLLAMA, RESTAURAR PADRÕES, ABRIR LOGS
"""

import logging

from gi.repository import Gtk

logger = logging.getLogger("beholder.gui.grimorio")


def _criar_linha_config(label_texto: str, valor_padrao: str) -> tuple[Gtk.Box, Gtk.Entry]:
    """Cria uma linha label + entry para configuração."""
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    lbl = Gtk.Label(label=label_texto)
    lbl.add_css_class("section-title")
    lbl.set_xalign(0)
    lbl.set_size_request(180, -1)

    entry = Gtk.Entry()
    entry.set_text(valor_padrao)
    entry.set_hexpand(True)

    row.append(lbl)
    row.append(entry)
    return row, entry


class GrimorioPage(Gtk.Box):
    """Página do módulo Grimório (configurações)."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self._build_ui()

    def _build_ui(self) -> None:
        # Título
        titulo = Gtk.Label(label="GRIMORIO")
        titulo.add_css_class("page-title")
        titulo.set_xalign(0)
        self.append(titulo)

        subtitulo = Gtk.Label(label="CONFIGURACOES")
        subtitulo.add_css_class("section-title")
        subtitulo.set_xalign(0)
        self.append(subtitulo)

        self.append(Gtk.Separator())

        # Área scrollável para as seções de config
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        conteudo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        conteudo.set_margin_top(8)
        conteudo.set_margin_bottom(8)

        # Seção Scraper
        scraper_frame = Gtk.Frame(label="SCRAPER")
        scraper_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        scraper_box.set_margin_top(8)
        scraper_box.set_margin_bottom(8)
        scraper_box.set_margin_start(8)
        scraper_box.set_margin_end(8)

        row_timeout, self._entry_timeout = _criar_linha_config("Timeout (s):", "30")
        row_delay_min, self._entry_delay_min = _criar_linha_config("Delay mínimo (s):", "1.0")
        row_delay_max, self._entry_delay_max = _criar_linha_config("Delay máximo (s):", "3.0")
        row_retries, self._entry_retries = _criar_linha_config("Máx. tentativas:", "3")

        scraper_box.append(row_timeout)
        scraper_box.append(row_delay_min)
        scraper_box.append(row_delay_max)
        scraper_box.append(row_retries)
        scraper_frame.set_child(scraper_box)
        conteudo.append(scraper_frame)

        # Seção IA
        ia_frame = Gtk.Frame(label="INTELIGENCIA ARTIFICIAL")
        ia_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        ia_box.set_margin_top(8)
        ia_box.set_margin_bottom(8)
        ia_box.set_margin_start(8)
        ia_box.set_margin_end(8)

        row_porta, self._entry_porta = _criar_linha_config("Porta Ollama:", "11435")
        row_modelo, self._entry_modelo = _criar_linha_config("Modelo:", "moondream")
        row_timeout_ia, self._entry_timeout_ia = _criar_linha_config("Timeout análise (s):", "60")

        ia_box.append(row_porta)
        ia_box.append(row_modelo)
        ia_box.append(row_timeout_ia)
        ia_frame.set_child(ia_box)
        conteudo.append(ia_frame)

        # Seção Saída
        saida_frame = Gtk.Frame(label="SAIDA")
        saida_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        saida_box.set_margin_top(8)
        saida_box.set_margin_bottom(8)
        saida_box.set_margin_start(8)
        saida_box.set_margin_end(8)

        row_output, self._entry_output = _criar_linha_config("Diretório de saída:", "output")
        row_kmeans, self._entry_kmeans = _criar_linha_config("Cores K-Means:", "4")

        saida_box.append(row_output)
        saida_box.append(row_kmeans)
        saida_frame.set_child(saida_box)
        conteudo.append(saida_frame)

        scroll.set_child(conteudo)
        self.append(scroll)

        # Ações
        acoes_frame = Gtk.Frame(label="ACOES")
        acoes_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        acoes_box.set_margin_top(8)
        acoes_box.set_margin_bottom(8)
        acoes_box.set_margin_start(8)
        acoes_box.set_margin_end(8)

        self._btn_salvar = Gtk.Button(label="SALVAR")
        self._btn_salvar.add_css_class("btn-primary")

        self._btn_testar = Gtk.Button(label="TESTAR OLLAMA")
        self._btn_testar.add_css_class("btn-secondary")

        self._btn_restaurar = Gtk.Button(label="RESTAURAR PADROES")
        self._btn_restaurar.add_css_class("btn-warning")

        self._btn_logs = Gtk.Button(label="ABRIR LOGS")
        self._btn_logs.add_css_class("btn-secondary")

        acoes_box.append(self._btn_salvar)
        acoes_box.append(self._btn_testar)
        acoes_box.append(self._btn_restaurar)
        acoes_box.append(self._btn_logs)
        acoes_frame.set_child(acoes_box)
        self.append(acoes_frame)
