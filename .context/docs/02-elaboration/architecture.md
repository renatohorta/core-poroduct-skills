# Architecture — Core Product Skills

> Discipline: Architecture and Design (`cp-architecture`). Updated 2026-08-18.

## Status

- [x] Done (current architecture documented)

## Layered view

```
┌──────────────────────────────────────────────────────────────┐
│ CONSUMERS (outside this repo)                               │
│   Hermes Agent            Claude Code                        │
│   $HERMES_SKILLS_DIR/creative/   ~/.claude/skills/           │
└───────────────▲──────────────────────▲───────────────────────┘
                │  scripts/install.sh (propagation)
┌───────────────┴──────────────────────┴───────────────────────┐
│ CANONICAL REPOSITORY (this repo)                             │
│                                                              │
│  skills/cp-orchestrator   ← single entry point               │
│      └── scripts/run.py   (4 agents + NexusExecutor)        │
│                │ subprocess (CLI `invoke` contract)          │
│      ┌─────────┴─────────────────────────────────┐           │
│      ▼                                           ▼           │
│  Pipeline (8 skills)                  Complementary (6)     │
│   cp-requirements                        cp-bug-fix            │
│   cp-architecture                       cp-competitive-analysis│
│   cp-implementation                     cp-goal-loop          │
│   cp-testing                            cp-maintenance         │
│   cp-security                         cp-agile           │
│   cp-devops                            cp-doc-initializer  │
│   cp-documentation                                            │
│   cp-quality                                               │
│                                                              │
│  skills/_shared/llm.py    ← provider-agnostic resolution      │
│  scripts/chat.py          ← direct trigger (CLI)             │
│  scripts/claude_proxy.py  ← Claude Code as LLM (OpenAI API)│
└──────────────────────────────────────────────────────────────┘
                                │ writes artifacts
                                ▼
                    .context/ of the TARGET PROJECT
```

## Components

| Component | Path | Responsibility |
|-----------|------|----------------|
| **Orchestrator** | `skills/cp-orchestrator/scripts/run.py` | Coordinates crews, manages artifacts, applies quality gates, runs native NEXUS |
| **Pipeline skills** | `skills/cp-{requirements,architecture,implementation,testing,security,devops,documentation,quality}/` | One engineering discipline each, with its own CrewAI crew |
| **Complementary skills** | `skills/cp-{bug-fix,competitive-analysis,goal-loop,maintenance,agile,doc-initializer}/` | Flows outside the linear pipeline |
| **LLM helper** | `skills/_shared/llm.py` | `build_crew_llm()` / `get_llm_config()` — resolves model/key/base |
| **Installer** | `scripts/install.sh` | Propagates `skills/` to Hermes and Claude |
| **Direct chat** | `scripts/chat.py` | Triggers any skill interactively using the `.env` |
| **Claude proxy** | `scripts/claude_proxy.py` | OpenAI-compatible API delegating to `claude -p` |

## Anatomy of a skill

```
skills/cp-<name>/
├── SKILL.md          # frontmatter (name, description/triggers) + documentation
├── scripts/run.py    # self-contained: CrewAI agents + CLI (argparse)
└── references/*.md   # durable knowledge (pitfalls, inventories, procedures)
```

Each `run.py` is **self-contained**: the agents are embedded in the Python
itself, with no dependency on an external agents directory.

## Trigger contract (`invoke` metadata)

The orchestrator calls each skill via `subprocess`. The contract is declared in
the `CREWS` dict of `cp-orchestrator/scripts/run.py`:

| `briefing_arg` | How the briefing is passed | Example skill |
|----------------|---------------------------|---------------|
| `positional` | positional argument | `cp-bug-fix`, `cp-competitive-analysis` |
| `goal` | `--goal <briefing>` | `cp-goal-loop` |
| `input` | positional in the 1st phase; `--input <ctx>` in the following | pipeline phases |
| `daemon` | no briefing — builds `--daemon` | `cp-agile` |
| `dir` | no briefing — builds `--dir <cwd>` | `cp-doc-initializer` |

`invoke.output` indicates whether the skill accepts `--output`. **Do not assume**
— `cp-bug-fix`, `cp-goal-loop` and `cp-agile` **reject** `--output`. See
`skills/cp-orchestrator/references/skills-cli-inventory.md`.

## Data flow between phases

```
briefing ─► cp-requirements ─► requirements.md
                                │  (_ctx_<phase>.txt: briefing + previous artifact[:3000])
                                ▼
                          cp-architecture --input _ctx_architecture.txt ─► architecture.md
                                ▼
                          ... until delivery
```

Artifacts go to `cp-orchestrator/outputs/pipeline_<timestamp>/`, with
`pipeline_report.json` at the end. The consolidated documentation goes to
`.context/docs/` of the target project.

## Orchestrator modes

| Mode | Phases |
|------|--------|
| `full` | requirements → architecture → implementation → testing → security → devops → documentation → quality |
| `sprint` | requirements → architecture → implementation → testing → devops |
| `micro` | implementation → testing |
| `security-audit` | security → quality |
| `documentation` | documentation → quality |
| `bugfix` / `competitive` / `full-dev` / `goal-loop` / `maintenance` / `agile` / `doc-initializer` | single skill |

## LLM resolution (`_shared/llm.py`)

Order, provider-agnostic:

1. Agent env vars — `LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE`, `LLM_TEMPERATURE`, `LLM_PROVIDER`
2. `.env` at the project root
3. Per-provider key detection (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, …)
4. Default: `gemini/gemini-2.5-flash`

Mapped providers: gemini/google, openai, anthropic/claude, ollama, openrouter,
deepseek, groq, mistral, cohere, together, xai/grok.

## Architectural decisions

- **ADR-0002** — `cp-full-dev` merged into the orchestrator; NEXUS runs in memory
  via `NexusExecutor`, eliminating a subprocess hop and the separate skill.
- **ADR-0003** — LLM resolved by the `_shared/llm.py` helper instead of the
  CrewAI default, avoiding `OPENAI_API_KEY is required` with another provider active.
- **ADR-0004** — Communication between skills via `subprocess` + files, not
  Python import: keeps each skill self-contained and independently installable.
- **ADR-0005** — `install.sh` does `rm -rf` on the destination before copying:
  the installed copy is disposable and always reflects the repository.

Full record: `.context/tracking/decisions.md`.
