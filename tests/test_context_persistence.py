"""Mandatory persistence of the RUP artifacts into `.context/` (ADR-0011/0012).

Unit tests of `skills/_shared/context.py` plus end-to-end runs of the real
skills: packet → the host's document → `--record` validates and writes
`.context/docs/<NN-phase>/rup-<skill>.md` + a row in `tracking/rup-log.md`.
No LLM involved: the host agent is the LLM, here replaced by a fixed document.
"""
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from conftest import (EXIT_CONTEXT_NOT_WRITABLE, authorize, EXIT_OK, EXIT_USAGE, ORCHESTRATOR,
                      REPO_ROOT, discipline_names, full_document, load_skill, skill_script)
from _shared import context as ctx
from _shared.rup import DISCIPLINES

DISCIPLINE_SKILLS = discipline_names()
PHASE_DIR = {"Inception": "01-inception", "Elaboration": "02-elaboration",
             "Construction": "03-construction", "Transition": "04-transition"}
POSIX_NON_ROOT = pytest.mark.skipif(
    os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="POSIX permissions (and not root)")


def run_skill(skill, args, env, python_cmd, cwd=REPO_ROOT, stdin=None, timeout=120):
    return subprocess.run(
        [python_cmd, str(skill_script(skill))] + args,
        capture_output=True, text=True, timeout=timeout, input=stdin,
        cwd=str(cwd), env=env, encoding="utf-8", errors="replace",
    )


def spec_of(skill, phase="Elaboration", context_dir="/tmp/ctx"):
    mod = load_skill(skill)
    return mod.governance_spec(phase, context_dir) if skill == ORCHESTRATOR else mod.SPEC


def record(skill, env, python_cmd, tmp_path, phase="Elaboration", doc=None, extra=()):
    path = tmp_path / f"{skill}-doc.md"
    path.write_text(doc if doc is not None else full_document(spec_of(skill, phase)),
                    encoding="utf-8")
    return run_skill(skill, ["--record", str(path), "--phase", phase, *extra], env, python_cmd)


def log_rows(context_dir):
    log = Path(context_dir) / "tracking" / "rup-log.md"
    if not log.exists():
        return []
    return [line for line in log.read_text(encoding="utf-8").splitlines()
            if line.startswith("| 20")]


# ─── context.py — resolution ─────────────────────────────────────────────

def test_resolve_prefers_explicit_then_env(tmp_path, monkeypatch):
    monkeypatch.setenv(ctx.CONTEXT_ENV_VAR, str(tmp_path / "from-env"))
    assert ctx.resolve_context_dir(tmp_path / "explicit") == (tmp_path / "explicit").resolve()
    assert ctx.resolve_context_dir() == (tmp_path / "from-env").resolve()


def test_resolve_walks_up_to_existing_context(tmp_path, monkeypatch):
    monkeypatch.delenv(ctx.CONTEXT_ENV_VAR, raising=False)
    (tmp_path / "proj" / ".context").mkdir(parents=True)
    deep = tmp_path / "proj" / "src" / "pkg"
    deep.mkdir(parents=True)
    assert ctx.resolve_context_dir(start=deep) == (tmp_path / "proj" / ".context").resolve()


def test_resolve_stops_at_git_root(tmp_path, monkeypatch):
    """Never escape the repository: a .context/ above the git root is ignored."""
    monkeypatch.delenv(ctx.CONTEXT_ENV_VAR, raising=False)
    (tmp_path / ".context").mkdir()             # outside the repo
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / "src").mkdir()
    assert ctx.resolve_context_dir(start=repo / "src") == (repo / ".context").resolve()


def test_resolve_falls_back_to_start(tmp_path, monkeypatch):
    monkeypatch.delenv(ctx.CONTEXT_ENV_VAR, raising=False)
    start = (tmp_path / "a" / "b").resolve()
    start.mkdir(parents=True)
    if any((d / ".context").is_dir() or (d / ".git").exists() for d in start.parents):
        pytest.skip("tmp dir lives under a .context/ or git checkout")
    assert ctx.resolve_context_dir(start=start) == start / ".context"


# ─── context.py — layout and writing ─────────────────────────────────────

