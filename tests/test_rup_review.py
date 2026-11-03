"""rup-review: checklist packet and verdict record (INIT-03 §7.9)."""
from pathlib import Path

import pytest

from conftest import EXIT_OK, EXIT_USAGE
from test_context_persistence import run_skill

from _shared import cards

SKILL = "rup-review"

EPIC = "## Goal\n\nSchedule visits.\n\n## Scope\n\nBooking only.\n"
STORY = ("## User story\n\nAs a patient I want to book so that I save time.\n\n"
         "## Acceptance criteria\n\n- Patient picks a slot\n\n"
         "## Definition of Done\n\n- Tests pass\n")
TASK = ("## Description\n\nDo it.\n\n## Target files\n\n- app/booking.py\n- app/slots.py\n\n"
        "## Covers\n\n- ST-001/AC-1\n")
GOOD_TEST = ("from app.booking import book\n\n\n"
             "def test_book_slot_st_001_ac_1():\n    assert book('09:00') == 'booked'\n")
REF = "tests/test_booking.py::test_book_slot_st_001_ac_1"
DELIVERY = ("## What was done\n\nImplemented booking.\n\n"
            "## Files changed\n\n- `app/booking.py`\n- app/extra.py\n\n"
            f"## Tests\n\n- {REF} — covers ST-001/AC-1\n\n"
            f"## Red evidence\n\n### {REF}\n\n```\nE   ImportError\n```\n")


@pytest.fixture
def proj(ctx_env):
    ctx = Path(ctx_env["RUP_CONTEXT_DIR"])
    cards.create(ctx, "epic", "Booking", EPIC)
    cards.create(ctx, "story", "Book a visit", STORY, parent="EP-001")
    task = cards.create(ctx, "task", "Add booking", TASK, parent="ST-001")
    cards.set_meta(task, "branch", "tk-001-add-booking")
    root = ctx.parent
    (root / "app").mkdir(parents=True, exist_ok=True)
    (root / "app" / "booking.py").write_text("def book(s):\n    return 'booked'\n", encoding="utf-8")
    (root / "tests").mkdir(exist_ok=True)
    (root / "tests" / "test_booking.py").write_text(GOOD_TEST, encoding="utf-8")
    task = cards.get(ctx, "TK-001")
    cards.set_section(task, "Delivery", DELIVERY)
    cards.move(ctx, "TK-001", "4-review", "delivered")
    return ctx, root


def run(args, env, python_cmd, stdin=None):
    return run_skill(SKILL, args, env, python_cmd, stdin=stdin)


def doc(verdict, findings):
    return f"## Verdict\n\n{verdict}\n\n## Findings\n\n{findings}\n"


def test_review_packet_requires_card_in_review(proj, ctx_env, python_cmd):
    ctx, _ = proj
    cards.move(ctx, "TK-001", "3-doing", "x")
    r = run(["TK-001"], ctx_env, python_cmd)
    assert r.returncode == EXIT_USAGE, r.stdout + r.stderr
    assert "3-doing" in r.stdout
    r = run(["--record", "TK-001", "--doc", "-"], ctx_env, python_cmd, stdin=doc("approved", "none"))
    assert r.returncode == EXIT_USAGE
    assert cards.get(ctx, "TK-001").status == "3-doing"


def test_review_packet_flags_files_outside_target(proj, ctx_env, python_cmd):
    r = run(["TK-001"], ctx_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    out = r.stdout
    assert "Outside target files:" in out and "app/extra.py" in out
    assert "Target files not changed:" in out and "app/slots.py" in out
    assert "ST-001/AC-1" in out and REF in out
    assert "Test checks: OK" in out
    assert "EP-001" in out and "ST-001" in out
    assert "tk-001-add-booking" in out and "7-done" in out
    assert "--record TK-001 --doc" in out


def test_approved_moves_to_testing(proj, ctx_env, python_cmd):
    ctx, _ = proj
    r = run(["--record", "TK-001", "--doc", "-"], ctx_env, python_cmd,
            stdin=doc("Approved", "- none"))
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    card = cards.get(ctx, "TK-001")
    assert card.status == "5-testing"
    assert "## Review" in card.body and "— approved" in card.body
    assert "review approved" in card.body


def test_changes_requested_moves_back_to_doing_with_reason(proj, ctx_env, python_cmd):
    ctx, _ = proj
    r = run(["--record", "TK-001", "--doc", "-"], ctx_env, python_cmd,
            stdin=doc("changes requested", "- app/extra.py is out of scope\n- add a test"))
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    card = cards.get(ctx, "TK-001")
    assert card.status == "3-doing"
    assert "changes requested: app/extra.py is out of scope" in card.body
    # second round: previous review is kept
    cards.move(ctx, "TK-001", "4-review", "delivered again")
    r = run(["--record", "TK-001", "--doc", "-"], ctx_env, python_cmd,
            stdin=doc("approved", "all good"))
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    body = cards.get(ctx, "TK-001").body
    assert "app/extra.py is out of scope" in body and "all good" in body
    assert body.count("### ") >= 2 and body.index("## Review") < body.index("## History")


def test_invalid_verdict_exits_1(proj, ctx_env, python_cmd):
    ctx, _ = proj
    before = cards.get(ctx, "TK-001").path.read_text(encoding="utf-8")
    for text in (doc("maybe", "x"), "## Verdict\n\napproved\n", doc("\n", "x")):
        r = run(["--record", "TK-001", "--doc", "-"], ctx_env, python_cmd, stdin=text)
        assert r.returncode == EXIT_USAGE, r.stdout + r.stderr
    card = cards.get(ctx, "TK-001")
    assert card.status == "4-review"
    assert card.path.read_text(encoding="utf-8") == before
