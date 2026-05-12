"""
Testes de integração — propagação dinâmica de config (Sprint 18, ADR-02).

Valida que alterações em DEFAULTS (feitas pelo Grimório em runtime) passam a
valer sem reiniciar a aplicação nos módulos que historicamente congelavam
valores em escopo de módulo.

Bugs cobertos:
- M-1: moondream_prompt lia `_cfg = DEFAULTS["IA"]` no import
- M-2: ollama_lifecycle lia `PORTA_OLLAMA` no import
- M-3: espolio lia `_DIR_OUTPUT` / `_DIR_DATA` no import
- M-4: StealthSpider congelava valores em `__init__`
- M-5: Orchestrator congelava `_kmeans_cores` em `__init__`
"""

import copy

import pytest

from src.core.config.defaults import DEFAULTS


def _snapshot_secao(nome: str):
    """Deep-copy a seção para permitir restauração correta de dicts aninhados."""
    return copy.deepcopy(DEFAULTS[nome])


def _restaurar_secao(nome: str, snapshot):
    DEFAULTS[nome].clear()
    DEFAULTS[nome].update(copy.deepcopy(snapshot))


@pytest.fixture
def cfg_ia_backup():
    snap = _snapshot_secao("IA")
    yield
    _restaurar_secao("IA", snap)


@pytest.fixture
def cfg_scraper_backup():
    snap = _snapshot_secao("Scraper")
    yield
    _restaurar_secao("Scraper", snap)


@pytest.fixture
def cfg_saida_backup():
    snap = _snapshot_secao("Saida")
    yield
    _restaurar_secao("Saida", snap)


@pytest.fixture
def cfg_espolio_backup():
    snap = _snapshot_secao("Espolio")
    yield
    _restaurar_secao("Espolio", snap)


@pytest.mark.integration
def test_moondream_porta_propaga(cfg_ia_backup):
    """Mudar DEFAULTS["IA"]["ollama_port"] deve afetar _base_url() imediatamente."""
    from src.ai_vision.moondream_prompt import _base_url

    DEFAULTS["IA"]["ollama_port"] = 11435
    antes = _base_url()
    DEFAULTS["IA"]["ollama_port"] = 22222
    depois = _base_url()

    assert "11435" in antes
    assert "22222" in depois


@pytest.mark.integration
def test_moondream_modelo_tier_propaga(cfg_ia_backup):
    """Alterar modelo_tier deve mudar o nome resolvido sem reiniciar."""
    from src.ai_vision.moondream_prompt import _resolver_modelo

    DEFAULTS["IA"]["modelo_tier"] = "low"
    nome_low = _resolver_modelo()
    DEFAULTS["IA"]["modelo_tier"] = "high"
    nome_high = _resolver_modelo()

    assert nome_low != nome_high, "Troca de tier não propagou"


@pytest.mark.integration
def test_ollama_lifecycle_porta_propaga(cfg_ia_backup):
    """ollama_lifecycle._base_url() reflete mudança em runtime."""
    from src.ai_vision.ollama_lifecycle import _base_url, _porta_ollama

    DEFAULTS["IA"]["ollama_port"] = 11435
    assert _porta_ollama() == 11435
    assert "11435" in _base_url()

    DEFAULTS["IA"]["ollama_port"] = 33333
    assert _porta_ollama() == 33333
    assert "33333" in _base_url()


@pytest.mark.integration
def test_espolio_diretorios_propagam(cfg_saida_backup):
    """_dir_output e _dir_data devem refletir mudanças em DEFAULTS."""
    from src.gui.pages.espolio import _dir_data, _dir_output

    DEFAULTS["Saida"]["diretorio_output"] = "saida_a"
    DEFAULTS["Saida"]["diretorio_data"] = "dados_a"
    assert _dir_output().name == "saida_a"
    assert _dir_data().name == "dados_a"

    DEFAULTS["Saida"]["diretorio_output"] = "saida_b"
    DEFAULTS["Saida"]["diretorio_data"] = "dados_b"
    assert _dir_output().name == "saida_b"
    assert _dir_data().name == "dados_b"


@pytest.mark.integration
def test_dataset_writer_mapa_propaga(cfg_espolio_backup):
    """subpasta_tipo reflete mudanças no mapa de pastas."""
    from src.exporter.dataset_writer import subpasta_tipo

    assert subpasta_tipo("icon") == "ícones"

    DEFAULTS["Espolio"]["mapa_pastas"]["icon"] = "glifos"
    assert subpasta_tipo("icon") == "glifos"


@pytest.mark.integration
def test_spider_recarrega_config_em_iniciar(cfg_scraper_backup, monkeypatch):
    """StealthSpider relê valores de DEFAULTS a cada iniciar()."""
    from src.scraper.stealth_spider import StealthSpider

    DEFAULTS["Scraper"]["timeout"] = 30
    DEFAULTS["Scraper"]["max_retries"] = 3
    DEFAULTS["Scraper"]["user_agent"] = "agente-a"

    spider = StealthSpider(
        on_log=lambda _m: None,
        on_progresso=lambda _f, _t: None,
        on_concluido=lambda _n: None,
    )
    # Impede a thread real de rodar
    monkeypatch.setattr(
        "src.scraper.stealth_spider.threading.Thread",
        lambda *a, **kw: type("FakeThread", (), {"start": lambda self: None, "is_alive": lambda self: False})(),
    )

    DEFAULTS["Scraper"]["timeout"] = 77
    DEFAULTS["Scraper"]["max_retries"] = 9
    DEFAULTS["Scraper"]["user_agent"] = "agente-b"

    spider.iniciar("https://exemplo.com")

    assert spider._timeout == 77
    assert spider._max_retries == 9
    assert spider._user_agent == "agente-b"


@pytest.mark.integration
def test_orchestrator_recarrega_kmeans_em_iniciar(cfg_saida_backup, monkeypatch):
    """Orchestrator relê _kmeans_cores de DEFAULTS a cada iniciar()."""
    from src.ai_vision.orchestrator import Orchestrator

    DEFAULTS["Saida"]["kmeans_cores"] = 4
    orch = Orchestrator(
        on_log=lambda _m: None,
        on_asset=lambda _a: None,
        on_concluido=lambda _n: None,
    )
    assert orch._kmeans_cores == 4

    DEFAULTS["Saida"]["kmeans_cores"] = 9
    # Stub da thread para não rodar de verdade
    monkeypatch.setattr(
        "src.ai_vision.orchestrator.threading.Thread",
        lambda *a, **kw: type("FakeThread", (), {"start": lambda self: None, "is_alive": lambda self: False})(),
    )
    orch.iniciar()
    assert orch._kmeans_cores == 9


@pytest.mark.integration
def test_protocolo_timeout_em_defaults():
    """DEFAULTS["Protocolo"]["timeout_url"] existe e é um inteiro positivo."""
    timeout = DEFAULTS["Protocolo"]["timeout_url"]
    assert isinstance(timeout, int)
    assert timeout > 0


# "A verdade é filha do tempo, não da autoridade." — Francis Bacon
