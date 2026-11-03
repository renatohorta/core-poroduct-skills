"""Smoke tests of the RUP (cp-*) skills — host-LLM model (ADR-0012).

Every skill must:
  - run on the standard library alone (no crewai, no LLM key, no site-packages)
  - print a work packet with its roles, required artifacts and the record command
  - reject a missing briefing / unreadable --input with exit 1
The orchestrator also: registry == skill dirs, --list, --discipline, --auto
protocol, Use Case Points (exact, validated), and install.sh in both agent layouts.
"""
import json
import re
import subprocess

import pytest

from conftest import (DOCUMENT_SKILLS, EXECUTION_SKILLS, EXIT_OK, EXIT_USAGE, ORCHESTRATOR, REPO_ROOT, SKILLS_DIR,
                      discipline_names, load_skill, skill_names, skill_script)
from _shared.rup import DISCIPLINES

SKILLS = DOCUMENT_SKILLS
DISCIPLINE_SKILLS = discipline_names()
BRIEFING = ["clinics scheduling SaaS"]


def run_skill(skill, args, env, python_cmd, cwd=REPO_ROOT, isolated=False, timeout=120):
    cmd = [python_cmd] + (["-S"] if isolated else []) + [str(skill_script(skill))] + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          cwd=str(cwd), env=env, encoding="utf-8", errors="replace")


