# Sprint 13 -- Correções Retroativas (Auditoria) -- Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir os 11 bugs e 2 violações identificados na auditoria das Sprints 0-10, tornando o pipeline funcional de ponta a ponta sem deadlocks.

**Architecture:** Pipeline produtor-consumidor com 3 threads (Scraper → Fila → Orchestrator → Fila → Packer). Filas singleton são substituídas por classe gerenciável. Todos os acessos a Queue passam a usar timeout para permitir cancelamento. Comunicação entre módulos UI (Córtex → Espólio) via referência cruzada em main_window.py.

**Tech Stack:** Python 3.12, GTK4/Libadwaita (PyGObject), threading, queue, hashlib, httpx, pytest.

---

## Estrutura de arquivos

| Ação | Arquivo | Responsabilidade |
|------|---------|-----------------|
| Modificar | `src/core/asset_queue.py` | BUG-02+10: FilasPipeline com nova_sessao() |
| Modificar | `src/scraper/stealth_spider.py` | BUG-02: usar filas.scraper + BUG-11: hashlib.md5 |
| Modificar | `src/ai_vision/orchestrator.py` | BUG-02+03: filas.scraper/processada + get(timeout) |
| Modificar | `src/exporter/packer.py` | BUG-02: usar filas.processada |
| Modificar | `src/gui/pages/espolio.py` | BUG-02+05: filas.processada + drenar antes de empacotar |
| Modificar | `src/gui/pages/cortex.py` | BUG-05+06: conectar_espolio + Pango.EllipsizeMode |
| Modificar | `src/gui/main_window.py` | BUG-05: conectar CortexPage → EspolioPage |
| Modificar | `src/gui/pages/protocolo.py` | BUG-04: timeout marca erro |
| Modificar | `src/gui/pages/grimorio.py` | BUG-09: httpx em thread separada |
| Modificar | `src/core/logging_config.py` | BUG-07: Path(__file__) em vez de Path("logs") |
| Modificar | `src/core/checkpoint.py` | BUG-07: Path(__file__) em vez de Path relativo |
| Modificar | `src/ai_vision/ollama_lifecycle.py` | BUG-08: Path(__file__) em vez de Path.cwd() |
| Modificar | `requirements.txt` | VIOLAÇÃO-02: remover PyGObject |
| Modificar | `Justfile` | VIOLAÇÃO-04: prefixar .venv/bin/ |
| Criar | `tests/unit/test_filas_pipeline.py` | Testes da classe FilasPipeline |
| Criar | `tests/unit/test_orchestrator_timeout.py` | Testes de threading com timeout e cancelamento |
| Criar | `tests/unit/test_hash_estavel.py` | Teste de estabilidade do hash de nomes de arquivo |
| Criar | `tests/unit/test_paths.py` | Teste de resolução de caminhos via Path(__file__) |

---

### Task 1: BUG-02 + BUG-10 -- FilasPipeline com nova_sessao()

**Files:**
- Modify: `src/core/asset_queue.py`
- Create: `tests/unit/test_filas_pipeline.py`

- [ ] **Step 1: Escrever teste da classe FilasPipeline**

```python
# tests/unit/test_filas_pipeline.py
"""
Testes da classe FilasPipeline.

Cobrem:
- nova_sessao() cria filas novas e vazias
- Filas respeitam maxsize de DEFAULTS
- SENTINEL funciona como esperado
- nova_sessao() não afeta dados já consumidos
"""

from queue import Full

import pytest

from src.core.asset_queue import SENTINEL, AssetBruto, AssetProcessado, FilasPipeline


def test_filas_iniciam_vazias():
    fp = FilasPipeline()
    assert fp.scraper.empty()
    assert fp.processada.empty()


def test_nova_sessao_cria_filas_novas():
    fp = FilasPipeline()
    scraper_antiga = fp.scraper
    fp.nova_sessao()
    assert fp.scraper is not scraper_antiga


def test_nova_sessao_filas_vazias_apos_uso():
    fp = FilasPipeline()
    fp.scraper.put("item1")
    fp.scraper.put("item2")
    fp.nova_sessao()
    assert fp.scraper.empty()
    assert fp.processada.empty()


def test_filas_respeitam_maxsize():
    fp = FilasPipeline()
    maxsize = fp.scraper.maxsize
    assert maxsize == 50
    for i in range(maxsize):
        fp.scraper.put(f"item_{i}")
    with pytest.raises(Full):
        fp.scraper.put("overflow", timeout=0.1)


def test_sentinel_funciona():
    fp = FilasPipeline()
    fp.scraper.put(SENTINEL)
    item = fp.scraper.get(timeout=1.0)
    assert item is SENTINEL
```

