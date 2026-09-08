# CLAUDE.md — Project Context

**Project**: Core Product Skills — canonical repository of the `cp-*` skills of
the Software Factory (CrewAI), propagated to the Hermes Agent and Claude Code.

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
   skills root, not to the category.
3. **Never assume a skill's CLI contract** — `--output` is not universal and the
   briefing is not always positional. Consult
   `skills/cp-orchestrator/references/skills-cli-inventory.md` and validate with
   `--dry-run`.
4. **Windows**: run the skills with `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` until
   `DT-01` is fixed.
5. **Before committing**: check `git status --short` — partial commits are the
   most common mistake here.
6. **Documentation skill**: `cp-software-spec` unifies initialization,
   reverse engineering and card refinement (Backlog → ToDo). It replaces the
   legacy `cp-doc-initializer` and `cp-documentation`.
