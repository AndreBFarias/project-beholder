# Project Beholder — Spec e Plano de Implementação
**Data:** 2026-04-13
**Status:** Aprovado para execução

---

## Context

O Project Beholder é um motor autônomo de predação visual para Linux. Seu objetivo é varrer URLs, extrair assets de interface (ícones, vetores, fundos), classificá-los via IA local (Ollama/Moondream), quantizar suas cores dominantes via K-Means e exportar pacotes .zip + dataset_assets.csv estruturados para consumo por outros repositórios (ex: Dracula_HyperOS3).

O projeto foi planejado em sessão de brainstorming completa. Todas as decisões de UI/UX, arquitetura e infra estão confirmadas abaixo. Os artefatos visuais de design estão em `.superpowers/brainstorm/` — devem ser copiados para `docs/design/` na Sprint 0.

---

## Decisões de Design Confirmadas

### Interface (GTK4 + Libadwaita)

**Framework:** PyGObject + GTK4 + Libadwaita (Python puro, sem arquivos .glade/.ui)
**Tema:** Dracula completo via `Gtk.CssProvider` — cores definidas em `src/gui/theme.py`
**Layout:** `Adw.NavigationSplitView` — sidebar fixa à esquerda, conteúdo à direita

**Paleta Dracula obrigatória:**
```python
DRACULA = {
    "background":    "#282a36",
    "current_line":  "#44475a",
    "foreground":    "#f8f8f2",
    "comment":       "#6272a4",
    "cyan":          "#8be9fd",
    "green":         "#50fa7b",
    "orange":        "#ffb86c",
    "pink":          "#ff79c6",
    "purple":        "#bd93f9",
    "red":           "#ff5555",
    "yellow":        "#f1fa8c",
}
```

**Sidebar — 5 módulos + separador + configurações:**
| Posição | Nome | Descrição | Cor de destaque |
|---------|------|-----------|-----------------|
| 1 | Caçada | URL alvo + scraper + log | `#bd93f9` (purple) |
| 2 | Córtex | Visão IA + VRAM | `#ff79c6` (pink) |
| 3 | Espólio | Exportação .zip + CSV | `#50fa7b` (green) |
| 4 | Protocolo | Batch + checkpoints | `#ffb86c` (orange) |
| — | *separador* | — | — |
| 5 | Grimório | Configurações | `#8be9fd` (cyan) |

**Header da janela:**
- Logo: `beholder-icon.png` (500×500, já existe na raiz) — exibida como 40×40px circular
- Título: "BEHOLDER" em `#bd93f9`, bold, `letter-spacing: 2px`
- Tagline: "motor de predação visual" em `#6272a4`, tamanho menor
- Ícones da sidebar: Adwaita symbolic icons (sem emojis, sem SVGs externos)

**Barra de status global (rodapé da janela):**
```
 ativo | 12 / 47 (25%) | VRAM: 1.2 GB | sessão: nova
```
Estados de sessão: `nova` · `ativa` · `pausada` · `restaurada — continuando de X/Y` · `concluída`

---

### Comportamentos por módulo

**Caçada:**
- Campo URL (Gtk.Entry) + botão INICIAR + toggle FURTIVO
- INICIAR → valida URL → dispara Thread A (scraper) → log em tempo real (Gtk.TextView append)
- Durante scraping: INICIAR vira PAUSAR + aparece CANCELAR
- PAUSAR → serializa estado → salva `.checkpoint.json` → status "pausada"
- CANCELAR → encerra thread → não salva → limpa `data/sessao_atual/`
- FURTIVO (toggle) → quando ativo: Playwright com evasão; quando inativo: requests simples

**Córtex:**
- ANALISAR → sobe Ollama em porta 11435 → carrega Moondream → processa fila de assets
- EXPURGAR VRAM → `pkill` no PID exato → limpa `OLLAMA_TMPDIR` → VRAM: 0 GB
- PAUSAR IA → pausa fila de processamento → mantém Ollama vivo
- Grid ao vivo: imagem original  tags JSON do Moondream

**Espólio:**
- GERAR PACOTE → organiza assets em subpastas (icons/, backgrounds/, outros/) → gera CSV final → compacta em `output/beholder_YYYYMMDD_HHMMSS.zip`
- ABRIR PASTA → `xdg-open output/`
- EXPORTAR CSV → diálogo Gtk.FileChooserDialog → salva só o CSV
- LIMPAR SESSÃO → confirmação obrigatória → remove `data/sessao_atual/`

**Protocolo:**
- Lista de URLs com status (pendente/em progresso/concluída/erro)
- ADICIONAR URL → valida → adiciona com status "pendente"
- IMPORTAR LISTA → Gtk.FileChooserDialog → carrega .txt (uma URL por linha) → duplicatas ignoradas
- EXECUTAR LOTE → processa fila sequencialmente (Caçada → Córtex → Espólio por URL) → checkpoint após cada URL
- RETOMAR SESSÃO → lê `.checkpoint.json` → reconstrói fila → status "restaurada — continuando de X/Y"

**Grimório:**
- Seções: Scraper (timeouts, delays, jitter), IA (porta Ollama, modelo), Saída (diretório output, naming), Avançado (K-Means cores)
- SALVAR → persiste em `~/.config/beholder/config.ini` (XDG)
- TESTAR OLLAMA → ping na porta configurada → feedback verde/vermelho
- RESTAURAR PADRÕES → confirmação → reset para `defaults.py`
- ABRIR LOGS → `xdg-open logs/beholder.log`

---

### Arquitetura — Pipeline Produtor-Consumidor

```
Thread A (Scraper/Produtor)
  stealth_spider.py + html_parser.py
  → Fila A (threading.Queue) — assets brutos
    → Thread B (AI Worker/Consumidor+Produtor)
         orchestrator.py + moondream_prompt.py + icon_alchemist.py
         → Fila B (threading.Queue) — assets processados + tags
           → Thread C (Exporter/Consumidor)
                packer.py + dataset_writer.py
                → data/sessao_atual/processed/ + dataset_assets.csv
```

**Regra fundamental:** Nenhuma thread toca widgets GTK diretamente. Toda atualização de UI via `GLib.idle_add(callback, dados)`.

**Ciclo do Ollama (efêmero):**
1. `ollama_lifecycle.py` sobe `./bin/ollama serve --port 11435`
2. Thread B consome da Fila A, chama API local, posta em Fila B
3. Ao finalizar: `pkill` no PID exato + `rm -rf $OLLAMA_TMPDIR`

**Sistema de checkpoints:**
- Arquivo: `data/sessao_atual/.checkpoint.json`
- Conteúdo: `{url, posicao_atual, assets_baixados, assets_processados, timestamp}`
- PAUSAR serializa estado das filas + posição
- RETOMAR desserializa e reconstrói threads

