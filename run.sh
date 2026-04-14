#!/usr/bin/env bash
# run.sh — Inicializa e executa o Project Beholder com ciclo de vida completo
#
# Responsabilidades:
#   PRE:   verificar venv (instala se ausente), limpar cache Python,
#          encerrar Ollama residual na porta 11435
#   RUN:   ativar venv, iniciar python3 main.py
#   POST:  ao sair (normal, Ctrl+C ou sinal), encerrar Ollama pelo PID exato,
#          limpar OLLAMA_TMPDIR, limpar cache Python — VRAM sempre liberada

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
OLLAMA_PORT=11435
OLLAMA_TMPDIR="/tmp/ollama_beholder"

cd "$PROJECT_DIR"

log()  { echo "[beholder] $*"; }
fail() { echo "[beholder] ERRO: $*" >&2; exit 1; }

# ----------------------------------------------------------------------
# Localizar PID do Ollama na porta 11435
# Usa lsof, ss ou fuser — nunca pkill -f (ADR-03)

encontrar_pid_ollama() {
    if command -v lsof >/dev/null 2>&1; then
        lsof -ti tcp:"$OLLAMA_PORT" 2>/dev/null | head -1 || true
    elif command -v ss >/dev/null 2>&1; then
        ss -tlnp "sport = :$OLLAMA_PORT" 2>/dev/null \
            | grep -oP 'pid=\K[0-9]+' | head -1 || true
    elif command -v fuser >/dev/null 2>&1; then
        fuser "${OLLAMA_PORT}/tcp" 2>/dev/null | awk '{print $1}' || true
    fi
}

# ----------------------------------------------------------------------
# Matar Ollama pelo PID exato (ADR-03)

matar_ollama() {
    local PID
    PID=$(encontrar_pid_ollama)

    if [ -n "$PID" ]; then
        log "Encerrando Ollama (PID $PID)..."
        kill -TERM "$PID" 2>/dev/null || true

        local ESPERA=0
        while kill -0 "$PID" 2>/dev/null && [ "$ESPERA" -lt 5 ]; do
            sleep 1
            ESPERA=$((ESPERA + 1))
        done

        if kill -0 "$PID" 2>/dev/null; then
            kill -KILL "$PID" 2>/dev/null || true
        fi

        log "Ollama encerrado. VRAM liberada."
    fi
}

# ----------------------------------------------------------------------
# Limpar cache Python

limpar_cache_python() {
    find "$PROJECT_DIR/src"   -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_DIR/tests" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_DIR"       -maxdepth 2 -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_DIR"       -name "*.pyc" -delete 2>/dev/null || true
    find "$PROJECT_DIR"       -name "*.pyo" -delete 2>/dev/null || true
}

# ----------------------------------------------------------------------
# Função de limpeza — executada SEMPRE ao sair (trap EXIT)
# Flag evita dupla execução em caso de sinais sobrepostos

_CLEANUP_EXECUTADO=false

cleanup() {
    $_CLEANUP_EXECUTADO && return
    _CLEANUP_EXECUTADO=true

    echo ""
    log "Encerrando Beholder — limpando recursos..."

    matar_ollama

    if [ -d "$OLLAMA_TMPDIR" ]; then
        rm -rf "$OLLAMA_TMPDIR"
        log "OLLAMA_TMPDIR limpo."
    fi

    log "Limpando cache Python..."
    limpar_cache_python

    log "Limpeza concluida. Ate a proxima."
}

trap cleanup EXIT
trap 'exit 130' INT    # Ctrl+C  → EXIT trap executa cleanup
trap 'exit 143' TERM   # SIGTERM → EXIT trap executa cleanup

# ----------------------------------------------------------------------
# PRE-FLIGHT: verificar display GTK

if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
    fail "Nenhum display detectado (DISPLAY/WAYLAND_DISPLAY ausentes).\n       O Beholder requer interface grafica GTK4."
fi

# ----------------------------------------------------------------------
# PRE-FLIGHT: instalar venv se ausente

if [ ! -f "$VENV_DIR/bin/python" ]; then
    log "Ambiente virtual nao encontrado — executando install.sh..."
    bash "$PROJECT_DIR/install.sh"
fi

# Verificacao minima de integridade do venv
"$VENV_DIR/bin/python" -c "import src" 2>/dev/null \
    || fail "venv parece corrompido. Execute: ./install.sh"

# ----------------------------------------------------------------------
# PRE-FLIGHT: limpar estado residual

log "Limpando cache Python anterior..."
limpar_cache_python

OLLAMA_RESIDUAL=$(encontrar_pid_ollama)
if [ -n "$OLLAMA_RESIDUAL" ]; then
    log "Ollama residual detectado na porta $OLLAMA_PORT (PID $OLLAMA_RESIDUAL) — encerrando antes de iniciar..."
    matar_ollama
fi

if [ -d "$OLLAMA_TMPDIR" ]; then
    log "OLLAMA_TMPDIR residual encontrado — limpando..."
    rm -rf "$OLLAMA_TMPDIR"
fi

# ----------------------------------------------------------------------
# INICIAR

log "Iniciando Beholder..."
source "$VENV_DIR/bin/activate"
python3 "$PROJECT_DIR/main.py"

# (cleanup é chamado automaticamente pelo trap EXIT ao sair do python)

# "A felicidade da sua vida depende da qualidade dos seus pensamentos." — Marco Aurelio