@pytest.mark.parametrize("phase, folder", list(PHASE_DIR.items()))
def test_artifact_path_follows_rup_phase_layout(tmp_path, phase, folder):
    p = ctx.artifact_path(tmp_path, phase, "rup-requirements")
    assert p == tmp_path / "docs" / folder / "rup-requirements.md"


def test_artifact_path_rejects_unknown_phase(tmp_path):
    with pytest.raises(ValueError, match="unknown RUP phase"):
        ctx.artifact_path(tmp_path, "Design", "rup-requirements")


def test_write_artifact_has_provenance_and_is_logged(tmp_path):
    now = datetime(2026, 11, 3, 14, 30, 0)
    path = ctx.write_artifact(tmp_path, "Vision Document: ...", skill="rup-requirements",
                              title="Requirements", phase="Inception",
                              briefing="clinics SaaS", now=now)
    assert path == tmp_path / "docs" / "01-inception" / "rup-requirements.md"
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\nskill: rup-requirements\n")
    assert "milestone: Lifecycle Objective (LCO)" in text
    assert "generated_at: 2026-11-03T14:30:00" in text
    assert "> clinics SaaS" in text
    assert text.rstrip().endswith("Vision Document: ...")
    rows = log_rows(tmp_path)
    assert rows == ["| 2026-11-03T14:30:00 | Inception | `rup-requirements` | "
                    "`docs/01-inception/rup-requirements.md` |"]


def test_rewrite_regenerates_file_and_appends_log(tmp_path):
    for content in ("first", "second"):
        path = ctx.write_artifact(tmp_path, content, skill="rup-test", title="Test",
                                  phase="Construction", briefing="b")
    assert path.read_text(encoding="utf-8").rstrip().endswith("second")
    assert "first" not in path.read_text(encoding="utf-8")
    assert len(log_rows(tmp_path)) == 2


def test_curated_docs_are_never_touched(tmp_path):
    curated = tmp_path / "docs" / "01-inception" / "requirements.md"
    curated.parent.mkdir(parents=True)
    curated.write_text("curated by a human", encoding="utf-8")
    ctx.write_artifact(tmp_path, "generated", skill="rup-requirements",
                       title="Requirements", phase="Inception", briefing="b")
    assert curated.read_text(encoding="utf-8") == "curated by a human"


def test_long_briefing_is_excerpted(tmp_path):
    path = ctx.write_artifact(tmp_path, "x", skill="rup-ccm", title="CCM",
                              phase="Elaboration", briefing="y" * 5000)
    text = path.read_text(encoding="utf-8")
    assert "[… truncated]" in text and "y" * 5000 not in text


@pytest.mark.skipif(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                    reason="POSIX permissions (and not root)")
def test_ensure_writable_exits_4(tmp_path, capsys):
    ro = tmp_path / "ro" / ".context"
    authorize(ro)
    ro.chmod(0o500)
    try:
        with pytest.raises(SystemExit) as exc:
            ctx.ensure_writable(ro, "Elaboration")
        assert exc.value.code == EXIT_CONTEXT_NOT_WRITABLE
        assert "mandatory" in capsys.readouterr().out
    finally:
        ro.chmod(0o700)


# ─── End-to-end: packet → document → --record ────────────────────────────

@pytest.mark.parametrize("skill", DISCIPLINE_SKILLS + [ORCHESTRATOR])
def test_record_writes_the_artifact(skill, ctx_env, python_cmd, tmp_path):
    context_dir = Path(ctx_env["RUP_CONTEXT_DIR"])
    r = record(skill, ctx_env, python_cmd, tmp_path, phase="Construction",
               extra=["clinics SaaS"])
    out = r.stdout + r.stderr
    assert r.returncode == EXIT_OK, out
    artifact = context_dir / "docs" / "03-construction" / f"{skill}.md"
    text = artifact.read_text(encoding="utf-8")
    assert f"skill: {skill}" in text and "> clinics SaaS" in text
    assert "## " in ctx_body(text)
    assert len(log_rows(context_dir)) == 1


def ctx_body(text):
    return text.split("\n## Artifacts\n", 1)[1]


