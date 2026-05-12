# Sprint 19 — Protocolo Multi-Site

**Status:** Completa (decisões confirmadas: 4 sites, layout híbrido, sequencial)
**Prioridade:** Média
**Objetivo:** Permitir que o protocolo varra X sites com estratégias específicas de extração e categorização.

---

## Contexto

Hoje `src/scraper/html_parser.py` é genérico — busca `<img>`, `<link rel="icon">`, `background: url(...)` e SVGs. Não há customização por domínio. Usuário espera rodar o protocolo sobre múltiplos sites, cada um com sua particularidade.

---

## Gap

- Sem registry de estratégias por domínio.
- Prompt Moondream idêntico para todo site.
- Sem campo `site_origem` em `AssetProcessado`.
- ZIP final mistura assets de todos os sites numa mesma pasta.

---

## Tarefas

- [ ] Criar `src/scraper/site_strategies/base.py` com ABC `SiteStrategy` — métodos `extrair_assets(html, url)` e `categoria_sugerida(asset)`
- [ ] `src/scraper/site_strategies/generic.py` — implementação atual encapsulada
- [ ] `src/scraper/site_registry.py` — dispatcher por domínio com fallback `generic`
- [ ] Adicionar campo `site_origem: str` em `AssetProcessado`
- [ ] Refatorar `src/scraper/stealth_spider.py` para usar registry
- [ ] `dataset_writer.py` passa a gerar layout `{site}/{categoria}/` no ZIP (ou `{categoria}/{site}_arquivo`, a definir)
- [ ] Nova seção `DEFAULTS["Protocolo"]["sites"]` — lista configurável
- [ ] Exemplos concretos de `SiteStrategy` para sites prioritários do usuário (Pinterest, Dribbble — a confirmar)
- [ ] Teste de integração que varre 2 domínios e valida segregação no ZIP

---

## Perguntas Pendentes Para o Usuário

1. Quais sites são prioritários para strategies customizadas? (Pinterest, Dribbble, Behance, Freepik?)
2. Estrutura do ZIP preferida?
   - (A) `{site}/{categoria}/arquivo.ext` — prioriza site
   - (B) `{categoria}/{site}_arquivo.ext` — prioriza categoria
3. O protocolo deve rodar sites em paralelo ou sequencial?

---

## Critério de Aceite

- Varrer 2 sites registrados → ZIP final segrega assets por site conforme estrutura escolhida.
- CSV tem coluna `site_origem`.
- Adicionar novo site = criar nova classe de strategy (sem tocar no spider).

---

*"Divide o teu campo em canteiros, pois assim colherás mais." — provérbio camponês*
