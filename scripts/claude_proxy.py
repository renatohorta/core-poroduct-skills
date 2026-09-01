#!/usr/bin/env python3
"""
claude_proxy.py — OpenAI-compatible proxy that uses Claude Code as the LLM.

Lets the CrewAI crews (cp-*) use Claude as the LLM, without needing
ANTHROPIC_API_KEY. The proxy exposes an OpenAI-compatible API (/v1/chat/completions)
and delegates each call to the `claude -p` command (which uses the Claude Code
OAuth authentication).

Usage:
  python scripts/claude_proxy.py --port 8090     # starts the proxy
  python scripts/claude_proxy.py --test          # tests a call

Then configure the skills' .env:
  LLM_MODEL=openai/claude-sonnet-4
  LLM_API_BASE=http://localhost:8090/v1
  LLM_API_KEY=anything   # the proxy ignores it, but CrewAI requires it
  LLM_PROVIDER=openai
"""

import argparse
import json
import os
import hmac
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# DT-01: UTF-8 on stdout/stderr (the Windows console uses cp1252 and breaks the
# script with UnicodeEncodeError when printing emoji/box-drawing).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_PORT = 8090
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
# Claude Code default model (can be overridden via env)
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "")
# DT-04: optional token. The proxy delegates the Claude Code OAuth session, so
# any local process that reaches it consumes the user's quota. Without a token,
# it keeps the old behavior (only the 127.0.0.1 bind protects) and warns at
# startup; with a token, it requires `Authorization: Bearer ***
PROXY_TOKEN = os.environ.get("CLAUDE_PROXY_TOKEN", "")


def _call_claude(messages, model=""):
    """Calls Claude Code via `claude -p` and returns the response.

    messages: list in OpenAI format [{role, content}, ...]
    """
    # Builds the prompt: system + user messages
    system_parts = [m["content"] for m in messages if m.get("role") == "system"]
    user_parts = [m["content"] for m in messages if m.get("role") == "user"]
    system_prompt = "\n\n".join(system_parts)
    user_prompt = "\n\n".join(user_parts)

    cmd = [CLAUDE_BIN, "-p", "--output-format", "json"]
    if system_prompt:
        cmd += ["--system-prompt", system_prompt]
    # Only passes --model if it is a valid model (not generic like "claude")
    if model and model not in ("claude", "claude-sonnet-4", "claude-opus-4"):
        cmd += ["--model", model]
    cmd.append(user_prompt)

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            return {"error": f"claude failed: {result.stderr[:500]}"}
        data = json.loads(result.stdout)
        return {"content": data.get("result", ""), "raw": data}
    except subprocess.TimeoutExpired:
        return {"error": "claude timeout after 300s"}
    except json.JSONDecodeError:
        return {"error": f"non-JSON response from claude: {result.stdout[:500]}"}
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════
# HTTP SERVER (OpenAI-compatible API)
# ═══════════════════════════════════════════════════════════════════════════

class ClaudeProxyHandler(BaseHTTPRequestHandler):
    def _authorized(self) -> bool:
        """DT-04: validates the Bearer token when CLAUDE_PROXY_TOKEN is set.

        Without a configured token, allows (compatibility with current use).
        """
        if not PROXY_TOKEN:
            return True
        header = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not header.startswith(prefix):
            return False
        return hmac.compare_digest(header[len(prefix):].strip(), PROXY_TOKEN)

    def _send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # /health stays open on purpose, for a credential-free liveness check.
        if self.path != "/health" and not self._authorized():
            self._send_json(401, {"error": "unauthorized: invalid or missing Bearer token"})
            return
        if self.path == "/health" or self.path == "/v1/models":
            self._send_json(200, {"status": "ok", "models": [CLAUDE_MODEL or "claude"]})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if not self._authorized():
            self._send_json(401, {"error": "unauthorized: invalid or missing Bearer token"})
            return
        if self.path != "/v1/chat/completions":
            self._send_json(404, {"error": "not found"})
            return

        # Reads the body
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON"})
            return

        messages = data.get("messages", [])
        model = data.get("model", "") or CLAUDE_MODEL

        # Calls Claude
        result = _call_claude(messages, model)
        if "error" in result:
            self._send_json(500, {"error": result["error"]})
            return

        # Response in OpenAI format
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
        # Silent log (or with a prefix)
        print(f"[claude-proxy] {self.command} {self.path} — {args[0]}")


def test_call():
    """Tests a call to Claude via the proxy."""
    print("🧪 Testing a call to Claude Code...")
    result = _call_claude(
        [{"role": "user", "content": "respond only: OK"}]
    )
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return 1
    print(f"✅ Response: {result['content']}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="claude_proxy.py — OpenAI-compatible proxy using Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python scripts/claude_proxy.py --port 8090
  python scripts/claude_proxy.py --test
        """,
    )
    parser.add_argument("--port", "-p", type=int, default=DEFAULT_PORT,
                        help=f"Proxy port (default: {DEFAULT_PORT})")
    parser.add_argument("--test", action="store_true",
                        help="Tests a call to Claude and exits")
    args = parser.parse_args()

    if args.test:
        return test_call()

    print(f"🚀 Claude Proxy started at http://localhost:{args.port}")
    print(f"   Endpoint: http://localhost:{args.port}/v1/chat/completions")
    print(f"   Claude bin: {CLAUDE_BIN}")
    print("   Press Ctrl+C to stop.\n")

    server = HTTPServer(("127.0.0.1", args.port), ClaudeProxyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹️  Proxy stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