**Sistema de logging:**
- `src/core/logging_config.py` — setup centralizado
- `logs/beholder.log` — DEBUG+, RotatingFileHandler (10 MB × 3 backups)
- Console — INFO+
- Loggers silenciados: httpx, urllib3, asyncio, PIL, playwright

**Config (padrão XDG):**
- `src/core/config/defaults.py` — fonte única de verdade (padrão ADR-02 do Luna)
- `~/.config/beholder/config.ini` — overrides do usuário
- `src/core/config/config.py` — loader com fallback para defaults

---

## Estrutura de Diretórios Final

```
project_beholder/
├── bin/                          # Binário ollama isolado
├── models/                       # Modelos LLM (moondream)
├── data/
│   └── sessao_atual/
│       ├── raw/                  # Assets brutos do scraper
│       ├── processed/            # Assets pós-IA
│       └── .checkpoint.json      # Estado da sessão
├── output/                       # Pacotes gerados
│   └── beholder_YYYYMMDD_HHMMSS.zip
├── logs/
│   ├── beholder.log
│   ├── beholder.log.1
│   └── beholder.log.2
├── src/
│   ├── gui/
│   │   ├── main_window.py        # Adw.ApplicationWindow principal
│   │   ├── sidebar.py            # NavigationSplitView + itens
│   │   ├── theme.py              # CSS Dracula via CssProvider
│   │   ├── widgets.py            # StatusBar, LogTerminal, AssetGrid
│   │   └── pages/
│   │       ├── cacada.py         # Módulo Caçada
│   │       ├── cortex.py         # Módulo Córtex
│   │       ├── espolio.py        # Módulo Espólio
│   │       ├── protocolo.py      # Módulo Protocolo
│   │       └── grimorio.py       # Módulo Grimório
│   ├── scraper/
│   │   ├── stealth_spider.py     # Playwright + evasão + requests
│   │   └── html_parser.py        # Extração de assets do HTML
│   ├── ai_vision/
│   │   ├── ollama_lifecycle.py   # Subir/matar Ollama
│   │   ├── orchestrator.py       # Comunicação com API local
│   │   └── moondream_prompt.py   # Prompts de classificação
│   ├── transformer/
│   │   └── icon_alchemist.py     # K-Means + canvas circular
│   ├── exporter/
│   │   ├── packer.py             # Geração de .zip
│   │   └── dataset_writer.py     # Escrita do CSV
│   └── core/
│       ├── config/
│       │   ├── defaults.py       # Fonte única de verdade
│       │   └── config.py         # Loader XDG
│       ├── logging_config.py     # Setup centralizado de logs
│       ├── checkpoint.py         # Serialização/restauração de estado
│       └── asset_queue.py        # Wrapper threading.Queue
├── scripts/
│   ├── hooks/
│   │   ├── check_anonymity.py
│   │   ├── check_acentuacao.py
│   │   ├── check_file_size.py
│   │   └── check_anti_burla.py
│   ├── ci_local.sh
│   └── run_beholder.sh           # Entry point (sobe Ollama + UI)
├── teardown.sh                   # Kill Ollama + limpa VRAM
├── tests/
│   ├── conftest.py
│   ├── smoke/
│   │   ├── test_config.py
│   │   ├── test_logging.py
│   │   └── test_imports.py
│   └── unit/
│       ├── test_html_parser.py
│       ├── test_icon_alchemist.py
│       └── test_checkpoint.py
├── docs/
│   ├── design/                   # HTMLs do brainstorming → copiar de .superpowers/brainstorm/
│   ├── superpowers/specs/        # Este spec
│   │   └── 2026-04-13-beholder-design.md
│   ├── adr/
│   │   ├── ADR-01-pipeline-producer-consumer.md
│   │   ├── ADR-02-config-centralizado.md
│   │   └── ADR-03-ollama-efemero.md
│   ├── sprints/
│   │   ├── ativas/
│   │   ├── backlog/
│   │   └── concluidas/
│   └── assets.md                 # Prompts para geração de ícones (Grok/MJ/DALL-E)
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug.yml
│   │   ├── sprint.yml
│   │   └── task.yml
│   ├── pull_request_template.md
│   └── workflows/
│       └── ci.yml
├── .pre-commit-config.yaml
├── CLAUDE.md
├── GSD.md
├── Justfile
├── pyproject.toml
├── requirements.txt
├── main.py                       # Entry point Python
├── beholder-icon.png             # Logo (já existe)
└── .gitignore
```

---

## Sprint Roadmap

> **Regra para modelos executores:** Cada sprint é atômica e autocontida. Leia o CLAUDE.md e o GSD.md antes de qualquer sprint. Execute `just ci-local` ao finalizar. Zero ambiguidade — se algo não estiver especificado, consulte o spec antes de inventar.

---

### Sprint 0 — Infraestrutura (PRIORIDADE MÁXIMA)

**Objetivo:** Criar toda a estrutura de projeto antes de qualquer linha de código funcional.

**Tarefas:**

**0.1 — Estrutura de diretórios**
Criar todos os diretórios listados na seção "Estrutura de Diretórios Final".
Criar `__init__.py` vazios em: `src/`, `src/gui/`, `src/gui/pages/`, `src/scraper/`, `src/ai_vision/`, `src/transformer/`, `src/exporter/`, `src/core/`, `src/core/config/`, `tests/`, `tests/smoke/`, `tests/unit/`.

**0.2 — `.gitignore`**
Conteúdo exato (da CLAUDE.md global):
```gitignore
__pycache__/
*.py[cod]
node_modules/
venv/
.venv/
logs/
*.log
.env
*.key
*.pem
.DS_Store
Thumbs.db
.vscode/
.idea/
*.swp
bin/
models/
data/
output/
.superpowers/
dataset_assets.csv
```

**0.3 — `pyproject.toml`**
```toml
[build-system]
requires = ["setuptools>=65.0", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "project-beholder"
version = "0.1.0"
description = "Motor autônomo de predação visual"
requires-python = ">=3.12"
license = {text = "GPL-3.0"}

[tool.ruff]
target-version = "py312"
line-length = 120
select = ["E", "F", "W", "I", "UP", "B"]
ignore = ["E501", "E701", "E712", "E741", "W293", "F811"]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.12"
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
markers = [
    "smoke: testes rápidos de sanidade",
    "unit: testes isolados",
    "integration: multi-componente",
    "requires_display: precisa de display GTK",
    "requires_gpu: precisa de GPU NVIDIA",
]
```

