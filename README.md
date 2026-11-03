# Core Product Skills

Central repository for the **skills** propagated to the **Hermes Agent** and
**Claude Code** — the **single source of truth**: any change is made here and then
propagated to the agents via `scripts/install.sh`.

The skills implement the **Rational Unified Process (RUP)** as an autonomous team
of CrewAI agents, grounded in *The Rational Unified Process: An Introduction*
(3rd ed.), Philippe Kruchten.

> The legacy Software Factory family (`cp-*`) was removed from the repository
> (ADR-0010). It is still available in the git history (up to commit `6490694`).

## The RUP skills (`skills/rup-*`)

The user interacts exclusively with `rup-orchestrator`, which governs the
lifecycle (Inception → Elaboration → Construction → Transition) and dispatches
the 8 discipline skills — **9 RUP disciplines, 21 agents**.

| Skill | Discipline | Agents |
|-------|------------|--------|
| `rup-orchestrator` | Project Management (governance) | 1 |
| `rup-environment` | Environment | 1 |
| `rup-business-modeling` | Business Modeling | 2 |
| `rup-requirements` | Requirements | 2 |
| `rup-analysis-design` | Analysis & Design | 5 |
| `rup-implementation` | Implementation | 2 |
| `rup-test` | Test | 4 |
| `rup-ccm` | Configuration & Change Management | 2 |
| `rup-deployment` | Deployment | 2 |

Full details: [`skills/README.md`](skills/README.md) and
[`docs/SKILLS.md`](docs/SKILLS.md).

## Repository structure

```
core-poroduct-skills/
├── README.md                 # This file
├── CLAUDE.md / AGENT.md      # Context for coding agents working on this repo
├── requirements.txt          # Runtime dependencies (crewai)
├── requirements-dev.txt      # + pytest
├── pytest.ini
├── .github/workflows/ci.yml  # CI
├── .context/                 # Operational context (source of truth for agents)
├── tests/                    # Suite (does not use LLM credentials)
├── docs/
│   ├── INSTALLATION.md       # How to install/update in Hermes and Claude
│   ├── ARCHITECTURE.md       # Architecture of the skills
│   └── SKILLS.md             # Detailed catalog of each skill
├── scripts/
│   ├── install.sh            # Installs/updates the skills in the agents
│   ├── chat.py               # Runs a skill directly with the .env LLM
│   └── claude_proxy.py       # OpenAI-compatible proxy backed by `claude -p`
└── skills/
    ├── README.md             # Family overview
    ├── _shared/llm.py        # shared LLM helper (not a skill)
    ├── rup-orchestrator/     # governance + dispatcher
    │   ├── SKILL.md
    │   ├── scripts/run.py
    │   └── references/       # lifecycle.md, sizing-estimation.md
    └── rup-<discipline>/     # 8 discipline skills (environment … deployment)
        ├── SKILL.md
        ├── scripts/run.py
        └── references/agents.md
```

## Quick install

```bash
# Installs/updates every skill in Hermes and Claude
./scripts/install.sh

# Only in Hermes / only in Claude
./scripts/install.sh --hermes
./scripts/install.sh --claude

# One specific skill
./scripts/install.sh --skill rup-requirements

# Simulation (shows what it would do, without copying)
./scripts/install.sh --dry-run
```

See [docs/INSTALLATION.md](docs/INSTALLATION.md) for details.

## Using the orchestrator

```bash
cd skills/rup-orchestrator
python scripts/run.py "clinics scheduling SaaS" --phase Inception        # governance
python scripts/run.py "briefing" --discipline requirements               # one discipline
python scripts/run.py "briefing" --auto --output out/iteration.md        # all, chained
python scripts/run.py --estimate --sizing sizing.json                    # UCP, no LLM
```

`--auto` runs the 8 disciplines in order and **chains** them: each discipline
receives the briefing plus the artifacts of the previous ones. With `--output
out/iteration.md` each discipline writes its own file (`out/iteration.01-environment.md`
… `out/iteration.08-deployment.md`). It stops at the first failing discipline.

## Development and testing

```bash
# Environment (uv is much faster than pip for the ~135 crewai transitive deps)
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements-dev.txt

# Full suite — needs no LLM credentials
.venv/Scripts/python.exe -m pytest        # Windows
.venv/bin/python -m pytest                # Linux/macOS
```

The suite **never calls an LLM**: testing the model is expensive, slow and
non-deterministic, and does not catch the bugs that actually occur here — which
are about CLI contract and error handling.

| File | What it guarantees |
|------|--------------------|
| `tests/test_smoke.py` | Every skill: `--help`/`--dry-run` without credentials (and without crewai), exit codes 1/2/3; orchestrator registry == discipline skills; `--auto` chaining, per-discipline output and stop-on-failure; UCP calculator, validation and agent tool; `install.sh` plan and installed copies running in the Claude and Hermes layouts |
| `tests/test_claude_proxy_auth.py` | Proxy authentication and bind restricted to localhost |
| `tests/test_higiene.py` | No committed secrets, no machine paths in code |

CI in `.github/workflows/ci.yml`: runs the suite on Python 3.12 and 3.13 on
Linux (blocking) and Windows (informative), plus `install.sh --dry-run`, on
pushes to `main` and on pull requests.

### Skill exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Usage error (missing briefing, unreadable `--input`, invalid sizing model) |
| 2 | No LLM configured |
| 3 | `crewai` not installed |

`--help` always works, and `--dry-run` shows the plan without credentials (and
without crewai, in which case the crew itself is not built).

## Portability

The skills are **portable** — they contain no hardcoded OS/machine paths or
fixed personal values. Each `run.py` finds `_shared/` either next to the skill
(repository, Claude Code) or one level up (Hermes, which nests skills in a
category directory).

## Skill LLM (provider-agnostic)

The CrewAI skills use the **LLM of the agent where they are being called**
(Hermes/Claude), with a fallback to a local `.env`. The `skills/_shared/llm.py`
helper resolves the LLM in this order:

1. Agent env vars (`LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE`, `LLM_PROVIDER`)
2. `.env` at the project root
3. Per-provider key detection (`GEMINI_API_KEY`, `OPENAI_API_KEY`, etc.)
4. Default: `gemini/gemini-2.5-flash`

This prevents the skills from falling into the CrewAI OpenAI default
(`OPENAI_API_KEY is required`) even with another provider configured.

## Direct conversation with the skills (scripts/chat.py)

`scripts/chat.py` runs any `rup-*` skill directly, using the `.env` LLM (without
depending on the agent). Unknown flags are forwarded to the skill:

```bash
python scripts/chat.py --list
python scripts/chat.py rup-requirements "scheduling system"
python scripts/chat.py rup-orchestrator "briefing" --phase Inception --dry-run
```

It picks the Python with `crewai` (`RUP_SKILLS_PYTHON`, else the project
`.venv`/`venv`) and loads the `.env`.

## Use Claude Code as the LLM of the crews (scripts/claude_proxy.py)

The CrewAI crews can use **Claude Code as LLM** (via OAuth, without needing
`ANTHROPIC_API_KEY`). `scripts/claude_proxy.py` exposes an OpenAI-compatible
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
