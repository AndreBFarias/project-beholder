"""
Módulo Córtex — Visão IA local via Ollama/Moondream.

Controles:
- ANALISAR: sobe Ollama e inicia Orchestrator (Thread B)
- EXPURGAR VRAM: mata Ollama pelo PID exato (ADR-03)
- PAUSAR IA: pausa Orchestrator sem matar Ollama
- Grid ao vivo de imagens analisadas

ADR-01: todos os callbacks de UI chamados via GLib.idle_add.
ADR-03: kill exclusivo pelo PID — NUNCA pkill -f ollama.
"""

import logging

from gi.repository import Gtk, Pango

from src.ai_vision.ollama_lifecycle import OllamaLifecycle
from src.ai_vision.orchestrator import Orchestrator
from src.core.asset_queue import AssetProcessado
from src.gui.widgets import LogTerminal, StatusBar

logger = logging.getLogger("beholder.gui.cortex")


def _criar_swatches(paleta: list[str]) -> Gtk.Box:
    """Cria caixinha de cores (swatches) a partir da paleta hex."""
    caixa = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
    for cor in paleta[:4]:
        swatch = Gtk.Label(label="  ")
        swatch.set_size_request(16, 16)
        try:
            swatch.set_tooltip_text(cor)
            # Aplica cor via CSS inline no widget
            provider = Gtk.CssProvider()
            provider.load_from_data(f"label {{ background-color: {cor}; }}".encode())
            swatch.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        except Exception as exc:
            logger.debug("CSS provider falhou para swatch %s: %s", cor, exc)
        caixa.append(swatch)
    return caixa


def _criar_card_asset(asset: AssetProcessado) -> Gtk.ListBoxRow:
    """Cria uma linha do grid de análises para um AssetProcessado."""
    row = Gtk.ListBoxRow()
    row.set_selectable(False)

    caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    caixa.set_margin_top(8)
    caixa.set_margin_bottom(8)
    caixa.set_margin_start(10)
    caixa.set_margin_end(10)

    # Linha 1: tipo + descricao
    linha1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    badge_tipo = Gtk.Label(label=f"[{asset.tipo.upper()}]")
    badge_tipo.add_css_class("sidebar-module-name")
    badge_tipo.set_xalign(0)

    lbl_desc = Gtk.Label(label=asset.descricao[:80] if asset.descricao else "—")
    lbl_desc.set_xalign(0)
    lbl_desc.set_hexpand(True)
    lbl_desc.set_ellipsize(Pango.EllipsizeMode.END)

    linha1.append(badge_tipo)
    linha1.append(lbl_desc)
    caixa.append(linha1)

    # Linha 2: tags + swatches de cores
    linha2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

    tags_texto = "  ".join(f"#{t}" for t in asset.tags[:5]) if asset.tags else "sem tags"
    lbl_tags = Gtk.Label(label=tags_texto)
    lbl_tags.add_css_class("sidebar-module-desc")
    lbl_tags.set_xalign(0)
    lbl_tags.set_hexpand(True)

    if asset.paleta_hex:
        swatches = _criar_swatches(asset.paleta_hex)
        linha2.append(lbl_tags)
        linha2.append(swatches)
    else:
        linha2.append(lbl_tags)

    caixa.append(linha2)

    # Linha 3: URL truncada
    url_curta = asset.url_original
    if len(url_curta) > 80:
        url_curta = url_curta[:77] + "..."
    lbl_url = Gtk.Label(label=url_curta)
    lbl_url.add_css_class("sidebar-module-desc")
    lbl_url.set_xalign(0)
    caixa.append(lbl_url)

    row.set_child(caixa)
    return row


