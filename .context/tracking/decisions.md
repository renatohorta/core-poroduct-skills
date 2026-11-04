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

---

## ADR-0013 — Execution skills, authorization gate, cards and roadmap in `.context/`

**Date**: 2026-11-03 · **Status**: Accepted — amends ADR-0011 (silent creation of `.context/`); extends ADR-0012 (same protocol, host agent is the LLM)

**Context**: The owner ran the whole development cycle (discovery, planning,
TDD, debugging, review, git hygiene) with the *superpowers* plugin. Its
documentation is hard to follow and it writes outside `.context/`
(`docs/superpowers/...`). The owner wants the state of the work readable in
`.context/` (epics, stories, tasks, a roadmap, cards that move between columns)
and tests that prove something. Separately, ADR-0011 created `.context/` and
wrote into it silently, which is unsafe in projects that already have
documentation (`.specs`, `.doc`, `docs/`, a non-standard `.context/`).
Design: `INIT-03-rup-execution-skills-design.md` (approach B: keep the 9
document skills, add focused execution skills).

**Decision**:

- **Authorization gate (amends ADR-0011).** A `.context/` is authorized when it
  holds the marker `.context/.rup-standard` (version, who, when). Every writing
  command of every skill checks it in `_shared/context.py`; without it nothing
  is written and the skill exits with the new code **5**, printing what was
  found, what would change and "ask the user; on approval run
  `rup-context --init`". Read-only packets still work, with a warning. Any
  `.context/` without the marker counts as non-standard, including this
  repository's own: one authorized `--init` per project.
- **`rup-context`**: `--status` (read-only), `--init --authorized-by "<who>"`
  (adds missing folders and skeleton files, the marker, and a RUP pointer block
  in `CLAUDE.md`/`AGENT.md`; never overwrites or deletes), `--import` /
  `--record-import` (existing docs are appended in `<!-- rup-import -->` blocks
  or create missing files; originals untouched).
- **Six execution skills** replace the plugin: `rup-context`, `rup-discover`
  (conversation, records `rup-discover.md`, embedded first in later packets),
  `rup-backlog` (cards, moves, roadmap, views), `rup-build` (TDD start/finish),
  `rup-debug` (bug cards, root cause before fix), `rup-review` (checklist and
  verdict). They reuse the packet -> document -> record protocol or plain
  state-changing commands. The 9 document skills are unchanged except for the
  marker check (shared code), `rup-discover.md` in `prior_artifacts()` and one
  governance instruction (allocate epics to iterations with `rup-backlog`).
- **Cards**: `EP-NNN`, `ST-NNN`, `TK-NNN`, `BUG-NNN`, IDs assigned by the skill,
  one file per card in `.context/kanban/<column>/<ID>.md`, frontmatter + fixed
  sections validated on creation, `## History` always last. Acceptance criteria
  get stable IDs `ST-NNN/AC-n`; a task's `## Covers` references them; stories
  and epics roll up automatically. Derivation from `rup-requirements` only adds
  cards.
- **Roadmap**: `.context/roadmap/R<n>.md` (releases) and `R<n>-I<m>.md`
  (iterations, with a RUP phase); epics are planned into iterations. Generated
  views `docs/06-roadmap.md` and `docs/06-board.md` are rewritten after every
  change and never hand-edited; the curated `06-kanban.md` is left alone.
- **Declaration-based moves**: `--move ID COLUMN --reason` is enough, any move
  is legal, a skipped column only warns in History. No proof is required.
- **Test-value checks** (`rup-build --finish`): the tests listed in the delivery
  must exist, reference a criterion of the parent story (or the bug ID), cover
  every `Covers` criterion, assert something non-constant, call project code and
  carry red evidence. Python is analysed with `ast`, JS/TS by pattern, other
  languages by name only. A failure records nothing (exit 1).
- **No git, no test runs in the skills.** Packets tell the agent which branch
  and commits to make; the card records the branch.
- **Triggering** replaces the superpowers session hook: the pointer block added
  by `--init`, no hook installed (works in Claude Code and Hermes).

**Consequences**:

- Exit code 5 joins 0/1/4. Every project, including this repository, needs one
  authorized `rup-context --init` before skills write again.
- 15 skills (9 document + 6 execution) plus `_shared` (adds `consent.py`,
  `frontmatter.py`, `cards.py`, `roadmap.py`, `testcheck*.py`); still stdlib
  only and tested with `python -S`. Suite: 268 passed.
- Old card schema (`TASK-NNN`, `task|bug|tech-debt|initiative`) is superseded;
  existing cards are not migrated automatically.
- Test checks are a brake on declared tests, not proof that they ran or pass.
- Uninstalling the superpowers plugin remains the owner's call.

---

## ADR-0014 — RUP skills renamed from `rup-*` to `cp-*`

**Date**: 2026-11-03 · **Status**: Accepted

**Context**: The owner asked for every skill to use the `cp-` prefix (Core
Product) instead of `rup-`. The prefix was already used by the legacy Software
Factory family removed in ADR-0010; those skills only exist in the git history,
so the names are free again.

**Decision**: Rename all 15 skills (`skills/rup-<name>` → `skills/cp-<name>`,
`git mv`) and every reference to their names: `SKILL.md` frontmatter, the
registry in `_shared/rup.py`, generated artifact names
(`.context/docs/<NN-phase>/cp-<skill>.md`, `cp-orchestrator-sizing.md`),
derivation sources (`cp-requirements#<heading>`), the pointer note, docs and
tests. Internal identifiers that are not skill names keep their names: the
marker `.context/.rup-standard`, the log `tracking/rup-log.md`, the
`<!-- rup-import -->` / `<!-- rup-skills:… -->` markers, `RUP_CONTEXT_DIR`,
`RUP_SKILLS_PYTHON` and the module `_shared/rup.py` (they name the RUP method,
not a skill). Historical records (ADR-0001…0013, `inbox/processed/`,
`translation-map.md`) are not rewritten.

