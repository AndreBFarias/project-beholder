#!/usr/bin/env bash
# flatpak-launcher.sh — Lancador do Beholder dentro do sandbox Flatpak.
#
# Executado pelo manifest com.beholder.app.yml como Command. Encapsula
# o run.sh do projeto para garantir caminhos relativos ao /app.

set -euo pipefail

APP_ROOT="/app/lib/beholder"
exec "${APP_ROOT}/run.sh" "$@"
