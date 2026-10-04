# Product Vision — Core Product Skills

> Source of truth: `.context/`. Updated 2026-08-18.

## Status

- [x] Done (initial vision documented)

## What it is

**Core Product Skills** is the canonical repository of the `cp-*` skills of the
**Software Factory** — a set of CrewAI-based skills that orchestrate specialized
agents to run the complete software development cycle, from requirement to
delivery, with quality gates between phases.

This repository is the **single source code**: any change is made here and
propagated to the consuming agents (**Hermes Agent** and **Claude Code**) via
`scripts/install.sh`.

## Status: deprecated (2026-10-04)

> ⚠️ All `cp-*` skills now live in **`skills/deprecated/`** and are in
> **deprecated mode** — `./scripts/install.sh` installs nothing unless given the
> `--deprecated` flag. They are kept for historical reference; the `cp-*` pipeline
> is no longer an active product (ADR-0007).

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
| **Single entry point** | `cp-orchestrator` triggers all other skills by mode |
| **Provider-agnostic** | `skills/deprecated/_shared/llm.py` resolves the host agent's LLM |
| **Portability** | Zero OS/machine paths and zero hardcoded personal values |
| **Quality gates** | Each phase only advances with PASS/WARN; FAIL stops the pipeline |

## Users

| Persona | Use |
|---------|-----|
| **Hermes Agent** | Consumes the skills installed in `$HERMES_SKILLS_DIR/creative/` |
| **Claude Code** | Consumes the skills installed in `~/.claude/skills/` |
| **Developer/maintainer** | Edits the skills here and runs `install.sh` |
| **CLI operator** | Triggers skills directly via `scripts/chat.py` |

## Scope

**In scope**
- Source code of the 15 `cp-*` skills (SKILL.md + `scripts/run.py` + `references/`),
  now under `skills/deprecated/`
- Shared LLM helper (`skills/deprecated/_shared/llm.py`)
- Install/propagation script (`scripts/install.sh`)
- Support tools: direct chat (`scripts/chat.py`) and OpenAI-compatible proxy
  to use Claude Code as the LLM (`scripts/claude_proxy.py`)

**Out of scope**
- Agent runtime (Hermes Agent and Claude Code are separate projects)
- The target projects where the pipeline runs (e.g. `crewbotics-back`)
- LLM hosting/infra — the repository only resolves credentials and endpoints

## Design principles

1. **Skill is self-contained** — each `run.py` embeds its own agents; it does
   not depend on an external agents directory.
2. **The orchestrator is the factory manager** — route every request to it; it
   chooses the mode, plans the phases and applies the quality gates.
3. **Explicit CLI contract** — the `invoke` metadata describes how each skill
   receives the briefing (`positional`/`goal`/`input`/`daemon`/`dir`) and whether
   it accepts `--output`. Never assume; test with `--dry-run`.
4. **Auto-detection over optional flags** — the correct mode must be detected
   from context, not depend on the LLM remembering to set a flag.
5. **Documentation in `.context/`** — never in `.hermes/` or `.claude/`.

## Decisions

- **ADR-0001** — Source of truth in `.context/` (see `.context/tracking/decisions.md`).
- **ADR-0002** — `cp-full-dev` merged into `cp-orchestrator` (native NEXUS pipeline).
- **ADR-0003** — Provider-agnostic LLM via `skills/deprecated/_shared/llm.py`.
