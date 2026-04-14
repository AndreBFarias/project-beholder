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

### Sentinel nas filas
```python
# Sempre enviar SENTINEL ao final para sinalizar EOF:
fila_scraper.put(None)  # Thread B para quando recebe None
```

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
