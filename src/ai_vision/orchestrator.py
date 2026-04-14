"""
Orchestrator — Thread B do pipeline produtor-consumidor.

Consome AssetBruto de filas.scraper, analisa via Moondream e extrai paleta
K-Means, então posta AssetProcessado em filas.processada.

ADR-01: Este é o ÚNICO módulo que invoca moondream_prompt.analisar_imagem().
Toda comunicação com Ollama passa aqui — nunca de fora deste módulo.
"""

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from queue import Empty

from gi.repository import GLib

from src.ai_vision.moondream_prompt import analisar_imagem
from src.core.asset_queue import SENTINEL, AssetBruto, AssetProcessado, filas
from src.core.config.defaults import DEFAULTS
from src.transformer.icon_alchemist import extrair_paleta

logger = logging.getLogger("beholder.ai_vision.orchestrator")

CallbackLog = Callable[[str], None]
CallbackAsset = Callable[[AssetProcessado], None]
CallbackConcluido = Callable[[int], None]


class Orchestrator:
    """
    Thread B do pipeline: análise por Moondream + extração de paleta K-Means.

    Args:
        on_log: Chamado com cada linha de log.
        on_asset: Chamado com cada AssetProcessado via GLib.idle_add.
        on_concluido: Chamado ao encerrar com o total de assets analisados.
    """

    def __init__(
        self,
        on_log: CallbackLog,
        on_asset: CallbackAsset,
        on_concluido: CallbackConcluido,
    ) -> None:
        self._on_log = on_log
        self._on_asset = on_asset
        self._on_concluido = on_concluido

        self._thread: threading.Thread | None = None
        self._evento_parar = threading.Event()
        self._evento_pausar = threading.Event()
        self._evento_pausar.set()  # set = rodando; clear = pausado

        self._kmeans_cores: int = DEFAULTS["Saida"]["kmeans_cores"]

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def iniciar(self) -> None:
        """Inicia Thread B. Ignorado se já em execução."""
        if self._thread and self._thread.is_alive():
            logger.warning("Orchestrator já em execução — ignorando iniciar()")
            return
        self._evento_parar.clear()
        self._evento_pausar.set()
        self._thread = threading.Thread(
            target=self._executar,
            daemon=True,
            name="beholder-orchestrator",
        )
        self._thread.start()
        logger.info("Orchestrator iniciado")

    def pausar(self) -> None:
        """Pausa o processamento entre assets."""
        self._evento_pausar.clear()
        self._log("[INFO] Orquestrador pausado.")

    def retomar(self) -> None:
        """Retoma após pausa."""
        self._evento_pausar.set()
        self._log("[INFO] Orquestrador retomado.")

    def cancelar(self) -> None:
        """Cancela o processamento. A thread encerra graciosamente."""
        self._evento_parar.set()
        self._evento_pausar.set()

    def esta_ativo(self) -> bool:
        """True se a thread está rodando."""
        return bool(self._thread and self._thread.is_alive())

    # ------------------------------------------------------------------
    # Thread B — execução interna
    # ------------------------------------------------------------------

    def _executar(self) -> None:
        """Corpo da Thread B: consome filas.scraper até SENTINEL."""
        total = 0
        try:
            while True:
                if self._evento_parar.is_set():
                    break

                self._evento_pausar.wait()
                if self._evento_parar.is_set():
                    break

                try:
                    item = filas.scraper.get(timeout=1.0)
                except Empty:
                    continue

                if item is SENTINEL:
                    logger.info("Orchestrator recebeu SENTINEL — encerrando")
                    break

                asset_bruto: AssetBruto = item

                if not asset_bruto.caminho_local:
                    self._log(f"[AVISO] Asset sem caminho local ignorado: {asset_bruto.url}")
                    continue

                self._log(f"[INFO] Analisando: {asset_bruto.url}")

                analise = analisar_imagem(asset_bruto.caminho_local)

                paleta: list[str] = []
                try:
                    paleta = extrair_paleta(asset_bruto.caminho_local, n_cores=self._kmeans_cores)
                except Exception as exc:
                    logger.warning("K-Means falhou para %s: %s", asset_bruto.caminho_local, exc)

                processado = AssetProcessado(
                    url_original=asset_bruto.url,
                    caminho_local=asset_bruto.caminho_local,
                    tipo=analise.get("tipo", asset_bruto.tipo),
                    descricao=analise.get("descricao", ""),
                    tags=analise.get("tags", []),
                    paleta_hex=paleta,
                    timestamp=datetime.now(UTC).isoformat(),
                )

                filas.processada.put(processado)
                total += 1

                paleta_resumida = ", ".join(paleta[:2]) if paleta else "—"
                self._log(f"[OK] {processado.tipo.upper()} — {processado.descricao[:60]} | cores: {paleta_resumida}")
                GLib.idle_add(self._on_asset, processado)

        except Exception as exc:
            logger.exception("Erro inesperado no Orchestrator")
            self._log(f"[ERRO] {exc}")
        finally:
            filas.processada.put(SENTINEL)
            self._log(f"[INFO] Orquestrador encerrado — {total} assets analisados.")
            GLib.idle_add(self._on_concluido, total)

    # ------------------------------------------------------------------
    # Helpers GLib.idle_add (ADR-01)
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        GLib.idle_add(self._on_log, msg)
