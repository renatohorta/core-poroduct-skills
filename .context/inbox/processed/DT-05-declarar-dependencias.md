# DT-05 — Dependencies not declared [Done]

**Type**: Technical debt · **Priority**: High · **Opened on**: 2026-08-18

## Context

The skills import `crewai`, but the repository has no `requirements.txt` nor
`pyproject.toml`. Installation depends on the host agent already having the lib —
there is no way to reproduce the environment or pin a version.

Consequences: `scripts/chat.py` must **detect** a Python with `crewai`
installed, and a CrewAI API break appears without warning.

## Proposal

`requirements.txt` at the root pinning at least `crewai` (known-good version),
with a note in `docs/INSTALLATION.md` about creating a local venv for development.

## Acceptance criterion

- `pip install -r requirements.txt` in a clean venv allows running
  `python scripts/chat.py --list` and a skill `--dry-run`.


---

## Resolution

**Done on 2026-08-18.** Verified with the suite (`pytest`, 158 tests, no
LLM credential). See `.context/docs/04-quality-qa.md`.
