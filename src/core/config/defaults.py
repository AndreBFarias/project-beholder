"""
Fonte única de verdade para todos os valores default do Project Beholder.

ADR-02: Nenhum valor numérico ou string de configuração deve ser hardcoded
fora deste arquivo. Toda lógica de fallback aponta para cá.
"""

DEFAULTS: dict = {
    "Scraper": {
        "timeout": 30,
        "delay_min": 1.0,
        "delay_max": 3.0,
        "jitter": True,
        "max_retries": 3,
        "modo_furtivo": False,
        "max_assets_por_pagina": 200,
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    },
    "IA": {
        "ollama_port": 11435,
        "modelo": "moondream",
        "modelo_tier": "low",
        "modelos_disponiveis": {
            "low": {"nome": "moondream", "vram_gb": 1.7, "descricao": "Rápido, qualidade básica"},
            "medium": {"nome": "minicpm-v", "vram_gb": 2.5, "descricao": "Equilíbrio qualidade/velocidade"},
            "high": {"nome": "llava:7b", "vram_gb": 4.5, "descricao": "Melhor precisão, mais lento"},
        },
        "max_concurrent": 1,
        "timeout_analise": 60,
        "ollama_tmpdir": "data/ollama_tmp",
        "ollama_models": "models",
    },
    "Saida": {
        "diretorio_output": "output",
        "diretorio_data": "data/sessao_atual",
        "kmeans_cores": 4,
        "formato_zip": "beholder_{timestamp}.zip",
        "colunas_csv": "url_original,caminho_local,tipo,descricao,tags,paleta_hex,timestamp",
    },
    "Interface": {
        "tema": "dracula",
        "log_nivel": "INFO",
        "janela_largura": 1100,
        "janela_altura": 700,
    },
    "Fila": {
        "maxsize_scraper": 50,
        "maxsize_processada": 50,
    },
}
