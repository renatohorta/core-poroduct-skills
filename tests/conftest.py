"""Shared fixtures of the suite.

The skills never call an LLM (ADR-0012): the agent running a skill is the LLM.
The scripts are deterministic — they print work packets, validate the agent's
documents and write `.context/` — so every behavior is testable as-is.
"""
import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
# The RUP (rup-*) skills live directly under skills/ (plus the _shared helpers).
SKILLS_DIR = REPO_ROOT / "skills"
ORCHESTRATOR = "rup-orchestrator"

# Let tests import the shared helpers (`from _shared import context`).
if str(SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(SKILLS_DIR))

# Exit codes (see skills/_shared/rup.py)
EXIT_OK = 0
EXIT_USAGE = 1
EXIT_CONTEXT_NOT_WRITABLE = 4
EXIT_NEEDS_CONSENT = 5


def skill_names():
    """Names of the RUP (rup-*) skills present in the repository."""
    return sorted(d.name for d in SKILLS_DIR.glob("rup-*")
                  if (d / "scripts" / "run.py").is_file())


def discipline_names():
    return [s for s in skill_names() if s != ORCHESTRATOR]


def skill_script(name: str) -> Path:
    return SKILLS_DIR / name / "scripts" / "run.py"


def load_skill(name: str):
    """Import a skill's run.py as a module (its main() is guarded)."""
    spec = importlib.util.spec_from_file_location(f"skill_{name.replace('-', '_')}",
                                                  skill_script(name))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def authorize(context_dir) -> Path:
    """Write a valid `.rup-standard` marker (creating the dir if needed)."""
    from datetime import datetime
    context_dir = Path(context_dir)
    context_dir.mkdir(parents=True, exist_ok=True)
    marker = context_dir / ".rup-standard"
    marker.write_text("version: 1\nauthorized_by: tests\n"
                      f"authorized_at: {datetime.now().isoformat(timespec='seconds')}\n",
                      encoding="utf-8")
    return marker


def full_document(spec) -> str:
    """A document with one `## <Artifact>` section per required artifact."""
    parts = []
    for agent in spec["agents"]:
        parts.append(f"# {agent['role']}\n")
        for artifact in agent["artifacts"]:
            parts.append(f"## {artifact}\n\nContent of {artifact}.\n")
    return "\n".join(parts)


@pytest.fixture(scope="session")
def clean_env(tmp_path_factory):
    """Environment with UTF-8 stdout and a throwaway RUP_CONTEXT_DIR.

    The skills write `.context/` mandatorily; a test must never write into this
    repository's own `.context/`.
    """
    env = {k: v for k, v in os.environ.items() if k != "RUP_CONTEXT_DIR"}
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["RUP_CONTEXT_DIR"] = str(tmp_path_factory.mktemp("session-context") / ".context")
    authorize(env["RUP_CONTEXT_DIR"])
    return env


@pytest.fixture
def ctx_env(clean_env, tmp_path):
    """clean_env with a per-test .context/ (returned in env["RUP_CONTEXT_DIR"])."""
    env = dict(clean_env)
    env["RUP_CONTEXT_DIR"] = str(tmp_path / "project" / ".context")
    authorize(env["RUP_CONTEXT_DIR"])
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
    of install.sh on Windows.
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
