---
name: rup-requirements
description: "RUP Requirements Discipline (3/9). This skill covers the RUP **Requirements Discipline**: eliciting, specifying and validating the system's requirements (Vision → SRS). Use when the user says 'gather requirements, vision document, use cases, SRS, FURPS, glossary' or needs the RUP requirements artifacts."
---

# rup-requirements — RUP Requirements Discipline

This skill covers the RUP **Requirements Discipline**: eliciting, specifying and validating the system's requirements (Vision → SRS).

Grounded in *The Rational Unified Process: An Introduction* (3rd ed.), Philippe
Kruchten. Part of the `rup` family — drive the whole lifecycle through
`rup-orchestrator`, or run this discipline directly.

## Agents (2)

| Agent (slug) | Role | Artifacts |
|--------------|------|-----------|
| `system-analyst` | System Analyst | Stakeholder Requests, Vision Document, Use-Case Model Survey, System Actors, Glossary, Requirements Management Plan |
| `requirements-specifier` | Requirements Specifier | Use Cases, Use-Case Packages, Supplementary Specifications (FURPS), Software Requirements Specification (SRS), Requirements Attributes |

## Phase focus

Inception → Elaboration

## How to run this skill — you are the LLM

This skill does not call any model: **you, the agent running it, produce the
artifacts**. The script gives you the work packet and records your result.

1. **Get the work packet** (read-only):

   ```bash
   python scripts/run.py "<briefing>" --phase <Inception|Elaboration|Construction|Transition>
   python scripts/run.py --input briefing.md --phase Elaboration     # long briefings
   ```

   It prints the RUP roles of this discipline (goal, perspective, mission), the
   **exact list of artifacts** you must write, the briefing, and the artifacts
   already recorded in `.context/` that this discipline builds on (governance +
   the earlier disciplines of the same phase).

2. **Write ONE markdown document**: a `# <Role>` per role, and a level-2
   heading `## <Artifact>` for every artifact listed. Follow the RUP conventions,
   reuse names/IDs from the earlier artifacts, state assumptions explicitly.

3. **Record it — mandatory** (the packet prints the exact command):

   ```bash
   python scripts/run.py --record doc.md --phase Elaboration "<briefing>"
   cat doc.md | python scripts/run.py --record - --phase Elaboration --input briefing.md
   ```

   The recorder checks that every required `## <Artifact>` section exists (if not,
   it lists the missing ones, writes nothing and exits `1` — add them and record
   again) and writes `.context/docs/<NN-phase>/rup-requirements.md` with a provenance header,
   plus a row in `.context/tracking/rup-log.md`.

## CLI contract

| Argument | Meaning |
|----------|---------|
| `briefing` (positional) | Business demand / context for the discipline |
| `--input <file>` | Read the briefing from a file (alternative to positional) |
| `--phase {Inception,Elaboration,Construction,Transition}` | RUP phase (default: Elaboration) |
| `--context-dir <dir>` | The `.context/` (default: `$RUP_CONTEXT_DIR`, else the nearest up to the git root) |
| `--record <file\|->` | Validate your document and write it to `.context/` |

Exit codes: `0` success · `1` usage error / missing artifacts · `4` `.context/`
not writable. Standard library only — no LLM key, no `crewai`.

## Reference

Agent → artifact mapping and missions: `references/agents.md`.
