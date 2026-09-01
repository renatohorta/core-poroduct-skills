# Security and LGPD — Core Product Skills

> Discipline: Security/Compliance (`cp-security`). Updated 2026-08-18.

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
| SEC-02 | `claude_proxy.py` **does not require authentication** — any local process can consume the Claude Code OAuth session | Medium | Bind restricted to `127.0.0.1` | Documented; do not run the proxy on a shared machine. See DT-04 |
| SEC-03 | Briefings sent to the crews go to the configured LLM provider | Medium | Explicit provider choice via `.env` | Do not put secrets/personal data in briefings |
| SEC-04 | Orchestrator's `subprocess.run` executes the skills' `run.py` | Low | Fixed `SKILL_PATHS` list, no `shell=True` | Keep — never build a command from a string |
| SEC-05 | `install.sh` does `rm -rf "$dst"` before copying | Low | Destination derived from known env vars | Never point `HERMES_SKILLS_DIR`/`CLAUDE_SKILLS_DIR` to a directory with its own content |
| SEC-06 | Pipeline artifacts may contain code snippets from the target project | Low | `outputs/` in `.gitignore` | Keep |

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

- **DT-04** — `claude_proxy.py` without authentication: evaluate a simple shared
  token (header `Authorization`) validated against an env var.
- **DOC-01** — Port divergence: the `README.md` recommends `--port 8090` but
  `DEFAULT_PORT = 8080` in `scripts/claude_proxy.py`. Align (8080 conflicts with
  common frontends).

## Decisions

- No SAST/dependabot scan for now: the repository has no declared dependencies
  (no `requirements.txt`/`pyproject.toml`) — see DT-05 in
  `.context/docs/05-devops-operations.md`.
