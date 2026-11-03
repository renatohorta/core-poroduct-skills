---
name: cp-debug
description: "Debug a bug the RUP way: open a BUG card, reproduce it, pin it with a failing regression test, find and record the root cause, then fix and deliver through cp-build. Use when the user reports a bug, a regression or unexpected behavior to fix."
---

# cp-debug — bugs: root cause before fix

Opens a `BUG-NNN` card in `.context/kanban/` and enforces the order: reproduce,
failing regression test, root cause recorded, fix. Needs the RUP standard
authorized in `.context/` (exit 5 otherwise: see `cp-context`). The skill never
runs your tests or git.

## Steps

1. Open: write a document with `## Symptom` and `## Reproduction`, then
   `python scripts/run.py --open --title "..." --doc FILE|- [--parent ST-001]`.
   It prints the protocol with the exact follow-up commands.
2. Reproduce, then write a failing regression test whose name (or a comment
   above it) names the bug ID (`BUG-001`). Run it, save the red output.
3. Find the root cause (`references/debugging.md`), not the symptom's location.
   Record it: `python scripts/run.py --diagnose BUG-001 --doc FILE|-` with a
   non-empty `## Root cause`. The card moves to `3-doing`.
4. Fix, get the test green, then deliver with
   `cp-build --finish BUG-001 --delivery FILE|-`. `cp-build` refuses a bug
   without `## Root cause` and requires a test that references the bug ID.

## Commands

- `--open --title T --doc FILE|- [--parent ST-NNN] [--priority P]` — new bug in `1-backlog`.
- `--diagnose BUG-NNN --doc FILE|-` — card in `1-backlog`, `2-todo` or `3-doing`;
  running it again replaces the root cause and logs `root cause updated`.
- `--context-dir D` — another `.context/` (default: auto-detect or `RUP_CONTEXT_DIR`).

Exit codes: 0 ok · 1 usage/invalid document · 4 not writable · 5 not authorized.
