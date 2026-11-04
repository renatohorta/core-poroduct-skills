# AGENT.md — Project Context

**Project**: Core Product Skills — canonical repository of the **RUP skills**
(`skills/cp-*`: 9 document skills + 6 execution skills, ADR-0013) propagated to the Hermes Agent and Claude Code. **The agent
running a skill is the LLM** (ADR-0012): the skills never call a model and are
pure standard library. The legacy Software Factory family (removed in ADR-0010) also used the `cp-` prefix; the current `cp-*` skills are the RUP skills, renamed from `rup-*` in ADR-0014. The CrewAI
execution (ADR-0012) only exists in the git history.

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
   `context.py`, `consent.py`, `frontmatter.py`, `cards.py`, `roadmap.py`,
   `testcheck*.py`, `testaudit.py`, `mutation.py`, `router.py`); it goes to the agent's skills root, not to the category.
   Every `run.py` looks for it next to the skill and one level up (Hermes).
3. **Skill protocol** — `run.py "<briefing>" [--input F] [--phase P]
   [--context-dir D]` prints the work packet; the agent writes one document with
   `## <Artifact>` per required artifact; `run.py --record FILE|- --phase P`
   validates and writes `.context/`. The orchestrator adds `--discipline`,
   `--auto`, `--status`, `--list`, `--estimate`, `--sizing`, `--sizing-template`,
   `--json`. Exit codes: 0 ok · 1 usage/invalid document/rejected delivery ·
   4 `.context/` not writable · 5 needs authorization (no `.context/.rup-standard`
   marker; the agent asks the user, then runs `cp-context --init`).
   The execution skills (`cp-context`, `cp-discover`, `cp-backlog`,
   `cp-build`, `cp-debug`, `cp-review`) add their own commands; see each
   `SKILL.md`.
4. **A discipline's roles/artifacts are data** — the `SPEC` dict in its
   `run.py`; the behavior is in `_shared/discipline.py`. Never reintroduce an
   LLM client, API key or third-party runtime dependency (tests run `python -S`).
5. **Artifacts always go to `.context/`** — `.context/docs/<NN-phase>/cp-<skill>.md`
   + `.context/tracking/rup-log.md` (ADR-0011). Tests must point `RUP_CONTEXT_DIR`
   at a temp dir (the `clean_env` fixture does) — never write into this repo's `.context/`.
6. **Cards and views** — cards are `.context/kanban/<column>/<ID>.md`
   (`EP/ST/TK/BUG-NNN`, criteria `ST-NNN/AC-n`, `## History` last); the roadmap
   lives in `.context/roadmap/`; `docs/06-roadmap.md` and `docs/06-board.md` are
   generated, never hand-edited. The skills never run git, and never run the
   project's tests — except `cp-test --mutate`, which runs the command of
   `.context/tests/profile.json` in disposable copies of the project (ADR-0016).
7. **Windows**: the skills force UTF-8 on stdout/stderr (`setup_console`).
8. **Before committing**: `git status --short` (partial commits are the most
   common mistake here) and `.venv/bin/python -m pytest` (~5 s).

<!-- rup-skills:start -->
## RUP skills — which one to use
- Any request, or not sure which: `cp-orchestrator --route "<request>"` — the
  agent routes it and runs the skills itself; the user never has to name one.
- Before building anything new: `cp-discover`
- Plan epics/stories/tasks, roadmap, move cards: `cp-backlog`
- Implement a task (TDD): `cp-build`
- Fix a bug: `cp-debug`
- Do the tests catch bugs? (static audit, mutation): `cp-test --audit`
- Review a delivered card: `cp-review`
- RUP documents (governance, disciplines): `cp-orchestrator`
- Project context lives in `.context/` (set up with `cp-context`).
<!-- rup-skills:end -->
