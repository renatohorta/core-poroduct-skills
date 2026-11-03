# API Contracts — Core Product Skills

> Updated 2026-11-03 (host-LLM model — ADR-0012).

## Status

- [x] Done (derived from the code; enforced by `tests/`)

## Overview

The skills are **CLI tools** used by an agent (the LLM). The contracts are the
CLI, the work packet, the recorded document and the `.context/` files.

## CLI — every skill

```
run.py "<briefing>" | --input FILE          # work packet (stdout, read-only)
       [--phase {Inception,Elaboration,Construction,Transition}]   # default Elaboration
       [--context-dir DIR]
run.py --record FILE|-                      # validate + write .context/
       [--phase P] [--context-dir DIR] ["<briefing>" | --input FILE]
```

## CLI — `rup-orchestrator` (adds)

| Flag | Meaning |
|------|---------|
| *(default)* | Governance work packet (`--record` records the governance document) |
| `--discipline <key>` | That discipline's work packet (record with the discipline's own `run.py`) |
| `--auto` | Iteration protocol: step 0 governance + 8 disciplines, in order, with commands + status |
| `--status` | Recorded artifact per step for the phase, and the next pending step |
| `--list` | The disciplines |
| `--estimate [--sizing F] [--json]` | Use Case Points; also recorded as `rup-orchestrator-sizing.md` |
| `--sizing-template` | Empty sizing model |

Discipline keys: `environment`, `business-modeling`, `requirements`,
`analysis-design`, `implementation`, `test`, `ccm`, `deployment`.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Usage error — missing briefing, unreadable `--input`/`--record` source, empty document, **missing required artifacts**, invalid sizing model, `--record` with `--discipline` |
| 4 | `.context/` not writable |

## Recorded document

One markdown document per skill run:

```markdown
# <Role>                       ← one per role, in the packet's order
## <Artifact>                  ← one per required artifact (exact name)
...
```

Validation: each required artifact must appear in a level-2 heading (`## `);
matching ignores case, punctuation and parenthesised qualifiers
(`## Supplementary Specifications` satisfies "Supplementary Specifications (FURPS)").

## `.context/` files (mandatory — ADR-0011)

| Run | File |
|-----|------|
| discipline `<key>` in phase P | `.context/docs/<NN-P>/rup-<key>.md` |
| governance | `.context/docs/<NN-P>/rup-orchestrator.md` |
| `--estimate` | `.context/docs/<NN-P>/rup-orchestrator-sizing.md` |
| every write | one row in `.context/tracking/rup-log.md` |

```markdown
---
skill: rup-requirements
discipline: Requirements
phase: Elaboration
milestone: Lifecycle Architecture (LCA)
generated_at: 2026-11-03T14:30:00
---

# Requirements — Elaboration
## Briefing      (quoted, first 1500 chars)
## Artifacts     (the recorded document)
```

## Sizing model (`--sizing` file)

```json
{
  "actors":   [{"type": "simple|average|complex", "count": 0}],
  "usecases": [{"type": "simple|average|complex", "count": 0}],
  "technical_factors":     {"T1": 0, "...": "0..5, T1..T13, empty = neutral"},
  "environmental_factors": {"F1": 0, "...": "0..5, F1..F8, empty = neutral"},
  "productivity_hours": 20
}
```

Output: `uaw`, `uucw`, `uucp`, `tcf`, `ef`, `ucp`, `effort_hours` (+ inputs).

## Decisions

- Skills talk via `subprocess` + files, not Python import (ADR-0004).
