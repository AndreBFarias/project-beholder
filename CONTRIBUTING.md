# Como Contribuir

Obrigado pelo interesse em contribuir com o Project Beholder!

## Índice

- [Código de Conduta](#código-de-conduta)
- [Configurando o Ambiente](#configurando-o-ambiente)
- [Padrões de Código](#padrões-de-código)
- [Regras do Projeto](#regras-do-projeto)
- [Submetendo Mudanças](#submetendo-mudanças)

## Código de Conduta

Este projeto adota o [Contributor Covenant v2.1](CODE_OF_CONDUCT.md). Ao participar, você concorda em respeitá-lo.

## Configurando o Ambiente

### Requisitos

- Python 3.10+
- GTK4 + Libadwaita (`gir1.2-gtk-4.0`, `gir1.2-adw-1`)
- Ollama (gerenciado pelo projeto, porta 11435)
- Just (task runner): `cargo install just`

### Instalação

```bash
git clone <repo>
cd Project_Beholder
bash install.sh
just ci-local
```

## Padrões de Código

### Lint e Formatação

```bash
just ci-local    # roda lint + smoke + unit + anonimato
ruff check src/ tests/
ruff format src/ tests/
```

### Threading GTK4 (ADR-01)

Threads **nunca** tocam widgets diretamente. Sempre use `GLib.idle_add(callback, dados)` para atualizar UI de threads.

### Ollama Efêmero (ADR-03)

Ollama roda em `./bin/ollama` na porta 11435. Toda comunicação passa por `src/ai_vision/orchestrator.py`. Nunca chame a API do Ollama diretamente.

### Commits

Mensagens em português, formato convencional:

```
tipo: descrição imperativa em PT-BR

# Tipos: feat, fix, refactor, docs, test, perf, chore
```

## Regras do Projeto

- **Zero emojis** em código, commits e documentação
- **Acentuação correta** obrigatória em todo texto PT-BR
- **Nenhuma menção a ferramentas de IA** em commits ou código
- **Type hints** em todas as funções novas
- **800 linhas** máximo por arquivo (exceto config e testes)
- **Config centralizada** em `src/core/config/defaults.py` (ADR-02)

## Submetendo Mudanças

### Antes de Abrir o PR

- [ ] `just ci-local` passando (4/4 estágios)
- [ ] Zero emojis no código e commits
- [ ] Acentuação correta em textos PT-BR
- [ ] `GLib.idle_add` em todas as atualizações de UI de threads
- [ ] Nenhum valor hardcoded fora de `defaults.py`
- [ ] Testado com `python main.py` (se mudança visual)

### Processo de Review

1. Um mantenedor vai revisar seu PR
2. Pode haver solicitações de mudanças
3. Após aprovação, o PR será mergeado
