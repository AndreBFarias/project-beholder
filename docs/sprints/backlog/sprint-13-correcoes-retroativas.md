# Sprint 13 — Correções Retroativas (Auditoria)

**Issue:** #8
**Status:** Completa
**Prioridade:** Crítica

---

## Contexto

Auditoria externa das Sprints 0–10 identificou 11 bugs (5 críticos) e 4 violações.
Esta sprint corrige todos eles. Ver relatório completo no issue #8.

---

## Bugs Críticos (corrigir primeiro)

| ID | Arquivo | Linha | Problema |
|----|---------|-------|----------|
| BUG-02 | `src/core/asset_queue.py` | 44–47 | Filas singleton causam deadlock entre sessões |
| BUG-03 | `src/ai_vision/orchestrator.py` | ~111 | `get()` sem timeout — cancelamento não funciona |
| BUG-04 | `src/gui/pages/protocolo.py` | ~327 | Timeout não marca URL como erro |
| BUG-05 | `src/gui/pages/cortex.py` + `espolio.py` | ~113 + ~170 | `registrar_asset()` nunca chamado — Espólio sempre vazio |

---

## Bugs Importantes

| ID | Arquivo | Linha | Problema |
|----|---------|-------|----------|
| BUG-06 | `src/gui/pages/cortex.py` | ~64 | `set_ellipsize(3)` — magic number, deve ser `Pango.EllipsizeMode.END` |
| BUG-07 | `src/core/logging_config.py` | 13 | `Path("logs")` relativo ao CWD |
| BUG-08 | `src/ai_vision/ollama_lifecycle.py` | ~125 | `Path.cwd()` para localizar binário |
| BUG-09 | `src/gui/pages/grimorio.py` | ~215 | HTTP síncrono na thread GTK — UI congela |
| BUG-10 | `src/core/asset_queue.py` | 44 | Estado residual entre execuções |
| BUG-11 | `src/scraper/stealth_spider.py` | ~255 | `hash()` instável para nomes de arquivo |

---

## Violações

| ID | Arquivo | Problema |
|----|---------|---------|
| VIOLAÇÃO-02 | `requirements.txt` | PyGObject via pip (GSD.md proíbe) |
| VIOLAÇÃO-04 | `Justfile` | Comandos CI sem `.venv/bin/` |

---

## Arquivos a Modificar

- `src/core/asset_queue.py` (BUG-02, BUG-10)
- `src/ai_vision/orchestrator.py` (BUG-03)
- `src/gui/pages/protocolo.py` (BUG-04)
- `src/gui/pages/cortex.py` (BUG-05, BUG-06)
- `src/gui/pages/espolio.py` (BUG-05)
- `src/gui/main_window.py` (BUG-05 — conectar páginas)
- `src/core/logging_config.py` (BUG-07)
- `src/core/checkpoint.py` (BUG-07 — mesmo padrão)
- `src/ai_vision/ollama_lifecycle.py` (BUG-08)
- `src/gui/pages/grimorio.py` (BUG-09)
- `src/scraper/stealth_spider.py` (BUG-11)
- `requirements.txt` (VIOLAÇÃO-02)
- `Justfile` (VIOLAÇÃO-04)
- `tests/unit/test_orchestrator_threading.py` (novo — testes de threading)

---

## Checklist de Execução

- [ ] Ler todos os arquivos listados antes de modificar
- [ ] BUG-02: criar classe FilasPipeline com nova_sessao()
- [ ] BUG-03: substituir get() por get(timeout=1.0) em loop com verificação de evento
- [ ] BUG-04: checar `is_set()` após wait() e marcar erro se timeout
- [ ] BUG-05: conectar EspolioPage.registrar_asset via CortexPage
- [ ] BUG-06: importar Pango e usar EllipsizeMode.END
- [ ] BUG-07/08: substituir Path.cwd() e Path("logs") por Path(__file__) relativos
- [ ] BUG-09: mover httpx para thread com GLib.idle_add no resultado
- [ ] BUG-11: usar hashlib.md5 em vez de hash()
- [ ] VIOLAÇÃO-02: remover PyGObject do requirements.txt
- [ ] VIOLAÇÃO-04: prefixar comandos Justfile com .venv/bin/
- [ ] Criar testes de threading para Orchestrator
- [ ] `just ci-local` verde com novos testes
- [ ] Commit + push + fechar issue #8

---

## Critério de Aceite

- Segunda execução de ANALISAR funciona sem deadlock
- EXPURGAR VRAM encerra Orchestrator em menos de 3 segundos
- Timeout no Protocolo marca URL como "erro" (não "concluída")
- Espólio mostra contadores corretos após análise
- EXPORTAR CSV exporta assets reais
- `just ci-local` verde com 97 testes