- [ ] **Step 2: Rodar teste e confirmar que falha**

Run: `.venv/bin/pytest tests/unit/test_filas_pipeline.py -v`
Expected: FAIL com `ImportError: cannot import name 'FilasPipeline'`

- [ ] **Step 3: Implementar FilasPipeline em asset_queue.py**

Substituir o conteúdo de `src/core/asset_queue.py` por:

```python
"""
Filas compartilhadas do pipeline produtor-consumidor (ADR-01).

FilasPipeline gerencia as filas do pipeline. Chamar nova_sessao() antes de
iniciar cada pipeline para evitar deadlock por estado residual (BUG-02/BUG-10).

Diagrama:
    Thread A (Scraper) → filas.scraper → Thread B (AI Worker) → filas.processada → Thread C (Exporter)

Regras:
- maxsize=50 em ambas as filas (backpressure para evitar consumo ilimitado de memória)
- SENTINEL = None sinaliza fim da fila para o consumidor encerrar graciosamente
"""

from dataclasses import dataclass, field
from queue import Queue

from src.core.config.defaults import DEFAULTS

SENTINEL = None  # Sinal de fim de fila (put None → consumidor encerra)


@dataclass
class AssetBruto:
    """Asset extraído pelo scraper, ainda sem processamento de IA."""

    url: str
    caminho_local: str
    tipo: str  # "icon" | "image" | "svg" | "background" | "other"
    origem: str  # URL da página onde foi encontrado


@dataclass
class AssetProcessado:
    """Asset após análise de IA e extração de paleta."""

    url_original: str
    caminho_local: str
    tipo: str
    descricao: str
    tags: list[str] = field(default_factory=list)
    paleta_hex: list[str] = field(default_factory=list)
    timestamp: str = ""


class FilasPipeline:
    """Gerencia as filas do pipeline produtor-consumidor.

    Chamar nova_sessao() antes de cada execução do pipeline para
    garantir filas limpas e evitar deadlock por estado residual.
    """

    def __init__(self) -> None:
        self._maxsize_scraper: int = DEFAULTS["Fila"]["maxsize_scraper"]
        self._maxsize_processada: int = DEFAULTS["Fila"]["maxsize_processada"]
        self.nova_sessao()

    def nova_sessao(self) -> None:
        """Cria filas novas e vazias para uma nova sessão do pipeline."""
        self.scraper: Queue = Queue(maxsize=self._maxsize_scraper)
        self.processada: Queue = Queue(maxsize=self._maxsize_processada)


filas = FilasPipeline()
```

- [ ] **Step 4: Rodar testes e confirmar que passam**

Run: `.venv/bin/pytest tests/unit/test_filas_pipeline.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/core/asset_queue.py tests/unit/test_filas_pipeline.py
git commit -m "refactor: substituir filas singleton por FilasPipeline com nova_sessao()"
```

---

### Task 2: BUG-02 continuação -- Atualizar consumidores das filas

**Files:**
- Modify: `src/scraper/stealth_spider.py:32,208-209,222`
- Modify: `src/ai_vision/orchestrator.py:19,111,145,156`
- Modify: `src/exporter/packer.py:22,81`
- Modify: `src/gui/pages/espolio.py:20,189-191`
- Modify: `src/gui/pages/busca.py` (adicionar nova_sessao antes de iniciar)

- [ ] **Step 1: Atualizar stealth_spider.py**

Alterar import (linha 32):
```python
# ANTES:
from src.core.asset_queue import SENTINEL, AssetBruto, fila_scraper

# DEPOIS:
from src.core.asset_queue import SENTINEL, AssetBruto, filas
```

Alterar usos (3 ocorrências):
- Linha 208 `fila_scraper.put(asset)` → `filas.scraper.put(asset)`
- Linha 222 `fila_scraper.put(SENTINEL)` → `filas.scraper.put(SENTINEL)`

- [ ] **Step 2: Atualizar orchestrator.py**

Alterar import (linha 19):
```python
# ANTES:
from src.core.asset_queue import SENTINEL, AssetBruto, AssetProcessado, fila_processada, fila_scraper

# DEPOIS:
from src.core.asset_queue import SENTINEL, AssetBruto, AssetProcessado, filas
```

Alterar usos (3 ocorrências):
- Linha 111 `item = fila_scraper.get()` → `item = filas.scraper.get()` (será refinado na Task 3)
- Linha 145 `fila_processada.put(processado)` → `filas.processada.put(processado)`
- Linha 156 `fila_processada.put(SENTINEL)` → `filas.processada.put(SENTINEL)`

