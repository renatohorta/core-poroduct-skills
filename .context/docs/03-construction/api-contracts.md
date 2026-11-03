# API Contracts — Core Product Skills

> Updated 2026-11-03 (RUP family).

## Status

- [x] Done (derived from the code; enforced by `tests/test_smoke.py`)

## Overview

The skills are **CLI tools**, not a REST API. The contracts are the CLI of each
`rup-*` skill and the files they exchange.

## CLI contract — every discipline skill

```
python skills/rup-<discipline>/scripts/run.py "<briefing>"
       [--input FILE]          # briefing/context from a file (overrides the positional)
       [--phase {Inception,Elaboration,Construction,Transition}]   # default Elaboration
       [--output FILE]         # write the crew result (parent dirs are created)
       [--dry-run]             # show the crew/agents, no LLM call (works without crewai)
```

## CLI contract — `rup-orchestrator` (adds)

| Flag | Meaning | Needs LLM? | Needs crewai? |
|------|---------|-----------|---------------|
| `--discipline <key>` | Dispatch one discipline (briefing positional) | via the child | via the child |
| `--auto` | Dispatch the 8 disciplines in order, chained | via the children | via the children |
| `--list` | List the disciplines | No | No |
| `--estimate [--sizing F] [--json]` | Use Case Points | No | No |
| `--sizing-template` | Print an empty sizing model | No | No |

Discipline keys: `environment`, `business-modeling`, `requirements`,
`analysis-design`, `implementation`, `test`, `ccm`, `deployment`.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Usage error — missing briefing, unreadable `--input`, invalid sizing model, missing discipline skill |
| 2 | No LLM configured (`require_llm`) |
| 3 | `crewai` not installed (`require_crewai`) |

In `--auto` the orchestrator exits with the code of the first failing discipline.

## Data contracts

### `--auto` artifacts

| `--output` | Discipline artifact path |
|------------|--------------------------|
| `out/iter.md` | `out/iter.01-environment.md` … `out/iter.08-deployment.md` |
| omitted | temporary workdir (deleted at the end; results still printed to stdout) |

Each discipline's `--input` is the briefing followed by
`# ARTIFACTS FROM PREVIOUS RUP DISCIPLINES (this iteration)` and one
`## <Title> (<key>)` section per earlier artifact (each capped at 12 000 chars).

### Sizing model (`--sizing` file and `use_case_points_calculator` input)

```json
{
  "actors":   [{"type": "simple|average|complex", "count": 0}],
  "usecases": [{"type": "simple|average|complex", "count": 0}],
  "technical_factors":     {"T1": 0, "...": "0..5, T1..T13, empty = neutral"},
  "environmental_factors": {"F1": 0, "...": "0..5, F1..F8, empty = neutral"},
  "productivity_hours": 20
}
```

Output: `uaw`, `uucw`, `uucp`, `tcf`, `ef`, `ucp`, `effort_hours` (+ inputs and
factor sums). Invalid input → CLI exit 1 / tool returns `ERROR: …`.

## Decisions

- Communication between skills is via `subprocess` + files, not Python import
  (ADR-0004).
