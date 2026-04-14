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

from src.core.asset_queue import SENTINEL, FilasPipeline


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
