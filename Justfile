# Project Beholder — Task runner

install:
    bash install.sh

setup:
    bash install.sh

ci-local:
    #!/usr/bin/env bash
    set -e
    echo "=== [1/4] Lint ==="
    .venv/bin/ruff check src/ tests/
    .venv/bin/ruff format --check src/ tests/
    echo "=== [2/4] Smoke ==="
    .venv/bin/pytest tests/smoke/ -v --timeout=10
    echo "=== [3/4] Unit ==="
    .venv/bin/pytest tests/unit/ -v
    echo "=== [4/4] Imports ==="
    .venv/bin/python -c "import src"
    echo "=== CI OK ==="

ci-quick:
    .venv/bin/ruff check src/ tests/
    .venv/bin/pytest tests/smoke/ --timeout=10 -q

run:
    bash run.sh

uninstall:
    bash uninstall.sh

teardown:
    bash teardown.sh

doctor:
    #!/usr/bin/env bash
    echo "=== Doctor ==="
    .venv/bin/python --version
    .venv/bin/python -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk; print('GTK4 OK')" 2>/dev/null || echo "AVISO: GTK4 nao encontrado"
    .venv/bin/python -c "import gi; gi.require_version('Adw', '1'); from gi.repository import Adw; print('Libadwaita OK')" 2>/dev/null || echo "AVISO: Libadwaita nao encontrado"
    .venv/bin/python -c "import playwright; print('Playwright OK')" 2>/dev/null || echo "AVISO: Playwright nao instalado"
    .venv/bin/python -c "import cv2; print('OpenCV OK')" 2>/dev/null || echo "AVISO: OpenCV nao instalado"
    .venv/bin/python -c "from sklearn.cluster import KMeans; print('scikit-learn OK')" 2>/dev/null || echo "AVISO: scikit-learn nao instalado"
    [ -f bin/ollama ] && echo "Ollama binario OK" || echo "AVISO: bin/ollama nao encontrado"
    echo "=== Doctor concluido ==="

lint:
    .venv/bin/ruff format src/ tests/
    .venv/bin/ruff check --fix src/ tests/

lint-check:
    .venv/bin/ruff check src/ tests/
    .venv/bin/ruff format --check src/ tests/

clean:
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true

test-smoke:
    .venv/bin/pytest tests/smoke/ -v

test-unit:
    .venv/bin/pytest tests/unit/ -v

test-all:
    .venv/bin/pytest tests/ -v
