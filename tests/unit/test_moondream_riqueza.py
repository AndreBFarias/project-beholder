"""
Testes de riqueza da resposta da IA (Sprint 20).

Valida:
- Prompt exige 2 frases e 6+ tags em PT-BR
- Parser aceita descrição multilinha (atravessa \\n até encontrar 'tags:')
- Parser remove tags duplicadas preservando ordem
- Limites max_descricao_chars e max_tags vêm de DEFAULTS
"""

import copy

import pytest

from src.ai_vision.moondream_prompt import (
    PROMPT_CLASSIFICACAO,
    _parse_chave_valor,
    _parsear_resposta,
)
from src.core.config.defaults import DEFAULTS


@pytest.fixture
def cfg_ia_backup():
    snap = copy.deepcopy(DEFAULTS["IA"])
    yield
    DEFAULTS["IA"].clear()
    DEFAULTS["IA"].update(copy.deepcopy(snap))


def test_prompt_pede_duas_frases():
    texto = PROMPT_CLASSIFICACAO.lower()
    assert "duas frases" in texto, "Prompt deve pedir 2 frases"


def test_prompt_pede_seis_tags():
    texto = PROMPT_CLASSIFICACAO.lower()
    assert "6" in texto or "seis" in texto, "Prompt deve pedir pelo menos 6 tags"


def test_prompt_menciona_estilo_e_cores():
    texto = PROMPT_CLASSIFICACAO.lower()
    assert "estilo" in texto, "Prompt deve pedir estilo visual"
    assert "cores" in texto, "Prompt deve pedir cores dominantes"


def test_parser_aceita_descricao_multilinha():
    resposta = (
        "type: icon\n"
        "descrição: um ícone de engrenagem estilizado em traço fino.\n"
        "Representa configurações de sistema em interfaces mobile minimalistas.\n"
        "tags: engrenagem, configuração, minimalista, monocromático, interface, aplicativo"
    )
    resultado = _parse_chave_valor(resposta)
    assert resultado is not None
    assert "engrenagem" in resultado["descricao"]
    assert "Representa configurações" in resultado["descricao"]
    assert len(resultado["tags"]) == 6


def test_parser_remove_tags_duplicadas():
    resposta = (
        "type: photo\n"
        "descrição: fotografia de paisagem ao pôr do sol.\n"
        "tags: pôr do sol, paisagem, PAISAGEM, céu, Céu, laranja"
    )
    resultado = _parse_chave_valor(resposta)
    # PAISAGEM/paisagem e Céu/céu são consideradas duplicatas (case-insensitive)
    tags_lower = [t.lower() for t in resultado["tags"]]
    assert len(tags_lower) == len(set(tags_lower)), "Tags duplicadas não foram removidas"


def test_parser_respeita_max_descricao_dinamico(cfg_ia_backup):
    DEFAULTS["IA"]["max_descricao_chars"] = 20
    resposta = (
        "type: icon\n"
        "descrição: uma descrição muito longa que deveria ser cortada no limite.\n"
        "tags: a, b, c"
    )
    resultado = _parse_chave_valor(resposta)
    assert len(resultado["descricao"]) == 20


def test_parser_respeita_max_tags_dinamico(cfg_ia_backup):
    DEFAULTS["IA"]["max_tags"] = 3
    resposta = (
        "type: icon\n"
        "descrição: teste.\n"
        "tags: a, b, c, d, e, f, g"
    )
    resultado = _parse_chave_valor(resposta)
    assert len(resultado["tags"]) == 3
    assert resultado["tags"] == ["a", "b", "c"]


def test_parser_descricao_longa_padrao():
    """Por padrão max_descricao_chars=300, então descrição rica cabe inteira."""
    descricao_longa = (
        "Uma ilustração detalhada representando uma engrenagem mecânica "
        "estilizada em tons de azul escuro e ciano. A composição usa "
        "linhas finas e preencheu áreas geométricas criando sensação de "
        "profundidade e tecnologia."
    )
    resposta = f"type: vector\ndescrição: {descricao_longa}\ntags: engrenagem, vetor, azul"
    resultado = _parse_chave_valor(resposta)
    # 300 chars é o default — texto tem ~260, deve caber inteiro
    assert descricao_longa[:100] in resultado["descricao"]
    assert len(resultado["descricao"]) >= 200


def test_parser_sem_tags_ainda_retorna():
    """Se não houver tags mas descrição for válida, ainda devolve resultado parcial."""
    resposta = "type: icon\ndescrição: ícone minimalista\ntags:"
    resultado = _parse_chave_valor(resposta)
    assert resultado is not None
    assert resultado["tipo"] == "icon"
    assert resultado["tags"] == []


def test_parsear_resposta_json_com_descricao_longa():
    texto = (
        '{"type": "photo", "description": "Fotografia ampla de uma paisagem costeira '
        'ao amanhecer, com tons rosados no céu e silhuetas de coqueiros à margem direita. '
        'Estilo cinematográfico, ideal para landing page de turismo.", '
        '"tags": ["paisagem", "amanhecer", "costa", "coqueiros", "rosa", "turismo"]}'
    )
    resultado = _parsear_resposta(texto)
    assert resultado["tipo"] == "photo"
    assert "cinematográfico" in resultado["descricao"]
    assert len(resultado["tags"]) == 6


# "Descrever é o primeiro ato de compreender." — Antoine de Saint-Exupéry
