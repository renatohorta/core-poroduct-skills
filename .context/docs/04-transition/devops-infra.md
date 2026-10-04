# DevOps and Operations — Core Product Skills

> ⚠️ **DEPRECATED MODE** — all `cp-*` skills live in **`skills/deprecated/`** and
> are no longer installed by default (ADR-0007). "Deploy" now requires
> `./scripts/install.sh --deprecated`.

> Discipline: DevOps/Infra (`cp-devops`), Autonomous loop (`cp-goal-loop`).
> Updated 2026-10-04.

## Status

- [x] Done (current operation documented)
- ⚠️ No CI/CD — deploy is manual via `install.sh`

## "Deploy" model

There is no server: the "deploy" is the **propagation of the skills** from this
repository to the agents' skills directories.

```
skills/deprecated/  ──[ scripts/install.sh --deprecated ]──►  Hermes:  $HERMES_SKILLS_DIR/creative/<skill>/
                                                            └─►  Claude:  $CLAUDE_SKILLS_DIR/<skill>/
                                                                 (+ _shared at the skills root, in both)
```

### Commands

```bash
./scripts/install.sh                          # no-op (deprecated mode)
./scripts/install.sh --deprecated             # Hermes + Claude
./scripts/install.sh --deprecated --hermes    # only Hermes
./scripts/install.sh --deprecated --claude    # only Claude
./scripts/install.sh --deprecated --skill cp-requirements  # only one skill
./scripts/install.sh --deprecated --dry-run   # simulates, does not copy
```

### Destinations and overrides

| Env var | Default (Windows) | Default (Linux/macOS) |
|---------|-------------------|----------------------|
| `HERMES_SKILLS_DIR` | `%LOCALAPPDATA%\hermes\skills` | `~/.hermes/skills` |
| `CLAUDE_SKILLS_DIR` | `~/.claude/skills` | `~/.claude/skills` |

In Hermes the skills go to the `creative/` category; in Claude they stay flat.
`_shared` is **not** a skill — it goes to the skills root in both destinations.

### Copy semantics

`install.sh` does `rm -rf "$dst"` and re-copies: the install is **disposable** and
always reflects the repository. Never edit the installed copy — it will be lost.
After copying, `__pycache__/` and `outputs/` are removed from the destination.

## Execution environment

| Item | Situation |
|------|-----------|
| Runtime | Python 3 (host: 3.14 on Windows) |
| Main dependency | `crewai` — **not declared** in a manifest (see DT-05) |
| Interpreter used by the orchestrator | Host agent's Python (e.g. Hermes venv) |
| `install.sh` shell | bash (Git Bash on Windows) |
| Configuration | `.env` at the root (template in `.env.example`) |

### Pitfall — encoding on Windows

The Windows console uses cp1252 and breaks on the skills' UTF-8 output. Run with:

```bash
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python skills/deprecated/cp-orchestrator/scripts/run.py ...
```

Definitive fix pending: DT-01.

### Pitfall — intermittent bash relay on Windows

`terminal`/`write_file` may fail with
`execvpe(/bin/bash) failed: No such file or directory`. Work around it using pure
Python (`subprocess`/`open`) via `execute_code`. See
`skills/deprecated/cp-orchestrator/references/windows-wsl-bash-relay-workaround.md`.

## LLM configuration

Provider-agnostic resolution (`skills/deprecated/_shared/llm.py`), in this order:

1. Agent env vars: `LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE`, `LLM_TEMPERATURE`, `LLM_PROVIDER`
2. `.env` at the project root
3. Per-provider key detection (`GEMINI_API_KEY`, `OPENAI_API_KEY`, …)
4. Default: `gemini/gemini-2.5-flash`

### Claude Code as the crews' LLM

```bash
python scripts/claude_proxy.py --port 8090   # exposes /v1/chat/completions → `claude -p`
python scripts/claude_proxy.py --test        # tests a call
```

```env
LLM_MODEL=openai/claude-sonnet-4
LLM_API_BASE=http://localhost:8090/v1
LLM_API_KEY=<any value — the proxy ignores it, CrewAI requires it>
LLM_PROVIDER=openai
```

> The proxy listens on `127.0.0.1` and **has no authentication** (see SEC-02).
> `DEFAULT_PORT` in the code is 8080, but the README recommends 8090 to avoid
> conflict with frontends — pass `--port 8090` explicitly until DOC-01 is resolved.

## Observability

| Signal | Where |
|--------|-------|
| Pipeline execution log | stdout of `run.py` (phase, quality gate, time) |
| Per-phase artifacts | `skills/deprecated/cp-orchestrator/outputs/pipeline_<timestamp>/<phase>.md` |
| Structured report | `.../pipeline_<timestamp>/pipeline_report.json` |
| Project progress | `.context/tracking/progress.md` |

There are no aggregated metrics, alerts or log retention — appropriate for local use.

## Runbook

| Situation | Action |
|-----------|--------|
| Skill does not appear in Claude | Confirm `~/.claude/skills/<skill>/SKILL.md`; restart the agent |
| Skill does not appear in Hermes | Confirm `$HERMES_SKILLS_DIR/creative/<skill>/`; reloads on the next turn |
| `OPENAI_API_KEY is required` | `.env` without `LLM_*` — configure the correct provider |
| `UnicodeEncodeError` | Run with `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` |
| Phase failed in `--auto` | Fix and resume with `--start-phase <phase>` |
| `Permission denied` on install | `chmod +x scripts/install.sh` (Linux/macOS) |
| Change "without effect" | Check which clone of the repo the process is running from |

## Pending items

- **DT-05** — No dependency manifest: create `requirements.txt` pinning
  `crewai` (and relevant transitives).
- **DT-06** — No CI: add a workflow that runs `install.sh --dry-run` + smoke
  tests on every push.
- **DT-01** — Fix UTF-8 encoding in the orchestrator's output (Windows).

## Decisions

- Distribution by directory copy (not an installable package): keeps the
  edit→propagate cycle in one command and without a build.
