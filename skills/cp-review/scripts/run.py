#!/usr/bin/env python3
"""
cp-review — review a delivered task (or bug) and record the verdict.

Usage:
  python run.py ID [--project-root DIR] [--context-dir D]
  python run.py --record ID --doc FILE|- [--context-dir D]
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

# _shared/ sits in the skills root: next to this skill (repo, Claude Code) or one
# level up when the agent nests skills in a category (Hermes: skills/<category>/).
_SKILL_DIR = Path(__file__).resolve().parent.parent
for _root in (_SKILL_DIR.parent, _SKILL_DIR.parent.parent):
    if (_root / "_shared" / "discipline.py").is_file():
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        break

from _shared import cards, context, testcheck  # noqa: E402
from _shared.discipline import cmdline, fail, missing_artifacts, read_document  # noqa: E402
from _shared.rup import EXIT_OK, setup_console  # noqa: E402

REVIEW_COLUMN = "4-review"
VERDICTS = ("approved", "changes requested")
REQUIRED = ["Verdict", "Findings"]


def in_review(context_dir, card_id):
    card = cards.get(context_dir, card_id)
    if card.status != REVIEW_COLUMN:
        fail(f"{card_id} is in {card.status}; review needs {REVIEW_COLUMN}")
    return card


def bullets(text: str) -> list:
    """Bullet items of a section, backticks and whitespace stripped."""
    items = []
    for line in text.splitlines():
        m = re.match(r"^\s*[-*]\s+(.*\S)", line)
        if m:
            items.append(m[1].strip().strip("`").strip())
    return items


def delivery_of(card):
    """The card's stored delivery (nested one heading level down), parsed."""
    return testcheck.parse_delivery(
        testcheck.extract_delivery(cards.section_text(card, "Delivery")))


def parent_chain(context_dir, card) -> list:
    chain, seen = [], {card.id}
    all_cards = cards.load_all(context_dir)
    cur = all_cards.get(card.meta.get("parent"))
    while cur is not None and cur.id not in seen:
        chain.append(cur)
        seen.add(cur.id)
        cur = all_cards.get(cur.meta.get("parent"))
    return chain


def packet(context_dir, card_id, project_root) -> None:
    card = in_review(context_dir, card_id)
    chain = parent_chain(context_dir, card)
    story = chain[0] if chain and chain[0].type == "story" else None
    delivery = delivery_of(card)
    me = Path(__file__).resolve()
    backlog = Path(__file__).resolve().parents[2] / "cp-backlog" / "scripts" / "run.py"

    print(f"# Review {card.id} — {card.title}\n")
    print("## 1. Criteria covered\n")
    wanted = [card.id] if card.type == "bug" else cards.covers(card)
    print(f"Required: {', '.join(wanted) or '(none)'}")
    print("Delivery tests:")
    for path, name, ids in delivery.tests:
        print(f"- {path}::{name} — covers {', '.join(ids)}")
    if not delivery.tests:
        print("- (none listed)")
    got = {i for _, _, ids in delivery.tests for i in ids}
    print("Not covered by any delivery test: "
          + (", ".join(c for c in wanted if c not in got) or "none"))

    print("\n## 2. Files\n")
    changed = bullets(delivery.section("Files changed"))
    targets = bullets(cards.section_text(card, "Target files"))
    outside = [f for f in changed if f not in targets]
    unchanged = [f for f in targets if f not in changed]
    print("Outside target files: " + (", ".join(outside) or "none"))
    print("Target files not changed: " + (", ".join(unchanged) or "none"))

    print("\n## 3. Test checks\n")
    problems = testcheck.check_delivery(delivery, card, story, Path(project_root))
    if problems:
        print("Test checks: PROBLEMS")
        for problem in problems:
            print(f"- {problem}")
    else:
        print("Test checks: OK")

    print("\n## 4. Mutation of the changed lines\n")
    mutation = delivery.section("Mutation").strip()
    print(mutation if mutation else
          "Not run: the delivery has no `## Mutation`. Ask for it (cp-test --mutate --lines "
          "FILE:A-B) or check that every survivor is explained.")

    print("\n## 5. Adversarial review (recommended for non-trivial cards)\n")
    print("Have an agent WITHOUT the builder's context review the diff against the story: "
          "concurrency, retries/idempotency, transactions and migrations, queries without "
          "an index, wrong counts, stale data, error paths. A green suite does not answer "
          "these. Each real finding is a `changes requested` item that starts with a test "
          "that reproduces it.")

    print("\n## 6. Traceability\n")
    print(f"Source: {card.meta.get('source') or '(none)'}")
    print("Parent chain: " + (" -> ".join(f"{c.id} ({c.title})" for c in chain) or "(none)"))
    epic = next((c for c in chain if c.type == "epic"), None)
    print(f"Iteration: {(epic.meta.get('iteration') if epic else '') or '(none)'}")

    print("\n## 7. Integration toward 7-done\n")
    print(f"1. Merge the card's branch `{card.meta.get('branch') or '(not recorded)'}` "
          "into the main line (git, by you).")
    print("2. Run the project's full test suite on the merged result.")
    for step, col in enumerate(("5-testing", "6-staging", "7-done"), 3):
        move = cmdline([sys.executable, backlog, "--move", card.id, col, "--reason", "<why>"])
        print(f"{step}. As each stage is reached: `{move}`")

    print("\n## 8. Record the verdict\n")
    print("Write `## Verdict` (first line `approved` or `changes requested`) and "
          "`## Findings` (references/review.md), then:\n")
    print("    " + cmdline([sys.executable, me, "--record", card.id, "--doc", "FILE|-"]))


