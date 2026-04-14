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
```python
# ERRADO — trava ou corrompe a UI:
self.label.set_text("novo")  # dentro de thread

# CERTO:
GLib.idle_add(self.label.set_text, "novo")
```

### Ollama PID
```python
# ERRADO — mata instâncias do sistema:
subprocess.run(["pkill", "-f", "ollama"])

# CERTO:
os.kill(self.ollama_pid, signal.SIGTERM)
self._processo.wait(timeout=5)
```

### Fila sem limite
```python
# ERRADO — memória ilimitada se scraper > IA:
fila = Queue()

# CERTO — backpressure de 50 itens:
fila = Queue(maxsize=50)
```

### Playwright no Linux
```bash
# Obrigatório após pip install:
playwright install chromium

# Sempre headless (sem display):
browser = p.chromium.launch(headless=True)
```

### K-Means em imagens RGBA
```python
# ERRADO — KMeans falha com 4 canais:
pixels = np.array(img).reshape(-1, 4)

# CERTO — converter para RGB antes:
pixels = np.array(img.convert("RGB")).reshape(-1, 3)
```

### Config XDG
```python
# CERTO — path XDG padrão:
config_path = Path.home() / ".config" / "beholder" / "config.ini"
config_path.parent.mkdir(parents=True, exist_ok=True)
```

### PyGObject — NUNCA instalar via pip
```bash
# ERRADO — falha porque precisa de headers de sistema:
pip install PyGObject

# CERTO — é um pacote de sistema, instalado pelo install.sh:
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1

# O venv é criado com --system-site-packages para acessar o gi do sistema.
# Nunca remover essa flag ao recriar o venv.
```

### Caminhos do Ollama — tudo dentro do projeto
```bash
# ERRADO — espalha arquivos fora do projeto:
OLLAMA_TMPDIR="/tmp/ollama_beholder"   # fora do projeto
# Ollama salva modelos em ~/.ollama/models por padrão — também errado

# CERTO — isolado dentro de Project_Beholder/:
OLLAMA_TMPDIR="$PROJECT_DIR/data/ollama_tmp"
OLLAMA_MODELS="$PROJECT_DIR/models"

# run.sh exporta essas variáveis antes de iniciar o Python.
# ollama_lifecycle.py deve usar Config().get('IA', 'ollama_tmpdir') e 'ollama_models'
# e converter para path absoluto com Path(PROJECT_DIR) / valor_relativo.
```

### Sentinel nas filas
```python
# Sempre enviar SENTINEL ao final para sinalizar EOF:
fila_scraper.put(None)  # Thread B para quando recebe None
```

## Estado das Sprints

| Sprint | Status | Descrição |
|--------|--------|-----------|
| 0 | COMPLETA | Infra: dirs, hooks, pyproject.toml, CLAUDE.md, ADRs |
| 1 | COMPLETA | UI Shell: GTK4 + tema Dracula |
| 2 | COMPLETA | Config + Logging |
| 3 | COMPLETA | Scraper básico (requests) |
| 4 | COMPLETA | Modo Furtivo (Playwright) |
| 5 | COMPLETA | Ollama Lifecycle (ADR-03) |
| 6 | COMPLETA | Moondream + K-Means |
| 7 | COMPLETA | Espólio: .zip + CSV |
| 8 | COMPLETA | Protocolo: batch + checkpoints |
| 9 | COMPLETA | Grimório: configurações persistidas |
| 10 | COMPLETA | Polish visual das 5 abas |
| 11 | BACKLOG | UI: Espólio redesign + textos + status bar (#6) |
| 12 | BACKLOG | Instalação: .desktop + moondream + venv fix (#7) |
| 13 | COMPLETA | Correções retroativas da auditoria (#8) |
| 14 | BACKLOG | Packaging: deb + flatpak + appimage (#9) |
| 15 | BACKLOG | Workflow CI/CD + pre-commit screenshots (#10) |

## Bugs Conhecidos

### Pendentes

| ID | Arquivo | Problema |
|----|---------|---------|
| BUG-01 | `install.sh:88` | venv sem `--system-site-packages` — GTK4 pode não funcionar (Sprint 12) |

### Resolvidos (Sprint 13)

| ID | Correção |
|----|----------|
| BUG-02 | FilasPipeline com nova_sessao() substitui singletons |
| BUG-03 | get(timeout=1.0) + loop com verificação de evento |
| BUG-04 | wait() retorna bool, timeout marca como erro |
| BUG-05 | CortexPage.conectar_espolio() via main_window.py |
| BUG-06 | Pango.EllipsizeMode.END substitui magic number |
| BUG-07 | Path(__file__) em logging_config e checkpoint |
| BUG-08 | Path(__file__) em ollama_lifecycle |
| BUG-09 | httpx em thread separada com GLib.idle_add |
| BUG-11 | hashlib.md5 substitui hash() instável |

## Distribuição

O Beholder suporta 3 formatos de distribuição (Sprint 14):

- **`.deb`** — Ubuntu/Debian: `sudo dpkg -i beholder_VERSION_amd64.deb`
- **Flatpak** — universal GNOME: `flatpak install beholder.flatpak`
- **AppImage** — universal Linux: `./Beholder-VERSION-x86_64.AppImage`

Builds automáticos via `.github/workflows/release.yml` ao criar tag `v*`.

---

## Checklists

### Pré-Sprint
- [ ] Ler sprint anterior (se existir)
- [ ] Ler CLAUDE.md
- [ ] just doctor (verifica dependências)

### Pré-Commit
- [ ] just ci-local (lint + smoke + unit)
- [ ] python main.py (validação visual manual)
- [ ] Zero GLib.idle_add faltando
- [ ] Nenhum except: vazio

## Comandos Essenciais
```bash
just setup          # instala deps + hooks
just ci-local       # lint + smoke + unit
just run            # python main.py
just doctor         # health check
just lint           # ruff format + check
```

## Módulos e Arquivos-Chave
| Módulo | Arquivo principal | Thread |
|--------|-------------------|--------|
| Caçada (UI) | src/gui/pages/cacada.py | main |
| Scraper | src/scraper/stealth_spider.py | Thread A |
| AI Worker | src/ai_vision/orchestrator.py | Thread B |
| Exporter | src/exporter/packer.py | Thread C |
| Ollama | src/ai_vision/ollama_lifecycle.py | main |
| Config | src/core/config/defaults.py | — |
| Logs | src/core/logging_config.py | — |
| Checkpoints | src/core/checkpoint.py | — |