**Consequences**:

- Agents must invoke `cp-orchestrator`, `cp-context`, `cp-backlog`, etc.;
  reinstall with `./scripts/install.sh` (old `rup-*` installed copies, if any,
  must be removed by hand — `install.sh` never deletes other skills).
- Artifacts recorded before the rename (`rup-<skill>.md`) are not migrated.
- Older ADRs mention `cp-*` meaning the legacy Software Factory; from ADR-0014
  on, `cp-*` means the RUP skills.

---

## ADR-0015 — Root `docs/` removed; `.context/` is the only documentation

**Date**: 2026-11-03 · **Status**: Accepted

**Context**: The repository kept two documentation trees: `.context/` (source
of truth for agents, ADR-0001) and a root `docs/` (`ARCHITECTURE.md`,
`INSTALLATION.md`, `SKILLS.md`) as a human-facing presentation copy. Every
change had to be written twice, and the copies drifted.

**Decision**: Delete the root `docs/`. `.context/` is the only documentation
of the project; the human entry points are `README.md` (overview, install,
tests) and `skills/README.md` + each `SKILL.md` (catalog). The content of the
removed files already lived in `.context/docs/02-elaboration/architecture.md`,
`.context/docs/04-transition/devops-infra.md` and the skill READMEs.

**Consequences**: Links now point into `.context/docs/`. `cp-context --status`
no longer reports `docs` as another documentation directory in this repository.
The removed files remain in the git history.

---

## ADR-0016 — cp-test measures the value of the tests (mutation testing)

**Date**: 2026-11-04 · **Status**: Accepted

**Context**: In a real project (Django + DRF, 577 tests), the cp-test packet asked
for the RUP test artifacts but never for measured numbers, and had no way to
answer "are our tests worth anything?". Line coverage was 96%; a mutation run
done by hand outside the skills scored 76%, with whole modules under 50%, and
an independent review found 12 real defects with the suite green. The scripts
were improvised (`MELHORIAS-cp-testes.md`).

**Decision**:

- The cp-test packet demands measured evidence (command, SHA, duration, result
  for every execution) and a new Test Manager artifact, **Test Value
  Assessment**. It embeds `.context/tests/{baseline,static-audit}.md` and
  `tests/mutation/{report,triage}.md` when they exist.
- `cp-test --audit` prints the protocol A0–A8 (profile, baseline, inventory,
  static audit, module choice, mutation, triage, action, record).
- Deterministic tools in `_shared/mutation.py` and `_shared/testaudit.py`
  (stdlib): Python AST mutants; a parallel, resumable runner in disposable copies
  of the project; per-module report; triage table checked against fixed rules
  (equivalent / real gap / dead code / out of scope, each with a reason; real gap
  → card; dead code → CR).
- **Exception to "the skills never run the project's tests"**: `cp-test --mutate`
  runs the suite command the agent wrote in `.context/tests/profile.json`, only in
  copies (the original is never written). Git is still never run: the SHA is read
  from `.git`. The run fingerprints every non-test file and refuses to continue
  if the code under test changed (test files may change: that is how a gap is
  closed, re-running the survivors).
- cp-build asks for mutation of the changed lines (`## Mutation` in the
  delivery; its absence is a warning, not a rejection); cp-review shows it and
  recommends an adversarial review; cp-debug requires the fix's mutants to die;
  the orchestrator routes test-value demands to `--audit` and adds the mutation
  score to the Measurement Plan.

**Consequences**: Mutation can take hours: `--budget` and resume, `--mutation-status`.
Non-Python projects use their ecosystem tool (Stryker, PIT, go-mutesting,
cargo-mutants) with the same protocol and JSONL format. The `## Mutation`
warning in cp-build can become a gate later. Items P1, P2, P3 and P5 of the
source document (record overwrites a phase, commit hint, `--init` summary,
estimate × actual) are not part of this decision.

## ADR-0017 — cp-orchestrator is the front door: the agent routes, the user never names a skill

**Date**: 2026-11-04 · **Status**: Accepted

**Context**: The team guide showed that a user had to know and call each skill
by name (`cp-discover` for discovery, `cp-requirements` for requirements, …).
The orchestrator only knew governance and the 8 disciplines; it did not know
the execution skills (discover, backlog, build, debug, review, test audit) and
did not route a plain request.

**Decision**:
- `cp-orchestrator --route "<request>"` prints a read-only routing packet: the
  request, the project state read from `.context/` (authorization, discovery,
  requirements, governance, board per column, open bugs), a suggested next step,
  every route with its exact command, the standard chains and the gates.
- Classification stays with the agent (ADR-0012): no keyword matching in code.
  The code only reads state and suggests, in this order: authorize → review →
  finish what is in 3-doing → open bugs → discover → requirements → derive the
  backlog → build what is in 2-todo → plan the backlog → ask the user.
- The agent runs the chain itself and stops only at the gates: authorizing
  `.context/`, the discovery conversation, confirming derived cards, a real
  ambiguity (one question), destructive or outward-facing actions. It never
  answers "call cp-xxx".
- The orchestrator SKILL.md description says it is the front door for any
  project request; the pointer note in CLAUDE.md / AGENT.md starts with the
  `--route` line, and `cp-context --init` refreshes an outdated pointer block
  between its markers (text outside the markers is never touched).

**Consequences**: The other skills keep working when called directly. Projects
initialized before this decision get the new pointer note by running
`cp-context --init` again (it only adds what is missing, plus the refresh).

