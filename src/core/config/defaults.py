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
    "Protocolo": {
        # Timeout máximo (segundos) para processar uma URL no lote do Protocolo
        "timeout_url": 300,
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
        # Limites de geração e parsing (Sprint 20 — descrições mais ricas):
        "num_predict": 400,  # tokens máximos por resposta (antes: 150 truncava demais)
        "max_descricao_chars": 300,  # limite no parser para a coluna descricao do CSV
        "max_tags": 10,  # limite no parser para a coluna tags do CSV
        "min_tags_esperadas": 5,  # abaixo disso considera resposta pobre e tenta retry
    },
    "Saida": {
        "diretorio_output": "output",
        "diretorio_data": "data/sessao_atual",
        "kmeans_cores": 4,
        "formato_zip": "beholder_{timestamp}.zip",
        "colunas_csv": "url_original,caminho_local,tipo,descricao,tags,paleta_hex,timestamp,site_origem",
        # Sprint 22: retenção automática de pacotes (zip) e CSVs no diretório output.
        # 0 desativa a poda. N > 0 mantém apenas os N mais recentes de cada tipo.
        "max_pacotes_retidos": 10,
    },
    "Espolio": {
        # Mapeamento de tipo (retornado pela IA) → nome da subpasta no ZIP (PT-BR).
        # Nomes acentuados são obrigatórios (GUIDE.md).
        "mapa_pastas": {
            "icon": "ícones",
            "logo": "ícones",
            "svg": "ícones",
            "vector": "ícones",
            "background": "fundos",
            "photo": "fundos",
            "ui_element": "outros",
            "other": "outros",
        },
        "pasta_fallback": "outros",
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
