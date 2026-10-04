# Quality and QA — Core Product Skills

> ⚠️ **DEPRECATED MODE** — all `cp-*` skills live in **`skills/deprecated/`** and
> are no longer installed or orchestrated by default (ADR-0007).

> Disciplines: Testing (`cp-testing`), Quality (`cp-quality`), Documentation
> (`cp-software-spec`), Bug-fix (`cp-bug-fix`). Updated 2026-10-04.

## Status

- [x] Done (initial diagnosis)
- ⚠️ **No automated tests** — the repository's biggest quality gap

## Current state (2026-08-18, after the fix round)

| Metric | Value |
|--------|-------|
| `cp-*` skills | 15 |
| Automated tests | **158** (+1 skip: the agile daemon) |
| Suite time | ~2min, with no credentials |
| CI pipeline | ✅ GitHub Actions (Linux 3.12/3.13 blocking, Windows informative) |
| Dependency manifest | ✅ `requirements.txt` (crewai>=1.15,<2) + `requirements-dev.txt` |
| Linter/formatter | ❌ None |

### Suite coverage

| File | What it guarantees |
|------|--------------------|
| `tests/test_smoke.py` | `--help` in every skill (even without `crewai`); `--dry-run` without credentials; exit codes 2/3 with actionable message |
| `tests/test_contrato_invoke.py` | `invoke` × `argparse` — including running the line the orchestrator would build |
| `tests/test_quality_gate.py` | Regression of BUG-03 and BUG-04 |
| `tests/test_claude_proxy_auth.py` | Proxy authentication and localhost bind |
| `tests/test_higiene.py` | Secrets and machine paths in committed files |

The `test_comando_montado_pelo_orquestrador_e_aceito` test was validated by
reintroducing BUG-05: it failed pointing out the exact command and the skill's
message.

**What the suite does not cover**: the internal logic of the crews (task
assembly, agent chaining) and any behavior that depends on an LLM response —
deliberate, as they are expensive and non-deterministic.

## Test strategy — implemented

As the skills are self-contained CLI scripts, the highest-return test is the
**CLI contract smoke test** — cheap, deterministic and catches the most frequent
bug class (a skill called with a flag it rejects).

| Level | Scope | How |
|-------|-------|-----|
| **Smoke (P0)** | Each skill responds to `--help` and `--dry-run` with exit 0 | `pytest` parametrized over `skills/deprecated/*/scripts/run.py` |
| **Contract (P0)** | The `invoke` declared in the orchestrator matches the skill's real `argparse` | Parse `add_argument` of each `run.py` and compare with `CREWS[...]['invoke']` |
| **Integration (P1)** | `install.sh --dry-run` lists all skills and `_shared` | Assert on the output |
| **Unit (P1)** | `_shared/llm.py`: resolution order and provider mapping | `pytest` with `monkeypatch` of env |
| **E2E (P2)** | A short pipeline (`--mode doc-initializer --auto`) in a tempdir | Assert on the generated `.context/` structure |

## Quality checklist per change

Before considering a skill change complete:

- [ ] `python skills/deprecated/cp-<name>/scripts/run.py --help` returns 0
- [ ] `python .../run.py "<briefing>" --dry-run` shows the expected plan
- [ ] If the CLI contract changed, `CREWS[...]['invoke']` was updated in the orchestrator
- [ ] `./scripts/install.sh --dry-run` still lists the skill
- [ ] `git status --short` checked before committing (avoids partial commits)
- [ ] Discipline documentation updated in `.context/docs/`

## Execution without a configured LLM — 2026-08-18 audit

Audited question: **do the skills run without a configured LLM?**

