# ADR-02: Config Centralizada (GOD MODE)

**Status:** ACEITA — 2026-04-13

## Contexto

Valores de configuração espalhados em múltiplos arquivos criam dessincronização (meta-regra anti-regressão N-para-N do projeto). Um valor de timeout em 3 lugares diferentes é uma bomba-relógio.

## Decisão

`src/core/config/defaults.py` é a ÚNICA fonte de verdade para todos os valores default.

### Hierarquia de resolução

1. `defaults.py` — constantes puras (sem lógica, sem imports do projeto)
2. `~/.config/beholder/config.ini` — overrides persistidos do usuário (XDG standard)
3. `src/core/config/config.py` — loader com fallback transparente para defaults

### Regras

- Nenhum valor numérico ou string de configuração hardcoded fora de `defaults.py`
- `.env` contém APENAS secrets (OLLAMA_HOST, API keys futuras)
- `config.ini` nunca é commitado (está no `.gitignore`)

## Alternativas Consideradas

- **TOML/YAML:** mais expressivo mas dependência extra desnecessária
- **Variáveis de ambiente para tudo:** dificulta persistência entre sessões via UI

## Consequências

- Mudança de default em um lugar se propaga automaticamente
- Grimório UI pode sobrescrever qualquer valor via `Config.save()`
- `just doctor` pode verificar integridade do config em <1s

## Enforcement

```bash
grep -rn "timeout.*=.*[0-9]" src/ --include="*.py" | grep -v defaults.py | grep -v test
```
Qualquer hit nesse grep fora de defaults.py é violação desta ADR.
