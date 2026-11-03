# Quality and QA — Core Product Skills

> Updated 2026-11-03 (RUP family, ADR-0010).

## Status

- [x] Done — suite green: **108 passed**, no credentials, ~50 s

## Current state

| Metric | Value |
|--------|-------|
| `rup-*` skills | 9 (orchestrator + 8 disciplines) |
| Automated tests | 108 |
| CI pipeline | ✅ GitHub Actions on `main` + PRs (Linux 3.12/3.13 blocking, Windows informative) |
| Dependency manifest | ✅ `requirements.txt` (crewai>=1.15,<2) + `requirements-dev.txt` |
| Linter/formatter | ❌ None |

### Suite coverage

| File | What it guarantees |
|------|--------------------|
| `tests/test_smoke.py` | Per skill: `--help` (also without crewai), `--dry-run` without credentials and without crewai, exit 2 without LLM, exit 3 without crewai, exit 1 on unreadable `--input`, `SKILL.md` + `references/` present. Orchestrator: `--list`, registry == skill dirs, `--discipline`/`--auto` dry-run, `--auto` per-discipline output paths, chained context (incl. truncation and missing artifacts), stop at first failure. UCP: hand-calculated reference, neutral factors, CLI `--estimate`/`--sizing-template`, input validation, tool body, tool attached to the governance agent. `install.sh`: dry-run plan, real install into temp Claude + Hermes layouts and the installed orchestrator running from both |
| `tests/test_claude_proxy_auth.py` | Proxy authentication and localhost bind |
| `tests/test_higiene.py` | Secrets and machine paths in committed files |

**What the suite does not cover**: anything that depends on an LLM response
(the content of the artifacts) — deliberate: expensive, slow, non-deterministic.

## Test strategy

The skills are self-contained CLI scripts, so the highest-return tests are the
**CLI contract** and **error handling** — cheap, deterministic, and where the
real bugs have been.

| Level | Scope | How |
|-------|-------|-----|
| **Smoke (P0)** | Every skill: `--help`, `--dry-run`, exit codes | `pytest` parametrized over `skills/rup-*/scripts/run.py` |
| **Contract (P0)** | Orchestrator registry == discipline skills; dispatch command accepted | registry parse + `--auto` run without LLM |
| **Unit (P1)** | UCP, sizing validation, `--auto` path/context helpers | import `run.py` as a module |
| **Integration (P1)** | `install.sh` plan and installed copies in both agent layouts | temp `HERMES_SKILLS_DIR`/`CLAUDE_SKILLS_DIR` |

## Quality checklist per change

- [ ] `python skills/rup-<name>/scripts/run.py --help` returns 0
- [ ] `python .../run.py "<briefing>" --dry-run` shows the expected plan
- [ ] A new discipline is registered in `DISCIPLINES` and has a skill dir
- [ ] `./scripts/install.sh --dry-run` still lists the skill
- [ ] `.venv/bin/python -m pytest` green
- [ ] `git status --short` checked before committing (avoids partial commits)
- [ ] `.context/docs/` updated

## Execution without a configured LLM

| Scenario | Behavior |
|----------|----------|
| `--help` without `crewai` | works (exit 0) |
| `--dry-run` without `crewai` | lists the planned agents from the embedded definitions (exit 0) |
| `--dry-run` with `crewai`, no key | builds the crew and lists agents (exit 0) |
| Real execution without key | exit 2, says which variable to set and points to `--dry-run` |
| Real execution without `crewai` | exit 3, `pip install crewai` |
| `--estimate`, `--sizing-template`, `--list` | never need crewai or an LLM |

## Durable pitfalls (recorded lessons)

1. **`git status --short` before committing** — commits come out incomplete when
   not all files were staged.
2. **Do not let the LLM do arithmetic** — deterministic formulas go in code and
   are offered to the agent as a tool (UCP).
3. **Shared output path in a loop** — writing every iteration to the same file
   silently keeps only the last one (the old `--auto` bug).
4. **GNU-only shell flags** — `find -printf` silently returned nothing on macOS
   (hidden by `|| true`); prefer bash globs.
5. **"Correct code but no effect in the app"** — confirm which clone/installed
   copy the process is running from before debugging the logic.

## Documentation

| Artifact | Location |
|----------|----------|
| Overview and quick install | `README.md` |
| Detailed install | `docs/INSTALLATION.md` |
| Architecture | `docs/ARCHITECTURE.md` |
| Skills catalog | `docs/SKILLS.md`, `skills/README.md` |
| Canonical context | `.context/` |
| Agent pointers | `CLAUDE.md`, `AGENT.md` |

> `docs/` is aimed at humans; `.context/` is the source of truth for agents and
> prevails in case of divergence.

## Decisions

- Prioritize smoke + contract before any crew test: testing the LLM itself is
  expensive, non-deterministic and does not catch the bugs that actually occur.
