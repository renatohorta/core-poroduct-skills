"""Smoke tests of the RUP (rup-*) skills — the active family.

Mirrors the guarantees of the cp-* smoke tests (which now live in
tests/test_smoke.py), but for skills/rup/:
  - `--help` always works (even without crewai)
  - `--dry-run` builds the crew without requiring a credential
  - the absence of a credential fails with code 2 and an actionable message
  - the absence of crewai fails with code 3 and an actionable message
  - the orchestrator exposes the 8 disciplines and the sub-dispatch
  - the Use Case Points estimator runs deterministically without an LLM
"""
import importlib.util
import json
import re
import subprocess

import pytest

from conftest import (EXIT_NO_CREWAI, EXIT_NO_LLM, EXIT_OK, REPO_ROOT,
                      rup_skill_names, rup_skill_script)

SKILLS = rup_skill_names()
ORCHESTRATOR = "rup-orchestrator"
DEFAULT_BRIEFING = ["test briefing"]

# The 8 disciplines the orchestrator must register (skill dir -> expected key).
DISCIPLINE_KEYS = ["environment", "business-modeling", "requirements",
                   "analysis-design", "implementation", "test", "ccm", "deployment"]


def run_skill(skill, args, env, python_cmd, timeout=120):
    return subprocess.run(
        [python_cmd, str(rup_skill_script(skill))] + args,
        capture_output=True, text=True, timeout=timeout,
        cwd=str(REPO_ROOT), env=env, encoding="utf-8", errors="replace",
    )


@pytest.mark.parametrize("skill", SKILLS)
def test_help_always_works(skill, clean_env, python_cmd):
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
        f"--help broke without crewai:\n{r.stdout}\n{r.stderr}")


@pytest.mark.parametrize("skill", SKILLS)
def test_dry_run_does_not_require_credential(skill, clean_env, python_cmd):
    """`--dry-run` builds the crew and lists the agents without any LLM key."""
    r = run_skill(skill, DEFAULT_BRIEFING + ["--dry-run"], clean_env, python_cmd)
    assert r.returncode == EXIT_OK, (
        f"--dry-run required a credential:\n{r.stdout}\n{r.stderr}")


@pytest.mark.parametrize("skill", SKILLS)
def test_without_llm_fails_with_actionable_message(skill, clean_env, python_cmd):
    """Without a credential, the real execution exits with 2 and says what to configure."""
    r = run_skill(skill, DEFAULT_BRIEFING, clean_env, python_cmd)
    output = r.stdout + r.stderr
    assert r.returncode == EXIT_NO_LLM, (
        f"expected exit {EXIT_NO_LLM}, got {r.returncode}:\n{output}")
    assert "LLM_API_KEY" in output, "the message must say what to configure"
    assert "--dry-run" in output, "the message must point to the no-LLM alternative"


@pytest.mark.parametrize("skill", SKILLS)
def test_without_crewai_fails_with_actionable_message(skill, clean_env, python_cmd, tmp_path):
    """Without the lib, the execution exits with 3 and instructs to install."""
    blocker = tmp_path / "crewai.py"
    blocker.write_text("raise ImportError('crewai blocked by the test')\n", encoding="utf-8")
    env = dict(clean_env)
    env["PYTHONPATH"] = str(tmp_path)

    r = run_skill(skill, DEFAULT_BRIEFING, env, python_cmd)
    output = r.stdout + r.stderr
    assert r.returncode == EXIT_NO_CREWAI, (
        f"expected exit {EXIT_NO_CREWAI}, got {r.returncode}:\n{output}")
    assert "pip install crewai" in output
    assert "Traceback" not in output, "must be an actionable message, not a traceback"


def test_orchestrator_lists_all_disciplines(clean_env, python_cmd):
    """`rup-orchestrator --list` must name every RUP discipline (no LLM needed)."""
    r = run_skill(ORCHESTRATOR, ["--list"], clean_env, python_cmd)
    assert r.returncode == EXIT_OK, f"--list failed:\n{r.stdout}\n{r.stderr}"
    for key in DISCIPLINE_KEYS:
        assert key in r.stdout, f"discipline {key!r} missing from --list"


def test_orchestrator_registry_matches_discipline_skills():
    """Every discipline in the orchestrator registry must map to a real skill dir."""
    src = rup_skill_script(ORCHESTRATOR).read_text(encoding="utf-8")
    block = re.search(r"^DISCIPLINES = \{(.*?)^\}", src, re.S | re.M)
    assert block, "DISCIPLINES registry not found in the orchestrator"
    registry = block.group(1)

    import json
    for key in DISCIPLINE_KEYS:
        m = re.search(r'^    "%s": \{"skill": "([^"]+)"' % re.escape(key), registry, re.M)
        assert m, f"discipline {key!r} missing from the orchestrator registry"
        skill = m.group(1)
        assert (REPO_ROOT / "skills" / "rup" / skill / "scripts" / "run.py").is_file(), (
            f"{key}: registered skill {skill!r} has no run.py on disk")


