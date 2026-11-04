# Project Progress — Core Product Skills

> Last update: 2026-11-03.

## cp-test measures the value of the tests — ADR-0016 (2026-11-04)

Source: `MELHORIAS-cp-testes.md` (jusfy-lawsuit session: 96% coverage, 76% mutation score).

| Change | Status | Date |
|--------|--------|------|
| `cp-test --audit`: protocol A0–A8 with the project's exact commands | ✅ Done | 2026-11-04 |
| `_shared/mutation.py`: AST mutants, parallel resumable runner in copies, changed-tree refusal, budget, `--lines`, report, triage skeleton + `--triage-check` | ✅ Done | 2026-11-04 |
| `_shared/testaudit.py`: no assert, trivial asserts, no project call, self-mock | ✅ Done | 2026-11-04 |
| Packet: mandatory measured evidence, new artifact Test Value Assessment, evidence files embedded | ✅ Done | 2026-11-04 |
| `references/audit.md` (protocol, profile, runner pitfalls), `references/triage.md` (classes, rules) | ✅ Done | 2026-11-04 |
| cp-build (mutate changed lines, `## Mutation` warning), cp-review (mutation + adversarial review), cp-debug (fix must kill its mutants), orchestrator (routing + metric) | ✅ Done | 2026-11-04 |
| Suite | ✅ 309 passed | 2026-11-04 |
| Not done from the document: P1 (`--record` overwrites a phase), P2 (commit hint), P3 (`--init` lists files outside `.context/`), P5 (estimate × actual) | ⏳ Open | — |

## Skills renamed `rup-*` → `cp-*` (2026-11-03)

| Change | Status | Date |
|--------|--------|------|
| 15 skill dirs, registry, SKILL.md, artifact names, docs and tests renamed (ADR-0014) | ✅ Done | 2026-11-03 |
| This repository's `.context/` authorized (`cp-context --init`) | ✅ Done | 2026-11-03 |
| Skills installed in Claude Code (`install.sh --claude`) | ✅ Done | 2026-11-03 |
| Root `docs/` removed; `.context/` is the only documentation (ADR-0015) | ✅ Done | 2026-11-03 |

## Execution skills — INIT-03 (2026-11-03)

| Change | Status | Date |
|--------|--------|------|
| Authorization gate: marker `.context/.rup-standard`, exit code 5 on every writing command | ✅ Done | 2026-11-03 |
| `cp-context`: `--status`, `--init`, `--import`, `--record-import`; pointer note in `CLAUDE.md`/`AGENT.md` | ✅ Done | 2026-11-03 |
| `cp-discover`: discovery conversation recorded as `cp-discover.md`, embedded first in later packets | ✅ Done | 2026-11-03 |
| `cp-backlog`: cards EP/ST/TK/BUG, moves with roll-up, derivation, releases/iterations, generated `06-roadmap.md`/`06-board.md` | ✅ Done | 2026-11-03 |
| `cp-build`, `cp-debug`, `cp-review`: TDD start/finish with test-value checks, bug flow, review verdict | ✅ Done | 2026-11-03 |
| Shared modules: `consent`, `frontmatter`, `cards`, `roadmap`, `testcheck{,_py,_js}` | ✅ Done | 2026-11-03 |
| Docs, ADR-0013, this `.context/` updated | ✅ Done | 2026-11-03 |
| Suite (no LLM, stdlib only, ~5 s) | ✅ 268 passed | 2026-11-03 |
| **Pending (owner)**: authorize this repository's `.context/` (`cp-context --init`), then uninstall superpowers if satisfied | ⏳ Open | — |

ADR: `.context/tracking/decisions.md` (ADR-0013). Closes INIT-03.

## Host agent is the LLM (2026-11-03)

