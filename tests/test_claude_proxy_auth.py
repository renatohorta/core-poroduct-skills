"""DT-04 — Autenticação opcional do claude_proxy.

O proxy delega à sessão OAuth do Claude Code, então quem alcança a porta consome
a cota do usuário. O bind em 127.0.0.1 protege da rede, mas não de outros
processos locais. `CLAUDE_PROXY_TOKEN` fecha essa brecha sem quebrar quem já usa
o proxy sem token.

Os testes exercitam só a camada de autorização — nenhum chama `claude -p`.
"""
import importlib.util

import pytest

from conftest import REPO_ROOT

PROXY_PY = REPO_ROOT / "scripts" / "claude_proxy.py"


def carrega_proxy(monkeypatch, token=""):
    """Recarrega o módulo com CLAUDE_PROXY_TOKEN definido (lido no import)."""
    monkeypatch.setenv("CLAUDE_PROXY_TOKEN", token)
    spec = importlib.util.spec_from_file_location(f"claude_proxy_{token or 'sem'}", PROXY_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class HandlerFalso:
    """Handler com só o necessário para exercitar `_authorized`."""

    def __init__(self, handler_cls, headers):
        self.headers = headers
        self._authorized = handler_cls._authorized.__get__(self)


def autorizado(mod, headers):
    return HandlerFalso(mod.ClaudeProxyHandler, headers)._authorized()


def test_sem_token_configurado_libera(monkeypatch):
    """Compatibilidade: sem CLAUDE_PROXY_TOKEN, o proxy aceita como antes."""
    mod = carrega_proxy(monkeypatch, "")
    assert autorizado(mod, {}) is True
    assert autorizado(mod, {"Authorization": "Bearer qualquer-coisa"}) is True


def test_com_token_exige_bearer_correto(monkeypatch):
    mod = carrega_proxy(monkeypatch, "segredo-123")
    assert autorizado(mod, {"Authorization": "Bearer segredo-123"}) is True


@pytest.mark.parametrize("headers", [
    {},                                          # sem header
    {"Authorization": ""},                       # header vazio
    {"Authorization": "Bearer errado"},          # token errado
    {"Authorization": "segredo-123"},            # sem o prefixo Bearer
    {"Authorization": "Basic segredo-123"},      # esquema errado
    {"Authorization": "Bearer segredo-1234"},    # prefixo do token correto
    {"Authorization": "Bearer segredo-12"},      # token truncado
])
def test_com_token_rejeita_credencial_invalida(monkeypatch, headers):
    mod = carrega_proxy(monkeypatch, "segredo-123")
    assert autorizado(mod, headers) is False


def test_porta_default_alinhada_com_a_documentacao(monkeypatch):
    """DOC-01: README e .env.example instruem 8090; o código precisa concordar."""
    mod = carrega_proxy(monkeypatch, "")
    assert mod.DEFAULT_PORT == 8090

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "8080" not in readme.replace("frontends na 8080", ""), (
        "README ainda cita 8080 fora da nota de conflito")


def test_proxy_escuta_apenas_em_localhost():
    """O proxy nunca pode escutar em 0.0.0.0: expõe a sessão OAuth na rede."""
    fonte = PROXY_PY.read_text(encoding="utf-8")
    assert '"127.0.0.1"' in fonte
    assert "0.0.0.0" not in fonte
