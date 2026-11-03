"""Cards: model, IDs, creation and the rup-backlog --new/--show/--list CLI."""
import pytest

from conftest import EXIT_NEEDS_CONSENT, EXIT_OK, EXIT_USAGE, authorize
from test_context_persistence import run_skill

from _shared import cards, frontmatter

SKILL = "rup-backlog"

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
