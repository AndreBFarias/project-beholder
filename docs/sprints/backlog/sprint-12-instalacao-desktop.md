# Sprint 12 — Instalação, .desktop e Download do Moondream

**Issue:** #7
**Status:** Completa
**Prioridade:** Alta

---

## Contexto

O `install.sh` tem 3 problemas críticos:
1. Cria venv sem `--system-site-packages` — GTK4 não funciona (BUG-01)
2. Não cria o arquivo `.desktop` — app não aparece no menu/dock
3. Acentuação incorreta em 3 mensagens

O `run.sh` não verifica nem baixa o modelo Moondream. O `OllamaLifecycle` trava no download sem timeout.

---

## Arquivos a Modificar

| Arquivo | Mudança |
|---------|---------|
| `install.sh` | `--system-site-packages` + criar `.desktop` + corrigir acentuação |
| `requirements.txt` | Remover `PyGObject>=3.48,<3.50` |
| `teardown.sh` | Corrigir acentuação linha 60 |
| `run.sh` | Adicionar função `verificar_modelo_ollama()` |
| `src/ai_vision/ollama_lifecycle.py` | subprocess.Popen com streaming + timeout 600s |

---

## Checklist de Execução

- [ ] Ler install.sh completo antes de modificar
- [ ] Adicionar `--system-site-packages` na linha 88 do install.sh
- [ ] Remover PyGObject do requirements.txt
- [ ] Adicionar bloco `.desktop` no passo 4 do install.sh
- [ ] Corrigir 3 mensagens de acentuação no install.sh
- [ ] Corrigir teardown.sh linha 60
- [ ] Adicionar `verificar_modelo_ollama()` no run.sh
- [ ] Corrigir subprocess no OllamaLifecycle (Popen + for linha in proc.stdout)
- [ ] Testar: `./install.sh` → `.desktop` criado → app no menu
- [ ] Testar: ANALISAR no Córtex → log de download ao vivo sem travar
- [ ] `just ci-local` verde
- [ ] Commit + push + fechar issue #7

---

## Critério de Aceite

- `./install.sh` executa sem erro
- `com.beholder.app.desktop` existe em `~/.local/share/applications/`
- Ícone `com.beholder.app.png` existe em `~/.local/share/icons/hicolor/512x512/apps/`
- App aparece no launcher do GNOME
- `./run.sh` baixa Moondream se ausente (com `bin/ollama` presente)
- ANALISAR mostra progresso do download no Log IA
- 97 testes passando
