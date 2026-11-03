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
| Runtime | Python 3.10+ (3.12 in CI) |
| Runtime dependencies | **None** — standard library only (ADR-0012) |
| The LLM | The agent running the skill (Claude Code, Hermes) — no key, no endpoint |
| `install.sh` shell | bash (Git Bash on Windows) |
| Configuration | Optional `RUP_CONTEXT_DIR`; nothing else |

### Pitfall — encoding on Windows

The Windows console uses cp1252. The skills call `setup_console()` to force
UTF-8; for other scripts, set `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`.

### Pitfall — intermittent bash relay on Windows

`execvpe(/bin/bash) failed: No such file or directory` (WSL relay). Use Git Bash
explicitly (`"C:\Program Files\Git\bin\bash.exe" scripts/install.sh`).

## Observability

| Signal | Where |
|--------|-------|
| Work packets | stdout of `run.py` |
| Artifacts | `.context/docs/<NN-phase>/rup-<skill>.md` |
| Artifact log | `.context/tracking/rup-log.md` |
| Iteration progress | `rup-orchestrator --status --phase P` |
| Project progress | `.context/tracking/progress.md` |

There are no aggregated metrics, alerts or log retention — appropriate for local use.

## Runbook

| Situation | Action |
|-----------|--------|
| Skill does not appear in Claude | Confirm `~/.claude/skills/<skill>/SKILL.md`; restart the agent |
| Skill does not appear in Hermes | Confirm `$HERMES_SKILLS_DIR/creative/<skill>/`; reloads on the next turn |
| `--record` says artifacts are missing | Add a `## <Artifact>` section for each listed artifact and record again |
| Exit 4 | `.context/` not writable — fix permissions or set `--context-dir` / `RUP_CONTEXT_DIR` |
| Exit 5 | `.context/` has no `.rup-standard` marker — ask the user; on approval `rup-context --init --authorized-by "<name>"` |
| `Delivery rejected:` (exit 1) | Fix each listed problem (missing test, no criterion link, trivial test, missing red evidence) and rerun `rup-build --finish` |
| `UnicodeEncodeError` | Run with `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` |
| `ModuleNotFoundError: _shared` | `_shared/` missing in the agent — rerun the full `install.sh` |
| Iteration interrupted | `rup-orchestrator --status --phase P` shows the next pending step; continue from its packet command |
| `Permission denied` on install | `chmod +x scripts/install.sh` (Linux/macOS) |
| Change "without effect" | Check which clone of the repo the process is running from |

## Pending items

- None for operations. Product items in `.context/inbox/`.

## Decisions

- Distribution by directory copy (not an installable package): keeps the
  edit→propagate cycle in one command and without a build.
