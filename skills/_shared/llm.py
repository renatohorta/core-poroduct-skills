#!/usr/bin/env python3
"""
llm.py — Resolução do LLM do agente para as skills cp-* (self-contained).

As skills CrewAI precisam de um `llm=` nos Agent() para não caírem no default
OpenAI do CrewAI. Este helper resolve o LLM do AGENTE onde a skill está sendo
chamada, com fallback para um `.env` local.

Ordem de resolução (provider-agnostic):
  1. Env vars do agente (Hermes/Claude): LLM_MODEL, LLM_API_KEY, LLM_API_BASE,
     LLM_TEMPERATURE, LLM_PROVIDER.
  2. `.env` na raiz do projeto (mesma convenção do crewbotics-back).
  3. Detecção de chave por provider (GEMINI_API_KEY, OPENAI_API_KEY,
     ANTHROPIC_API_KEY, OLLAMA_API_KEY, etc.) + mapeamento do modelo.
  4. Default: gemini/gemini-2.5-flash (sem chave → CrewAI cai em stub/erro claro).

Uso:
  from llm import build_crew_llm, get_llm_config
  llm = build_crew_llm()          # retorna crewai.LLM ou None
  cfg = get_llm_config()          # dict com model/api_key/api_base/temperature
"""

import os
import sys
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_MODEL = "gemini/gemini-2.5-flash"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TIMEOUT = 120

# Mapeia provider -> (env var da chave, prefixo do modelo)
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
    """Carrega variáveis de um .env na raiz do projeto (sem dependência externa)."""
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
    """Detecta o provider a partir da chave disponível no ambiente."""
    for provider, (key_var, _) in PROVIDER_KEY_MAP.items():
        if env.get(key_var):
            return provider
    return ""


def _normalize_model(model: str, provider: str) -> str:
    """Garante o formato provider/model (evita o CrewAI cair no default OpenAI)."""
    if "/" in model:
        return model
    prefix = PROVIDER_KEY_MAP.get(provider, ("", ""))[1]
    if prefix:
        return prefix + model
    return model


def get_llm_config(root: Path = None) -> dict:
    """Retorna a config de LLM resolvida (env do agente > .env > detecção > default)."""
    # 1. Env vars do agente (Hermes/Claude)
    model = os.environ.get("LLM_MODEL", "")
    api_key = os.environ.get("LLM_API_KEY", "")
    api_base = os.environ.get("LLM_API_BASE", "")
    temperature = os.environ.get("LLM_TEMPERATURE", "")
    provider = os.environ.get("LLM_PROVIDER", "")

    # 2. .env local
    dotenv = _load_dotenv(root)
    model = model or dotenv.get("LLM_MODEL", "")
    api_key = api_key or dotenv.get("LLM_API_KEY", "")
    api_base = api_base or dotenv.get("LLM_API_BASE", "")
    temperature = temperature or dotenv.get("LLM_TEMPERATURE", "")
    provider = provider or dotenv.get("LLM_PROVIDER", "")

    # 3. Detecção de chave por provider (se ainda não há chave)
    if not api_key:
        detected = _detect_provider_from_key({**os.environ, **dotenv})
        if detected:
            provider = provider or detected
            key_var = PROVIDER_KEY_MAP[detected][0]
            api_key = os.environ.get(key_var, "") or dotenv.get(key_var, "")

    # 4. Normaliza o modelo com o prefixo do provider
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
    """Constrói um crewai.LLM a partir da config resolvida.

    Retorna None se o crewai não estiver instalado ou se não houver chave
    configurada (a skill pode então avisar em vez de cair no default OpenAI).
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
        # Quando passamos provider= explícito ao CrewAI, o modelo deve vir SEM
        # o prefixo do provider (ex: 'gemini-2.5-flash', não 'gemini/gemini-2.5-flash').
        # Com prefixo + provider explícito, o CrewAI envia o nome errado à API → 404.
        if "/" in kwargs["model"]:
            kwargs["model"] = kwargs["model"].split("/", 1)[1]

    try:
        return LLM(**kwargs)
    except Exception as e:
        print(f"  ⚠️  Falha ao construir LLM: {e}")
        return None


def get_agent_llm():
    """Retorna o LLM do agente (Hermes/Claude) via CLI, se disponível.

    Usa `hermes -z` (Hermes) para delegar ao LLM do agente. Retorna None se
    não for possível.
    """
    hermes = os.environ.get("HERMES_BIN", "hermes")
    try:
        import subprocess
        r = subprocess.run(
            [hermes, "-z", "responda apenas com a palavra OK"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0 and r.stdout.strip():
            return {"mode": "hermes-cli", "command": hermes}
    except Exception:
        pass
    return None


if __name__ == "__main__":
    cfg = get_llm_config()
    print("=== Config de LLM resolvida ===")
    print(f"  model: {cfg['model']}")
    print(f"  api_key: {'<REDACTED>' if cfg['api_key'] else '(vazio)'}")
    print(f"  api_base: {cfg['api_base'] or '(vazio)'}")
    print(f"  temperature: {cfg['temperature']}")
    print(f"  provider: {cfg['provider'] or '(auto)'}")
    print(f"  configured: {cfg['configured']}")
