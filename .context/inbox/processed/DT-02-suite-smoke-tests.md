# DT-02 — No automated test suite [Done]

**Type**: Technical debt · **Priority**: High · **Opened on**: 2026-08-18

## Context

The repository has 15 skills and 15 `run.py` scripts, and **zero tests**. All
validation is manual (ad hoc `--dry-run`), so CLI contract regressions only
appear when the orchestrator breaks in production.

## Proposal

`pytest` parametrized over `skills/*/scripts/run.py`:

1. `--help` returns exit 0 for every skill.
2. `--dry-run` (with the briefing in the correct format per skill) returns exit 0.
3. `install.sh --dry-run` lists the 15 skills + `_shared`.
4. `_shared/llm.py`: resolution order (agent env > `.env` > per-key detection >
   default) with `monkeypatch`.

No test should call a real LLM — expensive and non-deterministic.

## Acceptance criterion

- `pytest` runs in < 60s without a configured LLM credential.
- A skill with a broken CLI contract makes the test fail.


---

## Resolution

**Done on 2026-08-18.** Verified with the suite (`pytest`, 158 tests, no
LLM credential). See `.context/docs/04-quality-qa.md`.
