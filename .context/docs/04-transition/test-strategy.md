# Quality and QA — Core Product Skills

> Updated 2026-11-03 (host-LLM model — ADR-0012; execution skills — ADR-0013).

## Status

- [x] Done — suite green: **268 passed**, ~5 s, no LLM, no third-party runtime

## Current state

| Metric | Value |
|--------|-------|
| `cp-*` skills | 15: 9 document (orchestrator + 8 disciplines, 21 roles) + 6 execution |
| Automated tests | 268 |
| CI pipeline | ✅ GitHub Actions on `main` + PRs (Linux 3.12/3.13 blocking, Windows informative) |
| Dependencies | runtime: none · dev: `pytest` |
| Linter/formatter | ❌ None |

### Suite coverage

| File | What it guarantees |
|------|--------------------|
| `tests/test_smoke.py` | Per skill: `--help`; **stdlib only** (`python -S`); packet with roles, every artifact, briefing and the `--record` command; exit 1 on missing briefing/unreadable `--input`; `--input` reused in the record command; `SKILL.md` teaches `--record`; well-formed `SPEC` (9 skills, 21 roles). Orchestrator: registry == skill dirs, `--list`, `--discipline` packet and its `--record` refusal, `--auto` order and status, sizing instructions in the governance packet. UCP: hand-calculated reference, neutral factors, validation, CLI, template. `install.sh`: dry-run plan; installed copies produce packets in the Claude and Hermes layouts |
| `tests/test_context_persistence.py` | `.context/` resolution (explicit, env, walk-up, git-root stop, fallback), phase layout, provenance, log, curated docs untouched, briefing excerpt, exit 4. End to end: `--record` for all 9 skills (file and stdin), rejection of missing artifacts (nothing written), tolerant heading matching, empty document, record without briefing, packets read-only, **chaining in RUP order** (later never leaks into earlier, header stripped), per-phase isolation, cap on earlier artifacts, `--status`/`--auto` progress, caller's project resolution from `--discipline`, sizing artifact with clean `--json`, guard against writing into this repo |
| `tests/test_consent.py`, `tests/test_rup_context.py` | Marker gate: every writing command exits 5 without it and writes nothing; read-only packets warn; `--init`/upgrade only adds, never overwrites; pointer note added once; import creates missing files / appends delimited blocks, originals untouched |
| `tests/test_frontmatter.py`, `tests/test_cards.py` | Parser/writer round trip; ID sequences, parent rules, criteria numbering, `Covers` validation, History last, moves (skip warning, reason required), roll-up, derivation report |
| `tests/test_roadmap.py` | Release/iteration files, planning, generated views (header, progress, unplanned epics) |
| `tests/test_testcheck.py` | Python (`ast`) and JS/TS checks: missing test, no criterion link, uncovered criterion, no assertion, constant assertion, no project call, missing red evidence |
| `tests/test_rup_{discover,build,debug,review}.py` | Discovery record; start/finish with good and bad deliveries (nothing written on rejection); bug flow (root cause before finish); review checklist and verdict moves |
| `tests/test_higiene.py` | No committed secrets, no machine paths, `.env` never tracked |

The host's writing quality (the artifact content) is not tested — it is the
agent's job; the suite guarantees the contract around it.

## Test strategy

| Level | Scope | How |
|-------|-------|-----|
| **Smoke (P0)** | Every skill's CLI and packet | `pytest` parametrized over `skills/cp-*/scripts/run.py` |
| **Contract (P0)** | Registry == skills; required artifacts in packet and enforced by `--record` | specs imported from `run.py` |
| **E2E (P0)** | packet → document → record → `.context/`, chaining, status | fixed documents built from each `SPEC` (`conftest.full_document`) |
| **Unit (P1)** | UCP, sizing validation, `.context/` helpers, heading matching | direct imports |
| **Integration (P1)** | `install.sh` + installed copies in both agent layouts | temp `HERMES_SKILLS_DIR`/`CLAUDE_SKILLS_DIR` |
| **Flow (P0)** | Execution skills end to end: authorize, create cards, move, plan, start/finish, review | fixed documents in a temp `RUP_CONTEXT_DIR` |

Every test runs with `RUP_CONTEXT_DIR` pointing to a temp dir (`clean_env`).

## Quality checklist per change

- [ ] `.venv/bin/python -m pytest` green (~5 s)
- [ ] A role/artifact change is made in the skill's `SPEC` (not in the engine)
- [ ] A new execution skill: `SKILL.md` <= ~60 lines, `run.py` with the `_shared` bootstrap and `setup_console()`, writing commands behind the marker gate, tests with `python -S`
- [ ] A new discipline: entry in `_shared/rup.py` `DISCIPLINES` + skill dir + `SKILL.md`
- [ ] No third-party import in `skills/` (the `python -S` test enforces it)
- [ ] `./scripts/install.sh --dry-run` lists the skill
- [ ] `git status --short` before committing; `.context/docs/` updated

## Durable pitfalls (recorded lessons)

1. **`git status --short` before committing** — commits come out incomplete when
   not all files were staged.
2. **Do not let the LLM do arithmetic** — deterministic formulas go in code
   (`--estimate`) and the packet tells the agent to run them.
3. **Shared output path in a loop** — writing every iteration to the same file
   silently keeps only the last one (the old `--auto` bug).
6. **A second LLM is a liability** — a separate pipeline (CrewAI + key/proxy)
   lost the host's context, broke tool calls through the proxy and cost twice;
   the host agent is the LLM (ADR-0012).
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

- Test the contract around the agent (packet, validation, persistence,
  chaining), never the agent's prose.
