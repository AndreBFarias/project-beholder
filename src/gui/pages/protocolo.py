"""
Módulo Protocolo — Sprint 1: estrutura visual completa, sem backend conectado.

Controles:
- Lista de URLs com status (pendente/em progresso/concluída/erro)
- ADICIONAR URL: valida e adiciona à fila
- IMPORTAR LISTA: carrega .txt com URLs
- EXECUTAR LOTE: processa sequencialmente
- RETOMAR SESSÃO: reconstrói estado do checkpoint
"""

import logging

from gi.repository import Gtk

logger = logging.getLogger("beholder.gui.protocolo")

# Colunas do modelo de lista
COL_URL = 0
COL_STATUS = 1


class ProtocoloPage(Gtk.Box):
    """Página do módulo Protocolo."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self._build_ui()

    def _build_ui(self) -> None:
        # Título
        titulo = Gtk.Label(label="PROTOCOLO")
        titulo.add_css_class("page-title")
        titulo.set_xalign(0)
        self.append(titulo)

        subtitulo = Gtk.Label(label="EXECUCAO EM LOTE")
        subtitulo.add_css_class("section-title")
        subtitulo.set_xalign(0)
        self.append(subtitulo)

        self.append(Gtk.Separator())

        # Adicionar URL individual
        add_frame = Gtk.Frame(label="ADICIONAR URL")
        add_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        add_box.set_margin_top(8)
        add_box.set_margin_bottom(8)
        add_box.set_margin_start(8)
        add_box.set_margin_end(8)

        self._entry_nova_url = Gtk.Entry()
        self._entry_nova_url.set_placeholder_text("https://exemplo.com")
        self._entry_nova_url.set_hexpand(True)

        self._btn_adicionar = Gtk.Button(label="ADICIONAR")
        self._btn_adicionar.add_css_class("btn-primary")
        self._btn_adicionar.connect("clicked", self._on_adicionar)

        self._btn_importar = Gtk.Button(label="IMPORTAR LISTA")
        self._btn_importar.add_css_class("btn-secondary")

        add_box.append(self._entry_nova_url)
        add_box.append(self._btn_adicionar)
        add_box.append(self._btn_importar)
        add_frame.set_child(add_box)
        self.append(add_frame)

        # Lista de URLs
        lista_frame = Gtk.Frame(label="FILA DE URLS")
        lista_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lista_box.set_margin_top(8)
        lista_box.set_margin_bottom(8)
        lista_box.set_margin_start(8)
        lista_box.set_margin_end(8)

        # Modelo de dados: (url, status)
        self._store = Gtk.ListStore(str, str)

        self._treeview = Gtk.TreeView(model=self._store)
        self._treeview.set_vexpand(True)

        col_url = Gtk.TreeViewColumn("URL", Gtk.CellRendererText(), text=COL_URL)
        col_url.set_expand(True)
        self._treeview.append_column(col_url)

        col_status = Gtk.TreeViewColumn("Status", Gtk.CellRendererText(), text=COL_STATUS)
        col_status.set_min_width(120)
        self._treeview.append_column(col_status)

        lista_scroll = Gtk.ScrolledWindow()
        lista_scroll.set_vexpand(True)
        lista_scroll.set_min_content_height(200)
        lista_scroll.set_child(self._treeview)

        lista_box.append(lista_scroll)
        lista_frame.set_child(lista_box)
        self.append(lista_frame)

        # Controles de execução do lote
        ctrl_frame = Gtk.Frame(label="CONTROLE DO LOTE")
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ctrl_box.set_margin_top(8)
        ctrl_box.set_margin_bottom(8)
        ctrl_box.set_margin_start(8)
        ctrl_box.set_margin_end(8)

        self._btn_executar = Gtk.Button(label="EXECUTAR LOTE")
        self._btn_executar.add_css_class("btn-primary")

        self._btn_retomar = Gtk.Button(label="RETOMAR SESSAO")
        self._btn_retomar.add_css_class("btn-warning")

        self._btn_limpar_lista = Gtk.Button(label="LIMPAR LISTA")
        self._btn_limpar_lista.add_css_class("btn-danger")
        self._btn_limpar_lista.connect("clicked", self._on_limpar_lista)

        ctrl_box.append(self._btn_executar)
        ctrl_box.append(self._btn_retomar)
        ctrl_box.append(self._btn_limpar_lista)
        ctrl_frame.set_child(ctrl_box)
        self.append(ctrl_frame)

    def _on_adicionar(self, _btn: Gtk.Button) -> None:
        """Adiciona URL à fila com status 'pendente'."""
        url = self._entry_nova_url.get_text().strip()
        if not url:
            return
        if not url.startswith(("http://", "https://")):
            return
        self._store.append([url, "pendente"])
        self._entry_nova_url.set_text("")

    def _on_limpar_lista(self, _btn: Gtk.Button) -> None:
        """Limpa todas as URLs da lista."""
        self._store.clear()
