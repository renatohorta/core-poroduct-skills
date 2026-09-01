# Project Progress — Core Product Skills

> Updated by the orchestrator after each completed phase. Last update: 2026-08-18.

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
| `cp-*` skills | ✅ 15 skills implemented and propagable |
| Orchestration | ✅ Single entry point with quality gates and 12 modes |
| LLM resolution | ✅ Provider-agnostic, with actionable failure (`require_llm`) |
| Distribution | ✅ `install.sh` (Hermes + Claude) |
| Automated tests | ✅ 158 tests, no LLM credential (DT-02/DT-03) |
| CI/CD | ✅ GitHub Actions: Linux 3.12/3.13 + Windows informative (DT-06) |
| Declared dependencies | ✅ `requirements.txt` / `requirements-dev.txt` (DT-05) |

## Suggested next steps

The backlog raised at initialization was fully completed on 2026-08-18.
There is no open item. Suggestions for when there is appetite:

1. **`.gitattributes`** — the repo does not have one, and Git converts LF->CRLF
   in the `.md` files on Windows. Another machine (or the Windows CI job) will
   see whole-file diffs with no real change. `* text=auto eol=lf` fixes it.
2. **Code coverage** — the suite covers contract and error handling; the
   internal logic of the crews (task assembly, chaining) remains untested.
3. **Skill versioning** — without a version or changelog, there is no way to know
   which version of a skill is installed in an agent.

Full backlog: `.context/docs/06-kanban.md`.
