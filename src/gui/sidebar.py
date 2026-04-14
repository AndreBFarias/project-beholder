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
LOGO_SIZE = 80

# Definição dos itens da sidebar: (id, nome, descrição, cor, ícone adwaita)
ITENS_SIDEBAR = [
    ("cacada", "Busca", "Extração de Assets", DRACULA_PURPLE, "system-search-symbolic"),
    ("cortex", "Córtex", "Visão IA Local", DRACULA_PINK, "preferences-system-symbolic"),
    ("espolio", "Espólio", "Exportação .zip + CSV", DRACULA_GREEN, "folder-download-symbolic"),
    ("protocolo", "Protocolo", "Execução em Lote", DRACULA_ORANGE, "view-list-symbolic"),
]

ITEM_GRIMORIO = ("grimorio", "Grimório", "Configurações", DRACULA_CYAN, "accessories-text-editor-symbolic")


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
    icone.set_pixel_size(18)
    caixa.append(icone)

    # Textos
    textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    lbl_nome = Gtk.Label(label=nome)
    lbl_nome.set_xalign(0)
    lbl_nome.add_css_class("sidebar-module-name")
    lbl_nome.set_markup(f'<span foreground="{cor}" weight="bold">{nome}</span>')

    lbl_desc = Gtk.Label(label=descricao)
    lbl_desc.set_xalign(0)
    lbl_desc.add_css_class("sidebar-module-desc")
    lbl_desc.set_markup(f'<span foreground="{DRACULA_COMMENT}">{descricao}</span>')

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
        self.set_size_request(240, -1)
        self._callback = on_modulo_selecionado
        self._ids: list[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        self._build_header()
        self._build_lista()

    def _build_header(self) -> None:
        """Cria o header com logo centralizada, título e tagline abaixo."""
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        header.add_css_class("sidebar-header")

        # Logo centralizada
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
        logo_img.set_halign(Gtk.Align.CENTER)
        logo_img.set_margin_top(10)

        # Título BEHOLDER abaixo da logo
        lbl_titulo = Gtk.Label()
        lbl_titulo.set_markup(
            f'<span foreground="{DRACULA_PURPLE}" weight="bold" letter_spacing="2048">Beholder</span>'
        )
        lbl_titulo.add_css_class("project-title")
        lbl_titulo.set_halign(Gtk.Align.CENTER)

        # Tagline abaixo do título
        lbl_tagline = Gtk.Label()
        lbl_tagline.set_markup(f'<span foreground="{DRACULA_COMMENT}">Motor de predação visual</span>')
        lbl_tagline.add_css_class("project-tagline")
        lbl_tagline.set_halign(Gtk.Align.CENTER)
        lbl_tagline.set_margin_bottom(4)

        header.append(logo_img)
        header.append(lbl_titulo)
        header.append(lbl_tagline)

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
