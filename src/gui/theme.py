"""
Tema Dracula para o Project Beholder via Gtk.CssProvider.

Define as constantes de cor e gera o CSS aplicado globalmente na aplicação.
"""

from gi.repository import Gdk, Gtk

# Paleta Dracula completa
DRACULA_BG = "#282a36"
DRACULA_CURRENT = "#44475a"
DRACULA_FG = "#f8f8f2"
DRACULA_COMMENT = "#6272a4"
DRACULA_PURPLE = "#bd93f9"
DRACULA_PINK = "#ff79c6"
DRACULA_GREEN = "#50fa7b"
DRACULA_ORANGE = "#ffb86c"
DRACULA_CYAN = "#8be9fd"
DRACULA_RED = "#ff5555"
DRACULA_YELLOW = "#f1fa8c"

CSS_DRACULA = f"""
window,
.main-window {{
    background-color: {DRACULA_BG};
    color: {DRACULA_FG};
}}
headerbar {{
    background-color: #21222c;
    border-bottom: 1px solid {DRACULA_CURRENT};
    color: {DRACULA_FG};
}}
.sidebar {{
    background-color: #21222c;
    border-right: 1px solid {DRACULA_CURRENT};
}}
.sidebar-header {{
    padding: 16px 12px 8px 12px;
    border-bottom: 1px solid {DRACULA_CURRENT};
}}
.project-title {{
    color: {DRACULA_PURPLE};
    font-weight: bold;
    font-size: 13px;
    letter-spacing: 2px;
}}
.project-tagline {{
    color: {DRACULA_COMMENT};
    font-size: 10px;
}}
listbox,
.nav-listbox {{
    background-color: #21222c;
}}
listbox row,
.nav-row {{
    padding: 8px 12px;
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
    background-color: #1e1f29;
    border-top: 1px solid {DRACULA_CURRENT};
    padding: 4px 12px;
    font-family: monospace;
    font-size: 11px;
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
.btn-primary {{
    background-color: {DRACULA_PURPLE};
    color: {DRACULA_BG};
    font-weight: bold;
    border-radius: 5px;
    border: none;
    padding: 6px 16px;
}}
.btn-primary:hover {{
    background-color: #caa4ff;
}}
.btn-primary:disabled {{
    background-color: {DRACULA_CURRENT};
    color: {DRACULA_COMMENT};
}}
.btn-secondary {{
    background-color: {DRACULA_CURRENT};
    color: {DRACULA_CYAN};
    border-radius: 5px;
    border: 1px solid {DRACULA_COMMENT};
    padding: 6px 16px;
}}
.btn-secondary:hover {{
    background-color: #555770;
}}
.btn-danger {{
    background-color: {DRACULA_RED};
    color: {DRACULA_FG};
    border-radius: 5px;
    border: none;
    padding: 6px 16px;
    font-weight: bold;
}}
.btn-danger:hover {{
    background-color: #ff7777;
}}
.btn-warning {{
    background-color: {DRACULA_ORANGE};
    color: {DRACULA_BG};
    border-radius: 5px;
    border: none;
    padding: 6px 16px;
    font-weight: bold;
}}
.log-terminal {{
    background-color: #1e1f29;
    color: {DRACULA_GREEN};
    font-family: monospace;
    font-size: 11px;
    border-radius: 6px;
    padding: 8px;
    border: 1px solid {DRACULA_CURRENT};
}}
textview,
textview text {{
    background-color: #1e1f29;
    color: {DRACULA_GREEN};
    font-family: monospace;
    font-size: 11px;
}}
entry {{
    background-color: #21222c;
    color: {DRACULA_FG};
    border: 1px solid {DRACULA_CURRENT};
    border-radius: 5px;
    padding: 6px 10px;
}}
entry:focus {{
    border-color: {DRACULA_PURPLE};
    box-shadow: 0 0 0 2px rgba(189, 147, 249, 0.2);
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
    font-size: 16px;
    font-weight: bold;
}}
label.section-title {{
    color: {DRACULA_COMMENT};
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}}
frame {{
    border: 1px solid {DRACULA_CURRENT};
    border-radius: 6px;
}}
frame > label {{
    color: {DRACULA_COMMENT};
    font-size: 11px;
}}
"""


def apply_theme() -> None:
    """Aplica o tema Dracula globalmente via Gtk.StyleContext."""
    provider = Gtk.CssProvider()
    provider.load_from_string(CSS_DRACULA)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
