"""
OllamaLifecycle — Gerencia o ciclo de vida do processo Ollama isolado.

ADR-03:
- Binário exclusivo: PROJECT_DIR/bin/ollama (NUNCA o ollama do sistema)
- Porta isolada: 11435 (NUNCA a 11434 padrão do sistema)
- Kill pelo PID exato: os.kill(pid, SIGTERM) + wait(5s) + SIGKILL se necessário
- NUNCA pkill -f ollama — mata instâncias do sistema hospedeiro
"""

import logging
import os
import signal
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path

import httpx
from gi.repository import GLib

from src.core.config.defaults import DEFAULTS

logger = logging.getLogger("beholder.ai_vision.ollama_lifecycle")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_cfg_ia = DEFAULTS["IA"]
PORTA_OLLAMA: int = _cfg_ia["ollama_port"]  # 11435
BASE_URL = f"http://127.0.0.1:{PORTA_OLLAMA}"
TIMEOUT_STARTUP = 30  # segundos aguardando Ollama responder na porta
TIMEOUT_SIGTERM = 5  # segundos antes de escalar para SIGKILL


class OllamaLifecycle:
    """
    Sobe e encerra o processo Ollama isolado do sistema hospedeiro.

    Garante que ./bin/ollama roda exclusivamente na porta 11435, com
    TMPDIR e MODELS dentro do diretório do projeto (sem poluir o sistema).

    Todos os callbacks de UI são chamados via GLib.idle_add (ADR-01).
    """

    def __init__(self) -> None:
        self._processo: subprocess.Popen | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------

    def esta_ativo(self) -> bool:
        """True se o processo Ollama está rodando."""
        return self._rodando()

    @property
    def pid(self) -> int | None:
        """PID do processo ativo ou None."""
        return self._processo.pid if self._rodando() else None

    def ping(self) -> bool:
        """Verifica se Ollama responde na porta 11435. Síncrono, timeout 2s."""
        try:
            with httpx.Client(timeout=2.0) as client:
                return client.get(f"{BASE_URL}/api/tags").status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # API pública — executam em thread separada
    # ------------------------------------------------------------------

    def subir(
        self,
        on_pronto: Callable[[str], None],
        on_erro: Callable[[str], None],
    ) -> None:
        """Sobe o Ollama em thread separada.

        Chama on_pronto(msg) quando pronto ou on_erro(msg) em caso de falha.
        Ignorado se o processo já está ativo.
        """
        if self._rodando():
            GLib.idle_add(on_pronto, f"Ollama já ativo (PID {self._processo.pid})")
            return

        threading.Thread(
            target=self._thread_subir,
            args=(on_pronto, on_erro),
            daemon=True,
            name="beholder-ollama-up",
        ).start()

    def expurgar(self, on_concluido: Callable[[], None] | None = None) -> None:
        """Mata o processo Ollama pelo PID exato em thread separada.

        SIGTERM → wait(5s) → SIGKILL. NUNCA pkill.
        Chama on_concluido() via GLib.idle_add ao encerrar.
        """
        if not self._rodando():
            if on_concluido:
                GLib.idle_add(on_concluido)
            return

        threading.Thread(
            target=self._thread_expurgar,
            args=(on_concluido,),
            daemon=True,
            name="beholder-ollama-kill",
        ).start()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _rodando(self) -> bool:
        return self._processo is not None and self._processo.poll() is None

    def _thread_subir(
        self,
        on_pronto: Callable[[str], None],
        on_erro: Callable[[str], None],
    ) -> None:
        """Corpo da thread de inicialização."""
        binario = _PROJECT_ROOT / "bin" / "ollama"

        if not binario.exists():
            msg = f"Binário não encontrado: {binario}"
            logger.error(msg)
            GLib.idle_add(on_erro, msg)
            return

        env = os.environ.copy()
        env["OLLAMA_HOST"] = f"127.0.0.1:{PORTA_OLLAMA}"
        env["OLLAMA_TMPDIR"] = str(_PROJECT_ROOT / _cfg_ia["ollama_tmpdir"])
        env["OLLAMA_MODELS"] = str(_PROJECT_ROOT / _cfg_ia["ollama_models"])

        Path(env["OLLAMA_TMPDIR"]).mkdir(parents=True, exist_ok=True)
        Path(env["OLLAMA_MODELS"]).mkdir(parents=True, exist_ok=True)

        with self._lock:
            try:
                self._processo = subprocess.Popen(
                    [str(binario), "serve"],
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                logger.info("Ollama iniciado — PID %d, porta %d", self._processo.pid, PORTA_OLLAMA)
            except OSError as exc:
                msg = f"Falha ao iniciar Ollama: {exc}"
                logger.error(msg)
                GLib.idle_add(on_erro, msg)
                return

        # Aguardar até o endpoint responder
        inicio = time.monotonic()
        while time.monotonic() - inicio < TIMEOUT_STARTUP:
            if not self._rodando():
                msg = "Ollama encerrou inesperadamente durante inicialização."
                logger.error(msg)
                GLib.idle_add(on_erro, msg)
                return
            if self.ping():
                msg = f"Ollama ativo — PID {self._processo.pid}, porta {PORTA_OLLAMA}"
                logger.info(msg)
                GLib.idle_add(on_pronto, msg)
                return
            time.sleep(0.5)

        msg = f"Timeout: Ollama não respondeu em {TIMEOUT_STARTUP}s."
        logger.error(msg)
        GLib.idle_add(on_erro, msg)

    def _thread_expurgar(self, on_concluido: Callable[[], None] | None) -> None:
        """Corpo da thread de encerramento."""
        with self._lock:
            if not self._rodando():
                if on_concluido:
                    GLib.idle_add(on_concluido)
                return

            pid = self._processo.pid
            logger.info("Expurgando Ollama PID %d via SIGTERM", pid)

            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                logger.warning("PID %d já não existe", pid)
                self._processo = None
                if on_concluido:
                    GLib.idle_add(on_concluido)
                return

            try:
                self._processo.wait(timeout=TIMEOUT_SIGTERM)
                logger.info("Ollama PID %d encerrado via SIGTERM", pid)
            except subprocess.TimeoutExpired:
                logger.warning("Timeout SIGTERM — escalando para SIGKILL (PID %d)", pid)
                try:
                    os.kill(pid, signal.SIGKILL)
                    self._processo.wait(timeout=2)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    pass

            self._processo = None

        logger.info("Ollama expurgado com sucesso")
        if on_concluido:
            GLib.idle_add(on_concluido)
