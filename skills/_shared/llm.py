#!/usr/bin/env python3
"""
llm.py — Agent LLM resolution for the cp-* skills (self-contained).

The CrewAI skills need an `llm=` on the Agent() to avoid falling into the CrewAI
OpenAI default. This helper resolves the LLM of the AGENT where the skill is
being called, with a fallback to a local `.env`.

Resolution order (provider-agnostic):
  1. Agent env vars (Hermes/Claude): LLM_MODEL, LLM_API_KEY, LLM_API_BASE,
     LLM_TEMPERATURE, LLM_PROVIDER.
  2. `.env` at the project root (same convention as crewbotics-back).
  3. Per-provider key detection (GEMINI_API_KEY, OPENAI_API_KEY,
     ANTHROPIC_API_KEY, OLLAMA_API_KEY, etc.) + model mapping.
  4. Default: gemini/gemini-2.5-flash (no key → CrewAI falls into a stub/clear error).

Usage:
  from llm import build_crew_llm, get_llm_config
  llm = build_crew_llm()          # returns crewai.LLM or None
  cfg = get_llm_config()          # dict with model/api_key/api_base/temperature
"""

import os
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_MODEL = "gemini/gemini-2.5-flash"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TIMEOUT = 120

# Maps provider -> (key env var, model prefix)
PROVIDER_KEY_MAP = {
    "gemini": ("GEMINI_API_KEY", "gemini/"),
    "google": ("GEMINI_API_KEY", "gemini/"),
    "openai": ("OPENAI_API_KEY", "openai/"),
    "anthropic": ("ANTHROPIC_API_KEY", "anthropic/"),
    "claude": ("ANTHROPIC_API_KEY", "anthropic/"),
    "ollama": ("OLLAMA_API_KEY", "ollama/"),
    "ollama_chat": ("OLLAMA_API_KEY", "ollama_chat/"),
    "openrouter": ("OPENROUTER_API_KEY", "openrouter/"),
    "deepseek": ("DEEPSEEK_API_KEY", "deepseek/"),
    "groq": ("GROQ_API_KEY", "groq/"),
    "mistral": ("MISTRAL_API_KEY", "mistral/"),
    "cohere": ("COHERE_API_KEY", "cohere/"),
    "together": ("TOGETHER_API_KEY", "together/"),
    "xai": ("XAI_API_KEY", "xai/"),
    "grok": ("XAI_API_KEY", "xai/"),
}


def _load_dotenv(root: Path = None) -> dict:
    """Loads variables from a .env at the project root (no external dependency)."""
    base = Path(root) if root else Path.cwd()
    env_file = base / ".env"
    if not env_file.exists():
        return {}
    env = {}
    for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def _detect_provider_from_key(env: dict) -> str:
    """Detects the provider from the key available in the environment."""
    for provider, (key_var, _) in PROVIDER_KEY_MAP.items():
        if env.get(key_var):
            return provider
    return ""


def _normalize_model(model: str, provider: str) -> str:
    """Ensures the provider/model format (avoids CrewAI falling into the OpenAI default)."""
    if "/" in model:
        return model
    prefix = PROVIDER_KEY_MAP.get(provider, ("", ""))[1]
    if prefix:
        return prefix + model
    return model


def get_llm_config(root: Path = None) -> dict:
    """Returns the resolved LLM config (agent env > .env > detection > default)."""
    # 1. Agent env vars (Hermes/Claude)
    model = os.environ.get("LLM_MODEL", "")
    api_key = os.environ.get("LLM_API_KEY", "")
    api_base = os.environ.get("LLM_API_BASE", "")
    temperature = os.environ.get("LLM_TEMPERATURE", "")
    provider = os.environ.get("LLM_PROVIDER", "")

    # 2. Local .env
    dotenv = _load_dotenv(root)
    model = model or dotenv.get("LLM_MODEL", "")
    api_key = api_key or dotenv.get("LLM_API_KEY", "")
    api_base = api_base or dotenv.get("LLM_API_BASE", "")
    temperature = temperature or dotenv.get("LLM_TEMPERATURE", "")
    provider = provider or dotenv.get("LLM_PROVIDER", "")

    # 3. Per-provider key detection (if there is still no key)
    if not api_key:
        detected = _detect_provider_from_key({**os.environ, **dotenv})
        if detected:
            provider = provider or detected
            key_var = PROVIDER_KEY_MAP[detected][0]
            api_key = os.environ.get(key_var, "") or dotenv.get(key_var, "")

    # 4. Normalizes the model with the provider prefix
    if model and provider:
        model = _normalize_model(model, provider)

    # 5. Defaults
    model = model or DEFAULT_MODEL
    try:
        temperature = float(temperature) if temperature else DEFAULT_TEMPERATURE
    except ValueError:
        temperature = DEFAULT_TEMPERATURE

    return {
        "model": model,
        "api_key": api_key,
        "api_base": api_base,
        "temperature": temperature,
        "provider": provider,
        "configured": bool(api_key),
    }


