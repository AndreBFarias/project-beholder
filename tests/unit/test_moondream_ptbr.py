"""
Testes do pipeline Moondream em PT-BR (Sprint 17).

Valida:
- PROMPT_CLASSIFICACAO contém instrução explícita para responder em português.
- Parser aceita respostas em PT-BR (descrição, descricao) e em inglês como fallback.
- Chaves de tipo permanecem em inglês (são enumeradas) — apenas descrição e tags
  viram PT-BR.
"""

import pytest

from src.ai_vision.moondream_prompt import (
    PROMPT_CLASSIFICACAO,
    _parse_chave_valor,
    _parsear_resposta,
)


def test_prompt_exige_portugues():
    """O prompt deve instruir explicitamente resposta em PT-BR."""
    texto = PROMPT_CLASSIFICACAO.lower()
    assert "portugu" in texto, "Prompt deve mencionar português"
    assert ("brazil" in texto) or ("brasil" in texto), "Prompt deve especificar PT-BR"


def test_parser_aceita_resposta_ptbr():
    """Resposta com 'descrição:' (acentuada) deve ser parseada."""
    resposta = (
        "type: icon\n"
        "descrição: ícone de engrenagem representando configuração\n"
        "tags: engrenagem, configuração, ajuste"
    )
    resultado = _parse_chave_valor(resposta)
    assert resultado is not None
    assert resultado["tipo"] == "icon"
    assert "configuração" in resultado["descricao"]
    assert "configuração" in resultado["tags"]


def test_parser_aceita_resposta_inglesa_como_fallback():
    """Quando o modelo ignora a instrução e volta em inglês, ainda parseamos."""
    resposta = (
        "type: background\n"
        "description: dark abstract background with purple tones\n"
        "tags: dark, abstract, purple"
    )
    resultado = _parse_chave_valor(resposta)
    assert resultado is not None
    assert resultado["tipo"] == "background"
    assert "dark" in resultado["descricao"]
    assert "purple" in resultado["tags"]


def test_parser_tipo_invalido_cai_para_other():
    """Tipo fora do enum conhecido vira 'other' (e não quebra)."""
    resposta = "type: banana\ndescription: fruta amarela\ntags: fruta"
    resultado = _parse_chave_valor(resposta)
    assert resultado is not None
    assert resultado["tipo"] == "other"


def test_parsear_resposta_formato_json():
    """_parsear_resposta aceita JSON direto e normaliza chaves inglesas."""
    texto = '{"type": "logo", "description": "logotipo da empresa", "tags": ["marca"]}'
    resultado = _parsear_resposta(texto)
    assert resultado["tipo"] == "logo"
    assert resultado["descricao"] == "logotipo da empresa"


def test_parsear_resposta_formato_livre_ptbr():
    """Resposta em texto livre com chaves PT-BR deve parsear."""
    texto = (
        "Esta é uma imagem.\n"
        "type: photo\n"
        "descrição: fotografia de paisagem noturna\n"
        "tags: paisagem, noite, urbano"
    )
    resultado = _parsear_resposta(texto)
    assert resultado["tipo"] == "photo"
    assert "paisagem" in resultado["descricao"]
    assert "noite" in resultado["tags"]


@pytest.mark.parametrize("tipo_ingles", ["icon", "background", "logo", "vector", "photo", "ui_element", "other"])
def test_tipos_enum_permanecem_ingleses(tipo_ingles):
    """Os tipos enumerados continuam em inglês — viraria quebra no pipeline."""
    resposta = f"type: {tipo_ingles}\ndescrição: teste\ntags: t"
    resultado = _parse_chave_valor(resposta)
    assert resultado["tipo"] == tipo_ingles


# "A língua é a pátria." — Fernando Pessoa
