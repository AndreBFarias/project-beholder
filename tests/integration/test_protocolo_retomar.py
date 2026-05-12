"""
Testes de integração — RETOMAR SESSÃO do Protocolo (Sprint 22.5).

Valida o ciclo completo do checkpoint:
- Salvar estado → carregar → recompor ListStore via `_on_retomar_sessao`.
- URLs concluídas/pendentes/erro aparecem com o status correto.
- Botão RETOMAR começa desabilitado quando não há checkpoint.
"""

import gi

gi.require_version("Gtk", "4.0")

import pytest  # noqa: E402

import src.core.checkpoint as ckpt  # noqa: E402
from src.core.checkpoint import EstadoCheckpoint  # noqa: E402


@pytest.fixture
def ckpt_path_tmp(tmp_path, monkeypatch):
    caminho = tmp_path / "checkpoint_test" / ".checkpoint.json"
    monkeypatch.setattr(ckpt, "CHECKPOINT_PATH", caminho)
    yield caminho
    if caminho.exists():
        caminho.unlink()


@pytest.mark.integration
def test_botao_retomar_desabilitado_sem_checkpoint(ckpt_path_tmp):
    from src.gui.pages.protocolo import ProtocoloPage

    page = ProtocoloPage()
    assert not page._btn_retomar.get_sensitive(), "Sem checkpoint salvo, botão RETOMAR deve iniciar desabilitado"


@pytest.mark.integration
def test_retomar_sessao_recompoe_listastore(ckpt_path_tmp):
    from src.gui.pages.protocolo import ProtocoloPage

    estado = EstadoCheckpoint(
        urls_pendentes=["https://pendente1.com", "https://pendente2.com"],
        urls_concluidas=["https://concluida.com"],
        urls_com_erro=["https://erro.com"],
        url_atual="https://atual.com",
        timestamp="2026-04-17T12:00:00",
    )
    ckpt.salvar(estado)

    page = ProtocoloPage()
    page._on_retomar_sessao(page._btn_retomar)

    # ListStore deve conter 1 concluída + 1 erro + 1 atual + 2 pendentes = 5
    linhas = [(row[0], row[1]) for row in page._store]
    assert len(linhas) == 5, f"Esperadas 5 linhas, veio {len(linhas)}: {linhas}"

    urls = [url for url, _ in linhas]
    assert "https://concluida.com" in urls
    assert "https://erro.com" in urls
    assert "https://atual.com" in urls
    assert "https://pendente1.com" in urls
    assert "https://pendente2.com" in urls

    # Status correto
    status_por_url = dict(linhas)
    assert status_por_url["https://concluida.com"] == "concluída"
    assert status_por_url["https://erro.com"] == "erro"
    assert status_por_url["https://atual.com"] == "pendente"
    assert status_por_url["https://pendente1.com"] == "pendente"


@pytest.mark.integration
def test_retomar_sem_checkpoint_mostra_aviso(ckpt_path_tmp):
    from src.gui.pages.protocolo import ProtocoloPage

    page = ProtocoloPage()
    # Força o botão habilitado só para verificar o caminho do handler
    page._btn_retomar.set_sensitive(True)
    page._on_retomar_sessao(page._btn_retomar)

    texto = page._label_status_lote.get_label()
    assert "Nenhum checkpoint" in texto or "AVISO" in texto


@pytest.mark.integration
def test_salvar_e_remover_checkpoint_ciclo_completo(ckpt_path_tmp):
    estado = EstadoCheckpoint(
        urls_pendentes=["x"],
        urls_concluidas=[],
        urls_com_erro=[],
        url_atual=None,
        timestamp="",
    )
    ckpt.salvar(estado)
    assert ckpt.existe()

    carregado = ckpt.carregar()
    assert carregado is not None
    assert carregado.urls_pendentes == ["x"]

    ckpt.remover()
    assert not ckpt.existe()


# "Quem persiste completa — quem começa já venceu metade." — provérbio