| Change | Status | Date |
|--------|--------|------|
| Work packet + `--record` engine (`_shared/discipline.py`), registry (`_shared/rup.py`) | ✅ Done | 2026-11-03 |
| 8 disciplines rewritten as `SPEC` data (roles/missions/artifacts kept verbatim) | ✅ Done | 2026-11-03 |
| Orchestrator: governance packet, `--discipline`, `--auto` protocol, `--status`, UCP via `--estimate` | ✅ Done | 2026-11-03 |
| Removed: crewai, `llm.py`, `claude_proxy.py`, `chat.py`, `.env.example`, `--dry-run`, `--output`, exits 2/3 | ✅ Done | 2026-11-03 |
| `SKILL.md` of every skill teaches the agent the protocol | ✅ Done | 2026-11-03 |
| Suite (no LLM, stdlib only, ~3 s) | ✅ 138 passed | 2026-11-03 |

ADR: `.context/tracking/decisions.md` (ADR-0012).

## Artifacts always persisted into `.context/` (2026-11-03)

| Change | Status | Date |
|--------|--------|------|
| `skills/_shared/context.py`: resolution, phase layout, provenance, log | ✅ Done | 2026-11-03 |
| All 9 skills write `.context/docs/<NN-phase>/cp-<skill>.md` (+ `--context-dir`) | ✅ Done | 2026-11-03 |
| Writability checked before the LLM call — exit 4 | ✅ Done | 2026-11-03 |
| `--auto` chains through the `.context/` artifacts; `--estimate` writes the sizing | ✅ Done | 2026-11-03 |
| Fake crewai + end-to-end tests; suite | ✅ 138 passed | 2026-11-03 |

ADR: `.context/tracking/decisions.md` (ADR-0011). Closes INIT-02.

## `cp-*` removed, RUP flattened into `skills/` (2026-11-03)

| Change | Status | Date |
|--------|--------|------|
| `skills/deprecated/` deleted; `skills/rup/*` moved to `skills/` | ✅ Done | 2026-11-03 |
| `install.sh`: flat layout, no `--deprecated`, portable listing (no `find -printf`) | ✅ Done | 2026-11-03 |
| `_shared` found in Claude (flat) and Hermes (category) installs | ✅ Done | 2026-11-03 |
| `--auto`: chained context, one artifact per discipline, stop on failure | ✅ Done | 2026-11-03 |
| UCP as a CrewAI tool for the governance agent + sizing validation | ✅ Done | 2026-11-03 |
| `--dry-run` without crewai; exit 1 on unreadable `--input` | ✅ Done | 2026-11-03 |
| CI on `main`; `chat.py` on `cp-*`; docs and `.context/` rewritten | ✅ Done | 2026-11-03 |
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
| `cp-*` skills | ✅ 15 skills: 9 document (orchestrator + 8 disciplines, 21 agents) + 6 execution |
| Authorization | ✅ Marker `.rup-standard` gates every write (exit 5); this repo's `.context/` not yet authorized |
| Cards / roadmap | ✅ `EP/ST/TK/BUG-NNN`, `.context/roadmap/`, generated views |
| Execution model | ✅ The host agent is the LLM: work packet → document → `--record` |
| Orchestration | ✅ Front door `--route` (ADR-0017), governance packet, `--discipline`, `--auto` protocol, `--status` |
| Sizing | ✅ UCP deterministic (`--estimate`); FPA/COCOMO II estimated by the agent |
| Dependencies | ✅ None at runtime (stdlib only) |
| Distribution | ✅ `install.sh` (Hermes + Claude), tested in both layouts |
| Automated tests | ✅ 336 tests, ~10 s, end to end through `.context/` |
| Persistence | ✅ Every artifact written to `.context/` (ADR-0011) |
| CI/CD | ✅ GitHub Actions on `main` + PRs: Linux 3.12/3.13 + Windows informative |

## Suggested next steps

1. **Deterministic FPA / COCOMO II** — same pattern as UCP (code + agent tool).
2. **`.gitattributes`** (`* text=auto eol=lf`) — avoids whole-file CRLF diffs on Windows.
3. **Skill versioning** — no way to know which version is installed in an agent.
