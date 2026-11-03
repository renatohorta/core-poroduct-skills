# INIT-02 — Persist the RUP artifacts into the target project's `.context/`

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

- [ ] Mapping discipline → `.context/docs/` file recorded in an ADR
- [ ] Opt-in flag (e.g. `--context-dir <path>`) on the orchestrator and disciplines
- [ ] Test with a temp `.context/` and no LLM (fake crew result)
