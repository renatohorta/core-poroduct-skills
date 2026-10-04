# Decision Log (ADRs) — Core Product Skills

> Every important decision is recorded here with context and rationale.

---

## ADR-0001 — Source of truth in `.context/`

**Date**: 2026-08-18 · **Status**: Accepted

**Context**: The project context was spread across `.hermes/` and `.claude/`,
polluting the repository and tying the documentation to a specific agent.

**Decision**: All context is read and written in `.context/`. `CLAUDE.md` and
`AGENT.md` at the root are only pointers. Creating `.hermes/`/`.claude/` for
context is forbidden.

**Consequences**: Documentation portable across agents; a single place to
consult. `docs/` still exists for human-facing documentation — in case of
divergence, `.context/` prevails.

---

## ADR-0002 — `cp-full-dev` merged into `cp-orchestrator`

**Date**: before 2026-08-18 · **Status**: Accepted

**Context**: The NEXUS pipeline (7 phases, 39 agents) lived in a separate skill,
triggered by the orchestrator via subprocess — an extra hop and two surfaces to
keep in sync.

**Decision**: NEXUS runs natively in the orchestrator via `NexusExecutor`; the
`cp-full-dev` skill was eliminated. Access is through the `full-dev` mode.

**Consequences**: Less indirection and automatic mode detection
(full/sprint/micro). In exchange, the orchestrator's `run.py` grew larger and
concentrates more responsibility.

---

## ADR-0003 — Provider-agnostic LLM resolution

**Date**: before 2026-08-18 · **Status**: Accepted

**Context**: Without an explicit `llm=`, CrewAI falls into the OpenAI default and
fails with `OPENAI_API_KEY is required` even with another provider configured.

**Decision**: `skills/deprecated/_shared/llm.py` resolves the LLM in this order: agent env
vars → project `.env` → per-provider key detection → default
`gemini/gemini-2.5-flash`. Every skill uses `build_crew_llm()`.

**Consequences**: The skills work with the host agent's LLM (Hermes or Claude)
without code changes. `_shared` must be propagated to the **root** of each
agent's skills, not to the category.

---

## ADR-0004 — Communication between skills via subprocess + files

**Date**: before 2026-08-18 · **Status**: Accepted

**Context**: The orchestrator needs to trigger 14 other skills.

**Decision**: Triggering via `subprocess.run` with an argument list (no
`shell=True`), passing context by file (`_ctx_<phase>.txt`) and receiving
artifacts in `outputs/pipeline_<timestamp>/`.

**Consequences**: Each skill remains self-contained and independently
installable, and a skill that hangs does not bring down the orchestrator (600s
timeout per phase). In exchange, the CLI contract becomes implicit coupling —
hence the `invoke` metadata (and DT-03, which proposes validating it
automatically).

---

## ADR-0005 — Installation by destructive copy

**Date**: before 2026-08-18 · **Status**: Accepted

**Context**: Installed copies diverged from the repository when edited at the
destination.

**Decision**: `install.sh` does `rm -rf "$dst"` before copying; `__pycache__/`
and `outputs/` are removed from the destination after the copy.

**Consequences**: The install is always a faithful mirror of the repository and
local edits are discarded by design. Risk: pointing `HERMES_SKILLS_DIR`/
`CLAUDE_SKILLS_DIR` at a directory with its own content erases that content.

---

## ADR-0006 — Mode auto-detection instead of an optional flag

**Date**: before 2026-08-18 · **Status**: Accepted

**Context**: Alternative skill modes controlled by an optional flag with
`default=False` were never triggered — the LLM calls the skill via function
calling and decides the parameters itself, without "remembering" the flag.

**Decision**: The correct mode is **detected** from the input content, not
declared by a flag.

**Consequences**: Skills work without extra instruction to the LLM. Requires
explicit, tested detection heuristics — and a clear fallback, to avoid falling
into a generic template without a signal that detection failed.

---

## ADR-0007 — All cp-* skills moved to `skills/deprecated/` (deprecated mode)

**Date**: 2026-10-04 · **Status**: Accepted

**Context**: The 15 `cp-*` skills were the active product of the repository, but
the whole `cp-*` pipeline is being retired. Keeping them at the top of `skills/`
made `install.sh` and the test suite treat them as the current, installable
skills — the default `./scripts/install.sh` propagated them and `skills/cp-*`
glob was the implicit "the skills" location.

**Decision**: Every `cp-*` directory (and the `_shared` helper, which is not a
skill but is imported by all of them via the relative path
`.../scripts/run.py → parent³`) was moved with `git mv` into
`skills/deprecated/`. The skills are in **deprecated mode**: `install.sh`
installs **nothing** by default and only propagates them when given the explicit
`--deprecated` flag.

**Consequences**:

- `skills/` now contains a single subdirectory, `deprecated/`. The relative
  resolution (`parent³ = skills/deprecated`) is preserved because `_shared` moved
  together, so no skill had to change its imports.
