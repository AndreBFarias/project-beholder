"""
Tema Dracula para o Project Beholder via Gtk.CssProvider.

Define as constantes de cor e gera o CSS aplicado globalmente na aplicação.
"""

from gi.repository import Gdk, Gtk

# Paleta Dracula — spec.draculatheme.com
DRACULA_BG = "#282a36"
DRACULA_CURRENT = "#44475a"  # Selection
DRACULA_FG = "#f8f8f2"
DRACULA_COMMENT = "#6272a4"
DRACULA_PURPLE = "#bd93f9"
DRACULA_PINK = "#ff79c6"
DRACULA_GREEN = "#50fa7b"
DRACULA_ORANGE = "#ffb86c"
DRACULA_CYAN = "#8be9fd"
DRACULA_RED = "#ff5555"
DRACULA_YELLOW = "#f1fa8c"

# ANSI Normal
DRACULA_ANSI_BLACK = "#21222c"

# ANSI Bright — usados para hover e estados interativos
DRACULA_BRIGHT_RED = "#ff6e6e"
DRACULA_BRIGHT_GREEN = "#69ff94"
DRACULA_BRIGHT_YELLOW = "#ffffa5"
DRACULA_BRIGHT_BLUE = "#d6acff"
DRACULA_BRIGHT_MAGENTA = "#ff92df"
DRACULA_BRIGHT_CYAN = "#a4ffff"
DRACULA_BRIGHT_WHITE = "#ffffff"

