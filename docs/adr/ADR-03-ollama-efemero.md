# ADR-03: Ollama Efêmero

**Status:** ACEITA — 2026-04-13

## Contexto

Manter o Ollama rodando permanentemente consome VRAM mesmo quando a análise não está ativa. Em máquinas com GPU limitada, isso é inaceitável. Além disso, usar o binário do sistema cria acoplamento com a instalação do usuário e risco de conflito de portas.

## Decisão

O Ollama **nunca roda permanentemente**. É invocado apenas quando a análise de IA é iniciada e encerrado imediatamente ao terminar ou ao usuário acionar EXPURGAR VRAM.

### Regras obrigatórias

1. **Binário isolado:** `./bin/ollama` — nunca o `ollama` do sistema
2. **Porta exclusiva:** `11435` — evita conflito com instâncias do sistema na porta padrão `11434`
3. **Encerramento cirúrgico:** `os.kill(PID_EXATO, signal.SIGTERM)` seguido de `processo.wait(timeout=5)`
   - **NUNCA** `pkill -f ollama` — mataria outras instâncias do sistema
   - Fallback: `os.kill(PID_EXATO, signal.SIGKILL)` se SIGTERM não encerrar em 5s
4. **Limpeza de VRAM:** `shutil.rmtree(OLLAMA_TMPDIR, ignore_errors=True)` após encerramento
5. **Diretório temporário isolado:** `OLLAMA_TMPDIR=/tmp/ollama_beholder` — nunca o tmp padrão do sistema

### Variáveis de ambiente obrigatórias

```python
env["OLLAMA_HOST"] = "127.0.0.1:11435"
env["OLLAMA_TMPDIR"] = "/tmp/ollama_beholder"
```

### Ciclo de vida

```
1. Usuário clica ANALISAR
   → OllamaLifecycle.subir()
   → subprocess.Popen([./bin/ollama, serve], env=env)
   → aguardar porta ficar acessível (ping com timeout)
   → registrar PID

2. Thread B processa fila de assets
   → chamadas HTTP para 127.0.0.1:11435

3. Usuário clica EXPURGAR VRAM ou fila esgota
   → OllamaLifecycle.expurgar()
   → os.kill(pid, SIGTERM) + wait(5s)
   → shutil.rmtree(OLLAMA_TMPDIR)
   → UI atualiza VRAM: 0 GB
```

## Por que porta 11435?

A porta padrão do Ollama é `11434`. Usar `11435` garante que:
- O Beholder nunca interfere com o Ollama do sistema do usuário
- Múltiplas instâncias (Beholder + sistema) coexistem sem conflito
- `teardown.sh` pode ser executado com segurança sem afetar outros processos

## Alternativas Consideradas

- **Ollama do sistema:** cria dependência de instalação externa, risco de conflito de versão, VRAM compartilhada
- **Docker:** overhead desnecessário, complexidade de instalação, latência de rede adicional
- **pkill -f ollama:** mata qualquer processo com "ollama" no nome — perigoso em ambientes com Ollama do sistema

## Consequências

- VRAM liberada completamente ao encerrar análise
- Zero interferência com outras ferramentas do usuário
- `teardown.sh` na raiz do projeto como mecanismo de emergência
- `just doctor` verifica presença de `./bin/ollama` e reporta ausência

## Enforcement

```bash
# Verificar se há chamadas à API do Ollama fora do orchestrator
grep -rn "localhost:11434\|127.0.0.1:11434\|ollama.*11434" src/ --include="*.py"
# Qualquer hit é violação desta ADR — a porta correta é 11435

# Verificar se há pkill -f ollama
grep -rn "pkill.*-f.*ollama\|killall.*ollama" src/ scripts/ --include="*.py" --include="*.sh"
# Qualquer hit é violação desta ADR
```
