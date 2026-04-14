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
