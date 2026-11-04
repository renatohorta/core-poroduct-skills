# Requirements — Core Product Skills

> Updated 2026-11-03 (RUP family — ADR-0008/0009/0010; execution skills — ADR-0013).

## Status

- [x] Done (requirements of the RUP family)

## Context

New requirements must enter through `.context/inbox/initiatives/`.

## Functional requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| RF-01 | Keep the canonical source code of all `cp-*` skills in `skills/` | Must | ✅ Implemented |
| RF-02 | Propagate the skills to Hermes and Claude via `scripts/install.sh` | Must | ✅ Implemented |
| RF-03 | Allow selective install (`--hermes`, `--claude`, `--skill`, `--dry-run`) | Must | ✅ Implemented |
| RF-04 | The agent running the skill is the LLM — no model call, key or proxy in the skills | Must | ✅ Implemented (ADR-0012) |
| RF-05 | Expose a single entry point (`cp-orchestrator`) that governs the RUP lifecycle | Must | ✅ Implemented |
| RF-06 | One skill per RUP discipline (8), with the agents and artifacts of the spec | Must | ✅ Implemented |
| RF-07 | Dispatch one discipline (`--discipline`) or all in order (`--auto`) | Must | ✅ Implemented |
| RF-08 | In `--auto`, pass the artifacts of earlier disciplines to the next ones and keep one artifact per discipline | Must | ✅ Implemented (2026-11-03) |
| RF-09 | Compute Use Case Points deterministically (CLI and agent tool) | Must | ✅ Implemented |
| RF-10 | Work packet per skill: roles, missions, required artifacts, earlier `.context/` artifacts | Must | ✅ Implemented |
| RF-11 | `--record` validates that every required artifact is present before writing | Must | ✅ Implemented |
| RF-12 | Iteration protocol (`--auto`) and progress (`--status`) for the host | Should | ✅ Implemented |
| RF-13 | **Always** persist the RUP artifacts into the target project's `.context/` | Must | ✅ Implemented (ADR-0011, INIT-02) |
| RF-15 | **Never write into `.context/` without the user's authorization**: marker `.rup-standard`, exit 5, `cp-context --init` after approval, non-destructive | Must | ✅ Implemented (ADR-0013) |
| RF-16 | Import existing project docs into `.context/` without moving, changing or deleting the originals | Should | ✅ Implemented (ADR-0013) |
| RF-17 | Discovery conversation recorded as `cp-discover.md` and embedded first in later packets | Must | ✅ Implemented (ADR-0013) |
| RF-18 | Cards `EP/ST/TK/BUG-NNN` with fixed, validated sections, stable criterion IDs `ST-NNN/AC-n` and parent links; derivation from the requirements only adds | Must | ✅ Implemented (ADR-0013) |
| RF-19 | Roadmap of releases → iterations → epics; generated `06-roadmap.md` and `06-board.md` | Must | ✅ Implemented (ADR-0013) |
| RF-20 | Move cards between columns by declaration, logged in the card and `rup-log.md`; automatic roll-up of stories/epics | Must | ✅ Implemented (ADR-0013) |
| RF-21 | Task execution with TDD: `--start` packet and branch name, `--finish` checks declared tests (exist, criterion-linked, non-trivial, red evidence) | Must | ✅ Implemented (ADR-0013) |
| RF-22 | Bug flow: root cause recorded before the fix, regression test referencing the bug ID | Must | ✅ Implemented (ADR-0013) |
| RF-23 | Review checklist and verdict that moves the card | Should | ✅ Implemented (ADR-0013) |
| RF-24 | Pointer note in the project's `CLAUDE.md`/`AGENT.md` listing which skill to use when | Should | ✅ Implemented (ADR-0013) |
| RF-14 | Compute FPA (IFPUG/NESMA) and COCOMO II deterministically | Could | ❌ Open — estimated by the agent today |

## Non-functional requirements

| ID | Requirement | Acceptance criterion | Status |
|----|-------------|----------------------|--------|
| NFR-01 | **Portability** | Zero hardcoded OS/machine paths; paths via env var + relative default | ✅ |
| NFR-02 | **No personal data in code** | Zero fixed handles/machine names in scripts | ✅ |
| NFR-03 | **No secrets needed** | The skills read no credential; `.env` stays git-ignored | ✅ |
| NFR-04 | **Skill self-containment** | Each `run.py` embeds its agents; no external directory | ✅ |
| NFR-05 | **UTF-8 encoding on Windows** | `setup_console()` forces UTF-8 on stdout/stderr | ✅ |
| NFR-06 | **Works in both agent layouts** | `_shared` found in Claude (flat) and Hermes (category) installs | ✅ (tested) |
| NFR-07 | **Automated test coverage** | Suite runs without credentials in CI | ✅ |
| NFR-08 | **No runtime dependency** | Standard library only (tested with `python -S`); no `git` subprocess, no LLM/network call | ✅ |
| NFR-09 | **Non-destructive** | Skills never delete, move or overwrite curated docs, imported originals, existing `CLAUDE.md`/`AGENT.md` text or `06-kanban.md` | ✅ |
| NFR-10 | **Readable skills** | Each execution `SKILL.md` <= ~60 lines: when to use, 2–4 steps, commands | ✅ |

