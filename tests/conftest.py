"""Fixtures compartilhadas da suíte.

Princípio: **nenhum teste chama LLM**. Testes de LLM são caros, lentos e
não-determinísticos, e não pegam os bugs que de fato ocorrem aqui — que são de
contrato CLI e de tratamento de erro. Todo teste roda com o ambiente limpo de
credenciais (ver `clean_env`), garantindo que a suíte passe em CI sem segredos.
"""
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

# Toda variável capaz de configurar um LLM — removida em todos os testes.
LLM_ENV_VARS = (
    "LLM_MODEL", "LLM_API_KEY", "LLM_API_BASE", "LLM_TEMPERATURE", "LLM_PROVIDER",
    "GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_API_KEY",
    "OPENROUTER_API_KEY", "DEEPSEEK_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY",
    "COHERE_API_KEY", "TOGETHER_API_KEY", "XAI_API_KEY",
)

# Códigos de saída padronizados pelas skills (ver .context/docs/04-qualidade-qa.md)
EXIT_OK = 0
EXIT_NO_LLM = 2
EXIT_NO_CREWAI = 3


def skill_names():
    """Nomes das skills cp-* presentes no repositório."""
    return sorted(d.name for d in SKILLS_DIR.glob("cp-*") if (d / "scripts" / "run.py").is_file())


def skill_script(name: str) -> Path:
    return SKILLS_DIR / name / "scripts" / "run.py"


@pytest.fixture(scope="session")
def clean_env():
    """Ambiente sem nenhuma credencial de LLM, com stdout em UTF-8."""
    env = {k: v for k, v in os.environ.items() if k not in LLM_ENV_VARS}
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


@pytest.fixture(scope="session")
def python_cmd():
    """Interpretador usado para rodar as skills — o mesmo que roda o pytest."""
    return sys.executable


@pytest.fixture(scope="session")
def bash_cmd():
    """Um bash que realmente funciona, ou skip.

    No Windows, `bash` no PATH resolve para o relay do WSL, que falha de forma
    intermitente com `execvpe(/bin/bash) failed`. Git Bash e o alvo real do
    install.sh — ver skills/cp-orquestrador/references/windows-wsl-bash-relay-workaround.md
    """
    import shutil
    import subprocess

    candidatos = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        shutil.which("bash"),
    ]
    for cmd in candidatos:
        if not cmd or not Path(cmd).exists():
            continue
        try:
            r = subprocess.run([cmd, "--version"], capture_output=True,
                               text=True, timeout=30)
            if r.returncode == 0 and "GNU bash" in r.stdout:
                return cmd
        except Exception:
            continue
    pytest.skip("nenhum bash utilizavel encontrado (Git Bash ausente)")
