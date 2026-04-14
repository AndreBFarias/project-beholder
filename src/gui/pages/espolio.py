"""
Módulo Espólio — Exportação de pacotes.

Controles:
- GERAR PACOTE: inicia Packer (Thread C) → .zip + CSV
- ABRIR PASTA: xdg-open output/
- EXPORTAR CSV: FileChooserDialog de salvamento
- LIMPAR SESSÃO: confirmação obrigatória + shutil.rmtree

ADR-01: todos os callbacks de UI chamados via GLib.idle_add.
"""

import logging
import shutil
import subprocess
from pathlib import Path

from gi.repository import Gtk

from src.core.asset_queue import AssetProcessado, filas
from src.core.config.defaults import DEFAULTS
from src.exporter.dataset_writer import escrever_csv
from src.exporter.packer import Packer
from src.gui.widgets import LogTerminal, StatusBar

logger = logging.getLogger("beholder.gui.espolio")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DIR_OUTPUT = _PROJECT_ROOT / DEFAULTS["Saida"]["diretorio_output"]
_DIR_DATA = _PROJECT_ROOT / DEFAULTS["Saida"]["diretorio_data"]


class EspolioPage(Gtk.Box):
    """Página do módulo Espólio."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self._assets: list[AssetProcessado] = []
        self._ultimo_zip: str = ""
        self._packer = Packer(
            on_log=self._cb_log,
            on_concluido=self._cb_pacote_concluido,
        )
        self._status_bar: StatusBar | None = None
        self._build_ui()

    def conectar_status_bar(self, status_bar: StatusBar) -> None:
        """Conecta a barra de status global para atualizações em tempo real."""
        self._status_bar = status_bar

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

        # Resumo da sessão — mini-cards horizontais
        resumo_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        resumo_box.set_homogeneous(True)

        cards_info = [
            ("Assets brutos:", "0"),
            ("Assets processados:", "0"),
            ("Ícones:", "0"),
            ("Fundos:", "0"),
            ("Outros:", "0"),
        ]

        self._labels_valores: dict[str, Gtk.Label] = {}
        for chave, valor in cards_info:
            card_frame = Gtk.Frame()
            card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            card_box.set_margin_top(12)
            card_box.set_margin_bottom(12)
            card_box.set_margin_start(8)
            card_box.set_margin_end(8)
            card_box.set_halign(Gtk.Align.CENTER)

            lbl_valor = Gtk.Label(label=valor)
            lbl_valor.add_css_class("page-title")
            self._labels_valores[chave] = lbl_valor

            nome_curto = chave.rstrip(":")
            lbl_nome = Gtk.Label(label=nome_curto)
            lbl_nome.add_css_class("section-title")

            card_box.append(lbl_valor)
            card_box.append(lbl_nome)
            card_frame.set_child(card_box)
            resumo_box.append(card_frame)

        self.append(resumo_box)

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
        self._btn_gerar.connect("clicked", self._on_gerar)

        self._btn_abrir_pasta = Gtk.Button(label="ABRIR PASTA")
        self._btn_abrir_pasta.add_css_class("btn-secondary")
        self._btn_abrir_pasta.connect("clicked", self._on_abrir_pasta)

        self._btn_exportar_csv = Gtk.Button(label="EXPORTAR CSV")
        self._btn_exportar_csv.add_css_class("btn-secondary")
        self._btn_exportar_csv.connect("clicked", self._on_exportar_csv)

        self._btn_limpar = Gtk.Button(label="LIMPAR SESSÃO")
        self._btn_limpar.add_css_class("btn-danger")
        self._btn_limpar.connect("clicked", self._on_limpar_sessao)

        row1.append(self._btn_gerar)
        row1.append(self._btn_abrir_pasta)
        row1.append(self._btn_exportar_csv)
        row1.append(self._btn_limpar)

        acoes_box.append(row1)
        acoes_frame.set_child(acoes_box)
        self.append(acoes_frame)

        # Log de operações
        log_frame = Gtk.Frame(label="Log")
        self._log_terminal = LogTerminal()
        self._log_terminal.set_min_content_height(120)
        self._log_terminal.append_line("Aguardando operação...")
        log_frame.set_child(self._log_terminal)
        self.append(log_frame)

        # Lista de pacotes gerados
        historico_frame = Gtk.Frame(label="Pacotes Gerados")
        hist_scroll = Gtk.ScrolledWindow()
        hist_scroll.set_vexpand(True)
        hist_scroll.set_min_content_height(150)

        self._listbox_pacotes = Gtk.ListBox()
        self._listbox_pacotes.add_css_class("nav-listbox")
        self._listbox_pacotes.set_selection_mode(Gtk.SelectionMode.NONE)

        self._row_placeholder_hist = Gtk.ListBoxRow()
        self._row_placeholder_hist.set_selectable(False)
        lbl_vazio = Gtk.Label(label="Nenhum pacote gerado nesta sessão.")
        lbl_vazio.add_css_class("section-title")
        lbl_vazio.set_vexpand(True)
        lbl_vazio.set_valign(Gtk.Align.CENTER)
        lbl_vazio.set_margin_top(12)
        self._row_placeholder_hist.set_child(lbl_vazio)
        self._listbox_pacotes.append(self._row_placeholder_hist)

        hist_scroll.set_child(self._listbox_pacotes)
        historico_frame.set_child(hist_scroll)
        self.append(historico_frame)

    # ------------------------------------------------------------------
    # API pública — chamada pelo Orchestrator ao concluir
    # ------------------------------------------------------------------

    def registrar_asset(self, asset: AssetProcessado) -> None:
        """Registra asset processado localmente para exportação direta."""
        self._assets.append(asset)
        self._atualizar_contadores()

    # ------------------------------------------------------------------
    # Handlers de botão
    # ------------------------------------------------------------------

    def _on_gerar(self, _btn: Gtk.Button) -> None:
        """Inicia Packer (Thread C) para gerar .zip."""
        if self._packer.esta_ativo():
            self._cb_log("[AVISO] Packer já em execução.")
            return
        self._btn_gerar.set_sensitive(False)
        self._cb_log("[INFO] Iniciando empacotamento...")
        if self._status_bar:
            self._status_bar.update(status="ativa", sessao="exportando")

        if self._assets:
            # Drena resíduos de sessões anteriores da fila processada
            while not filas.processada.empty():
                try:
                    filas.processada.get_nowait()
                except Exception as exc:
                    logger.debug("Erro ao drenar fila residual: %s", exc)
                    break
            for asset in self._assets:
                filas.processada.put(asset)
            filas.processada.put(None)  # SENTINEL
            self._packer.iniciar()
        else:
            self._cb_log("[AVISO] Nenhum asset disponível para empacotar.")
            self._btn_gerar.set_sensitive(True)

    def _on_abrir_pasta(self, _btn: Gtk.Button) -> None:
        """Abre o diretório output/ com xdg-open."""
        _DIR_OUTPUT.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.Popen(["xdg-open", str(_DIR_OUTPUT)], start_new_session=True)
        except OSError as exc:
            logger.error("Falha ao abrir pasta: %s", exc)
            self._cb_log(f"[ERRO] Não foi possível abrir a pasta: {exc}")

    def _on_exportar_csv(self, _btn: Gtk.Button) -> None:
        """Abre FileChooserDialog para salvar CSV."""
        janela = self.get_root()
        dialogo = Gtk.FileChooserDialog(
            title="Exportar CSV",
            transient_for=janela,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialogo.add_button("_Cancelar", Gtk.ResponseType.CANCEL)
        dialogo.add_button("_Salvar", Gtk.ResponseType.ACCEPT)
        dialogo.set_current_name("beholder_metadata.csv")

        filtro = Gtk.FileFilter()
        filtro.set_name("CSV (*.csv)")
        filtro.add_pattern("*.csv")
        dialogo.add_filter(filtro)

        dialogo.connect("response", self._cb_dialogo_csv)
        dialogo.present()

    def _on_limpar_sessao(self, _btn: Gtk.Button) -> None:
        """Pede confirmação e limpa dados da sessão."""
        janela = self.get_root()
        dialogo = Gtk.MessageDialog(
            transient_for=janela,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Limpar sessão atual?",
        )
        dialogo.format_secondary_text(
            "Isso apagará todos os arquivos em data/sessao_atual/. Esta ação não pode ser desfeita."
        )
        dialogo.connect("response", self._cb_confirmar_limpar)
        dialogo.present()

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _cb_dialogo_csv(self, dialogo: Gtk.FileChooserDialog, resposta: int) -> None:
        if resposta == Gtk.ResponseType.ACCEPT:
            arquivo = dialogo.get_file()
            if arquivo:
                destino = Path(arquivo.get_path())
                try:
                    escrever_csv(self._assets, destino)
                    self._cb_log(f"[OK] CSV exportado: {destino}")
                except OSError as exc:
                    logger.error("Falha ao exportar CSV: %s", exc)
                    self._cb_log(f"[ERRO] {exc}")
        dialogo.destroy()

    def _cb_confirmar_limpar(self, dialogo: Gtk.MessageDialog, resposta: int) -> None:
        dialogo.destroy()
        if resposta == Gtk.ResponseType.YES:
            try:
                if _DIR_DATA.exists():
                    shutil.rmtree(_DIR_DATA)
                    _DIR_DATA.mkdir(parents=True, exist_ok=True)
                self._assets.clear()
                self._atualizar_contadores()
                self._cb_log("[INFO] Sessão limpa.")
                logger.info("Sessão limpa pelo usuário")
            except OSError as exc:
                logger.error("Falha ao limpar sessão: %s", exc)
                self._cb_log(f"[ERRO] {exc}")

    def _cb_log(self, msg: str) -> None:
        self._log_terminal.append_line(msg)
        logger.info("Espólio: %s", msg)

    def _cb_pacote_concluido(self, caminho_zip: str) -> None:
        """Packer encerrou — atualiza histórico e reativa botão."""
        self._btn_gerar.set_sensitive(True)
        if self._status_bar:
            self._status_bar.update(status="concluída", sessao="exportação")
        if caminho_zip:
            self._ultimo_zip = caminho_zip
            self._adicionar_historico(caminho_zip)
            self._cb_log(f"[OK] Pacote pronto: {Path(caminho_zip).name}")
        else:
            self._cb_log("[AVISO] Empacotamento encerrado sem arquivo.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _atualizar_contadores(self) -> None:
        icons = sum(1 for a in self._assets if a.tipo in {"icon", "logo", "svg", "vector"})
        fundos = sum(1 for a in self._assets if a.tipo in {"background", "photo"})
        outros = len(self._assets) - icons - fundos

        self._labels_valores["Assets processados:"].set_label(str(len(self._assets)))
        self._labels_valores["Ícones:"].set_label(str(icons))
        self._labels_valores["Fundos:"].set_label(str(fundos))
        self._labels_valores["Outros:"].set_label(str(outros))

    def _adicionar_historico(self, caminho_zip: str) -> None:
        if self._row_placeholder_hist:
            self._listbox_pacotes.remove(self._row_placeholder_hist)
            self._row_placeholder_hist = None

        row = Gtk.ListBoxRow()
        row.set_selectable(False)
        lbl = Gtk.Label(label=Path(caminho_zip).name)
        lbl.set_xalign(0)
        lbl.set_margin_top(4)
        lbl.set_margin_bottom(4)
        lbl.set_margin_start(8)
        row.set_child(lbl)
        self._listbox_pacotes.prepend(row)
