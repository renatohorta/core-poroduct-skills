# Product Vision — Core Product Skills

> Source of truth: `.context/`. Updated 2026-11-03.

## Status

- [x] Done (vision updated for the RUP family — ADR-0008, ADR-0010)

## What it is

**Core Product Skills** is the canonical repository of the **`rup-*` skills**: a
team of CrewAI agents that implements the **Rational Unified Process** (Kruchten,
*The Rational Unified Process: An Introduction*, 3rd ed.) — 9 disciplines, 1
orchestrator and 20 specialist agents.

This repository is the **single source code**: any change is made here and
propagated to the consuming agents (**Hermes Agent** and **Claude Code**) via
`scripts/install.sh`.

> History: the repository previously hosted the Software Factory family
> (`cp-*`). It was deprecated (ADR-0007) and then removed (ADR-0010); it remains
> in the git history up to commit `6490694`.

## Problem it solves

Without this repository, each agent would have its own divergent copy of the
skills, with hardcoded paths and LLM configuration coupled to a provider. That
caused:

- **Divergence** between the skill installed in Hermes and the one installed in Claude.
- **Rework** when fixing the same bug in two places.
- **Provider coupling** — the crews fell into the CrewAI OpenAI default
  (`OPENAI_API_KEY is required`) even with another provider configured.

## Value proposition

| Pillar | How it materializes |
|--------|---------------------|
| **Single source of truth** | Skills edited in `skills/`, propagated by `install.sh` |
| **Single entry point** | `rup-orchestrator` governs the lifecycle and dispatches the disciplines |
| **Faithful to RUP** | Phases/milestones (LCO, LCA, IOC, PR), roles and artifacts from Kruchten |
| **Deterministic where possible** | Use Case Points computed in code, exposed to the agent as a tool |
| **Provider-agnostic** | `skills/_shared/llm.py` resolves the host agent's LLM |
| **Portability** | Zero OS/machine paths and zero hardcoded personal values |

## Users

| Persona | Use |
|---------|-----|
| **Hermes Agent** | Consumes the skills installed in `$HERMES_SKILLS_DIR/creative/` |
| **Claude Code** | Consumes the skills installed in `~/.claude/skills/` |
| **Developer/maintainer** | Edits the skills here and runs `install.sh` |
| **CLI operator** | Triggers skills directly via `scripts/chat.py` |

## Scope

**In scope**
- Source code of the 9 `rup-*` skills (SKILL.md + `scripts/run.py` + `references/`)
- Shared LLM helper (`skills/_shared/llm.py`)
- Install/propagation script (`scripts/install.sh`)
- Support tools: direct chat (`scripts/chat.py`) and OpenAI-compatible proxy
  to use Claude Code as the LLM (`scripts/claude_proxy.py`)

**Out of scope**
- Agent runtime (Hermes Agent and Claude Code are separate projects)
- The target projects where the skills run
- LLM hosting/infra — the repository only resolves credentials and endpoints

## Design principles

1. **Skill is self-contained** — each `run.py` embeds its own agents; it does
   not depend on an external agents directory.
2. **The orchestrator is the single interface** — the user talks to
   `rup-orchestrator`; it plans, sizes, emits Work Orders and dispatches.
3. **Uniform CLI contract** — every skill takes
   `"<briefing>" [--phase] [--input] [--output] [--dry-run]`; test with `--dry-run`.
4. **Compute, don't guess** — deterministic formulas (UCP) run in code and are
   given to the LLM as tools.
5. **Documentation in `.context/`** — never in `.hermes/` or `.claude/`.

## Decisions

- **ADR-0001** — Source of truth in `.context/`.
- **ADR-0003** — Provider-agnostic LLM via `skills/_shared/llm.py`.
- **ADR-0008** — RUP family as the active product.
- **ADR-0009** — Use Case Points computed in the orchestrator.
- **ADR-0010** — `cp-*` removed; RUP skills flattened into `skills/`.
