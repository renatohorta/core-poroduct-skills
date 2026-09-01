"""DT-04 — Optional authentication of claude_proxy.

The proxy delegates to the Claude Code OAuth session, so whoever reaches the port
consumes the user's quota. The 127.0.0.1 bind protects from the network, but not
from other local processes. `CLAUDE_PROXY_TOKEN` closes that gap without breaking
those who already use the proxy without a token.

The tests exercise only the authorization layer — none call `claude -p`.
"""
import importlib.util

import pytest

from conftest import REPO_ROOT

PROXY_PY = REPO_ROOT / "scripts" / "claude_proxy.py"


def load_proxy(monkeypatch, token=""):
    """Reloads the module with CLAUDE_PROXY_TOKEN set (read at import)."""
    monkeypatch.setenv("CLAUDE_PROXY_TOKEN", token)
    spec = importlib.util.spec_from_file_location(f"claude_proxy_{token or 'none'}", PROXY_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeHandler:
    """Handler with only what is needed to exercise `_authorized`."""

    def __init__(self, handler_cls, headers):
        self.headers = headers
        self._authorized = handler_cls._authorized.__get__(self)


def authorized(mod, headers):
    return FakeHandler(mod.ClaudeProxyHandler, headers)._authorized()


def test_without_configured_token_allows(monkeypatch):
    """Compatibility: without CLAUDE_PROXY_TOKEN, the proxy accepts as before."""
    mod = load_proxy(monkeypatch, "")
    assert authorized(mod, {}) is True
    assert authorized(mod, {"Authorization": "Bearer anything"}) is True


def test_with_token_requires_correct_bearer(monkeypatch):
    mod = load_proxy(monkeypatch, "secret-123")
    assert authorized(mod, {"Authorization": "Bearer secret-123"}) is True


@pytest.mark.parametrize("headers", [
    {},                                          # no header
    {"Authorization": ""},                       # empty header
    {"Authorization": "Bearer wrong"},           # wrong token
    {"Authorization": "secret-123"},             # without the Bearer prefix
    {"Authorization": "Basic secret-123"},        # wrong scheme
    {"Authorization": "Bearer secret-1234"},      # correct token prefix
    {"Authorization": "Bearer secret-12"},       # truncated token
])
def test_with_token_rejects_invalid_credential(monkeypatch, headers):
    mod = load_proxy(monkeypatch, "secret-123")
    assert authorized(mod, headers) is False


def test_default_port_aligned_with_documentation(monkeypatch):
    """DOC-01: README and .env.example instruct 8090; the code must agree."""
    mod = load_proxy(monkeypatch, "")
    assert mod.DEFAULT_PORT == 8090

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "8080" not in readme.replace("frontends on 8080", ""), (
        "README still cites 8080 outside the conflict note")


def test_proxy_listens_only_on_localhost():
    """The proxy can never listen on 0.0.0.0: it exposes the OAuth session on the network."""
    source = PROXY_PY.read_text(encoding="utf-8")
    assert '"127.0.0.1"' in source
    assert "0.0.0.0" not in source