def test_orchestrator_discipline_dry_run(clean_env, python_cmd):
    """`--discipline <key> --dry-run` is accepted without an LLM."""
    r = run_skill(ORCHESTRATOR, ["test briefing", "--discipline", "requirements", "--dry-run"],
                  clean_env, python_cmd)
    assert r.returncode == EXIT_OK, f"discipline --dry-run failed:\n{r.stdout}\n{r.stderr}"
    assert "requirements" in r.stdout.lower()


def test_orchestrator_auto_dry_run(clean_env, python_cmd):
    """`--auto --dry-run` lists every discipline without running anything."""
    r = run_skill(ORCHESTRATOR, ["test briefing", "--auto", "--dry-run"],
                  clean_env, python_cmd)
    assert r.returncode == EXIT_OK, f"--auto --dry-run failed:\n{r.stdout}\n{r.stderr}"
    for key in DISCIPLINE_KEYS:
        assert key in r.stdout, f"discipline {key!r} missing from --auto --dry-run"


@pytest.mark.parametrize("skill", SKILLS)
def test_every_rup_skill_has_skill_md_and_references(skill):
    """Every RUP skill ships SKILL.md, a run.py and at least one reference."""
    d = REPO_ROOT / "skills" / "rup" / skill
    assert (d / "SKILL.md").is_file(), f"{skill}: SKILL.md missing"
    assert (d / "scripts" / "run.py").is_file(), f"{skill}: run.py missing"
    refs = list((d / "references").glob("*.md"))
    assert refs, f"{skill}: no references/*.md"


# ─── Software Sizing & Effort Estimation (Use Case Points) ───────────────

def _load_orchestrator():
    spec = importlib.util.spec_from_file_location(
        "rup_orq_test", rup_skill_script(ORCHESTRATOR))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ucp_neutral_matches_hand_calculation():
    """UUCP/UCP with neutral factors must match the hand-computed reference."""
    orq = _load_orchestrator()
    result = orq.compute_ucp(
        actors=[{"type": "average", "count": 2}, {"type": "complex", "count": 2}],
        usecases=[{"type": "average", "count": 10}, {"type": "complex", "count": 5}],
        technical_factors={}, environmental_factors={},
        productivity_hours=20,
    )
    assert result["uaw"] == 10
    assert result["uucw"] == 175
    assert result["uucp"] == 185
    assert result["tcf"] == 1.0
    assert result["ef"] == 1.0
    assert result["ucp"] == 185.0
    assert result["effort_hours"] == 3700.0


def test_ucp_empty_factor_maps_are_neutral():
    """Omitting the factor maps must be exactly neutral (TCF = EF = 1.0)."""
    orq = _load_orchestrator()
    r = orq.compute_ucp(actors=[{"type": "simple", "count": 1}],
                        usecases=[{"type": "simple", "count": 1}])
    assert r["tcf"] == 1.0 and r["ef"] == 1.0
    assert r["ucp"] == float(r["uucp"])


def test_ucp_estimate_cli_without_llm(clean_env, python_cmd, tmp_path):
    """`--estimate --sizing <file> --json` runs deterministically without an LLM."""
    model = tmp_path / "sizing.json"
    model.write_text(json.dumps({
        "actors": [{"type": "average", "count": 2}, {"type": "complex", "count": 2}],
        "usecases": [{"type": "average", "count": 10}, {"type": "complex", "count": 5}],
        "technical_factors": {}, "environmental_factors": {},
        "productivity_hours": 20,
    }), encoding="utf-8")

    r = run_skill(ORCHESTRATOR, ["--estimate", "--sizing", str(model), "--json"],
                  clean_env, python_cmd)
    assert r.returncode == EXIT_OK, f"--estimate failed:\n{r.stdout}\n{r.stderr}"
    data = json.loads(r.stdout)
    assert data["uucp"] == 185 and data["ucp"] == 185.0
    assert data["effort_hours"] == 3700.0


def test_sizing_template_cli_without_llm(clean_env, python_cmd):
    """`--sizing-template` prints a valid JSON model and needs no crewai/LLM."""
    r = run_skill(ORCHESTRATOR, ["--sizing-template"], clean_env, python_cmd)
    assert r.returncode == EXIT_OK, f"--sizing-template failed:\n{r.stdout}\n{r.stderr}"
    data = json.loads(r.stdout)
    assert "actors" in data and "usecases" in data and "productivity_hours" in data
