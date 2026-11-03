---
name: rup-context
description: "Set up and check the project's .context/ for the RUP skills. Use when a rup-* skill exits with code 5 (not authorized), when a project has no .context/ or one without the .rup-standard marker, or when the user says 'set up RUP', 'adopt the RUP standard', 'init .context'."
---

# rup-context — adopt the RUP standard in `.context/`

Every `rup-*` skill writes into `.context/`, but only after the user authorized
the RUP standard there (marker `.context/.rup-standard`). This skill detects the
state and, **only with the user's explicit approval**, adds what is missing.
It never overwrites or deletes existing files.

## Steps

1. Run `python scripts/run.py --status` (read-only).
2. Show the user what was found (exists, authorized, other doc dirs such as
   `.specs/` or `docs/`) and what `--init` will create (the `missing:` list,
   the marker, and a RUP pointer note in `CLAUDE.md` / `AGENT.md` — existing
   text is kept).
3. **Ask the user.** Run `--init` ONLY after they explicitly approve:
   `python scripts/run.py --init --authorized-by "<user name>"`
4. If `other doc dirs` is not "none", offer `--import` to bring those docs in
   (arrives with the import step; originals are never moved or deleted).

## Commands

- `--status` — report `context_dir`, `exists`, `authorized`, `missing`, `other doc dirs` (exit 0).
- `--init --authorized-by "<who>"` — create the missing standard tree, write the marker, add the pointer note.
- `--context-dir D` — target another `.context/` (default: auto-detect or `RUP_CONTEXT_DIR`).

Exit codes: 0 ok · 1 usage (e.g. `--init` without `--authorized-by`, or project root missing).
The standard tree is listed in `references/standard.md`.
