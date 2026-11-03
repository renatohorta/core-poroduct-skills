# Installation and Update

The skills live directly under `skills/` (`rup-*`, plus the `_shared/` helper).
`scripts/install.sh` propagates every directory that has a `SKILL.md` to the
agents (Hermes and Claude), and copies `_shared/` to the agents' skills root.

## Prerequisites

To **propagate** the skills (normal use):

- **bash** (Git Bash on Windows, or native bash on Linux/macOS)
- Write access to the agents' skills directories

To **run** the skills, the host agent needs `crewai` installed. Without it,
`--help` and `--dry-run` still work and execution exits with code 3 and an
install instruction (never with a traceback).

## Development environment

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements-dev.txt
.venv/Scripts/python.exe -m pytest      # Windows  (.venv/bin/python on Unix)
```

> **Python 3.14**: the `pip` resolver may pin `crewai` to an old version
> (0.11.x) because of transitive wheel metadata. With `uv`, resolution normally
> reaches 1.15.x. When in doubt, use 3.12 or 3.13.

## Installation

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

## Destination directories

The script detects the destination automatically, but you can override it via env vars:

| Env var | Default (Windows) | Default (Linux/macOS) |
|---------|-------------------|----------------------|
| `HERMES_SKILLS_DIR` | `%LOCALAPPDATA%\hermes\skills` | `~/.hermes/skills` |
| `CLAUDE_SKILLS_DIR` | `~/.claude/skills` | `~/.claude/skills` |

### Destination structure

- **Hermes**: the skills are installed in the `creative` category:
  `$HERMES_SKILLS_DIR/creative/<skill>/`, with `_shared/` at
  `$HERMES_SKILLS_DIR/_shared/`
- **Claude**: the skills are installed flat:
  `$CLAUDE_SKILLS_DIR/<skill>/`, with `_shared/` at `$CLAUDE_SKILLS_DIR/_shared/`

Each `run.py` finds `_shared/` next to the skill or one level up, so both layouts
work.

## Update flow

1. Edit the skills **in this repository** (in `skills/`).
2. Run `./scripts/install.sh` to propagate.
3. Restart the agent (Hermes reloads skills on the next turn; Claude reloads on
   the next command).

## Example

```bash
# Updates only the orchestrator in Hermes
./scripts/install.sh --hermes --skill rup-orchestrator

# Updates everything in Claude
./scripts/install.sh --claude
```

## Troubleshooting

- **"No skills found"**: confirm that `skills/rup-*/SKILL.md` exists in the
  repository (only directories with a `SKILL.md` are installed).
- **`--skill X` not found**: use the directory name, e.g. `rup-requirements`.
- **`ModuleNotFoundError: _shared`**: `_shared/` was not propagated — rerun the
  full install (not only `--skill`) once.
- **Permission denied**: on Linux/macOS, run `chmod +x scripts/install.sh`.
- **Claude does not see the skill**: confirm that `~/.claude/skills/<skill>/SKILL.md`
  exists and that Claude was restarted.
