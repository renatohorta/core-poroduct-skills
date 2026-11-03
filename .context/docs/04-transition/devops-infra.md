# DevOps and Operations — Core Product Skills

> Updated 2026-11-03 (RUP family, flat `skills/` layout — ADR-0010).

## Status

- [x] Done (current operation documented)
- CI on GitHub Actions (tests); deploy is manual via `install.sh`

## "Deploy" model

There is no server: the "deploy" is the **propagation of the skills** from this
repository to the agents' skills directories.

```
skills/rup-*/  ──[ scripts/install.sh ]──►  Hermes:  $HERMES_SKILLS_DIR/creative/<skill>/
                                                            └─►  Claude:  $CLAUDE_SKILLS_DIR/<skill>/
                                                                 (+ _shared at the skills root, in both)
```

### Commands

```bash
./scripts/install.sh                          # Hermes + Claude
./scripts/install.sh --hermes                 # only Hermes
./scripts/install.sh --claude                 # only Claude
./scripts/install.sh --skill rup-requirements # only one skill
./scripts/install.sh --dry-run                # simulates, does not copy
```

### Destinations and overrides

| Env var | Default (Windows) | Default (Linux/macOS) |
|---------|-------------------|----------------------|
| `HERMES_SKILLS_DIR` | `%LOCALAPPDATA%\hermes\skills` | `~/.hermes/skills` |
| `CLAUDE_SKILLS_DIR` | `~/.claude/skills` | `~/.claude/skills` |

In Hermes the skills go to the `creative/` category; in Claude they stay flat.
`_shared` is **not** a skill — it goes to the skills root in both destinations;
each `run.py` looks for it next to the skill and one level up. Only directories
with a `SKILL.md` are installed.

### Copy semantics

`install.sh` does `rm -rf "$dst"` and re-copies: the install is **disposable** and
always reflects the repository. Never edit the installed copy — it will be lost.
After copying, `__pycache__/` and `outputs/` are removed from the destination.

## Execution environment

| Item | Situation |
|------|-----------|
| Runtime | Python 3.11–3.13 recommended (3.12 in CI) |
| Main dependency | `crewai>=1.15,<2` (`requirements.txt`) |
| Interpreter used by the orchestrator | `RUP_SKILLS_PYTHON`, else the current one |
| `install.sh` shell | bash (Git Bash on Windows) |
| Configuration | `.env` at the root (template in `.env.example`) |

### Pitfall — encoding on Windows

The Windows console uses cp1252. The skills call `setup_console()` (DT-01,
fixed) to force UTF-8; for other scripts, set `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`.

### Pitfall — intermittent bash relay on Windows

`terminal`/`write_file` may fail with
`execvpe(/bin/bash) failed: No such file or directory` (WSL relay). Use Git Bash
explicitly (`"C:\Program Files\Git\bin\bash.exe" scripts/install.sh`) or pure
Python (`subprocess`/`open`).

## LLM configuration

Provider-agnostic resolution (`skills/_shared/llm.py`), in this order:

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

> The proxy listens on `127.0.0.1` (default port 8090). Set `CLAUDE_PROXY_TOKEN`
> to require a bearer token (SEC-02).

## Observability

| Signal | Where |
|--------|-------|
| Execution log | stdout of `run.py` (phase, dispatched command, crew output) |
| Artifacts | `--output` file; in `--auto`, `<stem>.NN-<key>.md` per discipline |
| Project progress | `.context/tracking/progress.md` |

There are no aggregated metrics, alerts or log retention — appropriate for local use.

## Runbook

| Situation | Action |
|-----------|--------|
| Skill does not appear in Claude | Confirm `~/.claude/skills/<skill>/SKILL.md`; restart the agent |
| Skill does not appear in Hermes | Confirm `$HERMES_SKILLS_DIR/creative/<skill>/`; reloads on the next turn |
| `OPENAI_API_KEY is required` | `.env` without `LLM_*` — configure the correct provider |
| `UnicodeEncodeError` | Run with `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` |
| `ModuleNotFoundError: _shared` | `_shared/` missing in the agent — rerun the full `install.sh` |
| A discipline failed in `--auto` | `--auto` stops there; fix and run the remaining ones with `--discipline <key>` (pass the earlier artifacts via the briefing/`--input`) |
| `Permission denied` on install | `chmod +x scripts/install.sh` (Linux/macOS) |
| Change "without effect" | Check which clone of the repo the process is running from |

## Pending items

- None for operations. Product items in `.context/inbox/`.

## Decisions

- Distribution by directory copy (not an installable package): keeps the
  edit→propagate cycle in one command and without a build.
