#!/usr/bin/env python3
"""
rup-backlog — kanban cards (epics, stories, tasks) in `.context/kanban/`.

Usage:
  python run.py --new {epic,story,task} --title T --doc FILE|- [--parent ID]
                [--priority P] [--source S] [--context-dir D]   (prints the new ID)
  python run.py --move ID COLUMN --reason R [--context-dir D]
  python run.py --show ID [--context-dir D]
  python run.py --release-new --title T [--milestone M] [--goal G] [--target-date D]
  python run.py --iteration-new --release R --phase P --goal G [--start S] [--end E]
  python run.py --plan EPIC --iteration I
  python run.py --roadmap                  (regenerate docs/06-roadmap.md, 06-board.md)
  python run.py --list [--column C] [--type T] [--context-dir D]
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

from _shared import cards, context, roadmap  # noqa: E402
from _shared.discipline import fail, read_document  # noqa: E402
from _shared.rup import EXIT_OK, setup_console  # noqa: E402


def print_list(context_dir, column=None, type=None) -> None:
    rows = [c for c in cards.load_all(context_dir).values()
            if (not column or c.status == column) and (not type or c.type == type)]
    rows.sort(key=lambda c: (cards.COLUMNS.index(c.status), c.id))
    print("| ID | Type | Title | Column | Parent |")
    print("|----|------|-------|--------|--------|")
    for c in rows:
        print(f"| {c.id} | {c.type} | {c.title} | {c.status} | {c.meta.get('parent', '')} |")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="RUP backlog — kanban cards in `.context/kanban/`")
    p.add_argument("--new", choices=["epic", "story", "task"], help="create a card in 1-backlog")
    p.add_argument("--title", help="card title (with --new)")
    p.add_argument("--doc", metavar="FILE|-", help="document with the card's `## ` sections")
    p.add_argument("--parent", help="parent card ID (story -> epic, task -> story)")
    p.add_argument("--priority", default="Should", help="Must | Should | Could | Won't")
    p.add_argument("--source", default="", help="RUP artifact path + section")
    p.add_argument("--move", nargs=2, metavar=("ID", "COLUMN"), help="move a card to a column")
    p.add_argument("--reason", help="why (required with --move)")
    p.add_argument("--show", metavar="ID", help="print a card")
    p.add_argument("--list", action="store_true", help="table of cards")
    p.add_argument("--column", choices=cards.COLUMNS, help="filter --list by column")
    p.add_argument("--type", choices=list(cards.TYPES), help="filter --list by type")
    p.add_argument("--release-new", action="store_true", help="create a release (needs --title)")
    p.add_argument("--milestone", default="", help="RUP milestone of the release (with --release-new)")
    p.add_argument("--goal", default="", help="goal of the release/iteration")
    p.add_argument("--target-date", default="", help="release target date (with --release-new)")
    p.add_argument("--iteration-new", action="store_true",
                   help="create an iteration (needs --release --phase --goal)")
    p.add_argument("--release", help="release ID (with --iteration-new)")
    p.add_argument("--phase", help="RUP phase of the iteration (with --iteration-new)")
    p.add_argument("--start", default="", help="iteration start date")
    p.add_argument("--end", default="", help="iteration end date")
    p.add_argument("--plan", metavar="EPIC", help="plan an epic into --iteration")
    p.add_argument("--iteration", help="iteration ID (with --plan)")
    p.add_argument("--roadmap", action="store_true", help="regenerate the roadmap and board views")
    p.add_argument("--context-dir", help="target .context/ (default: auto-detect)")
    args = p.parse_args(argv)
    context_dir = context.resolve_context_dir(args.context_dir)

    if args.new:
        if not args.title or not args.doc:
            fail("--new needs --title and --doc FILE|-")
        context.ensure_writable(context_dir)
        card = cards.create(context_dir, args.new, args.title, read_document(args.doc),
                            parent=args.parent, priority=args.priority, source=args.source)
        print(card.id)
        return EXIT_OK

    if args.move:
        card_id, column = args.move
        if not args.reason:
            fail("--move needs --reason R")
        card = cards.move(context_dir, card_id, column, args.reason)
        print(f"{card.id} -> {card.status}")
        return EXIT_OK

    if args.release_new:
        if not args.title:
            fail("--release-new needs --title T")
        print(roadmap.new_release(context_dir, args.title, milestone=args.milestone,
                                  goal=args.goal, target_date=args.target_date))
        return EXIT_OK

    if args.iteration_new:
        if not (args.release and args.phase and args.goal):
            fail("--iteration-new needs --release R --phase P --goal G")
        print(roadmap.new_iteration(context_dir, args.release, args.phase, args.goal,
                                    start=args.start, end=args.end))
        return EXIT_OK

    if args.plan:
        if not args.iteration:
            fail("--plan needs --iteration I")
        epic = roadmap.plan_epic(context_dir, args.plan, args.iteration)
        print(f"{epic.id} -> {args.iteration}")
        return EXIT_OK

    if args.roadmap:
        for path in roadmap.regenerate_views(context_dir):
            print(path)
        return EXIT_OK

    if args.show:
        print(cards.get(context_dir, args.show).path.read_text(encoding="utf-8"), end="")
        return EXIT_OK

    if args.list:
        print_list(context_dir, args.column, args.type)
        return EXIT_OK

    p.print_help()
    return EXIT_OK


if __name__ == "__main__":
    setup_console()  # UTF-8 on stdout/stderr (Windows console is cp1252)
    sys.exit(main())
