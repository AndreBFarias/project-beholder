"""
Interface HTTP com o Ollama/Moondream para análise de imagens.

ADR-01 (bridges): Este é o ÚNICO ponto de contato com a API Ollama.
Nenhum outro módulo deve chamar /api/generate diretamente.
"""

import base64
import json
import logging
import re
from io import BytesIO
from pathlib import Path

import httpx

from src.core.config.defaults import DEFAULTS

logger = logging.getLogger("beholder.ai_vision.moondream_prompt")

_TIPOS_VALIDOS = {"icon", "background", "logo", "vector", "photo", "ui_element", "other"}

# Formatos raster aceitos diretamente pelo decoder nativo do Ollama (libllamacpp).
# SVG e ICO crasham o subprocesso (signal during cgo) e precisam ser rasterizados antes.
_RASTER_NATIVO = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
_RASTER_LARGURA_PADRAO = 512


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
    "Você é um analista visual. Examine a imagem e responda em português do Brasil "
    "no formato abaixo. Não repita estas instruções, não escreva exemplos, "
    "apenas preencha os três campos.\n\n"
    "tipo: icon ou logo ou background ou photo ou vector ou ui_element ou other\n"
    "descricao: duas frases descrevendo o que aparece e o estilo visual "
    "(cores, traço, composição).\n"
    "tags: 6 a 8 palavras-chave em português separadas por vírgula."
)

# Prompts atômicos do fallback: cada um é uma pergunta única para a IA quando
# o prompt estruturado retorna lixo. Modelos pequenos (moondream) respondem
# melhor a perguntas curtas em inglês — traduzimos a saída em seguida.
PROMPT_DESCRICAO_SIMPLES = "Describe this image in one or two short sentences."
PROMPT_TAGS_SIMPLES = "List 6 to 8 short visual keywords for this image, separated by commas. Do not write sentences."

_FALLBACK: dict = {"tipo": "other", "descricao": "análise indisponível", "tags": []}

# Heurística para inferir tipo a partir do nome do arquivo / URL quando o
# modelo devolve "other" ou resposta vazia. Mantemos as chaves em inglês para
# casar com _TIPOS_VALIDOS.
_HEURISTICA_TIPO: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("icon", ("favicon", "icon", "ícone", "/icons/", "icon-")),
    ("logo", ("logo", "brand", "marca", "wordmark")),
    ("background", ("background", "fundo", "hero", "banner", "cover", "bg-", "bg_")),
    ("photo", ("photo", "foto", "picture", "img-", "hero-")),
)

# Sprint 22.4 — heurística de detecção de inglês para acionar tradução fallback.
_ACENTOS_PTBR = "áéíóúâêîôûãõàçÁÉÍÓÚÂÊÎÔÛÃÕÀÇ"
_STOPWORDS_EN = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "with",
        "for",
        "of",
        "in",
        "on",
        "at",
        "by",
        "from",
        "this",
        "that",
        "these",
        "those",
        "and",
        "or",
        "but",
        "it",
        "its",
        "as",
        "into",
        "over",
        "under",
        "shows",
        "showing",
        "depicts",
        "depicting",
        "has",
        "have",
        "there",
    }
)


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


def _inferir_tipo_por_arquivo(caminho: Path) -> str:
    """Heurística de tipo a partir do nome do arquivo (e extensão)."""
    nome = caminho.name.lower()
    for tipo, palavras in _HEURISTICA_TIPO:
        if any(p in nome for p in palavras):
            return tipo
    if caminho.suffix.lower() == ".svg":
        return "vector"
    return "other"


def _perguntar_imagem(imagem_b64: str, pergunta: str, temperatura: float = 0.2) -> str:
    """Envia uma única pergunta sobre a imagem e devolve a resposta crua.

    Usado pelo fallback decomposto quando o prompt estruturado retorna lixo.
    Falhas devolvem string vazia (o chamador decide o próximo passo).
    """
    payload = {
        "model": _resolver_modelo(),
        "prompt": pergunta,
        "images": [imagem_b64],
        "stream": False,
        "options": {
            "num_predict": _cfg_ia().get("num_predict", 400),
            "temperature": temperatura,
        },
    }
    try:
        with httpx.Client(timeout=_timeout_analise()) as client:
            resp = client.post(f"{_base_url()}/api/generate", json=payload)
            resp.raise_for_status()
            return (resp.json().get("response") or "").strip()
    except Exception as exc:
        logger.warning("Falha em pergunta isolada (%.40s...): %s", pergunta, exc)
        return ""


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


