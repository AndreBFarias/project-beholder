# Sprint 18 — Config Dinâmica (ADR-02)

**Status:** Completa
**Prioridade:** Média
**Objetivo:** Mudanças em Grimório devem propagar em runtime sem reiniciar a aplicação.

---

## Contexto

ADR-02 define `src/core/config/defaults.py` como fonte única de verdade. Porém vários módulos leem `DEFAULTS[...]` em escopo de módulo (import time) — mudanças feitas pelo usuário em Grimório são ignoradas até reiniciar.

---

## Bugs (Médios)

| ID  | Arquivo | Linhas | Problema |
|-----|---------|--------|----------|
| M-1 | `src/ai_vision/moondream_prompt.py` | 20-22 | `_cfg = DEFAULTS["IA"]` no import |
| M-2 | `src/ai_vision/ollama_lifecycle.py` | 28-29 | `PORTA_OLLAMA` no import |
| M-3 | `src/gui/pages/espolio.py` | 29-30 | `_DIR_OUTPUT`/`_DIR_DATA` no import |
| M-4 | `src/scraper/stealth_spider.py` | 96-101 | Valores congelados em `__init__` |
| M-5 | `src/ai_vision/orchestrator.py` | 56 | `_kmeans_cores` em `__init__` |
| M-6 | `src/gui/pages/protocolo.py` | 333 | Timeout 300s hardcoded |
| M-7 | `src/gui/pages/grimorio.py` | 93-149 | Placeholders hardcoded em UI |
| B-3 | `src/exporter/dataset_writer.py` | 17 | `_COLUNAS` estático |

---

## Regra

Nenhum módulo deve ler `DEFAULTS[...]` em escopo de módulo. Toda leitura dentro de funções, properties ou no início de métodos onde o valor é efetivamente usado.

Para classes de longa duração (Spider, Orchestrator): recarregar config no início de `iniciar()` ou em properties com getter.

---

## Tarefas

- [ ] Refatorar cada módulo listado acima para ler DEFAULTS dinamicamente
- [ ] Garantir que Grimório persiste alterações (já feito) E dispare reload (verificar)
- [ ] Teste `tests/integration/test_config_propagation.py` que altera `DEFAULTS` em runtime e valida propagação
- [ ] Documentar a regra em CLAUDE.md (seção "Config Centralizada")

---

## Critério de Aceite

- Alterar `modelo_tier` em Grimório durante execução afeta próxima análise sem reiniciar.
- Alterar `diretorio_output` em Grimório afeta próximo export do Espólio.
- Teste de propagação verde.

---

*"Não há lei sem constância." — Rui Barbosa*
