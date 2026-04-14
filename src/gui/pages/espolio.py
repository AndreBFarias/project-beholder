"""
Módulo Espólio — Sprint 1: estrutura visual completa, sem backend conectado.

Controles:
- GERAR PACOTE: organiza assets e cria .zip + CSV
- ABRIR PASTA: xdg-open output/
- EXPORTAR CSV: diálogo de salvamento
- LIMPAR SESSÃO: confirmação obrigatória
"""

import logging

from gi.repository import Gtk

logger = logging.getLogger("beholder.gui.espolio")


class EspolioPage(Gtk.Box):
    """Página do módulo Espólio."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self._build_ui()

    def _build_ui(self) -> None:
        # Título
        titulo = Gtk.Label(label="Espólio")
        titulo.add_css_class("page-title")
        titulo.set_xalign(0)
        self.append(titulo)

        subtitulo = Gtk.Label(label="Exportação de Pacotes")
        subtitulo.add_css_class("section-title")
        subtitulo.set_xalign(0)
        self.append(subtitulo)

        self.append(Gtk.Separator())

        # Resumo da sessão
        resumo_frame = Gtk.Frame(label="Sessão Atual")
        resumo_grid = Gtk.Grid()
        resumo_grid.set_row_spacing(6)
        resumo_grid.set_column_spacing(16)
        resumo_grid.set_margin_top(8)
        resumo_grid.set_margin_bottom(8)
        resumo_grid.set_margin_start(8)
        resumo_grid.set_margin_end(8)

        labels_info = [
            ("Assets brutos:", "0"),
            ("Assets processados:", "0"),
            ("Ícones:", "0"),
            ("Fundos:", "0"),
            ("Outros:", "0"),
        ]

        self._labels_valores: dict[str, Gtk.Label] = {}
        for i, (chave, valor) in enumerate(labels_info):
            lbl_chave = Gtk.Label(label=chave)
            lbl_chave.add_css_class("section-title")
            lbl_chave.set_xalign(1)

            lbl_valor = Gtk.Label(label=valor)
            lbl_valor.set_xalign(0)
            self._labels_valores[chave] = lbl_valor

            resumo_grid.attach(lbl_chave, 0, i, 1, 1)
            resumo_grid.attach(lbl_valor, 1, i, 1, 1)

        resumo_frame.set_child(resumo_grid)
        self.append(resumo_frame)

        # Ações de exportação
        acoes_frame = Gtk.Frame(label="Ações")
        acoes_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        acoes_box.set_margin_top(8)
        acoes_box.set_margin_bottom(8)
        acoes_box.set_margin_start(8)
        acoes_box.set_margin_end(8)

        row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._btn_gerar = Gtk.Button(label="GERAR PACOTE")
        self._btn_gerar.add_css_class("btn-primary")

        self._btn_abrir_pasta = Gtk.Button(label="ABRIR PASTA")
        self._btn_abrir_pasta.add_css_class("btn-secondary")

        self._btn_exportar_csv = Gtk.Button(label="EXPORTAR CSV")
        self._btn_exportar_csv.add_css_class("btn-secondary")

        row1.append(self._btn_gerar)
        row1.append(self._btn_abrir_pasta)
        row1.append(self._btn_exportar_csv)

        row2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._btn_limpar = Gtk.Button(label="LIMPAR SESSÃO")
        self._btn_limpar.add_css_class("btn-danger")
        row2.append(self._btn_limpar)

        acoes_box.append(row1)
        acoes_box.append(row2)
        acoes_frame.set_child(acoes_box)
        self.append(acoes_frame)

        # Lista de pacotes gerados
        historico_frame = Gtk.Frame(label="Pacotes Gerados")
        hist_scroll = Gtk.ScrolledWindow()
        hist_scroll.set_vexpand(True)
        hist_scroll.set_min_content_height(150)

        self._label_historico = Gtk.Label(label="Nenhum pacote gerado nesta sessão.")
        self._label_historico.add_css_class("section-title")
        self._label_historico.set_vexpand(True)
        self._label_historico.set_valign(Gtk.Align.CENTER)

        hist_scroll.set_child(self._label_historico)
        historico_frame.set_child(hist_scroll)
        self.append(historico_frame)
