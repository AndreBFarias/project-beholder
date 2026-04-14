"""
Módulo Córtex — Visão IA local via Ollama/Moondream.

Controles:
- ANALISAR: sobe Ollama e processa fila de assets
- EXPURGAR VRAM: mata Ollama pelo PID exato (ADR-03)
- PAUSAR IA: pausa fila sem matar Ollama (Sprint 6)
- Grid ao vivo de imagens analisadas (Sprint 6)

ADR-01: todos os callbacks de UI chamados via GLib.idle_add pelo OllamaLifecycle.
ADR-03: kill exclusivo pelo PID — NUNCA pkill -f ollama.
"""

import logging

from gi.repository import Gtk

from src.ai_vision.ollama_lifecycle import OllamaLifecycle

logger = logging.getLogger("beholder.gui.cortex")


class CortexPage(Gtk.Box):
    """Página do módulo Córtex."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self._lifecycle = OllamaLifecycle()
        self._build_ui()

    def _build_ui(self) -> None:
        # Título
        titulo = Gtk.Label(label="Córtex")
        titulo.add_css_class("page-title")
        titulo.set_xalign(0)
        self.append(titulo)

        subtitulo = Gtk.Label(label="Visão IA Local")
        subtitulo.add_css_class("section-title")
        subtitulo.set_xalign(0)
        self.append(subtitulo)

        self.append(Gtk.Separator())

        # Status do Ollama
        status_frame = Gtk.Frame(label="Ollama")
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        status_box.set_margin_top(8)
        status_box.set_margin_bottom(8)
        status_box.set_margin_start(8)
        status_box.set_margin_end(8)

        self._label_ollama_status = Gtk.Label(label=" offline")
        self._label_ollama_status.add_css_class("status-dot-erro")

        self._label_modelo = Gtk.Label(label="Modelo: --")
        self._label_modelo.add_css_class("section-title")

        self._label_vram = Gtk.Label(label="VRAM: 0 GB")
        self._label_vram.add_css_class("section-title")

        status_box.append(self._label_ollama_status)
        status_box.append(Gtk.Separator.new(Gtk.Orientation.VERTICAL))
        status_box.append(self._label_modelo)
        status_box.append(Gtk.Separator.new(Gtk.Orientation.VERTICAL))
        status_box.append(self._label_vram)
        status_frame.set_child(status_box)
        self.append(status_frame)

        # Botões de controle da IA
        ctrl_frame = Gtk.Frame(label="Controle")
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ctrl_box.set_margin_top(8)
        ctrl_box.set_margin_bottom(8)
        ctrl_box.set_margin_start(8)
        ctrl_box.set_margin_end(8)

        self._btn_analisar = Gtk.Button(label="ANALISAR")
        self._btn_analisar.add_css_class("btn-primary")
        self._btn_analisar.connect("clicked", self._on_analisar)

        self._btn_pausar_ia = Gtk.Button(label="PAUSAR IA")
        self._btn_pausar_ia.add_css_class("btn-warning")
        self._btn_pausar_ia.set_sensitive(False)

        self._btn_expurgar = Gtk.Button(label="EXPURGAR VRAM")
        self._btn_expurgar.add_css_class("btn-danger")
        self._btn_expurgar.set_sensitive(False)
        self._btn_expurgar.connect("clicked", self._on_expurgar)

        ctrl_box.append(self._btn_analisar)
        ctrl_box.append(self._btn_pausar_ia)
        ctrl_box.append(self._btn_expurgar)
        ctrl_frame.set_child(ctrl_box)
        self.append(ctrl_frame)

        # Grid de imagens analisadas (placeholder — Sprint 6)
        grid_frame = Gtk.Frame(label="Análises")
        grid_scroll = Gtk.ScrolledWindow()
        grid_scroll.set_vexpand(True)
        grid_scroll.set_min_content_height(300)

        self._label_placeholder = Gtk.Label(
            label="Nenhuma análise realizada.\nInicie a Busca e depois clique em ANALISAR."
        )
        self._label_placeholder.set_justify(Gtk.Justification.CENTER)
        self._label_placeholder.add_css_class("section-title")
        self._label_placeholder.set_vexpand(True)
        self._label_placeholder.set_valign(Gtk.Align.CENTER)

        grid_scroll.set_child(self._label_placeholder)
        grid_frame.set_child(grid_scroll)
        self.append(grid_frame)

    # ------------------------------------------------------------------
    # Handlers de botão
    # ------------------------------------------------------------------

    def _on_analisar(self, _btn: Gtk.Button) -> None:
        """Inicia o Ollama via OllamaLifecycle."""
        self._btn_analisar.set_sensitive(False)
        self._btn_expurgar.set_sensitive(False)
        self._set_status("iniciando...", css="status-dot-ativo")
        self._lifecycle.subir(
            on_pronto=self._cb_ollama_pronto,
            on_erro=self._cb_ollama_erro,
        )
        logger.info("Solicitando subida do Ollama")

    def _on_expurgar(self, _btn: Gtk.Button) -> None:
        """Mata o Ollama pelo PID exato."""
        self._btn_analisar.set_sensitive(False)
        self._btn_expurgar.set_sensitive(False)
        self._btn_pausar_ia.set_sensitive(False)
        self._set_status("expurgando...", css="status-dot-pausado")
        self._lifecycle.expurgar(on_concluido=self._cb_expurgar_concluido)
        logger.info("Solicitando expurgo do Ollama")

    # ------------------------------------------------------------------
    # Callbacks de UI — chamados via GLib.idle_add pelo OllamaLifecycle
    # ------------------------------------------------------------------

    def _cb_ollama_pronto(self, msg: str) -> None:
        """Ollama subiu com sucesso."""
        self._set_status("ativo", css="status-dot-concluido")
        self._label_vram.set_label("VRAM: -- GB")
        self._btn_expurgar.set_sensitive(True)
        self._btn_pausar_ia.set_sensitive(True)
        self._label_placeholder.set_label(f"Ollama ativo.\n{msg}\n\nAguardando assets da Busca...")
        logger.info("Córtex: Ollama pronto — %s", msg)

    def _cb_ollama_erro(self, msg: str) -> None:
        """Falha ao subir o Ollama."""
        self._set_status("erro", css="status-dot-erro")
        self._btn_analisar.set_sensitive(True)
        self._label_placeholder.set_label(f"Erro ao iniciar Ollama:\n{msg}")
        logger.error("Córtex: falha no Ollama — %s", msg)

    def _cb_expurgar_concluido(self) -> None:
        """Ollama foi encerrado com sucesso."""
        self._set_status("offline", css="status-dot-erro")
        self._label_vram.set_label("VRAM: 0 GB")
        self._btn_analisar.set_sensitive(True)
        self._btn_pausar_ia.set_sensitive(False)
        self._label_placeholder.set_label("VRAM liberada.\nClique em ANALISAR para reiniciar o Ollama.")
        logger.info("Córtex: Ollama expurgado")

    # ------------------------------------------------------------------
    # Helper de status
    # ------------------------------------------------------------------

    def _set_status(self, texto: str, css: str) -> None:
        """Atualiza o label de status removendo a classe CSS anterior."""
        for cls in ("status-dot-ativo", "status-dot-pausado", "status-dot-erro", "status-dot-concluido"):
            self._label_ollama_status.remove_css_class(cls)
        self._label_ollama_status.add_css_class(css)
        self._label_ollama_status.set_label(f" {texto}")
