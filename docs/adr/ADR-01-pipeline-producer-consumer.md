# ADR-01: Pipeline Produtor-Consumidor

**Status:** ACEITA — 2026-04-13

## Contexto

O Beholder precisa executar scraping, análise IA e exportação concorrentemente sem travar a UI GTK4. O scraper pode ser mais rápido ou mais lento que a IA, dependendo do site alvo e da GPU disponível.

## Decisão

Três threads independentes comunicando via `threading.Queue` com limite de tamanho (backpressure):

```
Thread A (Scraper/Produtor)
  → Fila A (maxsize=50) — assets brutos
    → Thread B (AI Worker/Consumidor+Produtor)
      → Fila B (maxsize=50) — assets processados
        → Thread C (Exporter/Consumidor)
```

Toda atualização de UI via `GLib.idle_add(callback, dados)`. Threads nunca tocam widgets diretamente.

## Alternativas Consideradas

- **Pipeline sequencial:** mais simples, mas UI trava entre etapas sem threading cuidadoso
- **Event bus GTK signals:** mais desacoplado, mas complexidade desnecessária para escopo atual
- **asyncio:** incompatível com Playwright sync_api e GLib main loop

## Consequências

- Scraper não espera IA terminar — paralelismo real
- UI nunca trava — GLib.idle_add garante updates no main loop
- Filas com maxsize=50 evitam consumo ilimitado de memória
- Checkpoints serializam estado das filas para retomada

## Enforcement

Qualquer chamada direta a widget GTK fora da thread principal é violação desta ADR.
Grep: `grep -rn "\.set_text\|\.set_fraction\|\.append" src/ --include="*.py"` — resultado fora de `main_window.py` ou `widgets.py` exige justificativa.
