"""Smoke tests of the RUP (rup-*) skills under skills/.

Verifies the minimum every skill must guarantee, without calling an LLM:
  - `--help` always works (even without crewai)
  - `--dry-run` builds the crew without requiring a credential — and still
    shows the plan when crewai is not installed
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

from conftest import (EXIT_NO_CREWAI, EXIT_NO_LLM, EXIT_OK, REPO_ROOT, SKILLS_DIR,
                      skill_names, skill_script)

SKILLS = skill_names()
ORCHESTRATOR = "rup-orchestrator"
DEFAULT_BRIEFING = ["test briefing"]

# The 8 disciplines the orchestrator must register (skill dir -> expected key).
DISCIPLINE_KEYS = ["environment", "business-modeling", "requirements",
                   "analysis-design", "implementation", "test", "ccm", "deployment"]


def run_skill(skill, args, env, python_cmd, timeout=120):
    return subprocess.run(
        [python_cmd, str(skill_script(skill))] + args,
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
    src = skill_script(ORCHESTRATOR).read_text(encoding="utf-8")
    block = re.search(r"^DISCIPLINES = \{(.*?)^\}", src, re.S | re.M)
    assert block, "DISCIPLINES registry not found in the orchestrator"
    registry = block.group(1)

    import json
    for key in DISCIPLINE_KEYS:
        m = re.search(r'^    "%s": \{"skill": "([^"]+)"' % re.escape(key), registry, re.M)
        assert m, f"discipline {key!r} missing from the orchestrator registry"
        skill = m.group(1)
        assert (SKILLS_DIR / skill / "scripts" / "run.py").is_file(), (
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
    d = SKILLS_DIR / skill
    assert (d / "SKILL.md").is_file(), f"{skill}: SKILL.md missing"
    assert (d / "scripts" / "run.py").is_file(), f"{skill}: run.py missing"
    refs = list((d / "references").glob("*.md"))
    assert refs, f"{skill}: no references/*.md"


# ─── Software Sizing & Effort Estimation (Use Case Points) ───────────────

def _load_orchestrator():
    spec = importlib.util.spec_from_file_location(
        "rup_orq_test", skill_script(ORCHESTRATOR))
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


def _block_crewai(clean_env, tmp_path):
    blocker = tmp_path / "crewai.py"
    blocker.write_text("raise ImportError('crewai blocked by the test')\n", encoding="utf-8")
    env = dict(clean_env)
    env["PYTHONPATH"] = str(tmp_path)
    return env


@pytest.mark.parametrize("skill", SKILLS)
def test_dry_run_works_without_crewai(skill, clean_env, python_cmd, tmp_path):
    """`--dry-run` shows the planned agents even when crewai is not installed."""
    r = run_skill(skill, DEFAULT_BRIEFING + ["--dry-run"],
                  _block_crewai(clean_env, tmp_path), python_cmd)
    assert r.returncode == EXIT_OK, f"--dry-run needed crewai:\n{r.stdout}\n{r.stderr}"
    assert "DRY RUN" in r.stdout and "Traceback" not in r.stdout + r.stderr


@pytest.mark.parametrize("skill", SKILLS)
def test_missing_input_file_is_usage_error(skill, clean_env, python_cmd, tmp_path):
    """A nonexistent --input file exits 1 with a message, not a traceback."""
    r = run_skill(skill, ["--input", str(tmp_path / "nope.md"), "--dry-run"],
                  clean_env, python_cmd)
    out = r.stdout + r.stderr
    assert r.returncode == 1, f"expected exit 1, got {r.returncode}:\n{out}"
    assert "--input" in out and "Traceback" not in out


# ─── --auto: one artifact per discipline, chained, stop on failure ───────

def test_auto_output_paths_are_unique_per_discipline(tmp_path):
    """With --output, each discipline gets its own file (no overwrite)."""
    orq = _load_orchestrator()
    paths = [orq.auto_output_path(str(tmp_path / "plan.md"), i, k, "unused")
             for i, k in enumerate(orq.DISCIPLINES, start=1)]
    assert len(set(paths)) == len(orq.DISCIPLINES)
    assert paths[0] == tmp_path / "plan.01-environment.md"
    assert paths[-1] == tmp_path / "plan.08-deployment.md"
    # without --output they land in the temporary workdir
    assert orq.auto_output_path(None, 3, "requirements", tmp_path) == \
        tmp_path / "03-requirements.md"


def test_chained_context_carries_previous_artifacts(tmp_path):
    """Each discipline receives the briefing plus the earlier disciplines' artifacts."""
    orq = _load_orchestrator()
    env_art = tmp_path / "01-environment.md"
    env_art.write_text("Development Case: use Scrum-RUP hybrid", encoding="utf-8")
    big = tmp_path / "02-business-modeling.md"
    big.write_text("x" * (orq.MAX_PRIOR_ARTIFACT_CHARS + 500), encoding="utf-8")

    first = orq.build_chained_context("clinics SaaS", [])
    assert first.strip() == "clinics SaaS"

    ctx = orq.build_chained_context(
        "clinics SaaS",
        [("environment", env_art), ("business-modeling", big),
         ("requirements", tmp_path / "missing.md")])
    assert ctx.startswith("clinics SaaS")
    assert "Development Case: use Scrum-RUP hybrid" in ctx
    assert "## Business Modeling (business-modeling)" in ctx
    assert "truncated" in ctx
    assert "(requirements)" not in ctx, "a missing artifact must be skipped"


