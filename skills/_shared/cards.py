"""
cards.py — kanban cards: model, IDs, creation (INIT-03 §7.4).

One file per card in its column folder: `.context/kanban/<column>/<ID>.md`
(frontmatter + fixed sections). The folder is the truth for `status`.
IDs are assigned here, never by the agent.

Pure standard library.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from _shared import context, frontmatter
from _shared.discipline import fail, missing_artifacts

COLUMNS = ["1-backlog", "2-todo", "3-doing", "4-review", "5-testing",
           "6-staging", "7-done", "blocked"]
TYPES = {"epic": "EP", "story": "ST", "task": "TK", "bug": "BUG"}
PRIORITIES = ["Must", "Should", "Could", "Won't"]
REQUIRED_SECTIONS = {
    "epic": ["Goal", "Scope"],
    "story": ["User story", "Acceptance criteria", "Definition of Done"],
    "task": ["Description", "Target files", "Covers"],
    "bug": ["Symptom", "Reproduction"],
}
PARENT_TYPE = {"story": "epic", "task": "story", "bug": "story"}

META_ORDER = ["id", "type", "title", "status", "parent", "priority", "source",
              "created_at", "updated_at"]
AC_ID = re.compile(r"ST-\d+/AC-\d+")
_NUMBERED = re.compile(r"^- \*\*ST-\d+/AC-\d+\*\*")


@dataclass
class Card:
    id: str
    type: str
    title: str
    status: str
    meta: dict
    body: str
    path: Path


def _kanban(context_dir) -> Path:
    return Path(context_dir) / "kanban"


def _type_of(card_id: str, meta: dict) -> str:
    if meta.get("type") in TYPES:
        return meta["type"]
    for t, prefix in TYPES.items():
        if card_id.startswith(prefix + "-"):
            return t
    return str(meta.get("type", ""))


def load_all(context_dir) -> dict:
    """Every card of every column folder; duplicate IDs exit 1 naming both paths."""
    found: dict[str, Card] = {}
    root = _kanban(context_dir)
    for column in COLUMNS:
        folder = root / column
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            meta, body = frontmatter.parse(path.read_text(encoding="utf-8"))
            card_id = str(meta.get("id") or path.stem)
            if card_id in found:
                fail(f"duplicate card id {card_id}: {found[card_id].path} and {path}")
            meta["id"] = card_id
            meta["status"] = column
            found[card_id] = Card(card_id, _type_of(card_id, meta),
                                  str(meta.get("title", "")), column, meta, body, path)
    return found


def get(context_dir, card_id: str) -> Card:
    card = load_all(context_dir).get(card_id)
    if card is None:
        fail(f"unknown card {card_id}")
    return card


def next_id(context_dir, type: str) -> str:
    prefix = TYPES[type]
    nums = [int(c.id[len(prefix) + 1:]) for c in load_all(context_dir).values()
            if c.id.startswith(prefix + "-") and c.id[len(prefix) + 1:].isdigit()]
    return f"{prefix}-{max(nums, default=0) + 1:03d}"


def _section_span(lines: list, name: str):
    """(start, end) line indexes of `## name` up to the next `## ` heading."""
    want = name.strip().lower()
    for i, line in enumerate(lines):
        if line.startswith("## ") and line[3:].strip().lower() == want:
            end = next((j for j in range(i + 1, len(lines)) if lines[j].startswith("## ")),
                       len(lines))
            return i, end
    return None


def _section_lines(body: str, name: str) -> list:
    lines = body.splitlines()
    span = _section_span(lines, name)
    return lines[span[0] + 1:span[1]] if span else []


def number_criteria(story_id: str, body: str) -> str:
    lines = body.splitlines()
    span = _section_span(lines, "Acceptance criteria")
    if not span:
        return body
    n = 0
    for i in range(span[0] + 1, span[1]):
        if not lines[i].startswith("- "):
            continue
        n += 1
        if not _NUMBERED.match(lines[i]):
            lines[i] = f"- **{story_id}/AC-{n}**: {lines[i][2:].strip()}"
    return "\n".join(lines) + ("\n" if body.endswith("\n") else "")


def acceptance_criteria(card: Card) -> list:
    return AC_ID.findall("\n".join(_section_lines(card.body, "Acceptance criteria")))


def covers(card: Card) -> list:
    return AC_ID.findall("\n".join(_section_lines(card.body, "Covers")))


def _check_line(label: str, value: str) -> None:
    """A frontmatter value: single line and not parseable as a `[...]` list."""
    if "\n" in value or "\r" in value:
        fail(f"the card {label} must be a single line")
    if value.startswith("[") and value.endswith("]"):
        fail(f"the card {label} must not start with '[' and end with ']' "
             "(it would be parsed as a list)")


def _validate(context_dir, type, title, body, parent, priority, source="") -> None:
    if type not in TYPES:
        fail(f"unknown card type {type!r} (valid: {', '.join(TYPES)})")
    title = (title or "").strip()
    if not title:
        fail("the card title is empty")
    _check_line("title", title)
    _check_line("source", (source or "").strip())
    if priority not in PRIORITIES:
        fail(f"invalid priority {priority!r} (valid: {', '.join(PRIORITIES)})")
    missing = missing_artifacts(body, REQUIRED_SECTIONS[type])
    if missing:
        fail(f"the {type} document lacks required sections: "
             + ", ".join(f"## {m}" for m in missing))
    if _section_span(body.splitlines(), "History"):
        fail("the document must not contain `## History` (the skill writes it)")
    if type == "story":
        bullets = [l for l in _section_lines(body, "Acceptance criteria")
                   if l.startswith("- ")]
        if not bullets:
            fail("a story needs at least one acceptance criterion "
                 "(a `- ` bullet under `## Acceptance criteria`)")

    parent_type = PARENT_TYPE.get(type)
    if parent_type is None:
        return
    if not parent:
        if type == "bug":
            return
        fail(f"a {type} needs --parent (an existing {parent_type})")
    parent_card = get(context_dir, parent)
    if parent_card.type != parent_type:
        fail(f"parent {parent} is a {parent_card.type}; a {type} needs a {parent_type}")
    if type == "task":
        probe = Card("", "task", "", "", {}, body, Path())
        if not covers(probe):
            fail("a task's `## Covers` must list at least one ST-NNN/AC-n criterion")
        unknown = [c for c in covers(probe) if c not in acceptance_criteria(parent_card)]
        if unknown:
            fail(f"Covers lists criteria not in {parent}: {', '.join(unknown)}")


def create(context_dir, type, title, body, *, parent=None, priority="Should",
           source="", now=None) -> Card:
    """Check consent (exit 5), validate, then write `kanban/1-backlog/<ID>.md` and log it."""
    context.ensure_writable(context_dir)
    _validate(context_dir, type, title, body, parent, priority, source)
    title = title.strip()
    now = now or datetime.now()
    stamp = now.isoformat(timespec="seconds")
    card_id = next_id(context_dir, type)
    sections = body.strip()
    if type == "story":
        sections = number_criteria(card_id, sections)
    meta = {"id": card_id, "type": type, "title": title, "status": COLUMNS[0],
            "parent": parent or "", "priority": priority, "source": source or "",
            "created_at": stamp, "updated_at": stamp}
    if type == "epic":
        meta["release"] = ""
        meta["iteration"] = ""
    card_body = (f"# {card_id} — {title}\n\n{sections}\n\n"
                 f"## History\n\n- {stamp} created in {COLUMNS[0]}\n")
    path = _kanban(context_dir) / COLUMNS[0] / f"{card_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(frontmatter.dump(meta, card_body), encoding="utf-8")
    context.append_event(context_dir, skill="rup-backlog",
                         what=f"created {card_id} ({type}) in {COLUMNS[0]}", now=now)
    return Card(card_id, type, title, COLUMNS[0], meta, card_body.rstrip() + "\n", path)


def set_section(card: Card, name: str, text: str, now=None) -> Card:
    """Replace (or append) `## <name>` in the card, persist, bump `updated_at`.

    Checks consent itself; the context dir is derived from the card path
    (`<context>/kanban/<column>/<ID>.md` -> `card.path.parents[2]`).
    """
    context.ensure_writable(card.path.parents[2])
    lines = card.body.rstrip("\n").splitlines()
    block = [f"## {name}", "", *text.strip().splitlines(), ""]
    span = _section_span(lines, name)
    if span:
        lines[span[0]:span[1]] = block
    else:
        hist = _section_span(lines, "History")
        if hist:  # History stays the last section
            lines[hist[0]:hist[0]] = block
        else:
            lines += ([""] if lines else []) + block
    card.body = "\n".join(lines).rstrip() + "\n"
    card.meta["updated_at"] = (now or datetime.now()).isoformat(timespec="seconds")
    card.path.write_text(frontmatter.dump(card.meta, card.body), encoding="utf-8")
    return card


def _children(context_dir, parent: Card) -> list:
    kinds = {"epic": ("story",), "story": ("task", "bug")}.get(parent.type, ())
    return [c for c in load_all(context_dir).values()
            if c.meta.get("parent") == parent.id and c.type in kinds]


def _started(card: Card) -> bool:
    return card.status != "blocked" and COLUMNS.index(card.status) >= COLUMNS.index("3-doing")


def move(context_dir, card_id, column, reason, *, actor="agent", now=None,
         rollup=True) -> Card:
    """Move a card to `column`: file, `status`, `updated_at`, History, log, roll-up.

    Any move is legal; skipping forward columns only adds a warning to the
    History line. Checks consent itself (exit 5).
    """
    context.ensure_writable(context_dir)
    reason = (reason or "").strip()
    if not reason:
        fail("a move needs a reason (--reason)")
    if "\n" in reason or "\r" in reason:
        fail("the move reason must be a single line")
    if column not in COLUMNS:
        fail(f"unknown column {column!r} (valid: {', '.join(COLUMNS)})")
    card = get(context_dir, card_id)
    if card.status == column:
        fail(f"{card_id} is already in {column}")
    now = now or datetime.now()
    stamp = now.isoformat(timespec="seconds")
    src = card.status
    line = f"- {stamp} {src} → {column} — {reason} ({actor})"
    if "blocked" not in (src, column):
        a, b = COLUMNS.index(src), COLUMNS.index(column)
        if b - a > 1:
            line += " ⚠️ skipped " + ", ".join(COLUMNS[a + 1:b])
    card.meta["status"] = column
    card.meta["updated_at"] = stamp
    lines = card.body.rstrip("\n").splitlines()
    span = _section_span(lines, "History")
    if span is None:
        lines += ["", "## History", "", line]
    else:
        end = span[1]
        while end > span[0] + 1 and not lines[end - 1].strip():
            end -= 1  # insert after the last History line, before trailing blanks
        lines[end:end] = [line]
    card.body = "\n".join(lines).rstrip() + "\n"
    new_path = _kanban(context_dir) / column / card.path.name
    new_path.parent.mkdir(parents=True, exist_ok=True)
    new_path.write_text(frontmatter.dump(card.meta, card.body), encoding="utf-8")
    card.path.unlink()
    card.path, card.status = new_path, column
    context.append_event(context_dir, skill="rup-backlog",
                         what=f"moved {card_id} {src} → {column}: {reason}", now=now)
    if rollup:
        _rollup(context_dir, card, now=now)
    return card


def rollup(context_dir, card: Card, *, now=None) -> list:
    """Move the parent (then the grandparent) after `card` changed column.

    Parent in 1-backlog/2-todo and a child started -> `3-doing`; parent with
    children all in `7-done` -> `7-done`. Returns the cards moved.
    """
    moved: list = []
    while card.meta.get("parent"):
        parent = load_all(context_dir).get(card.meta["parent"])
        if parent is None:
            break
        kids = _children(context_dir, parent)
        target, why = None, ""
        if kids and all(k.status == "7-done" for k in kids):
            if parent.status != "7-done":
                target, why = "7-done", "roll-up: all children done"
        elif parent.status in ("1-backlog", "2-todo"):
            first = next((k for k in kids if _started(k)), None)
            if first:
                target, why = "3-doing", f"roll-up: {first.id} started"
        if target:
            parent = move(context_dir, parent.id, target, why, actor="rup-backlog",
                          now=now, rollup=False)
            moved.append(parent)
        card = parent
    return moved


_rollup = rollup  # `move` has a parameter named `rollup`