def record(context_dir, card_id, source) -> None:
    context.ensure_writable(context_dir)
    card = in_review(context_dir, card_id)
    text = read_document(source)
    parsed = testcheck.parse_delivery(text)
    missing = missing_artifacts("\n".join(f"## {h}" for h in parsed.sections), REQUIRED)
    if missing:
        fail("the review document needs " + ", ".join(f"`## {m}`" for m in missing))
    first = next((l.strip() for l in parsed.section("Verdict").splitlines() if l.strip()), "")
    verdict = first.lower()
    if verdict not in VERDICTS:
        fail(f"the first line of `## Verdict` must be `approved` or `changes requested`, got {first!r}")
    findings = parsed.section("Findings").strip()
    if not findings:
        fail("`## Findings` is empty (write `none` if there is nothing to report)")

    stamp = datetime.now().isoformat(timespec="seconds")
    previous = cards.section_text(card, "Review")
    entry = f"### {stamp} — {verdict}\n\n{findings}"
    card = cards.set_section(card, "Review", f"{previous}\n\n{entry}" if previous else entry)
    if verdict == "approved":
        card = cards.move(context_dir, card_id, "5-testing", "review approved")
    else:
        line = next((l.strip() for l in findings.splitlines() if l.strip()), "")
        line = re.sub(r"^[-*]\s+", "", line)
        card = cards.move(context_dir, card_id, "3-doing", f"changes requested: {line}")
    print(f"{card.id} review recorded ({verdict}) -> {card.status}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="RUP review — checklist packet and verdict record")
    p.add_argument("id", nargs="?", metavar="ID", help="card in 4-review: print the checklist packet")
    p.add_argument("--record", metavar="ID", help="record the verdict and move the card")
    p.add_argument("--doc", metavar="FILE|-", help="review document (with --record)")
    p.add_argument("--project-root", help="project root holding the tests (default: parent of .context/)")
    p.add_argument("--context-dir", help="target .context/ (default: auto-detect)")
    args = p.parse_args(argv)
    context_dir = context.resolve_context_dir(args.context_dir)

    if args.record:
        if not args.doc:
            fail("--record needs --doc FILE|-")
        record(context_dir, args.record, args.doc)
        return EXIT_OK
    if args.id:
        packet(context_dir, args.id, args.project_root or Path(context_dir).resolve().parent)
        return EXIT_OK
    p.print_help()
    return EXIT_OK


if __name__ == "__main__":
    setup_console()  # UTF-8 on stdout/stderr (Windows console is cp1252)
    sys.exit(main())
