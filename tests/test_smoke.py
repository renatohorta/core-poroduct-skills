"""DT-02 — Smoke tests of the cp-* skills.

Verifies the minimum every skill must guarantee, without calling an LLM:
  - `--help` always works (even without crewai installed)
  - `--dry-run` builds the crew without requiring a credential
  - the absence of a credential fails with code 2 and an actionable message
  - the absence of crewai fails with code 3 and an actionable message
"""
import subprocess
import sys
import tempfile

import pytest

from conftest import (EXIT_NO_CREWAI, EXIT_NO_LLM, EXIT_OK, REPO_ROOT,
                      skill_names, skill_script)

SKILLS = skill_names()

# Minimum briefing accepted by each skill, per its own CLI contract.
# See .context/docs/02-architecture.md (the `invoke` metadata).
BRIEFING_ARGS = {
    "cp-goal-loop": ["--goal", "test goal"],
    "cp-agile": [],
    "cp-software-spec": ["--init"],
}
DEFAULT_BRIEFING = ["test briefing"]

# Skills that do not use an LLM: they are pure Python and run fully without a credential.
NO_LLM_SKILLS = {"cp-agile", "cp-software-spec"}


def briefing_for(skill: str, tmp_path=None):
    if skill == "cp-software-spec":
        return ["--init", "--dir", str(tmp_path or tempfile.mkdtemp())]
    return BRIEFING_ARGS.get(skill, DEFAULT_BRIEFING)


def run_skill(skill, args, env, python_cmd, timeout=120):
    return subprocess.run(
        [python_cmd, str(skill_script(skill))] + args,
        capture_output=True, text=True, timeout=timeout,
        cwd=str(REPO_ROOT), env=env, encoding="utf-8", errors="replace",
    )


@pytest.mark.parametrize("skill", SKILLS)
def test_help_always_works(skill, clean_env, python_cmd):
    """`--help` must work in every skill, including without crewai (DT-07).

    Regression: before DT-07, 12 of the 15 skills imported crewai at the top of
    the module and died with ModuleNotFoundError before argparse.
    """
    r = run_skill(skill, ["--help"], clean_env, python_cmd)
    assert r.returncode == EXIT_OK, f"--help failed:\n{r.stdout}\n{r.stderr}"
    assert "usage:" in r.stdout.lower()


@pytest.mark.parametrize("skill", SKILLS)
def test_help_works_without_crewai(skill, clean_env, python_cmd, tmp_path):
    """`--help` cannot depend on crewai — simulated by blocking the import."""
    blocker = tmp_path / "crewai.py"
    blocker.write_text("raise ImportError('crewai blocked by the test')\n", encoding="utf-8")
    env = dict(clean_env)
    env["PYTHONPATH"] = str(tmp_path)

    r = run_skill(skill, ["--help"], env, python_cmd)
    assert r.returncode == EXIT_OK, (
        f"--help broke without crewai (DT-07):\n{r.stdout}\n{r.stderr}")


@pytest.mark.parametrize("skill", sorted(set(SKILLS) - NO_LLM_SKILLS))
def test_dry_run_does_not_require_credential(skill, clean_env, python_cmd):
    """`--dry-run` builds the crew and lists the agents without any LLM key."""
    r = run_skill(skill, briefing_for(skill) + ["--dry-run"], clean_env, python_cmd)
    assert r.returncode == EXIT_OK, (
        f"--dry-run required a credential:\n{r.stdout}\n{r.stderr}")


@pytest.mark.parametrize("skill", sorted(set(SKILLS) - NO_LLM_SKILLS - {"cp-orchestrator"}))
def test_without_llm_fails_with_actionable_message(skill, clean_env, python_cmd):
    """Without a credential, the real execution exits with 2 and says what to configure (DT-08).

    Regression: before, `build_crew_llm()` returned None, the None reached the
    Agent() and CrewAI fell into the OpenAI default, failing later with
    `OPENAI_API_KEY is required`.
    """
    r = run_skill(skill, briefing_for(skill), clean_env, python_cmd)
    output = r.stdout + r.stderr
    assert r.returncode == EXIT_NO_LLM, (
        f"expected exit {EXIT_NO_LLM}, got {r.returncode}:\n{output}")
    assert "LLM_API_KEY" in output, "the message must say what to configure"
    assert "--dry-run" in output, "the message must point to the no-LLM alternative"