def build_crew_llm(root: Path = None):
    """Builds a crewai.LLM from the resolved config.

    Returns None if crewai is not installed or if there is no configured key
    (the skill can then warn instead of falling into the OpenAI default).
    """
    cfg = get_llm_config(root)
    if not cfg["configured"]:
        return None

    try:
        from crewai import LLM
    except ImportError:
        return None

    kwargs = {
        "model": cfg["model"],
        "temperature": cfg["temperature"],
        "timeout": DEFAULT_TIMEOUT,
    }
    if cfg["api_key"]:
        kwargs["api_key"] = cfg["api_key"]
    if cfg["api_base"]:
        kwargs["base_url"] = cfg["api_base"]
    if cfg["provider"]:
        kwargs["provider"] = cfg["provider"]
        # When we pass an explicit provider= to CrewAI, the model must come WITHOUT
        # the provider prefix (e.g. 'gemini-2.5-flash', not 'gemini/gemini-2.5-flash').
        # With a prefix + explicit provider, CrewAI sends the wrong name to the API → 404.
        if "/" in kwargs["model"]:
            kwargs["model"] = kwargs["model"].split("/", 1)[1]

    try:
        return LLM(**kwargs)
    except Exception as e:
        print(f"  ⚠️  Failed to build LLM: {e}")
        return None


def require_crewai(exit_code: int = 3):
    """Ensures crewai is installed; otherwise exits with a clear message.

    Call AFTER parse_args(), so that `--help` keeps working without the lib.
    """
    try:
        import crewai  # noqa: F401
    except ImportError:
        print()
        print("[X] crewai not installed - required to run this skill.")
        print("    Install with:  pip install crewai")
        print("    (--help still works without the lib.)")
        sys.exit(exit_code)


def require_llm(root: Path = None, exit_code: int = 2):
    """Returns a configured crewai.LLM, or exits with an actionable message.

    Exists because `build_crew_llm()` returns None when there is no key: passing
    that None to the Agent makes CrewAI fall into the OpenAI default and fail later
    with `OPENAI_API_KEY is required`. Call it immediately before the
    `crew.kickoff()` - never on the `--dry-run` path, which must keep working
    without a credential.
    """
    llm = build_crew_llm(root)
    if llm is None:
        cfg = get_llm_config(root)
        print()
        print("[X] No LLM configured - this skill needs one to run.")
        print(f"    Resolved model: {cfg['model']} (no key)")
        print("    Configure one of the options:")
        print("      - Env vars: LLM_MODEL, LLM_API_KEY (and LLM_API_BASE if applicable)")
        print("      - .env file at the project root (see .env.example)")
        print("      - Provider key: GEMINI_API_KEY, OPENAI_API_KEY,")
        print("        ANTHROPIC_API_KEY, GROQ_API_KEY, ...")
        print("    To inspect the skill without an LLM, use --dry-run.")
        sys.exit(exit_code)
    return llm


def setup_console():
    """Forces UTF-8 on stdout/stderr.

    The Windows console uses cp1252 and breaks the skill with UnicodeEncodeError
    when printing emoji or box-drawing. `errors="replace"` ensures no exotic
    environment interrupts execution.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def get_agent_llm():
    """Returns the agent's LLM (Hermes/Claude) via CLI, if available.

    Uses `hermes -z` (Hermes) to delegate to the agent's LLM. Returns None if
    not possible.
    """
    hermes = os.environ.get("HERMES_BIN", "hermes")
    try:
        import subprocess
        r = subprocess.run(
            [hermes, "-z", "respond only with the word OK"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0 and r.stdout.strip():
            return {"mode": "hermes-cli", "command": hermes}
    except Exception:
        pass
    return None


if __name__ == "__main__":
    cfg = get_llm_config()
    print("=== Resolved LLM config ===")
    print(f"  model: {cfg['model']}")
    print(f"  api_key: {'<REDACTED>' if cfg['api_key'] else '(empty)'}")
    print(f"  api_base: {cfg['api_base'] or '(empty)'}")
    print(f"  temperature: {cfg['temperature']}")
    print(f"  provider: {cfg['provider'] or '(auto)'}")
    print(f"  configured: {cfg['configured']}")
