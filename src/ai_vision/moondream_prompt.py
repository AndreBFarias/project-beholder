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

_TIPOS_VALIDOS = {"icon", "background", "logo", "vector", "photo", "ui_element", "other"}


def _cfg_ia() -> dict:
    """Retorna a seção IA de DEFAULTS no momento da chamada (ADR-02)."""
    return DEFAULTS["IA"]


def _base_url() -> str:
    return f"http://127.0.0.1:{_cfg_ia()['ollama_port']}"


def _timeout_analise() -> int:
    return _cfg_ia()["timeout_analise"]


def _resolver_modelo() -> str:
    """Resolve o nome do modelo a partir do tier configurado (lido dinamicamente)."""
    cfg = _cfg_ia()
    tier = cfg.get("modelo_tier", "low")
    modelos = cfg.get("modelos_disponiveis", {})
    if tier in modelos:
        return modelos[tier]["nome"]
    return cfg["modelo"]


PROMPT_CLASSIFICACAO = (
    "Você é um assistente que analisa imagens para um catálogo visual em português do Brasil.\n"
    "Responda SOMENTE em português do Brasil. Seja descritivo e específico.\n"
    "Formato obrigatório (mantenha as chaves em inglês, mas escreva os valores em PT-BR):\n"
    "type: icon OR background OR logo OR vector OR photo OR ui_element OR other\n"
    "description: duas frases em português descrevendo 1) o que a imagem mostra "
    "(elementos visuais concretos) e 2) estilo/uso provável (ex: 'estilo minimalista "
    "para interface mobile' ou 'fundo abstrato para landing page').\n"
    "tags: pelo menos 6 palavras-chave em português separadas por vírgula, "
    "cobrindo: tema, estilo visual, cores dominantes, elementos gráficos e contexto "
    "de uso (ex: 'engrenagem, configuração, minimalista, monocromático, interface, "
    "aplicativo')."
)

_FALLBACK: dict = {"tipo": "other", "descricao": "análise indisponível", "tags": []}

# Sprint 22.4 — heurística de detecção de inglês para acionar tradução fallback.
_ACENTOS_PTBR = "áéíóúâêîôûãõàçÁÉÍÓÚÂÊÎÔÛÃÕÀÇ"
_STOPWORDS_EN = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "with", "for", "of", "in", "on", "at",
    "by", "from", "this", "that", "these", "those", "and", "or", "but", "it", "its",
    "as", "into", "over", "under", "shows", "showing", "depicts", "depicting", "has",
    "have", "there",
})


def _parece_ingles(texto: str) -> bool:
    """Heurística: sem acentos + pelo menos 2 stopwords inglesas → provavelmente inglês."""
    if not texto:
        return False
    if any(c in _ACENTOS_PTBR for c in texto):
        return False
    palavras = re.findall(r"\b[a-zA-Z]+\b", texto.lower())
    if len(palavras) < 3:
        return False
    hits = sum(1 for p in palavras if p in _STOPWORDS_EN)
    return hits >= 2


