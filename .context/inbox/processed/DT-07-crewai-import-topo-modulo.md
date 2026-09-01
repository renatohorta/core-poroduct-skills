# DT-07 — `crewai` imported at the top of the module blocks even `--help` [Fixed]

**Type**: Technical debt · **Priority**: High · **Opened on**: 2026-08-18
**Verified empirically**: yes (12/15 skills fail)

## Symptom

Without `crewai` installed, **12 of the 15 skills** die at import — not even
`--help` works:

```
ModuleNotFoundError: No module named 'crewai'
  File ".../cp-requirements/scripts/run.py", line 19, in <module>
    from crewai import Agent, Task, Crew, Process
```

Affects: `cp-architecture`, `cp-bug-fix`, `cp-competitive-analysis`, `cp-devops`,
`cp-documentation`, `cp-goal-loop`, `cp-implementation`, `cp-maintenance`,
`cp-quality`, `cp-requirements`, `cp-security`, `cp-testing`.

Does not affect: `cp-agile` and `cp-doc-initializer` (do not use an LLM) and
`cp-orchestrator` (already uses late import inside functions — see "Reference").

## Impact

- Impossible to inspect a skill's CLI contract without installing the heavy lib.
- Impossible to write a `--help`/`--dry-run` smoke test (blocks DT-02/DT-03).
- The error message is a traceback, not an actionable instruction.

## Reference — the correct pattern already exists in the repository

`cp-orchestrator/scripts/run.py` does a late import with a clear message:

```python
try:
    from crewai import Agent, Task, Crew, Process
except ImportError:
    print("❌ crewai not installed. Run: pip install crewai")
    sys.exit(1)
```

## Proposed fix

Replace the top-level import with the same pattern, moving `from crewai import ...`
inside `get_agent()`/`build_crew()`, or use a guard at the top:

```python
try:
    from crewai import Agent, Task, Crew, Process
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    Agent = Task = Crew = Process = None
```

...and check `CREWAI_AVAILABLE` only at the real execution point (`kickoff`),
letting `--help` and `--dry-run` always work.

## Acceptance criterion

- `python skills/cp-<any>/scripts/run.py --help` returns 0 in a clean venv.
- Running without `crewai` produces an actionable message and exit code ≠ 0.


---

## Resolution

**Fixed on 2026-08-18**, propagated to the agents via `./scripts/install.sh`.
Verified empirically with the two-layer harness (without `crewai` / with
`crewai` stub and no key). See `.context/docs/04-quality-qa.md`.
