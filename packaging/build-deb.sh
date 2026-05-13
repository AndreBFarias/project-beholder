#!/usr/bin/env bash
# build-deb.sh — Empacota o Beholder em .deb (Ubuntu/Debian).
#
# Uso: ./packaging/build-deb.sh <versao>
# Saida: dist/beholder_<versao>_amd64.deb
#
# O .deb instala apenas o codigo Python + lancador `beholder` + .desktop + icones.
# Ollama, modelos de visao e Playwright sao baixados pelo run.sh em runtime (Sprint 14).

set -euo pipefail

VERSAO="${1:-0.2.1}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ROOT_BUILD="$(mktemp -d)"
PKG_NAME="beholder_${VERSAO}_amd64"
PKG_DIR="${ROOT_BUILD}/${PKG_NAME}"
DEST_DEB_DIR="${PROJECT_DIR}/dist"

trap 'rm -rf "${ROOT_BUILD}"' EXIT

log() { echo "[build-deb] $*"; }

log "Versao: ${VERSAO}"
log "Staging: ${PKG_DIR}"

# Estrutura FHS:
#   /usr/lib/beholder/          codigo Python (src/, main.py, run.sh)
#   /usr/bin/beholder           wrapper que invoca run.sh
#   /usr/share/applications/    .desktop
#   /usr/share/icons/hicolor/*  icones em multiplas resolucoes
#   /usr/share/doc/beholder/    LICENSE, CHANGELOG, README
#   DEBIAN/                     control, postinst etc.

mkdir -p "${PKG_DIR}/DEBIAN"
mkdir -p "${PKG_DIR}/usr/lib/beholder"
mkdir -p "${PKG_DIR}/usr/bin"
mkdir -p "${PKG_DIR}/usr/share/applications"
mkdir -p "${PKG_DIR}/usr/share/doc/beholder"

# Copia codigo do projeto (sem .venv, sem .git, sem bin/, sem models/, sem lib/)
log "Copiando codigo..."
rsync -a \
    --exclude=".git" --exclude=".venv" --exclude="__pycache__" \
    --exclude="bin" --exclude="models" --exclude="lib" \
    --exclude="data" --exclude="output" --exclude="logs" \
    --exclude="dist" --exclude="*.deb" --exclude="*.AppImage" \
    --exclude="docs/screenshots/*.gif" \
    "${PROJECT_DIR}/src" \
    "${PROJECT_DIR}/main.py" \
    "${PROJECT_DIR}/run.sh" \
    "${PROJECT_DIR}/install.sh" \
    "${PROJECT_DIR}/requirements.txt" \
    "${PROJECT_DIR}/beholder-icon.png" \
    "${PKG_DIR}/usr/lib/beholder/"

# Docs (LICENSE obrigatorio em /usr/share/doc/<pacote>/)
cp "${PROJECT_DIR}/LICENSE" "${PKG_DIR}/usr/share/doc/beholder/copyright"
[ -f "${PROJECT_DIR}/README.md" ] && cp "${PROJECT_DIR}/README.md" "${PKG_DIR}/usr/share/doc/beholder/"
[ -f "${PROJECT_DIR}/CHANGELOG.md" ] && cp "${PROJECT_DIR}/CHANGELOG.md" "${PKG_DIR}/usr/share/doc/beholder/"

# Lancador /usr/bin/beholder
cat > "${PKG_DIR}/usr/bin/beholder" <<'LAUNCHER'
#!/usr/bin/env bash
# Lancador do Beholder instalado via .deb.
# Delega para /usr/lib/beholder/run.sh, que cuida do venv + Ollama + main.py.
exec /usr/lib/beholder/run.sh "$@"
LAUNCHER
chmod +x "${PKG_DIR}/usr/bin/beholder"

# .desktop
cp "${PROJECT_DIR}/packaging/com.beholder.app.desktop" "${PKG_DIR}/usr/share/applications/"

# Icones (gera redimensionados a partir do PNG original)
ICON_SRC="${PROJECT_DIR}/beholder-icon.png"
for SIZE in 48 128 256 512; do
    ICON_DIR="${PKG_DIR}/usr/share/icons/hicolor/${SIZE}x${SIZE}/apps"
    mkdir -p "${ICON_DIR}"
    if command -v convert >/dev/null 2>&1; then
        convert "${ICON_SRC}" -resize "${SIZE}x${SIZE}" "${ICON_DIR}/com.beholder.app.png"
    elif command -v magick >/dev/null 2>&1; then
        magick "${ICON_SRC}" -resize "${SIZE}x${SIZE}" "${ICON_DIR}/com.beholder.app.png"
    else
        cp "${ICON_SRC}" "${ICON_DIR}/com.beholder.app.png"
    fi
done

# DEBIAN/control com substituicao de versao
sed "s|@VERSAO@|${VERSAO}|g" "${PROJECT_DIR}/debian/control" > "${PKG_DIR}/DEBIAN/control"
cp "${PROJECT_DIR}/debian/postinst" "${PKG_DIR}/DEBIAN/postinst" 2>/dev/null || true
cp "${PROJECT_DIR}/debian/postrm"   "${PKG_DIR}/DEBIAN/postrm"   2>/dev/null || true
[ -f "${PKG_DIR}/DEBIAN/postinst" ] && chmod 755 "${PKG_DIR}/DEBIAN/postinst"
[ -f "${PKG_DIR}/DEBIAN/postrm" ]   && chmod 755 "${PKG_DIR}/DEBIAN/postrm"

# Build
mkdir -p "${DEST_DEB_DIR}"
log "Empacotando..."
dpkg-deb --root-owner-group --build "${PKG_DIR}" "${DEST_DEB_DIR}/${PKG_NAME}.deb"

log "OK: ${DEST_DEB_DIR}/${PKG_NAME}.deb"