Method: each skill executed with `--help` and `--dry-run` in an environment with
the 15 credential variables removed (`LLM_*`, `GEMINI_API_KEY`, `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, …) and no `.env` at the root. Then repeated with an
instrumented `crewai` stub on the `PYTHONPATH`, to separate "missing the lib" from
"missing the key".

### Result — before × after the fixes

| Scenario | Before | After |
|----------|--------|-------|
| `--help` without `crewai` | 3/15 skills work | **15/15** ✅ |
| `--dry-run` without `crewai` | `ModuleNotFoundError` traceback | actionable message, exit 3 |
| `--dry-run` with `crewai`, no key | works | works (unchanged) ✅ |
| Real execution without key | 4–5 agents with `llm=None` reach `kickoff()` **without warning** | fails before building the crew, exit 2, actionable message |
| Skill crashes during the pipeline | gate WARN → "✅ Pipeline completed successfully" | gate **FAIL** → pipeline stops |

### Verdict per skill (holds after the fixes)

| Skill | Runs without LLM? | Note |
|-------|-------------------|------|
| `cp-doc-initializer` | ✅ **Yes, fully** | Pure Python, deterministic — does not even import `crewai` |
| `cp-agile` | ✅ **Yes, fully** | Pure Python; the daemon/kanban does not use an LLM |
| `cp-orchestrator` | ⚠️ **Partially** | `--dry-run` (plan) and `--auto` work; the simulation mode (default) requires an LLM |
| the other 12 | ❌ **No, by design** | A CrewAI crew **is** an LLM call |

The LLM dependency in the 12 skills is inherent and was not removed — what
changed is that they now **fail well**: `--help` always works, `--dry-run` lets
you inspect the crew without credentials, and the failure says what to do instead
of showing a traceback.

### Known limitation

`--dry-run` **without `crewai` installed** does not build the crew (exits with
code 3 and an install instruction). Building the crew requires the real CrewAI
classes. Only `--help` is guaranteed without the lib.

### Standardized exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Usage error (missing briefing, invalid argument) |
| **2** | No LLM configured (`require_llm`) |
| **3** | `crewai` not installed (`require_crewai`) |

## Known bugs and defects

| ID | Defect | Severity | Status |
|----|--------|----------|--------|
| DOC-01 | `claude_proxy.py` port diverges between README (8090) and code (8080) | Low | 🔵 Open |
| ~~BUG-03~~ | ~~Quality gate ignores exit code~~ | High | ✅ Fixed 2026-08-18 |
| ~~BUG-04~~ | ~~`"OK"` as substring produces false PASS~~ | Medium | ✅ Fixed 2026-08-18 |
| ~~BUG-05~~ | ~~`goal-loop` mode broken (missing `--steps`)~~ | Medium | ✅ Fixed 2026-08-18 |
| ~~DT-01~~ | ~~`UnicodeEncodeError` on Windows console~~ | Medium | ✅ Fixed 2026-08-18 |

Resolved items in `.context/inbox/processed/`; open ones in `.context/inbox/`.

## Durable pitfalls (recorded lessons)

1. **Never assume a skill's CLI contract** — `--output` is not universal; the
   briefing is not always positional. Consult
   `skills/deprecated/cp-orchestrator/references/skills-cli-inventory.md`.
2. **`git status --short` before committing** — commits come out incomplete when
   not all files were staged.
3. **Do not rely on an optional flag the LLM must remember to set** — the correct
   mode should be auto-detected from context.
4. **"Correct code but no effect in the app"** — confirm which clone of the
   repository the process is running from before debugging the logic.
5. **The roadmap lies** — cross-check the declared state against the real code
   before reporting "what is missing".

## Documentation

| Artifact | Location | Status |
|----------|----------|--------|
| Overview and quick install | `README.md` | ✅ Updated |
| Detailed install | `docs/INSTALLATION.md` | ✅ |
| Architecture | `docs/ARCHITECTURE.md` | ✅ |
| Skills catalog | `docs/SKILLS.md` | ✅ |
| Canonical context | `.context/` | ✅ Initialized in this round |
| Agent pointers | `CLAUDE.md`, `AGENT.md` | ✅ |

> Note: `docs/` (the **repository's** documentation, aimed at humans) and
> `.context/` (the **project's** context, source of truth for agents) coexist.
> `.context/` prevails in case of divergence.

## Decisions

- Prioritize smoke + contract before any crew test: testing the LLM itself is
  expensive, non-deterministic and does not catch the bugs that actually occur.


## Artifact — Bug Fix (NEXUS-Micro) (2026-08-18 13:26)

```

Traceback (most recent call last):
  File "C:\Users\renat\.claude\skills\cp-bug-fix\scripts\run.py", line 17, in <module>
    from crewai import Agent, Task, Crew, Process
ModuleNotFoundError: No module named 'crewai'

```


## Artifact — Bug Fix (NEXUS-Micro) (2026-08-18 13:36)

```

[X] crewai not installed - required to run this skill.
    Install with:  pip install crewai
    (--help still works without the lib.)

```