**0.4 — `requirements.txt`**
```
# Interface
PyGObject>=3.48.0
# Scraping
playwright>=1.40.0
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
# Visão computacional
opencv-python>=4.8.0
Pillow>=10.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
# IA local
httpx>=0.25.0
# Utilitários
python-dotenv>=1.0.0
# Dev
pytest>=8.0.0
pytest-cov>=4.1.0
ruff>=0.3.0
pre-commit>=3.5.0
```

**0.5 — `CLAUDE.md`** (raiz do projeto)
```markdown
# CLAUDE.md — Project Beholder
Leitura obrigatória antes de qualquer sprint.

## Regras Invioláveis

### Acentuação PT-BR
OBRIGATÓRIA em todos os commits, código, docs, variáveis em português.
Nunca: "funcao", "configuracao", "execucao". Sempre: "função", "configuração", "execução".

### Anonimato
PROIBIDO mencionar nomes de IAs em commits, código ou docs.
Permitido: variáveis técnicas (OLLAMA_PORT, modelo, provider).

### Zero Emojis
Proibido em código, commits, docs e logs.

### Arquivo máximo: 800 linhas
Exceções: config, testes, registries.

### Threading GTK4
Threads NUNCA tocam widgets diretamente.
SEMPRE usar GLib.idle_add(callback, dados) para atualizar UI de threads.

### Ollama Efêmero (ADR-03)
Ollama SEMPRE roda em ./bin/ollama na porta 11435.
teardown.sh DEVE matar pelo PID exato + limpar OLLAMA_TMPDIR.

### Config Centralizada (ADR-02)
src/core/config/defaults.py é a ÚNICA fonte de verdade para defaults.
Nunca hardcode valores de configuração fora desse arquivo.

### Pipeline Bridges (ADR-01)
Toda comunicação com Ollama passa por src/ai_vision/orchestrator.py.
Nunca chame a API do Ollama diretamente de fora do orchestrator.

## Workflow Obrigatório
1. Ler CLAUDE.md + GSD.md antes de começar
2. Implementar mantendo compatibilidade
3. Testar incrementalmente
4. just ci-local antes de commitar
5. Commit em PT-BR sem mencionar IA

## Validação da UI
"Se não testou com python main.py, não está testado."
Screenshots da UI antes e depois de mudanças visuais.

## Checklist Pré-Commit
- [ ] Testes passando (just ci-local)
- [ ] Zero emojis no código
- [ ] Zero menções a IA
- [ ] Acentuação PT-BR correta
- [ ] GLib.idle_add em todas as atualizações de UI de threads
- [ ] Nenhum valor hardcoded fora de defaults.py
```

**0.6 — `GSD.md`** (raiz do projeto)
```markdown
# GSD — Get Shit Done

Resumo executivo do que quebra no Beholder.

## Regras Invioláveis (6)
1. GTK4 threads: GLib.idle_add() SEMPRE — nunca toque widget de thread
2. Ollama: sempre ./bin/ollama na porta 11435 — nunca ollama do sistema
3. Config: defaults.py é a lei — nunca hardcode fora dele
4. Bridges: orchestrator.py é o único que fala com Ollama diretamente
5. Checkpoints: sempre serializar estado antes de encerrar thread
6. Teardown: pkill pelo PID exato — nunca pkill -f ollama (mata outros processos)

## Armadilhas Críticas

### Threading GTK4
ERRADO: `self.label.set_text("novo")` dentro de thread
CERTO: `GLib.idle_add(self.label.set_text, "novo")`

### Ollama PID
ERRADO: `subprocess.run(["pkill", "-f", "ollama"])`
CERTO: `os.kill(self.ollama_pid, signal.SIGTERM)` + aguardar processo encerrar

### Fila cheia
A Fila A pode crescer indefinidamente se o scraper for mais rápido que a IA.
SEMPRE usar `queue.Queue(maxsize=50)` — não Queue() sem limite.

### Playwright no Linux
Requer: `playwright install chromium` após pip install.
Sem display: usar `--headless` SEMPRE.

### K-Means em imagens RGBA
Pillow → numpy: flatten para RGB antes de aplicar K-Means (ignorar canal alpha).
```python
img_array = np.array(img.convert("RGB")).reshape(-1, 3)
```

### Config XDG
Path correto: `Path.home() / ".config" / "beholder" / "config.ini"`
Criar diretório se não existir: `path.parent.mkdir(parents=True, exist_ok=True)`

## Checklists

### Pré-Sprint
- [ ] Ler sprint anterior (se existir)
- [ ] Ler CLAUDE.md
- [ ] just doctor (verifica dependências)

### Pré-Commit
- [ ] just ci-local (lint + smoke + unit)
- [ ] python main.py (validação visual manual)
- [ ] Zero GLib.idle_add faltando

## Comandos Essenciais
```bash
just setup          # instala deps + hooks
just ci-local       # lint + smoke + unit
just run            # python main.py
just doctor         # health check
just lint           # ruff format + check
```
```

**0.7 — `Justfile`**
```just
# Project Beholder — Task runner

setup:
    pip install -r requirements.txt
    playwright install chromium
    pre-commit install

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
    python -c "import src.gui.main_window; import src.core.config.config; import src.core.logging_config"
    echo "=== CI OK ==="

ci-quick:
    ruff check src/ tests/
    pytest tests/smoke/ --timeout=10 -q

run:
    python main.py

doctor:
    #!/usr/bin/env bash
    echo "=== Doctor ==="
    python --version
    python -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk; print('GTK4 OK')"
    python -c "import gi; gi.require_version('Adw', '1'); from gi.repository import Adw; print('Libadwaita OK')"
    python -c "import playwright; print('Playwright OK')"
    python -c "import cv2; print('OpenCV OK')"
    python -c "from sklearn.cluster import KMeans; print('scikit-learn OK')"
    [ -f bin/ollama ] && echo "Ollama binário OK" || echo "AVISO: bin/ollama não encontrado"

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
```