def _normalizar_svg_dimensoes(svg_texto: str) -> str:
    """Força width/height válidos no `<svg>` raiz (sprites têm width="0").

    Substitui qualquer width/height existente por 512 e adiciona se ausentes.
    Não toca em `<symbol>` ou `<g>` internos.
    """
    largura = str(_RASTER_LARGURA_PADRAO)
    # Atua só no primeiro `<svg ...>`
    match = re.search(r"<svg\b[^>]*>", svg_texto, flags=re.IGNORECASE)
    if not match:
        return svg_texto
    tag = match.group(0)
    tag_nova = re.sub(r'\s(width|height)\s*=\s*"[^"]*"', "", tag, flags=re.IGNORECASE)
    tag_nova = tag_nova[:-1] + f' width="{largura}" height="{largura}">'
    return svg_texto[: match.start()] + tag_nova + svg_texto[match.end() :]


def _ler_imagem_como_raster(caminho: Path) -> bytes | None:
    """Lê o arquivo e devolve bytes raster que o Ollama consiga decodificar.

    SVG é rasterizado via cairosvg; ICO é convertido via Pillow (frame de maior
    resolução). Demais formatos raster passam diretos. Retorna None se a
    conversão falhar (chamador usa _FALLBACK).
    """
    suf = caminho.suffix.lower()
    if suf in _RASTER_NATIVO:
        try:
            return caminho.read_bytes()
        except OSError as exc:
            logger.error("Falha ao ler imagem %s: %s", caminho, exc)
            return None

    if suf == ".svg":
        try:
            import cairosvg
        except ImportError:
            logger.warning("cairosvg ausente — pulando SVG %s", caminho)
            return None
        # Algumas SVGs (sprites de symbol) têm width=0 height=0; precisamos
        # reescrever atributos antes de rasterizar para o cairosvg conseguir
        # determinar o tamanho.
        try:
            svg_texto = caminho.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            logger.warning("Falha ao ler SVG %s: %s", caminho, exc)
            return None
        ultima_falha: Exception | None = None
        for kwargs in (
            {"output_width": _RASTER_LARGURA_PADRAO},
            {"parent_width": _RASTER_LARGURA_PADRAO, "parent_height": _RASTER_LARGURA_PADRAO},
            {"bytestring": _normalizar_svg_dimensoes(svg_texto).encode("utf-8")},
        ):
            try:
                if "bytestring" in kwargs:
                    return cairosvg.svg2png(**kwargs)
                return cairosvg.svg2png(url=str(caminho), **kwargs)
            except Exception as exc:
                ultima_falha = exc
        logger.warning("Falha ao rasterizar SVG %s: %s", caminho, ultima_falha)
        return None

    if suf == ".ico":
        try:
            from PIL import Image
        except ImportError:
            logger.warning("Pillow ausente — pulando ICO %s", caminho)
            return None
        try:
            with Image.open(caminho) as img:
                if hasattr(img, "ico") and getattr(img.ico, "sizes", None):
                    maior = max(img.ico.sizes(), key=lambda wh: wh[0] * wh[1])
                    img.size = maior
                quadro = img.convert("RGBA")
                buf = BytesIO()
                quadro.save(buf, format="PNG")
                return buf.getvalue()
        except Exception as exc:
            logger.warning("Falha ao converter ICO %s: %s", caminho, exc)
            return None

    try:
        return caminho.read_bytes()
    except OSError as exc:
        logger.error("Falha ao ler imagem %s: %s", caminho, exc)
        return None


def analisar_imagem(caminho: str | Path) -> dict:
    """
    Envia a imagem para o modelo de visão via Ollama e retorna a análise.

    Estratégia em camadas para resiliência independente do tamanho do modelo:
      1. Prompt estruturado único (PROMPT_CLASSIFICACAO).
      2. Se resposta vier pobre/parcial, decompõe em duas perguntas atômicas
         curtas (PROMPT_DESCRICAO_SIMPLES + PROMPT_TAGS_SIMPLES) que modelos
         pequenos como moondream conseguem responder.
      3. Tipo inferido por heurística sobre o nome do arquivo quando o modelo
         devolver "other" ou vazio.

    Args:
        caminho: Caminho local do arquivo de imagem.

    Returns:
        Dict com chaves: tipo (str), descricao (str), tags (list[str]).
    """
    caminho_path = Path(caminho)
    bytes_imagem = _ler_imagem_como_raster(caminho_path)
    if bytes_imagem is None:
        resultado = _FALLBACK.copy()
        resultado["tipo"] = _inferir_tipo_por_arquivo(caminho_path)
        return resultado
    imagem_b64 = base64.b64encode(bytes_imagem).decode()

    resultado = _tentar_estruturado(imagem_b64, caminho_path)
    if not _resposta_satisfatoria(resultado):
        complementar = _tentar_decomposto(imagem_b64, caminho_path)
        resultado = _combinar_resultados(resultado, complementar)

    # Override de tipo via heurística quando IA não conseguiu classificar.
    if resultado.get("tipo") in (None, "", "other"):
        resultado["tipo"] = _inferir_tipo_por_arquivo(caminho_path)

    return _aplicar_traducao_fallback(resultado)


