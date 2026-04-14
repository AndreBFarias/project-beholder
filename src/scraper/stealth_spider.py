"""
StealthSpider — Thread A do pipeline produtor-consumidor.

Dois modos de operação:
- Normal  : requests com backoff exponencial
- Furtivo : Playwright headless com evasão de fingerprint (UA aleatório,
            viewport variado, navigator.webdriver mascarado, backoff em 429/403)

Toda atualização de UI é feita via GLib.idle_add (ADR-01).

Fluxo:
    StealthSpider.iniciar(url, modo_furtivo=False)
        → thread._executar()
            → _get_com_retry(url) ou _get_playwright(url)  → HTML
            → extrair_assets(html, url)  → list[AssetBruto]
            → _baixar_asset(asset)  → Path
            → filas.scraper.put(asset)
        → filas.scraper.put(SENTINEL)  → sinaliza fim para Thread B
"""

import hashlib
import logging
import random
import threading
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

import requests
from gi.repository import GLib

from src.core.asset_queue import SENTINEL, AssetBruto, filas
from src.core.config.defaults import DEFAULTS
from src.scraper.html_parser import extrair_assets

logger = logging.getLogger("beholder.scraper.stealth_spider")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# User-agents realistas para rotação no modo furtivo
USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.46",
]

VIEWPORTS = [
    {"width": 1280, "height": 720},
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1920, "height": 1080},
    {"width": 1600, "height": 900},
]

# Executado antes do JS da página — mascara sinais de automação
SCRIPT_EVASAO = (
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});"
    "Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR', 'pt', 'en-US', 'en']});"
)

CallbackLog = Callable[[str], None]
CallbackProgresso = Callable[[float, str], None]
CallbackConcluido = Callable[[int], None]


