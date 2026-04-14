"""
Widgets reutilizáveis do Project Beholder.

Regra fundamental (ADR-01): NUNCA chamar métodos destes widgets diretamente
de threads. Sempre usar GLib.idle_add(widget.metodo, args).
"""

import logging

from gi.repository import Gtk

logger = logging.getLogger("beholder.widgets")


class StatusBar(Gtk.Box):
    """
    Barra de status global exibida no rodapé da janela principal.

    Formato:  estado | X / Y (Z%) | VRAM: W GB | sessão: S

    IMPORTANTE: Chamar update() apenas via GLib.idle_add() quando em threads.
    """

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.add_css_class("status-bar")
        self._build_ui()

    def _build_ui(self) -> None:
        self._label_status = Gtk.Label(label=" nova")
        self._label_status.add_css_class("status-dot-ativo")
        self._label_status.set_xalign(0)

        self._label_progresso = Gtk.Label(label="0 / 0 (0%)")
        self._label_progresso.set_xalign(0)

        self._label_vram = Gtk.Label(label="VRAM: -- GB")
        self._label_vram.set_xalign(0)

        self._label_sessao = Gtk.Label(label="sessão: nova")
        self._label_sessao.set_xalign(0)

        sep1 = Gtk.Label(label="|")
        sep1.add_css_class("section-title")
        sep2 = Gtk.Label(label="|")
        sep2.add_css_class("section-title")
        sep3 = Gtk.Label(label="|")
        sep3.add_css_class("section-title")

        self.append(self._label_status)
        self.append(sep1)
        self.append(self._label_progresso)
        self.append(sep2)
        self.append(self._label_vram)
        self.append(sep3)
        self.append(self._label_sessao)

    def update(
        self,
        status: str = "nova",
        baixados: int = 0,
        total: int = 0,
        vram_gb: float | None = None,
        sessao: str = "nova",
    ) -> None:
        """
        Atualiza todos os campos da barra de status.

        Args:
            status: Estado atual ("nova", "ativa", "pausada", "concluída", "erro")
            baixados: Assets baixados até agora
            total: Total estimado de assets
            vram_gb: VRAM em uso em GB (None = desconhecido)
            sessao: Descrição do estado da sessão
        """
        percentual = int(baixados / total * 100) if total > 0 else 0

        icone = ""
        css_class = "status-dot-ativo"
        if status == "pausada":
            css_class = "status-dot-pausado"
        elif status in ("erro", "cancelada"):
            css_class = "status-dot-erro"
        elif status == "concluída":
            css_class = "status-dot-concluido"

        self._label_status.set_label(f"{icone} {status}")
        self._label_status.remove_css_class("status-dot-ativo")
        self._label_status.remove_css_class("status-dot-pausado")
        self._label_status.remove_css_class("status-dot-erro")
        self._label_status.remove_css_class("status-dot-concluido")
        self._label_status.add_css_class(css_class)

        self._label_progresso.set_label(f"{baixados} / {total} ({percentual}%)")

        vram_str = f"{vram_gb:.1f} GB" if vram_gb is not None else "-- GB"
        self._label_vram.set_label(f"VRAM: {vram_str}")

        self._label_sessao.set_label(f"sessão: {sessao}")


class LogTerminal(Gtk.ScrolledWindow):
    """
    Terminal de log em tempo real — TextView append-only com auto-scroll.

    IMPORTANTE: Chamar append_line() apenas via GLib.idle_add() quando em threads.
    """

    MAX_LINHAS = 500  # Evita crescimento ilimitado do buffer

    def __init__(self) -> None:
        super().__init__()
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.set_min_content_height(200)
        self._build_ui()

    def _build_ui(self) -> None:
        self._textview = Gtk.TextView()
        self._textview.set_editable(False)
        self._textview.set_cursor_visible(False)
        self._textview.add_css_class("log-terminal")
        self._textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)

        self._buffer = self._textview.get_buffer()
        self.set_child(self._textview)

    def append_line(self, texto: str) -> None:
        """
        Adiciona uma linha ao terminal de log.

        Chame via GLib.idle_add(self.log_terminal.append_line, msg) de threads.
        """
        end_iter = self._buffer.get_end_iter()
        self._buffer.insert(end_iter, texto + "\n")

        # Limitar buffer para não crescer infinitamente
        linha_count = self._buffer.get_line_count()
        if linha_count > self.MAX_LINHAS:
            inicio = self._buffer.get_start_iter()
            corte = self._buffer.get_iter_at_line(linha_count - self.MAX_LINHAS)
            self._buffer.delete(inicio, corte)

        # Auto-scroll para a última linha
        adj = self.get_vadjustment()
        adj.set_value(adj.get_upper())

    def limpar(self) -> None:
        """Limpa todo o conteúdo do terminal."""
        self._buffer.set_text("")
