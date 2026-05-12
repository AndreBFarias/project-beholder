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

from gi.repository import Gtk, Pango

from src.core.asset_queue import AssetProcessado, filas
from src.core.config.defaults import DEFAULTS
from src.exporter.dataset_writer import escrever_csv
from src.exporter.packer import Packer
from src.gui.widgets import LogTerminal, StatusBar

logger = logging.getLogger("beholder.gui.espolio")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _dir_output() -> Path:
    """Diretório de saída lido dinamicamente de DEFAULTS (ADR-02)."""
    return _PROJECT_ROOT / DEFAULTS["Saida"]["diretorio_output"]


def _dir_data() -> Path:
    """Diretório da sessão lido dinamicamente de DEFAULTS (ADR-02)."""
    return _PROJECT_ROOT / DEFAULTS["Saida"]["diretorio_data"]


def _criar_thumb(caminho: str) -> Gtk.Widget:
    """Cria thumb de 72x72 a partir do arquivo local, ou placeholder em caso de falha."""
    TAMANHO = 72
    if caminho:
        try:
            p = Path(caminho)
            if p.exists() and p.is_file():
                pic = Gtk.Picture.new_for_filename(str(p))
                pic.set_size_request(TAMANHO, TAMANHO)
                pic.set_content_fit(Gtk.ContentFit.CONTAIN)
                pic.set_can_shrink(True)
                return pic
        except Exception as exc:
            logger.debug("Thumb falhou para %s: %s", caminho, exc)

    placeholder = Gtk.Label(label="◈")
    placeholder.set_size_request(TAMANHO, TAMANHO)
    placeholder.add_css_class("section-title")
    return placeholder


