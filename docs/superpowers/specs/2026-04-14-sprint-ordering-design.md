# Sprint Ordering -- Fases 1-4

**Data:** 2026-04-14
**Prioridade definida pelo usuário:** Estabilidade > Polish Visual > Distribuição

---

## Visão Geral

Ordenação e estratégia de paralelismo para as Sprints 11-15 do backlog do Project Beholder. Quatro fases sequenciais, com paralelismo na Fase 2.

```
FASE 1: Sprint 13 (estabilidade)
FASE 2: Sprint 11 + Sprint 12 [paralelo via worktrees]
FASE 3: Sprint 14 (packaging)
FASE 4: Sprint 15 (CI/CD)
```

---

## Fase 1 -- Sprint 13: Correções Retroativas

**Objetivo:** Pipeline funcional de ponta a ponta. Segunda execução de ANALISAR sem deadlock.

**Prioridade:** Crítica -- bloqueia todas as outras fases.

### Ordem interna de execução

A ordem respeita dependências entre bugs (ex: filas corrigidas antes de conectar o pipeline).

| Passo | Bug/Violação | Arquivo(s) | Mudança |
|-------|-------------|------------|---------|
| 1 | BUG-02 + BUG-10 | `asset_queue.py` | Filas singleton → classe `FilasPipeline` com `nova_sessao()` que recria filas limpas |
| 2 | BUG-03 | `orchestrator.py` | `fila_scraper.get()` → `get(timeout=1.0)` em loop com verificação de `_evento_parar` |
| 3 | BUG-05 | `cortex.py`, `espolio.py`, `main_window.py` | Conectar `CortexPage._cb_asset_processado` → `EspolioPage.registrar_asset` via referência cruzada em `main_window.py` |
| 4 | BUG-04 | `protocolo.py` | Após `concluido_evt.wait(timeout=300)`, checar `is_set()` — se False, marcar como "erro" |
| 5 | BUG-06 | `cortex.py` | `set_ellipsize(3)` → `set_ellipsize(Pango.EllipsizeMode.END)` com import de Pango |
| 6 | BUG-07 + BUG-08 | `logging_config.py`, `checkpoint.py`, `ollama_lifecycle.py` | `Path("logs")` e `Path.cwd()` → caminhos relativos a `Path(__file__).resolve().parent` |
| 7 | BUG-09 | `grimorio.py` | `httpx.get()` síncrono na GTK thread → mover para `threading.Thread` com `GLib.idle_add` no resultado |
| 8 | BUG-11 | `stealth_spider.py` | `hash(asset.url)` → `hashlib.md5(asset.url.encode()).hexdigest()[:12]` |
| 9 | VIOLAÇÃO-02 | `requirements.txt` | Remover linha `PyGObject>=3.48,<3.50` |
| 10 | VIOLAÇÃO-04 | `Justfile` | Prefixar comandos com `.venv/bin/` onde aplicável |
| 11 | Testes novos | `tests/unit/test_orchestrator_threading.py` | Testes de threading para Orchestrator com timeout e cancelamento |

### Critério de aceite

- `just ci-local` verde com 70+ testes
- `python main.py` → Busca funciona → Córtex ANALISAR funciona (com Ollama) → Espólio mostra contadores reais → GERAR PACOTE gera .zip válido
- Segunda execução de ANALISAR sem deadlock
- EXPURGAR VRAM encerra Orchestrator em < 3 segundos
- Timeout no Protocolo marca URL como "erro" (não "concluída")

---

## Fase 2 -- Sprint 11 + Sprint 12 [Paralelo]

Executadas em paralelo via worktrees. Zero overlap de arquivos.

### Sprint 11: UI Polish

**Objetivo:** Interface visualmente polida nas 5 abas.

| Arquivo | Mudança |
|---------|---------|
| `src/gui/pages/espolio.py` | Substituir `Gtk.Grid` por 5 mini-cards horizontais (Gtk.Frame com número grande + label pequeno) |
| `src/gui/theme.py` | `.status-bar` font-size: `13px` → `15px` |
| `src/gui/widgets.py` | Capitalizar labels da StatusBar ("nova" → "Nova", etc.) |
| `src/gui/pages/busca.py` | Verificar/corrigir labels de `Gtk.Frame` para capitalização correta |
| `src/gui/pages/cortex.py` | Idem |
| `src/gui/pages/protocolo.py` | Idem |
| `src/gui/pages/grimorio.py` | Idem |

**Critério de aceite:**
- `python main.py` abre sem erro
- Espólio mostra 5 cards horizontais com número grande + label pequeno
- Nenhum label de Gtk.Frame em minúsculo nas 5 abas
- Status bar com fonte maior e texto capitalizado
- `just ci-local` verde

### Sprint 12: Instalação e Desktop

**Objetivo:** Instalação funcional com .desktop e download automático do Moondream.

| Arquivo | Mudança |
|---------|---------|
| `install.sh` | Adicionar `--system-site-packages` na criação do venv + criar `.desktop` + corrigir acentuação |
| `requirements.txt` | PyGObject já removido na Sprint 13 -- verificar apenas |
| `teardown.sh` | Corrigir acentuação na linha 60 |
| `run.sh` | Adicionar função `verificar_modelo_ollama()` que baixa Moondream se ausente |
| `src/ai_vision/ollama_lifecycle.py` | `subprocess.Popen` com streaming de stdout + timeout 600s para download |

**Critério de aceite:**
- `./install.sh` executa sem erro
- `.desktop` criado em `~/.local/share/applications/`
- Ícone em `~/.local/share/icons/hicolor/512x512/apps/`
- App aparece no launcher GNOME
- `./run.sh` baixa Moondream se ausente
- ANALISAR mostra progresso do download no Log IA
- `just ci-local` verde

### Verificação de zero overlap

| Sprint 11 toca | Sprint 12 toca |
|----------------|----------------|
| espolio.py | install.sh |
| theme.py | run.sh |
| widgets.py | teardown.sh |
| busca.py | ollama_lifecycle.py |
| cortex.py | requirements.txt (verificação apenas) |
| protocolo.py | |
| grimorio.py | |

Nenhum arquivo em comum. Merge sem conflito garantido.

---

## Fase 3 -- Sprint 14: Packaging

**Objetivo:** Distribuição em 3 formatos (`.deb`, Flatpak, AppImage).

**Depende de:** Sprint 12 (install corrigido) + Sprint 13 (bugs corrigidos)

**Escopo:** Criar scripts de build para cada formato + workflow de release no GitHub Actions.

---

## Fase 4 -- Sprint 15: CI/CD

**Objetivo:** Pipeline de CI completo com testes, lint e screenshots automáticos.

**Depende de:** Sprint 14 (release workflow precisa dos builds)

**Escopo:** Workflows GitHub Actions para CI (push/PR) + release (tags v*) + pre-commit com screenshots.

---

## Resumo de execução

| Fase | Sprint(s) | Modo | Bloqueada por |
|------|-----------|------|---------------|
| 1 | 13 | Sequencial | Nenhuma |
| 2 | 11 + 12 | Paralelo (worktrees) | Fase 1 |
| 3 | 14 | Sequencial | Fase 2 |
| 4 | 15 | Sequencial | Fase 3 |

---

## Validação obrigatória

Toda sprint deve ser validada executando `python main.py` e verificando visualmente o resultado antes de declarar conclusão. Type checking e testes automatizados verificam correção de código, não correção de feature.