def test_auto_stops_at_first_failing_discipline(clean_env, python_cmd, tmp_path):
    """Without an LLM the first discipline exits 2; --auto must stop there."""
    r = run_skill(ORCHESTRATOR, ["test briefing", "--auto", "--output",
                                 str(tmp_path / "plan.md")], clean_env, python_cmd,
                  timeout=300)
    out = r.stdout + r.stderr
    assert r.returncode == EXIT_NO_LLM, f"expected exit {EXIT_NO_LLM}:\n{out}"
    assert "stopping --auto" in out
    assert "dispatching business-modeling" not in out, "--auto ran past a failure"


# ─── UCP: validation and the agent's tool ────────────────────────────────

@pytest.mark.parametrize("model, fragment", [
    ({"actors": [{"type": "huge", "count": 1}]}, "actors[0].type"),
    ({"usecases": [{"type": "simple", "count": -1}]}, "usecases[0].count"),
    ({"technical_factors": {"T99": 3}}, "unknown factor"),
    ({"environmental_factors": {"F1": 9}}, "F1"),
    ({"productivity_hours": 0}, "productivity_hours"),
])
def test_ucp_model_validation(model, fragment):
    orq = _load_orchestrator()
    with pytest.raises(orq.SizingError, match=re.escape(fragment)):
        orq.ucp_from_model(model)


def test_ucp_estimate_cli_rejects_invalid_model(clean_env, python_cmd, tmp_path):
    """An invalid sizing file exits 1 with a message, not a traceback."""
    model = tmp_path / "sizing.json"
    model.write_text('{"actors": [{"type": "huge", "count": 1}]}', encoding="utf-8")
    r = run_skill(ORCHESTRATOR, ["--estimate", "--sizing", str(model)],
                  clean_env, python_cmd)
    out = r.stdout + r.stderr
    assert r.returncode == 1, out
    assert "invalid sizing model" in out and "Traceback" not in out


def test_ucp_tool_body_computes_and_reports_errors():
    """The tool returns the deterministic JSON, or an ERROR text (never raises)."""
    orq = _load_orchestrator()
    data = json.loads(orq.ucp_tool_run(json.dumps({
        "actors": [{"type": "average", "count": 2}, {"type": "complex", "count": 2}],
        "usecases": [{"type": "average", "count": 10}, {"type": "complex", "count": 5}],
    })))
    assert data["ucp"] == 185.0 and data["effort_hours"] == 3700.0
    assert orq.ucp_tool_run("not json").startswith("ERROR:")


def test_governance_agent_has_the_ucp_tool():
    """The PM agent must be able to CALL compute_ucp instead of guessing numbers."""
    pytest.importorskip("crewai")
    orq = _load_orchestrator()
    crew = orq.build_crew("clinics SaaS", "Inception")
    names = [t.name for t in crew.agents[0].tools]
    assert orq.UCP_TOOL_NAME in names
    assert orq.UCP_TOOL_NAME in crew.tasks[0].description


# ─── install.sh ──────────────────────────────────────────────────────────

def _install(bash_cmd, clean_env, tmp_path, *args):
    env = dict(clean_env)
    env["HERMES_SKILLS_DIR"] = str(tmp_path / "hermes")
    env["CLAUDE_SKILLS_DIR"] = str(tmp_path / "claude")
    return subprocess.run(
        [bash_cmd, "scripts/install.sh", *args],
        capture_output=True, text=True, timeout=120,
        cwd=str(REPO_ROOT), env=env, encoding="utf-8", errors="replace",
    )


def test_install_sh_dry_run_plans_every_skill(clean_env, tmp_path, bash_cmd):
    """The plan covers every rup-* skill plus _shared, and never a non-skill entry."""
    r = _install(bash_cmd, clean_env, tmp_path, "--dry-run")
    assert r.returncode == EXIT_OK, f"install.sh failed:\n{r.stdout}\n{r.stderr}"
    for skill in SKILLS:
        assert skill in r.stdout, f"{skill} did not appear in the install plan"
    assert "_shared" in r.stdout, "_shared must be propagated (it is not a skill)"
    assert "README.md →" not in r.stdout
    assert not (tmp_path / "claude").exists(), "--dry-run must not copy anything"


def test_installed_skills_run_in_both_agent_layouts(clean_env, tmp_path, bash_cmd,
                                                    python_cmd):
    """Installed copies find _shared in Claude (flat) and Hermes (category) layouts."""
    r = _install(bash_cmd, clean_env, tmp_path)
    assert r.returncode == EXIT_OK, f"install.sh failed:\n{r.stdout}\n{r.stderr}"
    assert (tmp_path / "claude" / "_shared" / "llm.py").is_file()
    assert (tmp_path / "hermes" / "_shared" / "llm.py").is_file()

    for installed in (tmp_path / "claude" / ORCHESTRATOR,
                      tmp_path / "hermes" / "creative" / ORCHESTRATOR):
        r = subprocess.run(
            [python_cmd, str(installed / "scripts" / "run.py"), "--list"],
            capture_output=True, text=True, timeout=120, env=clean_env,
            encoding="utf-8", errors="replace",
        )
        assert r.returncode == EXIT_OK, f"{installed}:\n{r.stdout}\n{r.stderr}"
        assert "requirements" in r.stdout
