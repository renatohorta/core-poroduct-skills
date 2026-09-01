# DT-08 — `build_crew_llm()` returns None and nobody checks it [Fixed]

**Type**: Technical debt / Bug · **Priority**: High · **Opened on**: 2026-08-18
**Verified empirically**: yes (13/13 skills that use an LLM)

## Context

`skills/_shared/llm.py` explicitly documents the contract:

> "Returns None if crewai is not installed or if there is no configured key
> (**the skill can then warn** instead of falling into the OpenAI default)."

**No skill implements that "warn".** The pattern in all 13 is:

```python
_crew_llm = build_crew_llm()      # can be None
return Agent(..., llm=_crew_llm)  # never checked
```

A search for any check of `_crew_llm` outside the assignment and the `llm=`:
zero occurrences.

## Evidence

With `crewai` present (instrumented stub) and **no key**, each skill:

| Skill | agents created | with `llm=None` | `LLM()` built | reached `kickoff()` |
|-------|----------------|-----------------|---------------|---------------------|
| cp-requirements | 4 | 4 | no | **yes** |
| cp-architecture | 5 | 5 | no | **yes** |
| cp-implementation | 5 | 5 | no | **yes** |
| cp-testing | 5 | 5 | no | **yes** |
| cp-security / devops / documentation / quality / bug-fix / competitive-analysis / maintenance / orchestrator | 4 | 4 | no | **yes** |

That is: 100% of the agents end up without an LLM and execution advances to
`kickoff()` **without a single warning**. In real CrewAI, `Agent(llm=None)` falls
into the OpenAI default — exactly the `OPENAI_API_KEY is required` the helper
exists to avoid.

## Proposed fix

Fail early, with a message that says what to do. In each skill's `build_crew()`
(or in a new `require_llm()` helper in `_shared/llm.py`):

```python
from _shared.llm import build_crew_llm, get_llm_config

def require_llm():
    llm = build_crew_llm()
    if llm is None:
        cfg = get_llm_config()
        print("❌ No LLM configured.")
        print(f"   Resolved model: {cfg['model']} (no key)")
        print("   Configure LLM_API_KEY/LLM_MODEL in the environment or in .env")
        print("   (see .env.example). Use --dry-run to inspect without an LLM.")
        sys.exit(2)
    return llm
```

Call it at the start of the real execution — **never** in `--dry-run`, which must
keep working without credentials.

## Acceptance criterion

- Without a key, the skill exits with code 2 and an actionable message, before
  building the crew.
- With `--dry-run`, the skill keeps working without a key.


---

## Resolution

**Fixed on 2026-08-18**, propagated to the agents via `./scripts/install.sh`.
Verified empirically with the two-layer harness (without `crewai` / with
`crewai` stub and no key). See `.context/docs/04-quality-qa.md`.
