# Architecture — Core Product Skills

> Updated 2026-11-03 (RUP family, flat `skills/` layout — ADR-0010).

## Status

- [x] Done (current architecture documented)

## Layered view

```
┌──────────────────────────────────────────────────────────────┐
│ CONSUMERS (outside this repo)                                │
│   Hermes Agent                    Claude Code                │
│   $HERMES_SKILLS_DIR/creative/    ~/.claude/skills/          │
│   (+ $HERMES_SKILLS_DIR/_shared)  (+ ~/.claude/skills/_shared)│
└───────────────▲──────────────────────▲───────────────────────┘
                │  scripts/install.sh (propagation)
┌───────────────┴──────────────────────┴───────────────────────┐
│ CANONICAL REPOSITORY (this repo)                             │
│                                                              │
│  skills/rup-orchestrator   ← single entry point (PM agent)   │
│      └── scripts/run.py  governance crew + UCP tool + dispatcher
│                │ subprocess: run.py <briefing|--input ctx> --phase P [--output F]
│      ┌─────────┴───────────────────────────────────┐         │
│      ▼                                             ▼         │
│  rup-environment → rup-business-modeling → rup-requirements → │
│  rup-analysis-design → rup-implementation → rup-test →        │
│  rup-ccm → rup-deployment          (order used by --auto)     │
│                                                              │
│  skills/_shared/llm.py    ← provider-agnostic LLM resolution │
│  scripts/chat.py          ← direct trigger (CLI)             │
│  scripts/claude_proxy.py  ← Claude Code as LLM (OpenAI API)  │
└──────────────────────────────────────────────────────────────┘
```

## Components

| Component | Path | Responsibility |
|-----------|------|----------------|
| **Orchestrator** | `skills/rup-orchestrator/scripts/run.py` | Governance crew (PM), UCP calculator (CLI + agent tool), dispatcher (`--discipline`, `--auto`) |
| **Discipline skills** | `skills/rup-{environment,business-modeling,requirements,analysis-design,implementation,test,ccm,deployment}/` | One RUP discipline each, with its own CrewAI crew |
| **LLM helper** | `skills/_shared/llm.py` | `build_crew_llm()`, `require_llm()`, `require_crewai()`, `setup_console()` |
| **Installer** | `scripts/install.sh` | Propagates every `skills/*/SKILL.md` dir + `_shared` to Hermes and Claude |
| **Direct chat** | `scripts/chat.py` | Runs any `rup-*` skill with the `.env` LLM |
| **Claude proxy** | `scripts/claude_proxy.py` | OpenAI-compatible API delegating to `claude -p` |

## Anatomy of a skill

```
skills/rup-<name>/
├── SKILL.md          # frontmatter (name, description/triggers) + documentation
├── scripts/run.py    # self-contained: CrewAI agents + CLI (argparse)
└── references/*.md   # agents.md (agent → artifacts); orchestrator: lifecycle, sizing
```

Each `run.py` locates `_shared/` next to the skill (repo, Claude) or one level
up (Hermes category layout) and inserts that root in `sys.path`. `crewai` is
imported guarded, so `--help` and `--dry-run` work without it.

## Data flow in `--auto`

```
briefing ─► ctx_01 = briefing ───────────────► rup-environment --input ctx_01 --output A1
            ctx_02 = briefing + A1 ──────────► rup-business-modeling --input ctx_02 --output A2
            ctx_03 = briefing + A1 + A2 ─────► rup-requirements ...
            ...                                (each prior artifact capped at 12 000 chars)
            stop at the first exit code != 0
```

`A<n>` is `<output-stem>.NN-<key>.md` next to `--output`, or a file in a
temporary workdir when `--output` is omitted (the crews also print their result
to stdout). The context files always live in the temporary workdir.

## Software sizing

`compute_ucp` (pure Python) is validated by `ucp_from_model` and exposed:
- on the CLI: `--estimate [--sizing F] [--json]`, `--sizing-template`;
- to the governance agent as the CrewAI tool `use_case_points_calculator` —
  the task tells the agent to call it instead of doing the arithmetic.

## LLM resolution (`_shared/llm.py`)

1. Agent env vars — `LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE`, `LLM_TEMPERATURE`, `LLM_PROVIDER`
2. `.env` at the project root
3. Per-provider key detection (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, …)
4. Default: `gemini/gemini-2.5-flash`

## Architectural decisions

- **ADR-0003** — LLM resolved by `_shared/llm.py` instead of the CrewAI default.
- **ADR-0004** — Communication between skills via `subprocess` + files, not
  Python import: each skill stays self-contained and independently installable.
- **ADR-0005** — `install.sh` does `rm -rf` on the destination before copying.
- **ADR-0008** — RUP family: orchestrator + 8 discipline skills.
- **ADR-0009** — UCP computed deterministically in the orchestrator.
- **ADR-0010** — `cp-*` removed, `rup-*` flattened into `skills/`, `--auto`
  chaining and the UCP agent tool.

Full record: `.context/tracking/decisions.md`.
