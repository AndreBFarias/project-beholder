"""
Interface HTTP com o Ollama/Moondream para análise de imagens.

ADR-01 (bridges): Este é o ÚNICO ponto de contato com a API Ollama.
Nenhum outro módulo deve chamar /api/generate diretamente.
"""

import base64
import json
import logging
import re
from pathlib import Path

import httpx

from src.core.config.defaults import DEFAULTS

logger = logging.getLogger("beholder.ai_vision.moondream_prompt")

_cfg = DEFAULTS["IA"]
_BASE_URL = f"http://127.0.0.1:{_cfg['ollama_port']}"
_TIMEOUT = _cfg["timeout_analise"]


def _resolver_modelo() -> str:
    """Resolve o nome do modelo a partir do tier configurado."""
    tier = _cfg.get("modelo_tier", "low")
    modelos = _cfg.get("modelos_disponiveis", {})
    if tier in modelos:
        return modelos[tier]["nome"]
    return _cfg["modelo"]


PROMPT_CLASSIFICACAO = (
    "Analyze this image and respond ONLY with valid JSON, no other text: "
    '{"tipo": "icon|background|logo|vector|photo|ui_element|other", '
    '"descricao": "brief description in up to 20 words", '
    '"tags": ["tag1", "tag2", "tag3"]}'
)

_FALLBACK: dict = {"tipo": "other", "descricao": "análise indisponível", "tags": []}


def analisar_imagem(caminho: str | Path) -> dict:
    """
    Envia a imagem para Moondream via Ollama e retorna o JSON analisado.

    Args:
        caminho: Caminho local do arquivo de imagem.

    Returns:
        Dict com chaves: tipo (str), descricao (str), tags (list[str]).
        Em caso de qualquer falha, retorna fallback com tipo="other".
    """
    try:
        imagem_b64 = base64.b64encode(Path(caminho).read_bytes()).decode()
    except OSError as exc:
        logger.error("Falha ao ler imagem %s: %s", caminho, exc)
        return _FALLBACK.copy()

    payload = {
        "model": _resolver_modelo(),
        "prompt": PROMPT_CLASSIFICACAO,
        "images": [imagem_b64],
        "stream": False,
        "options": {"num_predict": 200},
    }

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(f"{_BASE_URL}/api/generate", json=payload)
            resp.raise_for_status()
            texto = resp.json().get("response", "")
            return _parsear_resposta(texto)
    except httpx.HTTPError as exc:
        logger.error("Erro HTTP ao analisar %s: %s", caminho, exc)
        return _FALLBACK.copy()
    except Exception:
        logger.exception("Erro inesperado ao analisar %s", caminho)
        return _FALLBACK.copy()


def _parsear_resposta(texto: str) -> dict:
    """Extrai JSON da resposta do modelo. Tolerante a texto extra ao redor."""
    # Parse direto
    try:
        return json.loads(texto.strip())
    except json.JSONDecodeError:
        pass

    # Extrai primeiro bloco {...} encontrado
    match = re.search(r"\{.*?\}", texto, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.warning("Resposta não parseável: %.100s", texto)
    return _FALLBACK.copy()
