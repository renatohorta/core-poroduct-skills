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

**Date**: before 2026-08-18 · **Status**: Superseded by ADR-0010 (the `cp-*` family was removed)

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

**Date**: before 2026-08-18 · **Status**: Superseded by ADR-0012 (no LLM client in the skills)

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

**Date**: before 2026-08-18 · **Status**: Superseded by ADR-0010 (applied to the removed `cp-*` family)

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

**Date**: 2026-10-04 · **Status**: Superseded by ADR-0010

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

**Date**: 2026-10-04 · **Status**: Accepted — layout (`skills/rup/`) amended by ADR-0010

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

---

## ADR-0010 — `cp-*` family removed; RUP skills flattened into `skills/`

**Date**: 2026-11-03 · **Status**: Accepted

**Context**: After ADR-0007/0008 the repository kept two families: the retired
`cp-*` skills under `skills/deprecated/` and the active RUP skills under
`skills/rup/`, each with its own copy of `_shared/`. The deprecated family was
dead weight — tests, `chat.py`, CI and docs still revolved around it — and the
extra `rup/` level only existed to separate the two. A review of the RUP family
also found defects: `--auto` wrote every discipline to the same `--output` (only
the last survived) and passed only the original briefing (no traceability
between disciplines); the governance prompt told the agent to use `compute_ucp`
without giving it any way to call it; `--dry-run` required crewai; `install.sh`
listed skills with GNU-only `find -printf` (nothing on macOS); installed skills
could not find `_shared` in Hermes' `skills/<category>/` layout; CI only ran on
pushes to `master` (the branch is `main`).

**Decision**:

- Delete `skills/deprecated/` (all `cp-*` skills and their `_shared`). They stay
  in the git history up to commit `6490694`.
- Move `skills/rup/*` to `skills/` (`skills/rup-*`, `skills/_shared/`,
  `skills/README.md`). `install.sh` installs every `skills/*` dir that has a
  `SKILL.md`; the `--deprecated` flag is gone.
- Each `run.py` looks for `_shared/` next to the skill and one level up, so the
  same copy works in the repo, in Claude Code (flat) and in Hermes (category).
- `--auto` chains the disciplines: each receives the briefing plus the earlier
  artifacts (`--input`, capped at 12 000 chars each), writes its own file
  (`<stem>.NN-<key>.md`) and the run stops at the first failure.
- The governance agent gets the `use_case_points_calculator` CrewAI tool
  (wrapping `compute_ucp`, with input validation); the task orders it to call
  the tool instead of computing by hand.
- `--dry-run` works without crewai (lists the planned agents); unreadable
  `--input` and invalid sizing models exit 1; `--output` creates parent dirs.
- CI triggers on `main`; `chat.py` targets the `rup-*` skills.

**Consequences**:

- The suite dropped the `cp-*` tests (contract `invoke`, quality gate, internal
  units, kanban flow) and gained coverage for the items above: 108 tests, no
  credentials. `tests/test_rup_smoke.py` became `tests/test_smoke.py`;
  `conftest.SKILLS_DIR` is `skills/`.
- The `.context/kanban/` flow is manual — the `cp-agile` daemon no longer exists.
- Writing the RUP artifacts into a target project's `.context/` was left open
  here and decided in ADR-0011.

---

## ADR-0011 — RUP artifacts are always persisted into `.context/`

**Date**: 2026-11-03 · **Status**: Accepted — recording mechanics amended by ADR-0012 (`--record`; no crew, no `--output`)

**Context**: The `rup-*` skills only printed their result and, optionally,
wrote it to `--output`. The RUP artifacts (Vision, SRS, SAD, Test Plan, Work
Orders, sizing…) therefore never became part of the project's source of truth,
`.context/` (ADR-0001), unless someone copied them by hand (INIT-02). The owner
decided persistence must be **mandatory**, not an opt-in flag.

**Decision**:

- Every real run of every `rup-*` skill writes its artifact to
  `.context/docs/<NN-phase>/rup-<skill>.md` — the phase folders already used by
  `.context/docs/` — and appends a row to `.context/tracking/rup-log.md`.
  `--estimate` writes `rup-orchestrator-sizing.md`. `--output` became an extra copy.