- [ ] **Step 3: Atualizar packer.py**

Alterar import (linha 22):
```python
# ANTES:
from src.core.asset_queue import SENTINEL, AssetProcessado, fila_processada

# DEPOIS:
from src.core.asset_queue import SENTINEL, AssetProcessado, filas
```

Alterar uso (linha 81):
- `item = fila_processada.get()` → `item = filas.processada.get()`

- [ ] **Step 4: Atualizar espolio.py**

Alterar import (linha 20):
```python
# ANTES:
from src.core.asset_queue import AssetProcessado, fila_processada

# DEPOIS:
from src.core.asset_queue import AssetProcessado, filas
```

Alterar _on_gerar (linhas 189-191) para drenar resíduos antes de postar:
```python
def _on_gerar(self, _btn: Gtk.Button) -> None:
    """Inicia Packer (Thread C) para gerar .zip."""
    if self._packer.esta_ativo():
        self._cb_log("[AVISO] Packer já em execução.")
        return
    self._btn_gerar.set_sensitive(False)
    self._cb_log("[INFO] Iniciando empacotamento...")

    if self._assets:
        # Drena resíduos de sessões anteriores da fila processada
        while not filas.processada.empty():
            try:
                filas.processada.get_nowait()
            except Exception:
                break
        for asset in self._assets:
            filas.processada.put(asset)
        filas.processada.put(None)  # SENTINEL
        self._packer.iniciar()
    else:
        self._cb_log("[AVISO] Nenhum asset disponível para empacotar.")
        self._btn_gerar.set_sensitive(True)
```

- [ ] **Step 5: Adicionar nova_sessao() em busca.py antes de iniciar**

Em `src/gui/pages/busca.py`, adicionar import e chamada:

Adicionar import no topo (após os existentes):
```python
from src.core.asset_queue import filas
```

Em `_on_iniciar`, antes de `self._spider.iniciar(...)`:
```python
filas.nova_sessao()
```

- [ ] **Step 6: Rodar testes existentes para verificar que nada quebrou**

Run: `.venv/bin/pytest tests/ -v --timeout=30`
Expected: 87 passed (82 existentes + 5 novos)

- [ ] **Step 7: Commit**

```bash
git add src/scraper/stealth_spider.py src/ai_vision/orchestrator.py src/exporter/packer.py src/gui/pages/espolio.py src/gui/pages/busca.py
git commit -m "refactor: migrar consumidores de fila_scraper/fila_processada para filas.*"
```

---

### Task 3: BUG-03 -- Orchestrator get() com timeout

**Files:**
- Modify: `src/ai_vision/orchestrator.py:1,99-111`
- Create: `tests/unit/test_orchestrator_timeout.py`

- [ ] **Step 1: Escrever teste de cancelamento do Orchestrator**