class StealthSpider:
    """
    Scraper de assets em thread separada (Thread A do pipeline).

    Args:
        on_log: Função chamada com cada linha de log (str).
        on_progresso: Função chamada com (fração 0.0–1.0, texto descritivo).
        on_concluido: Função chamada ao encerrar com o total de assets baixados.
    """

    def __init__(
        self,
        on_log: CallbackLog,
        on_progresso: CallbackProgresso,
        on_concluido: CallbackConcluido,
    ) -> None:
        self._on_log = on_log
        self._on_progresso = on_progresso
        self._on_concluido = on_concluido

        self._thread: threading.Thread | None = None
        self._evento_parar = threading.Event()
        self._evento_pausar = threading.Event()
        self._evento_pausar.set()  # set = rodando; clear = pausado

        cfg = DEFAULTS["Scraper"]
        self._timeout: int = cfg["timeout"]
        self._delay_min: float = cfg["delay_min"]
        self._delay_max: float = cfg["delay_max"]
        self._max_retries: int = cfg["max_retries"]
        self._user_agent: str = cfg["user_agent"]

        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self._user_agent})

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def iniciar(self, url: str, diretorio_saida: str | None = None, modo_furtivo: bool = False) -> None:
        """Inicia o scraping em thread separada. Ignorado se já em execução.

        Args:
            url: Página alvo.
            diretorio_saida: Pasta local onde os assets serão salvos.
            modo_furtivo: Se True, usa Playwright com evasão de fingerprint.
        """
        if self._thread and self._thread.is_alive():
            logger.warning("Spider já em execução — ignorando iniciar()")
            return

        self._evento_parar.clear()
        self._evento_pausar.set()

        self._thread = threading.Thread(
            target=self._executar,
            args=(url, diretorio_saida, modo_furtivo),
            daemon=True,
            name="beholder-spider",
        )
        self._thread.start()
        logger.info("StealthSpider iniciado para %s (furtivo=%s)", url, modo_furtivo)

    def pausar(self) -> None:
        """Pausa a thread entre downloads. Retomável via retomar()."""
        self._evento_pausar.clear()
        self._log("[INFO] Scraping pausado.")
        logger.info("StealthSpider pausado")

    def retomar(self) -> None:
        """Retoma a thread após pausa."""
        self._evento_pausar.set()
        self._log("[INFO] Scraping retomado.")
        logger.info("StealthSpider retomado")

    def cancelar(self) -> None:
        """Cancela a operação atual. A thread encerra graciosamente."""
        self._evento_parar.set()
        self._evento_pausar.set()  # desbloqueia se estava pausado
        self._log("[INFO] Scraping cancelado.")
        logger.info("StealthSpider cancelado")

    def esta_pausado(self) -> bool:
        """True se o spider está ativamente pausado."""
        return not self._evento_pausar.is_set()

    def esta_ativo(self) -> bool:
        """True se a thread de scraping está rodando."""
        return bool(self._thread and self._thread.is_alive())

    # ------------------------------------------------------------------
    # Thread A — execução interna
    # ------------------------------------------------------------------

    def _executar(self, url: str, diretorio_saida: str | None, modo_furtivo: bool) -> None:
        """Corpo da Thread A: baixa página, extrai e baixa assets."""
        dir_saida = Path(diretorio_saida) if diretorio_saida else _PROJECT_ROOT / DEFAULTS["Saida"]["diretorio_data"]
        dir_saida.mkdir(parents=True, exist_ok=True)
        total_baixados = 0

        try:
            if modo_furtivo:
                self._log("[INFO] Modo furtivo ativo — Playwright com evasão de fingerprint.")
                self._progresso(0.05, "Modo furtivo: iniciando Playwright...")
                html = self._get_playwright(url)
            else:
                self._log(f"[INFO] Conectando a {url} ...")
                self._progresso(0.05, "Baixando página...")
                html = self._get_com_retry(url)

            if html is None:
                self._log(f"[ERRO] Falha ao baixar {url} após {self._max_retries} tentativas.")
                self._progresso(0.0, "Erro ao conectar")
                return

            self._log(f"[OK] Página baixada ({len(html)} bytes)")
            self._progresso(0.1, "Analisando HTML...")

            assets = extrair_assets(html, url)
            total = len(assets)
            self._log(f"[INFO] {total} assets encontrados.")

            if total == 0:
                self._progresso(1.0, "Nenhum asset encontrado")
                return

            for i, asset in enumerate(assets):
                if self._evento_parar.is_set():
                    break

                # Bloqueia enquanto pausado (libera ao retomar ou cancelar)
                self._evento_pausar.wait()
                if self._evento_parar.is_set():
                    break

                fracao = 0.1 + (i / total) * 0.9
                self._progresso(fracao, f"Asset {i + 1} / {total}")

                caminho = self._baixar_asset(asset, dir_saida)
                if caminho:
                    asset.caminho_local = str(caminho)
                    filas.scraper.put(asset)
                    total_baixados += 1
                    self._log(f"[OK] {asset.tipo.upper()} — {asset.url}")
                else:
                    self._log(f"[AVISO] Falha ao baixar: {asset.url}")

                # Jitter entre downloads para evitar bloqueio por rate-limit
                if i < total - 1 and not self._evento_parar.is_set():
                    time.sleep(random.uniform(self._delay_min, self._delay_max))

        except Exception as exc:
            logger.exception("Erro inesperado no StealthSpider")
            self._log(f"[ERRO] Exceção inesperada: {exc}")
        finally:
            filas.scraper.put(SENTINEL)

            if self._evento_parar.is_set():
                texto_final = f"Cancelado — {total_baixados} assets baixados."
            else:
                texto_final = f"Concluído — {total_baixados} assets baixados."

            self._progresso(1.0, texto_final)
            self._log(f"[INFO] {texto_final}")
            self._concluido(total_baixados)

    def _get_com_retry(self, url: str) -> str | None:
        """GET com backoff exponencial. Retorna o HTML ou None em caso de falha."""
        for tentativa in range(1, self._max_retries + 1):
            if self._evento_parar.is_set():
                return None
            try:
                resp = self._session.get(url, timeout=self._timeout)
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            except requests.RequestException as exc:
                logger.warning("Tentativa %d falhou (%s): %s", tentativa, url, exc)
                if tentativa < self._max_retries:
                    espera = 2**tentativa
                    self._log(f"[AVISO] Tentativa {tentativa} falhou — aguardando {espera}s...")
                    time.sleep(espera)
        return None

    def _baixar_asset(self, asset: AssetBruto, diretorio: Path) -> Path | None:
        """Baixa um único asset para disco. Retorna o Path salvo ou None."""
        try:
            nome = Path(urlparse(asset.url).path).name
            if not nome or "." not in nome:
                nome = f"asset_{hashlib.md5(asset.url.encode()).hexdigest()[:12]}.bin"

            caminho = diretorio / nome

            # Reutiliza arquivo já baixado
            if caminho.exists():
                return caminho

            resp = self._session.get(asset.url, timeout=self._timeout, stream=True)
            resp.raise_for_status()

            with caminho.open("wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    if self._evento_parar.is_set():
                        caminho.unlink(missing_ok=True)
                        return None
                    fh.write(chunk)

            return caminho
        except Exception as exc:
            logger.debug("Falha ao baixar %s: %s", asset.url, exc)
            return None

    def _get_playwright(self, url: str) -> str | None:
        """Obtém HTML via Playwright headless com evasão de fingerprint.

        Mascara navigator.webdriver, rotaciona user-agent e viewport.
        Aplica backoff exponencial em respostas 429/403.
        """
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright

        user_agent = random.choice(USER_AGENTS)
        viewport = random.choice(VIEWPORTS)

        self._log(f"[INFO] Playwright — UA: {user_agent[:60]}...")
        self._log(f"[INFO] Playwright — viewport: {viewport['width']}x{viewport['height']}")

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                ctx = browser.new_context(
                    user_agent=user_agent,
                    viewport=viewport,
                    locale="pt-BR",
                    timezone_id="America/Sao_Paulo",
                )
                ctx.add_init_script(SCRIPT_EVASAO)
                page = ctx.new_page()

                for tentativa in range(1, self._max_retries + 1):
                    if self._evento_parar.is_set():
                        return None
                    try:
                        resp = page.goto(url, timeout=self._timeout * 1000, wait_until="domcontentloaded")
                        if resp and resp.status in (429, 403):
                            espera = 2**tentativa
                            self._log(
                                f"[AVISO] HTTP {resp.status} — backoff {espera}s "
                                f"(tentativa {tentativa}/{self._max_retries})..."
                            )
                            time.sleep(espera)
                            continue
                        html = page.content()
                        self._log(f"[OK] Página capturada via Playwright ({len(html)} bytes)")
                        return html
                    except PlaywrightError as exc:
                        logger.warning("Playwright tentativa %d: %s", tentativa, exc)
                        if tentativa < self._max_retries:
                            espera = 2**tentativa
                            self._log(f"[AVISO] Tentativa {tentativa} falhou — aguardando {espera}s...")
                            time.sleep(espera)

                self._log(f"[ERRO] Playwright falhou após {self._max_retries} tentativas.")
                return None
            finally:
                browser.close()

    # ------------------------------------------------------------------
    # Helpers GLib.idle_add (ADR-01 — nunca tocar UI direto de thread)
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        GLib.idle_add(self._on_log, msg)

    def _progresso(self, fracao: float, texto: str) -> None:
        GLib.idle_add(self._on_progresso, fracao, texto)

    def _concluido(self, total: int) -> None:
        GLib.idle_add(self._on_concluido, total)