def _resposta_satisfatoria(resultado: dict) -> bool:
    """True quando o resultado tem tipo não-other + descrição razoável + tags."""
    cfg = _cfg_ia()
    min_tags = cfg.get("min_tags_esperadas", 5)
    min_desc_chars = 30
    tem_tipo = resultado.get("tipo") and resultado["tipo"] != "other"
    tem_desc = len(resultado.get("descricao", "")) >= min_desc_chars
    tem_tags = len(resultado.get("tags", [])) >= min_tags
    return tem_tipo and tem_desc and tem_tags


def _tentar_estruturado(imagem_b64: str, caminho: Path) -> dict:
    """Faz uma chamada com PROMPT_CLASSIFICACAO. Retorna fallback se quebrar."""
    cfg = _cfg_ia()
    payload = {
        "model": _resolver_modelo(),
        "prompt": PROMPT_CLASSIFICACAO,
        "images": [imagem_b64],
        "stream": False,
        "options": {"num_predict": cfg.get("num_predict", 400), "temperature": 0.2},
    }
    try:
        with httpx.Client(timeout=_timeout_analise()) as client:
            resp = client.post(f"{_base_url()}/api/generate", json=payload)
            resp.raise_for_status()
            texto = (resp.json().get("response") or "").strip()
            if not texto:
                logger.info("Estruturado vazio para %s — entrando em fallback", caminho)
                return _FALLBACK.copy()
            return _parsear_resposta(texto)
    except httpx.HTTPError as exc:
        logger.error("Erro HTTP no prompt estruturado para %s: %s", caminho, exc)
        return _FALLBACK.copy()
    except Exception:
        logger.exception("Erro inesperado no prompt estruturado para %s", caminho)
        return _FALLBACK.copy()


def _tentar_decomposto(imagem_b64: str, caminho: Path) -> dict:
    """Faz duas perguntas atômicas (descrição + tags) e devolve o que vier.

    Funciona melhor em modelos pequenos que falham com prompts estruturados.
    Tipo fica como "other" — o chamador aplica heurística por nome depois.
    """
    cfg = _cfg_ia()
    max_desc = cfg.get("max_descricao_chars", 300)
    max_tags = cfg.get("max_tags", 10)

    bruto_desc = _perguntar_imagem(imagem_b64, PROMPT_DESCRICAO_SIMPLES, temperatura=0.1)
    bruto_tags = _perguntar_imagem(imagem_b64, PROMPT_TAGS_SIMPLES, temperatura=0.1)

    descricao = " ".join(bruto_desc.split())[:max_desc]
    tags_partidas = [t.strip().strip("#").strip() for t in re.split(r"[,;\n]", bruto_tags)]
    vistas: set[str] = set()
    tags: list[str] = []
    for tag in tags_partidas:
        if not tag or len(tag) > 40:  # filtra frases longas que não são tag
            continue
        chave = tag.lower()
        if chave in vistas:
            continue
        vistas.add(chave)
        tags.append(tag)
        if len(tags) >= max_tags:
            break

    logger.info(
        "Fallback decomposto para %s: desc=%d chars, tags=%d",
        caminho,
        len(descricao),
        len(tags),
    )
    return {"tipo": "other", "descricao": descricao, "tags": tags}


def _combinar_resultados(principal: dict, complementar: dict) -> dict:
    """Preenche campos vazios/curtos do principal com os do complementar."""
    cfg = _cfg_ia()
    min_desc_chars = 30
    min_tags = cfg.get("min_tags_esperadas", 5)

    combinado = principal.copy()
    if len(combinado.get("descricao", "")) < min_desc_chars and complementar.get("descricao"):
        combinado["descricao"] = complementar["descricao"]
    if len(combinado.get("tags", [])) < min_tags and complementar.get("tags"):
        combinado["tags"] = complementar["tags"]
    if combinado.get("tipo") in (None, "", "other") and complementar.get("tipo") not in (None, "", "other"):
        combinado["tipo"] = complementar["tipo"]
    return combinado


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