@pytest.mark.parametrize("skill", DISCIPLINE_SKILLS)
def test_record_rejects_missing_artifacts(skill, ctx_env, python_cmd, tmp_path):
    spec = spec_of(skill)
    dropped = spec["agents"][-1]["artifacts"][-1]
    doc = full_document(spec).replace(f"## {dropped}\n", "Forgot this one.\n")
    r = record(skill, ctx_env, python_cmd, tmp_path, doc=doc)
    assert r.returncode == EXIT_USAGE, r.stdout
    assert f"  - {dropped}" in r.stdout and "Nothing was written" in r.stdout
    assert not (Path(ctx_env["RUP_CONTEXT_DIR"]) / "docs").exists()


def test_heading_matching_tolerates_qualifiers_and_case():
    from _shared.discipline import missing_artifacts
    required = ["Supplementary Specifications (FURPS)", "Software Requirements Specification (SRS)",
                "Release Description / Release Notes"]
    doc = ("## supplementary specifications\n## 3. Software Requirements Specification\n"
           "## Release Description / Release Notes — v1\n")
    assert missing_artifacts(doc, required) == []
    assert missing_artifacts("### Supplementary Specifications\n", required[:1]) == required[:1], \
        "only level-2 headings count"


def test_record_from_stdin(ctx_env, python_cmd):
    doc = full_document(spec_of("rup-ccm"))
    r = run_skill("rup-ccm", ["--record", "-", "--phase", "Transition"], ctx_env, python_cmd,
                  stdin=doc)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert (Path(ctx_env["RUP_CONTEXT_DIR"]) / "docs" / "04-transition" / "rup-ccm.md").is_file()


def test_record_empty_document_is_rejected(ctx_env, python_cmd, tmp_path):
    r = record("rup-test", ctx_env, python_cmd, tmp_path, doc="   \n")
    assert r.returncode == EXIT_USAGE and "empty" in r.stdout


def test_record_without_briefing_still_writes(ctx_env, python_cmd, tmp_path):
    r = record("rup-environment", ctx_env, python_cmd, tmp_path)
    assert r.returncode == EXIT_OK, r.stdout
    text = (Path(ctx_env["RUP_CONTEXT_DIR"]) / "docs" / "02-elaboration"
            / "rup-environment.md").read_text(encoding="utf-8")
    assert "briefing not provided at record time" in text


@POSIX_NON_ROOT
def test_unwritable_context_exits_4(ctx_env, python_cmd, tmp_path):
    ro = tmp_path / "ro" / ".context"
    authorize(ro)
    ro.chmod(0o500)
    env = dict(ctx_env, RUP_CONTEXT_DIR=str(ro))
    try:
        r = record("rup-requirements", env, python_cmd, tmp_path)
    finally:
        ro.chmod(0o700)
    assert r.returncode == EXIT_CONTEXT_NOT_WRITABLE, r.stdout + r.stderr


def test_packet_is_read_only(ctx_env, python_cmd):
    r = run_skill("rup-test", ["briefing", "--phase", "Transition"], ctx_env, python_cmd)
    assert r.returncode == EXIT_OK
    assert "04-transition" in r.stdout and "rup-test.md" in r.stdout
    assert not (Path(ctx_env["RUP_CONTEXT_DIR"]) / "docs").exists(), \
        "a packet must not write anything"


def test_packets_chain_through_context_in_rup_order(ctx_env, python_cmd, tmp_path):
    """Each packet embeds governance + the earlier disciplines recorded in .context/."""
    marker = {s: f"MARKER-{s.upper()}" for s in (ORCHESTRATOR, "rup-environment", "rup-ccm")}
    for skill, m in marker.items():
        doc = full_document(spec_of(skill)) + f"\n{m}\n"
        assert record(skill, ctx_env, python_cmd, tmp_path, doc=doc).returncode == EXIT_OK

    bm = run_skill("rup-business-modeling", ["b"], ctx_env, python_cmd).stdout
    assert marker[ORCHESTRATOR] in bm and marker["rup-environment"] in bm
    assert marker["rup-ccm"] not in bm, "a later discipline must not leak into an earlier one"
    assert "skill: rup-environment" not in bm, "the provenance header must be stripped"

    env_packet = run_skill("rup-environment", ["b"], ctx_env, python_cmd).stdout
    assert marker[ORCHESTRATOR] in env_packet and marker["rup-environment"] not in env_packet

    deploy = run_skill("rup-deployment", ["b"], ctx_env, python_cmd).stdout
    assert marker["rup-ccm"] in deploy

    gov = run_skill(ORCHESTRATOR, ["b"], ctx_env, python_cmd).stdout
    assert marker["rup-ccm"] in gov and marker[ORCHESTRATOR] not in gov


