# Sprint 11 — UI: Espólio Redesign + Textos + Status Bar

**Issue:** #6
**Status:** Backlog
**Prioridade:** Alta

---

## Contexto

Sprint 10 entregou ajustes pontuais. Ainda restam problemas visuais visíveis:
- Aba Espólio com grid de texto plano sem hierarquia
- Labels de Gtk.Frame em minúsculo em várias abas
- Status bar com fonte 13px (pequena demais) e texto não capitalizado

---

## Arquivos a Modificar

| Arquivo | Mudança |
|---------|---------|
| `src/gui/pages/espolio.py` | Substituir Gtk.Grid por 5 mini-cards horizontais |
| `src/gui/theme.py` | `.status-bar font-size: 13px → 15px` |
| `src/gui/widgets.py` | Capitalizar labels da StatusBar |
| `src/gui/pages/busca.py` | Verificar labels de frame |
| `src/gui/pages/cortex.py` | Verificar labels de frame |
| `src/gui/pages/protocolo.py` | Verificar labels de frame |
| `src/gui/pages/grimorio.py` | Verificar labels de frame |

---

## Checklist de Execução

- [ ] Ler todos os 7 arquivos antes de modificar qualquer um
- [ ] Substituir Gtk.Grid no Espólio por Box com 5 Gtk.Frame cards
- [ ] Manter chaves de `_labels_valores` idênticas (não quebrar `_atualizar_contadores`)
- [ ] Corrigir todos os `Gtk.Frame(label=...)` para capitalização correta
- [ ] Alterar font-size do status-bar em theme.py
- [ ] Capitalizar labels em widgets.py StatusBar
- [ ] `just ci-local` verde
- [ ] Screenshot das 5 abas
- [ ] Commit com mensagem descritiva em PT-BR
- [ ] Push e fechar issue #6

---

## Critério de Aceite

- `python main.py` abre sem erro
- Espólio mostra 5 cards horizontais com número grande + label pequeno
- Nenhum label de Gtk.Frame em minúsculo nas 5 abas
- Status bar com fonte maior e texto capitalizado
- 66+ testes passando
