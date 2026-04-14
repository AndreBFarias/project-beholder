# CLAUDE.md — Project Beholder
Leitura obrigatória antes de qualquer sprint.

## Regras Invioláveis

### Acentuação PT-BR
OBRIGATÓRIA em todos os commits, código, docs, variáveis em português.
Nunca: "funcao", "configuracao", "execucao". Sempre: "função", "configuração", "execução".

### Anonimato
PROIBIDO mencionar nomes de IAs em commits, código ou docs.
Permitido: variáveis técnicas (OLLAMA_PORT, modelo, provider).

### Zero Emojis
Proibido em código, commits, docs e logs.

### Arquivo máximo: 800 linhas
Exceções: config, testes, registries.

### Threading GTK4 (ADR-01)
Threads NUNCA tocam widgets diretamente.
SEMPRE usar GLib.idle_add(callback, dados) para atualizar UI de threads.

### Ollama Efêmero (ADR-03)
Ollama SEMPRE roda em ./bin/ollama na porta 11435.
teardown.sh DEVE matar pelo PID exato + limpar OLLAMA_TMPDIR.
NUNCA usar pkill -f ollama — mata instâncias do sistema.

### Config Centralizada (ADR-02)
src/core/config/defaults.py é a ÚNICA fonte de verdade para defaults.
Nunca hardcode valores de configuração fora desse arquivo.

### Pipeline Bridges (ADR-01)
Toda comunicação com Ollama passa por src/ai_vision/orchestrator.py.
Nunca chame a API do Ollama diretamente de fora do orchestrator.

## Workflow Obrigatório
1. Ler CLAUDE.md + GSD.md antes de começar
2. Implementar mantendo compatibilidade
3. Testar incrementalmente
4. just ci-local antes de commitar
5. Commit em PT-BR sem mencionar IA

## Validação da UI
"Se não testou com python main.py, não está testado."
Screenshots da UI antes e depois de mudanças visuais.

## Checklist Pré-Commit
- [ ] Testes passando (just ci-local)
- [ ] Zero emojis no código
- [ ] Zero menções a IA
- [ ] Acentuação PT-BR correta
- [ ] GLib.idle_add em todas as atualizações de UI de threads
- [ ] Nenhum valor hardcoded fora de defaults.py
