#!/usr/bin/env bash
# teardown.sh — Encerra o Ollama e libera VRAM (mecanismo de emergência — ADR-03)
#
# Uso: ./teardown.sh
# Pode ser chamado a qualquer momento, mesmo sem o Beholder rodando.
# Mata o Ollama pelo PID exato via porta 11435 — nunca pkill -f ollama.

OLLAMA_PORT=11435
# Caminho do OLLAMA_TMPDIR dentro do projeto (não em /tmp)
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
OLLAMA_TMPDIR="$PROJECT_DIR/data/ollama_tmp"

log()  { echo "[teardown] $*"; }

# Localizar PID do Ollama na porta 11435 (ADR-03: porta exclusiva do Beholder)
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

# Encerrar Ollama
OLLAMA_PID=$(encontrar_pid_ollama)

if [ -n "$OLLAMA_PID" ]; then
    log "Encerrando Ollama (PID $OLLAMA_PID) na porta $OLLAMA_PORT..."
    kill -TERM "$OLLAMA_PID" 2>/dev/null || true

    # Aguardar encerramento gracioso (máximo 5 segundos)
    ESPERA=0
    while kill -0 "$OLLAMA_PID" 2>/dev/null && [ "$ESPERA" -lt 5 ]; do
        sleep 1
        ESPERA=$((ESPERA + 1))
    done

    # Forçar se ainda estiver vivo
    if kill -0 "$OLLAMA_PID" 2>/dev/null; then
        log "Forçando encerramento (SIGKILL)..."
        kill -KILL "$OLLAMA_PID" 2>/dev/null || true
    fi

    log "Ollama encerrado. VRAM liberada."
else
    log "Nenhum Ollama ativo na porta $OLLAMA_PORT."
fi

# Limpar diretório temporário do Ollama
if [ -d "$OLLAMA_TMPDIR" ]; then
    rm -rf "$OLLAMA_TMPDIR"
    log "OLLAMA_TMPDIR limpo ($OLLAMA_TMPDIR)."
fi

log "Teardown concluído."

# "Retire o que é desnecessário e você encontrará o suficiente." — Marco Aurélio
