# UI Spec — Core Product Skills

> Document managed by the `cp-software-spec` skill. Updated 2026-09-07.

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
| `scripts/chat.py` | Direct interactive trigger of any skill |
| `scripts/claude_proxy.py` | OpenAI-compatible proxy delegating to `claude -p` |
| `skills/deprecated/cp-orchestrator/scripts/run.py` | Single entry point (factory manager) |
| `skills/deprecated/cp-<name>/scripts/run.py` | Each skill's own CLI |

## Design System (CLI conventions)

- **UTF-8 output** on stdout/stderr (DT-01: `setup_console()` forces it on Windows).
- **Standardized exit codes**: 0 success, 1 usage error, 2 no LLM, 3 no crewai.
- **`--help` always works** (even without crewai); `--dry-run` inspects without
  a credential.
- **Emoji + box-drawing** in output for readability.

## Screen-spec template (for target projects)

When documenting a target project's screens for a UI generator (Lovable etc.),
use `skills/deprecated/cp-software-spec/templates/spec-telas-lovable.md`. Key rules:

1. Inventory **routes** (`src/routes/**`), the **AppShell** (shared layout), and
   **Generative UI** dynamic cards (chat) — all are first-class screens.
2. Define the **Design System tokens** before the screens.
3. Require per-screen **states**: loading / error (with retry) / empty / populated.
4. **Variation = layout, never functionality/scope.**

## Decisions

- No web UI in this repo; the CLI is the interface.
- The `.context/` structure is the "UI" for agents — it must stay concise and
  operational, not narrative.
