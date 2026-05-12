# Sprint 17 — Espólio em PT-BR

**Status:** Completa
**Prioridade:** Crítica
**Objetivo:** CSV e estrutura de pastas do ZIP em português, conforme CLAUDE.md.

---

## Contexto

CLAUDE.md exige acentuação PT-BR obrigatória. Implementação atual viola:

- Prompt Moondream em inglês → descrições em `AssetProcessado.descricao` chegam em inglês.
- Mapeamento de pastas hardcoded em inglês (`icons/`, `backgrounds/`) em `dataset_writer.py`.

Usuário espera: `ícones/`, `fundos/`, `outros/` no ZIP e descrições em PT-BR no CSV.

---

## Bugs

| ID  | Arquivo | Linhas | Problema |
|-----|---------|--------|----------|
| C-3 | `src/ai_vision/moondream_prompt.py` | 36-40 | Prompt em inglês |
| C-4 | `src/exporter/dataset_writer.py` | 20-29 | Nomes de pasta em inglês |
| B-4 | `tests/unit/test_exporter.py` | 147-164 | Teste valida inglês |

---

## Tarefas

- [ ] Mover `_MAPA_TIPO` para `src/core/config/defaults.py` em `DEFAULTS["Espolio"]["mapa_pastas"]` com nomes PT-BR
- [ ] `dataset_writer.subpasta_tipo()` passa a ler dinamicamente de `DEFAULTS` (não no escopo de módulo)
- [ ] Atualizar `PROMPT_CLASSIFICACAO` em `moondream_prompt.py` para instruir resposta em PT-BR
- [ ] Reforçar parser `_parse_chave_valor()` para aceitar tanto "description:" quanto "descrição:"
- [ ] Pipeline de tradução fallback: se resposta voltar em inglês, segunda chamada ao modelo pedindo tradução
- [ ] Atualizar `tests/unit/test_exporter.py` para esperar `"ícones"`, `"fundos"`, `"outros"`
- [ ] Novo teste `tests/unit/test_moondream_ptbr.py` validando prompt PT-BR e parser bilíngue
- [ ] `just ci-local` verde

---

## Arquivos a Modificar

- `src/core/config/defaults.py`
- `src/exporter/dataset_writer.py`
- `src/ai_vision/moondream_prompt.py`
- `tests/unit/test_exporter.py`
- `tests/unit/test_moondream_ptbr.py` (novo)

---

## Critério de Aceite

- ZIP exportado contém pastas `ícones/`, `fundos/`, `outros/`.
- Coluna `descricao` do CSV é majoritariamente PT-BR em amostra real.
- Testes de exporter passam com nomes PT-BR.

---

*"Escreva em sua própria língua, e as coisas soarão como devem soar." — Euclides da Cunha*
