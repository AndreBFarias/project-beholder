# Project Beholder — Task runner

install:
    bash install.sh

setup:
    bash install.sh

ci-local:
    #!/usr/bin/env bash
    set -e
    echo "=== [1/4] Lint ==="
    ruff check src/ tests/
    ruff format --check src/ tests/
    echo "=== [2/4] Smoke ==="
    pytest tests/smoke/ -v --timeout=10
    echo "=== [3/4] Unit ==="
    pytest tests/unit/ -v
    echo "=== [4/4] Imports ==="
    python -c "import src"
    echo "=== CI OK ==="

ci-quick:
    ruff check src/ tests/
    pytest tests/smoke/ --timeout=10 -q

run:
    bash run.sh

uninstall:
    bash uninstall.sh

teardown:
    bash teardown.sh

doctor:
    #!/usr/bin/env bash
    echo "=== Doctor ==="
    python --version
    python -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk; print('GTK4 OK')" 2>/dev/null || echo "AVISO: GTK4 nao encontrado"
    python -c "import gi; gi.require_version('Adw', '1'); from gi.repository import Adw; print('Libadwaita OK')" 2>/dev/null || echo "AVISO: Libadwaita nao encontrado"
    python -c "import playwright; print('Playwright OK')" 2>/dev/null || echo "AVISO: Playwright nao instalado"
    python -c "import cv2; print('OpenCV OK')" 2>/dev/null || echo "AVISO: OpenCV nao instalado"
    python -c "from sklearn.cluster import KMeans; print('scikit-learn OK')" 2>/dev/null || echo "AVISO: scikit-learn nao instalado"
    [ -f bin/ollama ] && echo "Ollama binario OK" || echo "AVISO: bin/ollama nao encontrado"
    echo "=== Doctor concluido ==="

lint:
    ruff format src/ tests/
    ruff check --fix src/ tests/

lint-check:
    ruff check src/ tests/
    ruff format --check src/ tests/

clean:
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true

test-smoke:
    pytest tests/smoke/ -v

test-unit:
    pytest tests/unit/ -v

test-all:
    pytest tests/ -v
