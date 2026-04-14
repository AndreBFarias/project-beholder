#!/usr/bin/env bash
# install.sh — Configura o ambiente do Project Beholder
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

cd "$PROJECT_DIR"

# ----------------------------------------------------------------------
# Utilitários

log()  { echo "[install] $*"; }
ok()   { echo "[install] OK: $*"; }
fail() { echo "[install] ERRO: $*" >&2; exit 1; }

separador() { echo "------------------------------------------------------------"; }

# ----------------------------------------------------------------------
# 1. Verificar Python >= 3.12

separador
log "1/5 — Verificando Python..."

PYTHON_BIN=""
for candidato in python3.12 python3.13 python3 python; do
    if command -v "$candidato" >/dev/null 2>&1; then
        if "$candidato" -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" 2>/dev/null; then
            PYTHON_BIN="$candidato"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    fail "Python 3.12+ nao encontrado. Instale com: sudo apt install python3.12"
fi

PYTHON_VER=$("$PYTHON_BIN" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
ok "Python $PYTHON_VER ($PYTHON_BIN)"

# ----------------------------------------------------------------------
# 2. Criar ou verificar venv

separador
log "2/5 — Ambiente virtual..."

if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/python" ]; then
    ok "venv ja existe em .venv/"
else
    if [ -d "$VENV_DIR" ]; then
        log "venv corrompido, recriando..."
        rm -rf "$VENV_DIR"
    fi
    log "Criando .venv/ com $PYTHON_BIN..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    ok "venv criado"
fi

PYTHON_VENV="$VENV_DIR/bin/python"
PIP_VENV="$VENV_DIR/bin/pip"

# ----------------------------------------------------------------------
# 3. Instalar dependências

separador
log "3/5 — Instalando dependencias..."

"$PIP_VENV" install --quiet --upgrade pip setuptools wheel
"$PIP_VENV" install --quiet -r "$PROJECT_DIR/requirements.txt"
ok "requirements.txt instalado"

# Playwright chromium (necessário para modo furtivo)
if "$VENV_DIR/bin/playwright" install chromium --quiet 2>/dev/null; then
    ok "Playwright chromium instalado"
else
    log "AVISO: playwright chromium nao instalado — modo furtivo indisponivel"
fi

# ----------------------------------------------------------------------
# 4. Instalar hooks git

separador
log "4/5 — Configurando hooks git..."

if [ -d "$PROJECT_DIR/.git" ]; then
    # Copiar hooks customizados
    cp "$PROJECT_DIR/hooks/pre-commit"  "$PROJECT_DIR/.git/hooks/pre-commit"
    cp "$PROJECT_DIR/hooks/commit-msg"  "$PROJECT_DIR/.git/hooks/commit-msg"
    chmod +x "$PROJECT_DIR/.git/hooks/pre-commit"
    chmod +x "$PROJECT_DIR/.git/hooks/commit-msg"

    # pre-commit framework (se disponivel no venv)
    if [ -f "$VENV_DIR/bin/pre-commit" ]; then
        "$VENV_DIR/bin/pre-commit" install --hook-type pre-commit >/dev/null 2>&1 || true
        "$VENV_DIR/bin/pre-commit" install --hook-type commit-msg  >/dev/null 2>&1 || true
        ok "pre-commit framework instalado"
    fi
    ok "hooks git configurados"
else
    log "AVISO: repositorio git nao encontrado — hooks nao instalados"
fi

# ----------------------------------------------------------------------
# 5. Verificação final (doctor)

separador
log "5/5 — Verificacao final..."

"$PYTHON_VENV" -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk; print('[install] OK: GTK4')"         2>/dev/null || log "AVISO: GTK4 nao disponivel — interface grafica nao vai funcionar"
"$PYTHON_VENV" -c "import gi; gi.require_version('Adw', '1');  from gi.repository import Adw; print('[install] OK: Libadwaita')"   2>/dev/null || log "AVISO: Libadwaita nao disponivel"
"$PYTHON_VENV" -c "from sklearn.cluster import KMeans; print('[install] OK: scikit-learn')"                                        2>/dev/null || log "AVISO: scikit-learn nao disponivel"
"$PYTHON_VENV" -c "import cv2; print('[install] OK: OpenCV')"                                                                      2>/dev/null || log "AVISO: OpenCV nao disponivel"
"$PYTHON_VENV" -c "import src; print('[install] OK: pacote src importavel')"

[ -f "$PROJECT_DIR/bin/ollama" ] && ok "bin/ollama presente" || log "AVISO: bin/ollama ausente — analise de IA indisponivel (baixe em ollama.com)"

separador
echo ""
echo "Instalacao concluida."
echo "Para iniciar o Beholder: ./run.sh"
echo ""

# "A sabedoria nao e dada — e conquistada." — Seneca
