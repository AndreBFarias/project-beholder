"""
Orchestrator — Thread B do pipeline produtor-consumidor.

Consome AssetBruto de filas.scraper, analisa via Moondream e extrai paleta
K-Means, então posta AssetProcessado em filas.processada.

ADR-01: Este é o ÚNICO módulo que invoca moondream_prompt.analisar_imagem().
Toda comunicação com Ollama passa aqui — nunca de fora deste módulo.
"""

import csv
import logging
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from queue import Empty, Full

from gi.repository import GLib

from src.ai_vision.moondream_prompt import analisar_imagem
from src.core.asset_queue import SENTINEL, AssetBruto, AssetProcessado, filas
from src.core.config.defaults import DEFAULTS
from src.scraper.site_registry import resolver_strategy
from src.transformer.icon_alchemist import extrair_paleta

_SUFIXOS_IMAGEM = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg")

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

    def iniciar(self, pausado: bool = False) -> None:
        """Inicia Thread B. Ignorado se já em execução.

        Args:
            pausado: se True, thread arranca em estado pausado (bloqueada no
                `_evento_pausar.wait()`). Chamar `retomar()` para liberar.
                Use em cenários com Ollama subindo assincronamente para evitar
                consumo prematuro de SENTINEL (race condition Busca→Cortex).
        """
        if self._thread and self._thread.is_alive():
            logger.warning("Orchestrator já em execução — ignorando iniciar()")
            return
        # Recarrega config de DEFAULTS (ADR-02)
        self._kmeans_cores = DEFAULTS["Saida"]["kmeans_cores"]
        self._evento_parar.clear()
        if pausado:
            self._evento_pausar.clear()
        else:
            self._evento_pausar.set()
        self._thread = threading.Thread(
            target=self._executar,
            daemon=True,
            name="beholder-orchestrator",
        )
        self._thread.start()
        logger.info("Orchestrator iniciado (pausado=%s)", pausado)

    def analisar_pasta_local(
        self,
        diretorio: str | Path,
        sufixos: tuple[str, ...] = _SUFIXOS_IMAGEM,
    ) -> int:
        """Varre diretório local e injeta assets já baixados na fila.

        Permite reanalisar imagens sem precisar rescrapar o site.
        Não chama `filas.nova_sessao()` — assume que o chamador quer injetar
        num estado de fila limpa ou complementar assets já existentes.

        Args:
            diretorio: pasta a varrer (não recursivo por padrão de `Path.iterdir`).
            sufixos: extensões aceitas (tuple lowercase com ponto).

        Returns:
            Quantidade de assets enfileirados.
        """
        diretorio = Path(diretorio)
        if not diretorio.exists() or not diretorio.is_dir():
            self._log(f"[ERRO] Diretório inexistente: {diretorio}")
            logger.error("analisar_pasta_local: diretório inválido %s", diretorio)
            return 0

        mapa_sites = self._construir_mapa_sites(diretorio)
        if mapa_sites:
            self._log(f"[INFO] {len(mapa_sites)} arquivos com site_origem recuperado de CSVs antigos")

        enfileirados = 0
        recuperados_csv = 0
        recuperados_subpasta = 0
        for arquivo in sorted(diretorio.rglob("*")):
            if not arquivo.is_file():
                continue
            if arquivo.suffix.lower() not in sufixos:
                continue

            # Prioridade 1: CSV antigo
            try:
                chave = str(arquivo.resolve())
            except OSError:
                chave = str(arquivo)
            site_hint = mapa_sites.get(chave)
            if site_hint:
                recuperados_csv += 1
            else:
                # Prioridade 2: nome da subpasta imediata
                try:
                    relativo = arquivo.relative_to(diretorio)
                    if len(relativo.parts) > 1:
                        site_hint = relativo.parts[0]
                        recuperados_subpasta += 1
                except ValueError:
                    pass

            asset = AssetBruto(
                url=arquivo.as_uri(),
                caminho_local=str(arquivo),
                tipo="image",
                origem="local",
                site_origem_hint=site_hint,
            )
            try:
                filas.scraper.put(asset, timeout=5.0)
                enfileirados += 1
            except Full:
                self._log(f"[AVISO] Fila cheia — arquivo ignorado: {arquivo.name}")
                logger.warning("Fila scraper cheia ao enfileirar %s", arquivo)
                break

        if recuperados_csv or recuperados_subpasta:
            self._log(f"[INFO] site_origem recuperado: {recuperados_csv} via CSV, {recuperados_subpasta} via subpasta")

        try:
            filas.scraper.put(SENTINEL, timeout=5.0)
        except Full:
            logger.warning("Fila cheia ao enviar SENTINEL de pasta local")

        self._log(f"[INFO] Modo pasta local: {enfileirados} arquivos enfileirados de {diretorio}")
        logger.info("analisar_pasta_local: %d assets enfileirados de %s", enfileirados, diretorio)
        return enfileirados

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
                    if total == 0:
                        self._log(
                            "[AVISO] Nenhum asset para analisar — a fila estava vazia. "
                            "Use a Busca para baixar imagens ou clique em ANALISAR PASTA."
                        )
                        logger.warning("Orchestrator encerrou sem processar assets (fila vazia)")
                    else:
                        logger.info("Orchestrator recebeu SENTINEL — encerrando (%d analisados)", total)
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

                # Sprint 21: hint explícito tem prioridade sobre resolução por URL.
                site_origem = asset_bruto.site_origem_hint or resolver_strategy(asset_bruto.origem).nome
                processado = AssetProcessado(
                    url_original=asset_bruto.url,
                    caminho_local=asset_bruto.caminho_local,
                    tipo=analise.get("tipo", asset_bruto.tipo),
                    descricao=analise.get("descricao", ""),
                    tags=analise.get("tags", []),
                    paleta_hex=paleta,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    site_origem=site_origem,
                )

                try:
                    filas.processada.put(processado, timeout=10.0)
                except Full:
                    self._log(f"[AVISO] Fila processada cheia — asset descartado: {asset_bruto.url}")
                    logger.warning("Fila processada cheia — asset descartado: %s", asset_bruto.url)
                    continue
                total += 1

                paleta_resumida = ", ".join(paleta[:2]) if paleta else "—"
                self._log(f"[OK] {processado.tipo.upper()} — {processado.descricao[:60]} | cores: {paleta_resumida}")
                GLib.idle_add(self._on_asset, processado)

        except Exception as exc:
            logger.exception("Erro inesperado no Orchestrator")
            self._log(f"[ERRO] {exc}")
        finally:
            try:
                filas.processada.put(SENTINEL, timeout=30.0)
            except Full:
                logger.warning("Fila processada cheia ao enviar SENTINEL — drenando")
                while not filas.processada.empty():
                    try:
                        filas.processada.get_nowait()
                    except Empty:
                        break
                filas.processada.put(SENTINEL)
            self._log(f"[INFO] Orquestrador encerrado — {total} assets analisados.")
            GLib.idle_add(self._on_concluido, total)

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _construir_mapa_sites(self, diretorio: Path) -> dict[str, str]:
        """Mapeia caminho_local absoluto → site_origem a partir de CSVs antigos.

        Fontes (Sprint 21):
        1. CSVs dentro de `diretorio` (qualquer nível) — ex: exportações manuais.
        2. CSVs em `{PROJECT_ROOT}/{DEFAULTS.Saida.diretorio_output}` — cópias
           geradas pelo Packer fora do ZIP.
        Ignora site_origem == "generic" (não carrega informação útil).
        """
        project_root = Path(__file__).resolve().parent.parent.parent
        output_dir = project_root / DEFAULTS["Saida"]["diretorio_output"]

        candidatos: list[Path] = []
        for padrao in ("*.csv",):
            try:
                candidatos.extend(diretorio.rglob(padrao))
            except OSError:
                pass
            if output_dir.exists():
                try:
                    candidatos.extend(output_dir.glob(padrao))
                except OSError:
                    pass

        mapa: dict[str, str] = {}
        for csv_path in candidatos:
            try:
                with csv_path.open(encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    if not reader.fieldnames or "caminho_local" not in reader.fieldnames:
                        continue
                    for linha in reader:
                        caminho = (linha.get("caminho_local") or "").strip()
                        site = (linha.get("site_origem") or "").strip()
                        if not caminho or not site or site == "generic":
                            continue
                        p = Path(caminho)
                        if not p.is_absolute():
                            p = project_root / caminho
                        try:
                            chave = str(p.resolve())
                        except OSError:
                            continue
                        mapa.setdefault(chave, site)
            except (OSError, csv.Error) as exc:
                logger.debug("Ignorando CSV %s: %s", csv_path, exc)
        return mapa

    # ------------------------------------------------------------------
    # Helpers GLib.idle_add (ADR-01)
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        GLib.idle_add(self._on_log, msg)