```python
# tests/unit/test_orchestrator_timeout.py
"""
Testes de threading do Orchestrator.

Cobrem:
- Thread encerra em < 3s quando _evento_parar é setado com fila vazia
- Thread consome SENTINEL e encerra normalmente
- Thread processa item e chama callback
"""

import threading
import unittest.mock as mock

import pytest

from src.core.asset_queue import SENTINEL, AssetBruto, FilasPipeline


@pytest.fixture
def filas_teste():
    return FilasPipeline()


@pytest.fixture
def mock_glib(monkeypatch):
    """Mock GLib.idle_add para chamar a função diretamente."""
    mock_idle_add = mock.MagicMock(side_effect=lambda fn, *args: fn(*args))
    monkeypatch.setattr("src.ai_vision.orchestrator.GLib.idle_add", mock_idle_add)
    return mock_idle_add


@pytest.fixture
def mock_analisar(monkeypatch):
    """Mock analisar_imagem para retornar resultado fixo."""
    resultado = {"tipo": "icon", "descricao": "ícone de teste", "tags": ["test"]}
    mock_fn = mock.MagicMock(return_value=resultado)
    monkeypatch.setattr("src.ai_vision.orchestrator.analisar_imagem", mock_fn)
    return mock_fn


@pytest.fixture
def mock_paleta(monkeypatch):
    """Mock extrair_paleta para retornar cores fixas."""
    mock_fn = mock.MagicMock(return_value=["#bd93f9", "#ff79c6"])
    monkeypatch.setattr("src.ai_vision.orchestrator.extrair_paleta", mock_fn)
    return mock_fn


def test_cancelamento_encerra_em_3s(filas_teste, mock_glib, monkeypatch):
    """Orchestrator deve encerrar em < 3s quando cancelado com fila vazia."""
    monkeypatch.setattr("src.ai_vision.orchestrator.filas", filas_teste)

    from src.ai_vision.orchestrator import Orchestrator

    log_msgs = []
    concluido = threading.Event()

    orch = Orchestrator(
        on_log=lambda msg: log_msgs.append(msg),
        on_asset=lambda a: None,
        on_concluido=lambda n: concluido.set(),
    )
    orch.iniciar()
    orch.cancelar()

    encerrou = concluido.wait(timeout=3.0)
    assert encerrou, "Orchestrator não encerrou em 3 segundos após cancelamento"


def test_sentinel_encerra_normalmente(filas_teste, mock_glib, monkeypatch):
    """Orchestrator encerra ao receber SENTINEL."""
    monkeypatch.setattr("src.ai_vision.orchestrator.filas", filas_teste)

    from src.ai_vision.orchestrator import Orchestrator

    filas_teste.scraper.put(SENTINEL)
    concluido = threading.Event()
    total_ref = [0]

    orch = Orchestrator(
        on_log=lambda msg: None,
        on_asset=lambda a: None,
        on_concluido=lambda n: (total_ref.__setitem__(0, n), concluido.set()),
    )
    orch.iniciar()

    encerrou = concluido.wait(timeout=5.0)
    assert encerrou
    assert total_ref[0] == 0


def test_processa_asset_antes_de_sentinel(
    filas_teste, mock_glib, mock_analisar, mock_paleta, monkeypatch, tmp_path
):
    """Orchestrator processa asset e chama on_asset."""
    monkeypatch.setattr("src.ai_vision.orchestrator.filas", filas_teste)

    from src.ai_vision.orchestrator import Orchestrator

    # Cria arquivo temporário para o asset
    img_path = tmp_path / "icon.png"
    img_path.write_bytes(b"\x89PNG fake")

    asset = AssetBruto(
        url="https://example.com/icon.png",
        caminho_local=str(img_path),
        tipo="icon",
        origem="https://example.com",
    )
    filas_teste.scraper.put(asset)
    filas_teste.scraper.put(SENTINEL)

    assets_recebidos = []
    concluido = threading.Event()

    orch = Orchestrator(
        on_log=lambda msg: None,
        on_asset=lambda a: assets_recebidos.append(a),
        on_concluido=lambda n: concluido.set(),
    )
    orch.iniciar()
    concluido.wait(timeout=10.0)

    assert len(assets_recebidos) == 1
    assert assets_recebidos[0].tipo == "icon"
    mock_analisar.assert_called_once()
```

- [ ] **Step 2: Rodar teste e confirmar que falha**

Run: `.venv/bin/pytest tests/unit/test_orchestrator_timeout.py::test_cancelamento_encerra_em_3s -v`
Expected: FAIL (timeout — o Orchestrator trava no get() sem timeout)

- [ ] **Step 3: Implementar get com timeout no Orchestrator**

Em `src/ai_vision/orchestrator.py`, adicionar import:
```python
from queue import Empty
```

Substituir o bloco de `_executar` (linhas 99-117) por:

```python
    def _executar(self) -> None:
        """Corpo da Thread B: consome filas.scraper até SENTINEL."""
        total = 0
        try:
            while True:
                if self._evento_parar.is_set():
                    break

                self._evento_pausar.wait()
                if self._evento_parar.is_set():
                    break

                try:
                    item = filas.scraper.get(timeout=1.0)
                except Empty:
                    continue

                if item is SENTINEL:
                    logger.info("Orchestrator recebeu SENTINEL — encerrando")
                    break
```

O restante do método permanece igual (a partir de `asset_bruto: AssetBruto = item`).

- [ ] **Step 4: Rodar testes e confirmar que passam**

Run: `.venv/bin/pytest tests/unit/test_orchestrator_timeout.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/ai_vision/orchestrator.py tests/unit/test_orchestrator_timeout.py
git commit -m "fix: adicionar timeout no get() do Orchestrator para permitir cancelamento"
```

---

### Task 4: BUG-05 -- Conectar Córtex → Espólio

**Files:**
- Modify: `src/gui/pages/cortex.py:303-311`
- Modify: `src/gui/main_window.py:83-93`

- [ ] **Step 1: Adicionar método conectar_espolio em CortexPage**

Em `src/gui/pages/cortex.py`, adicionar método na classe CortexPage (após `__init__`):

```python
    def conectar_espolio(self, espolio_page) -> None:
        """Conecta o Córtex ao Espólio para alimentar contadores de exportação."""
        self._espolio = espolio_page
```

- [ ] **Step 2: Atualizar _cb_asset_processado para chamar registrar_asset**

