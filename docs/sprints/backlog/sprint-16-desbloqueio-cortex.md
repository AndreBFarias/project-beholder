# Sprint 16 — Desbloqueio do Córtex

**Status:** Completa
**Prioridade:** Crítica
**Objetivo:** Fazer o Córtex efetivamente iniciar o Ollama, analisar imagens e permitir reanálise sem re-download.

---

## Contexto

Auditoria revelou dois bugs críticos no pipeline Córtex:

1. **Race condition**: `iniciar_pipeline_automatico()` sobe Ollama em thread separada enquanto o Scraper já começa a empurrar assets. Se o Scraper termina e envia SENTINEL antes do Orchestrator iniciar, a Thread B consome SENTINEL na primeira iteração e encerra sem analisar nada.
2. **Sem modo offline**: Orchestrator só lê `filas.scraper`. Fora de uma sessão de scraping a fila fica vazia. Por isso o usuário precisa "baixar de novo" para reanalisar.

Impacto para o usuário: imagens baixam mas nunca viram CSV/ZIP; reanálise exige rescraping.

---

## Bugs Críticos

| ID  | Arquivo | Linhas | Problema |
|-----|---------|--------|----------|
| C-1 | `src/gui/pages/busca.py` | 167-170 | Scraper iniciado antes do Orchestrator estar pronto |
| C-1 | `src/gui/pages/cortex.py` | 128-146 | Orchestrator só inicia após `_cb_ollama_pronto` |
| C-2 | `src/gui/pages/cortex.py` | (ausente) | Sem botão "ANALISAR PASTA" |
| B-1 | `src/ai_vision/orchestrator.py` | 113-119 | Silent failure quando fila só tem SENTINEL |

---

## Tarefas

- [ ] Iniciar Orchestrator em estado pausado ANTES do Scraper em `_on_iniciar`
- [ ] Retomar Orchestrator apenas em `_cb_ollama_pronto`; cancelar em `_cb_ollama_erro`
- [ ] Adicionar método `Orchestrator.analisar_pasta_local(diretorio, sufixos)` que varre diretório, cria `AssetBruto(origem="local")`, injeta em `filas.scraper`, acrescenta SENTINEL e inicia thread
- [ ] Novo botão "ANALISAR PASTA" em `src/gui/pages/cortex.py`
- [ ] Log de aviso em `Orchestrator._executar()` quando total de assets consumidos for 0 (fila estava vazia ou só tinha SENTINEL)
- [ ] Teste de integração `tests/integration/test_cortex_reanalise.py`
- [ ] `just ci-local` verde

---

## Arquivos a Modificar

- `src/gui/pages/busca.py` (sequenciamento do pipeline)
- `src/gui/pages/cortex.py` (novo botão, ajuste em `iniciar_pipeline_automatico`)
- `src/ai_vision/orchestrator.py` (novo método `analisar_pasta_local`, aviso de fila vazia)
- `tests/integration/test_cortex_reanalise.py` (novo)

---

## Critério de Aceite

- Busca → assets são efetivamente analisados (comprovado por assets em `filas.processada` após sessão).
- Botão "ANALISAR PASTA" em sessão limpa reanalisa imagens do `diretorio_data` sem rescraping.
- Se fila estiver vazia, Córtex exibe "[AVISO] Nenhum asset para analisar" em vez de encerrar silenciosamente.
- 1 teste de integração novo verde.

---

*"A razão é, e deve ser apenas, escrava das paixões." — David Hume*