@pytest.mark.parametrize("skill", sorted(set(SKILLS) - NO_LLM_SKILLS))
def test_without_crewai_fails_with_actionable_message(skill, clean_env, python_cmd, tmp_path):
    """Without the lib, the execution exits with 3 and instructs to install (DT-07)."""
    blocker = tmp_path / "crewai.py"
    blocker.write_text("raise ImportError('crewai blocked by the test')\n", encoding="utf-8")
    env = dict(clean_env)
    env["PYTHONPATH"] = str(tmp_path)

    r = run_skill(skill, briefing_for(skill), env, python_cmd)
    output = r.stdout + r.stderr
    assert r.returncode == EXIT_NO_CREWAI, (
        f"expected exit {EXIT_NO_CREWAI}, got {r.returncode}:\n{output}")
    assert "pip install crewai" in output
    assert "Traceback" not in output, "must be an actionable message, not a traceback"


@pytest.mark.parametrize("skill", sorted(NO_LLM_SKILLS))
def test_skills_without_llm_run_fully(skill, clean_env, python_cmd, tmp_path):
    """cp-agile and cp-software-spec are pure Python: run without a credential."""
    args = briefing_for(skill, tmp_path) + ["--dry-run"]
    r = run_skill(skill, args, clean_env, python_cmd)
    assert r.returncode == EXIT_OK, f"{skill} failed without an LLM:\n{r.stdout}\n{r.stderr}"


def test_initializer_creates_kanban_from_the_start(clean_env, python_cmd, tmp_path):
    """The kanban is born at initialization, not on the first cp-agile run.

    Regression: `.context/docs/06-kanban.md` and `cp-agile` reference
    `.context/kanban/`, but only the agile `--init` created the columns — in a
    new project the pointer was orphaned.
    """
    r = run_skill("cp-software-spec", ["--init", "--dir", str(tmp_path)],
                  clean_env, python_cmd)
    assert r.returncode == EXIT_OK, f"initializer failed: {r.stdout} {r.stderr}"

    kanban = tmp_path / ".context" / "kanban"
    assert (kanban / "README.md").is_file(), "kanban/README.md was not created"

    # The columns mirror KANBAN_COLUMNS + BLOCKED_DIR of cp-agile.
    columns = ["1-backlog", "2-todo", "3-doing", "4-review",
               "5-testing", "6-staging", "7-done", "blocked"]
    for col in columns:
        assert (kanban / col).is_dir(), f"column {col} was not created"
        # git does not version an empty directory: without .gitkeep the structure does not travel.
        assert (kanban / col / ".gitkeep").is_file(), f"{col}/.gitkeep missing"


def test_kanban_columns_match_between_agile_and_spec():
    """The two skills declare the columns separately — they cannot diverge."""
    import re

    def columns(skill, const):
        src = skill_script(skill).read_text(encoding="utf-8")
        block = re.search(rf"^{const} = \[(.*?)\]", src, re.S | re.M)
        assert block, f"{const} not found in {skill}"
        return re.findall(r'"([^"]+)"', block.group(1))

    assert columns("cp-agile", "KANBAN_COLUMNS") ==         columns("cp-software-spec", "KANBAN_COLUMNS")


def test_install_sh_dry_run_lists_all_skills(clean_env, tmp_path, bash_cmd):
    """`install.sh --dry-run` must list all skills and the _shared helper."""
    env = dict(clean_env)
    env["HERMES_SKILLS_DIR"] = str(tmp_path / "hermes")
    env["CLAUDE_SKILLS_DIR"] = str(tmp_path / "claude")

    r = subprocess.run(
        [bash_cmd, "scripts/install.sh", "--dry-run"],
        capture_output=True, text=True, timeout=120,
        cwd=str(REPO_ROOT), env=env, encoding="utf-8", errors="replace",
    )
    assert r.returncode == EXIT_OK, f"install.sh failed:\n{r.stdout}\n{r.stderr}"
    for skill in SKILLS:
        assert skill in r.stdout, f"{skill} did not appear in the install plan"
    assert "_shared" in r.stdout, "_shared must be propagated (it is not a skill)"