**0.8 — `hooks/pre-commit`** (adaptado do Conversor-Video-Para-ASCII)
```bash
#!/bin/bash
# Protocolo 1: Anti-emoji
if git diff --cached --name-only | xargs grep -l $'[\U0001F600-\U0001F9FF]' 2>/dev/null; then
    echo "ERRO: Emojis detectados no código. Remova-os antes do commit."
    exit 1
fi

# Protocolo 2: Anonimato (bloqueia menções a IAs em commits)
PATTERNS="[Cc]laude\|[Gg][Pp][Tt]\|[Gg]emini\|[Cc]opilot\|[Aa]nthropic\|[Oo]pen[Aa][Ii]"
if git diff --cached -- '*.py' '*.md' | grep "^+" | grep -v "^+++" | grep -q "$PATTERNS"; then
    echo "ERRO: Menção a IA detectada. Remova antes do commit."
    exit 1
fi

# Protocolo 3: Validação de sintaxe Python
for file in $(git diff --cached --name-only --diff-filter=ACM | grep "\.py$"); do
    if [ -f "$file" ]; then
        python -m py_compile "$file" 2>/dev/null || {
            echo "ERRO: Sintaxe Python inválida em $file"
            exit 1
        }
    fi
done

# Protocolo 4: Anti-burla (sem TODO/FIXME inline, sem except vazio)
for file in $(git diff --cached --name-only --diff-filter=ACM | grep "\.py$"); do
    if git diff --cached "$file" | grep "^+" | grep -v "^+++" | grep -q "# TODO\|# FIXME\|# HACK"; then
        echo "ERRO: TODO/FIXME/HACK detectado em $file. Crie uma issue no GitHub."
        exit 1
    fi
    if git diff --cached "$file" | grep "^+" | grep -v "^+++" | grep -q "except:$\|except Exception:$"; then
        echo "AVISO: except sem handler específico em $file. Considere tratar a exceção."
    fi
done

echo "Pre-commit OK"
exit 0
```

**0.9 — `hooks/commit-msg`**
```bash
#!/bin/bash
MSG=$(cat "$1")
    exit 1
fi
exit 0
```

**0.10 — `.pre-commit-config.yaml`**
```yaml
repos:
  - repo: local
    hooks:
      - id: check-anonymity
        name: "T1 — Anonimato (sem menções a IA)"
        entry: bash hooks/pre-commit
        language: system
        stages: [pre-commit]

      - id: check-syntax
        name: "T1 — Sintaxe Python"
        entry: python -m py_compile
        language: system
        types: [python]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        name: "T2 — Ruff lint"
        args: [--fix]
      - id: ruff-format
        name: "T3 — Ruff format"

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
        name: "T3 — Trailing whitespace"
      - id: end-of-file-fixer
        name: "T3 — End of file"
      - id: check-yaml
        name: "T1 — YAML válido"
      - id: check-json
        name: "T1 — JSON válido"
      - id: check-merge-conflict
        name: "T1 — Merge conflicts"
      - id: detect-private-key
        name: "T1 — Private keys"
```

**0.11 — `.github/ISSUE_TEMPLATE/bug.yml`**
```yaml
name: "Bug Report"
description: "Reportar um comportamento incorreto"
title: "[BUG] "
labels: ["bug"]
body:
  - type: textarea
    id: descricao
    attributes:
      label: "Descrição"
      description: "O que aconteceu?"
    validations:
      required: true
  - type: textarea
    id: passos
    attributes:
      label: "Passos para reproduzir"
      placeholder: "1. Abrir o Beholder\n2. Inserir URL X\n3. Clicar em INICIAR\n4. Ver erro"
    validations:
      required: true
  - type: textarea
    id: esperado
    attributes:
      label: "Comportamento esperado"
    validations:
      required: true
  - type: dropdown
    id: severidade
    attributes:
      label: "Severidade"
      options: ["P0 — Crítico (crash)", "P1 — Alto (feature quebrada)", "P2 — Médio", "P3 — Baixo"]
    validations:
      required: true
  - type: input
    id: ambiente
    attributes:
      label: "Ambiente"
      placeholder: "Ubuntu 24.04, Python 3.12, GTK 4.x"
```

**0.12 — `.github/ISSUE_TEMPLATE/sprint.yml`**
```yaml
name: "Sprint"
description: "Criar uma nova sprint de desenvolvimento"
title: "Sprint XX: "
labels: ["sprint"]
body:
  - type: input
    id: id
    attributes:
      label: "ID da Sprint"
      placeholder: "ex: 01"
    validations:
      required: true
  - type: dropdown
    id: prioridade
    attributes:
      label: "Prioridade"
      options: ["CRÍTICA", "ALTA", "MÉDIA", "BAIXA"]
    validations:
      required: true
  - type: dropdown
    id: tipo
    attributes:
      label: "Tipo"
      options: ["feature", "bugfix", "infra", "refactor", "docs", "perf"]
    validations:
      required: true
  - type: dropdown
    id: modulo
    attributes:
      label: "Módulo principal"
      options: ["infra", "gui", "cacada", "cortex", "espolio", "protocolo", "grimorio", "core", "docs"]
    validations:
      required: true
  - type: textarea
    id: objetivo
    attributes:
      label: "Objetivo"
    validations:
      required: true
  - type: textarea
    id: tarefas
    attributes:
      label: "Tarefas"
      placeholder: "- [ ] Tarefa 1\n- [ ] Tarefa 2"
    validations:
      required: true
  - type: textarea
    id: criterios
    attributes:
      label: "Critérios de aceitação"
      placeholder: "just ci-local passa\npython main.py abre sem erro\n..."
    validations:
      required: true
```

**0.13 — `.github/pull_request_template.md`**
```markdown
## Descrição
<!-- O que essa PR faz? -->

## Issue relacionada
Closes #

## Tipo de mudança
- [ ] feat: nova feature
- [ ] fix: correção de bug
- [ ] refactor: refatoração
- [ ] docs: documentação
- [ ] infra: infraestrutura

## Checklist
- [ ] `just ci-local` passa
- [ ] `python main.py` abre sem erro
- [ ] Nenhum emoji no código
- [ ] Nenhuma menção a IA
- [ ] Acentuação PT-BR correta
- [ ] GLib.idle_add em toda atualização de UI de thread
- [ ] Nenhum valor hardcoded fora de defaults.py
```

**0.14 — ADR-01: Pipeline Produtor-Consumidor**
Arquivo: `docs/adr/ADR-01-pipeline-producer-consumer.md`
```markdown
# ADR-01: Pipeline Produtor-Consumidor

**Status:** ACEITA — 2026-04-13

## Contexto
O Beholder precisa executar scraping, análise IA e exportação concorrentemente sem travar a UI.

## Decisão
Três threads independentes comunicando via `threading.Queue`:
- Thread A (Scraper) → Fila A → Thread B (AI Worker) → Fila B → Thread C (Exporter)
- Toda atualização de UI via `GLib.idle_add()`
- Filas com `maxsize=50` para backpressure

## Consequências
- Scraper não espera IA terminar
- UI nunca trava
- Filas limitadas evitam consumo ilimitado de memória
- Checkpoints serializam estado das filas

## Enforcement
Qualquer chamada direta a widget GTK fora da thread principal é violação desta ADR.
```

