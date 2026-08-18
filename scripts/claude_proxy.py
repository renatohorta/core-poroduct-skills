#!/usr/bin/env python3
"""
claude_proxy.py — Proxy OpenAI-compatível que usa o Claude Code como LLM.

Permite que as crews CrewAI (cp-*) usem o Claude como LLM, sem precisar de
ANTHROPIC_API_KEY. O proxy expõe uma API OpenAI-compatível (/v1/chat/completions)
e delega cada chamada ao comando `claude -p` (que usa a autenticação OAuth do
Claude Code).

Uso:
  python scripts/claude_proxy.py --port 8080     # inicia o proxy
  python scripts/claude_proxy.py --test          # testa uma chamada

Depois, configure o .env das skills:
  LLM_MODEL=openai/claude-sonnet-4
  LLM_API_BASE=http://localhost:8080/v1
  LLM_API_KEY=qualquer-coisa   # o proxy ignora, mas o CrewAI exige
  LLM_PROVIDER=openai
"""

import argparse
import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_PORT = 8080
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
# Modelo padrão do Claude Code (pode ser sobrescrito via env)
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "")


def _call_claude(messages, model=""):
    """Chama o Claude Code via `claude -p` e retorna a resposta.

    messages: lista no formato OpenAI [{role, content}, ...]
    """
    # Monta o prompt: system + user messages
    system_parts = [m["content"] for m in messages if m.get("role") == "system"]
    user_parts = [m["content"] for m in messages if m.get("role") == "user"]
    system_prompt = "\n\n".join(system_parts)
    user_prompt = "\n\n".join(user_parts)

    cmd = [CLAUDE_BIN, "-p", "--output-format", "json"]
    if system_prompt:
        cmd += ["--system-prompt", system_prompt]
    # Só passa --model se for um modelo válido (não genérico como "claude")
    if model and model not in ("claude", "claude-sonnet-4", "claude-opus-4"):
        cmd += ["--model", model]
    cmd.append(user_prompt)

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            return {"error": f"claude falhou: {result.stderr[:500]}"}
        data = json.loads(result.stdout)
        return {"content": data.get("result", ""), "raw": data}
    except subprocess.TimeoutExpired:
        return {"error": "claude timeout após 300s"}
    except json.JSONDecodeError:
        return {"error": f"resposta não-JSON do claude: {result.stdout[:500]}"}
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════
# SERVIDOR HTTP (API OpenAI-compatível)
# ═══════════════════════════════════════════════════════════════════════════

class ClaudeProxyHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health" or self.path == "/v1/models":
            self._send_json(200, {"status": "ok", "models": [CLAUDE_MODEL or "claude"]})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self._send_json(404, {"error": "not found"})
            return

        # Lê o body
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON"})
            return

        messages = data.get("messages", [])
        model = data.get("model", "") or CLAUDE_MODEL

        # Chama o Claude
        result = _call_claude(messages, model)
        if "error" in result:
            self._send_json(500, {"error": result["error"]})
            return

        # Resposta no formato OpenAI
        response = {
            "id": "chatcmpl-claude-proxy",
            "object": "chat.completion",
            "created": 0,
            "model": model or "claude",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": result["content"]},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }
        self._send_json(200, response)

    def log_message(self, format, *args):
        # Log silencioso (ou com prefixo)
        print(f"[claude-proxy] {self.command} {self.path} — {args[0]}")


def test_call():
    """Testa uma chamada ao Claude via proxy."""
    print("🧪 Testando chamada ao Claude Code...")
    result = _call_claude(
        [{"role": "user", "content": "responda apenas: OK"}]
    )
    if "error" in result:
        print(f"❌ Erro: {result['error']}")
        return 1
    print(f"✅ Resposta: {result['content']}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="claude_proxy.py — Proxy OpenAI-compatível usando Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Exemplos:
  python scripts/claude_proxy.py --port 8080
  python scripts/claude_proxy.py --test
        """,
    )
    parser.add_argument("--port", "-p", type=int, default=DEFAULT_PORT,
                        help=f"Porta do proxy (default: {DEFAULT_PORT})")
    parser.add_argument("--test", action="store_true",
                        help="Testa uma chamada ao Claude e sai")
    args = parser.parse_args()

    if args.test:
        return test_call()

    print(f"🚀 Claude Proxy iniciado em http://localhost:{args.port}")
    print(f"   Endpoint: http://localhost:{args.port}/v1/chat/completions")
    print(f"   Claude bin: {CLAUDE_BIN}")
    print("   Pressione Ctrl+C para parar.\n")

    server = HTTPServer(("127.0.0.1", args.port), ClaudeProxyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹️  Proxy interrompido.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