def _traduzir_para_ptbr(texto: str) -> str:
    """Chama o próprio modelo Ollama pedindo tradução. Retorna texto original em caso de falha."""
    prompt = (
        "Traduza o texto a seguir para português do Brasil. "
        "Retorne APENAS a tradução, sem comentários, aspas ou explicações.\n\n"
        f"Texto:\n{texto}"
    )
    payload = {
        "model": _resolver_modelo(),
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": _cfg_ia().get("num_predict", 400), "temperature": 0.1},
    }
    try:
        with httpx.Client(timeout=_timeout_analise()) as client:
            resp = client.post(f"{_base_url()}/api/generate", json=payload)
            resp.raise_for_status()
            traduzido = resp.json().get("response", "").strip()
            # Remove aspas envolventes se o modelo devolver com elas
            if len(traduzido) > 2 and traduzido[0] in "\"'" and traduzido[-1] == traduzido[0]:
                traduzido = traduzido[1:-1].strip()
            return traduzido or texto
    except Exception:
        logger.exception("Falha na tradução fallback")
        return texto


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

    cfg = _cfg_ia()
    min_tags = cfg.get("min_tags_esperadas", 5)
    min_desc_chars = 30  # abaixo disso consideramos descrição pobre

    for tentativa, temperatura in enumerate([0.2, 0.5], start=1):
        payload = {
            "model": _resolver_modelo(),
            "prompt": PROMPT_CLASSIFICACAO,
            "images": [imagem_b64],
            "stream": False,
            "options": {
                "num_predict": cfg.get("num_predict", 400),
                "temperature": temperatura,
            },
        }

        try:
            with httpx.Client(timeout=_timeout_analise()) as client:
                resp = client.post(f"{_base_url()}/api/generate", json=payload)
                resp.raise_for_status()
                texto = resp.json().get("response", "")
                resultado = _parsear_resposta(texto)

                # Aceita quando temos tipo não-other E descrição decente E tags suficientes.
                tem_tipo = resultado.get("tipo") and resultado["tipo"] != "other"
                tem_desc = len(resultado.get("descricao", "")) >= min_desc_chars
                tem_tags = len(resultado.get("tags", [])) >= min_tags

                if tem_tipo and tem_desc and tem_tags:
                    return _aplicar_traducao_fallback(resultado)

                if tentativa == 1:
                    logger.info(
                        "Resposta pobre para %s (tipo=%s, desc=%d chars, tags=%d) — retry",
                        caminho,
                        resultado.get("tipo"),
                        len(resultado.get("descricao", "")),
                        len(resultado.get("tags", [])),
                    )
                    continue

                # Segunda tentativa: devolve o que conseguir, traduzindo se ainda estiver em inglês.
                return _aplicar_traducao_fallback(resultado)

        except httpx.HTTPError as exc:
            logger.error("Erro HTTP ao analisar %s: %s", caminho, exc)
            return _FALLBACK.copy()
        except Exception:
            logger.exception("Erro inesperado ao analisar %s", caminho)
            return _FALLBACK.copy()

    return _FALLBACK.copy()


def _aplicar_traducao_fallback(resultado: dict) -> dict:
    """Se descrição ainda parece inglês, chama o modelo pedindo tradução (Sprint 22.4)."""
    descricao = resultado.get("descricao", "")
    if descricao and _parece_ingles(descricao):
        logger.info("Descrição em inglês detectada — acionando tradução fallback")
        resultado["descricao"] = _traduzir_para_ptbr(descricao)
    return resultado


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
    """Parse de formato 'type: X / description: Y / tags: a, b, c'.

    Aceita descrições que se estendem por múltiplas linhas (vão até a próxima
    chave reconhecida ou fim de texto). Limites de descricao/tags lidos de
    DEFAULTS (Sprint 20).
    """
    cfg = _cfg_ia()
    max_desc = cfg.get("max_descricao_chars", 300)
    max_tags = cfg.get("max_tags", 10)

    tipo_match = re.search(r"(?:type|tipo)\s*:\s*(\w[\w_]*)", texto, re.IGNORECASE)
    # Descrição pode atravessar linhas até encontrar "tags:" ou fim do texto.
    desc_match = re.search(
        r"(?:description|descri[çc][ãa]o)\s*:\s*(.+?)(?=\n\s*tags?\s*:|\Z)",
        texto,
        re.IGNORECASE | re.DOTALL,
    )
    tags_match = re.search(
        r"tags?\s*:\s*(.+?)(?=\n\s*(?:type|tipo|description|descri[çc][ãa]o)\s*:|\Z)",
        texto,
        re.IGNORECASE | re.DOTALL,
    )

    if not tipo_match:
        return None

    tipo = tipo_match.group(1).lower().strip()
    if tipo not in _TIPOS_VALIDOS:
        tipo = "other"

    descricao = " ".join(desc_match.group(1).split()) if desc_match else ""
    tags_raw = " ".join(tags_match.group(1).split()) if tags_match else ""
    tags = [t.strip().strip("#").strip() for t in re.split(r"[,;]", tags_raw) if t.strip()]
    # Remove tags vazias e duplicatas preservando ordem
    vistas: set[str] = set()
    tags_limpas: list[str] = []
    for tag in tags:
        chave = tag.lower()
        if chave and chave not in vistas:
            vistas.add(chave)
            tags_limpas.append(tag)

    return {"tipo": tipo, "descricao": descricao[:max_desc], "tags": tags_limpas[:max_tags]}


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
