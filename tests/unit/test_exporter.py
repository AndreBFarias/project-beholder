"""
Testes unitários para src/exporter/dataset_writer.py.

Cobrem:
- escrever_csv gera arquivo com cabeçalho correto
- escrever_csv serializa listas (tags, paleta_hex) separadas por |
- ler_csv retorna lista de dicts com os valores originais
- escrever_csv com lista vazia gera apenas cabeçalho
- subpasta_tipo mapeia tipos corretamente
"""

import csv

import pytest

from src.core.asset_queue import AssetProcessado
from src.exporter.dataset_writer import escrever_csv, ler_csv, subpasta_tipo

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def asset_simples():
    return AssetProcessado(
        url_original="https://example.com/icon.svg",
        caminho_local="data/sessao_atual/icon.svg",
        tipo="icon",
        descricao="ícone de configuração",
        tags=["config", "settings", "gear"],
        paleta_hex=["#bd93f9", "#ff79c6"],
        timestamp="2026-01-01T00:00:00+00:00",
    )


@pytest.fixture
def asset_sem_extras():
    return AssetProcessado(
        url_original="https://example.com/bg.jpg",
        caminho_local="data/sessao_atual/bg.jpg",
        tipo="background",
        descricao="fundo escuro",
        tags=[],
        paleta_hex=[],
        timestamp="2026-01-02T00:00:00+00:00",
    )


# ------------------------------------------------------------------
# escrever_csv
# ------------------------------------------------------------------


def test_escrever_csv_cria_arquivo(tmp_path, asset_simples):
    destino = tmp_path / "out.csv"
    resultado = escrever_csv([asset_simples], destino)
    assert resultado.exists()


def test_escrever_csv_cabecalho_correto(tmp_path, asset_simples):
    destino = tmp_path / "out.csv"
    escrever_csv([asset_simples], destino)
    with destino.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert set(reader.fieldnames) == {
            "url_original",
            "caminho_local",
            "tipo",
            "descricao",
            "tags",
            "paleta_hex",
            "timestamp",
        }


def test_escrever_csv_serializa_tags(tmp_path, asset_simples):
    destino = tmp_path / "out.csv"
    escrever_csv([asset_simples], destino)
    linhas = ler_csv(destino)
    assert linhas[0]["tags"] == "config|settings|gear"


def test_escrever_csv_serializa_paleta(tmp_path, asset_simples):
    destino = tmp_path / "out.csv"
    escrever_csv([asset_simples], destino)
    linhas = ler_csv(destino)
    assert linhas[0]["paleta_hex"] == "#bd93f9|#ff79c6"


def test_escrever_csv_listas_vazias(tmp_path, asset_sem_extras):
    destino = tmp_path / "out.csv"
    escrever_csv([asset_sem_extras], destino)
    linhas = ler_csv(destino)
    assert linhas[0]["tags"] == ""
    assert linhas[0]["paleta_hex"] == ""


def test_escrever_csv_lista_vazia_gera_cabecalho(tmp_path):
    destino = tmp_path / "vazio.csv"
    escrever_csv([], destino)
    with destino.open(encoding="utf-8") as f:
        conteudo = f.read()
    assert "url_original" in conteudo
    # Apenas uma linha (cabeçalho)
    assert conteudo.count("\n") == 1


def test_escrever_csv_multiplos_assets(tmp_path, asset_simples, asset_sem_extras):
    destino = tmp_path / "multi.csv"
    escrever_csv([asset_simples, asset_sem_extras], destino)
    linhas = ler_csv(destino)
    assert len(linhas) == 2


def test_escrever_csv_cria_diretorios(tmp_path, asset_simples):
    destino = tmp_path / "nested" / "dir" / "out.csv"
    escrever_csv([asset_simples], destino)
    assert destino.exists()


# ------------------------------------------------------------------
# ler_csv
# ------------------------------------------------------------------


def test_ler_csv_retorna_lista_vazia_se_nao_existe(tmp_path):
    resultado = ler_csv(tmp_path / "inexistente.csv")
    assert resultado == []


def test_ler_csv_roundtrip(tmp_path, asset_simples):
    destino = tmp_path / "rt.csv"
    escrever_csv([asset_simples], destino)
    linhas = ler_csv(destino)
    assert linhas[0]["url_original"] == asset_simples.url_original
    assert linhas[0]["tipo"] == asset_simples.tipo
    assert linhas[0]["descricao"] == asset_simples.descricao
    assert linhas[0]["timestamp"] == asset_simples.timestamp


# ------------------------------------------------------------------
# subpasta_tipo
# ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tipo", "esperado"),
    [
        ("icon", "icons"),
        ("logo", "icons"),
        ("svg", "icons"),
        ("vector", "icons"),
        ("background", "backgrounds"),
        ("photo", "backgrounds"),
        ("ui_element", "outros"),
        ("other", "outros"),
        ("desconhecido", "outros"),
        ("ICON", "icons"),  # case-insensitive
        ("BACKGROUND", "backgrounds"),
    ],
)
def test_subpasta_mapeamento(tipo, esperado):
    assert subpasta_tipo(tipo) == esperado
