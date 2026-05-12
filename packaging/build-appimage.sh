#!/usr/bin/env bash
# build-appimage.sh — Empacota o Beholder em AppImage universal.
#
# Uso: ./packaging/build-appimage.sh <versao>
# Saida: dist/Beholder-<versao>-x86_64.AppImage
#
# Estrategia: AppDir + linuxdeploy. Ollama, Playwright e modelos sao
# baixados pelo run.sh em runtime (nao entram no AppImage).

set -euo pipefail

VERSAO="${1:-0.2.1}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="${PROJECT_DIR}/dist"
APPDIR="${DIST_DIR}/Beholder.AppDir"
LINUXDEPLOY="${LINUXDEPLOY:-${HOME}/.cache/linuxdeploy-x86_64.AppImage}"

log() { echo "[build-appimage] $*"; }

mkdir -p "${DIST_DIR}"

# Baixa linuxdeploy se ausente
if [ ! -x "${LINUXDEPLOY}" ]; then
    log "Baixando linuxdeploy..."
    mkdir -p "$(dirname "${LINUXDEPLOY}")"
    curl -fSL --progress-bar \
        "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage" \
        -o "${LINUXDEPLOY}"
    chmod +x "${LINUXDEPLOY}"
fi

log "Limpando AppDir anterior..."
rm -rf "${APPDIR}"
mkdir -p "${APPDIR}/usr/lib/beholder"
mkdir -p "${APPDIR}/usr/bin"
mkdir -p "${APPDIR}/usr/share/applications"
mkdir -p "${APPDIR}/usr/share/icons/hicolor/256x256/apps"

# Codigo do projeto (mesmas exclusoes do build-deb)
log "Copiando codigo..."
rsync -a \
    --exclude=".git" --exclude=".venv" --exclude="__pycache__" \
    --exclude="bin" --exclude="models" --exclude="lib" \
    --exclude="data" --exclude="output" --exclude="logs" \
    --exclude="dist" --exclude="*.deb" --exclude="*.AppImage" \
    "${PROJECT_DIR}/src" \
    "${PROJECT_DIR}/main.py" \
    "${PROJECT_DIR}/run.sh" \
    "${PROJECT_DIR}/install.sh" \
    "${PROJECT_DIR}/requirements.txt" \
    "${PROJECT_DIR}/beholder-icon.png" \
    "${APPDIR}/usr/lib/beholder/"

# AppRun: ponto de entrada do AppImage
cat > "${APPDIR}/AppRun" <<'APPRUN'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
exec "${HERE}/usr/lib/beholder/run.sh" "$@"
APPRUN
chmod +x "${APPDIR}/AppRun"

# Lancador adicional em /usr/bin (alguns desktops usam)
cat > "${APPDIR}/usr/bin/beholder" <<'BIN'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
exec "${HERE}/../lib/beholder/run.sh" "$@"
BIN
chmod +x "${APPDIR}/usr/bin/beholder"

# .desktop dentro do AppDir
cp "${PROJECT_DIR}/packaging/com.beholder.app.desktop" "${APPDIR}/com.beholder.app.desktop"
cp "${PROJECT_DIR}/packaging/com.beholder.app.desktop" "${APPDIR}/usr/share/applications/"

# Icone 256x256 (linuxdeploy procura no nivel do AppDir e no hicolor)
if command -v convert >/dev/null 2>&1; then
    convert "${PROJECT_DIR}/beholder-icon.png" -resize "256x256" \
        "${APPDIR}/com.beholder.app.png"
elif command -v magick >/dev/null 2>&1; then
    magick "${PROJECT_DIR}/beholder-icon.png" -resize "256x256" \
        "${APPDIR}/com.beholder.app.png"
else
    cp "${PROJECT_DIR}/beholder-icon.png" "${APPDIR}/com.beholder.app.png"
fi
cp "${APPDIR}/com.beholder.app.png" \
   "${APPDIR}/usr/share/icons/hicolor/256x256/apps/com.beholder.app.png"

log "Rodando linuxdeploy..."
cd "${DIST_DIR}"
NO_STRIP=1 OUTPUT="Beholder-${VERSAO}-x86_64.AppImage" \
    "${LINUXDEPLOY}" --appdir "${APPDIR}" --output appimage

log "OK: ${DIST_DIR}/Beholder-${VERSAO}-x86_64.AppImage"
