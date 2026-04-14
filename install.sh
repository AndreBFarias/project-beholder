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
    fail "Python 3.12+ não encontrado. Instale com: sudo apt install python3.12"
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

# Instalar .desktop e ícone
DESKTOP_FILE="$HOME/.local/share/applications/com.beholder.app.desktop"
ICON_DIR="$HOME/.local/share/icons/hicolor/512x512/apps"
ICON_FILE="$ICON_DIR/com.beholder.app.png"

mkdir -p "$(dirname "$DESKTOP_FILE")"
mkdir -p "$ICON_DIR"

if [ -f "$PROJECT_DIR/beholder-icon.png" ]; then
    cp "$PROJECT_DIR/beholder-icon.png" "$ICON_FILE"
    ok "Ícone instalado em $ICON_FILE"
else
    log "AVISO: beholder-icon.png não encontrado — ícone não instalado"
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

[ -f "$PROJECT_DIR/bin/ollama" ] && ok "bin/ollama presente" || log "AVISO: bin/ollama ausente — análise de IA indisponível (baixe em ollama.com)"

separador
echo ""
echo "Instalação concluída."
echo "Para iniciar o Beholder: ./run.sh"
echo ""

# "A sabedoria não é dada — é conquistada." — Sêneca
