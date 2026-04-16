# Histórico de Mudanças

Todas as alterações relevantes do projeto estão documentadas aqui.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [0.2.0] - 2026-04-15

### Corrigido
- Pipeline automatico: Busca aciona Cortex (Ollama + Orchestrator) sem navegacao manual
- Travamento com 50+ imagens: filas com timeout e tratamento de backpressure
- Playwright: pre-flight no run.sh + fallback para requests quando browsers ausentes
- Ollama: verificacao de permissao, porta ocupada e returncode na inicializacao
- Icone desktop: multi-resolucao, StartupWMClass, GLib.set_prgname para WM_CLASS
- URL auto-prepend https:// quando usuario omite protocolo

### Melhorado
- Prompt de analise IA: formato chave-valor simples com parser multi-formato e retry
- Validacao e normalizacao de respostas do modelo (aceita type/tipo, description/descricao)
- install.sh gera index.theme e atualiza gtk-update-icon-cache
- Mensagens de erro mais claras no ciclo de vida do Ollama

---

## [0.1.1] - 2026-04-15

### Adicionado
- Código de Conduta (Contributor Covenant v2.1)
- Política de Segurança (SECURITY.md)
- Guia de contribuição (CONTRIBUTING.md)
- Template de feature request para GitHub
- Template de PR para GitHub
- .mailmap para unificação de identidade git
- Badge CI no README

### Corrigido
- pyproject.toml modernizado com authors, keywords, classifiers e URLs
- Acentuação corrigida no README ("Descricao" -> "Descrição")

---

## [0.1.0] - 2026-04-14

### Adicionado
- Motor de scraping com stealth spider (Selenium + requests fallback)
- Análise visual via Ollama com Moondream (modelos low/medium/high)
- Interface GTK4/Libadwaita com 4 módulos (Busca, Cortex, Espólio, Protocolo)
- Pipeline de orquestração com checkpoint e retomada
- Exportação estruturada (.csv + .zip)
- Sistema de tiers de modelos de visão (low/medium/high)
- Install.sh com download automático do Ollama
- CI com 4 estágios (lint, smoke, unit, anonimato)
- Testes smoke e unitários (14 testes)
- Documentação completa (CLAUDE.md, GSD.md, ADRs)
- Justfile como task runner

---

<!-- "O olho vê apenas o que a mente está preparada para compreender." -- Robertson Davies -->
