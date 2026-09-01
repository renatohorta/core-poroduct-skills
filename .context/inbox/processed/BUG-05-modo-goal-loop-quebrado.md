# BUG-05 — Orchestrator's `goal-loop` mode is broken [Fixed]

**Type**: Bug · **Severity**: Medium · **Opened on**: 2026-08-18
**Verified empirically**: yes

## Symptom

The example documented in the `cp-orchestrator` `SKILL.md` fails:

```bash
python run.py "deploy in staging working" --mode goal-loop --auto
```

The skill exits with code 1:

```
[!] Provide --steps or --steps-file
```

## Cause

Divergent contract between what the orchestrator sends and what the skill requires:

| | |
|---|---|
| Orchestrator sends (`invoke.briefing_arg = "goal"`) | `--goal <briefing>` |
| `cp-goal-loop` requires | `--goal` **and** (`--steps` or `--steps-file`) |

The `cli_args` declared in the crew already list `--steps`, but `_build_cli_args()`
only builds `--goal` — the `cli_args` metadata is documentary, not used to build
the call.

## Proposed fix

Two options:

1. **Derive the steps from the briefing** — the orchestrator breaks the briefing
   into steps and sends `--steps`. More aligned with the orchestrator role,
   requires heuristics.
2. **Make `--steps` optional in the skill** — without steps, `cp-goal-loop`
   derives a single step from the `--goal`. Smaller change, and the
   try-and-correct loop still makes sense with a single step.

I recommend (2): it keeps the `invoke` contract simple and makes the documented
example work.

## Acceptance criterion

- `python run.py "<goal>" --mode goal-loop --auto` runs without an argument error.
- This case becomes a DT-03 test (`invoke` × `argparse` contract validation).


---

## Resolution

**Fixed on 2026-08-18**, propagated to the agents via `./scripts/install.sh`.
Verified empirically with the two-layer harness (without `crewai` / with
`crewai` stub and no key). See `.context/docs/04-quality-qa.md`.
