# Sprint 15 — Workflow CI/CD e Pre-commit Hook de Screenshots

**Issue:** #10
**Status:** Backlog
**Prioridade:** Média

---

## Contexto

O Justfile usa binários do sistema em vez do `.venv/`. O pre-commit não tem proteção contra `print()`. Não existe mecanismo automático de screenshot ao modificar a GUI.

---

## Arquivos a Modificar/Criar

| Arquivo | Ação |
|---------|------|
| `Justfile` | Prefixar com `.venv/bin/`; adicionar targets `fmt`, `screenshots` |
| `.pre-commit-config.yaml` | Adicionar hook `no-print-statements` |
| `tools/screenshot_ci.py` | Criar — script de screenshot automático via Xvfb |
| `hooks/pre-commit-assets` | Criar — hook post-commit que gera screenshots |
| `install.sh` | Registrar `hooks/pre-commit-assets` como `.git/hooks/post-commit` |

---

## Checklist de Execução

- [ ] Ler Justfile atual antes de modificar
- [ ] Ler .pre-commit-config.yaml atual
- [ ] Atualizar Justfile: `PYTHON`, `PYTEST`, `RUFF` como variáveis; todos os targets usam `.venv/bin/`
- [ ] Adicionar target `screenshots` no Justfile
- [ ] Adicionar hook `no-print-statements` no .pre-commit-config.yaml
- [ ] Criar `tools/screenshot_ci.py` (ver issue #10 para código)
- [ ] Criar `hooks/pre-commit-assets` (ver issue #10 para código)
- [ ] Adicionar registro do hook post-commit no install.sh
- [ ] Testar: `just ci-local` usa `.venv/bin/`
- [ ] Testar: `pre-commit run --all-files` passa com novo hook
- [ ] Testar: `just screenshots` (com Xvfb disponível)
- [ ] `just ci-local` verde
- [ ] Commit + push + fechar issue #10

---

## Critério de Aceite

- `just ci-local` usa `.venv/bin/ruff` e `.venv/bin/pytest`
- `pre-commit run --all-files` detecta e rejeita `print()` em `src/`
- `tools/screenshot_ci.py` executa sem erro com `DISPLAY=:99`
- Hook `post-commit` instalado automaticamente pelo `install.sh`
- `just screenshots` funciona ou sai com AVISO gracioso
