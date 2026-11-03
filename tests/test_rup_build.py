"""rup-build: --start / --finish of a task (INIT-03 §7.7)."""
from pathlib import Path

import pytest

from conftest import EXIT_NEEDS_CONSENT, EXIT_OK, EXIT_USAGE
from test_context_persistence import run_skill

from _shared import cards, frontmatter

SKILL = "rup-build"

EPIC = "## Goal\n\nSchedule visits.\n\n## Scope\n\nBooking only.\n"
STORY = ("## User story\n\nAs a patient I want to book so that I save time.\n\n"
         "## Acceptance criteria\n\n- Patient picks a slot\n\n"
         "## Definition of Done\n\n- Tests pass\n")
TASK = ("## Description\n\nDo it.\n\n## Target files\n\n- app/booking.py\n\n"
        "## Covers\n\n- ST-001/AC-1\n")

GOOD_TEST = ("from app.booking import book\n\n\n"
             "def test_book_slot_st_001_ac_1():\n    assert book('09:00') == 'booked'\n")
TRIVIAL_TEST = ("from app.booking import book\n\n\n"
                "def test_book_slot_st_001_ac_1():\n    book('09:00')\n    assert True\n")
REF = "tests/test_booking.py::test_book_slot_st_001_ac_1"
DELIVERY = (f"## What was done\n\nImplemented booking.\n\n## Files changed\n\n- app/booking.py\n\n"
            f"## Tests\n\n- {REF} — covers ST-001/AC-1\n\n"
            f"## Red evidence\n\n### {REF}\n\n```\nE   ImportError\n```\n")


@pytest.fixture
def proj(ctx_env, tmp_path):
    ctx = Path(ctx_env["RUP_CONTEXT_DIR"])
    cards.create(ctx, "epic", "Booking", EPIC)
    cards.create(ctx, "story", "Book a visit", STORY, parent="EP-001")
    cards.create(ctx, "task", "Add the Booking endpoint!", TASK, parent="ST-001")
    root = ctx.parent
    (root / "app").mkdir(parents=True, exist_ok=True)
    (root / "app" / "booking.py").write_text("def book(s):\n    return 'booked'\n", encoding="utf-8")
    return ctx, root


def run(args, env, python_cmd, stdin=None):
    return run_skill(SKILL, args, env, python_cmd, stdin=stdin)


def put_test(root, text):
    p = root / "tests" / "test_booking.py"
    p.parent.mkdir(exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_start_moves_to_doing_sets_branch_and_prints_packet(proj, ctx_env, python_cmd):
    ctx, _ = proj
    r = run(["--start", "TK-001"], ctx_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    card = cards.get(ctx, "TK-001")
    assert card.status == "3-doing"
    assert card.meta["branch"] == "tk-001-add-the-booking-endpoint"
    assert "tk-001-add-the-booking-endpoint" in r.stdout
    assert "ST-001/AC-1" in r.stdout and "Patient picks a slot" in r.stdout
    assert "app/booking.py" in r.stdout
    assert "--finish TK-001 --delivery" in r.stdout
    assert "red" in r.stdout.lower() and "commit" in r.stdout.lower()


def test_start_from_wrong_column_exits_1(proj, ctx_env, python_cmd):
    ctx, _ = proj
    cards.move(ctx, "TK-001", "4-review", "x")
    r = run(["--start", "TK-001"], ctx_env, python_cmd)
    assert r.returncode == EXIT_USAGE, r.stdout + r.stderr
    assert cards.get(ctx, "TK-001").status == "4-review"


def test_finish_with_good_delivery_records_and_moves_to_review(proj, ctx_env, python_cmd):
    ctx, root = proj
    put_test(root, GOOD_TEST)
    assert run(["--start", "TK-001"], ctx_env, python_cmd).returncode == EXIT_OK
    r = run(["--finish", "TK-001", "--delivery", "-"], ctx_env, python_cmd, stdin=DELIVERY)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    card = cards.get(ctx, "TK-001")
    assert card.status == "4-review"
    assert "## Delivery" in card.body and "Implemented booking." in card.body
    assert card.body.index("## Delivery") < card.body.index("## History")


def test_finish_with_trivial_test_refuses_and_writes_nothing(proj, ctx_env, python_cmd):
    ctx, root = proj
    put_test(root, TRIVIAL_TEST)
    run(["--start", "TK-001"], ctx_env, python_cmd)
    before = cards.get(ctx, "TK-001").path.read_text(encoding="utf-8")
    r = run(["--finish", "TK-001", "--delivery", "-"], ctx_env, python_cmd, stdin=DELIVERY)
    assert r.returncode == EXIT_USAGE, r.stdout + r.stderr
    assert "Delivery rejected:" in r.stdout + r.stderr
    card = cards.get(ctx, "TK-001")
    assert card.status == "3-doing" and card.path.read_text(encoding="utf-8") == before


def test_finish_requires_doing(proj, ctx_env, python_cmd):
    ctx, root = proj
    put_test(root, GOOD_TEST)
    r = run(["--finish", "TK-001", "--delivery", "-"], ctx_env, python_cmd, stdin=DELIVERY)
    assert r.returncode == EXIT_USAGE, r.stdout + r.stderr
    assert cards.get(ctx, "TK-001").status == "1-backlog"


def test_build_requires_consent(proj, ctx_env, python_cmd):
    ctx, _ = proj
    (ctx / ".rup-standard").unlink()
    r = run(["--start", "TK-001"], ctx_env, python_cmd)
    assert r.returncode == EXIT_NEEDS_CONSENT, r.stdout + r.stderr
    assert cards.get(ctx, "TK-001").status == "1-backlog"
