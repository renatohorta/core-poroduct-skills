# DT-04 — `claude_proxy.py` without authentication [Done]

**Type**: Security · **Priority**: Medium · **Opened on**: 2026-08-18
**Related**: SEC-02 in `.context/docs/03-security-lgpd.md`

## Context

`scripts/claude_proxy.py` exposes `/v1/chat/completions` delegating to `claude -p`,
which uses the user's Claude Code OAuth session. The server **validates no
header** — any local process can consume the session and quota.

Current mitigation: bind on `127.0.0.1` (not exposed on the network). Residual
risk: other processes/users on the same machine.

## Proposal

Validate `Authorization: Bearer ***` against `CLAUDE_PROXY_TOKEN`:

- Token absent from the environment → keep current behavior + warning at startup
  (does not break existing users).
- Token present → reject a request without a match with 401.

Combines well with the skills' `.env`, which already needs to fill `LLM_API_KEY`
(today ignored by the proxy).

## Acceptance criterion

- With `CLAUDE_PROXY_TOKEN` set, a request without the correct header receives 401.
- `.env.example` documents the variable.


---

## Resolution

**Done on 2026-08-18.** Verified with the suite (`pytest`, 158 tests, no
LLM credential). See `.context/docs/04-quality-qa.md`.
