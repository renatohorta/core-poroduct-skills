# Project Progress — Core Product Skills

> Last update: 2026-11-03.

## `cp-*` removed, RUP flattened into `skills/` (2026-11-03)

| Change | Status | Date |
|--------|--------|------|
| `skills/deprecated/` deleted; `skills/rup/*` moved to `skills/` | ✅ Done | 2026-11-03 |
| `install.sh`: flat layout, no `--deprecated`, portable listing (no `find -printf`) | ✅ Done | 2026-11-03 |
| `_shared` found in Claude (flat) and Hermes (category) installs | ✅ Done | 2026-11-03 |
| `--auto`: chained context, one artifact per discipline, stop on failure | ✅ Done | 2026-11-03 |
| UCP as a CrewAI tool for the governance agent + sizing validation | ✅ Done | 2026-11-03 |
| `--dry-run` without crewai; exit 1 on unreadable `--input` | ✅ Done | 2026-11-03 |
| CI on `main`; `chat.py` on `rup-*`; docs and `.context/` rewritten | ✅ Done | 2026-11-03 |
| Suite | ✅ 108 passed | 2026-11-03 |

ADR: `.context/tracking/decisions.md` (ADR-0010).

## RUP family created (2026-10-04)

| Change | Status | Date |
|--------|--------|------|
| `skills/rup/` created (flattened on 2026-11-03): 9 skills (orchestrator + 8 disciplines), 21 agents | ✅ Done | 2026-10-04 |
| `install.sh` installs the active `rup` family by default | ✅ Done | 2026-10-04 |
| `tests/test_rup_smoke.py` + conftest RUP helpers | ✅ Done | 2026-10-04 |
| Software Sizing & Effort Estimation (Use Case Points) + `--estimate` CLI | ✅ Done | 2026-10-04 |
| Docs updated (README, docs/, .context) | ✅ Done | 2026-10-04 |

ADRs: `.context/tracking/decisions.md` (ADR-0008, ADR-0009).
Specified by `~/Downloads/especificacao_agentes_rup.md` (Kruchten, RUP 3rd ed.).

## Deprecation (2026-10-04)

| Change | Status | Date |
|--------|--------|------|
| All 15 `cp-*` skills moved to `skills/deprecated/` | ✅ Done | 2026-10-04 |
| `install.sh` no-op by default; `--deprecated` opt-in | ✅ Done | 2026-10-04 |
| Tests + `chat.py` repointed to `skills/deprecated/` | ✅ Done | 2026-10-04 |
| Documentation updated to deprecated mode | ✅ Done | 2026-10-04 |
| Suite green after the move | ✅ 232 passed, 1 skipped | 2026-10-04 |

ADR: `.context/tracking/decisions.md` (ADR-0007).

## Documentation initialization

| Phase | Status | Date | Artifact |
|-------|--------|------|----------|
| `.context/` structure | ✅ Done | 2026-08-18 | `.context/` + `CLAUDE.md` + `AGENT.md` |
| Product vision | ✅ Done | 2026-08-18 | `docs/00-vision.md` |
| Requirements | ✅ Done | 2026-08-18 | `docs/01-requirements.md` |
| Architecture | ✅ Done | 2026-08-18 | `docs/02-architecture.md` |
| Security/LGPD | ✅ Done | 2026-08-18 | `docs/03-security-lgpd.md` |
| Quality/QA | ✅ Done | 2026-08-18 | `docs/04-quality-qa.md` |
| DevOps/Operations | ✅ Done | 2026-08-18 | `docs/05-devops-operations.md` |
| Kanban | ✅ Done | 2026-08-18 | `docs/06-kanban.md` |

## Product state

| Area | State |
|------|-------|
| `rup-*` skills | ✅ 9 skills (orchestrator + 8 disciplines), 21 agents |
| Orchestration | ✅ Governance crew, `--discipline`, chained `--auto` |
| Sizing | ✅ UCP deterministic (CLI + agent tool); FPA/COCOMO II LLM-produced |
| LLM resolution | ✅ Provider-agnostic, actionable failure (`require_llm`) |
| Distribution | ✅ `install.sh` (Hermes + Claude), tested in both layouts |
| Automated tests | ✅ 108 tests, no LLM credential |
| CI/CD | ✅ GitHub Actions on `main` + PRs: Linux 3.12/3.13 + Windows informative |

## Suggested next steps

1. **INIT-02** — persist the RUP artifacts into the target project's `.context/`.
2. **Deterministic FPA / COCOMO II** — same pattern as UCP (code + agent tool).
3. **`.gitattributes`** (`* text=auto eol=lf`) — avoids whole-file CRLF diffs on Windows.
4. **Skill versioning** — no way to know which version is installed in an agent.
