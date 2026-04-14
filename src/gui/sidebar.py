"""
Sidebar de navegação do Project Beholder.

Usa Gtk.ListBox para os 5 módulos + separador + Grimório.
O header exibe a logo circular (beholder-icon.png), título e tagline.
"""

import logging
from collections.abc import Callable
from pathlib import Path

from gi.repository import GdkPixbuf, Gtk

from src.gui.theme import (
    DRACULA_COMMENT,
    DRACULA_CYAN,
    DRACULA_GREEN,
    DRACULA_ORANGE,
    DRACULA_PINK,
    DRACULA_PURPLE,
)

logger = logging.getLogger("beholder.gui.sidebar")

LOGO_PATH = Path("beholder-icon.png")
LOGO_SIZE = 40

# Definição dos itens da sidebar: (id, nome, descrição, cor, ícone adwaita)
ITENS_SIDEBAR = [
    ("cacada", "Cacada", "extração de assets", DRACULA_PURPLE, "system-search-symbolic"),
    ("cortex", "Cortex", "visão IA local", DRACULA_PINK, "preferences-system-symbolic"),
    ("espolio", "Espolio", "exportação .zip + CSV", DRACULA_GREEN, "folder-download-symbolic"),
    ("protocolo", "Protocolo", "execução em lote", DRACULA_ORANGE, "view-list-symbolic"),
]

ITEM_GRIMORIO = ("grimorio", "Grimorio", "configurações", DRACULA_CYAN, "accessories-text-editor-symbolic")


def _criar_item_sidebar(
    nome: str,
    descricao: str,
    cor: str,
    icone_name: str,
) -> Gtk.ListBoxRow:
    """Cria uma linha da sidebar com ícone, nome e descrição."""
    row = Gtk.ListBoxRow()
    row.add_css_class("nav-row")

    caixa = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    caixa.set_margin_top(6)
    caixa.set_margin_bottom(6)
    caixa.set_margin_start(4)
    caixa.set_margin_end(4)

    # Ícone Adwaita symbolic
    icone = Gtk.Image.new_from_icon_name(icone_name)
    icone.set_pixel_size(16)
    caixa.append(icone)

    # Textos
    textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
    lbl_nome = Gtk.Label(label=nome.upper())
    lbl_nome.set_xalign(0)
    lbl_nome.set_markup(f'<span foreground="{cor}" weight="bold" size="small">{nome.upper()}</span>')

    lbl_desc = Gtk.Label(label=descricao)
    lbl_desc.set_xalign(0)
    lbl_desc.set_markup(f'<span foreground="{DRACULA_COMMENT}" size="x-small">{descricao}</span>')

    textos.append(lbl_nome)
    textos.append(lbl_desc)
    caixa.append(textos)

    row.set_child(caixa)
    return row


class Sidebar(Gtk.Box):
    """
    Sidebar de navegação lateral.

    Ao selecionar um item, chama on_modulo_selecionado(modulo_id: str).
    """

    def __init__(self, on_modulo_selecionado: Callable[[str], None]) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add_css_class("sidebar")
        self.set_size_request(200, -1)
        self._callback = on_modulo_selecionado
        self._ids: list[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        self._build_header()
        self._build_lista()

    def _build_header(self) -> None:
        """Cria o header com logo, título e tagline."""
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        header.add_css_class("sidebar-header")

        # Logo circular
        logo_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        logo_box.set_margin_top(4)

        if LOGO_PATH.exists():
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(LOGO_PATH), LOGO_SIZE, LOGO_SIZE, True)
                logo_img = Gtk.Image.new_from_pixbuf(pixbuf)
                logo_img.set_size_request(LOGO_SIZE, LOGO_SIZE)
            except Exception:
                logo_img = Gtk.Image.new_from_icon_name("image-missing")
        else:
            logo_img = Gtk.Image.new_from_icon_name("application-x-executable")

        logo_img.set_pixel_size(LOGO_SIZE)

        textos_header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_titulo = Gtk.Label()
        lbl_titulo.set_markup(
            f'<span foreground="{DRACULA_PURPLE}" weight="bold" size="small" letter_spacing="2048">BEHOLDER</span>'
        )
        lbl_titulo.set_xalign(0)

        lbl_tagline = Gtk.Label()
        lbl_tagline.set_markup(f'<span foreground="{DRACULA_COMMENT}" size="x-small">motor de predação visual</span>')
        lbl_tagline.set_xalign(0)

        textos_header.append(lbl_titulo)
        textos_header.append(lbl_tagline)

        logo_box.append(logo_img)
        logo_box.append(textos_header)
        header.append(logo_box)

        self.append(header)

    def _build_lista(self) -> None:
        """Cria a ListBox com os módulos e o separador antes do Grimório."""
        self._listbox = Gtk.ListBox()
        self._listbox.add_css_class("nav-listbox")
        self._listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._listbox.connect("row-selected", self._on_row_selected)
        self._listbox.set_vexpand(True)

        for modulo_id, nome, descricao, cor, icone in ITENS_SIDEBAR:
            row = _criar_item_sidebar(nome, descricao, cor, icone)
            self._listbox.append(row)
            self._ids.append(modulo_id)

        # Separador visual antes do Grimório
        sep_row = Gtk.ListBoxRow()
        sep_row.set_selectable(False)
        sep_row.set_activatable(False)
        sep_row.set_child(Gtk.Separator())
        self._listbox.append(sep_row)
        self._ids.append(None)  # placeholder para o separador

        # Grimório
        grim_id, grim_nome, grim_desc, grim_cor, grim_icone = ITEM_GRIMORIO
        row_grim = _criar_item_sidebar(grim_nome, grim_desc, grim_cor, grim_icone)
        self._listbox.append(row_grim)
        self._ids.append(grim_id)

        self.append(self._listbox)

        # Selecionar primeiro item (Caçada) por padrão
        primeira_row = self._listbox.get_row_at_index(0)
        if primeira_row:
            self._listbox.select_row(primeira_row)

    def _on_row_selected(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        """Dispara callback quando usuário seleciona um módulo."""
        if row is None:
            return
        idx = row.get_index()
        if idx < len(self._ids) and self._ids[idx] is not None:
            self._callback(self._ids[idx])