# ─── every skill ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("skill", SKILLS)
def test_help_works(skill, clean_env, python_cmd):
    r = run_skill(skill, ["--help"], clean_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert "usage:" in r.stdout.lower() and "--record" in r.stdout


@pytest.mark.parametrize("skill", SKILLS)
def test_runs_on_stdlib_only(skill, clean_env, python_cmd):
    """`python -S` (no site-packages): proves there is no third-party import."""
    r = run_skill(skill, BRIEFING, clean_env, python_cmd, isolated=True)
    assert r.returncode == EXIT_OK, f"needs a third-party package:\n{r.stdout}\n{r.stderr}"


@pytest.mark.parametrize("skill", SKILLS)
def test_packet_lists_roles_artifacts_and_record_command(skill, clean_env, python_cmd):
    spec = (load_skill(skill).governance_spec("Elaboration", "/tmp/ctx")
            if skill == ORCHESTRATOR else load_skill(skill).SPEC)
    r = run_skill(skill, BRIEFING, clean_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    out = r.stdout
    assert out.startswith("# RUP work packet")
    assert "you, the agent running this skill, are the LLM" in out
    assert "clinics scheduling SaaS" in out
    assert "--record" in out and f"{skill}.md" in out
    for agent in spec["agents"]:
        assert agent["role"] in out
        for artifact in agent["artifacts"]:
            assert f"  - {artifact}" in out, f"{skill}: artifact {artifact!r} not in the packet"


@pytest.mark.parametrize("skill", SKILLS)
def test_missing_briefing_is_usage_error(skill, clean_env, python_cmd):
    r = run_skill(skill, [], clean_env, python_cmd)
    assert r.returncode == EXIT_USAGE and "briefing" in r.stdout


@pytest.mark.parametrize("skill", SKILLS)
def test_missing_input_file_is_usage_error(skill, clean_env, python_cmd, tmp_path):
    r = run_skill(skill, ["--input", str(tmp_path / "nope.md")], clean_env, python_cmd)
    out = r.stdout + r.stderr
    assert r.returncode == EXIT_USAGE, out
    assert "--input" in out and "Traceback" not in out


@pytest.mark.parametrize("skill", SKILLS)
def test_input_file_briefing_is_used(skill, clean_env, python_cmd, tmp_path):
    f = tmp_path / "briefing.md"
    f.write_text("dental clinics, multi-tenant", encoding="utf-8")
    r = run_skill(skill, ["--input", str(f)], clean_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert "dental clinics, multi-tenant" in r.stdout
    assert "--input" in r.stdout.split("## Briefing")[0], \
        "the suggested --record command should reuse the briefing file"


@pytest.mark.parametrize("skill", SKILLS)
def test_every_skill_has_skill_md_and_references(skill):
    d = SKILLS_DIR / skill
    assert (d / "SKILL.md").is_file(), f"{skill}: SKILL.md missing"
    assert list((d / "references").glob("*.md")), f"{skill}: no references/*.md"
    text = (d / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: " + skill), f"{skill}: frontmatter name"
    assert "--record" in text, f"{skill}: SKILL.md must teach the host the record step"


@pytest.mark.parametrize("skill", DISCIPLINE_SKILLS)
def test_spec_is_well_formed(skill):
    spec = load_skill(skill).SPEC
    assert spec["key"] == skill[len("cp-"):]
    assert DISCIPLINES[spec["key"]]["skill"] == skill
    assert DISCIPLINES[spec["key"]]["title"] == spec["title"]
    assert spec["agents"], f"{skill}: no agents"
    names = [a for agent in spec["agents"] for a in agent["artifacts"]]
    assert len(names) == len(set(names)), f"{skill}: duplicate artifact names"
    for agent in spec["agents"]:
        for field in ("slug", "role", "goal", "backstory", "mission", "artifacts"):
            assert agent.get(field), f"{skill}/{agent.get('slug')}: {field} missing"


def test_agent_count_matches_the_rup_specification():
    """9 skills, 21 agents (1 orchestrator + 20 specialists)."""
    total = 1 + sum(len(load_skill(s).SPEC["agents"]) for s in DISCIPLINE_SKILLS)
    assert len(DOCUMENT_SKILLS) == 9 and total == 21


# ─── orchestrator ────────────────────────────────────────────────────────

def test_registry_matches_discipline_skills():
    from _shared.rup import ORCHESTRATOR_SKILL
    for skill in [ORCHESTRATOR_SKILL] + [d["skill"] for d in DISCIPLINES.values()]:
        assert skill_script(skill).is_file(), f"{skill}: registered but has no run.py"
    for skill in skill_names():
        spec = getattr(load_skill(skill), "SPEC", None)
        if isinstance(spec, dict) and spec.get("key") is not None:
            assert spec["key"] in DISCIPLINES, f"{skill}: SPEC key not in the registry"
            assert DISCIPLINES[spec["key"]]["skill"] == skill


def test_orchestrator_lists_all_disciplines(clean_env, python_cmd):
    r = run_skill(ORCHESTRATOR, ["--list"], clean_env, python_cmd)
    assert r.returncode == EXIT_OK
    for key in DISCIPLINES:
        assert key in r.stdout


def test_orchestrator_discipline_prints_that_packet(clean_env, python_cmd):
    r = run_skill(ORCHESTRATOR, BRIEFING + ["--discipline", "requirements"], clean_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert r.stdout.startswith("# RUP work packet — Requirements (`cp-requirements`)")


def test_orchestrator_discipline_rejects_record(clean_env, python_cmd, tmp_path):
    doc = tmp_path / "d.md"
    doc.write_text("x", encoding="utf-8")
    r = run_skill(ORCHESTRATOR, ["--discipline", "ccm", "--record", str(doc)],
                  clean_env, python_cmd)
    assert r.returncode == EXIT_USAGE and "cp-ccm" in r.stdout


def test_auto_prints_the_protocol_in_rup_order(clean_env, python_cmd):
    r = run_skill(ORCHESTRATOR, BRIEFING + ["--auto", "--phase", "Inception"], clean_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    out = r.stdout
    assert "are the LLM" in out and "in order" in out
    order = [ORCHESTRATOR] + [d["skill"] for d in DISCIPLINES.values()]
    positions = [out.index(f"{s}/scripts/run.py") for s in order]
    assert positions == sorted(positions), "steps out of RUP order"
    assert "--phase Inception" in out and "Next pending step: 0" in out


def test_auto_requires_a_briefing(clean_env, python_cmd):
    r = run_skill(ORCHESTRATOR, ["--auto"], clean_env, python_cmd)
    assert r.returncode == EXIT_USAGE


def test_governance_packet_carries_the_sizing_commands(clean_env, python_cmd):
    r = run_skill(ORCHESTRATOR, BRIEFING + ["--phase", "Inception"], clean_env, python_cmd)
    out = r.stdout
    assert "--sizing-template" in out and "--estimate --sizing" in out
    assert "never by you" in out
    for d in DISCIPLINES.values():
        assert d["skill"] in out, "a Work Order target is missing"


# ─── Software Sizing & Effort Estimation (Use Case Points) ───────────────

def test_ucp_neutral_matches_hand_calculation():
    orq = load_skill(ORCHESTRATOR)
    r = orq.compute_ucp(
        actors=[{"type": "average", "count": 2}, {"type": "complex", "count": 2}],
        usecases=[{"type": "average", "count": 10}, {"type": "complex", "count": 5}],
        technical_factors={}, environmental_factors={}, productivity_hours=20)
    assert (r["uaw"], r["uucw"], r["uucp"]) == (10, 175, 185)
    assert r["tcf"] == r["ef"] == 1.0
    assert r["ucp"] == 185.0 and r["effort_hours"] == 3700.0


def test_ucp_empty_factor_maps_are_neutral():
    orq = load_skill(ORCHESTRATOR)
    r = orq.compute_ucp(actors=[{"type": "simple", "count": 1}],
                        usecases=[{"type": "simple", "count": 1}])
    assert r["tcf"] == 1.0 and r["ef"] == 1.0 and r["ucp"] == float(r["uucp"])


@pytest.mark.parametrize("model, fragment", [
    ({"actors": [{"type": "huge", "count": 1}]}, "actors[0].type"),
    ({"usecases": [{"type": "simple", "count": -1}]}, "usecases[0].count"),
    ({"technical_factors": {"T99": 3}}, "unknown factor"),
    ({"environmental_factors": {"F1": 9}}, "F1"),
    ({"productivity_hours": 0}, "productivity_hours"),
])
def test_ucp_model_validation(model, fragment):
    orq = load_skill(ORCHESTRATOR)
    with pytest.raises(orq.SizingError, match=re.escape(fragment)):
        orq.ucp_from_model(model)


def test_ucp_estimate_cli(clean_env, python_cmd, tmp_path):
    model = tmp_path / "sizing.json"
    model.write_text(json.dumps({
        "actors": [{"type": "average", "count": 2}, {"type": "complex", "count": 2}],
        "usecases": [{"type": "average", "count": 10}, {"type": "complex", "count": 5}],
    }), encoding="utf-8")
    r = run_skill(ORCHESTRATOR, ["--estimate", "--sizing", str(model), "--json"],
                  clean_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    data = json.loads(r.stdout)
    assert data["uucp"] == 185 and data["ucp"] == 185.0 and data["effort_hours"] == 3700.0


def test_ucp_estimate_cli_rejects_invalid_model(clean_env, python_cmd, tmp_path):
    model = tmp_path / "sizing.json"
    model.write_text('{"actors": [{"type": "huge", "count": 1}]}', encoding="utf-8")
    r = run_skill(ORCHESTRATOR, ["--estimate", "--sizing", str(model)], clean_env, python_cmd)
    out = r.stdout + r.stderr
    assert r.returncode == EXIT_USAGE and "invalid sizing model" in out
    assert "Traceback" not in out


def test_sizing_template_cli(clean_env, python_cmd):
    r = run_skill(ORCHESTRATOR, ["--sizing-template"], clean_env, python_cmd)
    assert r.returncode == EXIT_OK
    data = json.loads(r.stdout)
    assert {"actors", "usecases", "productivity_hours"} <= set(data)


# ─── install.sh ──────────────────────────────────────────────────────────

def _install(bash_cmd, clean_env, tmp_path, *args):
    env = dict(clean_env)
    env["HERMES_SKILLS_DIR"] = str(tmp_path / "hermes")
    env["CLAUDE_SKILLS_DIR"] = str(tmp_path / "claude")
    return subprocess.run([bash_cmd, "scripts/install.sh", *args], capture_output=True,
                          text=True, timeout=120, cwd=str(REPO_ROOT), env=env,
                          encoding="utf-8", errors="replace")


def test_install_sh_dry_run_plans_every_skill(clean_env, tmp_path, bash_cmd):
    r = _install(bash_cmd, clean_env, tmp_path, "--dry-run")
    assert r.returncode == EXIT_OK, f"install.sh failed:\n{r.stdout}\n{r.stderr}"
    for skill in SKILLS:
        assert skill in r.stdout
    assert "_shared" in r.stdout
    assert "README.md →" not in r.stdout
    assert not (tmp_path / "claude").exists(), "--dry-run must not copy anything"


def test_installed_skills_run_in_both_agent_layouts(clean_env, tmp_path, bash_cmd, python_cmd):
    """Installed copies find _shared in Claude (flat) and Hermes (category) layouts."""
    r = _install(bash_cmd, clean_env, tmp_path)
    assert r.returncode == EXIT_OK, f"install.sh failed:\n{r.stdout}\n{r.stderr}"
    for root in (tmp_path / "claude", tmp_path / "hermes" / "creative"):
        for skill in (ORCHESTRATOR, "cp-requirements"):
            run_py = root / skill / "scripts" / "run.py"
            r = subprocess.run([python_cmd, str(run_py), "briefing"], capture_output=True,
                               text=True, timeout=120, env=clean_env,
                               encoding="utf-8", errors="replace")
            assert r.returncode == EXIT_OK, f"{run_py}:\n{r.stdout}\n{r.stderr}"
            assert r.stdout.startswith("# RUP work packet")


@pytest.mark.parametrize("skill", EXECUTION_SKILLS)
def test_execution_skills_help_and_stdlib(skill, clean_env, python_cmd):
    for isolated in (False, True):
        r = run_skill(skill, ["--help"], clean_env, python_cmd, isolated=isolated)
        assert r.returncode == EXIT_OK, r.stdout + r.stderr
    d = SKILLS_DIR / skill
    text = (d / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: " + skill), f"{skill}: frontmatter name"
    assert list((d / "references").glob("*.md")), f"{skill}: no references/*.md"