- **Naming**: the `rup-` prefix separates generated artifacts from the curated
  docs (`requirements.md`, `architecture.md`, …), which are never overwritten.
- **Policy**: regenerate the file per run and phase, with a provenance
  frontmatter (skill, discipline, phase, milestone, timestamp) and a briefing
  excerpt; history lives in git, the log keeps every write.
- **Which `.context/`**: `--context-dir` > `RUP_CONTEXT_DIR` > nearest
  `.context/` walking up from cwd, stopping at the git root (never escapes the
  repository) > `<git root or cwd>/.context`, created on first write. The
  orchestrator resolves it once and passes `--context-dir` to each child,
  because children run with cwd = the skills root.
- **Fail before paying**: writability is checked before `kickoff()`; failure
  exits with the new code **4** and no LLM call is made.
- `--auto` chains through `.context/`: each discipline receives the body (after
  `## Artifacts`) of the earlier disciplines' `.context/` files.
- Single implementation in `skills/_shared/context.py` (stdlib only).

**Consequences**:

- Running a skill always changes the project's working tree (new/updated
  `rup-*.md` + log). Commit them like any other context change.
- `--dry-run`, `--help`, `--list` and `--sizing-template` write nothing.
- Tests: a fake `crewai` (`tests/fakes/crewai/`) lets the suite run every skill
  end to end without an LLM; `clean_env` points `RUP_CONTEXT_DIR` to a temp dir
  and a guard test fails if anything lands in this repository's `.context/`.
  Suite: 138 passed.

---

## ADR-0012 — The host agent is the LLM; CrewAI, `llm.py`, proxy and chat removed

**Date**: 2026-11-03 · **Status**: Accepted

**Context**: The RUP skills ran CrewAI crews that needed their own LLM. The
agent invoking a skill (Claude Code, Hermes) does not pass its model or
credentials to subprocesses, so the crews had two options: an API key resolved
by `_shared/llm.py` (paid separately; with only `ANTHROPIC_API_KEY` set it still
picked the Gemini default model and failed), or `scripts/claude_proxy.py`
(`claude -p` per call: dropped the assistant turns CrewAI's loop relies on,
ignored `tools` — so the UCP tool could not be called — slow and quota-hungry).
Either way it was a **second** LLM, without the conversation context the agent
already had.

**Decision**: The agent running the skill is the only LLM. The skills became
deterministic, standard-library programs with a two-step protocol:

1. **Work packet** — `run.py "<briefing>" --phase P` prints the roles (goal,
   perspective, mission), the exact required artifacts, RUP rules, the briefing,
   the earlier artifacts recorded in `.context/` (governance + earlier
   disciplines of the phase) and the exact `--record` command.
2. **Record** — `run.py --record FILE|- --phase P` checks that every required
   artifact has a `## <Artifact>` section (else lists them, writes nothing,
   exit 1) and writes `.context/` (ADR-0011).

- Each discipline's `run.py` is now its `SPEC` (roles/missions/artifacts as
  data, extracted verbatim from the former crews) + `_shared/discipline.py`.
- `_shared/rup.py` is the single registry (phases, ordered disciplines, exits).
- Orchestrator: governance packet (with the exact `--sizing-template` /
  `--estimate` commands — UCP is never computed by the model), `--discipline`
  (that skill's packet), `--auto` (iteration protocol, in order), `--status`.
- **Removed**: `crewai` dependency, `_shared/llm.py`, `scripts/claude_proxy.py`
  (and its tests), `scripts/chat.py`, `.env.example`, `--dry-run`, `--output`,
  exit codes 2 and 3.

**Consequences**:

- Same model and context as the conversation; no key, proxy or extra cost;
  real tool use by the host (it runs `--estimate` itself).
- No runtime dependency (tests run the skills with `python -S`); suite from ~50 s
  to ~3 s; the fake crewai is gone — E2E tests record fixed documents.
- The skills can no longer run unattended without an agent (CI, cron): the
  artifacts are written by whoever runs the protocol.
- `--auto` no longer executes anything: it prints the protocol; the agent runs
  the steps in order (each packet embeds the earlier steps' artifacts).
- Security surface shrank: no socket, no credential read (SEC-02 closed).