def test_chaining_is_per_phase(ctx_env, python_cmd, tmp_path):
    doc = full_document(spec_of("rup-environment")) + "\nMARKER-INCEPTION\n"
    assert record("rup-environment", ctx_env, python_cmd, tmp_path, phase="Inception",
                  doc=doc).returncode == EXIT_OK
    out = run_skill("rup-requirements", ["b", "--phase", "Elaboration"], ctx_env, python_cmd).stdout
    assert "MARKER-INCEPTION" not in out


def test_long_earlier_artifacts_are_capped(ctx_env, python_cmd, tmp_path):
    from _shared.rup import MAX_PRIOR_ARTIFACT_CHARS
    doc = full_document(spec_of("rup-environment")) + "z" * (MAX_PRIOR_ARTIFACT_CHARS + 100)
    assert record("rup-environment", ctx_env, python_cmd, tmp_path, doc=doc).returncode == EXIT_OK
    out = run_skill("rup-business-modeling", ["b"], ctx_env, python_cmd).stdout
    assert "[… truncated — full artifact in" in out


def test_status_and_auto_reflect_recorded_steps(ctx_env, python_cmd, tmp_path):
    for skill in (ORCHESTRATOR, "rup-environment"):
        assert record(skill, ctx_env, python_cmd, tmp_path).returncode == EXIT_OK
    st = run_skill(ORCHESTRATOR, ["--status"], ctx_env, python_cmd).stdout
    assert re.search(r"\| 0 \| Governance \| `rup-orchestrator` \| ✅ ", st)
    assert re.search(r"\| 1 \| Environment \| `rup-environment` \| ✅ ", st)
    assert "Next pending step: 2 — Business Modeling" in st
    auto = run_skill(ORCHESTRATOR, ["b", "--auto"], ctx_env, python_cmd).stdout
    assert "Next pending step: 2 — Business Modeling" in auto


def test_discipline_packet_targets_the_callers_project(clean_env, python_cmd, tmp_path):
    """--discipline runs the child with cwd = skills root; .context/ must still be
    the caller's project, not the skills repository."""
    project = tmp_path / "caller-project"
    (project / ".git").mkdir(parents=True)
    env = {k: v for k, v in clean_env.items() if k != "RUP_CONTEXT_DIR"}
    r = run_skill(ORCHESTRATOR, ["b", "--discipline", "requirements"], env, python_cmd,
                  cwd=project)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    expected = (project / ".context" / "docs" / "02-elaboration" / "rup-requirements.md").resolve()
    assert str(expected) in r.stdout


def test_estimate_writes_sizing_artifact_and_keeps_json_clean(ctx_env, python_cmd, tmp_path):
    model = tmp_path / "sizing.json"
    model.write_text(json.dumps({
        "actors": [{"type": "average", "count": 2}, {"type": "complex", "count": 2}],
        "usecases": [{"type": "average", "count": 10}, {"type": "complex", "count": 5}],
    }), encoding="utf-8")
    r = run_skill(ORCHESTRATOR, ["--estimate", "--sizing", str(model), "--json",
                                 "--phase", "Inception"], ctx_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert json.loads(r.stdout)["ucp"] == 185.0, "stdout must stay pure JSON"
    artifact = (Path(ctx_env["RUP_CONTEXT_DIR"]) / "docs" / "01-inception"
                / "rup-orchestrator-sizing.md")
    text = artifact.read_text(encoding="utf-8")
    assert "| UCP (Use Case Points) | 185.0 |" in text
    assert re.search(r"\| Effort @ 20\.0 h/UCP \| 3700\.0 h \|", text)


def test_repo_context_untouched_by_the_suite():
    """Guard: the suite must never write generated artifacts into this repo."""
    generated = list((REPO_ROOT / ".context" / "docs").glob("*/rup-*.md"))
    assert not generated, f"tests leaked artifacts into the repo: {generated}"
    assert not (REPO_ROOT / ".context" / "tracking" / "rup-log.md").exists()
