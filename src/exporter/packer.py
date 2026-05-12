"""
Packer — Thread C do pipeline produtor-consumidor.

Consome AssetProcessado de filas.processada, organiza em subpastas por tipo
(ícones/, fundos/, outros/) e compacta em output/beholder_{timestamp}.zip.
Nomes das subpastas lidos de DEFAULTS["Espolio"]["mapa_pastas"] (PT-BR).

ADR-01: callbacks de UI sempre via GLib.idle_add.
"""

import logging
import shutil
import threading
import zipfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from queue import Empty

from gi.repository import GLib

from src.core.asset_queue import SENTINEL, AssetProcessado, filas
from src.core.config.defaults import DEFAULTS
from src.exporter.dataset_writer import escrever_csv, subpasta_tipo

logger = logging.getLogger("beholder.exporter.packer")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

CallbackLog = Callable[[str], None]
CallbackConcluido = Callable[[str], None]  # recebe caminho do zip


class Packer:
    """
    Thread C do pipeline: organiza assets e gera pacote .zip + CSV.

    Args:
        on_log: Linha de log para UI.
        on_concluido: Chamado com o caminho do .zip ao encerrar.
    """

    def __init__(
        self,
        on_log: CallbackLog,
        on_concluido: CallbackConcluido,
    ) -> None:
        self._on_log = on_log
        self._on_concluido = on_concluido
        self._thread: threading.Thread | None = None
        self._evento_parar = threading.Event()
        self._dir_output = _PROJECT_ROOT / DEFAULTS["Saida"]["diretorio_output"]

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def cancelar(self) -> None:
        """Sinaliza para a Thread C encerrar graciosamente."""
        self._evento_parar.set()

    def iniciar(self) -> None:
        """Inicia Thread C. Ignorado se já em execução."""
        if self._thread and self._thread.is_alive():
            logger.warning("Packer já em execução — ignorando iniciar()")
            return
        self._evento_parar.clear()
        self._thread = threading.Thread(
            target=self._executar,
            daemon=True,
            name="beholder-packer",
        )
        self._thread.start()
        logger.info("Packer iniciado")

    def esta_ativo(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ------------------------------------------------------------------
    # Thread C — execução interna
    # ------------------------------------------------------------------

    def _executar(self) -> None:
        """Consome filas.processada até SENTINEL e gera pacote."""
        assets: list[AssetProcessado] = []
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        staging = self._dir_output / f"staging_{timestamp}"

        try:
            while not self._evento_parar.is_set():
                try:
                    item = filas.processada.get(timeout=1.0)
                except Empty:
                    continue
                if item is SENTINEL:
                    logger.info("Packer recebeu SENTINEL — encerrando")
                    break
                asset: AssetProcessado = item
                assets.append(asset)
                self._log(f"[INFO] Empacotando: {Path(asset.caminho_local).name}")

                # Copia arquivo para subpasta organizada (layout híbrido: categoria/site/).
                if asset.caminho_local:
                    src = Path(asset.caminho_local)
                    if src.exists():
                        site_slug = (asset.site_origem or "generic").strip() or "generic"
                        pasta = staging / subpasta_tipo(asset.tipo) / site_slug
                        pasta.mkdir(parents=True, exist_ok=True)
                        destino = pasta / src.name
                        # Evita colisão de nomes
                        if destino.exists():
                            destino = pasta / f"{src.stem}_{len(assets)}{src.suffix}"
                        shutil.copy2(src, destino)

            if not assets:
                self._log("[AVISO] Nenhum asset para empacotar.")
                GLib.idle_add(self._on_concluido, "")
                return

            # Gera CSV de metadados
            csv_path = staging / "metadata.csv"
            escrever_csv(assets, csv_path)

            # Compacta em .zip
            nome_zip = DEFAULTS["Saida"]["formato_zip"].format(timestamp=timestamp)
            zip_path = self._dir_output / nome_zip
            self._dir_output.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for arquivo in staging.rglob("*"):
                    if arquivo.is_file():
                        zf.write(arquivo, arquivo.relative_to(staging))

            # Sprint 21: cópia do CSV fora do ZIP para recuperação de site_origem
            # em reanálises futuras via "ANALISAR PASTA".
            try:
                csv_final = self._dir_output / f"metadata_{timestamp}.csv"
                shutil.copy2(csv_path, csv_final)
                logger.info("CSV de metadados preservado em %s", csv_final)
            except OSError as exc:
                logger.warning("Falha ao preservar cópia do CSV fora do ZIP: %s", exc)

            # Remove staging temporário
            shutil.rmtree(staging, ignore_errors=True)

            # Sprint 22: retenção automática de outputs antigos
            self._podar_outputs_antigos()

            self._log(f"[OK] Pacote gerado: {zip_path} ({len(assets)} assets)")
            GLib.idle_add(self._on_concluido, str(zip_path))

        except Exception as exc:
            logger.exception("Erro no Packer")
            self._log(f"[ERRO] {exc}")
            shutil.rmtree(staging, ignore_errors=True)
            GLib.idle_add(self._on_concluido, "")

    def _podar_outputs_antigos(self) -> None:
        """Mantém apenas os N mais recentes de cada tipo em output/ (Sprint 22).

        N lido de `DEFAULTS["Saida"]["max_pacotes_retidos"]`. Valor 0 desativa.
        Poda independente para ZIPs e CSVs preservados.
        """
        max_retidos = DEFAULTS["Saida"].get("max_pacotes_retidos", 0)
        if max_retidos <= 0:
            return
        if not self._dir_output.exists():
            return

        for padrao in ("beholder_*.zip", "metadata_*.csv"):
            arquivos = sorted(
                self._dir_output.glob(padrao),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for obsoleto in arquivos[max_retidos:]:
                try:
                    obsoleto.unlink()
                    logger.info("Poda de outputs: removido %s", obsoleto.name)
                except OSError as exc:
                    logger.warning("Falha ao remover %s: %s", obsoleto, exc)

    def _log(self, msg: str) -> None:
        GLib.idle_add(self._on_log, msg)
