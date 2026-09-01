# DT-03 — `invoke` contract is not validated against the real argparse [Done]

**Type**: Technical debt · **Priority**: High · **Opened on**: 2026-08-18

## Context

The orchestrator declares, in the `CREWS` dict, how each skill is triggered
(`invoke.briefing_arg` and `invoke.output`). This metadata is maintained **by
hand**. If the skill changes its `argparse` and the metadata is not updated, the
phase breaks at runtime — the skill's argparse rejects the flag.

Known cases: `cp-bug-fix`, `cp-goal-loop` and `cp-agile` do **not** accept
`--output`; `cp-goal-loop` only receives the briefing via `--goal`; `cp-agile`
and `cp-doc-initializer` have no positional argument.

## Proposal

A test that, for each skill:

1. Extracts the real `add_argument` from `skills/cp-*/scripts/run.py`.
2. Compares with `CREWS[<key>]['invoke']` of the orchestrator.
3. Fails if `output=True` but the skill does not declare `--output`, or if the
   declared `briefing_arg` does not exist in the skill.

Keep `skills/cp-orchestrator/references/skills-cli-inventory.md` as
documentation derived from this test.

## Acceptance criterion

- Adding a new skill without updating `CREWS` makes the test fail with a message
  pointing to the divergent field.


---

## Resolution

**Done on 2026-08-18.** Verified with the suite (`pytest`, 158 tests, no
LLM credential). See `.context/docs/04-quality-qa.md`.