**0.15 — ADR-02: Config Centralizada**
Arquivo: `docs/adr/ADR-02-config-centralizado.md`
```markdown
# ADR-02: Config Centralizada (GOD MODE)

**Status:** ACEITA — 2026-04-13

## Decisão
`src/core/config/defaults.py` é a ÚNICA fonte de verdade para valores default.
Nenhum valor de configuração é hardcoded em outro lugar.

## Hierarquia
1. `defaults.py` — constantes puras
2. `~/.config/beholder/config.ini` — overrides do usuário (XDG)
3. `config.py` — loader com fallback para defaults

## Enforcement
Grep por strings literais de configuração fora de defaults.py é violação desta ADR.
```

**0.16 — ADR-03: Ollama Efêmero**
Arquivo: `docs/adr/ADR-03-ollama-efemero.md`
```markdown
# ADR-03: Ollama Efêmero

**Status:** ACEITA — 2026-04-13

## Decisão
O Ollama NUNCA roda permanentemente. É invocado quando necessário e encerrado ao final.

## Regras
- Binário em `./bin/ollama` (isolado do sistema)
- Porta exclusiva: 11435 (evita conflito com Ollama do sistema na 11434)
- Encerramento: `os.kill(PID_EXATO, signal.SIGTERM)` — nunca `pkill -f ollama`
- Limpeza: `shutil.rmtree(os.environ.get("OLLAMA_TMPDIR", "/tmp/ollama_beholder"))`

## Por que porta 11435?
Evita conflito com instâncias do sistema na porta padrão 11434.
```

**0.17 — `main.py`**
```python
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw
from src.gui.main_window import BeholderWindow
from src.core.logging_config import setup_logging


def main() -> None:
    setup_logging()
    app = Adw.Application(application_id="com.beholder.app")
    app.connect("activate", on_activate)
    app.run(None)


def on_activate(app: Adw.Application) -> None:
    window = BeholderWindow(application=app)
    window.present()


if __name__ == "__main__":
    main()
```

**0.18 — Copiar artefatos visuais**
```bash
mkdir -p docs/design
cp .superpowers/brainstorm/*/content/*.html docs/design/
```
Renomear os arquivos copiados para nomes semânticos:
- `layout-principal.html` → `01-layout-opcoes.html`
- `nomenclatura-v2.html` → `02-nomenclatura-opcoes.html`
- `sidebar-confirmada.html` → `03-sidebar-final.html`
- `botoes-comportamentos.html` → `04-botoes-comportamentos.html`
- `arquitetura.html` → `05-arquitetura-pipeline.html`