- The test suite and `scripts/chat.py` point at `skills/deprecated/`
  (`tests/conftest.py`, `scripts/chat.py`).
- `install.sh` gained the `--deprecated` flag and a no-op default guard; the
  smoke test was split to assert both the no-op default and the opt-in listing.
- The skills are kept for historical reference; they are no longer an active
  pipeline. See `.context/docs/01-inception/vision-and-scope.md`.

---

## ADR-0008 — New active family: RUP skills under `skills/rup/`

**Date**: 2026-10-04 · **Status**: Accepted

**Context**: With the `cp-*` family retired (ADR-0007), the repository needed an
active skill family. The specification `~/Downloads/especificacao_agentes_rup.md`
defines a complete RUP agent team, strictly grounded in Kruchten's *The Rational
Unified Process: An Introduction* (3rd ed.): 9 disciplines, 1 orchestrator
(`RUP-Orchestrator`, base role Project Manager) and 20 specialized agents.

**Decision**: Create the **RUP family** under `skills/rup/` as the active family,
one skill per discipline (9 skills total):

- `rup-orchestrator` (governance + dispatcher)
- 8 discipline skills: `rup-environment`, `rup-business-modeling`,
  `rup-requirements`, `rup-analysis-design`, `rup-implementation`, `rup-test`,
  `rup-ccm`, `rup-deployment`.

Each skill follows the repository convention: `SKILL.md` + `scripts/run.py`
(self-contained CrewAI crew, agents embedded inline) + `references/` (agent →
artifact mapping, or the lifecycle for the orchestrator). The orchestrator
dispatches a discipline by running its `scripts/run.py` via `subprocess`
(same communication pattern as the deprecated orchestrator, ADR-0004).

**Consequences**:

- `install.sh` now installs the **active `rup` family by default**; the
  deprecated `cp-*` family requires `--deprecated` (both can be combined).
- `_shared/llm.py` is duplicated into `skills/rup/_shared/` (it is not a skill
  and is imported by every skill via the relative path
  `.../scripts/run.py → parent³ = skills/rup/`), keeping the two families
  independently installable.
- The test suite gained `tests/test_rup_smoke.py` (help/dry-run/exit codes,
  orchestrator registry == discipline skills); `tests/conftest.py` exposes
  `RUP_SKILLS_DIR`, `rup_skill_names()`, `rup_skill_script()`.
- Shared CLI across the family: `run.py "<briefing>" [--phase P] [--input F]
  [--output F] [--dry-run]`, plus `--discipline`/`--auto`/`--list` on the
  orchestrator. Provider-agnostic; exit codes 0/1/2/3 as the rest of the repo.
- Provenance: generated from the RUP specification; the family README and each
  `references/agents.md` record the discipline → agent → artifact mapping.

---

## ADR-0009 — Software Sizing & Effort Estimation (Use Case Points) in the orchestrator

**Date**: 2026-10-04 · **Status**: Accepted

**Context**: The RUP specification was updated to add, under the
`RUP-Orchestrator`'s strict responsibility, the artifact **Software Sizing &
Effort Estimation**: Function Point Analysis (FPA / IFPUG and NESMA), **Use Case
Points** (UCP: UAW/UUCW/UUCP, TCF/EF), and parametric estimates (COCOMO II,
SLOC/KLOC). The artifact feeds the Measurement Plan/Database and the Iteration
Plan, and matures across phases: preliminary/indicative in Inception (§3.1) and
baselined in Elaboration (§3.2).

**Decision**: Implement the **Use Case Points** calculation as a deterministic,
pure-Python function in `rup-orchestrator/scripts/run.py` (`compute_ucp`),
exposed through the CLI so it runs with **no LLM and no crewai**:

- `--estimate [--sizing <file>] [--json]` — compute UCP from a JSON sizing model
  (actors, use cases, TCF/EF factors, productivity h).
- `--sizing-template` — print an empty sizing model to fill in.
- `--list` was moved before `require_crewai()` so these deterministic commands
  never need the library or a credential.

The LLM-produced artifacts (FPA, COCOMO II/SLOC) remain part of the governance
Task; UCP is computed exactly in code because it is a deterministic formula.

**Consequences**:

- The neutral convention: **empty TCF/EF maps mean exactly neutral** (TCF = EF =
  1.0), and missing individual factors default to their mid-point (T = 2, F = 3).
- New reference `rup-orchestrator/references/sizing-estimation.md` documents the
  formulas, the 13 TCF and 8 EF factors, and a worked example
  (UUCP=185 → UCP=185 → 3700 h @ 20 h/UCP).
- Tests added in `tests/test_rup_smoke.py`: hand-calculated UCP match, neutral
  empty-factor behavior, and CLI `--estimate`/`--sizing-template` without an LLM.
- SKILL/docs updated (orchestrator SKILL.md, `skills/rup/README.md`,
  `docs/SKILLS.md`, `docs/ARCHITECTURE.md`).
