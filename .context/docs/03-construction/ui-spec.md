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
| `scripts/chat.py` | Direct trigger of any `rup-*` skill with the `.env` LLM |
| `scripts/claude_proxy.py` | OpenAI-compatible proxy delegating to `claude -p` |
| `skills/rup-orchestrator/scripts/run.py` | Single entry point (RUP governance + dispatch) |
| `skills/rup-<discipline>/scripts/run.py` | Each discipline's own CLI |

## Design System (CLI conventions)

- **UTF-8 output** on stdout/stderr (DT-01: `setup_console()` forces it on Windows).
- **Standardized exit codes**: 0 success, 1 usage error, 2 no LLM, 3 no crewai.
- **`--help` always works** (even without crewai); `--dry-run` inspects without
  a credential, and without crewai it lists the planned agents.
- **Emoji + box-drawing** in output for readability.

## Decisions

- No web UI in this repo; the CLI is the interface.
- The `.context/` structure is the "UI" for agents — it must stay concise and
  operational, not narrative.
