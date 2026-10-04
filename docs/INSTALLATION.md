# Installation and Update

The repository hosts two skill families under `skills/`:

- **Active**: `skills/rup/` (Rational Unified Process) — **installed by default**.
- **Deprecated**: `skills/deprecated/` (the legacy `cp-*` Software Factory) —
  installed **only** with `--deprecated`.

The `scripts/install.sh` script propagates the skills to the agents (Hermes and
Claude). A plain run installs the active `rup` family; `--deprecated` adds the
legacy `cp-*` family on top.

## Prerequisites

To **propagate** the skills (normal use):

- **bash** (Git Bash on Windows, or native bash on Linux/macOS)
- Write access to the agents' skills directories

To **run** the skills, the host agent needs `crewai` installed. Without it,
`--help` still works and execution exits with code 3 and an install instruction
(never with a traceback).

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
# Default: installs/updates the ACTIVE RUP family in Hermes and Claude
./scripts/install.sh

# Only in Hermes / only in Claude
./scripts/install.sh --hermes
./scripts/install.sh --claude

# One specific skill
./scripts/install.sh --skill rup-requirements

# Simulation (shows what it would do, without copying)
./scripts/install.sh --dry-run

# ALSO install the deprecated cp-* family (adds it on top of the rup family)
./scripts/install.sh --deprecated
```

## Destination directories

The script detects the destination automatically, but you can override it via env vars:

| Env var | Default (Windows) | Default (Linux/macOS) |
|---------|-------------------|----------------------|
| `HERMES_SKILLS_DIR` | `%LOCALAPPDATA%\hermes\skills` | `~/.hermes/skills` |
| `CLAUDE_SKILLS_DIR` | `~/.claude/skills` | `~/.claude/skills` |

### Destination structure

- **Hermes**: the skills are installed in the `creative` category:
  `$HERMES_SKILLS_DIR/creative/<skill>/`
- **Claude**: the skills are installed flat:
  `$CLAUDE_SKILLS_DIR/<skill>/`

## Update flow

1. Edit the skills **in this repository** (in `skills/`).
2. Run `./scripts/install.sh` to propagate.
3. Restart the agent (Hermes reloads skills on the next turn; Claude reloads on
   the next command).

## Example

```bash
# Updates only the orchestrator in Hermes
./scripts/install.sh --hermes --skill cp-orchestrator

# Updates everything in Claude
./scripts/install.sh --claude
```

## Troubleshooting

- **"No skill found"**: confirm that `skills/rup/` exists in the repository.
- **The cp-* skills are not installed**: that is intended — they are deprecated;
  pass `--deprecated` to include them.
- **Permission denied**: on Linux/macOS, run `chmod +x scripts/install.sh`.
- **Claude does not see the skill**: confirm that `~/.claude/skills/<skill>/SKILL.md`
  exists and that Claude was restarted.
