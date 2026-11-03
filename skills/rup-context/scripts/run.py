#!/usr/bin/env python3
"""
rup-context — detect the project's `.context/` and adopt the RUP standard in it.

Nothing is written without the user's approval: `--status` only reads;
`--init --authorized-by "<who>"` (run it ONLY after the user approved) adds the
missing standard folders/files, writes the `.rup-standard` marker and the
CLAUDE.md / AGENT.md pointer note. Existing files are never overwritten.

Usage:
  python run.py --status [--context-dir D]
  python run.py --init --authorized-by "Ana" [--context-dir D]
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

from _shared import consent, context  # noqa: E402
from _shared.rup import EXIT_OK, EXIT_USAGE, setup_console  # noqa: E402


def print_status(state) -> None:
    print(f"context_dir: {state.context_dir}")
    print(f"exists: {'yes' if state.exists else 'no'}")
    print(f"authorized: {'yes' if state.authorized else 'no'}")
    print(f"missing: {len(state.missing)}")
    for rel in state.missing:
        print(f"  - {rel}")
    print("other doc dirs: " + (", ".join(state.other_doc_dirs) or "none"))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="RUP context — detect `.context/` and adopt the RUP standard "
                    "(init only after the user approves)")
    p.add_argument("--status", action="store_true", help="read-only report")
    p.add_argument("--init", action="store_true",
                   help="add the missing standard tree, marker and pointer note")
    p.add_argument("--authorized-by", help="who approved --init (the user)")
    p.add_argument("--context-dir", help="target .context/ (default: auto-detect)")
    args = p.parse_args(argv)
    context_dir = context.resolve_context_dir(args.context_dir)

    if args.init:
        if not args.authorized_by:
            print("[X] --init requires --authorized-by \"<who approved>\" "
                  "(ask the user first).")
            return EXIT_USAGE
        created = consent.init_context(context_dir, authorized_by=args.authorized_by)
        print(f"Authorized by {args.authorized_by}. Created {len(created)} entries:")
        for path in created:
            print(f"  + {path}")
        return EXIT_OK

    print_status(consent.detect(context_dir))
    return EXIT_OK


if __name__ == "__main__":
    setup_console()  # UTF-8 on stdout/stderr (Windows console is cp1252)
    sys.exit(main())
