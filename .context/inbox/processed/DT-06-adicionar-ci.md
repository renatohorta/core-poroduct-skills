# DT-06 — No CI [Done]

**Type**: Technical debt · **Priority**: Medium · **Opened on**: 2026-08-18
**Depends on**: DT-02, DT-05

## Context

There is no CI workflow. Nothing validates a push before the skills are
propagated to the agents by `install.sh`.

## Proposal

Workflow (GitHub Actions) on every push/PR:

1. `bash -n scripts/install.sh` (syntax) and `./scripts/install.sh --dry-run`
   with `HERMES_SKILLS_DIR`/`CLAUDE_SKILLS_DIR` pointing to a tempdir.
2. `pytest` (smoke + contract, DT-02/DT-03).
3. Hygiene check: no absolute machine path (`C:\Users\`, `/home/`)
   and no API key pattern in the committed files.

## Acceptance criterion

- A PR with a broken skill is blocked by CI.


---

## Resolution

**Done on 2026-08-18.** Verified with the suite (`pytest`, 158 tests, no
LLM credential). See `.context/docs/04-quality-qa.md`.
