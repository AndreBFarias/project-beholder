<div align="center">

[![opensource](https://badges.frapsoft.com/os/v1/open-source.png?v=103)](#)
[![Licença](https://img.shields.io/badge/licenca-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-green.svg)](https://www.python.org/)
[![GTK](https://img.shields.io/badge/GTK-4.0-green.svg)](https://www.gtk.org/)

<div align="center">
  <h1>Project Beholder</h1>
  <img src="beholder-icon.png" width="120" alt="Logo Project Beholder">
</div>

</div>

---

### Descrição

Motor autônomo de predação visual para Linux. O Beholder varre a web, captura assets de interface (ícones, vetores, fundos, logos) e os analisa via visão computacional com Moondream/Ollama rodando localmente. Gera arquivos `.csv` e `.zip` estruturados prontos para consumo por outros repositórios.

---

### Principais Funcionalidades

| Módulo | Função |
|--------|--------|
| **Busca** | Scraping de assets por URL com modo furtivo (Playwright) |
| **Córtex** | Análise IA local via Moondream — classifica, descreve e tagueia cada asset |
| **Espólio** | Exportação `.zip` estruturado + CSV com metadados |
| **Protocolo** | Execução em lote com checkpoint e retomada de sessão |
| **Grimório** | Configurações persistidas via XDG |

---

### Interface

<div align="center">
<img src="docs/screenshots/busca.png" width="700" alt="Aba Busca — Extração de Assets">
</div>

---

### Instalação

#### Ubuntu/Debian (.deb)

```bash
sudo dpkg -i beholder_VERSION_amd64.deb
sudo apt-get install -f
```

#### Flatpak

```bash
flatpak install beholder.flatpak
flatpak run com.beholder.app
```

#### AppImage

```bash
chmod +x Beholder-VERSION-x86_64.AppImage
./Beholder-VERSION-x86_64.AppImage
```

#### Via Script (Desenvolvimento)

```bash
git clone https://github.com/[REDACTED]/project-beholder.git
cd project-beholder
chmod +x install.sh
./install.sh
```

---

### Requisitos

**Obrigatórios:**
- Linux (Ubuntu 22.04+)
- Python 3.12+
- GTK 4.0 + Libadwaita 1.x
- `python3-gi`, `python3-gi-cairo`, `gir1.2-gtk-4.0`, `gir1.2-adw-1`

**Para análise IA (Córtex):**
- Ollama binary em `./bin/ollama` (baixar em [ollama.com](https://ollama.com))
- Modelo `moondream` (baixado automaticamente pelo `run.sh`)
- GPU recomendada (NVIDIA/AMD) — funciona em CPU também

**Para modo furtivo (Busca):**
- Playwright: instalado automaticamente pelo `install.sh`

---

### Execução

```bash
./run.sh
```

O `run.sh` verifica o venv, baixa o Moondream se ausente, limpa estado residual do Ollama e inicia o app. Ao fechar, libera a VRAM automaticamente.

---

### Desenvolvimento

```bash
just ci-local    # lint + formato + testes (66+ testes)
just test        # apenas testes
just lint        # apenas lint e formato
just fmt         # corrigir formato automaticamente
just run         # iniciar o app
```

---

### Estrutura do Projeto

```
project-beholder/
  main.py                        # Entry point
  install.sh                     # Instala dependências + .desktop + hooks
  run.sh                         # Inicia o app com ciclo de vida completo
  teardown.sh                    # Limpeza forçada (emergência)
  src/
    gui/
      pages/                     # 5 módulos: busca, cortex, espolio, protocolo, grimório
      widgets.py                 # LogTerminal, StatusBar
      theme.py                   # CSS Dracula
      sidebar.py                 # Navegação lateral
      main_window.py             # Janela principal GTK4
    scraper/
      stealth_spider.py          # Thread A — scraping + Playwright
      html_parser.py             # Extração de assets do HTML
    ai_vision/
      orchestrator.py            # Thread B — bridge Ollama (ADR-01)
      ollama_lifecycle.py        # Gerenciamento de VRAM (ADR-03)
      moondream_prompt.py        # Prompt estruturado JSON
    transformer/
      icon_alchemist.py          # K-Means + canvas circular
    exporter/
      packer.py                  # Thread C — .zip
      dataset_writer.py          # CSV
    core/
      asset_queue.py             # Filas inter-thread com backpressure
      checkpoint.py              # Serialização de estado
      config/
        defaults.py              # Fonte única de verdade (ADR-02)
        config.py                # Persistência XDG
  tests/
    unit/                        # Testes unitários (pytest)
    smoke/                       # Smoke tests de importação
  docs/
    adr/                         # Decisões de arquitetura
    sprints/                     # Documentação das sprints
  packaging/                     # Scripts de build (Sprint 14)
  .github/workflows/             # CI/CD (Sprint 14)
```

---

### ADRs (Decisões de Arquitetura)

| ADR | Regra |
|-----|-------|
| ADR-01 | Threads NUNCA tocam widgets — obrigatório `GLib.idle_add()` |
| ADR-02 | `defaults.py` é a única fonte de verdade para configurações |
| ADR-03 | Ollama sempre em `./bin/ollama` porta 11435 — kill pelo PID exato |

---

### Documentação

- [GSD.md](GSD.md) — Armadilhas críticas e estado das sprints
- [CLAUDE.md](CLAUDE.md) — Regras de desenvolvimento
- [docs/adr/](docs/adr/) — Decisões de arquitetura
- [docs/sprints/](docs/sprints/) — Histórico e backlog de sprints

---

### Licença

MIT — Veja [LICENSE](LICENSE) para detalhes.
