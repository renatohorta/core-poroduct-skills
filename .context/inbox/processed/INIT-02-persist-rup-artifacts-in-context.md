# [Done] INIT-02 — Persist the RUP artifacts into the target project's `.context/`

**Type**: initiative · **Priority**: Should · **Raised**: 2026-11-03

## Context

The `rup-*` skills write their result only to stdout and to `--output`. Since
2026-11-03, `--auto` chains the disciplines (each receives the earlier
artifacts) and keeps one file per discipline, but nothing lands in the target
project's `.context/` — the RUP artifacts (Vision, SRS, SAD, Test Plan, …) are
not part of the project's source of truth unless someone copies them.

## Decision needed

Map each discipline's artifacts to `.context/docs/` (e.g. requirements →
`01-inception/requirements.md`, analysis-design → `02-elaboration/architecture.md`,
test → `04-transition/test-strategy.md`, deployment → `04-transition/devops-infra.md`)
and choose the write policy: overwrite, append a dated section, or write to a
staging file for review.

## Acceptance

- [x] Mapping recorded in ADR-0011: `.context/docs/<NN-phase>/rup-<discipline>.md`,
      regenerated per run, plus `.context/tracking/rup-log.md`
- [x] **Mandatory** (not opt-in, by the owner's decision): every real run writes;
      `--context-dir` / `RUP_CONTEXT_DIR` only choose *where*; unwritable → exit 4
      before the LLM call
- [x] Tests with a temp `.context/` and no LLM (`tests/fakes/crewai`,
      `tests/test_context_persistence.py`)

Resolved 2026-11-03.
