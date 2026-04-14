# Project Beholder

Motor autônomo de predação visual para Linux.

## O que é

O Beholder varre a web, captura assets de interface (ícones, vetores, fundos) e os
transmuta via visão computacional (Moondream/Ollama). Gera arquivos `.csv` e `.zip`
estruturados para consumo por outros repositórios.

## Pilares

- **Scraping Evasivo** — bypasses de detecção, modo furtivo via Playwright, delays e
  jitter configuráveis
- **Inteligência Isolada** — Ollama invocado em `./bin/ollama` na porta 11435,
  terminado pelo PID exato após uso; nunca parasita o sistema hospedeiro
- **Análise Agnóstica** — describe, tagueia e extrai paleta primária (K-Means) de cada
  asset capturado

## Módulos

| Módulo | Função |
|--------|--------|
| Busca | Extração de assets por URL |
| Córtex | Visão IA local (Moondream) |
| Espólio | Exportação `.zip` + CSV |
| Protocolo | Execução em lote com checkpoint |
| Grimório | Configurações persistidas |

## Requisitos

- Linux (Ubuntu 22.04+)
- Python 3.11+
- GTK 4 + Libadwaita
- Ollama (`./bin/ollama`) com modelo `moondream`

## Instalação

```bash
./install.sh
```

## Execução

```bash
./run.sh
```

## Desenvolvimento

```bash
just ci-local   # lint + testes
just test       # apenas testes
just lint       # apenas lint
```

## Licença

MIT
