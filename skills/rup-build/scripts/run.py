#!/usr/bin/env python3
"""
rup-build — start and finish a task (or bug) the test-first way.

Usage:
  python run.py --start ID [--context-dir D]
  python run.py --finish ID --delivery FILE|- [--project-root DIR] [--context-dir D]
"""

import argparse
import re
import sys
from pathlib import Path

# _shared/ sits in the skills root: next to this skill (repo, Claude Code) or one
# level up when the agent nests skills in a category (Hermes: skills/<category>/).
_SKILL_DIR = Path(__file__).resolve().parent.parent
for _root in (_SKILL_DIR.parent, _SKILL_DIR.parent.parent):
    if (_root / "_shared" / "discipline.py").is_file():
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        break

from _shared import cards, context, roadmap, testcheck  # noqa: E402
from _shared.discipline import cmdline, fail, prior_artifacts, read_document  # noqa: E402
from _shared.rup import EXIT_OK, setup_console  # noqa: E402

BUILDABLE = ("task", "bug")
STARTABLE = ("1-backlog", "2-todo", "blocked")
DEFAULT_PHASE = "Construction"
TDD_RULES = [
    "Write the test FIRST and run it: it must fail (red). Save that output.",
    "Name the criterion in the test (test name, docstring or a comment above it): "
    "`ST-NNN/AC-n` for a task, the bug ID or a criterion for a bug.",
    "The test must assert real behavior and call project code: no `assert True`, "
    "no constant comparisons, no test without assertions.",
    "Implement the minimum, run again: green.",
    "Commit after every green step.",
    "Finish with the delivery document (references/tdd.md) and the --finish command below.",
]


def slug(text: str, limit=None) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit].strip("-") if limit else s


def branch_name(card) -> str:
    return f"{slug(card.id)}-{slug(card.title, 40)}".rstrip("-")


def parent_of(context_dir, card):
    pid = card.meta.get("parent")
    return cards.load_all(context_dir).get(pid) if pid else None


def packet_phase(context_dir, card) -> str:
    """Phase of the epic's iteration (card -> story -> epic -> iteration); Construction if unlinked."""
    story = parent_of(context_dir, card)
    epic = parent_of(context_dir, story) if story else None
    iteration = str(epic.meta.get("iteration", "")) if epic else ""
    return (roadmap.iteration_phase(context_dir, iteration) if iteration else "") or DEFAULT_PHASE


def buildable(context_dir, card_id):
    card = cards.get(context_dir, card_id)
    if card.type not in BUILDABLE:
        fail(f"{card_id} is a {card.type}; rup-build works on tasks and bugs")
    return card


def start(context_dir, card_id) -> None:
    context.ensure_writable(context_dir)
    card = buildable(context_dir, card_id)
    if card.status not in STARTABLE:
        fail(f"{card_id} is in {card.status}; --start needs {', '.join(STARTABLE)}")
    cards.set_meta(card, "branch", branch_name(card))
    card = cards.move(context_dir, card_id, "3-doing", "started")
    story = parent_of(context_dir, card)
    phase = packet_phase(context_dir, card)
    me = Path(__file__).resolve()

    print(f"# Build {card.id} — {card.title}\n")
    print(f"Branch: `{card.meta['branch']}` (create it in git yourself)\n")
    print(f"## {card.type.capitalize()} card\n")
    print(card.body.strip(), "\n")
    if story is not None:
        print(f"## Parent story {story.id} — {story.title}\n")
        print("\n".join(l for l in story.body.splitlines()
                        if "/AC-" in l) or "(no criteria)", "\n")
    print("## Earlier RUP artifacts (" + phase + ")\n")
    found = prior_artifacts(context_dir, phase, "rup-build")
    for label, path, body in found:
        print(f"### {label}\n\n{body}\n")
    if not found:
        print("(none recorded)\n")
    print("## TDD rules\n")
    for i, rule in enumerate(TDD_RULES, 1):
        print(f"{i}. {rule}")
    finish = cmdline([sys.executable, me, "--finish", card.id, "--delivery", "FILE|-"])
    print(f"\n## When done\n\n    {finish}\n")


def finish(context_dir, card_id, source, project_root) -> None:
    context.ensure_writable(context_dir)
    card = buildable(context_dir, card_id)
    if card.status != "3-doing":
        fail(f"{card_id} is in {card.status}; --finish needs 3-doing (run --start first)")
    story = parent_of(context_dir, card)
    if card.type == "task" and (story is None or story.type != "story"):
        fail(f"{card_id} has no parent story")
    text = read_document(source).strip()
    delivery = testcheck.parse_delivery(text)
    problems = testcheck.check_delivery(delivery, card, story, Path(project_root))
    if problems:
        print("Delivery rejected:")
        for problem in problems:
            print(f"- {problem}")
        sys.exit(1)
    for warning in testcheck.delivery_warnings(delivery, Path(project_root)):
        print(f"⚠️ {warning}")
    cards.set_section(card, "Delivery", text)
    if card.type == "bug":
        cards.set_section(card, "Fix", testcheck._section(delivery.sections, "What was done"))
        cards.set_section(card, "Regression test", testcheck._section(delivery.sections, "Tests"))
    card = cards.move(context_dir, card_id, "4-review", "delivered")
    print(f"{card.id} -> {card.status}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="RUP build — start and finish a task test-first")
    p.add_argument("--start", metavar="ID", help="start a task/bug: move to 3-doing, print the packet")
    p.add_argument("--finish", metavar="ID", help="validate the delivery and move to 4-review")
    p.add_argument("--delivery", metavar="FILE|-", help="delivery document (with --finish)")
    p.add_argument("--project-root", help="project root holding the tests (default: parent of .context/)")
    p.add_argument("--context-dir", help="target .context/ (default: auto-detect)")
    args = p.parse_args(argv)
    context_dir = context.resolve_context_dir(args.context_dir)

    if args.start:
        start(context_dir, args.start)
        return EXIT_OK
    if args.finish:
        if not args.delivery:
            fail("--finish needs --delivery FILE|-")
        finish(context_dir, args.finish, args.delivery,
               args.project_root or Path(context_dir).resolve().parent)
        return EXIT_OK
    p.print_help()
    return EXIT_OK


if __name__ == "__main__":
    setup_console()  # UTF-8 on stdout/stderr (Windows console is cp1252)
    sys.exit(main())