Substituir o método `_cb_asset_processado` (linhas 303-311):

```python
    def _cb_asset_processado(self, asset: AssetProcessado) -> None:
        """Recebe asset analisado, adiciona ao grid e registra no Espólio."""
        if self._row_placeholder:
            self._listbox_grid.remove(self._row_placeholder)
            self._row_placeholder = None

        card = _criar_card_asset(asset)
        self._listbox_grid.prepend(card)

        if hasattr(self, "_espolio") and self._espolio:
            self._espolio.registrar_asset(asset)
```

- [ ] **Step 3: Conectar páginas em main_window.py**

Em `src/gui/main_window.py`, após a criação do dicionário `self._paginas` (linha 93), adicionar:

```python
        # Conectar Córtex → Espólio (BUG-05)
        self._paginas["cortex"].conectar_espolio(self._paginas["espolio"])
```

- [ ] **Step 4: Commit**

```bash
git add src/gui/pages/cortex.py src/gui/main_window.py
git commit -m "fix: conectar Córtex ao Espólio para alimentar contadores de exportação"
```

---

### Task 5: BUG-04 -- Timeout no Protocolo marca erro

**Files:**
- Modify: `src/gui/pages/protocolo.py:326-329`

- [ ] **Step 1: Corrigir tratamento de timeout em _executar_lote_thread**

Em `src/gui/pages/protocolo.py`, substituir o bloco de execução do spider (linhas 316-332):

```python
            spider = StealthSpider(
                on_log=lambda msg: GLib.idle_add(self._label_status_lote.set_label, msg[:80]),
                on_progresso=lambda _f, _t: None,
                on_concluido=lambda n, _s=status_ref, _e=concluido_evt: (
                    _s.__setitem__(0, "sem assets") if n == 0 else None,
                    _e.set(),
                ),
            )
            try:
                spider.iniciar(url, modo_furtivo=modo_furtivo)
                terminado = concluido_evt.wait(timeout=300)
                if not terminado:
                    status_final[0] = "erro"
                    spider.cancelar()
                    logger.warning("Timeout ao processar %s", url)
            except Exception as exc:
                logger.error("Erro ao processar %s: %s", url, exc)
                status_final[0] = "erro"
```

A diferença: `concluido_evt.wait(timeout=300)` agora retorna bool, e se `False` (timeout), marca como "erro" e cancela o spider.

- [ ] **Step 2: Commit**

```bash
git add src/gui/pages/protocolo.py
git commit -m "fix: timeout no Protocolo marca URL como erro em vez de concluída"
```

---

### Task 6: BUG-06 -- Pango.EllipsizeMode.END

**Files:**
- Modify: `src/gui/pages/cortex.py:1,64`

- [ ] **Step 1: Adicionar import de Pango e corrigir magic number**

Em `src/gui/pages/cortex.py`, adicionar ao bloco de imports do gi.repository:

```python
# ANTES:
from gi.repository import Gtk

# DEPOIS:
from gi.repository import Gtk, Pango
```

Substituir o magic number na função `_criar_card_asset` (linha 64):

```python
# ANTES:
    lbl_desc.set_ellipsize(3)  # PANGO_ELLIPSIZE_END

# DEPOIS:
    lbl_desc.set_ellipsize(Pango.EllipsizeMode.END)
```

- [ ] **Step 2: Commit**

```bash
git add src/gui/pages/cortex.py
git commit -m "fix: substituir magic number por Pango.EllipsizeMode.END no Córtex"
```

---

### Task 7: BUG-07 + BUG-08 -- Caminhos relativos a Path(\_\_file\_\_)

**Files:**
- Modify: `src/core/logging_config.py:12-13`
- Modify: `src/core/checkpoint.py:15`
- Modify: `src/ai_vision/ollama_lifecycle.py:125`
- Create: `tests/unit/test_paths.py`

- [ ] **Step 1: Escrever teste de resolução de caminhos**

