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
# 0. Instalar dependências de sistema (GTK4 + GObject bindings)
#
# PyGObject NÃO é instalado via pip — é um pacote de sistema ligado ao GTK do SO.
# Verificamos quais pacotes faltam antes de chamar sudo (evita sudo desnecessário).

separador
log "0/5 — Dependências de sistema (GTK4)..."

PKGS_NECESSARIOS=(
    python3-gi
    python3-gi-cairo
    gir1.2-gtk-4.0
    gir1.2-adw-1
    gir1.2-glib-2.0
    libgirepository1.0-dev
)

PKGS_FALTANDO=()
for pkg in "${PKGS_NECESSARIOS[@]}"; do
    dpkg -s "$pkg" >/dev/null 2>&1 || PKGS_FALTANDO+=("$pkg")
done

if [ ${#PKGS_FALTANDO[@]} -gt 0 ]; then
    log "Pacotes ausentes: ${PKGS_FALTANDO[*]}"
    log "Instalando via apt (requer sudo)..."
    sudo apt-get install -y "${PKGS_FALTANDO[@]}"
    ok "Pacotes de sistema instalados"
else
    ok "Dependências de sistema já presentes"
fi

# ----------------------------------------------------------------------
# 1. Verificar Python >= 3.10 com GI (PyGObject) disponível

separador
log "1/5 — Verificando Python..."

# Prioridade: Python com GI bindings (necessário para GTK4)
# O --system-site-packages só funciona se o venv for criado do mesmo
# Python que tem os bindings compilados (tipicamente /usr/bin/python3).
PYTHON_BIN=""

# Primeiro: tentar encontrar Python com GI disponível (>= 3.10)
for candidato in /usr/bin/python3 python3 python3.12 python3.13 python3.11 python3.10; do
    if command -v "$candidato" >/dev/null 2>&1; then
        if "$candidato" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
            if "$candidato" -c "import gi" 2>/dev/null; then
                PYTHON_BIN="$candidato"
                log "Python com GI encontrado: $candidato"
                break
            fi
        fi
    fi
done

# Fallback: qualquer Python >= 3.10 (sem GI — GTK4 não vai funcionar)
if [ -z "$PYTHON_BIN" ]; then
    for candidato in python3.12 python3.13 python3.11 python3.10 python3 python; do
        if command -v "$candidato" >/dev/null 2>&1; then
            if "$candidato" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
                PYTHON_BIN="$candidato"
                log "AVISO: Python sem GI — GTK4 pode não funcionar"
                break
            fi
        fi
    done
fi

if [ -z "$PYTHON_BIN" ]; then
    fail "Python 3.10+ não encontrado. Instale com: sudo apt install python3"
fi

PYTHON_VER=$("$PYTHON_BIN" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
ok "Python $PYTHON_VER ($PYTHON_BIN)"

# ----------------------------------------------------------------------
# 2. Criar ou verificar venv

separador
log "2/5 — Ambiente virtual..."

if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/python" ]; then
    ok "venv já existe em .venv/"
else
    if [ -d "$VENV_DIR" ]; then
        log "venv corrompido, recriando..."
        rm -rf "$VENV_DIR"
    fi
    log "Criando .venv/ com $PYTHON_BIN..."
    "$PYTHON_BIN" -m venv --system-site-packages "$VENV_DIR"
    ok "venv criado"
fi

PYTHON_VENV="$VENV_DIR/bin/python"
PIP_VENV="$VENV_DIR/bin/pip"

# ----------------------------------------------------------------------
# 3. Instalar dependências

separador
log "3/5 — Instalando dependências..."

"$PIP_VENV" install --quiet --upgrade pip setuptools wheel

# PKG_CONFIG_PATH necessário para PyGObject compilar com os headers de sistema.
# Ubuntu 22.04 tem gobject-introspection-1.0 em /usr/lib/x86_64-linux-gnu/pkgconfig/
export PKG_CONFIG_PATH="/usr/lib/x86_64-linux-gnu/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"

"$PIP_VENV" install -r "$PROJECT_DIR/requirements.txt"
ok "requirements.txt instalado"

# Playwright chromium (necessário para modo furtivo)
if "$VENV_DIR/bin/playwright" install chromium --quiet 2>/dev/null; then
    ok "Playwright chromium instalado"
else
    log "AVISO: playwright chromium não instalado — modo furtivo indisponível"
fi

# ----------------------------------------------------------------------
# 4. Instalar hooks git

separador
log "4/5 — Configurando hooks git e diretórios..."

# Garantir que diretórios do projeto existem (isolados dentro do projeto)
mkdir -p "$PROJECT_DIR/bin"
mkdir -p "$PROJECT_DIR/models"
mkdir -p "$PROJECT_DIR/data/sessao_atual"
mkdir -p "$PROJECT_DIR/data/ollama_tmp"
mkdir -p "$PROJECT_DIR/output"
mkdir -p "$PROJECT_DIR/logs"
ok "Diretórios do projeto criados"

# Baixar binário do Ollama se ausente (ADR-03: isolado em bin/ollama)
OLLAMA_BIN="$PROJECT_DIR/bin/ollama"
if [ -f "$OLLAMA_BIN" ]; then
    ok "bin/ollama já presente"
else
    log "Baixando Ollama (pode levar alguns minutos)..."
    OLLAMA_VERSION=$(curl -sL "https://api.github.com/repos/ollama/ollama/releases/latest" | grep '"tag_name"' | head -1 | sed 's/.*"tag_name": "//;s/".*//')
    OLLAMA_VERSION="${OLLAMA_VERSION:-v0.20.7}"
    OLLAMA_URL="https://github.com/ollama/ollama/releases/download/${OLLAMA_VERSION}/ollama-linux-amd64.tar.zst"
    OLLAMA_TMP_TAR="$PROJECT_DIR/bin/.ollama-download.tar.zst"
    if curl -fSL --progress-bar "$OLLAMA_URL" -o "$OLLAMA_TMP_TAR"; then
        tar --zstd -xf "$OLLAMA_TMP_TAR" -C "$PROJECT_DIR" bin/ollama
        chmod +x "$OLLAMA_BIN"
        rm -f "$OLLAMA_TMP_TAR"
        ok "bin/ollama ${OLLAMA_VERSION} instalado"
    else
        log "AVISO: Falha ao baixar Ollama — análise de IA indisponível"
        log "       URL tentada: $OLLAMA_URL"
        rm -f "$OLLAMA_TMP_TAR"
    fi
fi

# Baixar modelos de visão (3 tiers) via Ollama
MODELOS_VISAO="moondream minicpm-v llava:7b"
OLLAMA_PORT=11435

if [ -f "$OLLAMA_BIN" ]; then
    log "Verificando modelos de visão..."
    OLLAMA_MODELS_DIR="$PROJECT_DIR/models"
    OLLAMA_TMP="$PROJECT_DIR/data/ollama_tmp"
    mkdir -p "$OLLAMA_MODELS_DIR" "$OLLAMA_TMP"

    FALTANDO=""
    for modelo in $MODELOS_VISAO; do
        nome_dir=$(echo "$modelo" | tr ':' '/')
        if [ -d "$OLLAMA_MODELS_DIR/manifests" ] && \
           find "$OLLAMA_MODELS_DIR/manifests" -path "*${nome_dir}*" -type f 2>/dev/null | grep -q .; then
            ok "Modelo $modelo presente"
        else
            FALTANDO="$FALTANDO $modelo"
        fi
    done

    if [ -n "$FALTANDO" ]; then
        log "Modelos ausentes:$FALTANDO — iniciando download..."
        log "Isso pode levar vários minutos na primeira instalação."

        export OLLAMA_HOST="127.0.0.1:$OLLAMA_PORT"
        export OLLAMA_MODELS="$OLLAMA_MODELS_DIR"
        OLLAMA_TMPDIR="$OLLAMA_TMP" "$OLLAMA_BIN" serve &
        SERVE_PID=$!

        ESPERA=0
        while ! curl -s "http://127.0.0.1:$OLLAMA_PORT/api/tags" >/dev/null 2>&1; do
            sleep 1
            ESPERA=$((ESPERA + 1))
            if [ "$ESPERA" -ge 30 ]; then
                log "AVISO: Ollama não respondeu — download dos modelos ignorado"
                kill -TERM "$SERVE_PID" 2>/dev/null || true
                wait "$SERVE_PID" 2>/dev/null || true
                FALTANDO=""
                break
            fi
        done

        for modelo in $FALTANDO; do
            log "Baixando $modelo..."
            if timeout 900 "$OLLAMA_BIN" pull "$modelo" 2>&1 | while IFS= read -r linha; do
                log "  $linha"
            done; then
                ok "Modelo $modelo baixado"
            else
                log "AVISO: Falha ao baixar $modelo — tente novamente via run.sh"
            fi
        done

        kill -TERM "$SERVE_PID" 2>/dev/null || true
        wait "$SERVE_PID" 2>/dev/null || true
    else
        ok "Todos os modelos de visão presentes"
    fi
else
    log "AVISO: bin/ollama ausente — modelos não baixados"
fi

if [ -d "$PROJECT_DIR/.git" ]; then
    # Copiar hooks customizados
    cp "$PROJECT_DIR/hooks/pre-commit"  "$PROJECT_DIR/.git/hooks/pre-commit"
    cp "$PROJECT_DIR/hooks/commit-msg"  "$PROJECT_DIR/.git/hooks/commit-msg"
    chmod +x "$PROJECT_DIR/.git/hooks/pre-commit"
    chmod +x "$PROJECT_DIR/.git/hooks/commit-msg"

    # pre-commit framework (se disponível no venv)
    if [ -f "$VENV_DIR/bin/pre-commit" ]; then
        "$VENV_DIR/bin/pre-commit" install --hook-type pre-commit >/dev/null 2>&1 || true
        "$VENV_DIR/bin/pre-commit" install --hook-type commit-msg  >/dev/null 2>&1 || true
        ok "pre-commit framework instalado"
    fi
    ok "hooks git configurados"
else
    log "AVISO: repositório git não encontrado — hooks não instalados"
fi

# Instalar .desktop e ícone em múltiplas resoluções
DESKTOP_FILE="$HOME/.local/share/applications/com.beholder.app.desktop"
ICON_NAME="com.beholder.app"
ICON_SOURCE="$PROJECT_DIR/beholder-icon.png"

mkdir -p "$(dirname "$DESKTOP_FILE")"

if [ -f "$ICON_SOURCE" ]; then
    for SIZE in 48 128 256 512; do
        ICON_DIR="$HOME/.local/share/icons/hicolor/${SIZE}x${SIZE}/apps"
        mkdir -p "$ICON_DIR"
        if "$PYTHON_VENV" -c "from PIL import Image" 2>/dev/null; then
            "$PYTHON_VENV" -c "
import sys
from PIL import Image
src, dst, sz = sys.argv[1], sys.argv[2], int(sys.argv[3])
img = Image.open(src)
img = img.resize((sz, sz), Image.LANCZOS)
img.save(dst)
" "$ICON_SOURCE" "$ICON_DIR/${ICON_NAME}.png" "$SIZE"
        elif command -v convert >/dev/null 2>&1; then
            convert "$ICON_SOURCE" -resize "${SIZE}x${SIZE}" "$ICON_DIR/${ICON_NAME}.png"
        elif command -v magick >/dev/null 2>&1; then
            magick "$ICON_SOURCE" -resize "${SIZE}x${SIZE}" "$ICON_DIR/${ICON_NAME}.png"
        else
            cp "$ICON_SOURCE" "$ICON_DIR/${ICON_NAME}.png"
        fi
    done
    ok "Ícone instalado em 48, 128, 256, 512"
else
    log "AVISO: beholder-icon.png não encontrado — ícone não instalado"
fi

# Garantir index.theme no hicolor (necessário para gtk-update-icon-cache)
HICOLOR_DIR="$HOME/.local/share/icons/hicolor"
if [ ! -f "$HICOLOR_DIR/index.theme" ]; then
    cat > "$HICOLOR_DIR/index.theme" << 'THEME'
[Icon Theme]
Name=Hicolor
Comment=Fallback Icon Theme
Hidden=true
Directories=48x48/apps,128x128/apps,256x256/apps,512x512/apps

[48x48/apps]
Size=48
Context=Applications
Type=Fixed

[128x128/apps]
Size=128
Context=Applications
Type=Fixed

[256x256/apps]
Size=256
Context=Applications
Type=Fixed

[512x512/apps]
Size=512
Context=Applications
Type=Fixed
THEME
fi

# Atualizar cache de ícones
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f "$HICOLOR_DIR" 2>/dev/null || true
fi

cat > "$DESKTOP_FILE" << 'DESKTOP'
[Desktop Entry]
Version=1.0
Type=Application
Name=Beholder
Comment=Motor de predação visual de assets de interface
Exec=EXEC_PLACEHOLDER
Icon=com.beholder.app
Terminal=false
Categories=Development;Graphics;
Keywords=design;assets;scraper;vision;
StartupWMClass=com.beholder.app
DESKTOP

# Substituir placeholder pelo caminho real
sed -i "s|EXEC_PLACEHOLDER|$PROJECT_DIR/run.sh|g" "$DESKTOP_FILE"

ok "Arquivo .desktop criado em $DESKTOP_FILE"

# Atualizar cache de aplicações
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

# ----------------------------------------------------------------------
# 5. Verificação final (doctor)

separador
log "5/5 — Verificação final..."

"$PYTHON_VENV" -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk; print('[install] OK: GTK4')"         2>/dev/null || log "AVISO: GTK4 não disponível — interface gráfica não vai funcionar"
"$PYTHON_VENV" -c "import gi; gi.require_version('Adw', '1');  from gi.repository import Adw; print('[install] OK: Libadwaita')"   2>/dev/null || log "AVISO: Libadwaita não disponível"
"$PYTHON_VENV" -c "from sklearn.cluster import KMeans; print('[install] OK: scikit-learn')"                                        2>/dev/null || log "AVISO: scikit-learn não disponível"
"$PYTHON_VENV" -c "import cv2; print('[install] OK: OpenCV')"                                                                      2>/dev/null || log "AVISO: OpenCV não disponível"
"$PYTHON_VENV" -c "import src; print('[install] OK: pacote src importavel')"

[ -f "$PROJECT_DIR/bin/ollama" ] && ok "bin/ollama presente" || log "AVISO: bin/ollama ausente — análise de IA indisponível"

separador
echo ""
echo "Instalação concluída."
echo "Para iniciar o Beholder: ./run.sh"
echo ""

# "A sabedoria não é dada — é conquistada." — Sêneca
