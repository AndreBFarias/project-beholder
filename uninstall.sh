#!/usr/bin/env bash
# uninstall.sh — Remove o ambiente do Project Beholder

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
OLLAMA_PORT=11435
OLLAMA_TMPDIR="/tmp/ollama_beholder"

cd "$PROJECT_DIR"

log()  { echo "[uninstall] $*"; }

separador() { echo "------------------------------------------------------------"; }

perguntar() {
    # perguntar "Mensagem?" → retorna 0 (sim) ou 1 (nao)
    local RESPOSTA
    printf "%s [s/N] " "$1"
    read -r RESPOSTA
    [[ "$RESPOSTA" =~ ^[Ss]$ ]]
}

# ----------------------------------------------------------------------
# Confirmação obrigatória

separador
echo ""
echo "  Project Beholder — Desinstalacao"
echo ""
echo "  Isso vai remover:"
echo "    - Ambiente virtual (.venv/)"
echo "    - Caches Python (__pycache__, *.pyc)"
echo "    - Hooks git instalados"
echo "    - Ollama em execucao na porta $OLLAMA_PORT"
echo "    - /tmp/ollama_beholder"
echo ""
separador

if ! perguntar "Confirmar desinstalacao?"; then
    echo "Cancelado."
    exit 0
fi

# ----------------------------------------------------------------------
# 1. Encerrar Ollama se rodando

separador
log "1/5 — Encerrando Ollama..."

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

OLLAMA_PID=$(encontrar_pid_ollama)
if [ -n "$OLLAMA_PID" ]; then
    log "Encerrando Ollama (PID $OLLAMA_PID)..."
    kill -TERM "$OLLAMA_PID" 2>/dev/null || true
    local_espera=0
    while kill -0 "$OLLAMA_PID" 2>/dev/null && [ "$local_espera" -lt 5 ]; do
        sleep 1
        local_espera=$((local_espera + 1))
    done
    kill -KILL "$OLLAMA_PID" 2>/dev/null || true
    log "Ollama encerrado. VRAM liberada."
else
    log "Nenhum Ollama ativo na porta $OLLAMA_PORT."
fi

# Limpar OLLAMA_TMPDIR
rm -rf "$OLLAMA_TMPDIR"
log "OLLAMA_TMPDIR limpo."

# ----------------------------------------------------------------------
# 2. Remover venv

separador
log "2/5 — Removendo ambiente virtual..."

if [ -d "$VENV_DIR" ]; then
    rm -rf "$VENV_DIR"
    log ".venv/ removido."
else
    log ".venv/ nao encontrado (ja removido)."
fi

# ----------------------------------------------------------------------
# 3. Limpar caches Python

separador
log "3/5 — Limpando caches Python..."

find "$PROJECT_DIR" -type d -name "__pycache__"  -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_DIR" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_DIR" -type d -name ".ruff_cache"   -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_DIR" -type d -name "*.egg-info"    -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_DIR" -name "*.pyc"  -delete 2>/dev/null || true
find "$PROJECT_DIR" -name "*.pyo"  -delete 2>/dev/null || true
log "Caches removidos."

# ----------------------------------------------------------------------
# 4. Remover hooks git

separador
log "4/5 — Removendo hooks git..."

if [ -d "$PROJECT_DIR/.git/hooks" ]; then
    rm -f "$PROJECT_DIR/.git/hooks/pre-commit"
    rm -f "$PROJECT_DIR/.git/hooks/commit-msg"
    log "Hooks git removidos."
else
    log "Hooks git nao encontrados."
fi

# ----------------------------------------------------------------------
# 5. Dados e modelos (opcionais — confirmação individual)

separador
log "5/5 — Dados e modelos (opcional)..."

if [ -d "$PROJECT_DIR/data" ] || [ -d "$PROJECT_DIR/output" ] || [ -d "$PROJECT_DIR/logs" ]; then
    echo ""
    echo "  Encontrado: data/, output/, logs/"
    if perguntar "  Remover dados de sessao, pacotes gerados e logs?"; then
        rm -rf "$PROJECT_DIR/data" "$PROJECT_DIR/output" "$PROJECT_DIR/logs"
        log "Dados, pacotes e logs removidos."
    else
        log "Dados preservados."
    fi
fi

if [ -d "$PROJECT_DIR/models" ]; then
    echo ""
    echo "  Encontrado: models/ (modelos de IA baixados)"
    if perguntar "  Remover modelos? (podem ser varios GB)"; then
        rm -rf "$PROJECT_DIR/models"
        log "Modelos removidos."
    else
        log "Modelos preservados."
    fi
fi

if [ -f "$PROJECT_DIR/bin/ollama" ]; then
    echo ""
    echo "  Encontrado: bin/ollama (binario do Ollama)"
    if perguntar "  Remover binario do Ollama?"; then
        rm -f "$PROJECT_DIR/bin/ollama"
        rmdir "$PROJECT_DIR/bin" 2>/dev/null || true
        log "Binario do Ollama removido."
    else
        log "Binario preservado."
    fi
fi

# ----------------------------------------------------------------------

separador
echo ""
echo "Desinstalacao concluida."
echo "O codigo-fonte e os arquivos de configuracao foram preservados."
echo "Para reinstalar: ./install.sh"
echo ""

# "Terminar bem e uma arte." — Seneca
