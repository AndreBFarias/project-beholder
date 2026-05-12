# Sprint 21 — Recuperação de site_origem em Reanálise

**Status:** Completa
**Prioridade:** Média
**Objetivo:** Ao usar ANALISAR PASTA, preservar o `site_origem` original dos assets em vez de cair em `generic`.

---

## Contexto

Sprint 16 entregou "ANALISAR PASTA" (reanálise sem rescraping). Sprint 19 adicionou `site_origem`. Mas quando imagens já baixadas são reprocessadas localmente, perdemos a informação de origem — tudo cai em `generic` porque o orchestrator resolvia via `resolver_strategy("local")`.

---

## Mudança

### Novo campo `AssetBruto.site_origem_hint`

Campo opcional que permite ao chamador forçar o `site_origem` sem depender de `resolver_strategy`. O orchestrator usa o hint quando presente; senão, fallback para a resolução por URL.

### Prioridade de resolução em `analisar_pasta_local`

1. **CSV antigo** — `_construir_mapa_sites` procura CSVs em:
   - `{diretorio}/**/*.csv` (exportações manuais)
   - `{PROJECT_ROOT}/output/*.csv` (cópias preservadas pelo Packer)

   Mapeia `caminho_local` → `site_origem`, ignorando linhas `generic`.

2. **Nome da subpasta** — se arquivo está em `pinterest/foo.png`, `site_origem_hint = "pinterest"`.

3. **Sem hint** — fallback para `resolver_strategy("local").nome` = `"generic"`.

### Packer preserva CSV fora do ZIP

Ao gerar pacote, copia `staging/metadata.csv` → `{output}/metadata_{timestamp}.csv`. Assim reanálises futuras encontram o mapa sem precisar descompactar nada.

---

## Arquivos Modificados

- `src/core/asset_queue.py` — novo campo `site_origem_hint` em `AssetBruto`
- `src/ai_vision/orchestrator.py` — respeita hint; novo método `_construir_mapa_sites`; `analisar_pasta_local` aplica as 3 prioridades
- `src/exporter/packer.py` — preserva CSV externo em `output/metadata_{timestamp}.csv`

---

## Arquivos Criados

- `tests/integration/test_recuperacao_site.py` (9 testes)

---

## Critério de Aceite

- [x] `AssetBruto.site_origem_hint` preservado até `AssetProcessado.site_origem`
- [x] CSV antigo alimenta o mapa
- [x] Subpasta funciona como fallback
- [x] Prioridade CSV > subpasta verificada por teste
- [x] Packer preserva CSV externo
- [x] 156/156 testes verdes

---

*"Lembrar é outra forma de viver." — Clarice Lispector*
