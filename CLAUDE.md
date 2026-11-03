# CLAUDE.md — Project Context

**Project**: Core Product Skills — canonical repository of the **RUP skills**
(`skills/rup-*`) propagated to the Hermes Agent and Claude Code. The legacy
`cp-*` family was removed (ADR-0010) and only exists in the git history.

**Source of truth: `.context/`**

Read and write all project context in `.context/`. **DO NOT** create or use
`.hermes/` or `.claude/` for context — the `.context/` directory is the single
source of truth and the only place agents read/write project context.

- Overview: `.context/README.md`
- RUP specification: `.context/docs/`
- Work intake: `.context/inbox/`
- Tracking and ADRs: `.context/tracking/`
- Task pipeline: `.context/kanban/`

## Essential rules of this repository

1. **Edit the skills here**, in `skills/` — the installed copy in the agent is
   discarded and rewritten on every `./scripts/install.sh`.
2. **`_shared` is not a skill** — it is a shared helper; it goes to the agent's
   skills root, not to the category. Every `run.py` looks for it next to the
   skill and one level up (Hermes category layout).
3. **CLI contract** — every `rup-*` skill takes
   `run.py "<briefing>" [--phase P] [--input F] [--output F] [--dry-run]`;
   the orchestrator adds `--discipline`, `--auto`, `--list`, `--estimate`,
   `--sizing`, `--sizing-template`, `--json`. Validate with `--dry-run`.
   Exit codes: 0 ok · 1 usage · 2 no LLM · 3 no crewai.
4. **Windows**: the skills force UTF-8 on stdout/stderr (`setup_console`); when
   running other scripts, set `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`.
5. **Before committing**: check `git status --short` — partial commits are the
   most common mistake here.
6. **Tests never call an LLM** — run `.venv/bin/python -m pytest` before
   committing; a new skill or flag needs a test in `tests/test_smoke.py`.
