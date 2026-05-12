# Sprint 20 — Riqueza da Descrição e Tags

**Status:** Completa
**Prioridade:** Média-Alta
**Objetivo:** Enriquecer as descrições e tags geradas pela IA e expô-las na UI do Espólio.

---

## Contexto

Após Sprints 16-19, o pipeline funcionava mas o conteúdo das análises ficava raso:
- Prompt pedia apenas "uma frase curta" e 3 tags.
- Parser truncava descrição em 100 chars e tags em 5.
- `num_predict: 150` cortava respostas antes do modelo completar.
- UI do Espólio não mostrava descrição nem tags — só contadores.

Resultado prático: CSV com dados pobres e sem visibilidade no Espólio antes de exportar.

---

## Mudanças

### Prompt mais rico

`src/ai_vision/moondream_prompt.py:PROMPT_CLASSIFICACAO` agora pede:
- 2 frases na descrição (conteúdo visual + estilo/uso provável)
- 6+ tags em PT-BR cobrindo: tema, estilo, cores dominantes, elementos gráficos, uso
- Contexto explícito (é um "catálogo visual em PT-BR")

### Limites configuráveis em DEFAULTS

Novos campos em `DEFAULTS["IA"]`:
- `num_predict: 400` (antes era hardcoded 150)
- `max_descricao_chars: 300` (antes: 100)
- `max_tags: 10` (antes: 5)
- `min_tags_esperadas: 5` (threshold para retry com resposta pobre)

### Parser mais tolerante

- Descrição pode atravessar múltiplas linhas até encontrar `tags:` ou fim do texto.
- Tags duplicadas (case-insensitive) são removidas preservando ordem.
- Limites lidos de DEFAULTS dinamicamente (ADR-02).
- Retry inteligente: se descrição < 30 chars OU tags < 5, tenta de novo com temperatura 0.5.

### UI Espólio com lista visual

Nova `ListBox` "Assets Processados" entre contadores e log. Cada card mostra:
- Badge `[TIPO]` + `@site_origem` + nome do arquivo
- Descrição completa com word wrap
- Tags como chips (`FlowBox`)
- Placeholder quando vazio; restaurado em LIMPAR SESSÃO

---

## Arquivos Modificados

- `src/core/config/defaults.py` (4 novos campos em IA)
- `src/ai_vision/moondream_prompt.py` (prompt, parser multilinha, retry inteligente)
- `src/gui/pages/espolio.py` (ListBox de assets + helper `_criar_card_asset_espolio`)

---

## Arquivos Criados

- `tests/unit/test_moondream_riqueza.py` (10 testes)
- `tests/integration/test_espolio_ui.py` (4 testes)

---

## Critério de Aceite

- [x] Prompt pede 2 frases e 6+ tags
- [x] Parser aceita descrição multilinha
- [x] Limites lidos de DEFAULTS (ADR-02)
- [x] UI do Espólio mostra cada asset com descrição completa e tags
- [x] LIMPAR SESSÃO restaura placeholder
- [x] 147/147 testes verdes

---

*"Descrever é o primeiro ato de compreender." — Antoine de Saint-Exupéry*
