"""Cards: model, IDs, creation and the cp-backlog --new/--show/--list CLI."""
from pathlib import Path

import pytest

from conftest import EXIT_NEEDS_CONSENT, EXIT_OK, EXIT_USAGE, authorize
from test_context_persistence import run_skill

from _shared import cards, frontmatter

SKILL = "cp-backlog"

EPIC = "## Goal\n\nSchedule visits.\n\n## Scope\n\nBooking only.\n"
STORY = ("## User story\n\nAs a patient I want to book so that I save time.\n\n"
         "## Acceptance criteria\n\n- Patient picks a slot\n- Patient gets a confirmation\n\n"
         "## Definition of Done\n\n- Tests pass\n")


def task_doc(covers="- ST-001/AC-1\n"):
    return ("## Description\n\nDo it.\n\n## Target files\n\n- a.py\n\n"
            f"## Covers\n\n{covers}")


@pytest.fixture
def ctx(tmp_path):
    d = tmp_path / ".context"
    authorize(d)
    return d


def make_story(ctx):
    cards.create(ctx, "epic", "Booking", EPIC)
    return cards.create(ctx, "story", "Book a visit", STORY, parent="EP-001")


def test_create_story_numbers_criteria(ctx):
    story = make_story(ctx)
    assert story.id == "ST-001"
    assert story.path == ctx / "kanban" / "1-backlog" / "ST-001.md"
    assert "- **ST-001/AC-1**: Patient picks a slot" in story.body
    assert "- **ST-001/AC-2**: Patient gets a confirmation" in story.body
    assert cards.acceptance_criteria(story) == ["ST-001/AC-1", "ST-001/AC-2"]
    meta, body = frontmatter.parse(story.path.read_text(encoding="utf-8"))
    assert list(meta)[:9] == ["id", "type", "title", "status", "parent", "priority",
                              "source", "created_at", "updated_at"]
    assert meta["status"] == "1-backlog" and meta["priority"] == "Should"
    assert body.startswith("# ST-001 — Book a visit")
    assert "created in 1-backlog" in body.split("## History")[1]
    epic = cards.get(ctx, "EP-001")
    assert epic.meta["release"] == "" and epic.meta["iteration"] == ""
    assert "created ST-001 (story) in 1-backlog" in (
        ctx / "tracking" / "rup-log.md").read_text(encoding="utf-8")


def test_number_criteria_keeps_numbered():
    body = "## Acceptance criteria\n\n- **ST-002/AC-1**: kept\n- new one\n\n## Other\n\n- x\n"
    out = cards.number_criteria("ST-002", body)
    assert "- **ST-002/AC-1**: kept" in out and "- **ST-002/AC-2**: new one" in out
    assert "- x" in out


def test_ids_are_sequential_per_type(ctx):
    assert cards.create(ctx, "epic", "A", EPIC).id == "EP-001"
    assert cards.create(ctx, "epic", "B", EPIC).id == "EP-002"
    assert cards.create(ctx, "story", "S", STORY, parent="EP-002").id == "ST-001"
    assert cards.next_id(ctx, "epic") == "EP-003"
    assert cards.next_id(ctx, "task") == "TK-001"


def test_missing_section_rejected_nothing_written(ctx, capsys):
    with pytest.raises(SystemExit) as e:
        cards.create(ctx, "epic", "A", "## Goal\n\nonly goal\n")
    assert e.value.code == EXIT_USAGE
    assert "Scope" in capsys.readouterr().out
    assert not list((ctx / "kanban").rglob("*.md"))


def test_task_requires_existing_story_parent(ctx):
    make_story(ctx)
    for parent in (None, "ST-099", "EP-001"):
        with pytest.raises(SystemExit) as e:
            cards.create(ctx, "task", "T", task_doc(), parent=parent)
        assert e.value.code == EXIT_USAGE
    assert cards.create(ctx, "task", "T", task_doc(), parent="ST-001").id == "TK-001"