## Prioritized backlog (MoSCoW)

**Could**
- Deterministic FPA / COCOMO II calculators (same pattern as UCP).
- Semantic versioning of the skills and a changelog.
- `.gitattributes` (`* text=auto eol=lf`) to avoid CRLF diffs on Windows.

**Won't (for now)**
- Publishing the skills as a distributable package (internal use).

## Business rules

- **BR-01** — Every skill change is made **in this repository**; editing the
  installed copy in the agent is forbidden (it will be overwritten on the next
  `install.sh`).
- **BR-02** — `_shared` is a shared helper, **not** a skill: it goes to the
  agent's skills root, not to the category.
- **BR-04** — Card IDs are assigned by the skill, never by the agent; a card's
  `status` equals its folder; a task covers criteria of its parent story.
- **BR-05** — A card moves when the agent *declares* the step done; no proof is
  required to move. The test brake lives in `cp-build --finish`.
- **BR-03** — The orchestrator registry (`DISCIPLINES`) and the `skills/cp-*`
  directories must match (enforced by a test).

---

## Security & LGPD (NFR)

# Security and LGPD — Core Product Skills

> Updated 2026-11-03.

## Status

- [x] Done (security baseline raised)

## Project classification

| Aspect | Situation |
|--------|-----------|
| Type | Development tool (skills/CLI), open source under the **MIT license** |
| Network exposure | None — no socket, no outbound call |
| Personal data processed | **No third-party personal data** is collected or stored |
| Attack surface | Local execution: reading the briefing/document, writing `.context/`, `subprocess` of sibling skills |

## Verified baseline (2026-08-18)

| Check | Result |
|-------|--------|
| Secrets committed to Git | ✅ None |
| API keys hardcoded in code | ✅ None (`sk-…`/`AIza…` not found) |
| `.gitignore` covers secrets | ✅ `.env`, `.env.local`, `.env.*.local` |
| Personal/machine paths hardcoded | ✅ None in the skills (env var + relative default) |

## Risks and controls

| ID | Risk | Severity | Current control | Action |
|----|------|----------|-----------------|--------|
| ~~SEC-01~~ | ~~LLM key leaks via `.env` copied along with the skill~~ | — | The skills read no key (ADR-0012) | — |
| ~~SEC-02~~ | ~~`claude_proxy.py` exposed the Claude Code OAuth session~~ | — | Proxy removed (ADR-0012) | — |
| SEC-03 | Briefings and earlier artifacts end up in the host agent's context, i.e. its LLM provider | Medium | Same exposure as the conversation itself — no extra provider | Do not put secrets/personal data in briefings |
| SEC-04 | Orchestrator's `subprocess.run` executes the skills' `run.py` | Low | Fixed `DISCIPLINES` registry, argument list, no `shell=True` | Keep — never build a command from a string |
| SEC-05 | `install.sh` does `rm -rf "$dst"` before copying | Low | Destination derived from known env vars | Never point `HERMES_SKILLS_DIR`/`CLAUDE_SKILLS_DIR` to a directory with its own content |
| SEC-06 | `.context/` artifacts may contain content from the target project | Low | Written only to the resolved `.context/` (never outside the git root unless `--context-dir`/`RUP_CONTEXT_DIR` says so) | Review `cp-*.md` before committing in projects with sensitive data |

## LGPD

The repository is **neither a controller nor an operator of personal data**: it
does not collect, store or process data subjects' data. Practical consequences:

- There is no legal basis to declare, nor an applicable RIPD for this repository.
- **Derived attention**: when the skills run over a target project that handles
  personal data, the content sent to the LLM (code, briefings, logs) may contain
  personal data from that project. The LGPD assessment belongs to the **target
  project**, which must record it in its own `.context/docs/03-security-lgpd.md`.
- Operational rule: **do not paste real production data** into skill briefings.

## Secret management

| Secret | Where it lives | Never |
|--------|----------------|-------|
None. The skills read no credential (ADR-0012); the host agent's own
authentication never reaches them.

## Security pending items

- None open.
