# Requirements — Core Product Skills

> Updated 2026-11-03 (RUP family — ADR-0008/0009/0010).

## Status

- [x] Done (requirements of the RUP family)

## Context

New requirements must enter through `.context/inbox/initiatives/`.

## Functional requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| RF-01 | Keep the canonical source code of all `rup-*` skills in `skills/` | Must | ✅ Implemented |
| RF-02 | Propagate the skills to Hermes and Claude via `scripts/install.sh` | Must | ✅ Implemented |
| RF-03 | Allow selective install (`--hermes`, `--claude`, `--skill`, `--dry-run`) | Must | ✅ Implemented |
| RF-04 | Resolve the host agent's LLM without coupling to a provider | Must | ✅ Implemented (`_shared/llm.py`) |
| RF-05 | Expose a single entry point (`rup-orchestrator`) that governs the RUP lifecycle | Must | ✅ Implemented |
| RF-06 | One skill per RUP discipline (8), with the agents and artifacts of the spec | Must | ✅ Implemented |
| RF-07 | Dispatch one discipline (`--discipline`) or all in order (`--auto`) | Must | ✅ Implemented |
| RF-08 | In `--auto`, pass the artifacts of earlier disciplines to the next ones and keep one artifact per discipline | Must | ✅ Implemented (2026-11-03) |
| RF-09 | Compute Use Case Points deterministically (CLI and agent tool) | Must | ✅ Implemented |
| RF-10 | Inspect the plan without an LLM (`--dry-run`, also without crewai) | Should | ✅ Implemented |
| RF-11 | Trigger skills directly via CLI (`scripts/chat.py`) | Should | ✅ Implemented |
| RF-12 | Use Claude Code as the crews' LLM via OpenAI-compatible proxy | Could | ✅ Implemented (`scripts/claude_proxy.py`) |
| RF-13 | Persist the RUP artifacts into the target project's `.context/` | Should | ❌ Open (INIT-02) |
| RF-14 | Compute FPA (IFPUG/NESMA) and COCOMO II deterministically | Could | ❌ Open — LLM-produced today |

## Non-functional requirements

| ID | Requirement | Acceptance criterion | Status |
|----|-------------|----------------------|--------|
| NFR-01 | **Portability** | Zero hardcoded OS/machine paths; paths via env var + relative default | ✅ |
| NFR-02 | **No personal data in code** | Zero fixed handles/machine names in scripts | ✅ |
| NFR-03 | **Secrets outside the repository** | `.env` in `.gitignore`; only `.env.example` committed | ✅ |
| NFR-04 | **Skill self-containment** | Each `run.py` embeds its agents; no external directory | ✅ |
| NFR-05 | **UTF-8 encoding on Windows** | `setup_console()` forces UTF-8 on stdout/stderr | ✅ |
| NFR-06 | **Works in both agent layouts** | `_shared` found in Claude (flat) and Hermes (category) installs | ✅ (tested) |
| NFR-07 | **Automated test coverage** | Suite runs without credentials in CI | ✅ |

## Prioritized backlog (MoSCoW)

**Should**
- INIT-02: persist RUP artifacts into `.context/`.

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
- **BR-03** — The orchestrator registry (`DISCIPLINES`) and the `skills/rup-*`
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
| Type | Development tool (skills/CLI), **internal use** |
| Network exposure | None by default; only `claude_proxy.py` opens a local socket |
| Personal data processed | **No third-party personal data** is collected or stored |
| Attack surface | Local execution: reading `.env`, `subprocess`, calls to LLM APIs |

## Verified baseline (2026-08-18)

| Check | Result |
|-------|--------|
| Secrets committed to Git | ✅ None — `git ls-files` only returns `.env.example` |
| API keys hardcoded in code | ✅ None (`sk-…`/`AIza…` not found) |
| `.gitignore` covers secrets | ✅ `.env`, `.env.local`, `.env.*.local` |
| Local proxy bind | ✅ `127.0.0.1` (not `0.0.0.0`) — no network exposure |
| Personal/machine paths hardcoded | ✅ None in the skills (env var + relative default) |

## Risks and controls

| ID | Risk | Severity | Current control | Action |
|----|------|----------|-----------------|--------|
| SEC-01 | LLM key leaks via `.env` copied along with the skill | Medium | `install.sh` copies only `skills/`; `.env` stays at the root and is ignored by Git | Keep — do not move `.env` into `skills/` |
| SEC-02 | `claude_proxy.py` exposes the Claude Code OAuth session to local processes | Medium | Bind restricted to `127.0.0.1`; optional `CLAUDE_PROXY_TOKEN` bearer (DT-04) | Set `CLAUDE_PROXY_TOKEN` on shared machines |
| SEC-03 | Briefings sent to the crews go to the configured LLM provider | Medium | Explicit provider choice via `.env` | Do not put secrets/personal data in briefings |
| SEC-04 | Orchestrator's `subprocess.run` executes the skills' `run.py` | Low | Fixed `DISCIPLINES` registry, argument list, no `shell=True` | Keep — never build a command from a string |
| SEC-05 | `install.sh` does `rm -rf "$dst"` before copying | Low | Destination derived from known env vars | Never point `HERMES_SKILLS_DIR`/`CLAUDE_SKILLS_DIR` to a directory with its own content |
| SEC-06 | `--auto` artifacts may contain content from the target project | Low | Written only where `--output` points; chaining files live in a temp dir deleted at the end | Do not point `--output` inside a committed path with sensitive content |

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
| `LLM_API_KEY` / `GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` … | Local `.env` (not committed) or agent env var | In `SKILL.md`, `run.py`, `references/` or a commit |

Public configuration template: `.env.example` (no real values).

## Security pending items

- None open. DT-04 (proxy token) and DOC-01 (proxy port 8090) were resolved on
  2026-08-18 — see `.context/inbox/processed/`.