def test_task_covers_must_exist_in_story(ctx, capsys):
    make_story(ctx)
    with pytest.raises(SystemExit) as e:
        cards.create(ctx, "task", "T", task_doc("- ST-001/AC-9\n"), parent="ST-001")
    assert e.value.code == EXIT_USAGE and "ST-001/AC-9" in capsys.readouterr().out
    task = cards.create(ctx, "task", "T", task_doc("- ST-001/AC-1\n- ST-001/AC-2\n"),
                        parent="ST-001")
    assert cards.covers(task) == ["ST-001/AC-1", "ST-001/AC-2"]


@pytest.mark.parametrize("title", ["", "  ", "[x]", "a\nb"])
def test_bad_titles_rejected(ctx, title):
    with pytest.raises(SystemExit) as e:
        cards.create(ctx, "epic", title, EPIC)
    assert e.value.code == EXIT_USAGE


def test_bad_priority_and_history_rejected(ctx):
    with pytest.raises(SystemExit):
        cards.create(ctx, "epic", "A", EPIC, priority="Maybe")
    with pytest.raises(SystemExit):
        cards.create(ctx, "epic", "A", EPIC + "\n## History\n\nx\n")
    assert not list((ctx / "kanban").rglob("*.md"))


def test_folder_wins_over_status_field(ctx):
    cards.create(ctx, "epic", "A", EPIC)
    src = ctx / "kanban" / "1-backlog" / "EP-001.md"
    dst = ctx / "kanban" / "3-doing" / "EP-001.md"
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.replace(dst)  # file moved by hand; frontmatter still says 1-backlog
    card = cards.load_all(ctx)["EP-001"]
    assert card.status == "3-doing" and card.meta["status"] == "3-doing"


def test_id_falls_back_to_filename(ctx):
    d = ctx / "kanban" / "2-todo"
    d.mkdir(parents=True)
    (d / "ST-007.md").write_text("---\ntitle: x\n---\n\nbody\n", encoding="utf-8")
    assert "ST-007" in cards.load_all(ctx)


def test_duplicate_id_exits_1_naming_both(ctx, capsys):
    cards.create(ctx, "epic", "A", EPIC)
    other = ctx / "kanban" / "2-todo"
    other.mkdir(parents=True, exist_ok=True)
    (other / "EP-001.md").write_text(
        (ctx / "kanban" / "1-backlog" / "EP-001.md").read_text(encoding="utf-8"),
        encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        cards.load_all(ctx)
    out = capsys.readouterr().out
    assert e.value.code == EXIT_USAGE
    assert str(ctx / "kanban" / "1-backlog" / "EP-001.md") in out
    assert str(other / "EP-001.md") in out


def test_set_section_replaces_and_appends(ctx):
    card = cards.create(ctx, "epic", "A", EPIC)
    card = cards.set_section(card, "Goal", "New goal.")
    card = cards.set_section(card, "Delivery", "Done.")
    text = card.path.read_text(encoding="utf-8")
    assert "New goal." in text and "Schedule visits." not in text
    assert "## Delivery\n\nDone." in text and "## Scope" in text
    assert cards.get(ctx, "EP-001").body.count("## Goal") == 1


def test_get_unknown_exits_1(ctx):
    with pytest.raises(SystemExit) as e:
        cards.get(ctx, "EP-404")
    assert e.value.code == EXIT_USAGE


# ─── Moves and roll-up ───

def story_with_tasks(ctx, n=2):
    make_story(ctx)
    for i in range(n):
        cards.create(ctx, "task", f"T{i}", task_doc(), parent="ST-001")


def col(ctx, card_id):
    return cards.get(ctx, card_id).status


def test_move_updates_folder_status_history_and_log(ctx):
    cards.create(ctx, "epic", "A", EPIC)
    card = cards.move(ctx, "EP-001", "2-todo", "planned", actor="renato")
    assert card.status == "2-todo"
    assert not (ctx / "kanban" / "1-backlog" / "EP-001.md").exists()
    path = ctx / "kanban" / "2-todo" / "EP-001.md"
    meta, body = frontmatter.parse(path.read_text(encoding="utf-8"))
    assert meta["status"] == "2-todo"
    assert "1-backlog → 2-todo — planned (renato)" in body.split("## History")[1]
    assert "⚠️" not in body
    assert "moved EP-001 1-backlog → 2-todo: planned" in (
        ctx / "tracking" / "rup-log.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("card_id,column,reason", [
    ("EP-001", "9-nope", "x"), ("EP-404", "2-todo", "x"),
    ("EP-001", "1-backlog", "x"), ("EP-001", "2-todo", "  ")])
