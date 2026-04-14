"""
Módulo Grimório — Configurações persistidas.

Seções:
- Scraper: timeout, delay_min, delay_max, max_retries
- IA: porta Ollama, modelo, timeout de análise
- Saída: diretório output, K-Means cores

Ações:
- SALVAR: persiste via Config.save()
- TESTAR OLLAMA: ping na porta configurada
- RESTAURAR PADRÕES: recarrega DEFAULTS e preenche campos
- ABRIR LOGS: xdg-open logs/
"""

import logging
import subprocess
import threading
from pathlib import Path

import httpx
from gi.repository import GLib, Gtk

from src.core.config.config import Config
from src.core.config.defaults import DEFAULTS

logger = logging.getLogger("beholder.gui.grimorio")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


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
        self._cfg = Config()
        self._build_ui()
        self._carregar_valores()

    def _build_ui(self) -> None:
        # Título
        titulo = Gtk.Label(label="Grimório")
        titulo.add_css_class("page-title")
        titulo.set_xalign(0)
        self.append(titulo)

        subtitulo = Gtk.Label(label="Configurações")
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
        scraper_frame = Gtk.Frame(label="Scraper")
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
        ia_frame = Gtk.Frame(label="Inteligência Artificial")
        ia_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        ia_box.set_margin_top(8)
        ia_box.set_margin_bottom(8)
        ia_box.set_margin_start(8)
        ia_box.set_margin_end(8)

        row_porta, self._entry_porta = _criar_linha_config("Porta Ollama:", "11435")
        row_timeout_ia, self._entry_timeout_ia = _criar_linha_config("Timeout análise (s):", "60")

        # Seletor de tier de modelo (low/medium/high)
        row_tier = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        lbl_tier = Gtk.Label(label="Modelo IA:")
        lbl_tier.add_css_class("section-title")
        lbl_tier.set_xalign(0)
        lbl_tier.set_size_request(180, -1)

        self._combo_tier = Gtk.ComboBoxText()
        modelos = DEFAULTS["IA"]["modelos_disponiveis"]
        for tier_id, info in modelos.items():
            self._combo_tier.append(
                tier_id,
                f"{tier_id.upper()} — {info['nome']} ({info['vram_gb']} GB) — {info['descricao']}",
            )
        self._combo_tier.set_hexpand(True)
        row_tier.append(lbl_tier)
        row_tier.append(self._combo_tier)

        ia_box.append(row_porta)
        ia_box.append(row_tier)
        ia_box.append(row_timeout_ia)
        ia_frame.set_child(ia_box)
        conteudo.append(ia_frame)

        # Seção Saída
        saida_frame = Gtk.Frame(label="Saída")
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

        # Status label
        self._label_status = Gtk.Label(label="")
        self._label_status.add_css_class("section-title")
        self._label_status.set_xalign(0)
        self.append(self._label_status)

        # Ações
        acoes_frame = Gtk.Frame(label="Ações")
        acoes_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        acoes_box.set_margin_top(8)
        acoes_box.set_margin_bottom(8)
        acoes_box.set_margin_start(8)
        acoes_box.set_margin_end(8)

        self._btn_salvar = Gtk.Button(label="SALVAR")
        self._btn_salvar.add_css_class("btn-primary")
        self._btn_salvar.connect("clicked", self._on_salvar)

        self._btn_testar = Gtk.Button(label="TESTAR OLLAMA")
        self._btn_testar.add_css_class("btn-secondary")
        self._btn_testar.connect("clicked", self._on_testar_ollama)

        self._btn_restaurar = Gtk.Button(label="RESTAURAR PADRÕES")
        self._btn_restaurar.add_css_class("btn-warning")
        self._btn_restaurar.connect("clicked", self._on_restaurar)

        self._btn_logs = Gtk.Button(label="ABRIR LOGS")
        self._btn_logs.add_css_class("btn-secondary")
        self._btn_logs.connect("clicked", self._on_abrir_logs)

        acoes_box.append(self._btn_salvar)
        acoes_box.append(self._btn_testar)
        acoes_box.append(self._btn_restaurar)
        acoes_box.append(self._btn_logs)
        acoes_frame.set_child(acoes_box)
        self.append(acoes_frame)

    # ------------------------------------------------------------------
    # Carregamento inicial
    # ------------------------------------------------------------------

    def _carregar_valores(self) -> None:
        """Preenche os campos com os valores atuais (config ou defaults)."""
        self._entry_timeout.set_text(str(self._cfg.get("Scraper", "timeout")))
        self._entry_delay_min.set_text(str(self._cfg.get("Scraper", "delay_min")))
        self._entry_delay_max.set_text(str(self._cfg.get("Scraper", "delay_max")))
        self._entry_retries.set_text(str(self._cfg.get("Scraper", "max_retries")))
        self._entry_porta.set_text(str(self._cfg.get("IA", "ollama_port")))
        tier_atual = str(self._cfg.get("IA", "modelo_tier") or "low")
        self._combo_tier.set_active_id(tier_atual)
        self._entry_timeout_ia.set_text(str(self._cfg.get("IA", "timeout_analise")))
        self._entry_output.set_text(str(self._cfg.get("Saida", "diretorio_output")))
        self._entry_kmeans.set_text(str(self._cfg.get("Saida", "kmeans_cores")))

    # ------------------------------------------------------------------
    # Handlers de botão
    # ------------------------------------------------------------------

    def _on_salvar(self, _btn: Gtk.Button) -> None:
        """Lê os campos e persiste via Config.save()."""
        try:
            self._cfg.set("Scraper", "timeout", self._entry_timeout.get_text().strip())
            self._cfg.set("Scraper", "delay_min", self._entry_delay_min.get_text().strip())
            self._cfg.set("Scraper", "delay_max", self._entry_delay_max.get_text().strip())
            self._cfg.set("Scraper", "max_retries", self._entry_retries.get_text().strip())
            self._cfg.set("IA", "ollama_port", self._entry_porta.get_text().strip())
            tier_selecionado = self._combo_tier.get_active_id() or "low"
            self._cfg.set("IA", "modelo_tier", tier_selecionado)
            modelos = DEFAULTS["IA"]["modelos_disponiveis"]
            if tier_selecionado in modelos:
                self._cfg.set("IA", "modelo", modelos[tier_selecionado]["nome"])
            self._cfg.set("IA", "timeout_analise", self._entry_timeout_ia.get_text().strip())
            self._cfg.set("Saida", "diretorio_output", self._entry_output.get_text().strip())
            self._cfg.set("Saida", "kmeans_cores", self._entry_kmeans.get_text().strip())
            self._cfg.save()
            self._label_status.set_label("[OK] Configurações salvas.")
            logger.info("Grimório: configurações salvas")
        except Exception as exc:
            self._label_status.set_label(f"[ERRO] {exc}")
            logger.error("Falha ao salvar configurações: %s", exc)

    def _on_testar_ollama(self, _btn: Gtk.Button) -> None:
        """Faz ping na porta configurada do Ollama em thread separada (ADR-01)."""
        porta = self._entry_porta.get_text().strip() or str(DEFAULTS["IA"]["ollama_port"])
        self._btn_testar.set_sensitive(False)
        self._label_status.set_label("Testando Ollama...")
        threading.Thread(
            target=self._thread_testar_ollama,
            args=(porta,),
            daemon=True,
            name="beholder-grimorio-test",
        ).start()
        logger.info("Grimório: teste Ollama na porta %s", porta)

    def _thread_testar_ollama(self, porta: str) -> None:
        """Thread de teste do Ollama — resultado via GLib.idle_add (ADR-01)."""
        url = f"http://127.0.0.1:{porta}/api/tags"
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    GLib.idle_add(self._label_status.set_label, f"[OK] Ollama online na porta {porta}.")
                else:
                    GLib.idle_add(self._label_status.set_label, f"[AVISO] Ollama respondeu HTTP {resp.status_code}.")
        except httpx.ConnectError:
            GLib.idle_add(self._label_status.set_label, f"[OFFLINE] Ollama não responde na porta {porta}.")
        except Exception as exc:
            GLib.idle_add(self._label_status.set_label, f"[ERRO] {exc}")
        finally:
            GLib.idle_add(self._btn_testar.set_sensitive, True)

    def _on_restaurar(self, _btn: Gtk.Button) -> None:
        """Restaura valores padrão e atualiza os campos."""
        self._cfg.restaurar_padroes()
        self._cfg = Config()  # recarrega sem config.ini
        self._carregar_valores()
        self._label_status.set_label("[OK] Padrões restaurados.")
        logger.info("Grimório: padrões restaurados")

    def _on_abrir_logs(self, _btn: Gtk.Button) -> None:
        """Abre a pasta logs/ com xdg-open."""
        logs_dir = _PROJECT_ROOT / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.Popen(["xdg-open", str(logs_dir)], start_new_session=True)
        except OSError as exc:
            logger.error("Falha ao abrir logs: %s", exc)
            self._label_status.set_label(f"[ERRO] {exc}")