```python
# tests/unit/test_paths.py
"""
Testes de resolução de caminhos via Path(__file__).

Verificam que LOGS_DIR, CHECKPOINT_PATH e o binário do Ollama
apontam para dentro do diretório do projeto, independente do CWD.
"""

from pathlib import Path


def test_logs_dir_dentro_do_projeto():
    from src.core.logging_config import LOGS_DIR

    projeto = Path(__file__).resolve().parent.parent.parent
    assert str(LOGS_DIR).startswith(str(projeto)), f"LOGS_DIR ({LOGS_DIR}) deve estar dentro de {projeto}"


def test_checkpoint_path_dentro_do_projeto():
    from src.core.checkpoint import CHECKPOINT_PATH

    projeto = Path(__file__).resolve().parent.parent.parent
    assert str(CHECKPOINT_PATH).startswith(str(projeto)), (
        f"CHECKPOINT_PATH ({CHECKPOINT_PATH}) deve estar dentro de {projeto}"
    )


def test_logs_dir_nao_depende_do_cwd(monkeypatch, tmp_path):
    """LOGS_DIR deve ser estável mesmo com CWD diferente."""
    import importlib

    import src.core.logging_config as mod

    monkeypatch.chdir(tmp_path)
    importlib.reload(mod)

    assert "logs" in str(mod.LOGS_DIR)
    assert str(tmp_path) not in str(mod.LOGS_DIR) or str(mod.LOGS_DIR).endswith("Project_Beholder/logs")
```

- [ ] **Step 2: Rodar teste e confirmar que falha**

Run: `.venv/bin/pytest tests/unit/test_paths.py -v`
Expected: FAIL (Path("logs") é relativo ao CWD)

- [ ] **Step 3: Corrigir logging_config.py**

Em `src/core/logging_config.py`, substituir linhas 12-13:

```python
# ANTES:
LOGS_DIR = Path("logs")
LOG_FILE = LOGS_DIR / "beholder.log"

# DEPOIS:
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = _PROJECT_ROOT / "logs"
LOG_FILE = LOGS_DIR / "beholder.log"
```

Explicação: `__file__` = `src/core/logging_config.py`, `.parent` × 3 = raiz do projeto.

- [ ] **Step 4: Corrigir checkpoint.py**

Em `src/core/checkpoint.py`, substituir linha 15:

```python
# ANTES:
CHECKPOINT_PATH = Path("data/sessao_atual/.checkpoint.json")

# DEPOIS:
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CHECKPOINT_PATH = _PROJECT_ROOT / "data" / "sessao_atual" / ".checkpoint.json"
```

- [ ] **Step 5: Corrigir ollama_lifecycle.py**

Em `src/ai_vision/ollama_lifecycle.py`, adicionar constante no topo (após imports):

```python
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
```

Na função `_thread_subir` (linha 125), substituir:

```python
# ANTES:
        projeto_dir = Path.cwd()
        binario = projeto_dir / "bin" / "ollama"

# DEPOIS:
        binario = _PROJECT_ROOT / "bin" / "ollama"
```

E atualizar as referências a `projeto_dir` dentro do mesmo método:

```python
# ANTES:
        env["OLLAMA_TMPDIR"] = str(projeto_dir / _cfg_ia["ollama_tmpdir"])
        env["OLLAMA_MODELS"] = str(projeto_dir / _cfg_ia["ollama_models"])

# DEPOIS:
        env["OLLAMA_TMPDIR"] = str(_PROJECT_ROOT / _cfg_ia["ollama_tmpdir"])
        env["OLLAMA_MODELS"] = str(_PROJECT_ROOT / _cfg_ia["ollama_models"])
```

- [ ] **Step 6: Rodar testes e confirmar que passam**

Run: `.venv/bin/pytest tests/unit/test_paths.py -v`
Expected: 3 passed

- [ ] **Step 7: Commit**

```bash
git add src/core/logging_config.py src/core/checkpoint.py src/ai_vision/ollama_lifecycle.py tests/unit/test_paths.py
git commit -m "fix: caminhos relativos a Path(__file__) em vez de CWD"
```

---

### Task 8: BUG-09 -- httpx assíncrono no Grimório

**Files:**
- Modify: `src/gui/pages/grimorio.py:2,215-230`

- [ ] **Step 1: Adicionar imports necessários**

Em `src/gui/pages/grimorio.py`, adicionar aos imports:

```python
import threading

from gi.repository import GLib, Gtk
```

Nota: `Gtk` já é importado. Adicionar apenas `threading` e `GLib`.

- [ ] **Step 2: Substituir _on_testar_ollama por versão com thread**

Substituir o método `_on_testar_ollama` (linhas 215-230) por:

