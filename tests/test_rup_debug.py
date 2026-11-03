"""cp-debug: --open / --diagnose of a bug, and the bug checks of cp-build --finish (INIT-03 §7.4, §7.8)."""
from pathlib import Path

import pytest

from conftest import EXIT_NEEDS_CONSENT, EXIT_OK, EXIT_USAGE
from test_context_persistence import run_skill

from _shared import cards, testcheck

EPIC = "## Goal\n\nSchedule visits.\n\n## Scope\n\nBooking only.\n"
STORY = ("## User story\n\nAs a patient I want to book so that I save time.\n\n"
         "## Acceptance criteria\n\n- Patient picks a slot\n\n"
         "## Definition of Done\n\n- Tests pass\n")
BUG_DOC = "## Symptom\n\nBooking twice crashes.\n\n## Reproduction\n\n1. book 09:00\n2. book 09:00\n"
DIAG = "## Root cause\n\nThe slot set is never checked before insert.\n"
TEST_SRC = ("from app.booking import book\n\n\n"
            "def test_double_booking_bug_001():\n    assert book('09:00') == 'booked'\n")
TEST_NO_ID = ("from app.booking import book\n\n\n"
              "def test_double_booking():\n    assert book('09:00') == 'booked'\n")
REF = "tests/test_booking.py::test_double_booking_bug_001"
REF_NO_ID = "tests/test_booking.py::test_double_booking"


def delivery(ref, covers="BUG-001"):
    return (f"## What was done\n\nChecked the slot set before insert.\n\n"
            f"## Files changed\n\n- app/booking.py\n\n"
            f"## Tests\n\n- {ref} — covers {covers}\n\n"
            f"## Red evidence\n\n### {ref}\n\n```\nE   AssertionError\n```\n")


@pytest.fixture
def proj(ctx_env):
    ctx = Path(ctx_env["RUP_CONTEXT_DIR"])
    root = ctx.parent
    (root / "app").mkdir(parents=True, exist_ok=True)
    (root / "app" / "booking.py").write_text("def book(s):\n    return 'booked'\n", encoding="utf-8")
    return ctx, root


def dbg(args, env, python_cmd, stdin=None):
    return run_skill("cp-debug", args, env, python_cmd, stdin=stdin)


def build(args, env, python_cmd, stdin=None):
    return run_skill("cp-build", args, env, python_cmd, stdin=stdin)


def put_test(root, text):
    p = root / "tests" / "test_booking.py"
    p.parent.mkdir(exist_ok=True)
    p.write_text(text, encoding="utf-8")


def open_bug(env, python_cmd, extra=()):
    return dbg(["--open", "--title", "Double booking crashes", "--doc", "-", *extra],
               env, python_cmd, stdin=BUG_DOC)


