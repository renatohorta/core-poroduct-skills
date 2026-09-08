# API Contracts — Core Product Skills

> Document managed by the `cp-software-spec` skill. Updated 2026-09-07.

## Status

- [x] In progress (derived from the existing code)

## Overview

The skills are **CLI tools**, not a REST API. The "contracts" here are the
**CLI contracts** of each `cp-*` skill — the `invoke` metadata that the
orchestrator uses to trigger them via subprocess. This is the operational
contract that matters for replication.

## CLI contract per skill

| Skill | Briefing | `--output` | Extra flags |
|-------|----------|-----------|-------------|
| `cp-requirements` | positional / `--input` | YES | — |
| `cp-architecture` | positional / `--input` | YES | — |
| `cp-implementation` | positional / `--input` | YES | `--type` |
| `cp-testing` | positional / `--input` | YES | `--source`, `--acceptance`, `--mode` |
| `cp-security` | positional / `--input` | YES | `--mode` |
| `cp-devops` | positional / `--input` | YES | `--mode` |
| `cp-quality` | positional / `--input` | YES | `--mode` |
| `cp-bug-fix` | positional (`bug_description`) | **NO** | `--type backend/frontend` |
| `cp-competitive-analysis` | positional / `--input` | YES | — |
| `cp-goal-loop` | **`--goal` (required)** | **NO** | `--steps`, `--max-attempts`, `--max-time` |
| `cp-maintenance` | positional / `--input` | YES | `--mode` |
| `cp-agile` | **`--daemon` (no positional)** | **NO** | `--sync-trello`, `--question`, `--blocker`, `--resume`, `--init`, `--doc` |
| `cp-software-spec` | **`--init` / `--inspect <path>` / `--refine-card <ID>`** | **NO** | `--dir`, `--force`, `--dry-run` |

> Full inventory and verification snippet:
> `skills/cp-orchestrator/references/skills-cli-inventory.md`.

## Orchestrator `invoke` metadata

The orchestrator declares, per crew, how the briefing enters and whether the
skill accepts `--output`:

| `briefing_arg` | How the briefing is passed | Example |
|----------------|---------------------------|---------|
| `positional` | positional argument | `cp-bug-fix` |
| `goal` | `--goal <briefing>` | `cp-goal-loop` |
| `input` | positional in the 1st phase; `--input <ctx>` in the following | pipeline phases |
| `daemon` | no briefing — builds `--daemon` | `cp-agile` |
| `dir` | no briefing — builds `--init --dir <cwd>` | `cp-software-spec` |
| `inspect` | no briefing — builds `--inspect <cwd>` | `documentation` |

## Data contracts

The skills exchange **markdown artifacts** via files. The orchestrator passes
the previous phase's artifact as `--input <ctx_file>` (a `_ctx_<phase>.txt`
with the briefing + previous artifact, truncated to 3000 chars).

```json
{
  "phase_artifact": {
    "source": "cp-orchestrator/outputs/pipeline_<ts>/<phase>.md",
    "passed_to_next": "via --input _ctx_<phase>.txt"
  }
}
```

## Decisions

- Communication between skills is via `subprocess` + files, not Python import
  (ADR-0004) — keeps each skill self-contained and independently installable.
