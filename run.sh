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
# Tudo relacionado ao Ollama fica dentro do projeto — nada em ~/.ollama ou /tmp
OLLAMA_TMPDIR="$PROJECT_DIR/data/ollama_tmp"
OLLAMA_MODELS="$PROJECT_DIR/models"

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
# Modelos de visão — 3 tiers (sincronizado com defaults.py)
MODELOS_VISAO="moondream minicpm-v llava:7b"

# Verificar e baixar modelos de visão via Ollama

verificar_modelos_ollama() {
    local OLLAMA_BIN="$PROJECT_DIR/bin/ollama"

    if [ ! -f "$OLLAMA_BIN" ]; then
        log "AVISO: bin/ollama ausente — verificação de modelos ignorada"
        return 0
    fi

    export OLLAMA_HOST="127.0.0.1:$OLLAMA_PORT"
    export OLLAMA_MODELS="$OLLAMA_MODELS"

    # Verificar quais modelos faltam
    local FALTANDO=""
    for modelo in $MODELOS_VISAO; do
        local nome_dir
        nome_dir=$(echo "$modelo" | tr ':' '/')
        if [ -d "$OLLAMA_MODELS/manifests" ] && \
           find "$OLLAMA_MODELS/manifests" -path "*${nome_dir}*" -type f 2>/dev/null | grep -q .; then
            log "Modelo $modelo já presente."
        else
            FALTANDO="$FALTANDO $modelo"
        fi
    done

    if [ -z "$FALTANDO" ]; then
        log "Todos os modelos de visão já presentes."
        return 0
    fi

    log "Modelos ausentes:$FALTANDO"
    log "Iniciando download — isso pode levar vários minutos na primeira execução."

    # Subir Ollama temporariamente para baixar os modelos
    mkdir -p "$OLLAMA_TMPDIR"
    mkdir -p "$OLLAMA_MODELS"

    OLLAMA_TMPDIR="$OLLAMA_TMPDIR" "$OLLAMA_BIN" serve &
    local SERVE_PID=$!

    # Aguardar Ollama ficar pronto (máximo 30s)
    local ESPERA=0
    while ! curl -s "http://127.0.0.1:$OLLAMA_PORT/api/tags" >/dev/null 2>&1; do
        sleep 1
        ESPERA=$((ESPERA + 1))
        if [ "$ESPERA" -ge 30 ]; then
            log "AVISO: Ollama não respondeu em 30s — download dos modelos ignorado"
            kill -TERM "$SERVE_PID" 2>/dev/null || true
            wait "$SERVE_PID" 2>/dev/null || true
            return 0
        fi
    done

    # Baixar cada modelo ausente (timeout 15 min por modelo)
    for modelo in $FALTANDO; do
        log "Baixando $modelo..."
        if timeout 900 "$OLLAMA_BIN" pull "$modelo" 2>&1 | while IFS= read -r linha; do
            log "  $linha"
        done; then
            log "Modelo $modelo baixado com sucesso."
        else
            log "AVISO: Falha ou timeout ao baixar $modelo — tente novamente depois."
        fi
    done

    # Encerrar Ollama temporário pelo PID exato (ADR-03)
    kill -TERM "$SERVE_PID" 2>/dev/null || true
    wait "$SERVE_PID" 2>/dev/null || true
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

    log "Limpeza concluída. Até a próxima."
}

trap cleanup EXIT
trap 'exit 130' INT    # Ctrl+C  → EXIT trap executa cleanup
trap 'exit 143' TERM   # SIGTERM → EXIT trap executa cleanup

# ----------------------------------------------------------------------
# PRE-FLIGHT: verificar display GTK

if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
    fail "Nenhum display detectado (DISPLAY/WAYLAND_DISPLAY ausentes).\n       O Beholder requer interface gráfica GTK4."
fi

# ----------------------------------------------------------------------
# PRE-FLIGHT: instalar venv se ausente

if [ ! -f "$VENV_DIR/bin/python" ]; then
    log "Ambiente virtual não encontrado — executando install.sh..."
    bash "$PROJECT_DIR/install.sh"
fi

# Verificação mínima de integridade do venv
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

# PRE-FLIGHT: verificar binário Ollama (ADR-03: isolado em bin/ollama)
OLLAMA_BIN="$PROJECT_DIR/bin/ollama"
if [ ! -f "$OLLAMA_BIN" ]; then
    log "bin/ollama ausente — baixando binário..."
    mkdir -p "$PROJECT_DIR/bin"
    OLLAMA_VERSION=$(curl -sL "https://api.github.com/repos/ollama/ollama/releases/latest" | grep '"tag_name"' | head -1 | sed 's/.*"tag_name": "//;s/".*//')
    OLLAMA_VERSION="${OLLAMA_VERSION:-v0.20.7}"
    OLLAMA_URL="https://github.com/ollama/ollama/releases/download/${OLLAMA_VERSION}/ollama-linux-amd64.tar.zst"
    OLLAMA_TMP_TAR="$PROJECT_DIR/bin/.ollama-download.tar.zst"
    if curl -fSL --progress-bar "$OLLAMA_URL" -o "$OLLAMA_TMP_TAR"; then
        tar --zstd -xf "$OLLAMA_TMP_TAR" -C "$PROJECT_DIR" bin/ollama
        chmod +x "$OLLAMA_BIN"
        rm -f "$OLLAMA_TMP_TAR"
        log "bin/ollama ${OLLAMA_VERSION} instalado."
    else
        log "AVISO: Falha ao baixar Ollama — análise de IA indisponível."
        rm -f "$OLLAMA_TMP_TAR"
    fi
fi

# PRE-FLIGHT: verificar modelos de visão (moondream, minicpm-v, llava:7b)
verificar_modelos_ollama

# ----------------------------------------------------------------------
# INICIAR

log "Iniciando Beholder..."
source "$VENV_DIR/bin/activate"

# Exportar variáveis de ambiente do Ollama para isolar tudo dentro do projeto
export OLLAMA_MODELS="$OLLAMA_MODELS"
export OLLAMA_TMPDIR="$OLLAMA_TMPDIR"

python3 "$PROJECT_DIR/main.py"

# (cleanup é chamado automaticamente pelo trap EXIT ao sair do python)

# "A felicidade da sua vida depende da qualidade dos seus pensamentos." — Marco Aurélio