def test_move_unknown_column_or_id_changes_nothing(ctx, card_id, column, reason):
    cards.create(ctx, "epic", "A", EPIC)
    before = (ctx / "kanban" / "1-backlog" / "EP-001.md").read_text(encoding="utf-8")
    log = (ctx / "tracking" / "rup-log.md").read_text(encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        cards.move(ctx, card_id, column, reason)
    assert e.value.code == EXIT_USAGE
    assert (ctx / "kanban" / "1-backlog" / "EP-001.md").read_text(encoding="utf-8") == before
    assert (ctx / "tracking" / "rup-log.md").read_text(encoding="utf-8") == log
    assert [p.name for p in (ctx / "kanban").rglob("*.md")] == ["EP-001.md"]


def test_skip_columns_warns_but_moves(ctx):
    cards.create(ctx, "epic", "A", EPIC)
    cards.move(ctx, "EP-001", "5-testing", "jump")
    text = cards.get(ctx, "EP-001").path.read_text(encoding="utf-8")
    assert "(agent) ⚠️ skipped 2-todo, 3-doing, 4-review" in text
    cards.move(ctx, "EP-001", "blocked", "stuck")
    cards.move(ctx, "EP-001", "1-backlog", "unstuck")
    cards.move(ctx, "EP-001", "2-todo", "back")  # forward by one: no warning
    text = cards.get(ctx, "EP-001").path.read_text(encoding="utf-8")
    assert text.count("⚠️") == 1


def test_set_section_adds_before_history_and_move_stays_in_history(ctx):
    card = cards.create(ctx, "epic", "A", EPIC)
    card = cards.set_section(card, "Delivery", "Done it.")
    sections = [l for l in card.body.splitlines() if l.startswith("## ")]
    assert sections == ["## Goal", "## Scope", "## Delivery", "## History"]
    cards.set_section(card, "Delivery", "Done again.")
    moved = cards.move(ctx, "EP-001", "4-review", "finish")
    text = moved.path.read_text(encoding="utf-8")
    sections = [l for l in text.splitlines() if l.startswith("## ")]
    assert sections[-1] == "## History"
    delivery = text.split("## Delivery")[1].split("## History")[0]
    assert "Done again." in delivery and "finish" not in delivery
    assert "→ 4-review — finish (agent)" in text.split("## History")[1]
    assert "created in 1-backlog" in text.split("## History")[1]


def test_story_rolls_to_doing_when_first_task_starts(ctx):
    story_with_tasks(ctx)
    cards.move(ctx, "TK-001", "3-doing", "start")
    assert col(ctx, "ST-001") == "3-doing" and col(ctx, "EP-001") == "3-doing"
    text = cards.get(ctx, "ST-001").path.read_text(encoding="utf-8")
    assert "roll-up: TK-001 started (cp-backlog)" in text
    cards.move(ctx, "TK-002", "4-review", "go")
    assert col(ctx, "ST-001") == "3-doing"
    assert text.count("roll-up") == 1


def test_blocked_child_does_not_start_parent(ctx):
    story_with_tasks(ctx)
    cards.move(ctx, "TK-001", "blocked", "waiting")
    assert col(ctx, "ST-001") == "1-backlog"


def test_story_and_epic_roll_to_done_when_all_children_done(ctx):
    story_with_tasks(ctx)
    cards.create(ctx, "bug", "B", "## Symptom\n\nx\n\n## Reproduction\n\ny\n",
                 parent="ST-001")
    cards.move(ctx, "TK-001", "7-done", "ok")
    assert col(ctx, "ST-001") == "3-doing"
    cards.move(ctx, "TK-002", "7-done", "ok")
    assert col(ctx, "ST-001") == "3-doing"  # the bug child is still open
    cards.move(ctx, "BUG-001", "7-done", "ok")
    assert col(ctx, "ST-001") == "7-done" and col(ctx, "EP-001") == "7-done"
    text = cards.get(ctx, "EP-001").path.read_text(encoding="utf-8")
    assert "roll-up: all children done (cp-backlog)" in text


def test_move_without_rollup_leaves_parent(ctx):
    story_with_tasks(ctx)
    cards.move(ctx, "TK-001", "3-doing", "start", rollup=False)
    assert col(ctx, "ST-001") == "1-backlog"


def test_move_requires_consent(tmp_path, capsys):
    d = tmp_path / ".context"
    authorize(d)
    cards.create(d, "epic", "A", EPIC)
    (d / ".rup-standard").unlink()
    with pytest.raises(SystemExit) as e:
        cards.move(d, "EP-001", "2-todo", "x")
    assert e.value.code == EXIT_NEEDS_CONSENT
    assert (d / "kanban" / "1-backlog" / "EP-001.md").exists()


def test_library_calls_require_consent(tmp_path):
    d = tmp_path / ".context"
    with pytest.raises(SystemExit) as e:
        cards.create(d, "epic", "A", EPIC)
    assert e.value.code == EXIT_NEEDS_CONSENT
    assert not (d / "kanban").exists() and not (d / "tracking").exists()
    authorize(d)
    card = cards.create(d, "epic", "A", EPIC)
    (d / ".rup-standard").unlink()
    with pytest.raises(SystemExit) as e:
        cards.set_section(card, "Goal", "changed")
    assert e.value.code == EXIT_NEEDS_CONSENT
    assert "changed" not in card.path.read_text(encoding="utf-8")


def test_story_needs_criteria_and_task_needs_covers(ctx):
    cards.create(ctx, "epic", "A", EPIC)
    no_ac = STORY.replace("- Patient picks a slot\n- Patient gets a confirmation\n", "")
    with pytest.raises(SystemExit) as e:
        cards.create(ctx, "story", "S", no_ac, parent="EP-001")
    assert e.value.code == EXIT_USAGE
    cards.create(ctx, "story", "S", STORY, parent="EP-001")
    with pytest.raises(SystemExit) as e:
        cards.create(ctx, "task", "T", task_doc("none\n"), parent="ST-001")
    assert e.value.code == EXIT_USAGE
    assert sorted(p.name for p in (ctx / "kanban").rglob("*.md")) == ["EP-001.md", "ST-001.md"]


@pytest.mark.parametrize("source", ["[x]", "a\nb"])
def test_bad_source_rejected(ctx, source):
    with pytest.raises(SystemExit) as e:
        cards.create(ctx, "epic", "A", EPIC, source=source)
    assert e.value.code == EXIT_USAGE
    assert not list((ctx / "kanban").rglob("*.md"))


# ─── CLI ───

def new(env, python_cmd, tmp_path, kind, title, doc, extra=()):
    f = tmp_path / "doc.md"
    f.write_text(doc, encoding="utf-8")
    return run_skill(SKILL, ["--new", kind, "--title", title, "--doc", str(f), *extra],
                     env, python_cmd)


def test_cli_new_show_list(ctx_env, python_cmd, tmp_path):
    r = new(ctx_env, python_cmd, tmp_path, "epic", "Booking", EPIC)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert r.stdout.strip() == "EP-001"
    r = new(ctx_env, python_cmd, tmp_path, "story", "Book", STORY,
            ["--parent", "EP-001", "--priority", "Must", "--source", "uc.md#UC1"])
    assert r.stdout.strip() == "ST-001"
    r = run_skill(SKILL, ["--show", "ST-001"], ctx_env, python_cmd)
    assert "priority: Must" in r.stdout and "ST-001/AC-1" in r.stdout
    r = run_skill(SKILL, ["--list"], ctx_env, python_cmd)
    assert "| ID | Type | Title | Column | Parent |" in r.stdout
    assert "| ST-001 | story | Book | 1-backlog | EP-001 |" in r.stdout
    r = run_skill(SKILL, ["--list", "--type", "epic"], ctx_env, python_cmd)
    assert "EP-001" in r.stdout and "ST-001" not in r.stdout
    r = run_skill(SKILL, ["--list", "--column", "7-done"], ctx_env, python_cmd)
    assert "EP-001" not in r.stdout


def test_cli_stdin_and_bug_rejected(ctx_env, python_cmd):
    r = run_skill(SKILL, ["--new", "epic", "--title", "E", "--doc", "-"], ctx_env,
                  python_cmd, stdin=EPIC)
    assert r.returncode == EXIT_OK and r.stdout.strip() == "EP-001"
    r = run_skill(SKILL, ["--new", "bug", "--title", "E", "--doc", "-"], ctx_env,
                  python_cmd, stdin=EPIC)
    assert r.returncode != EXIT_OK


def test_new_requires_consent(clean_env, python_cmd, tmp_path):
    env = dict(clean_env, RUP_CONTEXT_DIR=str(tmp_path / "nope" / ".context"))
    r = new(env, python_cmd, tmp_path, "epic", "E", EPIC)
    assert r.returncode == EXIT_NEEDS_CONSENT, r.stdout + r.stderr
    assert not (tmp_path / "nope" / ".context" / "kanban").exists()


def test_cli_move(ctx_env, python_cmd, tmp_path):
    new(ctx_env, python_cmd, tmp_path, "epic", "Booking", EPIC)
    r = run_skill(SKILL, ["--move", "EP-001", "3-doing", "--reason", "start"], ctx_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert "EP-001 -> 3-doing" in r.stdout
    r = run_skill(SKILL, ["--list", "--column", "3-doing"], ctx_env, python_cmd)
    assert "EP-001" in r.stdout
    r = run_skill(SKILL, ["--move", "EP-001", "7-done"], ctx_env, python_cmd)
    assert r.returncode == EXIT_USAGE
    r = run_skill(SKILL, ["--move", "EP-001", "nope", "--reason", "x"], ctx_env, python_cmd)
    assert r.returncode == EXIT_USAGE


# ─── derive from requirements ───

REQUIREMENTS = """# Requirements Specifier

## Use-Case Packages

### Booking
Visits.

### Billing ###

## Use Cases

### Book a visit
Flow.

### Cancel a visit

## Supplementary Specifications

### Not a candidate
"""


def write_requirements(ctx, text=REQUIREMENTS, phase="Elaboration"):
    from _shared import context
    path = context.artifact_path(ctx, phase, "cp-requirements")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# header\n\n## Artifacts\n" + text, encoding="utf-8")


def test_derive_requires_requirements_artifact(ctx_env, python_cmd):
    r = run_skill(SKILL, ["--derive"], ctx_env, python_cmd)
    assert r.returncode == EXIT_USAGE, r.stdout + r.stderr
    assert "record cp-requirements first" in r.stdout + r.stderr


def test_derive_report_pending_derived_orphans(ctx):
    write_requirements(ctx)
    cards.create(ctx, "epic", "Booking", EPIC, source="cp-requirements#Booking")
    cards.create(ctx, "epic", "Gone", EPIC, source="cp-requirements#Removed package")
    cards.create(ctx, "epic", "Manual", EPIC, source="other.md#X")
    report = cards.derivation_report(ctx, "Elaboration")
    assert report["derived"] == ["cp-requirements#Booking"]
    assert report["pending"] == ["cp-requirements#Billing", "cp-requirements#Book a visit",
                                 "cp-requirements#Cancel a visit"]
    assert report["orphans"] == ["cp-requirements#Removed package"]


def test_derive_cli_prints_commands(ctx_env, python_cmd, tmp_path):
    write_requirements(Path(ctx_env["RUP_CONTEXT_DIR"]))
    r = run_skill(SKILL, ["--derive"], ctx_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert "Not yet derived" in r.stdout and "Already derived" in r.stdout
    assert "Orphan cards" in r.stdout
    assert "--new epic --title Billing" in r.stdout
    assert "--new story --title 'Book a visit'" in r.stdout
    assert "--source 'cp-requirements#Book a visit'" in r.stdout
    assert "<epic ID>" in r.stdout


def test_derive_never_modifies_existing_cards(ctx_env, python_cmd, tmp_path):
    ctx = Path(ctx_env["RUP_CONTEXT_DIR"])
    write_requirements(ctx)
    card = cards.create(ctx, "epic", "Booking", EPIC, source="cp-requirements#Booking")
    before = card.path.read_bytes()
    r = run_skill(SKILL, ["--derive"], ctx_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert card.path.read_bytes() == before
    assert sorted(p.name for p in (ctx / "kanban" / "1-backlog").iterdir()) == ["EP-001.md"]


def test_no_skipped_warning_on_normal_flows(ctx):
    cards.create(ctx, "epic", "A", EPIC)
    cards.move(ctx, "EP-001", "3-doing", "start")  # 1-backlog -> 3-doing
    cards.move(ctx, "EP-001", "2-todo", "back")
    cards.move(ctx, "EP-001", "3-doing", "again")  # 2-todo -> 3-doing
    cards.move(ctx, "EP-001", "7-done", "roll-up", actor="cp-backlog")
    assert "⚠️" not in cards.get(ctx, "EP-001").path.read_text(encoding="utf-8")
    cards.create(ctx, "epic", "B", EPIC)
    cards.move(ctx, "EP-002", "4-review", "jump")  # still warns
    assert "⚠️ skipped" in cards.get(ctx, "EP-002").path.read_text(encoding="utf-8")


def test_branch_name_is_shared_and_stable(ctx):
    cards.create(ctx, "epic", "A", EPIC)
    card = cards.create(ctx, "story", "Book a visit", STORY, parent="EP-001")
    assert cards.branch_name(card) == "st-001-book-a-visit"
    long = cards.create(ctx, "epic", "x" * 80, EPIC)
    assert cards.branch_name(long) == "ep-002-" + "x" * 40


def test_derive_with_unknown_phase_is_an_argparse_error(ctx_env, python_cmd):
    for args in (["--derive", "--phase", "Foo"],
                 ["--iteration-new", "--release", "R1", "--phase", "Foo", "--goal", "g"]):
        r = run_skill(SKILL, args, ctx_env, python_cmd)
        assert r.returncode == 2 and "invalid choice" in r.stderr
        assert "Traceback" not in r.stderr


def test_new_accepts_a_bom_crlf_document(ctx_env, python_cmd, tmp_path):
    doc = tmp_path / "epic.md"
    doc.write_bytes(b"\xef\xbb\xbf" + EPIC.replace("\n", "\r\n").encode("utf-8"))
    r = run_skill(SKILL, ["--new", "epic", "--title", "Booking", "--doc", str(doc)],
                  ctx_env, python_cmd)
    assert r.returncode == EXIT_OK, r.stdout + r.stderr
    assert r.stdout.strip() == "EP-001"
    body = cards.get(Path(ctx_env["RUP_CONTEXT_DIR"]), "EP-001").body
    assert "\r" not in body and "﻿" not in body
