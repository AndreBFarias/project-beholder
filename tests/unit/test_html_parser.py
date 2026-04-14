"""
Testes unitários para src/scraper/html_parser.py.

Cobrem:
- Extração de <img src> e <img data-src>
- Extração de <link rel="icon">
- Extração de background-image no atributo style
- Normalização de URLs relativas
- Deduplicação de URLs
- Filtragem de extensões inválidas
- HTML vazio retorna lista vazia
- Classificação correta de tipo
"""

from src.scraper.html_parser import _classificar_tipo, _url_valida, extrair_assets

BASE = "https://exemplo.com"


# ------------------------------------------------------------------
# Testes de _url_valida
# ------------------------------------------------------------------


def test_url_valida_png():
    assert _url_valida("https://exemplo.com/logo.png") is True


def test_url_valida_svg():
    assert _url_valida("https://cdn.site.com/icons/star.svg") is True


def test_url_valida_ico():
    assert _url_valida("https://exemplo.com/favicon.ico") is True


def test_url_invalida_sem_extensao():
    assert _url_valida("https://exemplo.com/pagina") is False


def test_url_invalida_pdf():
    assert _url_valida("https://exemplo.com/doc.pdf") is False


def test_url_invalida_javascript():
    assert _url_valida("javascript:void(0)") is False


# ------------------------------------------------------------------
# Testes de _classificar_tipo
# ------------------------------------------------------------------


def test_tipo_svg():
    assert _classificar_tipo("https://cdn.com/icon.svg") == "svg"


def test_tipo_icon_por_extensao():
    assert _classificar_tipo("https://exemplo.com/favicon.ico") == "icon"


def test_tipo_icon_por_palavra():
    assert _classificar_tipo("https://cdn.com/icons/arrow.png") == "icon"


def test_tipo_background_por_palavra():
    assert _classificar_tipo("https://cdn.com/background-hero.jpg") == "background"


def test_tipo_image_fallback():
    assert _classificar_tipo("https://cdn.com/photo.jpg") == "image"


# ------------------------------------------------------------------
# Testes de extrair_assets
# ------------------------------------------------------------------


def test_html_vazio_retorna_lista_vazia():
    assets = extrair_assets("", BASE)
    assert assets == []


def test_html_sem_assets_retorna_lista_vazia():
    html = "<html><body><p>Texto puro</p></body></html>"
    assets = extrair_assets(html, BASE)
    assert assets == []


def test_extrai_img_src():
    html = '<html><body><img src="/imgs/logo.png"></body></html>'
    assets = extrair_assets(html, BASE)
    assert len(assets) == 1
    assert assets[0].url == "https://exemplo.com/imgs/logo.png"
    assert assets[0].tipo == "image"
    assert assets[0].origem == BASE


def test_extrai_img_data_src():
    html = '<html><body><img data-src="/lazy/icone.svg"></body></html>'
    assets = extrair_assets(html, BASE)
    assert len(assets) == 1
    assert assets[0].url == "https://exemplo.com/lazy/icone.svg"
    assert assets[0].tipo == "svg"


def test_extrai_link_icon():
    html = '<html><head><link rel="icon" href="/favicon.ico"></head></html>'
    assets = extrair_assets(html, BASE)
    assert len(assets) == 1
    assert assets[0].tipo == "icon"
    assert assets[0].url == "https://exemplo.com/favicon.ico"


def test_extrai_link_apple_touch_icon():
    html = '<html><head><link rel="apple-touch-icon" href="/apple-icon.png"></head></html>'
    assets = extrair_assets(html, BASE)
    assert len(assets) == 1
    assert assets[0].tipo == "icon"


def test_extrai_background_image_style():
    html = "<html><body><div style=\"background-image: url('/bg/hero.jpg')\"></div></body></html>"
    assets = extrair_assets(html, BASE)
    assert len(assets) == 1
    assert assets[0].url == "https://exemplo.com/bg/hero.jpg"
    assert assets[0].tipo == "background"


def test_normaliza_url_relativa():
    html = '<html><body><img src="imagens/logo.png"></body></html>'
    assets = extrair_assets(html, BASE)
    assert assets[0].url == "https://exemplo.com/imagens/logo.png"


def test_normaliza_url_absoluta_externa():
    html = '<html><body><img src="https://cdn.externo.com/icon.svg"></body></html>'
    assets = extrair_assets(html, BASE)
    assert assets[0].url == "https://cdn.externo.com/icon.svg"


def test_deduplicacao_urls_identicas():
    html = """
    <html><body>
      <img src="/logo.png">
      <img src="/logo.png">
    </body></html>
    """
    assets = extrair_assets(html, BASE)
    assert len(assets) == 1


def test_deduplicacao_relativa_e_absoluta():
    html = f"""
    <html><body>
      <img src="/logo.png">
      <img src="{BASE}/logo.png">
    </body></html>
    """
    assets = extrair_assets(html, BASE)
    assert len(assets) == 1


def test_filtra_extensao_invalida():
    html = '<html><body><img src="/doc.pdf"><img src="/script.js"></body></html>'
    assets = extrair_assets(html, BASE)
    assert assets == []


def test_extrai_multiplos_tipos():
    html = """
    <html>
    <head>
      <link rel="icon" href="/favicon.ico">
    </head>
    <body>
      <img src="/logo.png">
      <div style="background-image: url('/bg.jpg')"></div>
    </body>
    </html>
    """
    assets = extrair_assets(html, BASE)
    assert len(assets) == 3
    tipos = {a.tipo for a in assets}
    assert "icon" in tipos
    assert "image" in tipos
    assert "background" in tipos


def test_assets_tem_origem_correta():
    html = '<html><body><img src="/logo.png"></body></html>'
    assets = extrair_assets(html, BASE)
    assert assets[0].origem == BASE


def test_assets_caminho_local_vazio():
    html = '<html><body><img src="/logo.png"></body></html>'
    assets = extrair_assets(html, BASE)
    assert assets[0].caminho_local == ""