def _criar_card_asset_espolio(asset: AssetProcessado) -> Gtk.ListBoxRow:
    """Cria linha com thumb, descrição completa, tags como chips e metadados."""
    row = Gtk.ListBoxRow()
    row.set_selectable(False)

    linha_topo = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    linha_topo.set_margin_top(10)
    linha_topo.set_margin_bottom(10)
    linha_topo.set_margin_start(12)
    linha_topo.set_margin_end(12)

    # Thumb à esquerda
    thumb = _criar_thumb(asset.caminho_local)
    thumb.set_valign(Gtk.Align.START)
    linha_topo.append(thumb)

    # Caixa de texto à direita da thumb
    caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    caixa.set_hexpand(True)

    # Linha 1: badges (tipo + site_origem) + nome do arquivo
    cabecalho = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    badge_tipo = Gtk.Label(label=f"[{asset.tipo.upper()}]")
    badge_tipo.add_css_class("sidebar-module-name")
    badge_tipo.set_xalign(0)

    badge_site = Gtk.Label(label=f"@{asset.site_origem or 'generic'}")
    badge_site.add_css_class("section-title")
    badge_site.set_xalign(0)

    nome_arquivo = Path(asset.caminho_local).name if asset.caminho_local else asset.url_original
    lbl_nome = Gtk.Label(label=nome_arquivo)
    lbl_nome.add_css_class("section-title")
    lbl_nome.set_xalign(0)
    lbl_nome.set_hexpand(True)
    lbl_nome.set_ellipsize(Pango.EllipsizeMode.MIDDLE)

    cabecalho.append(badge_tipo)
    cabecalho.append(badge_site)
    cabecalho.append(lbl_nome)
    caixa.append(cabecalho)

    # Linha 2: descrição completa (com wrap)
    desc_texto = asset.descricao.strip() if asset.descricao else "(sem descrição)"
    lbl_desc = Gtk.Label(label=desc_texto)
    lbl_desc.set_xalign(0)
    lbl_desc.set_wrap(True)
    lbl_desc.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
    lbl_desc.set_max_width_chars(80)
    caixa.append(lbl_desc)

    # Linha 3: tags como chips
    if asset.tags:
        tags_box = Gtk.FlowBox()
        tags_box.set_selection_mode(Gtk.SelectionMode.NONE)
        tags_box.set_max_children_per_line(10)
        tags_box.set_row_spacing(4)
        tags_box.set_column_spacing(4)
        for tag in asset.tags:
            chip = Gtk.Label(label=f"#{tag}")
            chip.add_css_class("sidebar-module-desc")
            chip.set_margin_start(4)
            chip.set_margin_end(4)
            tags_box.append(chip)
        caixa.append(tags_box)
    else:
        lbl_sem_tags = Gtk.Label(label="(sem tags)")
        lbl_sem_tags.add_css_class("sidebar-module-desc")
        lbl_sem_tags.set_xalign(0)
        caixa.append(lbl_sem_tags)

    linha_topo.append(caixa)
    row.set_child(linha_topo)
    return row


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

        # Lista de assets processados (descrição + tags)
        assets_frame = Gtk.Frame(label="Assets Processados")
        assets_scroll = Gtk.ScrolledWindow()
        assets_scroll.set_vexpand(True)
        assets_scroll.set_min_content_height(220)
        assets_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._listbox_assets = Gtk.ListBox()
        self._listbox_assets.add_css_class("nav-listbox")
        self._listbox_assets.set_selection_mode(Gtk.SelectionMode.NONE)

        self._row_placeholder_assets = Gtk.ListBoxRow()
        self._row_placeholder_assets.set_selectable(False)
        lbl_sem_assets = Gtk.Label(
            label="Nenhum asset processado ainda.\nAnalise imagens no Córtex para ver descrições e tags aqui."
        )
        lbl_sem_assets.set_justify(Gtk.Justification.CENTER)
        lbl_sem_assets.add_css_class("section-title")
        lbl_sem_assets.set_vexpand(True)
        lbl_sem_assets.set_valign(Gtk.Align.CENTER)
        lbl_sem_assets.set_margin_top(20)
        self._row_placeholder_assets.set_child(lbl_sem_assets)
        self._listbox_assets.append(self._row_placeholder_assets)

        assets_scroll.set_child(self._listbox_assets)
        assets_frame.set_child(assets_scroll)
        self.append(assets_frame)

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

        if self._row_placeholder_assets is not None:
            self._listbox_assets.remove(self._row_placeholder_assets)
            self._row_placeholder_assets = None
        self._listbox_assets.prepend(_criar_card_asset_espolio(asset))

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
        destino = _dir_output()
        destino.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.Popen(["xdg-open", str(destino)], start_new_session=True)
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
                pasta_dados = _dir_data()
                if pasta_dados.exists():
                    shutil.rmtree(pasta_dados)
                    pasta_dados.mkdir(parents=True, exist_ok=True)
                self._assets.clear()
                self._ultimo_zip = ""
                self._atualizar_contadores()
                self._limpar_lista_assets()
                self._limpar_historico_pacotes()
                self._log_terminal.limpar()
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

    def _limpar_historico_pacotes(self) -> None:
        """Remove todas as linhas do histórico de pacotes e restaura placeholder."""
        filho = self._listbox_pacotes.get_first_child()
        while filho is not None:
            proximo = filho.get_next_sibling()
            self._listbox_pacotes.remove(filho)
            filho = proximo

        self._row_placeholder_hist = Gtk.ListBoxRow()
        self._row_placeholder_hist.set_selectable(False)
        lbl_vazio = Gtk.Label(label="Nenhum pacote gerado nesta sessão.")
        lbl_vazio.add_css_class("section-title")
        lbl_vazio.set_vexpand(True)
        lbl_vazio.set_valign(Gtk.Align.CENTER)
        lbl_vazio.set_margin_top(12)
        self._row_placeholder_hist.set_child(lbl_vazio)
        self._listbox_pacotes.append(self._row_placeholder_hist)

    def _limpar_lista_assets(self) -> None:
        """Remove todos os cards do ListBox de assets e restaura placeholder."""
        filho = self._listbox_assets.get_first_child()
        while filho is not None:
            proximo = filho.get_next_sibling()
            self._listbox_assets.remove(filho)
            filho = proximo

        self._row_placeholder_assets = Gtk.ListBoxRow()
        self._row_placeholder_assets.set_selectable(False)
        lbl = Gtk.Label(
            label="Nenhum asset processado ainda.\nAnalise imagens no Córtex para ver descrições e tags aqui."
        )
        lbl.set_justify(Gtk.Justification.CENTER)
        lbl.add_css_class("section-title")
        lbl.set_vexpand(True)
        lbl.set_valign(Gtk.Align.CENTER)
        lbl.set_margin_top(20)
        self._row_placeholder_assets.set_child(lbl)
        self._listbox_assets.append(self._row_placeholder_assets)

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
