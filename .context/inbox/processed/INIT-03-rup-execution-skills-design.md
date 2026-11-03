# [Done] INIT-03 — RUP execution skills: replace the superpowers plugin

**Type**: initiative · **Status**: implemented (ADR-0013) · **Raised**: 2026-11-03
**Reviewed**: independent builder check done; its 7 open points resolved below and marked *(my call)*
**Approach chosen**: B (keep the 9 document skills, add focused execution skills)

## 1. Intent and why

The owner uses the *superpowers* plugin for the whole development cycle —
discovering what to build, planning, executing, TDD, debugging, verification,
code review and git hygiene — and wants the **RUP family of this repository to
cover all of it**, so that the plugin is no longer needed.

Why: superpowers' documentation is not organized enough for the owner to follow
what is happening, and it writes outside `.context/` (`docs/superpowers/...`).
The owner wants the **state of the work to be readable in `.context/`**:

- epics, stories and tasks as well-defined cards;
- a roadmap of **releases → iterations → epics**, planned inside `.context/`;
- cards **moving between columns (folders)** as execution happens;
- **tests that add value** — never `assert True`, never tests of invented behavior;
- safe use in projects that already have documentation (`.specs`, `.doc`,
  `docs/`, or a non-standard `.context/`): ask before creating/updating `.context/`.

## 2. Goals

| ID | Goal |
|----|------|
| G1 | Cards for **epic → story → task** (+ bug), with a fixed, validated structure and parent links, traceable to the RUP artifacts they come from |
| G2 | **Roadmap**: releases contain iterations, iterations contain epics; a generated view shows progress |
| G3 | Cards **move between kanban columns by command** as work progresses; every move is recorded in the card and in a log |
| G4 | Procedural skills that **conduct the work**: discovery conversation, decomposition/plan, TDD execution, debugging, review, git hygiene |
| G5 | **Valuable tests**: every test is linked to an acceptance criterion of a story, written before the code (red first), and checked for trivial/empty assertions |
| G6 | **Brownfield safety**: detect existing documentation, **ask authorization** before creating or updating `.context/`, upgrade non-destructively, import existing docs into `.context/` |
| G7 | Works in **Claude Code and Hermes**; same model as today (the agent is the LLM, ADR-0012); standard library only |

## 3. Non-goals

