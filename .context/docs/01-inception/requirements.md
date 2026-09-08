# Requirements — Core Product Skills

> Discipline: Requirements Engineering (`cp-requirements`). Updated 2026-08-18.

## Status

- [x] Done (initial requirements derived from existing code)

## Context

The requirements below were **derived by reverse engineering** from the existing
code and documentation (`README.md`, `docs/`, `scripts/`, `skills/`). New
requirements must enter through `.context/inbox/initiatives/`.

## Functional requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| RF-01 | Keep the canonical source code of all `cp-*` skills in `skills/` | Must | ✅ Implemented |
| RF-02 | Propagate the skills to Hermes and Claude via `scripts/install.sh` | Must | ✅ Implemented |
| RF-03 | Allow selective install (`--hermes`, `--claude`, `--skill`, `--dry-run`) | Must | ✅ Implemented |
| RF-04 | Resolve the host agent's LLM without coupling to a provider | Must | ✅ Implemented (`_shared/llm.py`) |
| RF-05 | Expose a single entry point (`cp-orchestrator`) for all skills | Must | ✅ Implemented |
| RF-06 | Apply quality gate (PASS/WARN/FAIL) between pipeline phases | Must | ✅ Implemented |
| RF-07 | Pass artifacts from one phase as input to the next | Must | ✅ Implemented |
| RF-08 | Allow resuming the pipeline from a phase (`--start-phase`) | Should | ✅ Implemented |
| RF-09 | Support pipeline simulation without running the crews (default / `--dry-run`) | Should | ✅ Implemented |
| RF-10 | Trigger skills directly via interactive CLI (`scripts/chat.py`) | Should | ✅ Implemented |
| RF-11 | Use Claude Code as the crews' LLM via OpenAI-compatible proxy | Could | ✅ Implemented (`scripts/claude_proxy.py`) |
| RF-12 | Initialize a target project's documentation in `.context/` | Must | ✅ Implemented (`cp-doc-initializer`) |
| RF-13 | Monitor backlog and dispatch tasks with bidirectional feedback | Should | ✅ Implemented (`cp-agile`) |
| RF-14 | Run the NEXUS pipeline (7 phases, 39 agents) natively | Should | ✅ Implemented (`full-dev` mode) |

## Non-functional requirements

| ID | Requirement | Acceptance criterion | Status |
|----|-------------|----------------------|--------|
| NFR-01 | **Portability** | Zero hardcoded OS/machine paths; paths via env var + relative default | ✅ |
| NFR-02 | **No personal data in code** | Zero fixed handles/machine names in scripts | ✅ |
| NFR-03 | **Secrets outside the repository** | `.env` in `.gitignore`; only `.env.example` committed | ✅ |
| NFR-04 | **Skill self-containment** | Each `run.py` embeds its agents; no external directory | ✅ |
| NFR-05 | **UTF-8 encoding on Windows** | Run with `PYTHONUTF8=1`/`PYTHONIOENCODING=utf-8` | ⚠️ Known gap (DT-01) |
| NFR-06 | **Per-phase timeout** | 600s per phase in `--auto` mode | ✅ |
| NFR-07 | **Automated test coverage** | Executable suite in the repository | ❌ Gap (DT-02) |

## Prioritized backlog (MoSCoW)

**Must (still pending)**
- No open items — the functional core is implemented.

**Should**
- DT-01: fix `UnicodeEncodeError` of `cp-orchestrator` on Windows cp1252 console.
- DT-02: create a test suite (minimum: smoke test of each skill's `--dry-run`).
- DT-03: automated validation of each skill's `invoke` contract.

**Could**
- CI that runs `install.sh --dry-run` + smoke tests on every push.
- Semantic versioning of the skills and a changelog.

**Won't (for now)**
- Publishing the skills as a distributable package (internal use).

## Business rules

- **BR-01** — Every skill change is made **in this repository**; editing the
  installed copy in the agent is forbidden (it will be overwritten on the next
  `install.sh`).
- **BR-02** — `_shared` is a shared helper, **not** a skill: it goes to the
  agent's skills root, not to the category.
- **BR-03** — Every `cp-*` skill documents its artifacts in `.context/docs/`,
  per the crew→file map defined in `.context/README.md`.

## Decisions

- Requirements derived from the real state of the code, not from a prior briefing;
  `00-vision.md` is the source of the product's intent.
