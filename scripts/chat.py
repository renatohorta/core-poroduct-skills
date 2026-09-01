#!/usr/bin/env python3
"""
chat.py — Direct conversation with the cp-* skills using the LLM via .env.

Lets you trigger any cp-* skill interactively, using the LLM configured in the
.env (same convention as crewbotics-back: LLM_MODEL, GEMINI_API_KEY/OPENAI_API_KEY/etc.).
Does not depend on the agent (Hermes/Claude).

Usage:
  python chat.py                          # lists the available skills
  python chat.py cp-requirements            # talks to the skill
  python chat.py cp-requirements "briefing" # runs with a direct briefing
  python chat.py --skill cp-requirements --prompt "scheduling system"
  python chat.py --list                   # lists skills
"""

import argparse
import importlib.util
import os
import sys
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

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

# Skills that accept a positional briefing (direct conversation)
CHAT_SKILLS = {
    "cp-requirements": "briefing",
    "cp-architecture": "briefing",
    "cp-implementation": "briefing",
    "cp-testing": "briefing",
    "cp-security": "briefing",
    "cp-devops": "briefing",
    "cp-documentation": "briefing",
    "cp-quality": "briefing",
    "cp-bug-fix": "bug_description",
    "cp-competitive-analysis": "context",
    "cp-maintenance": "description",
    "cp-goal-loop": "goal",
    "cp-orchestrator": "briefing",
}


def _load_dotenv(root: Path = None) -> dict:
    """Loads variables from a .env at the project root."""
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


def list_skills():
    """Lists the skills available for conversation."""
    print("=== cp-* skills available for conversation ===")
    for name, arg in CHAT_SKILLS.items():
        run_py = SKILLS_DIR / name / "scripts" / "run.py"
        status = "✅" if run_py.exists() else "❌"
        print(f"  {status} {name} (arg: {arg})")
    print("\nUsage: python chat.py <skill> \"<briefing>\"")
    print("     python chat.py cp-requirements \"scheduling system\"")


def _resolve_python():
    """Resolves the Python interpreter that has crewai installed.

    Priority:
      1. Env var CP_SKILLS_PYTHON (explicit)
      2. .venv/Scripts/python.exe in the current directory or parents
      3. sys.executable (fallback)
    """
    explicit = os.environ.get("CP_SKILLS_PYTHON")
    if explicit and Path(explicit).exists():
        return explicit

    # Looks for .venv in cwd and parent directories
    cwd = Path.cwd()
    for base in [cwd] + list(cwd.parents[:4]):
        for venv in [base / ".venv", base / "venv"]:
            py = venv / "Scripts" / "python.exe"
            if py.exists():
                # Confirms it has crewai
                import subprocess
                r = subprocess.run([str(py), "-c", "import crewai"],
                                   capture_output=True, text=True)
                if r.returncode == 0:
                    return str(py)
    return sys.executable


def run_skill(skill: str, prompt: str, extra_args: list = None):
    """Runs a cp-* skill with the provided briefing."""
    run_py = SKILLS_DIR / skill / "scripts" / "run.py"
    if not run_py.exists():
        print(f"❌ Skill '{skill}' not found at {run_py}")
        return 1

    # Loads the .env and injects it into the environment
    dotenv = _load_dotenv()
    for k, v in dotenv.items():
        os.environ.setdefault(k, v)

    # Resolves the Python with crewai
    python = _resolve_python()

    # Builds the command
    cmd = [python, str(run_py)]
    if prompt:
        cmd.append(prompt)
    if extra_args:
        cmd.extend(extra_args)

    print(f"🚀 Running {skill} with the .env LLM...")
    print(f"   Python: {python}")
    print(f"   Command: {' '.join(cmd)}\n")

    import subprocess
    result = subprocess.run(cmd, cwd=str(SKILLS_DIR.parent))
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="chat.py — Direct conversation with the cp-* skills via .env",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python chat.py --list
  python chat.py cp-requirements "scheduling system for clinics"
  python chat.py --skill cp-requirements --prompt "scheduling system"
  python chat.py cp-bug-fix "the /login endpoint returns 500"
        """,
    )
    parser.add_argument("skill", nargs="?", help="Skill name (e.g. cp-requirements)")
    parser.add_argument("prompt", nargs="?", help="Briefing/prompt for the skill")
    parser.add_argument("--skill", dest="skill_flag", help="Skill name (alternative)")
    parser.add_argument("--prompt", dest="prompt_flag", help="Briefing (alternative)")
    parser.add_argument("--list", "-l", action="store_true", help="Lists the skills")
    parser.add_argument("--extra", nargs="*", default=[], help="Extra args for the skill")
    # parse_known_args: unknown flags (e.g. --dry-run) are captured and
    # forwarded to the skill, instead of argparse rejecting them.
    args, unknown = parser.parse_known_args()

    if args.list:
        list_skills()
        return 0

    skill = args.skill or args.skill_flag
    prompt = args.prompt or args.prompt_flag

    if not skill:
        list_skills()
        return 0

    if skill not in CHAT_SKILLS:
        print(f"❌ Skill '{skill}' does not support direct conversation.")
        print("   Available:", ", ".join(CHAT_SKILLS.keys()))
        return 1

    # Combines --extra with unknown flags (e.g. --dry-run)
    extra = list(args.extra) + list(unknown)
    return run_skill(skill, prompt, extra)


if __name__ == "__main__":
    sys.exit(main())