- **Proof-gated moves.** A card advances when the agent *declares* the step is
  done (owner's decision). No test run is required to move a card.
- Running the target project's test suite from the skills (the agent runs it).
- Rewriting the 9 RUP document skills (they gain only the small hooks listed in §7.12).
- Trello or any external board sync.
- Uninstalling superpowers — the owner does that once satisfied.
- Parallel-agent orchestration (the host agent decides how to parallelize).

## 4. Anti-goals (failure even if it "works")

- Documentation scattered outside `.context/`.
- Any skill creating or changing `.context/` **without the user's authorization**.
- Tests not linked to an acceptance criterion, or trivially true.
- Long, multi-purpose `SKILL.md` files the owner cannot follow.
- Any LLM client, API key or third-party runtime dependency (ADR-0012).
- Destroying or overwriting existing content (curated docs, imported originals).

## 5. Constraints (from the current system)

- ADR-0011: artifacts always persisted into `.context/`; ADR-0012: the host agent
  is the LLM; the skills are deterministic, stdlib-only, tested with `python -S`.
- Protocol pattern already in place: **packet** (read-only, printed for the agent)
  → **document** written by the agent → **`--record`** (validates, writes,
  logs). New skills reuse it.
- `_shared/` holds behavior (`rup.py`, `discipline.py`, `context.py`); each skill's
  `run.py` finds `_shared/` next to the skill or one level up (Hermes).
- Exit codes today: 0 ok · 1 usage/invalid document · 4 `.context/` not writable.
- Kanban columns already exist: `1-backlog`, `2-todo`, `3-doing`, `4-review`,
  `5-testing`, `6-staging`, `7-done`, `blocked` (card = `.md` with frontmatter,
  column = folder). Nothing moves cards today (`cp-agile` was removed).
- Curated `.context/docs/` files are never overwritten; generated ones are `rup-*`.
- Tests point `RUP_CONTEXT_DIR` at temp dirs; never write into this repo's `.context/`.

## 6. Approaches considered

| | Approach | Trade-off | Decision |
|-|----------|-----------|----------|
| A | Extend the 9 existing skills (requirements gets discovery, implementation gets TDD, ccm gets debug/review/git, orchestrator gets roadmap) | Stays at 9 skills, but each skill mixes "produce a RUP document" with "conduct work": long `SKILL.md`, weaker triggering — the very illegibility the owner complains about | Rejected |
| **B** | **Keep the 9 document skills; add a few focused execution skills in the same family** | ~15 skills instead of 9, but each is short, single-purpose, with a precise trigger (what makes superpowers fire at the right time); the tested document skills stay untouched | **Chosen** |
| C | One `rup` skill with subcommands | One entry point, but a single `SKILL.md` carrying every behavior triggers poorly and is hard to read | Rejected |

## 7. Design (decided)

### 7.1 New skills

| Skill | Replaces (superpowers) | Purpose |
|-------|------------------------|---------|
| `rup-context` | — (new need) | Detect, **ask authorization**, initialize/upgrade `.context/`, import existing docs, add the agent pointer note |
| `rup-discover` | brainstorming | Conversation before building: one question at a time, play back, then record Vision/Requirements into `.context/` |
| `rup-backlog` | writing-plans | Epics/stories/tasks, releases/iterations, **move** cards, generate roadmap and board views |
| `rup-build` | executing-plans, test-driven-development, verification-before-completion, using-git-worktrees | Execute one task with TDD; record delivery (incl. test↔criterion map) |
| `rup-debug` | systematic-debugging | Bug card + root-cause protocol; regression test before the fix |
| `rup-review` | requesting/receiving-code-review, finishing-a-development-branch | Review checklist for cards in `4-review`; branch integration steps on the way to `7-done` |

Each follows the existing protocol (packet → document → record) where the agent
writes content, and plain commands where the skill only changes state (e.g.
`move`). Each `SKILL.md` is short: when to use, the 2–4 steps, the commands.

### 7.2 `.context/` authorization (G6) — changes current behavior

- **Standard marker**: `.context/.rup-standard` (version of the standard,
  date and who authorized). Its presence = authorized.
- **Every writing command of every skill** (all `--record`, card creation,
  `move`, roadmap generation) checks the marker. If missing it **writes nothing**
  and exits with a **new code 5**, printing for the agent: *what was found*
  (no `.context/`; a `.context/` that does not follow the standard; other doc
  dirs such as `.specs`, `.doc`, `docs/`), *what would be created/changed*, and
  the instruction **"ask the user; on approval run `rup-context --init`"**.
- Read-only packets still work without the marker, with a warning line.
- `rup-context --init` (run only after the user approved) creates or upgrades:
  it **adds** missing folders/files of the standard tree and never deletes or
  overwrites existing files; it writes the marker.
- This replaces the current silent creation in `context.py` (ADR-0011 mechanics
  amended; a new ADR records it).
- **The standard tree** *(my call)* = this repository's layout plus `roadmap/`:
  `docs/01-inception/{vision-and-scope,requirements}.md`,
  `docs/02-elaboration/{architecture,domain-model}.md`,
  `docs/03-construction/{api-contracts,ui-spec,data-dictionary}.md`,
  `docs/04-transition/{test-strategy,devops-infra}.md`,
  `inbox/{initiatives,tasks,bugs,tech-debt,processed}/`,
  `kanban/{1-backlog,…,7-done,blocked}/` + `kanban/README.md`, `roadmap/`,
  `tracking/{progress,decisions}.md`, `README.md`. `--init` creates **skeletons
  only for missing files** (headings + "to be filled" note) and missing folders.
- "Non-standard" *(my call)* simply means **no marker**: any `.context/` without
  `.rup-standard` — including one the ADR-0011 skills already wrote to, and
  this repository's own — needs one authorized `--init` before any skill writes
  again. This follows the owner's rule that an existing `.context/` must not be
  changed without authorization; it is a one-time step per project.

### 7.3 Importing existing documentation (G6) — owner's choice: bring into `.context/`

- `rup-context --import` prints an **import packet**: inventory of the existing
  doc dirs/files and the standard target for each (vision, requirements,
  architecture, contracts, data, tests, devops).
- The agent writes one import document; `rup-context --record-import` validates
  it (one `## <target file>` section per inventory target) and writes it
  *(my call, honoring "never overwrite")*: a **missing** standard file is created
  with the section's content; an **existing** curated file is never rewritten —
  the content is **appended** inside a delimited block
  `<!-- rup-import source="…" date="…" --> … <!-- /rup-import -->`, leaving
  every existing line untouched. Each block carries the **source link**.
- **Originals are never moved, changed or deleted.** Retiring them is the user's call.
- The import is recorded in `tracking/rup-log.md`.

### 7.4 Cards (G1)

- Types and IDs: `EP-NNN` (epic), `ST-NNN` (story), `TK-NNN` (task), `BUG-NNN`.
  IDs are assigned by the skill, never by the agent.
- One file per card in its column folder: `.context/kanban/<column>/<ID>.md`,
  frontmatter + fixed sections. Common frontmatter: `id`, `type`, `title`,
  `status` (always equal to the folder), `parent`, `priority` (MoSCoW),
  `source` (RUP artifact path + section), `created_at`, `updated_at`.
  Epics also carry `release` and `iteration`; stories/tasks inherit them.
- Required sections, validated on record (same mechanism as today's
  `## <Artifact>` check):
  - **Epic**: Goal, Scope, Stories (generated list of children).
  - **Story**: User story ("As a … I want … so that …"), **Acceptance criteria**
    with stable IDs `ST-NNN/AC-n`, Definition of Done.
  - **Task**: Description, Target files, **Covers** (list of `ST-NNN/AC-n`),
    and, filled at completion, **Delivery** (what was done, files changed,
    tests → criteria map, red evidence).
  - **Bug**: Symptom, Reproduction, Root cause, Fix, Regression test.
- **Origin**: `rup-backlog` can derive epics/stories from the recorded RUP
  artifacts (use-case packages → epics, use cases → stories) via a packet that
  embeds `rup-requirements`'s artifact; tasks come from decomposing a story.
- **Re-deriving** after the requirements change *(my call)*: only **adds** cards
  for use cases/packages not yet covered (matched by `source`); existing cards
  are never modified — the packet lists the differences (new, removed, changed
  sources) for the agent to handle by hand.
- Every move appends to the card's **History** section:
  `<timestamp> <from> → <to> — <reason>`, and a row to `tracking/rup-log.md`.

### 7.5 Roadmap (G2)

- Releases and iterations are small files under `.context/roadmap/`:
  `R<n>.md` (id, title, milestone, goal, optional target date) and
  `R<n>-I<m>.md` (id, release, **RUP phase**, goal, optional dates).
- An epic is planned by setting its `iteration` (command in `rup-backlog`).
- **The roadmap is a generated view, never hand-edited**: `rup-backlog --roadmap`
  writes `.context/docs/06-roadmap.md` (releases → iterations → epics → story
  progress) and `.context/docs/06-board.md` (board by column). Both are
  regenerated after every move. *(My call)* the existing curated
  `06-kanban.md` is **not** touched — generated views get their own files.
- The orchestrator's Iteration Plan points at the iteration file; allocation of
  epics to iterations happens through `rup-backlog`.

### 7.6 Moving cards (G3)

- `rup-backlog --move <ID> <column> --reason "<text>"`. **Declaration is
  enough** (owner's decision): no proof is required to move.
- The move updates `status`, `updated_at`, the History section, moves the file
  between folders, logs it, and regenerates the views.
- `rup-build`/`rup-review`/`rup-debug` call the same move logic at their
  natural transitions (start → `3-doing`, finish → `4-review`, review approved →
  `5-testing`/back to `3-doing`, etc.).
- **Any move is legal** *(my call, consistent with "declaration is enough")*;
  a jump that skips columns prints a warning in the History line, never blocks.
- `5-testing` → `6-staging` → `7-done` *(my call)*: plain `--move` with a reason
  (the agent or the user declares it); `rup-review`'s checklist lists the branch
  integration steps for the move to `7-done`. No dedicated command.
- **Roll-up of parents** *(my call)*: stories and epics also live in the columns
  and move **automatically**: a story goes to `3-doing` when its first task
  does, and to `7-done` when all its tasks are in `7-done` (same for an epic and
  its stories). A manual `--move` of a story/epic is still allowed. Roadmap
  progress = share of children in `7-done`.

### 7.7 Executing a task with TDD (G4, G5)

- `rup-build --start TK-NNN` moves the task to `3-doing` and prints the
  **execution packet**: the task, its story and acceptance criteria, target
  files, the RUP context, a suggested branch name (`tk-nnn-<slug>`), and the
  rules: write the test first; each test names the criterion it covers
  (`ST-NNN/AC-n` in the test name, docstring or a comment on the test); run it
  and see it fail; implement; run it and see it pass.
- `rup-build --finish TK-NNN --delivery <file|->` records the **Delivery**
  section and moves the card to `4-review`. Before accepting, it **checks the
  tests listed in the delivery** (this is the test brake, not a move gate):
  - each listed test exists in the named file;
  - each references a criterion ID that exists in the parent story;
  - every criterion in the task's *Covers* list has at least one test;
  - no trivial test: no assertion at all, only constant assertions
    (`assert True`, `assert 1 == 1`, `expect(true).toBe(true)`, …), or a body
    that never calls code from the project;
  - a **red evidence** excerpt (the failing output the agent saw) is present
    per test (declarative, consistent with G3).
  If any check fails, nothing is recorded and the list of problems is printed.
- Git: the skills **do not run git** (no subprocess to git); the packets tell
  the agent what to do (branch per task, commit per green step) and the card
  records the branch name.

### 7.7b Discovery (G4) *(my call)*

`rup-discover "<idea>"` prints the conversation protocol (one question at a
time, play back each part, ask what is wrong or missing). It records **its own
artifact**, `docs/01-inception/rup-discover.md`, with required sections:
Problem, Users, Goals, Non-goals, Anti-goals, Constraints, Open questions. It
does not write `rup-requirements.md` (avoids two skills overwriting each other).
The chain continues through the existing skills: `rup-discover.md` is embedded
in the `rup-requirements` packet (see §7.12), whose recorded artifact
(use cases) is what `rup-backlog` derives epics/stories from.

### 7.8 Debugging (G4)

`rup-debug --open "<symptom>"` creates a `BUG-NNN` card (parent story if
known) and prints the protocol: reproduce → write a failing regression test →
find and **record the root cause** → fix → finish via `rup-build --finish`
(same test checks; the regression test must reference the bug ID).

### 7.9 Review and finishing (G4)

`rup-review TK-NNN` prints a checklist packet (criteria covered, delivery vs
target files, tests checks summary, traceability to RUP artifacts, branch
integration steps). The agent records a **Review** section with a verdict:
approved → next column; changes requested → back to `3-doing` with the reasons.

### 7.10 Triggering (replaces the superpowers session hook)

On `rup-context --init` (same authorization), the skill **adds a short pointer
note** to the project's `CLAUDE.md`/`AGENT.md` (creating them if absent, never
replacing existing text) listing which RUP skill to use for which moment. This
works for both Claude Code and Hermes; no hook is installed.

### 7.12 Changes to the existing 9 skills *(my call — the complete list)*

1. The marker check (§7.2) lives in `_shared/context.py`, so every existing
   `--record` and `--estimate` gets it without code changes in the skills.
2. `_shared/discipline.py` `prior_artifacts()` also embeds `rup-discover.md`
   (first, before governance) in every packet of the phase.
3. The orchestrator's governance packet gains one instruction: allocate epics to
   iterations with `rup-backlog` and reference the iteration file in the
   Iteration Plan. The orchestrator does not create or read roadmap files itself.
4. No document skill creates cards.

## 8. Testing approach

Same style as today: stdlib, no LLM, temp `RUP_CONTEXT_DIR`, `python -S` for
every new skill, end-to-end flows with fixed documents (card creation, moves,
roadmap regeneration, start/finish with good and bad tests, consent refusal
with exit 5, non-destructive init/upgrade, import leaving originals untouched).

## 9. Left to the builder

- Exact CLI flag names and help texts (keep the existing style).
- The frontmatter subset and its stdlib parser/writer (flat keys + simple lists).
- Trivial-test heuristics per language: precise for Python (`ast`), pattern-based
  for others; the list of supported languages for the first version.
- Exact wording of packets and `SKILL.md` files (short, step-based).
- File layout details of the generated views.
- Migration of existing cards that use the old `task|bug|tech-debt|initiative` schema.
