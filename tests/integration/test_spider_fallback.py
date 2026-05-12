"""
Testes de integração — fallback Playwright→requests (Sprint 22.6).

Valida:
- Quando Playwright falha, spider usa `_get_com_retry` sem derrubar a thread.
- Mensagem de aviso aparece no log.
- HTML do fallback é parseado normalmente pela site_strategy.
"""

import threading
import unittest.mock as mock
from pathlib import Path

import pytest

from src.core.asset_queue import FilasPipeline


@pytest.fixture
def filas_teste():
    return FilasPipeline()


@pytest.mark.integration
def test_fallback_ativa_quando_playwright_falha(filas_teste, monkeypatch, tmp_path):
    """Modo furtivo: se _get_playwright lança exceção, cai em _get_com_retry sem crash."""
    monkeypatch.setattr("src.scraper.stealth_spider.filas", filas_teste)
    monkeypatch.setattr("src.scraper.stealth_spider.GLib.idle_add", lambda fn, *a: fn(*a))

    from src.scraper.stealth_spider import StealthSpider

    logs: list[str] = []
    concluido = threading.Event()

    spider = StealthSpider(
        on_log=lambda m: logs.append(m),
        on_progresso=lambda _f, _t: None,
        on_concluido=lambda _n: concluido.set(),
    )

    # Playwright falha de propósito
    monkeypatch.setattr(
        spider,
        "_get_playwright",
        mock.MagicMock(side_effect=RuntimeError("chromium não instalado")),
    )
    # Requests retorna HTML mínimo válido
    html_fake = '<html><body><img src="/foo.png"></body></html>'
    monkeypatch.setattr(
        spider,
        "_get_com_retry",
        mock.MagicMock(return_value=html_fake),
    )
    # Download real de assets desnecessário — mocka para evitar rede
    monkeypatch.setattr(
        spider,
        "_baixar_asset",
        mock.MagicMock(return_value=str(tmp_path / "fake.png")),
    )

    spider.iniciar("https://exemplo.com", diretorio_saida=str(tmp_path), modo_furtivo=True)
    assert concluido.wait(timeout=10.0)

    log_texto = " ".join(logs)
    assert "Playwright indisponível" in log_texto, f"Log esperava aviso; veio: {log_texto}"
    assert "fallback" in log_texto.lower()
    spider._get_com_retry.assert_called_once_with("https://exemplo.com")


@pytest.mark.integration
def test_modo_normal_nao_chama_playwright(filas_teste, monkeypatch, tmp_path):
    """Modo furtivo=False jamais invoca Playwright."""
    monkeypatch.setattr("src.scraper.stealth_spider.filas", filas_teste)
    monkeypatch.setattr("src.scraper.stealth_spider.GLib.idle_add", lambda fn, *a: fn(*a))

    from src.scraper.stealth_spider import StealthSpider

    concluido = threading.Event()
    spider = StealthSpider(
        on_log=lambda _m: None,
        on_progresso=lambda _f, _t: None,
        on_concluido=lambda _n: concluido.set(),
    )

    playwright_spy = mock.MagicMock()
    monkeypatch.setattr(spider, "_get_playwright", playwright_spy)
    monkeypatch.setattr(
        spider,
        "_get_com_retry",
        mock.MagicMock(return_value="<html></html>"),
    )

    spider.iniciar("https://exemplo.com", diretorio_saida=str(tmp_path), modo_furtivo=False)
    assert concluido.wait(timeout=10.0)

    playwright_spy.assert_not_called()


# "O que não quebra, fortalece — o que falha, ensina." — Nietzsche adaptado
