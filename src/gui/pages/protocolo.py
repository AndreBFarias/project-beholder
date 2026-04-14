"""
Módulo Protocolo — Execução em lote com checkpoint.

Controles:
- ADICIONAR URL: valida e insere na fila visual
- IMPORTAR LISTA: FileChooserDialog → .txt com URLs (uma por linha)
- EXECUTAR LOTE: processa URLs sequencialmente via StealthSpider
- RETOMAR SESSÃO: restaura estado do checkpoint e continua
- LIMPAR LISTA: apaga fila visual + checkpoint

ADR-01: todos os callbacks de UI chamados via GLib.idle_add.
"""

import logging
import threading
from datetime import UTC, datetime
from pathlib import Path

from gi.repository import GLib, Gtk

from src.core import checkpoint as ckpt
from src.core.checkpoint import EstadoCheckpoint
from src.scraper.stealth_spider import StealthSpider

logger = logging.getLogger("beholder.gui.protocolo")

# Colunas do modelo de lista
COL_URL = 0
COL_STATUS = 1


class ProtocoloPage(Gtk.Box):
    """Página do módulo Protocolo."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self._thread_lote: threading.Thread | None = None
        self._parar_lote = threading.Event()
        self._build_ui()

    def _build_ui(self) -> None:
        # Título
        titulo = Gtk.Label(label="Protocolo")
        titulo.add_css_class("page-title")
        titulo.set_xalign(0)
        self.append(titulo)

        subtitulo = Gtk.Label(label="Execução em Lote")
        subtitulo.add_css_class("section-title")
        subtitulo.set_xalign(0)
        self.append(subtitulo)

        self.append(Gtk.Separator())

        # Adicionar URL individual
        add_frame = Gtk.Frame(label="Adicionar URL")
        add_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        add_box.set_margin_top(8)
        add_box.set_margin_bottom(8)
        add_box.set_margin_start(8)
        add_box.set_margin_end(8)

        self._entry_nova_url = Gtk.Entry()
        self._entry_nova_url.set_placeholder_text("https://exemplo.com")
        self._entry_nova_url.set_hexpand(True)
        self._entry_nova_url.connect("activate", self._on_adicionar)

        self._btn_adicionar = Gtk.Button(label="ADICIONAR")
        self._btn_adicionar.add_css_class("btn-primary")
        self._btn_adicionar.connect("clicked", self._on_adicionar)

        self._btn_importar = Gtk.Button(label="IMPORTAR LISTA")
        self._btn_importar.add_css_class("btn-secondary")
        self._btn_importar.connect("clicked", self._on_importar_lista)

        add_box.append(self._entry_nova_url)
        add_box.append(self._btn_adicionar)
        add_box.append(self._btn_importar)
        add_frame.set_child(add_box)
        self.append(add_frame)

        # Lista de URLs
        lista_frame = Gtk.Frame(label="Fila de URLs")
        lista_frame.set_vexpand(True)
        lista_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lista_box.set_margin_top(8)
        lista_box.set_margin_bottom(8)
        lista_box.set_margin_start(8)
        lista_box.set_margin_end(8)

        # Modelo de dados: (url, status)
        self._store = Gtk.ListStore(str, str)

        self._treeview = Gtk.TreeView(model=self._store)
        self._treeview.set_vexpand(True)

        col_url = Gtk.TreeViewColumn("URL", Gtk.CellRendererText(), text=COL_URL)
        col_url.set_expand(True)
        self._treeview.append_column(col_url)

        col_status = Gtk.TreeViewColumn("Status", Gtk.CellRendererText(), text=COL_STATUS)
        col_status.set_min_width(120)
        self._treeview.append_column(col_status)

        lista_scroll = Gtk.ScrolledWindow()
        lista_scroll.set_vexpand(True)
        lista_scroll.set_min_content_height(200)
        lista_scroll.set_child(self._treeview)

        lista_box.append(lista_scroll)
        lista_frame.set_child(lista_box)
        self.append(lista_frame)

        # Progresso do lote
        prog_frame = Gtk.Frame(label="Progresso")
        prog_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        prog_box.set_margin_top(8)
        prog_box.set_margin_bottom(8)
        prog_box.set_margin_start(8)
        prog_box.set_margin_end(8)

        self._barra_lote = Gtk.ProgressBar()
        self._barra_lote.set_show_text(True)
        self._barra_lote.set_text("Aguardando lote...")
        self._barra_lote.set_fraction(0.0)

        self._label_status_lote = Gtk.Label(label="")
        self._label_status_lote.add_css_class("sidebar-module-desc")
        self._label_status_lote.set_xalign(0)

        prog_box.append(self._barra_lote)
        prog_box.append(self._label_status_lote)
        prog_frame.set_child(prog_box)
        self.append(prog_frame)

        # Controles de execução do lote
        ctrl_frame = Gtk.Frame(label="Controle do Lote")
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ctrl_box.set_margin_top(8)
        ctrl_box.set_margin_bottom(8)
        ctrl_box.set_margin_start(8)
        ctrl_box.set_margin_end(8)

        self._btn_executar = Gtk.Button(label="EXECUTAR LOTE")
        self._btn_executar.add_css_class("btn-primary")
        self._btn_executar.connect("clicked", self._on_executar_lote)

        self._btn_retomar = Gtk.Button(label="RETOMAR SESSÃO")
        self._btn_retomar.add_css_class("btn-warning")
        self._btn_retomar.connect("clicked", self._on_retomar_sessao)
        self._btn_retomar.set_sensitive(ckpt.existe())

        self._btn_limpar_lista = Gtk.Button(label="LIMPAR LISTA")
        self._btn_limpar_lista.add_css_class("btn-danger")
        self._btn_limpar_lista.connect("clicked", self._on_limpar_lista)

        # Toggle modo furtivo
        lbl_furtivo = Gtk.Label(label="FURTIVO")
        lbl_furtivo.add_css_class("section-title")
        self._toggle_furtivo = Gtk.Switch()
        self._toggle_furtivo.set_valign(Gtk.Align.CENTER)

        ctrl_box.append(self._btn_executar)
        ctrl_box.append(self._btn_retomar)
        ctrl_box.append(self._btn_limpar_lista)
        ctrl_box.append(Gtk.Separator.new(Gtk.Orientation.VERTICAL))
        ctrl_box.append(lbl_furtivo)
        ctrl_box.append(self._toggle_furtivo)
        ctrl_frame.set_child(ctrl_box)
        self.append(ctrl_frame)

    # ------------------------------------------------------------------
    # Handlers de botão
    # ------------------------------------------------------------------

    def _on_adicionar(self, _widget) -> None:
        """Adiciona URL à fila com status 'pendente'."""
        url = self._entry_nova_url.get_text().strip()
        if not url:
            return
        if not url.startswith(("http://", "https://")):
            self._label_status_lote.set_label("[AVISO] URL deve começar com http:// ou https://")
            return
        self._store.append([url, "pendente"])
        self._entry_nova_url.set_text("")
        self._label_status_lote.set_label(f"[OK] URL adicionada — {self._total_na_fila()} na fila")

    def _on_importar_lista(self, _btn: Gtk.Button) -> None:
        """Abre FileChooserDialog para importar .txt com URLs."""
        janela = self.get_root()
        dialogo = Gtk.FileChooserDialog(
            title="Importar Lista de URLs",
            transient_for=janela,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialogo.add_button("_Cancelar", Gtk.ResponseType.CANCEL)
        dialogo.add_button("_Abrir", Gtk.ResponseType.ACCEPT)

        filtro = Gtk.FileFilter()
        filtro.set_name("Texto (*.txt)")
        filtro.add_pattern("*.txt")
        dialogo.add_filter(filtro)

        dialogo.connect("response", self._cb_dialogo_importar)
        dialogo.present()

    def _on_executar_lote(self, _btn: Gtk.Button) -> None:
        """Inicia execução sequencial das URLs pendentes."""
        if self._thread_lote and self._thread_lote.is_alive():
            self._label_status_lote.set_label("[AVISO] Lote já em execução.")
            return

        urls_pendentes = self._coletar_urls_pendentes()
        if not urls_pendentes:
            self._label_status_lote.set_label("[AVISO] Nenhuma URL pendente na fila.")
            return

        self._parar_lote.clear()
        self._btn_executar.set_sensitive(False)
        self._btn_retomar.set_sensitive(False)
        self._barra_lote.set_fraction(0.0)
        self._barra_lote.set_text(f"0 / {len(urls_pendentes)}")

        modo_furtivo = self._toggle_furtivo.get_active()
        self._thread_lote = threading.Thread(
            target=self._executar_lote_thread,
            args=(urls_pendentes, modo_furtivo),
            daemon=True,
            name="beholder-protocolo-lote",
        )
        self._thread_lote.start()
        logger.info("Lote iniciado: %d URLs, modo_furtivo=%s", len(urls_pendentes), modo_furtivo)

    def _on_retomar_sessao(self, _btn: Gtk.Button) -> None:
        """Restaura checkpoint e reconstitui a fila."""
        estado = ckpt.carregar()
        if not estado:
            self._label_status_lote.set_label("[AVISO] Nenhum checkpoint encontrado.")
            self._btn_retomar.set_sensitive(False)
            return

        self._store.clear()

        for url in estado.urls_concluidas:
            self._store.append([url, "concluída"])

        for url in estado.urls_com_erro:
            self._store.append([url, "erro"])

        if estado.url_atual:
            self._store.append([estado.url_atual, "pendente"])

        for url in estado.urls_pendentes:
            self._store.append([url, "pendente"])

        total_pend = len(estado.urls_pendentes) + (1 if estado.url_atual else 0)
        self._label_status_lote.set_label(
            f"[OK] Sessão restaurada — {total_pend} pendentes, {len(estado.urls_concluidas)} concluídas"
        )
        logger.info("Checkpoint restaurado: %d pendentes", total_pend)

    def _on_limpar_lista(self, _btn: Gtk.Button) -> None:
        """Limpa todas as URLs da lista e remove checkpoint."""
        self._store.clear()
        ckpt.remover()
        self._btn_retomar.set_sensitive(False)
        self._barra_lote.set_fraction(0.0)
        self._barra_lote.set_text("Aguardando lote...")
        self._label_status_lote.set_label("[OK] Lista limpa.")

    # ------------------------------------------------------------------
    # Thread do lote
    # ------------------------------------------------------------------

    def _executar_lote_thread(self, entradas: list[tuple[str, str]], modo_furtivo: bool) -> None:
        """
        Thread do lote: processa URLs sequencialmente.

        Args:
            entradas: Lista de (url, path_string) — url + path da linha no ListStore.
            modo_furtivo: Se True, usa Playwright.
        """
        total = len(entradas)
        concluidas: list[str] = []
        com_erro: list[str] = []

        for i, (url, path_str) in enumerate(entradas):
            if self._parar_lote.is_set():
                break

            # Atualiza status → em progresso
            GLib.idle_add(self._atualizar_status, path_str, "em progresso")
            GLib.idle_add(self._label_status_lote.set_label, f"[{i + 1}/{total}] {url[:60]}")

            # Salva checkpoint antes de iniciar a URL
            GLib.idle_add(
                self._salvar_checkpoint,
                [u for u, _ in entradas[i:]],
                concluidas[:],
                com_erro[:],
                url,
            )

            # Executa spider para esta URL (bloqueia até on_concluido)
            status_final = ["concluída"]
            concluido_evt, status_ref = threading.Event(), status_final

            spider = StealthSpider(
                on_log=lambda msg: GLib.idle_add(self._label_status_lote.set_label, msg[:80]),
                on_progresso=lambda _f, _t: None,
                on_concluido=lambda n, _s=status_ref, _e=concluido_evt: (
                    _s.__setitem__(0, "sem assets") if n == 0 else None,
                    _e.set(),
                ),
            )
            try:
                spider.iniciar(url, modo_furtivo=modo_furtivo)
                concluido_evt.wait(timeout=300)  # máx 5 min por URL
            except Exception as exc:
                logger.error("Erro ao processar %s: %s", url, exc)
                status_final[0] = "erro"

            final = status_final[0]
            if final == "concluída":
                concluidas.append(url)
            else:
                com_erro.append(url)

            GLib.idle_add(self._atualizar_status, path_str, final)

            # Progresso geral
            fracao = (i + 1) / total
            GLib.idle_add(self._barra_lote.set_fraction, fracao)
            GLib.idle_add(self._barra_lote.set_text, f"{i + 1} / {total}")

        # Limpeza final
        GLib.idle_add(self._finalizar_lote, total, concluidas, com_erro)

    # ------------------------------------------------------------------
    # Callbacks FileChooser
    # ------------------------------------------------------------------

    def _cb_dialogo_importar(self, dialogo: Gtk.FileChooserDialog, resposta: int) -> None:
        if resposta == Gtk.ResponseType.ACCEPT:
            arquivo = dialogo.get_file()
            if arquivo:
                caminho = Path(arquivo.get_path())
                self._importar_urls_de_arquivo(caminho)
        dialogo.destroy()

    def _importar_urls_de_arquivo(self, caminho: Path) -> None:
        """Lê URLs de um .txt (uma por linha) e adiciona à fila."""
        try:
            linhas = caminho.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            logger.error("Falha ao ler arquivo: %s", exc)
            self._label_status_lote.set_label(f"[ERRO] {exc}")
            return

        adicionadas = 0
        for linha in linhas:
            url = linha.strip()
            if url.startswith(("http://", "https://")):
                self._store.append([url, "pendente"])
                adicionadas += 1

        self._label_status_lote.set_label(f"[OK] {adicionadas} URLs importadas de {caminho.name}")
        logger.info("Importadas %d URLs de %s", adicionadas, caminho)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _total_na_fila(self) -> int:
        return self._store.iter_n_children(None)

    def _coletar_urls_pendentes(self) -> list[tuple[str, str]]:
        """Retorna lista de (url, path_string) para URLs com status 'pendente'."""
        resultado = []
        it = self._store.get_iter_first()
        while it:
            status = self._store.get_value(it, COL_STATUS)
            if status == "pendente":
                url = self._store.get_value(it, COL_URL)
                path_str = self._store.get_path(it).to_string()
                resultado.append((url, path_str))
            it = self._store.iter_next(it)
        return resultado

    def _atualizar_status(self, path_str: str, status: str) -> None:
        """Atualiza status de uma linha da ListStore (main thread via GLib.idle_add)."""
        try:
            path = Gtk.TreePath.new_from_string(path_str)
            it = self._store.get_iter(path)
            if it:
                self._store.set_value(it, COL_STATUS, status)
        except Exception:
            pass

    def _salvar_checkpoint(
        self,
        pendentes: list[str],
        concluidas: list[str],
        com_erro: list[str],
        url_atual: str | None,
    ) -> None:
        """Salva checkpoint (main thread via GLib.idle_add)."""
        estado = EstadoCheckpoint(
            urls_pendentes=pendentes,
            urls_concluidas=concluidas,
            urls_com_erro=com_erro,
            url_atual=url_atual,
            timestamp=datetime.now(UTC).isoformat(),
        )
        ckpt.salvar(estado)

    def _finalizar_lote(self, total: int, concluidas: list[str], com_erro: list[str]) -> None:
        """Encerra execução do lote e atualiza UI (main thread)."""
        self._btn_executar.set_sensitive(True)
        ckpt.remover()
        self._btn_retomar.set_sensitive(False)
        self._barra_lote.set_fraction(1.0)
        self._barra_lote.set_text(f"{len(concluidas)} / {total}")
        self._label_status_lote.set_label(f"[OK] Lote concluído — {len(concluidas)} OK, {len(com_erro)} erro(s)")
        logger.info("Lote encerrado: %d/%d URLs", len(concluidas), total)
