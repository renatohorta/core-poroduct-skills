---
name: rup-review
description: "Review a delivered RUP task or bug: print a checklist packet (criteria covered, delivery vs target files, test checks, traceability, integration steps) and record an approved / changes requested verdict that moves the card. Use when a card sits in 4-review."
---

# rup-review — checklist and verdict

Reviews a card in `4-review` (delivered by `rup-build`) and records the verdict
in the card. Needs the RUP standard authorized in `.context/` (exit 5 otherwise:
see `rup-context`). The skill never runs your tests or git.

## Steps

1. Print the packet: `python scripts/run.py TK-001 [--project-root DIR]`. It
   lists criteria covered, files changed vs target files, a fresh test check,
   traceability (source, parent chain, iteration) and integration steps.
2. Review the code and tests against it (`references/review.md`).
3. Write a document with `## Verdict` (first line `approved` or
   `changes requested`) and `## Findings` (`none` is fine when approved).
4. Record it: `python scripts/run.py --record TK-001 --doc FILE|-`.
   - `approved` -> card moves to `5-testing`.
   - `changes requested` -> back to `3-doing`, first finding as the reason.
5. After approval, merge the branch, run the full suite and move the card on
   with `rup-backlog --move` through `6-staging` to `7-done`.

## Commands

- `ID [--project-root DIR]` — checklist packet; the card must be in `4-review`.
- `--record ID --doc FILE|-` — verdict; appends to `## Review` (earlier reviews kept).
- `--context-dir D` — another `.context/` (default: auto-detect or `RUP_CONTEXT_DIR`).

Exit codes: 0 ok · 1 usage/invalid document · 4 not writable · 5 not authorized.