```python
    def _on_testar_ollama(self, _btn: Gtk.Button) -> None:
        """Faz ping na porta configurada do Ollama em thread separada (ADR-01)."""
        porta = self._entry_porta.get_text().strip() or str(DEFAULTS["IA"]["ollama_port"])
        self._btn_testar.set_sensitive(False)
        self._label_status.set_label("Testando Ollama...")
        threading.Thread(
            target=self._thread_testar_ollama,
            args=(porta,),
            daemon=True,
            name="beholder-grimorio-test",
        ).start()
        logger.info("Grimório: teste Ollama na porta %s", porta)

    def _thread_testar_ollama(self, porta: str) -> None:
        """Thread de teste do Ollama — resultado via GLib.idle_add (ADR-01)."""
        url = f"http://127.0.0.1:{porta}/api/tags"
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    GLib.idle_add(self._label_status.set_label, f"[OK] Ollama online na porta {porta}.")
                else:
                    GLib.idle_add(
                        self._label_status.set_label, f"[AVISO] Ollama respondeu HTTP {resp.status_code}."
                    )
        except httpx.ConnectError:
            GLib.idle_add(self._label_status.set_label, f"[OFFLINE] Ollama não responde na porta {porta}.")
        except Exception as exc:
            GLib.idle_add(self._label_status.set_label, f"[ERRO] {exc}")
        finally:
            GLib.idle_add(self._btn_testar.set_sensitive, True)
```

- [ ] **Step 3: Commit**

```bash
git add src/gui/pages/grimorio.py
git commit -m "fix: mover teste do Ollama no Grimório para thread separada"
```

---

### Task 9: BUG-11 -- hashlib.md5 para nomes de arquivo

**Files:**
- Modify: `src/scraper/stealth_spider.py:5,256`
- Create: `tests/unit/test_hash_estavel.py`

- [ ] **Step 1: Escrever teste de estabilidade do hash**

```python
# tests/unit/test_hash_estavel.py
"""
Testes de estabilidade de hash para nomes de arquivo.

Verifica que o mesmo URL sempre gera o mesmo nome de arquivo,
mesmo entre execuções diferentes do processo Python.
"""

import hashlib


def _gerar_nome(url: str) -> str:
    """Reproduz a lógica de geração de nome do stealth_spider."""
    return f"asset_{hashlib.md5(url.encode()).hexdigest()[:12]}.bin"


def test_hash_estavel_entre_chamadas():
    url = "https://example.com/imagem.png"
    nome1 = _gerar_nome(url)
    nome2 = _gerar_nome(url)
    assert nome1 == nome2


def test_hash_diferente_para_urls_diferentes():
    nome1 = _gerar_nome("https://a.com/x.png")
    nome2 = _gerar_nome("https://b.com/y.png")
    assert nome1 != nome2


def test_hash_formato_valido():
    nome = _gerar_nome("https://example.com/test.svg")
    assert nome.startswith("asset_")
    assert nome.endswith(".bin")
    assert len(nome) == len("asset_") + 12 + len(".bin")


def test_hash_reproduzivel_entre_sessoes():
    """O valor md5 é determinístico, diferente de hash() que usa randomização."""
    url = "https://example.com/icon.svg"
    esperado = f"asset_{hashlib.md5(url.encode()).hexdigest()[:12]}.bin"
    assert _gerar_nome(url) == esperado
```

- [ ] **Step 2: Rodar teste e confirmar que passa (teste da lógica nova isolada)**

Run: `.venv/bin/pytest tests/unit/test_hash_estavel.py -v`
Expected: 4 passed

- [ ] **Step 3: Corrigir stealth_spider.py**

Adicionar import no topo de `src/scraper/stealth_spider.py`:

```python
import hashlib
```

Substituir a geração de nome de fallback no método `_baixar_asset` (linha 256):

```python
# ANTES:
                nome = f"asset_{hash(asset.url) & 0xFFFFFF:06x}.bin"

# DEPOIS:
                nome = f"asset_{hashlib.md5(asset.url.encode()).hexdigest()[:12]}.bin"
```

- [ ] **Step 4: Rodar todos os testes**

Run: `.venv/bin/pytest tests/ -v --timeout=30`
Expected: todos passam

- [ ] **Step 5: Commit**

```bash
git add src/scraper/stealth_spider.py tests/unit/test_hash_estavel.py
git commit -m "fix: usar hashlib.md5 para nomes de arquivo estáveis entre execuções"
```

---

### Task 10: VIOLAÇÃO-02 + VIOLAÇÃO-04 -- requirements.txt + Justfile

**Files:**
- Modify: `requirements.txt:1-5`
- Modify: `Justfile:10-20,42-55`

- [ ] **Step 1: Remover PyGObject do requirements.txt**

Remover as linhas 1-5 (comentário + PyGObject):

```
# ANTES (linhas 1-5):
# Interface
# PyGObject 3.50+ requer girepository-2.0 (GLib 2.80+) — indisponível no Ubuntu 22.04.
# Pinar em <3.50 para usar gobject-introspection-1.0 (disponível em Ubuntu 22.04 como 1.72.0).
# install.sh exporta PKG_CONFIG_PATH para que meson encontre os headers de compilação.
PyGObject>=3.48,<3.50

# DEPOIS (linhas 1-2):
# Interface — PyGObject é pacote de sistema (GSD.md), instalado via install.sh
# Nunca instalar PyGObject via pip.
```