def test_open_creates_bug_with_required_sections(proj, ctx_env, python_cmd):
    ctx, _ = proj
    r = open_bug(ctx_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    card = cards.get(ctx, "BUG-001")
    assert card.type == "bug" and card.status == "1-backlog"
    assert "## Symptom" in card.body and "## Reproduction" in card.body
    assert "--diagnose BUG-001" in r.stdout
    assert "--start BUG-001" in r.stdout and "--finish BUG-001" in r.stdout
    assert "BUG-001" in r.stdout and "root cause" in r.stdout.lower()


def test_open_with_parent_story_and_missing_sections(proj, ctx_env, python_cmd):
    ctx, _ = proj
    cards.create(ctx, "epic", "Booking", EPIC)
    cards.create(ctx, "story", "Book a visit", STORY, parent="EP-001")
    r = open_bug(ctx_env, python_cmd, ["--parent", "ST-001", "--priority", "Must"])
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert cards.get(ctx, "BUG-001").meta["parent"] == "ST-001"
    bad = dbg(["--open", "--title", "x", "--doc", "-"], ctx_env, python_cmd, stdin="## Symptom\n\nonly\n")
    assert bad.returncode == EXIT_USAGE, bad.stdout + bad.stderr


def test_diagnose_records_root_cause(proj, ctx_env, python_cmd):
    ctx, _ = proj
    open_bug(ctx_env, python_cmd)
    r = dbg(["--diagnose", "BUG-001", "--doc", "-"], ctx_env, python_cmd, stdin=DIAG)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    card = cards.get(ctx, "BUG-001")
    assert card.status == "3-doing"
    assert "## Root cause" in card.body and "never checked before insert" in card.body
    assert "diagnosed" in card.body
    # re-diagnose replaces and logs
    r = dbg(["--diagnose", "BUG-001", "--doc", "-"], ctx_env, python_cmd,
            stdin="## Root cause\n\nActually a race.\n")
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    card = cards.get(ctx, "BUG-001")
    assert card.status == "3-doing" and card.body.count("## Root cause") == 1
    assert "Actually a race." in card.body and "never checked" not in card.body
    assert "root cause updated" in card.body


def test_diagnose_refusals(proj, ctx_env, python_cmd):
    ctx, _ = proj
    open_bug(ctx_env, python_cmd)
    r = dbg(["--diagnose", "BUG-001", "--doc", "-"], ctx_env, python_cmd, stdin="## Root cause\n\n\n")
    assert r.returncode == EXIT_USAGE
    r = dbg(["--diagnose", "BUG-001", "--doc", "-"], ctx_env, python_cmd, stdin="## Other\n\nx\n")
    assert r.returncode == EXIT_USAGE
    assert "Root cause" not in cards.get(ctx, "BUG-001").body
    cards.create(ctx, "epic", "Booking", EPIC)
    r = dbg(["--diagnose", "EP-001", "--doc", "-"], ctx_env, python_cmd, stdin=DIAG)
    assert r.returncode == EXIT_USAGE
    cards.move(ctx, "BUG-001", "4-review", "x")
    r = dbg(["--diagnose", "BUG-001", "--doc", "-"], ctx_env, python_cmd, stdin=DIAG)
    assert r.returncode == EXIT_USAGE
    assert cards.get(ctx, "BUG-001").status == "4-review"


def test_debug_requires_consent(proj, ctx_env, python_cmd):
    ctx, _ = proj
    open_bug(ctx_env, python_cmd)
    (ctx / ".rup-standard").unlink()
    r = dbg(["--diagnose", "BUG-001", "--doc", "-"], ctx_env, python_cmd, stdin=DIAG)
    assert r.returncode == EXIT_NEEDS_CONSENT, r.stdout + r.stderr
    assert cards.get(ctx, "BUG-001").status == "1-backlog"


def test_finish_bug_without_root_cause_refused(proj, ctx_env, python_cmd):
    ctx, root = proj
    put_test(root, TEST_SRC)
    open_bug(ctx_env, python_cmd)
    assert build(["--start", "BUG-001"], ctx_env, python_cmd).returncode == EXIT_OK
    before = cards.get(ctx, "BUG-001").path.read_text(encoding="utf-8")
    r = build(["--finish", "BUG-001", "--delivery", "-"], ctx_env, python_cmd, stdin=delivery(REF))
    assert r.returncode == EXIT_USAGE, r.stdout + r.stderr
    assert "cp-debug --diagnose" in r.stdout + r.stderr
    card = cards.get(ctx, "BUG-001")
    assert card.status == "3-doing" and card.path.read_text(encoding="utf-8") == before


def test_finish_bug_records_fix_and_regression_test(proj, ctx_env, python_cmd):
    ctx, root = proj
    put_test(root, TEST_SRC)
    open_bug(ctx_env, python_cmd)
    dbg(["--diagnose", "BUG-001", "--doc", "-"], ctx_env, python_cmd, stdin=DIAG)
    r = build(["--finish", "BUG-001", "--delivery", "-"], ctx_env, python_cmd, stdin=delivery(REF))
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    card = cards.get(ctx, "BUG-001")
    assert card.status == "4-review"
    assert "## Fix\n\nChecked the slot set before insert." in card.body
    assert "## Regression test" in card.body and f"{REF} — covers BUG-001" in card.body
    assert "## Delivery" in card.body


def test_finish_bug_with_unrelated_parent_card_still_works(proj, ctx_env, python_cmd):
    ctx, root = proj
    put_test(root, TEST_SRC)
    cards.create(ctx, "epic", "Booking", EPIC)
    cards.create(ctx, "story", "Book a visit", STORY, parent="EP-001")
    open_bug(ctx_env, python_cmd, ["--parent", "ST-001"])
    dbg(["--diagnose", "BUG-001", "--doc", "-"], ctx_env, python_cmd, stdin=DIAG)
    r = build(["--finish", "BUG-001", "--delivery", "-"], ctx_env, python_cmd, stdin=delivery(REF))
    assert r.returncode == EXIT_OK, r.stdout + r.stderr


def test_regression_test_must_reference_bug_id(proj, ctx_env, python_cmd):
    ctx, root = proj
    put_test(root, TEST_NO_ID)
    open_bug(ctx_env, python_cmd)
    dbg(["--diagnose", "BUG-001", "--doc", "-"], ctx_env, python_cmd, stdin=DIAG)
    r = build(["--finish", "BUG-001", "--delivery", "-"], ctx_env, python_cmd,
              stdin=delivery(REF_NO_ID))
    assert r.returncode == EXIT_USAGE, r.stdout + r.stderr
    assert "BUG-001" in r.stdout + r.stderr
    assert cards.get(ctx, "BUG-001").status == "3-doing"


def test_delivery_section_accessor_is_tolerant():
    d = testcheck.parse_delivery("## What was done (summary)\n\nText\n\n## Tests\n\n- x\n")
    assert d.section("what was done") == "Text"
    assert d.section("Missing") == ""


def test_diagnose_sets_the_branch(ctx_env, python_cmd):
    ctx = Path(ctx_env["RUP_CONTEXT_DIR"])
    cards.create(ctx, "bug", "Double booking!", BUG_DOC)
    r = run_skill("cp-debug", ["--diagnose", "BUG-001", "--doc", "-"], ctx_env, python_cmd, stdin=DIAG)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    card = cards.get(ctx, "BUG-001")
    assert card.status == "3-doing" and card.meta["branch"] == "bug-001-double-booking"
    assert cards.branch_name(card) == card.meta["branch"]
    again = run_skill("cp-debug", ["--diagnose", "BUG-001", "--doc", "-"], ctx_env, python_cmd, stdin=DIAG)
    assert again.returncode == EXIT_OK
    assert cards.get(ctx, "BUG-001").meta["branch"] == "bug-001-double-booking"


def test_open_protocol_says_start_only_when_not_diagnosed(ctx_env, python_cmd):
    r = run_skill("cp-debug", ["--open", "--title", "T", "--doc", "-"], ctx_env, python_cmd, stdin=BUG_DOC)
    assert "(only if not diagnosed)" in r.stdout
