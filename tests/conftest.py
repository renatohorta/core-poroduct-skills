"""Shared fixtures of the suite.

Principle: **no test calls an LLM**. LLM tests are expensive, slow and
non-deterministic, and do not catch the bugs that actually occur here — which
are about CLI contract and error handling. Every test runs with a credential-free
environment (see `clean_env`), ensuring the suite passes in CI without secrets.
"""
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

# Every variable capable of configuring an LLM — removed in all tests.
LLM_ENV_VARS = (
    "LLM_MODEL", "LLM_API_KEY", "LLM_API_BASE", "LLM_TEMPERATURE", "LLM_PROVIDER",
    "GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_API_KEY",
    "OPENROUTER_API_KEY", "DEEPSEEK_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY",
    "COHERE_API_KEY", "TOGETHER_API_KEY", "XAI_API_KEY",
)

# Exit codes standardized by the skills (see .context/docs/04-quality-qa.md)
EXIT_OK = 0
EXIT_NO_LLM = 2
EXIT_NO_CREWAI = 3


def skill_names():
    """Names of the cp-* skills present in the repository."""
    return sorted(d.name for d in SKILLS_DIR.glob("cp-*") if (d / "scripts" / "run.py").is_file())


def skill_script(name: str) -> Path:
    return SKILLS_DIR / name / "scripts" / "run.py"


@pytest.fixture(scope="session")
def clean_env():
    """Environment without any LLM credential, with UTF-8 stdout."""
    env = {k: v for k, v in os.environ.items() if k not in LLM_ENV_VARS}
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


@pytest.fixture(scope="session")
def python_cmd():
    """Interpreter used to run the skills — the same one that runs pytest."""
    return sys.executable


@pytest.fixture(scope="session")
def bash_cmd():
    """A bash that actually works, or skip.

    On Windows, `bash` on the PATH resolves to the WSL relay, which fails
    intermittently with `execvpe(/bin/bash) failed`. Git Bash is the real target
    of install.sh — see skills/cp-orchestrator/references/windows-wsl-bash-relay-workaround.md
    """
    import shutil
    import subprocess

    candidates = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        shutil.which("bash"),
    ]
    for cmd in candidates:
        if not cmd or not Path(cmd).exists():
            continue
        try:
            r = subprocess.run([cmd, "--version"], capture_output=True,
                               text=True, timeout=30)
            if r.returncode == 0 and "GNU bash" in r.stdout:
                return cmd
        except Exception:
            continue
    pytest.skip("no usable bash found (Git Bash missing)")
