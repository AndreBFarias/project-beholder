"""
Packer — Thread C do pipeline produtor-consumidor.

Consome AssetProcessado de filas.processada, organiza em subpastas por tipo
(icons/, backgrounds/, outros/) e compacta em output/beholder_{timestamp}.zip.

ADR-01: callbacks de UI sempre via GLib.idle_add.
"""

import logging
import shutil
import threading
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from gi.repository import GLib

from src.core.asset_queue import SENTINEL, AssetProcessado, filas
from src.core.config.defaults import DEFAULTS
from src.exporter.dataset_writer import escrever_csv, subpasta_tipo

logger = logging.getLogger("beholder.exporter.packer")

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
        self._dir_output = Path(DEFAULTS["Saida"]["diretorio_output"])

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def iniciar(self) -> None:
        """Inicia Thread C. Ignorado se já em execução."""
        if self._thread and self._thread.is_alive():
            logger.warning("Packer já em execução — ignorando iniciar()")
            return
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
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        staging = self._dir_output / f"staging_{timestamp}"

        try:
            while True:
                item = filas.processada.get()
                if item is SENTINEL:
                    logger.info("Packer recebeu SENTINEL — encerrando")
                    break
                asset: AssetProcessado = item
                assets.append(asset)
                self._log(f"[INFO] Empacotando: {Path(asset.caminho_local).name}")

                # Copia arquivo para subpasta organizada
                if asset.caminho_local:
                    src = Path(asset.caminho_local)
                    if src.exists():
                        pasta = staging / subpasta_tipo(asset.tipo)
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

            # Remove staging temporário
            shutil.rmtree(staging, ignore_errors=True)

            self._log(f"[OK] Pacote gerado: {zip_path} ({len(assets)} assets)")
            GLib.idle_add(self._on_concluido, str(zip_path))

        except Exception as exc:
            logger.exception("Erro no Packer")
            self._log(f"[ERRO] {exc}")
            shutil.rmtree(staging, ignore_errors=True)
            GLib.idle_add(self._on_concluido, "")

    def _log(self, msg: str) -> None:
        GLib.idle_add(self._on_log, msg)
