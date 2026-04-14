"""
Testes unitários para src/transformer/icon_alchemist.py.

Cobrem:
- extrair_paleta retorna N strings hex no formato correto
- conversão automática RGBA→RGB não lança exceção
- n_cores limitado ao número de pixels disponíveis
- criar_icone_circular retorna RGBA com tamanho correto
- cantos são transparentes, centro é opaco
"""

import numpy as np
import pytest
from PIL import Image

from src.transformer.icon_alchemist import criar_icone_circular, extrair_paleta


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def img_rgb(tmp_path):
    """Imagem RGB 60x60 com 4 quadrantes de cores distintas."""
    img = Image.new("RGB", (60, 60))
    cores = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
    for x in range(60):
        for y in range(60):
            quadrante = (x // 30) + (y // 30) * 2
            img.putpixel((x, y), cores[quadrante % 4])
    path = tmp_path / "rgb.png"
    img.save(path)
    return path


@pytest.fixture
def img_rgba(tmp_path):
    """Imagem RGBA 30x30 com canal alpha parcial."""
    img = Image.new("RGBA", (30, 30), (100, 150, 200, 128))
    path = tmp_path / "rgba.png"
    img.save(path)
    return path


@pytest.fixture
def img_2x2(tmp_path):
    """Imagem mínima 2x2 para testar limite de n_cores."""
    img = Image.new("RGB", (2, 2))
    img.putpixel((0, 0), (255, 0, 0))
    img.putpixel((1, 0), (0, 255, 0))
    img.putpixel((0, 1), (0, 0, 255))
    img.putpixel((1, 1), (128, 128, 128))
    path = tmp_path / "tiny.png"
    img.save(path)
    return path


# ------------------------------------------------------------------
# extrair_paleta
# ------------------------------------------------------------------


def test_retorna_n_cores(img_rgb):
    paleta = extrair_paleta(img_rgb, n_cores=4)
    assert len(paleta) == 4


def test_formato_hex(img_rgb):
    for cor in extrair_paleta(img_rgb, n_cores=3):
        assert cor.startswith("#")
        assert len(cor) == 7
        int(cor[1:], 16)  # deve ser hex válido


def test_aceita_rgba_sem_falhar(img_rgba):
    paleta = extrair_paleta(img_rgba, n_cores=2)
    assert len(paleta) == 2


def test_n_cores_limitado_por_pixels(img_2x2):
    # 4 pixels disponíveis — pedir 10 deve retornar no máximo 4
    paleta = extrair_paleta(img_2x2, n_cores=10)
    assert len(paleta) <= 4


def test_n_cores_1(img_rgb):
    paleta = extrair_paleta(img_rgb, n_cores=1)
    assert len(paleta) == 1


def test_cores_distintas_em_imagem_com_4_quadrantes(img_rgb):
    paleta = extrair_paleta(img_rgb, n_cores=4)
    # Todas as cores devem ser únicas
    assert len(set(paleta)) == 4


# ------------------------------------------------------------------
# criar_icone_circular
# ------------------------------------------------------------------


def test_tamanho_correto(img_rgb):
    icone = criar_icone_circular(img_rgb, tamanho=64)
    assert icone.size == (64, 64)


def test_modo_rgba(img_rgb):
    icone = criar_icone_circular(img_rgb, tamanho=32)
    assert icone.mode == "RGBA"


def test_cantos_transparentes(img_rgb):
    icone = criar_icone_circular(img_rgb, tamanho=64)
    pixels = np.array(icone)
    assert pixels[0, 0, 3] == 0, "canto superior esquerdo deve ser transparente"
    assert pixels[0, 63, 3] == 0, "canto superior direito deve ser transparente"
    assert pixels[63, 0, 3] == 0, "canto inferior esquerdo deve ser transparente"
    assert pixels[63, 63, 3] == 0, "canto inferior direito deve ser transparente"


def test_centro_opaco(img_rgb):
    icone = criar_icone_circular(img_rgb, tamanho=64)
    pixels = np.array(icone)
    assert pixels[32, 32, 3] > 0, "centro deve ser opaco"


def test_aceita_rgba(img_rgba):
    icone = criar_icone_circular(img_rgba, tamanho=30)
    assert icone.mode == "RGBA"
    assert icone.size == (30, 30)


@pytest.mark.parametrize("tamanho", [16, 32, 64, 128])
def test_tamanhos_variados(img_rgb, tamanho):
    icone = criar_icone_circular(img_rgb, tamanho=tamanho)
    assert icone.size == (tamanho, tamanho)
