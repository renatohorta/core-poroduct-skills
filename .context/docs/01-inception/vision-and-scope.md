# Product Vision — Core Product Skills

> Source of truth: `.context/`. Updated 2026-11-03.

## Status

- [x] Done (vision updated for the RUP family — ADR-0008, ADR-0010)

## What it is

**Core Product Skills** is the canonical repository of the **`cp-*` skills**,
which implement the **Rational Unified Process** (Kruchten, *The Rational Unified
Process: An Introduction*, 3rd ed.) — 9 disciplines, 1 orchestrator and 20
specialist roles. **The agent running a skill (Claude Code, Hermes) is the LLM**
(ADR-0012): the skills hand it a work packet and record its artifacts into the
project's `.context/`.

This repository is the **single source code**: any change is made here and
propagated to the consuming agents (**Hermes Agent** and **Claude Code**) via
`scripts/install.sh`.

> History: the repository previously hosted the Software Factory family
> (also `cp-*`, different skills). It was deprecated (ADR-0007) and then removed (ADR-0010); it remains
> in the git history up to commit `6490694`.

## Problem it solves

Without this repository, each agent would have its own divergent copy of the
skills. That caused:

- **Divergence** between the skill installed in Hermes and the one installed in Claude.
- **Rework** when fixing the same bug in two places.

And running the RUP roles as a separate LLM pipeline (the former CrewAI crews)
meant a second model, its own API key or a proxy, cost on top of the agent's,
and the loss of the conversation context the agent already had (ADR-0012).

## Value proposition

| Pillar | How it materializes |
|--------|---------------------|
| **Single source of truth** | Skills edited in `skills/`, propagated by `install.sh` |
| **Single entry point** | `cp-orchestrator` governs the lifecycle and dispatches the disciplines |
| **Faithful to RUP** | Phases/milestones (LCO, LCA, IOC, PR), roles and artifacts from Kruchten |
| **Deterministic where possible** | Use Case Points computed in code, exposed to the agent as a tool |
| **Same LLM, same context** | The host agent plays the RUP roles itself — no API key, proxy or extra model |
| **Persisted** | Every artifact recorded in the project's `.context/` (ADR-0011) |
| **Portability** | Zero OS/machine paths and zero hardcoded personal values |

## Users

| Persona | Use |
|---------|-----|
| **Hermes Agent** | Consumes the skills installed in `$HERMES_SKILLS_DIR/creative/` |
| **Claude Code** | Consumes the skills installed in `~/.claude/skills/` |
| **Developer/maintainer** | Edits the skills here and runs `install.sh` |
| **CLI operator** | Runs `run.py` by hand to read a packet or record a document |

## Scope

**In scope**
- Source code of the 9 `cp-*` skills (SKILL.md + `scripts/run.py` + `references/`)
- Shared helpers (`skills/_shared/`: registry, packet/record engine, `.context/` writer)
- Install/propagation script (`scripts/install.sh`)

**Out of scope**
- Agent runtime (Hermes Agent and Claude Code are separate projects)
- The target projects where the skills run
- Any LLM client, credential or endpoint — the host agent is the model

## Design principles

1. **Skill is self-contained** — each `run.py` embeds its own agents; it does
   not depend on an external agents directory.
2. **The orchestrator is the single interface** — the user talks to
   `cp-orchestrator`; it plans, sizes, emits Work Orders and dispatches.
3. **Uniform protocol** — packet (`"<briefing>" [--input] [--phase]`) → one
   document with `## <Artifact>` per required artifact → `--record`.
4. **Compute, don't guess** — deterministic formulas (UCP) run in code
   (`--estimate`); the packet tells the agent to use them.
5. **Documentation in `.context/`** — never in `.hermes/` or `.claude/`.

## Decisions

- **ADR-0001** — Source of truth in `.context/`.
- **ADR-0011** — Artifacts always persisted into `.context/`.
- **ADR-0008** — RUP family as the active product.
- **ADR-0009** — Use Case Points computed in the orchestrator.
- **ADR-0010** — legacy Software Factory `cp-*` removed; RUP skills flattened into `skills/`.
- **ADR-0014** — RUP skills renamed from `rup-*` to `cp-*`.
- **ADR-0012** — The host agent is the LLM; CrewAI, `llm.py`, proxy and chat removed.
