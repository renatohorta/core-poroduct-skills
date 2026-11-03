# AGENT.md — Project Context

**Project**: Core Product Skills — canonical repository of the **RUP skills**
(`skills/rup-*`) propagated to the Hermes Agent and Claude Code. **The agent
running a skill is the LLM** (ADR-0012): the skills never call a model and are
pure standard library. The legacy `cp-*` family (ADR-0010) and the CrewAI
execution (ADR-0012) only exist in the git history.

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
2. **`_shared` is not a skill** — helpers (`rup.py`, `discipline.py`,
   `context.py`); it goes to the agent's skills root, not to the category.
   Every `run.py` looks for it next to the skill and one level up (Hermes).
3. **Skill protocol** — `run.py "<briefing>" [--input F] [--phase P]
   [--context-dir D]` prints the work packet; the agent writes one document with
   `## <Artifact>` per required artifact; `run.py --record FILE|- --phase P`
   validates and writes `.context/`. The orchestrator adds `--discipline`,
   `--auto`, `--status`, `--list`, `--estimate`, `--sizing`, `--sizing-template`,
   `--json`. Exit codes: 0 ok · 1 usage/missing artifacts · 4 `.context/` not writable.
4. **A discipline's roles/artifacts are data** — the `SPEC` dict in its
   `run.py`; the behavior is in `_shared/discipline.py`. Never reintroduce an
   LLM client, API key or third-party runtime dependency (tests run `python -S`).
5. **Artifacts always go to `.context/`** — `.context/docs/<NN-phase>/rup-<skill>.md`
   + `.context/tracking/rup-log.md` (ADR-0011). Tests must point `RUP_CONTEXT_DIR`
   at a temp dir (the `clean_env` fixture does) — never write into this repo's `.context/`.
6. **Windows**: the skills force UTF-8 on stdout/stderr (`setup_console`).
7. **Before committing**: `git status --short` (partial commits are the most
   common mistake here) and `.venv/bin/python -m pytest` (~3 s).
