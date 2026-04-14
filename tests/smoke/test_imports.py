"""
Smoke tests: verifica que os módulos core importam sem erro.
Esses testes não requerem display GTK nem GPU.
"""

import pytest


@pytest.mark.smoke
def test_importar_pathlib() -> None:
    """Stdlib disponível."""
    from pathlib import Path

    assert Path.home().exists()


@pytest.mark.smoke
def test_importar_requests() -> None:
    """requests disponível."""
    import requests

    assert hasattr(requests, "get")


@pytest.mark.smoke
def test_importar_beautifulsoup() -> None:
    """beautifulsoup4 disponível."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup("<html><body>ok</body></html>", "html.parser")
    assert soup.body is not None


@pytest.mark.smoke
def test_importar_numpy() -> None:
    """numpy disponível."""
    import numpy as np

    arr = np.array([1, 2, 3])
    assert arr.sum() == 6


@pytest.mark.smoke
def test_importar_pillow() -> None:
    """Pillow disponível."""
    from PIL import Image

    assert hasattr(Image, "open")


@pytest.mark.smoke
def test_importar_sklearn() -> None:
    """scikit-learn disponível."""
    from sklearn.cluster import KMeans

    assert KMeans is not None


@pytest.mark.smoke
def test_importar_httpx() -> None:
    """httpx disponível."""
    import httpx

    assert hasattr(httpx, "get")


@pytest.mark.smoke
def test_importar_dotenv() -> None:
    """python-dotenv disponível."""
    from dotenv import load_dotenv

    assert callable(load_dotenv)
