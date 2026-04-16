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

_TIPOS_VALIDOS = {"icon", "background", "logo", "vector", "photo", "ui_element", "other"}


def _resolver_modelo() -> str:
    """Resolve o nome do modelo a partir do tier configurado."""
    tier = _cfg.get("modelo_tier", "low")
    modelos = _cfg.get("modelos_disponiveis", {})
    if tier in modelos:
        return modelos[tier]["nome"]
    return _cfg["modelo"]


PROMPT_CLASSIFICACAO = (
    "What is this image? Answer with exactly this format:\n"
    "type: icon OR background OR logo OR vector OR photo OR ui_element OR other\n"
    "description: one short sentence\n"
    "tags: word1, word2, word3"
)

_FALLBACK: dict = {"tipo": "other", "descricao": "análise indisponível", "tags": []}


def analisar_imagem(caminho: str | Path) -> dict:
    """
    Envia a imagem para o modelo de visão via Ollama e retorna a análise.

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

    for tentativa, temperatura in enumerate([0.1, 0.3], start=1):
        payload = {
            "model": _resolver_modelo(),
            "prompt": PROMPT_CLASSIFICACAO,
            "images": [imagem_b64],
            "stream": False,
            "options": {"num_predict": 150, "temperature": temperatura},
        }

        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.post(f"{_BASE_URL}/api/generate", json=payload)
                resp.raise_for_status()
                texto = resp.json().get("response", "")
                resultado = _parsear_resposta(texto)

                if resultado != _FALLBACK and resultado.get("tipo") != "other":
                    return resultado

                if tentativa == 1:
                    logger.info("Primeira tentativa retornou fallback para %s — retry", caminho)
                    continue

                return resultado

        except httpx.HTTPError as exc:
            logger.error("Erro HTTP ao analisar %s: %s", caminho, exc)
            return _FALLBACK.copy()
        except Exception:
            logger.exception("Erro inesperado ao analisar %s", caminho)
            return _FALLBACK.copy()

    return _FALLBACK.copy()


def _parsear_resposta(texto: str) -> dict:
    """Extrai dados estruturados da resposta do modelo. Tolerante a formatos variados."""
    # Tentativa 1: JSON direto
    try:
        resultado = json.loads(texto.strip())
        if _validar_resultado(resultado):
            return resultado
    except json.JSONDecodeError:
        pass

    # Tentativa 2: extrair primeiro bloco {...}
    match = re.search(r"\{[^}]+\}", texto, re.DOTALL)
    if match:
        try:
            resultado = json.loads(match.group())
            if _validar_resultado(resultado):
                return resultado
        except json.JSONDecodeError:
            pass

    # Tentativa 3: parse chave-valor (type:, description:, tags:)
    resultado = _parse_chave_valor(texto)
    if resultado:
        return resultado

    logger.warning("Resposta não parseável: %.200s", texto)
    return _FALLBACK.copy()


def _parse_chave_valor(texto: str) -> dict | None:
    """Parse de formato 'type: X / description: Y / tags: a, b, c'."""
    tipo_match = re.search(r"(?:type|tipo)\s*:\s*(\w[\w_]*)", texto, re.IGNORECASE)
    desc_match = re.search(r"(?:description|descri[çc][ãa]o)\s*:\s*(.+?)(?:\n|$)", texto, re.IGNORECASE)
    tags_match = re.search(r"tags?\s*:\s*(.+?)(?:\n|$)", texto, re.IGNORECASE)

    if not tipo_match:
        return None

    tipo = tipo_match.group(1).lower().strip()
    if tipo not in _TIPOS_VALIDOS:
        tipo = "other"

    descricao = desc_match.group(1).strip() if desc_match else ""
    tags_raw = tags_match.group(1).strip() if tags_match else ""
    tags = [t.strip().strip("#").strip() for t in re.split(r"[,;]", tags_raw) if t.strip()]

    return {"tipo": tipo, "descricao": descricao[:100], "tags": tags[:5]}


def _validar_resultado(resultado: dict) -> bool:
    """Verifica se o resultado tem os campos mínimos esperados."""
    if not isinstance(resultado, dict):
        return False
    # Normalizar chave "type" (inglês) para "tipo" (padrão interno)
    if "type" in resultado and "tipo" not in resultado:
        resultado["tipo"] = resultado.pop("type")
    if "description" in resultado and "descricao" not in resultado:
        resultado["descricao"] = resultado.pop("description")
    tipo = str(resultado.get("tipo", "")).lower()
    if tipo in _TIPOS_VALIDOS:
        resultado["tipo"] = tipo
        return True
    return bool(resultado.get("descricao"))


# "A razão é, e deve ser apenas, escrava das paixões." — David Hume
