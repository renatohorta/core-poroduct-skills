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


def _validate(context_dir, type, title, body, parent, priority) -> None:
    if type not in TYPES:
        fail(f"unknown card type {type!r} (valid: {', '.join(TYPES)})")
    title = (title or "").strip()
    if not title:
        fail("the card title is empty")
    if "\n" in title or "\r" in title:
        fail("the card title must be a single line")
    if title.startswith("[") and title.endswith("]"):
        fail("the card title must not start with '[' and end with ']' "
             "(it would be parsed as a list)")
    if priority not in PRIORITIES:
        fail(f"invalid priority {priority!r} (valid: {', '.join(PRIORITIES)})")
    missing = missing_artifacts(body, REQUIRED_SECTIONS[type])
    if missing:
        fail(f"the {type} document lacks required sections: "
             + ", ".join(f"## {m}" for m in missing))
    if _section_span(body.splitlines(), "History"):
        fail("the document must not contain `## History` (the skill writes it)")

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
        unknown = [c for c in covers(probe) if c not in acceptance_criteria(parent_card)]
        if unknown:
            fail(f"Covers lists criteria not in {parent}: {', '.join(unknown)}")


def create(context_dir, type, title, body, *, parent=None, priority="Should",
           source="", now=None) -> Card:
    """Validate, then write `kanban/1-backlog/<ID>.md` and log it."""
    _validate(context_dir, type, title, body, parent, priority)
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
    """Replace (or append) `## <name>` in the card, persist, bump `updated_at`."""
    lines = card.body.rstrip("\n").splitlines()
    block = [f"## {name}", "", *text.strip().splitlines(), ""]
    span = _section_span(lines, name)
    if span:
        lines[span[0]:span[1]] = block
    else:
        lines += ([""] if lines else []) + block
    card.body = "\n".join(lines).rstrip() + "\n"
    card.meta["updated_at"] = (now or datetime.now()).isoformat(timespec="seconds")
    card.path.write_text(frontmatter.dump(card.meta, card.body), encoding="utf-8")
    return card
