#!/usr/bin/env python3
"""
cp-debug — open a bug and record its root cause before it is fixed.

Usage:
  python run.py --open --title T --doc FILE|- [--parent ST-NNN] [--priority P] [--context-dir D]
  python run.py --diagnose BUG-NNN --doc FILE|- [--context-dir D]
"""

import argparse
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

from _shared import cards, context  # noqa: E402
from _shared.discipline import cmdline, fail, read_document  # noqa: E402
from _shared.rup import EXIT_OK, setup_console  # noqa: E402
from _shared.testcheck import parse_delivery  # noqa: E402  (tolerant `## ` heading matching)

DIAGNOSABLE = ("1-backlog", "2-todo", "3-doing")
PROTOCOL = [
    "Reproduce the bug with the steps in the card.",
    "Write a failing regression test whose name (or a comment above it) names `{id}`; run it and save the red output.",
    "Find the ROOT cause (references/debugging.md): why it happens, not where it shows.",
    "Record it: `{diagnose}`. The document needs a non-empty `## Root cause`.",
    "Fix the root cause with the minimum change; the regression test turns green.",
    "Prove the regression test guards the fix: `{mutate}` on the lines you fixed — the "
    "mutants that undo the fix (the flipped condition) must be killed. Report it in "
    "`## Mutation` of the delivery.",
    "Deliver: `{finish}`. Run `{start}` first (only if not diagnosed): --diagnose already starts the bug and sets its branch.",
]


def sibling(skill: str) -> Path:
    return Path(__file__).resolve().parents[2] / skill / "scripts" / "run.py"


def open_bug(context_dir, title, source, parent, priority) -> None:
    body = read_document(source).strip()
    card = cards.create(context_dir, "bug", title, body, parent=parent, priority=priority)
    me, build = Path(__file__).resolve(), sibling("cp-build")
    cmds = {
        "diagnose": cmdline([sys.executable, me, "--diagnose", card.id, "--doc", "FILE|-"]),
        "start": cmdline([sys.executable, build, "--start", card.id]),
        "finish": cmdline([sys.executable, build, "--finish", card.id, "--delivery", "FILE|-"]),
        "mutate": cmdline([sys.executable, sibling("cp-test"), "--mutate", "--lines",
                           "<fixed-file>:<start>-<end>"]),
    }
    print(f"{card.id} created in {card.status}: {card.title}\n")
    print("## Debugging protocol\n")
    for i, step in enumerate(PROTOCOL, 1):
        print(f"{i}. {step.format(id=card.id, **cmds)}")


def diagnose(context_dir, card_id, source) -> None:
    context.ensure_writable(context_dir)
    card = cards.get(context_dir, card_id)
    if card.type != "bug":
        fail(f"{card_id} is a {card.type}; cp-debug works on bugs")
    if card.status not in DIAGNOSABLE:
        fail(f"{card_id} is in {card.status}; --diagnose needs {', '.join(DIAGNOSABLE)}")
    cause = parse_delivery(read_document(source)).section("Root cause")
    if not cause:
        fail("the document needs a non-empty `## Root cause` section")
    again = bool(cards.section_text(card, "Root cause"))
    card = cards.set_section(card, "Root cause", cause)
    if again:
        card = cards.add_history(card, "root cause updated")
    if not card.meta.get("branch"):
        card = cards.set_meta(card, "branch", cards.branch_name(card))
    if card.status != "3-doing":
        card = cards.move(context_dir, card_id, "3-doing", "diagnosed")
    print(f"{card.id} root cause recorded -> {card.status}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="RUP debug — bug protocol and root-cause record")
    p.add_argument("--open", action="store_true", help="create a bug card and print the protocol")
    p.add_argument("--title", help="bug title (with --open)")
    p.add_argument("--parent", help="parent story ST-NNN (with --open, optional)")
    p.add_argument("--priority", default="Should", help="Must|Should|Could (with --open)")
    p.add_argument("--diagnose", metavar="BUG-NNN", help="record the root cause")
    p.add_argument("--doc", metavar="FILE|-", help="document: Symptom + Reproduction (--open) or Root cause (--diagnose)")
    p.add_argument("--context-dir", help="target .context/ (default: auto-detect)")
    args = p.parse_args(argv)
    context_dir = context.resolve_context_dir(args.context_dir)

    if args.open:
        if not args.title or not args.doc:
            fail("--open needs --title and --doc FILE|-")
        open_bug(context_dir, args.title, args.doc, args.parent, args.priority)
        return EXIT_OK
    if args.diagnose:
        if not args.doc:
            fail("--diagnose needs --doc FILE|-")
        diagnose(context_dir, args.diagnose, args.doc)
        return EXIT_OK
    p.print_help()
    return EXIT_OK


if __name__ == "__main__":
    setup_console()  # UTF-8 on stdout/stderr (Windows console is cp1252)
    sys.exit(main())