- [ ] **Step 2: Prefixar comandos do Justfile com .venv/bin/**

Substituir o conteúdo do `Justfile`:

```just
# Project Beholder — Task runner

install:
    bash install.sh

setup:
    bash install.sh

ci-local:
    #!/usr/bin/env bash
    set -e
    echo "=== [1/4] Lint ==="
    .venv/bin/ruff check src/ tests/
    .venv/bin/ruff format --check src/ tests/
    echo "=== [2/4] Smoke ==="
    .venv/bin/pytest tests/smoke/ -v --timeout=10
    echo "=== [3/4] Unit ==="
    .venv/bin/pytest tests/unit/ -v
    echo "=== [4/4] Imports ==="
    .venv/bin/python -c "import src"
    echo "=== CI OK ==="

ci-quick:
    .venv/bin/ruff check src/ tests/
    .venv/bin/pytest tests/smoke/ --timeout=10 -q

run:
    bash run.sh

uninstall:
    bash uninstall.sh

teardown:
    bash teardown.sh

doctor:
    #!/usr/bin/env bash
    echo "=== Doctor ==="
    .venv/bin/python --version
    .venv/bin/python -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk; print('GTK4 OK')" 2>/dev/null || echo "AVISO: GTK4 nao encontrado"
    .venv/bin/python -c "import gi; gi.require_version('Adw', '1'); from gi.repository import Adw; print('Libadwaita OK')" 2>/dev/null || echo "AVISO: Libadwaita nao encontrado"
    .venv/bin/python -c "import playwright; print('Playwright OK')" 2>/dev/null || echo "AVISO: Playwright nao instalado"
    .venv/bin/python -c "import cv2; print('OpenCV OK')" 2>/dev/null || echo "AVISO: OpenCV nao instalado"
    .venv/bin/python -c "from sklearn.cluster import KMeans; print('scikit-learn OK')" 2>/dev/null || echo "AVISO: scikit-learn nao instalado"
    [ -f bin/ollama ] && echo "Ollama binario OK" || echo "AVISO: bin/ollama nao encontrado"
    echo "=== Doctor concluido ==="

lint:
    .venv/bin/ruff format src/ tests/
    .venv/bin/ruff check --fix src/ tests/

lint-check:
    .venv/bin/ruff check src/ tests/
    .venv/bin/ruff format --check src/ tests/

clean:
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true

test-smoke:
    .venv/bin/pytest tests/smoke/ -v

test-unit:
    .venv/bin/pytest tests/unit/ -v

test-all:
    .venv/bin/pytest tests/ -v
```

- [ ] **Step 3: Verificar lint**

Run: `.venv/bin/ruff check src/ tests/`
Expected: sem erros

- [ ] **Step 4: Commit**

```bash
git add requirements.txt Justfile
git commit -m "fix: remover PyGObject do requirements.txt e prefixar .venv/bin/ no Justfile"
```

---

### Task 11: Validação final -- ci-local + validação visual

**Files:** Nenhum novo.

- [ ] **Step 1: Rodar ci-local completo**

Run: `just ci-local`
Expected: lint OK, smoke OK, unit OK, imports OK — 90+ testes passando

- [ ] **Step 2: Validação visual da interface**

Run: `python main.py`

Checklist de validação visual:
1. App abre sem erro
2. Busca: inserir URL e clicar INICIAR → scraping funciona
3. Córtex: clicar ANALISAR → status muda (pode falhar se Ollama ausente, mas não deve travar)
4. Espólio: se análise funcionou, contadores devem refletir os assets processados
5. Protocolo: adicionar URL e clicar EXECUTAR LOTE → progresso atualiza
6. Grimório: clicar TESTAR OLLAMA → UI não congela (resultado aparece após 2s)
7. Grimório: SALVAR e RESTAURAR PADRÕES funcionam

- [ ] **Step 3: Commit final consolidando**

Se houve ajustes durante a validação:
```bash
git add -u
git commit -m "fix: ajustes finais da Sprint 13 após validação visual"
```

- [ ] **Step 4: Atualizar GSD.md**

Marcar Sprint 13 como COMPLETA no GSD.md:

```markdown
| 13 | COMPLETA | Correções retroativas da auditoria |
```

E mover os bugs corrigidos para uma seção "Bugs Resolvidos" ou removê-los da seção "Bugs Conhecidos".

```bash
git add GSD.md
git commit -m "docs: marcar Sprint 13 como completa no GSD.md"
```