CSS_DRACULA = f"""
window,
.main-window {{
    background-color: {DRACULA_BG};
    color: {DRACULA_FG};
}}
headerbar {{
    background-color: {DRACULA_ANSI_BLACK};
    border-bottom: 1px solid {DRACULA_CURRENT};
    color: {DRACULA_FG};
}}
.sidebar {{
    background-color: {DRACULA_ANSI_BLACK};
    border-right: 1px solid {DRACULA_CURRENT};
}}
.sidebar-header {{
    padding: 16px 12px 8px 12px;
    border-bottom: 1px solid {DRACULA_CURRENT};
}}
.project-title {{
    color: {DRACULA_PURPLE};
    font-weight: bold;
    font-size: 16px;
}}
.project-tagline {{
    color: {DRACULA_COMMENT};
    font-size: 14px;
}}
.sidebar-module-name {{
    font-size: 14px;
    font-weight: bold;
}}
.sidebar-module-desc {{
    font-size: 13px;
}}
listbox,
.nav-listbox {{
    background-color: {DRACULA_ANSI_BLACK};
}}
listbox row,
.nav-row {{
    padding: 10px 14px;
    border-left: 3px solid transparent;
    background-color: transparent;
    color: {DRACULA_FG};
}}
listbox row:selected,
.nav-row:selected {{
    background-color: {DRACULA_BG};
    border-left-color: {DRACULA_PURPLE};
    color: {DRACULA_PURPLE};
}}
listbox row:hover,
.nav-row:hover {{
    background-color: {DRACULA_CURRENT};
}}
.status-bar {{
    background-color: {DRACULA_ANSI_BLACK};
    border-top: 1px solid {DRACULA_CURRENT};
    padding: 5px 12px;
    font-family: monospace;
    font-size: 15px;
    color: {DRACULA_COMMENT};
}}
.status-dot-ativo {{
    color: {DRACULA_GREEN};
    font-weight: bold;
}}
.status-dot-pausado {{
    color: {DRACULA_ORANGE};
    font-weight: bold;
}}
.status-dot-erro {{
    color: {DRACULA_RED};
    font-weight: bold;
}}
.status-dot-concluido {{
    color: {DRACULA_CYAN};
    font-weight: bold;
}}
.status-dot-aviso {{
    color: {DRACULA_YELLOW};
    font-weight: bold;
}}
.btn-primary {{
    background-color: {DRACULA_PURPLE};
    color: {DRACULA_BG};
    font-weight: bold;
    border-radius: 6px;
    border: none;
    padding: 9px 22px;
}}
.btn-primary:hover {{
    background-color: {DRACULA_BRIGHT_BLUE};
}}
.btn-primary:disabled {{
    background-color: {DRACULA_CURRENT};
    color: {DRACULA_COMMENT};
}}
.btn-secondary {{
    background-color: {DRACULA_CURRENT};
    color: {DRACULA_CYAN};
    border-radius: 6px;
    border: 1px solid {DRACULA_COMMENT};
    padding: 9px 22px;
}}
.btn-secondary:hover {{
    background-color: {DRACULA_COMMENT};
}}
.btn-danger {{
    background-color: {DRACULA_RED};
    color: {DRACULA_FG};
    border-radius: 6px;
    border: none;
    padding: 9px 22px;
    font-weight: bold;
}}
.btn-danger:hover {{
    background-color: {DRACULA_BRIGHT_RED};
}}
.btn-warning {{
    background-color: {DRACULA_ORANGE};
    color: {DRACULA_BG};
    border-radius: 6px;
    border: none;
    padding: 9px 22px;
    font-weight: bold;
}}
.log-terminal {{
    background-color: {DRACULA_ANSI_BLACK};
    color: {DRACULA_GREEN};
    font-family: monospace;
    font-size: 14px;
    border-radius: 6px;
    padding: 8px;
    border: 1px solid {DRACULA_CURRENT};
}}
textview,
textview text {{
    background-color: {DRACULA_ANSI_BLACK};
    color: {DRACULA_GREEN};
    font-family: monospace;
    font-size: 14px;
}}
entry {{
    background-color: {DRACULA_ANSI_BLACK};
    color: {DRACULA_FG};
    border: 1px solid {DRACULA_CURRENT};
    border-radius: 5px;
    padding: 6px 10px;
}}
entry:focus {{
    border-color: {DRACULA_PURPLE};
}}
progressbar trough {{
    background-color: {DRACULA_CURRENT};
    border-radius: 3px;
}}
progressbar progress {{
    background-color: {DRACULA_PURPLE};
    border-radius: 3px;
}}
separator {{
    background-color: {DRACULA_CURRENT};
    min-height: 1px;
}}
scale trough {{
    background-color: {DRACULA_CURRENT};
}}
scale highlight {{
    background-color: {DRACULA_PURPLE};
}}
switch {{
    background-color: {DRACULA_CURRENT};
}}
switch:checked {{
    background-color: {DRACULA_GREEN};
}}
label.page-title {{
    color: {DRACULA_FG};
    font-size: 24px;
    font-weight: bold;
}}
label.section-title {{
    color: {DRACULA_COMMENT};
    font-size: 14px;
    font-weight: bold;
}}
frame {{
    border: 1px solid {DRACULA_CURRENT};
    border-radius: 6px;
}}
frame > label {{
    color: {DRACULA_COMMENT};
    font-size: 14px;
    font-weight: bold;
}}
treeview {{
    background-color: {DRACULA_ANSI_BLACK};
    color: {DRACULA_FG};
    font-size: 13px;
}}
treeview > row {{
    background-color: {DRACULA_ANSI_BLACK};
    color: {DRACULA_FG};
}}
treeview > row:selected {{
    background-color: {DRACULA_CURRENT};
    color: {DRACULA_FG};
}}
treeview > header > button {{
    background-color: {DRACULA_ANSI_BLACK};
    color: {DRACULA_COMMENT};
    border-bottom: 1px solid {DRACULA_CURRENT};
    font-size: 13px;
}}
columnview {{
    background-color: {DRACULA_ANSI_BLACK};
    color: {DRACULA_FG};
}}
"""


def apply_theme() -> None:
    """Aplica o tema Dracula globalmente via Gtk.StyleContext.

    load_from_string() só existe no PyGObject >= 3.50 (GTK 4.12+).
    Ubuntu 22.04 tem PyGObject 3.48 — usar load_from_data(bytes).
    """
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS_DRACULA.encode("utf-8"))
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
