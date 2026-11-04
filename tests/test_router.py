"""cp-orchestrator --route: the front door that routes a plain request to the right skill."""
from pathlib import Path

import pytest

from conftest import EXIT_OK, EXIT_USAGE, SKILLS_DIR, skill_names
from test_context_persistence import record, run_skill

from _shared import consent, router

ROUTE_KEYS = ["context", "discover", "requirements", "discipline", "governance", "iteration",
              "estimate", "backlog", "build", "debug", "review", "test-audit", "status"]


def _state(**kw):
    st = router.State(Path("/x/.context"), kw.pop("authorized", True))
    for k, v in kw.items():
        setattr(st, k, v)
    return st


def _snapshot(d):
    d = Path(d)
    return sorted(str(p.relative_to(d)) for p in d.rglob("*")) if d.exists() else []


# ─── CLI ────────────────────────────────────────────────────────────────

def test_route_prints_request_state_every_route_and_chains(ctx_env, python_cmd):
    r = run_skill("cp-orchestrator", ["--route", "quero login com Google"], ctx_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    out = r.stdout
    assert "quero login com Google" in out
    assert "`.context/` authorized: yes" in out
    for key in ROUTE_KEYS:
        assert f"| `{key}`" in out, key
    assert "**State suggests**: `discover`" in out
    assert "Never tell the user" in out
    assert "New product / feature / epic" in out


def test_route_needs_no_request_and_no_consent_and_writes_nothing(clean_env, python_cmd,
                                                                    tmp_path):
    env = dict(clean_env, RUP_CONTEXT_DIR=str(tmp_path / "p" / ".context"))
    (tmp_path / "p").mkdir()
    r = run_skill("cp-orchestrator", ["--route"], env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert "authorized: NO" in r.stdout
    assert "**State suggests**: `context`" in r.stdout
    assert not (tmp_path / "p" / ".context").exists()


def test_route_is_read_only_on_an_authorized_context(ctx_env, python_cmd):
    before = _snapshot(ctx_env["RUP_CONTEXT_DIR"])
    r = run_skill("cp-orchestrator", ["--route", "e agora?"], ctx_env, python_cmd)
    assert r.returncode == EXIT_OK
    assert _snapshot(ctx_env["RUP_CONTEXT_DIR"]) == before


def test_route_rejects_record(ctx_env, python_cmd, tmp_path):
    doc = tmp_path / "d.md"
    doc.write_text("## X\n", encoding="utf-8")
    r = run_skill("cp-orchestrator", ["--route", "--record", str(doc)], ctx_env, python_cmd)
    assert r.returncode == EXIT_USAGE
    assert "--route only prints" in r.stdout


def test_route_sees_recorded_discovery_and_suggests_requirements(ctx_env, python_cmd, tmp_path):
    record("cp-discover", ctx_env, python_cmd, tmp_path, phase="Inception")
    r = run_skill("cp-orchestrator", ["--route"], ctx_env, python_cmd)
    assert "Discovery: recorded (Inception)" in r.stdout
    assert "**State suggests**: `requirements`" in r.stdout


def test_route_commands_point_at_existing_skills(ctx_env, python_cmd):
    out = run_skill("cp-orchestrator", ["--route", "x"], ctx_env, python_cmd).stdout
    for skill in ("cp-context", "cp-discover", "cp-backlog", "cp-build", "cp-debug",
                  "cp-review", "cp-test", "cp-orchestrator"):
        script = SKILLS_DIR / skill / "scripts" / "run.py"
        assert str(script) in out, skill
        assert skill in skill_names()


# ─── suggestion order ──────────────────────────────────────────────────────

@pytest.mark.parametrize("state, expected", [
    (dict(authorized=False, columns={"4-review": ["TK-001"]}), "context"),
    (dict(columns={"4-review": ["TK-002"], "3-doing": ["TK-003"]}), "review"),
    (dict(columns={"3-doing": ["TK-003"]}, open_bugs=["BUG-001"]), "build"),
    (dict(columns={"2-todo": ["BUG-001"]}, open_bugs=["BUG-001"]), "debug"),
    (dict(), "discover"),
    (dict(discovery="Inception"), "requirements"),
    (dict(discovery="Inception", requirements=["Inception"]), "backlog"),
    (dict(discovery="Inception", requirements=["Inception"],
          columns={"1-backlog": ["EP-001"], "2-todo": ["TK-004"]}), "build"),
    (dict(discovery="Inception", requirements=["Inception"],
          columns={"1-backlog": ["TK-005"]}), "backlog"),
    (dict(discovery="Inception", requirements=["Inception"],
          columns={"7-done": ["TK-006"]}), "status"),
])
def test_suggest_follows_the_flow(state, expected):
    key, why = router.suggest(_state(**state))
    assert key == expected
    assert why


def test_suggest_names_the_cards():
    _, why = router.suggest(_state(columns={"4-review": ["TK-010", "BUG-002"]}))
    assert "TK-010" in why and "BUG-002" in why


def test_read_state_survives_a_broken_card(tmp_path, capsys):
    ctx = tmp_path / ".context"
    for col in ("1-backlog", "2-todo"):
        (ctx / "kanban" / col).mkdir(parents=True)
        (ctx / "kanban" / col / "TK-001.md").write_text("---\nid: TK-001\n---\n", "utf-8")
    st = router.read_state(ctx)
    assert st.card_error
    assert "could not be read" in router.render("x", st, lambda *a: " ".join(a))


def test_read_state_lists_board_and_open_bugs(tmp_path):
    ctx = tmp_path / ".context"
    for col, cid in (("2-todo", "BUG-001"), ("7-done", "BUG-002"), ("3-doing", "TK-001")):
        (ctx / "kanban" / col).mkdir(parents=True)
        (ctx / "kanban" / col / f"{cid}.md").write_text(f"---\nid: {cid}\n---\n", "utf-8")
    st = router.read_state(ctx)
    assert st.columns == {"2-todo": ["BUG-001"], "3-doing": ["TK-001"], "7-done": ["BUG-002"]}
    assert st.open_bugs == ["BUG-001"]


# ─── discoverability ────────────────────────────────────────────────────────

def test_orchestrator_skill_md_is_the_front_door():
    text = (SKILLS_DIR / "cp-orchestrator" / "SKILL.md").read_text(encoding="utf-8")
    head = text.split("---")[1]
    assert "FRONT DOOR" in head and "never has to name a skill" in head
    assert "--route" in text


def test_pointer_note_routes_through_the_orchestrator():
    assert 'cp-orchestrator --route "<request>"' in consent.POINTER_BODY


def test_pointer_note_refreshes_an_outdated_block(tmp_path):
    old = f"# Mine\n\nkeep me\n\n{consent.POINTER_START}\n## old list\n{consent.POINTER_END}\n\nafter\n"
    (tmp_path / "CLAUDE.md").write_text(old, encoding="utf-8")
    touched = consent.ensure_pointer_note(tmp_path)
    text = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert tmp_path / "CLAUDE.md" in touched
    assert "## old list" not in text and "--route" in text
    assert text.startswith("# Mine\n\nkeep me\n\n") and text.endswith(f"{consent.POINTER_END}\n\nafter\n")
    assert tmp_path / "CLAUDE.md" not in consent.ensure_pointer_note(tmp_path)  # idempotent


def test_pointer_note_leaves_a_broken_block_alone(tmp_path):
    broken = f"x\n{consent.POINTER_START}\nno end marker\n"
    (tmp_path / "CLAUDE.md").write_text(broken, encoding="utf-8")
    consent.ensure_pointer_note(tmp_path)
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == broken
