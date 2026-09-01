"""Repository hygiene — portability and secrets.

Two invariants the README promises and only a test keeps honest:
  - **Portability**: zero hardcoded OS/machine paths and zero fixed personal values.
  - **Secrets outside the repository**: no committed keys.
"""
import re
import subprocess

import pytest

from conftest import REPO_ROOT

# Committed extensions worth inspecting.
EXTENSIONS = ("*.py", "*.sh", "*.md", "*.txt", "*.yml", "*.yaml", "*.example")

# Ignored directories (not committed or irrelevant).
IGNORE = {".git", ".venv", "venv", "__pycache__", "outputs", ".pytest_cache", "node_modules"}

# Machine/user paths that cannot be hardcoded.
# Case-SENSITIVE on purpose: the references enumerate env vars like
# "USERPROFILE/HOME/LOCALAPPDATA", which would match /home/ without case distinction.
PATH_PATTERNS = [
    re.compile(r"[Cc]:[\\/]+Users[\\/]+[A-Za-z]"),   # Windows home
    re.compile(r"/c/Users/[A-Za-z]"),                # Windows home via git-bash
    re.compile(r"/home/[a-z][a-z0-9_-]*/"),          # Linux home
    re.compile(r"/Users/[a-z][a-z0-9_-]*/"),         # macOS home
]

# API key formats of real providers.
SECRET_PATTERNS = [
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}"), "OpenAI key"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"), "Anthropic key"),
    (re.compile(r"\bAIza[A-Za-z0-9_-]{30,}"), "Google/Gemini key"),
    (re.compile(r"\bghp_[A-Za-z0-9]{30,}"), "GitHub token"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
]


def committed_files():
    """Files tracked by git, filtered by extension."""
    r = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                       cwd=str(REPO_ROOT), encoding="utf-8", errors="replace")
    if r.returncode != 0:
        pytest.skip("git unavailable")
    for line in r.stdout.splitlines():
        path = REPO_ROOT / line.strip()
        if not path.is_file():
            continue
        if any(part in IGNORE for part in path.parts):
            continue
        if path.suffix in {".py", ".sh", ".md", ".txt", ".yml", ".yaml", ".example"}:
            yield path


def test_no_committed_secret():
    """No API key can be in a git-tracked file."""
    findings = []
    for path in committed_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern, label in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append(f"{path.relative_to(REPO_ROOT)}: {label}")
    assert not findings, "committed secret:\n  " + "\n  ".join(findings)


# Only EXECUTABLE files enter the portability check.
#
# Markdown is deliberately left out. The `references/` are reports of real
# incidents — "the backend started from C:\Users\...\PycharmProjects\crewbotics-back, an
# old clone" — where the concrete path IS the information; generalizing would destroy the
# diagnostic value. The README promise ("the skills are portable, paths use
# env var + relative default") is about the code, and that is what this test sustains.
EXECUTABLE_EXTENSIONS = {".py", ".sh"}


def test_no_hardcoded_machine_path():
    """Portability: in code, paths come from env var + relative default.

    The tests are the deliberate exception — they need to locate the host's Git Bash.
    """
    findings = []
    for path in committed_files():
        rel = path.relative_to(REPO_ROOT)
        if rel.parts[0] == "tests" or path.suffix not in EXECUTABLE_EXTENSIONS:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in PATH_PATTERNS:
            for m in pattern.finditer(text):
                findings.append(f"{rel}: {m.group(0)!r}")
    assert not findings, "hardcoded machine path:\n  " + "\n  ".join(findings)


def test_env_not_committed():
    """`.env` holds a credential and can never be tracked — only `.env.example`."""
    r = subprocess.run(["git", "ls-files", ".env"], capture_output=True, text=True,
                       cwd=str(REPO_ROOT), encoding="utf-8", errors="replace")
    assert not r.stdout.strip(), ".env is committed — remove it with `git rm --cached .env`"
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore


def test_env_example_has_no_real_value():
    """`.env.example` is a template: the key variables are empty or commented."""
    example = REPO_ROOT / ".env.example"
    if not example.exists():
        pytest.skip(".env.example missing")
    suspects = []
    for n, line in enumerate(example.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if "KEY" not in key.upper() and "TOKEN" not in key.upper():
            continue
        value = value.strip().strip('"').strip("'")
        # Obvious placeholders are acceptable.
        if value and not re.fullmatch(r"[<{].*[>}]|your[-_].*|xxx+|\.\.\.|change[-_]?me",
                                      value, re.I):
            suspects.append(f"line {n}: {key.strip()}={value[:12]}...")
    assert not suspects, ".env.example with a real value:\n  " + "\n  ".join(suspects)
