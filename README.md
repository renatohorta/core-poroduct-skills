# Core Product Skills

Central repository for the **Software Factory** skills (CrewAI). This is the
**canonical source code** of the `cp-*` skills — from here you install/update
the skills in both the **Hermes Agent** and **Claude Code**.

## What it is

This repository contains the base code (SKILL.md + scripts + references) of the
`cp-*` skills of the Software Factory. It serves as the **single source of
truth**: any change is made here and then propagated to the agents (Hermes and
Claude) via the install script.

## Included skills

Complete development pipeline orchestrated by crews of CrewAI agents.

| Skill | Function |
|-------|----------|
| `cp-orchestrator` | **Factory manager** — coordinates all crews in sequence, manages artifacts and applies quality gates. Includes the native NEXUS pipeline (merge of `cp-full-dev`). |
| `cp-requirements` | Requirements Engineering (Business Analyst, Specifier, Validator, PO Proxy) |
| `cp-architecture` | Architecture and Design (Software, Data, API, UX Architect, Reviewer) |
| `cp-implementation` | Implementation (Backend, Frontend, Mobile Dev, Reviewer, Integrator) |
| `cp-testing` | Testing (Unit, Integration, E2E, Performance, Analyst) |
| `cp-security` | Security (Analyst, Pentester, Compliance, Fix Engineer) |
| `cp-devops` | DevOps and Infra (CI/CD, Infra, Monitoring, Infra Security) |
| `cp-software-spec` | Software Spec & Knowledge Base — unifies initialization, reverse engineering and card refinement (Backlog → ToDo) in a concise RUP model (`.context/`) |
| `cp-quality` | Quality (Auditor, Metrics, Continuous Improvement, Validator) |
| `cp-bug-fix` | Bug fixing (Developer → QA → Evidence Collector, max. 3 retries) |
| `cp-competitive-analysis` | Competitive intelligence (Market, Competitors, Pricing, Strategist) |
| `cp-goal-loop` | Autonomous try-and-correct loop until success is reached |
| `cp-maintenance` | Maintenance and evolution (bug-fix, refactor, improvement, full) |
| `cp-agile` | Execution pipeline — monitors backlog, dispatches tasks and manages bidirectional feedback (questions, blockers, resume) |

## Repository structure
```
core-poroduct-skills/
├── README.md                 # This file
├── requirements.txt          # Runtime dependencies (crewai)
├── requirements-dev.txt      # + pytest
├── pytest.ini
├── .github/workflows/ci.yml  # CI
├── tests/                    # Suite (does not use LLM credentials)
├── docs/
│   ├── INSTALLATION.md       # How to install/update in Hermes and Claude
│   ├── ARCHITECTURE.md       # Software Factory architecture
│   └── SKILLS.md             # Detailed catalog of each skill
├── scripts/
│   └── install.sh            # Installs/updates the skills in the agents
└── skills/
    ├── cp-orchestrator/
    │   ├── SKILL.md
    │   ├── scripts/run.py
    │   └── references/*.md
    ├── cp-requirements/
    ├── ... (all cp-* skills)
    └── cp-testing/
```

## Quick install

```bash
# Installs/updates all skills in Hermes and Claude
./scripts/install.sh

# Only in Hermes
./scripts/install.sh --hermes

# Only in Claude
./scripts/install.sh --claude

# Only one specific skill
./scripts/install.sh --skill cp-requirements
```

See [docs/INSTALLATION.md](docs/INSTALLATION.md) for details.

## Development and testing

```bash
# Environment (uv is much faster than pip for the ~135 crewai transitive deps)
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements-dev.txt

# Full suite — needs no LLM credentials
.venv/Scripts/python.exe -m pytest        # Windows
.venv/bin/python -m pytest                # Linux/macOS
```

The suite (158 tests) **never calls an LLM**: testing the model is expensive,
slow and non-deterministic, and does not catch the bugs that actually occur
here — which are about CLI contract and error handling.

| File | What it guarantees |
|------|--------------------|
| `tests/test_smoke.py` | `--help` works in every skill (even without `crewai`); `--dry-run` runs without credentials; missing LLM/lib exits with code and actionable message |
| `tests/test_contrato_invoke.py` | The orchestrator's `invoke` metadata matches the real `argparse` — including running the command line the orchestrator would build |
| `tests/test_quality_gate.py` | The quality gate fails on exit code and does not approve by substring |
| `tests/test_claude_proxy_auth.py` | Proxy authentication and bind restricted to localhost |
| `tests/test_higiene.py` | No committed secrets, no machine paths in code |

CI in `.github/workflows/ci.yml`: runs the suite on Python 3.12 and 3.13 on
Linux (blocking) and Windows (informative), plus `install.sh --dry-run`.

### Skill exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Usage error (missing briefing, invalid argument) |
| 2 | No LLM configured |
| 3 | `crewai` not installed |

`--help` always works, and `--dry-run` inspects the crew without credentials.

## Portability

The skills are **portable** — they contain no hardcoded OS/machine paths or
fixed personal values. Project paths use env vars + relative defaults.

## Skill LLM (provider-agnostic)

The CrewAI skills use the **LLM of the agent where they are being called**
(Hermes/Claude), with a fallback to a local `.env`. The `skills/_shared/llm.py`
helper resolves the LLM in this order:

1. Agent env vars (`LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE`, `LLM_PROVIDER`)
2. `.env` at the project root (same convention as crewbotics-back)
3. Per-provider key detection (`GEMINI_API_KEY`, `OPENAI_API_KEY`, etc.)
4. Default: `gemini/gemini-2.5-flash`

This prevents the skills from falling into the CrewAI OpenAI default
(`OPENAI_API_KEY is required`) even with another provider configured.

## Direct conversation with the skills (scripts/chat.py)

The `scripts/chat.py` lets you trigger any cp-* skill interactively, using the
`.env` LLM (without depending on the agent):

```bash
python scripts/chat.py --list                          # lists the skills
python scripts/chat.py cp-requirements "scheduling system"
python scripts/chat.py cp-requirements "briefing" --dry-run
```

The script automatically detects the Python with `crewai` installed (project
`.venv`) and loads the `.env`.

## Use Claude Code as the LLM of the crews (scripts/claude_proxy.py)

The CrewAI crews can use **Claude Code as LLM** (via OAuth, without needing
`ANTHROPIC_API_KEY`). The `scripts/claude_proxy.py` exposes an OpenAI-compatible
API that delegates each call to the `claude -p` command:

```bash
# 1. Starts the proxy (port 8090, avoids conflict with frontends on 8080)
python scripts/claude_proxy.py --port 8090

# 2. Tests a call
python scripts/claude_proxy.py --test
```

Then configure the skills' `.env` to point to the proxy:

```env
LLM_MODEL=openai/claude-sonnet-4
LLM_API_BASE=http://localhost:8090/v1
LLM_API_KEY=***   # the proxy ignores it, but CrewAI requires it
LLM_PROVIDER=openai
```

> **Note:** the proxy uses Claude Code's default model (it does not pass
> `--model` for generic models). To choose a specific model, set `CLAUDE_MODEL`
> in the environment (e.g. `claude-opus-4`).

## License

Internal use. © Renato Sacramento Horta.
