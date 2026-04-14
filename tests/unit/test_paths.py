"""
Testes de resolução de caminhos via Path(__file__).

Verificam que LOGS_DIR, CHECKPOINT_PATH e o binário do Ollama
apontam para dentro do diretório do projeto, independente do CWD.
"""

from pathlib import Path


def test_logs_dir_dentro_do_projeto():
    from src.core.logging_config import LOGS_DIR

    projeto = Path(__file__).resolve().parent.parent.parent
    assert str(LOGS_DIR).startswith(str(projeto)), f"LOGS_DIR ({LOGS_DIR}) deve estar dentro de {projeto}"


def test_checkpoint_path_dentro_do_projeto():
    from src.core.checkpoint import CHECKPOINT_PATH

    projeto = Path(__file__).resolve().parent.parent.parent
    assert str(CHECKPOINT_PATH).startswith(str(projeto)), (
        f"CHECKPOINT_PATH ({CHECKPOINT_PATH}) deve estar dentro de {projeto}"
    )


def test_logs_dir_nao_depende_do_cwd(monkeypatch, tmp_path):
    """LOGS_DIR deve ser estável mesmo com CWD diferente."""
    import importlib

    import src.core.logging_config as mod

    monkeypatch.chdir(tmp_path)
    importlib.reload(mod)

    assert "logs" in str(mod.LOGS_DIR)
    assert str(tmp_path) not in str(mod.LOGS_DIR) or str(mod.LOGS_DIR).endswith("Project_Beholder/logs")