**0.19 — `docs/assets.md`**
Criar com o conteúdo completo de prompts para geração de ícones via Grok/MJ/DALL-E:
- Ícone do GTK App (beholder-icon.png já existe, servir como referência)
- Ícones dos botões fundamentais da UI: INICIAR, FURTIVO, PAUSAR, CANCELAR, EXPURGAR VRAM, ANALISAR, GERAR PACOTE, ABRIR PASTA, EXECUTAR LOTE, RETOMAR, SALVAR, TESTAR OLLAMA
- Para cada ícone: prompt positivo + prompt negativo + paleta Dracula
- Padrão: fundo preto (#000000) para ícones de status bar, branco (#ffffff) para mascaramento

**Critérios de aceitação da Sprint 0:**
```bash
just doctor          # todos os checks passam
just ci-local        # lint passa (sem código real ainda, só __init__.py)
python -c "import src"  # importação sem erro
git log --oneline -1    # commit com mensagem PT-BR sem menção a IA
```

---

### Sprint 1 — UI Shell (Janela GTK4 Navegável)

**Objetivo:** Janela completa com sidebar, tema Dracula, logo e 5 módulos navegáveis. Sem backend — apenas estrutura visual funcional.

**Arquivos a criar:**
- `src/gui/theme.py`
- `src/gui/main_window.py`
- `src/gui/sidebar.py`
- `src/gui/widgets.py`
- `src/gui/pages/cacada.py`
- `src/gui/pages/cortex.py`
- `src/gui/pages/espolio.py`
- `src/gui/pages/protocolo.py`
- `src/gui/pages/grimorio.py`

**1.1 — `src/gui/theme.py`**

Define as cores Dracula e gera o CSS para `Gtk.CssProvider`:

```python
DRACULA_BG = "#282a36"
DRACULA_CURRENT = "#44475a"
DRACULA_FG = "#f8f8f2"
DRACULA_COMMENT = "#6272a4"
DRACULA_PURPLE = "#bd93f9"
DRACULA_PINK = "#ff79c6"
DRACULA_GREEN = "#50fa7b"
DRACULA_ORANGE = "#ffb86c"
DRACULA_CYAN = "#8be9fd"
DRACULA_RED = "#ff5555"
DRACULA_YELLOW = "#f1fa8c"

CSS_DRACULA = f"""
window, .main-window {{
    background-color: {DRACULA_BG};
    color: {DRACULA_FG};
}}
.sidebar {{
    background-color: #21222c;
    border-right: 1px solid {DRACULA_CURRENT};
}}
.nav-row {{
    padding: 6px 12px;
    border-left: 2px solid transparent;
}}
.nav-row:selected {{
    background-color: {DRACULA_BG};
    border-left-color: {DRACULA_PURPLE};
    color: {DRACULA_PURPLE};
}}
.project-title {{
    color: {DRACULA_PURPLE};
    font-weight: bold;
    font-size: 13px;
    letter-spacing: 2px;
}}
.project-tagline {{
    color: {DRACULA_COMMENT};
    font-size: 10px;
}}
.status-bar {{
    background-color: #1e1f29;
    border-top: 1px solid {DRACULA_CURRENT};
    padding: 4px 12px;
    font-family: monospace;
    font-size: 11px;
    color: {DRACULA_COMMENT};
}}
.status-active {{ color: {DRACULA_GREEN}; }}
.btn-primary {{
    background-color: {DRACULA_PURPLE};
    color: {DRACULA_BG};
    font-weight: bold;
    border-radius: 5px;
}}
.btn-secondary {{
    background-color: {DRACULA_CURRENT};
    color: {DRACULA_CYAN};
    border-radius: 5px;
}}
.btn-danger {{
    background-color: {DRACULA_RED};
    color: {DRACULA_FG};
    border-radius: 5px;
}}
.log-terminal {{
    background-color: #1e1f29;
    color: {DRACULA_GREEN};
    font-family: monospace;
    font-size: 11px;
    border-radius: 6px;
    padding: 8px;
}}
entry {{
    background-color: #21222c;
    color: {DRACULA_FG};
    border: 1px solid {DRACULA_CURRENT};
    border-radius: 5px;
}}
entry:focus {{
    border-color: {DRACULA_PURPLE};
}}
"""

def apply_theme() -> None:
    from gi.repository import Gtk, Gdk
    provider = Gtk.CssProvider()
    provider.load_from_string(CSS_DRACULA)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
```

**1.2 — `src/gui/main_window.py`**

`Adw.ApplicationWindow` com `Gtk.Box` vertical:
- Topo: `Adw.HeaderBar` com título "BEHOLDER"
- Centro: `Adw.NavigationSplitView` (sidebar + conteúdo)
- Rodapé: `StatusBar` widget

Estrutura da classe:
```python
class BeholderWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Project Beholder")
        self.set_default_size(1100, 700)
        apply_theme()
        self._build_ui()

    def _build_ui(self) -> None:
        # Gtk.Box vertical (header + split + status)
        # Adw.NavigationSplitView com sidebar e stack
        # Conectar sidebar.on_row_selected → trocar página no stack
        ...
```

**1.3 — `src/gui/sidebar.py`**

`Gtk.ListBox` com 5 linhas + separador + Grimório:
- Cada linha: ícone simbólico Adwaita + label nome + label descrição
- Ícones sugeridos (Adwaita symbolic):
  - Caçada: `"find-location-symbolic"` ou `"system-search-symbolic"`
  - Córtex: `"brain-augmentation-symbolic"` ou `"preferences-system-symbolic"`
  - Espólio: `"folder-download-symbolic"`
  - Protocolo: `"view-list-symbolic"`
  - Grimório: `"open-book-symbolic"` ou `"accessories-text-editor-symbolic"`
- Header da sidebar: logo circular (GdkPixbuf de beholder-icon.png) + título + tagline

**1.4 — `src/gui/widgets.py`**

```python
class StatusBar(Gtk.Box):
    """Barra de status global na base da janela."""
    def update(self, status: str, progress: str, vram: str, session: str) -> None:
        ...

class LogTerminal(Gtk.ScrolledWindow):
    """Terminal de log em tempo real — Gtk.TextView append-only."""
    def append_line(self, text: str) -> None:
        # Chamado via GLib.idle_add — não chamar diretamente de threads
        ...
```

**1.5 — Pages (cada módulo)**

Cada arquivo em `src/gui/pages/` cria uma `Gtk.Box` com os widgets do módulo.
Sprint 1: estrutura visual completa, botões presentes mas sem conectar a backend.
Labels placeholder onde virão dados dinâmicos.

Exemplo mínimo para `cacada.py`:
```python
class CacadaPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(16)
        self.set_margin_bottom(16)
        self.set_margin_start(20)
        self.set_margin_end(20)
        self._build_ui()

    def _build_ui(self) -> None:
        # URL bar (Entry + botão INICIAR + toggle FURTIVO)
        # LogTerminal (ScrolledWindow + TextView)
        # Barra de progresso (Gtk.ProgressBar)
        ...
```

**Critérios de aceitação da Sprint 1:**
```bash
python main.py          # janela abre, sidebar navegável, tema Dracula visível
just ci-local           # lint passa
# Verificação manual:
# - logo visível no header da sidebar
# - clicar em cada item da sidebar troca o conteúdo
# - tema escuro com cores Dracula corretas
# - status bar visível no rodapé
```

---

### Sprint 2 — Config + Logging

**Objetivo:** Infraestrutura de configuração e logging funcionais.

**Arquivos a criar:**
- `src/core/config/defaults.py`
- `src/core/config/config.py`
- `src/core/logging_config.py`
- `tests/smoke/test_config.py`
- `tests/smoke/test_logging.py`

**2.1 — `src/core/config/defaults.py`**
```python
from pathlib import Path

DEFAULTS: dict = {
    "Scraper": {
        "timeout": 30,
        "delay_min": 1.0,
        "delay_max": 3.0,
        "jitter": True,
        "max_retries": 3,
        "modo_furtivo": False,
    },
    "IA": {
        "ollama_port": 11435,
        "modelo": "moondream",
        "max_concurrent": 1,
        "timeout_analise": 60,
    },
    "Saida": {
        "diretorio_output": "output",
        "diretorio_data": "data",
        "kmeans_cores": 4,
        "formato_zip": "beholder_{timestamp}.zip",
    },
    "Interface": {
        "tema": "dracula",
        "log_nivel": "INFO",
    },
}
```

**2.2 — `src/core/config/config.py`**
- Loader que lê `~/.config/beholder/config.ini`
- Fallback para `defaults.py` se chave não encontrada
- `get(section, key)` → valor com tipo correto
- `save()` → persiste em XDG path
- Criar diretório XDG se não existir

**2.3 — `src/core/logging_config.py`**
```python
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging() -> None:
    Path("logs").mkdir(exist_ok=True)
    fmt = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
    # Handler arquivo: DEBUG+, 10MB, 3 backups
    file_handler = RotatingFileHandler(
        "logs/beholder.log", maxBytes=10*1024*1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(fmt))
    # Handler console: INFO+
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(fmt))
    # Root logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)
    # Silenciar loggers barulhentos
    for noisy in ["httpx", "urllib3", "asyncio", "PIL", "playwright"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)
```

**Critérios de aceitação da Sprint 2:**
```bash
just ci-local
python -c "from src.core.config.config import Config; c = Config(); print(c.get('Scraper', 'timeout'))"
# deve imprimir: 30
python -c "from src.core.logging_config import setup_logging; setup_logging(); import logging; logging.getLogger('beholder').info('teste')"
# deve criar logs/beholder.log
```

---

### Sprint 3 — Scraper Básico (requests)

**Objetivo:** Caçada funcional com requests simples (sem Playwright). Integração com UI via GLib.idle_add.

**Arquivos a criar/modificar:**
- `src/scraper/html_parser.py` (novo)
- `src/scraper/stealth_spider.py` (novo, versão requests)
- `src/core/asset_queue.py` (novo)
- `src/gui/pages/cacada.py` (conectar backend)
- `tests/unit/test_html_parser.py` (novo)

**3.1 — `src/scraper/html_parser.py`**
```python
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger("beholder.parser")

@dataclass
class Asset:
    url: str
    tipo: str  # "icon" | "image" | "svg" | "background"
    origem: str  # URL da página onde foi encontrado

def extrair_assets(html: str, base_url: str) -> list[Asset]:
    """Extrai todos os assets de imagem de uma página HTML."""
    ...
```

**3.2 — `src/scraper/stealth_spider.py`**
```python
import threading
import time
import random
import logging
import requests
from queue import Queue
from src.scraper.html_parser import extrair_assets, Asset

logger = logging.getLogger("beholder.scraper")

class StealthSpider:
    def __init__(self, fila_saida: Queue, callback_progresso, callback_log) -> None:
        self._fila_saida = fila_saida
        self._callback_progresso = callback_progresso  # GLib.idle_add target
        self._callback_log = callback_log              # GLib.idle_add target
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None

    def iniciar(self, url: str) -> None:
        self._parar.clear()
        self._thread = threading.Thread(target=self._executar, args=(url,), daemon=True)
        self._thread.start()

    def pausar(self) -> None:
        self._parar.set()

    def _executar(self, url: str) -> None:
        # 1. requests.get(url) com timeout configurado
        # 2. extrair_assets(html, url)
        # 3. Para cada asset: baixar + put na fila_saida + GLib.idle_add(callback_progresso)
        # 4. Checar self._parar.is_set() após cada asset
        ...
```

**3.3 — `src/core/asset_queue.py`**
```python
from queue import Queue
from dataclasses import dataclass

SENTINEL = None  # Marca fim da fila

@dataclass
class AssetProcessado:
    caminho_local: str
    url_original: str
    tipo: str
    tags: dict
    paleta: list[str]

fila_scraper: Queue = Queue(maxsize=50)    # Thread A → Thread B
fila_processada: Queue = Queue(maxsize=50) # Thread B → Thread C
```

**3.4 — Integração com `cacada.py`**
- Botão INICIAR conectado a `StealthSpider.iniciar(url)`
- Log updates via `GLib.idle_add(self.log_terminal.append_line, mensagem)`
- Progresso via `GLib.idle_add(self.progress_bar.set_fraction, valor)`
- Botão muda para PAUSAR durante execução

**Critérios de aceitação da Sprint 3:**
```bash
just ci-local
python main.py
# Verificar manualmente:
# 1. Inserir https://example.com
# 2. Clicar INICIAR
# 3. Ver log em tempo real sem travar a UI
# 4. Clicar PAUSAR — log para, botão muda
```

---

### Sprint 4 — Modo Furtivo (Playwright)

**Objetivo:** Ativar Playwright no stealth_spider quando toggle FURTIVO estiver ativo.

**Arquivos a modificar:**
- `src/scraper/stealth_spider.py` (adicionar modo Playwright)

**4.1 — Adição do modo Playwright ao StealthSpider**

Quando `modo_furtivo=True`:
- Usar `playwright.sync_api` em thread separada (não async)
- `browser.new_context()` com user_agent aleatório, viewport variado
- Jitter: `time.sleep(random.uniform(delay_min, delay_max))`
- Backoff exponencial em erros 429/403: aguardar 2^tentativa segundos
- Em bloqueio detectado (Cloudflare challenge): novo contexto + novo fingerprint

**Critérios de aceitação da Sprint 4:**
```bash
just ci-local
# Verificar manualmente:
# 1. Toggle FURTIVO ativado
# 2. URL de site com proteção básica
# 3. Log mostra "modo furtivo ativo"
# 4. Assets são extraídos sem erro 403
```

---

### Sprint 5 — Córtex: Ollama Lifecycle

**Objetivo:** Subir e matar o Ollama corretamente. UI do Córtex conectada.

**Arquivos a criar:**
- `src/ai_vision/ollama_lifecycle.py`
- `scripts/run_beholder.sh` (atualizado)
- `teardown.sh`

**5.1 — `src/ai_vision/ollama_lifecycle.py`**
```python
import subprocess
import os
import signal
import shutil
import logging
from pathlib import Path

logger = logging.getLogger("beholder.ollama")

OLLAMA_BIN = Path("./bin/ollama")
OLLAMA_PORT = 11435
OLLAMA_TMPDIR = Path("/tmp/ollama_beholder")

class OllamaLifecycle:
    def __init__(self) -> None:
        self._pid: int | None = None
        self._processo: subprocess.Popen | None = None

    def subir(self) -> bool:
        """Sobe o Ollama em ./bin/ollama na porta 11435."""
        if not OLLAMA_BIN.exists():
            logger.error("bin/ollama não encontrado")
            return False
        OLLAMA_TMPDIR.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["OLLAMA_HOST"] = f"127.0.0.1:{OLLAMA_PORT}"
        env["OLLAMA_TMPDIR"] = str(OLLAMA_TMPDIR)
        self._processo = subprocess.Popen(
            [str(OLLAMA_BIN), "serve"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._pid = self._processo.pid
        logger.info("Ollama subindo (PID %s) na porta %s", self._pid, OLLAMA_PORT)
        return True

    def expurgar(self) -> None:
        """Mata o Ollama pelo PID exato e limpa VRAM."""
        if self._pid:
            try:
                os.kill(self._pid, signal.SIGTERM)
                self._processo.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                if self._pid:
                    os.kill(self._pid, signal.SIGKILL)
            finally:
                self._pid = None
                self._processo = None
        if OLLAMA_TMPDIR.exists():
            shutil.rmtree(OLLAMA_TMPDIR, ignore_errors=True)
        logger.info("Ollama encerrado, VRAM liberada")
```

**Critérios de aceitação da Sprint 5:**
```bash
# Verificar manualmente:
# 1. Clicar ANALISAR → log mostra "Ollama subindo"
# 2. Monitor de processos mostra ollama na porta 11435
# 3. Clicar EXPURGAR VRAM → processo encerrado, VRAM: 0 GB no status
```

---

### Sprint 6 — Córtex: Moondream + Transformação

**Objetivo:** Análise real de imagens com Moondream. K-Means aplicado.

**Arquivos a criar:**
- `src/ai_vision/orchestrator.py`
- `src/ai_vision/moondream_prompt.py`
- `src/transformer/icon_alchemist.py`
- `tests/unit/test_icon_alchemist.py`

**6.1 — `src/ai_vision/moondream_prompt.py`**
```python
PROMPT_CLASSIFICACAO = (
    "Analyze this image and respond in JSON with these exact fields: "
    '{"tipo": "one of: icon|background|logo|vector|photo|ui_element|other", '
    '"descricao": "brief description in english, max 20 words", '
    '"tags": ["tag1", "tag2", "tag3"]}'
)
```

**6.2 — `src/transformer/icon_alchemist.py`**
```python
from sklearn.cluster import KMeans
import numpy as np
from PIL import Image
from pathlib import Path

def extrair_paleta(caminho_imagem: str | Path, n_cores: int = 4) -> list[str]:
    """
    Aplica K-Means na imagem e retorna N cores dominantes em hex.
    Ignora canal alpha (converte para RGB antes).
    """
    img = Image.open(caminho_imagem).convert("RGB")
    pixels = np.array(img).reshape(-1, 3)
    # Subsample para performance em imagens grandes
    if len(pixels) > 10000:
        pixels = pixels[::len(pixels)//10000]
    kmeans = KMeans(n_clusters=n_cores, random_state=42, n_init=10)
    kmeans.fit(pixels)
    cores = kmeans.cluster_centers_.astype(int)
    return [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in cores]

def criar_icone_circular(
    caminho_entrada: str | Path,
    caminho_saida: str | Path,
    tamanho: int = 256,
) -> None:
    """
    Redimensiona e recorta imagem em canvas circular com fundo transparente.
    """
    ...
```

**Critérios de aceitação da Sprint 6:**
```bash
python -c "
from src.transformer.icon_alchemist import extrair_paleta
cores = extrair_paleta('beholder-icon.png')
print(cores)  # deve retornar lista de 4 hex colors
"
just ci-local
```

---

### Sprint 7 — Espólio: Exportação

**Objetivo:** Gerar pacote .zip + CSV final. UI do Espólio conectada.

**Arquivos a criar:**
- `src/exporter/packer.py`
- `src/exporter/dataset_writer.py`

**7.1 — `src/exporter/dataset_writer.py`**

Colunas do CSV: `url_original,caminho_local,tipo,descricao,tags,paleta_hex,timestamp`

**7.2 — `src/exporter/packer.py`**

- Organiza assets em subpastas por tipo (icons/, backgrounds/, outros/)
- Gera `dataset_assets.csv` final
- Compacta tudo em `output/beholder_{timestamp}.zip`
- Nome do ZIP: `beholder_YYYYMMDD_HHMMSS.zip`

**Critérios de aceitação da Sprint 7:**
```bash
# Verificar manualmente após rodada completa:
# 1. Clicar GERAR PACOTE
# 2. output/beholder_*.zip criado
# 3. ZIP contém: icons/, backgrounds/, outros/, dataset_assets.csv
# 4. CSV tem todas as colunas com dados corretos
```

---

### Sprint 8 — Protocolo: Batch + Checkpoints

**Objetivo:** Fila de URLs com progresso rastreado e capacidade de retomada.

**Arquivos a criar:**
- `src/core/checkpoint.py`
- `src/gui/pages/protocolo.py` (conectar backend)

**8.1 — `src/core/checkpoint.py`**
```python
import json
from pathlib import Path
from dataclasses import dataclass, asdict

CHECKPOINT_PATH = Path("data/sessao_atual/.checkpoint.json")

@dataclass
class EstadoCheckpoint:
    urls_pendentes: list[str]
    urls_concluidas: list[str]
    urls_com_erro: list[str]
    url_atual: str | None
    timestamp: str

def salvar(estado: EstadoCheckpoint) -> None:
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(json.dumps(asdict(estado), ensure_ascii=False, indent=2))

def carregar() -> EstadoCheckpoint | None:
    if not CHECKPOINT_PATH.exists():
        return None
    dados = json.loads(CHECKPOINT_PATH.read_text())
    return EstadoCheckpoint(**dados)

def existe() -> bool:
    return CHECKPOINT_PATH.exists()
```

**Critérios de aceitação da Sprint 8:**
```bash
just ci-local
# Verificar manualmente:
# 1. Adicionar 3 URLs ao Protocolo
# 2. EXECUTAR LOTE
# 3. PAUSAR no meio da 2ª URL
# 4. Status mostra "pausada"
# 5. Fechar e reabrir o app
# 6. RETOMAR SESSÃO → continua de onde parou
```

---

### Sprint 9 — Grimório: UI de Configurações

**Objetivo:** Todas as configurações editáveis e persistidas via XDG.

**Arquivos a modificar:**
- `src/gui/pages/grimorio.py` (conectar ao Config)

**Seções do Grimório:**
- **Scraper:** timeout, delay_min, delay_max, max_retries
- **IA:** ollama_port, modelo, timeout_analise
- **Saída:** diretorio_output, kmeans_cores
- **Ações:** SALVAR, TESTAR OLLAMA, RESTAURAR PADRÕES, ABRIR LOGS

**Critérios de aceitação da Sprint 9:**
```bash
# Verificar manualmente:
# 1. Mudar ollama_port para 11436
# 2. Clicar SALVAR
# 3. Fechar e reabrir o app
# 4. Porta mostra 11436 (persiste)
# 5. RESTAURAR PADRÕES → volta para 11435
# 6. TESTAR OLLAMA → verde se Ollama ativo, vermelho se não
```

---

### Sprint 10 — Polish, Docs e assets.md

**Objetivo:** Finalizar documentação, criar assets.md completo, copiar HTMLs de design.

**Tarefas:**
1. Copiar HTMLs do brainstorming para `docs/design/` com nomes semânticos
2. Criar `docs/superpowers/specs/2026-04-13-beholder-design.md` com este spec
3. Criar `docs/assets.md` completo com todos os prompts mapeados
4. Criar `docs/sprints/backlog/` com issues futuras identificadas
5. Revisar e completar `README.md` do projeto
6. `just ci-local` deve passar completamente

---

## Arquivos Críticos

| Arquivo | Sprint | Importância |
|---------|--------|-------------|
| `src/gui/theme.py` | 1 | Define toda a paleta Dracula |
| `src/gui/main_window.py` | 1 | Entry point da UI |
| `src/core/config/defaults.py` | 2 | Fonte única de verdade (ADR-02) |
| `src/core/logging_config.py` | 2 | Observabilidade de tudo |
| `src/scraper/stealth_spider.py` | 3+4 | Core do produto |
| `src/ai_vision/ollama_lifecycle.py` | 5 | Gestão de VRAM (ADR-03) |
| `src/transformer/icon_alchemist.py` | 6 | K-Means + exportação circular |
| `src/core/checkpoint.py` | 8 | Retomada de sessão |
| `CLAUDE.md` | 0 | Regras invioláveis |
| `GSD.md` | 0 | Armadilhas críticas |

---

## Verificação End-to-End

Teste completo após Sprint 10:
```bash
just setup
just doctor
python main.py &
# 1. Caçada: inserir https://example.com → INICIAR → ver log
# 2. Aguardar 5 assets → PAUSAR → ver status "pausada"
# 3. RETOMAR → continua
# 4. Córtex: ANALISAR → ver grid imagem × tags
# 5. Espólio: GERAR PACOTE → ver ZIP em output/
# 6. Protocolo: adicionar 2 URLs → EXECUTAR LOTE → acompanhar progresso
# 7. Grimório: mudar timeout → SALVAR → TESTAR OLLAMA
just ci-local
```

---

*"Código que não pode ser entendido não pode ser mantido."*
*"Local First. Zero Emojis. Zero Bullshit."*