class CortexPage(Gtk.Box):
    """Página do módulo Córtex."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self._lifecycle = OllamaLifecycle()
        self._orchestrator = Orchestrator(
            on_log=self._cb_log,
            on_asset=self._cb_asset_processado,
            on_concluido=self._cb_orquestrador_concluido,
        )
        self._espolio = None
        self._status_bar: StatusBar | None = None
        self._build_ui()

    def conectar_status_bar(self, status_bar: StatusBar) -> None:
        """Conecta a barra de status global para atualizações em tempo real."""
        self._status_bar = status_bar

    def conectar_espolio(self, espolio_page) -> None:
        """Conecta o Córtex ao Espólio para alimentar contadores de exportação."""
        self._espolio = espolio_page

    def iniciar_pipeline_automatico(self) -> None:
        """Inicia Ollama + Orchestrator programaticamente (chamado pela Busca)."""
        if self._orchestrator.esta_ativo():
            logger.info("Pipeline já ativo — ignorando início automático")
            return
        if self._lifecycle.esta_ativo():
            self._orchestrator.iniciar()
            self._btn_pausar_ia.set_sensitive(True)
            self._btn_expurgar.set_sensitive(True)
            self._set_status("ativo", css="status-dot-concluido")
            logger.info("Pipeline automático: Orchestrator iniciado (Ollama já ativo)")
            return
        self._btn_analisar.set_sensitive(False)
        self._set_status("iniciando...", css="status-dot-ativo")
        self._lifecycle.subir(
            on_pronto=self._cb_ollama_pronto,
            on_erro=self._cb_ollama_erro,
        )
        logger.info("Pipeline automático solicitado pela Busca")

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

        # Botões de controle
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
        self._btn_pausar_ia.connect("clicked", self._on_pausar_ia)

        self._btn_expurgar = Gtk.Button(label="EXPURGAR VRAM")
        self._btn_expurgar.add_css_class("btn-danger")
        self._btn_expurgar.set_sensitive(False)
        self._btn_expurgar.connect("clicked", self._on_expurgar)

        ctrl_box.append(self._btn_analisar)
        ctrl_box.append(self._btn_pausar_ia)
        ctrl_box.append(self._btn_expurgar)
        ctrl_frame.set_child(ctrl_box)
        self.append(ctrl_frame)

        # Área principal: grid + log divididos
        area_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        area_box.set_vexpand(True)

        # Grid de análises (ListBox com scroll)
        grid_frame = Gtk.Frame(label="Análises")
        grid_frame.set_hexpand(True)
        grid_scroll = Gtk.ScrolledWindow()
        grid_scroll.set_vexpand(True)
        grid_scroll.set_min_content_height(250)
        grid_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._listbox_grid = Gtk.ListBox()
        self._listbox_grid.add_css_class("nav-listbox")
        self._listbox_grid.set_selection_mode(Gtk.SelectionMode.NONE)

        self._label_placeholder = Gtk.Label(
            label="Nenhuma análise realizada.\nInicie a Busca e depois clique em ANALISAR."
        )
        self._label_placeholder.set_justify(Gtk.Justification.CENTER)
        self._label_placeholder.add_css_class("section-title")
        self._label_placeholder.set_vexpand(True)
        self._label_placeholder.set_valign(Gtk.Align.CENTER)
        self._label_placeholder.set_margin_top(20)

        row_placeholder = Gtk.ListBoxRow()
        row_placeholder.set_selectable(False)
        row_placeholder.set_child(self._label_placeholder)
        self._listbox_grid.append(row_placeholder)
        self._row_placeholder = row_placeholder

        grid_scroll.set_child(self._listbox_grid)
        grid_frame.set_child(grid_scroll)
        area_box.append(grid_frame)

        # Log do orquestrador (lateral direita)
        log_frame = Gtk.Frame(label="Log IA")
        log_frame.set_size_request(180, -1)
        self._log_ia = LogTerminal()
        log_frame.set_child(self._log_ia)
        area_box.append(log_frame)

        self.append(area_box)

    # ------------------------------------------------------------------
    # Handlers de botão
    # ------------------------------------------------------------------

    def _on_analisar(self, _btn: Gtk.Button) -> None:
        """Sobe Ollama e inicia Orchestrator."""
        self._btn_analisar.set_sensitive(False)
        self._btn_expurgar.set_sensitive(False)
        self._set_status("iniciando...", css="status-dot-ativo")
        self._lifecycle.subir(
            on_pronto=self._cb_ollama_pronto,
            on_erro=self._cb_ollama_erro,
        )
        logger.info("Solicitando subida do Ollama")

    def _on_pausar_ia(self, _btn: Gtk.Button) -> None:
        """Alterna pausa/retomada do Orchestrator."""
        if self._orchestrator.esta_ativo():
            if self._btn_pausar_ia.get_label() == "PAUSAR IA":
                self._orchestrator.pausar()
                self._btn_pausar_ia.set_label("RETOMAR IA")
            else:
                self._orchestrator.retomar()
                self._btn_pausar_ia.set_label("PAUSAR IA")

    def _on_expurgar(self, _btn: Gtk.Button) -> None:
        """Cancela Orchestrator e mata Ollama."""
        self._orchestrator.cancelar()
        self._btn_analisar.set_sensitive(False)
        self._btn_expurgar.set_sensitive(False)
        self._btn_pausar_ia.set_sensitive(False)
        self._set_status("expurgando...", css="status-dot-pausado")
        self._lifecycle.expurgar(on_concluido=self._cb_expurgar_concluido)
        logger.info("Solicitando expurgo do Ollama")

    # ------------------------------------------------------------------
    # Callbacks — chamados via GLib.idle_add
    # ------------------------------------------------------------------

    def _cb_ollama_pronto(self, msg: str) -> None:
        """Ollama ativo — inicia o Orchestrator."""
        from src.core.config.defaults import DEFAULTS

        self._set_status("ativo", css="status-dot-concluido")
        self._label_vram.set_label("VRAM: -- GB")
        tier = DEFAULTS["IA"].get("modelo_tier", "low")
        modelos = DEFAULTS["IA"].get("modelos_disponiveis", {})
        nome_modelo = modelos.get(tier, {}).get("nome", DEFAULTS["IA"]["modelo"])
        self._label_modelo.set_label(f"Modelo: {nome_modelo}")
        self._btn_expurgar.set_sensitive(True)
        self._btn_pausar_ia.set_sensitive(True)
        self._log_ia.append_line(f"[OK] {msg}")
        self._orchestrator.iniciar()
        if self._status_bar:
            self._status_bar.update(status="ativa", sessao="análise")
        logger.info("Córtex: Ollama pronto, Orchestrator iniciado — %s", msg)

    def _cb_ollama_erro(self, msg: str) -> None:
        """Falha ao subir Ollama."""
        self._set_status("erro", css="status-dot-erro")
        self._btn_analisar.set_sensitive(True)
        self._log_ia.append_line(f"[ERRO] {msg}")
        logger.error("Córtex: falha no Ollama — %s", msg)

    def _cb_expurgar_concluido(self) -> None:
        """Ollama encerrado."""
        self._set_status("offline", css="status-dot-erro")
        self._label_vram.set_label("VRAM: 0 GB")
        self._label_modelo.set_label("Modelo: --")
        self._btn_analisar.set_sensitive(True)
        self._btn_pausar_ia.set_sensitive(False)
        self._btn_pausar_ia.set_label("PAUSAR IA")
        self._log_ia.append_line("[INFO] VRAM liberada.")
        if self._status_bar:
            self._status_bar.update(status="nova", vram_gb=0.0, sessao="offline")
        logger.info("Córtex: Ollama expurgado")

    def _cb_log(self, msg: str) -> None:
        """Linha de log do Orchestrator."""
        self._log_ia.append_line(msg)

    def _cb_asset_processado(self, asset: AssetProcessado) -> None:
        """Recebe asset analisado, adiciona ao grid e registra no Espólio."""
        if self._row_placeholder:
            self._listbox_grid.remove(self._row_placeholder)
            self._row_placeholder = None

        card = _criar_card_asset(asset)
        self._listbox_grid.prepend(card)

        if self._espolio:
            self._espolio.registrar_asset(asset)

    def _cb_orquestrador_concluido(self, total: int) -> None:
        """Orchestrator encerrou."""
        self._btn_pausar_ia.set_sensitive(False)
        self._btn_pausar_ia.set_label("PAUSAR IA")
        self._log_ia.append_line(f"[INFO] Análise concluída — {total} assets.")
        if self._status_bar:
            self._status_bar.update(status="concluída", baixados=total, total=total, sessao="análise")
        logger.info("Córtex: Orchestrator concluído — %d assets", total)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _set_status(self, texto: str, css: str) -> None:
        for cls in ("status-dot-ativo", "status-dot-pausado", "status-dot-erro", "status-dot-concluido"):
            self._label_ollama_status.remove_css_class(cls)
        self._label_ollama_status.add_css_class(css)
        self._label_ollama_status.set_label(f" {texto}")
