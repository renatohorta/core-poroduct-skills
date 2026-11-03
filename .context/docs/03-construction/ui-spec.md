# UI Spec — Core Product Skills

> Updated 2026-11-03.

## Status

- [x] In progress (derived from the existing code)

## Overview

This repository is a **CLI/agent toolset** — it has no web UI of its own. The
"UI" is the **CLI surface** of the skills and the **`.context/` structure** that
agents read/write. This file documents the CLI surface and the screen-spec
template used when documenting a target project's screens for a UI generator.

## CLI surface (the "screens" of the toolset)

| Entry point | Purpose |
|-------------|---------|
| `scripts/install.sh` | Propagates `skills/` to Hermes and Claude |
| `skills/rup-orchestrator/scripts/run.py` | Single entry point (RUP governance + dispatch) |
| `skills/rup-<discipline>/scripts/run.py` | Each discipline's own CLI |
| `skills/rup-{context,discover,backlog,build,debug,review}/scripts/run.py` | Execution skills (ADR-0013) |

## Design System (CLI conventions)

- **UTF-8 output** on stdout/stderr (DT-01: `setup_console()` forces it on Windows).
- **Standardized exit codes**: 0 success, 1 usage error / missing artifacts /
  invalid document / rejected delivery, 4 `.context/` not writable, 5 needs
  authorization (no `.rup-standard` marker).
- **The packet is the main "screen"**: markdown addressed to the host agent —
  instructions first, then briefing, earlier artifacts and roles; exact commands
  (absolute paths, quoted for the OS) so the host can copy them.
- **Emoji + box-drawing** in output for readability.

## Decisions

- No web UI in this repo; the CLI is the interface.
- The `.context/` structure is the "UI" for agents — it must stay concise and
  operational, not narrative.
