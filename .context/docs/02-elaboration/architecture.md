# Architecture — Core Product Skills

> Updated 2026-11-03 (host-LLM model — ADR-0012).

## Status

- [x] Done (current architecture documented)

## Principle

**The agent running a skill is the LLM.** The skills never call a model: they
are deterministic, standard-library scripts that (1) compile a *work packet* for
the agent and (2) validate and record the agent's document into the project's
`.context/` (mandatory, ADR-0011). Same model, same conversation context, no API
key, proxy or extra dependency.

## Layered view

```
┌──────────────────────────────────────────────────────────────┐
│ HOST AGENT = the LLM (outside this repo)                     │
│   Claude Code: ~/.claude/skills/       Hermes: <skills>/creative/
└──────┬─────────────────────────────────────────▲─────────────┘
       │ 1. run.py "<briefing>" --phase P         │ packet (stdout)
       │ 3. run.py --record doc.md --phase P      │ ok / missing artifacts
┌──────▼─────────────────────────────────────────┴─────────────┐
│ SKILLS (this repo, installed by scripts/install.sh)          │
│  rup-orchestrator   governance packet · --discipline · --auto │
│                     --status · --estimate (UCP)               │
│  rup-<discipline>×8 SPEC (roles, missions, artifacts as data) │
│  _shared/discipline.py  packet rendering + --record validation│
│  _shared/context.py     .context/ resolution + writing        │
│  _shared/rup.py         phases, ordered disciplines, exits    │
└──────────────────────────────┬───────────────────────────────┘
                               │ writes
                               ▼
        <project>/.context/docs/<NN-phase>/rup-<skill>.md
        <project>/.context/tracking/rup-log.md
```

## Components

| Component | Path | Responsibility |
|-----------|------|----------------|
| **Registry** | `skills/_shared/rup.py` | Phases, ordered `DISCIPLINES`, exit codes, `setup_console()` |
| **Engine** | `skills/_shared/discipline.py` | `render_packet()`, `prior_artifacts()`, `missing_artifacts()`, `record()`, shared CLI |
| **Context helper** | `skills/_shared/context.py` | `resolve_context_dir()`, `ensure_writable()`, `write_artifact()`, log |
| **Discipline skills** | `skills/rup-<discipline>/scripts/run.py` | `SPEC` (roles, missions, artifacts) + `discipline.main()` |
| **Orchestrator** | `skills/rup-orchestrator/scripts/run.py` | Governance spec, `--discipline`, `--auto` protocol, `--status`, UCP |
| **Installer** | `scripts/install.sh` | Copies every `skills/*/SKILL.md` dir + `_shared` to Hermes and Claude |

## The protocol

1. **Packet** — `run.py "<briefing>" [--input F] --phase P [--context-dir D]`
   prints: instructions (one document, `# <Role>`, `## <Artifact>`, RUP rules,
   the exact `--record` command), the briefing, the earlier artifacts from
   `.context/`, and each role's goal/perspective/mission/artifacts. Read-only.
2. **Document** — the host writes it.
3. **Record** — `run.py --record FILE|- --phase P ["<briefing>"|--input F]`:
   every required artifact must have a level-2 heading containing its name
   (case, punctuation and parenthesised qualifiers ignored); otherwise it lists
   the missing ones, writes nothing and exits 1. Then `.context/` is written.

## Chaining

`prior_artifacts()` embeds, from `.context/docs/<NN-phase>/`: for a discipline,
the governance artifact + the disciplines **before** it in RUP order; for
governance, every discipline of the phase. Bodies only (after `## Artifacts`),
each capped at 12 000 chars. Doing the steps in order therefore gives each one
the output of the previous ones; `--auto` prints that order with the commands
and `--status` the progress.

`--discipline <key>` runs the discipline's skill in a subprocess (ADR-0004) with
an explicit `--context-dir` (the child's cwd is the skills root, so it must not
resolve `.context/` itself).

## Artifacts in `.context/` (mandatory — ADR-0011)

- `.context/docs/<NN-phase>/rup-<skill>.md` (+ `rup-orchestrator-sizing.md` from
  `--estimate`), with provenance frontmatter; regenerated per run; curated docs
  never touched.
- `.context/tracking/rup-log.md`: one row per write.
- Resolution: `--context-dir` > `RUP_CONTEXT_DIR` > nearest `.context/` up to the
  git root > `<git root or cwd>/.context`. Unwritable → exit 4.

## Software sizing

`compute_ucp` + `ucp_from_model` (validation) behind `--estimate`. The governance
packet carries the exact `--sizing-template` / `--estimate` commands and forbids
computing UCP by hand; FPA and COCOMO II are the host's estimates.

## Architectural decisions

- **ADR-0004** — Skills talk via `subprocess` + files, not Python import.
- **ADR-0005** — `install.sh` does `rm -rf` on the destination before copying.
- **ADR-0008** — RUP family: orchestrator + 8 discipline skills.
- **ADR-0009** — UCP computed deterministically in the orchestrator.
- **ADR-0010** — `cp-*` removed, `rup-*` flattened into `skills/`.
- **ADR-0011** — Artifacts always persisted into `.context/`.
- **ADR-0012** — The host agent is the LLM; CrewAI, `llm.py`, proxy, chat removed.

Full record: `.context/tracking/decisions.md`.
