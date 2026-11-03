# [Done] RUP Execution Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add six execution skills (`rup-context`, `rup-discover`, `rup-backlog`, `rup-build`, `rup-debug`, `rup-review`) so the RUP family covers the whole development cycle with epics/stories/tasks, a roadmap and card moves inside `.context/`, value-checked tests and an authorization gate.

**Architecture:** Behavior lives in new `skills/_shared/` modules (`consent`, `frontmatter`, `cards`, `roadmap`, `testcheck`); each new skill is a thin `scripts/run.py` CLI plus a short `SKILL.md`, reusing the existing packet → document → record pattern of `_shared/discipline.py`. The host agent is the LLM; scripts are deterministic.

**Tech Stack:** Python 3.10+ standard library only (`ast`, `re`, `pathlib`, `argparse`, `dataclasses`); pytest for tests.

**Spec:** `.context/inbox/initiatives/INIT-03-rup-execution-skills-design.md` (approved 2026-11-03). Read it first.

## Global Constraints

- Standard library only; every skill must run under `python -S` (no site-packages).
- No LLM client, API key, network call, or `git` subprocess in `skills/`.
- Exit codes: `0` ok · `1` usage/invalid document · `4` `.context/` not writable · **`5` needs authorization (new)**.
- Every writing command checks the marker `.context/.rup-standard`; without it: write nothing, exit 5, print what was found, what would change, and "ask the user; on approval run `rup-context --init`".
- Never delete, move or rewrite existing files: curated `.context/docs/*.md`, imported originals, existing `CLAUDE.md`/`AGENT.md` text, `docs/06-kanban.md`.
- Card IDs assigned by the skill: `EP-NNN`, `ST-NNN`, `TK-NNN`, `BUG-NNN` (3 digits, per-type sequence). Acceptance-criterion IDs: `ST-NNN/AC-n`.
- Kanban columns, exactly: `1-backlog`, `2-todo`, `3-doing`, `4-review`, `5-testing`, `6-staging`, `7-done`, `blocked`. Card `status` always equals its folder.
- Generated views: `.context/docs/06-roadmap.md`, `.context/docs/06-board.md`; regenerated after every move/plan change.
- Each new skill: `skills/rup-<name>/{SKILL.md, scripts/run.py, references/<name>.md}`, the same `_shared` bootstrap as `skills/rup-ccm/scripts/run.py`, `setup_console()` in `__main__`.
- `SKILL.md` ≤ ~60 lines: when to use, the 2–4 steps, the commands. Repo docs in English.
- Tests never write into this repository's `.context/` (`RUP_CONTEXT_DIR` → temp dir); suite stays fast (no LLM).

## Review Focus

- A card edited by hand so `status:` disagrees with its folder → the folder wins; any move rewrites `status`. (Test in Task 5.)
- The same card ID present in two folders (hand copy) → every command exits 1 naming both paths; nothing written. (Task 5.)
- `--move` to an unknown column or an unknown ID → exit 1, nothing changed, no log row. (Task 6.)
- A delivery naming a test file that does not exist or lies outside the project root → reported as a problem, never a traceback. (Task 9.)
- Card / document files with Windows CRLF line endings or a BOM → parsed like LF files. (Task 4.)

---

### Task 0: Baseline commit of pending work

**Files:** none new — the working tree holds uncommitted ADR-0011/0012 work and the INIT-03 design.

- [ ] **Step 1:** Run `git status --short` and `.venv/bin/python -m pytest -q`. Expected: 138 passed.
- [ ] **Step 2:** Commit everything as one baseline (`git add -A`), message `feat: host agent is the LLM; mandatory .context persistence (ADR-0011, ADR-0012)` + the INIT-03 design. Do not push.

---

### Task 1: Authorization gate (marker + exit 5)

**Files:**
- Modify: `skills/_shared/rup.py` (add `EXIT_NEEDS_CONSENT = 5`)
- Modify: `skills/_shared/context.py`
- Modify: `tests/conftest.py`, `tests/test_context_persistence.py`
- Test: `tests/test_consent.py`

**Interfaces:**
- Produces (`context.py`): `MARKER = ".rup-standard"`; `has_consent(context_dir) -> bool`; `require_consent(context_dir) -> None` (exits 5 with the message from Global Constraints; message also lists, via `consent.detect` in Task 2 — until then, the plain sentence); `ensure_writable(context_dir, phase=None)` now calls `require_consent` **before** any `mkdir` (phase optional: `None` checks only the context root and `tracking/`).
- Produces (`conftest.py`): fixture helper `authorize(context_dir: Path) -> Path` writing a valid marker; `clean_env` and `ctx_env` contexts are authorized.

- [ ] **Step 1: Write failing tests** in `tests/test_consent.py`:
  - `test_record_without_marker_exits_5_and_writes_nothing` — `rup-ccm --record <full doc>` against an unauthorized temp context → returncode 5, stdout contains `rup-context --init` and `ask the user`, the context dir does not exist afterwards.
  - `test_estimate_without_marker_exits_5` — `rup-orchestrator --estimate` → 5.
  - `test_packet_without_marker_still_prints_with_warning` — `rup-ccm "b"` → 0, stdout contains `not authorized`.
  - `test_record_with_marker_writes` — after `authorize()`, record → 0.
- [ ] **Step 2:** Run `pytest tests/test_consent.py -v` → FAIL (record exits 0 today).
- [ ] **Step 3:** Implement the `context.py` interfaces; in `discipline.render_packet`, prepend one warning line `⚠️ .context/ not authorized yet — recording will ask for authorization (rup-context --init).` when `not has_consent(context_dir)`.
- [ ] **Step 4:** Update fixtures (`clean_env` session context and `ctx_env` authorized via `authorize()`); `test_unwritable_context_exits_4` authorizes before `chmod`. Run full suite → all pass.
- [ ] **Step 5:** Commit `feat(context): authorization marker gate, exit 5`.

---

### Task 2: `rup-context` — detect, init (non-destructive), pointer note; suite split

**Files:**
- Create: `skills/_shared/consent.py`
- Create: `skills/rup-context/{SKILL.md, scripts/run.py, references/standard.md}`
- Modify: `skills/_shared/context.py` (`require_consent` message uses `consent.detect`)
- Modify: `tests/conftest.py`, `tests/test_smoke.py` (skill sets)
- Test: `tests/test_rup_context.py`

**Interfaces:**
- Produces (`consent.py`):
  - `STANDARD_VERSION = "1"`; `DOC_DIR_CANDIDATES = [".specs", ".spec", ".doc", ".docs", "docs", "doc", "documentation", "specs"]`.
  - `standard_tree() -> dict[str, str | None]` — relative path → skeleton text (`None` = directory). Exactly the tree of spec §7.2; skeleton = `# <Title>\n\n> To be filled.\n`.
  - `@dataclass ContextState: context_dir: Path; exists: bool; authorized: bool; missing: list[str]; other_doc_dirs: list[str]`.
  - `detect(context_dir: Path) -> ContextState` — `other_doc_dirs` = candidates that exist in `context_dir.parent` (excluding `.context`), relative names.
  - `init_context(context_dir: Path, *, authorized_by: str, now=None) -> list[Path]` — creates only missing entries, writes marker (`version`, `authorized_by`, `authorized_at`), appends the pointer note, logs one row; returns created paths.
  - `POINTER_START = "<!-- rup-skills:start -->"`, `POINTER_END = "<!-- rup-skills:end -->"`; `ensure_pointer_note(project_root: Path) -> list[Path]` — for `CLAUDE.md` and `AGENT.md`: create if absent, else append the block only if `POINTER_START` absent. Block lists: discover → `rup-discover`; plan/cards/roadmap → `rup-backlog`; implement a task → `rup-build`; bug → `rup-debug`; review → `rup-review`; RUP documents → `rup-orchestrator`.
- Produces (`context.py`): `append_event(context_dir, *, skill: str, what: str, now=None) -> Path` — appends `| <iso> | — | <skill> | <what> |` to `tracking/rup-log.md` (same table as `append_log`). Used by init, import, card creation and moves.
- Produces (CLI `rup-context/scripts/run.py`): `--status` (prints `ContextState`, exit 0); `--init --authorized-by "<who>"` (prints created paths); `--context-dir D` like other skills.
- Produces (`conftest.py`): `DOCUMENT_SKILLS` (orchestrator + `DISCIPLINES` skills) and `EXECUTION_SKILLS` (the rest); existing parametrized tests in `test_smoke.py` use `DOCUMENT_SKILLS`; `test_agent_count…` asserts `len(DOCUMENT_SKILLS) == 9` and 21 roles. Add `test_execution_skills_help_and_stdlib` parametrized over `EXECUTION_SKILLS` (`--help` exit 0; `python -S … --help` exit 0; `SKILL.md` frontmatter name; `references/*.md` present).

- [ ] **Step 1: Failing tests** (`tests/test_rup_context.py`):
  - `test_status_reports_missing_marker_and_doc_dirs` — temp project with `.specs/` and `docs/`; `--status` lists both and `authorized: no`.
  - `test_init_creates_full_tree_and_marker` — every key of `standard_tree()` exists afterwards; marker has `authorized_by`.
  - `test_init_never_overwrites` — pre-existing `docs/02-elaboration/architecture.md` with text `KEEP` and `kanban/README.md` with `KEEP` → unchanged after init.
  - `test_init_is_idempotent` — second run creates nothing (empty list) and adds no second pointer block.
  - `test_pointer_note_appended_once_and_preserves_text` — existing `CLAUDE.md` with `OWNER TEXT` keeps it; block appears exactly once; `AGENT.md` created.
  - `test_exit5_message_lists_found_doc_dirs` — unauthorized record with `.doc/` present → stdout contains `.doc`.
- [ ] **Step 2:** Run → FAIL (module missing).
- [ ] **Step 3:** Implement `consent.py`, the CLI and `SKILL.md` (steps: run `--status`; show the user what was found and what will be created; **only after the user approves** run `--init --authorized-by "<user>"`; then offer `--import` if `other_doc_dirs`). Wire `require_consent` to print `detect()` details.
- [ ] **Step 4:** Split skill sets in `conftest.py`/`test_smoke.py`; run full suite → pass.
- [ ] **Step 5:** Commit `feat(rup-context): detect, authorized init, pointer note`.

---

### Task 3: `rup-context` — import existing documentation

**Files:**
- Modify: `skills/_shared/consent.py`, `skills/rup-context/scripts/run.py`, `SKILL.md`
- Test: `tests/test_rup_context.py`

**Interfaces:**
- Produces: `IMPORT_TARGETS = {"vision": "docs/01-inception/vision-and-scope.md", "requirements": "docs/01-inception/requirements.md", "architecture": "docs/02-elaboration/architecture.md", "domain": "docs/02-elaboration/domain-model.md", "contracts": "docs/03-construction/api-contracts.md", "ui": "docs/03-construction/ui-spec.md", "data": "docs/03-construction/data-dictionary.md", "tests": "docs/04-transition/test-strategy.md", "devops": "docs/04-transition/devops-infra.md"}`.
- `inventory(context_dir) -> list[Path]` — every `*.md`/`*.txt`/`*.adoc`/`*.rst` under `other_doc_dirs` (sorted).
- CLI `--import` → packet: the inventory (path + size), the target list, the instructions (one `## <target path>` section per target the agent fills; each section starts with `Source: <original path(s)>`; omit targets with nothing to import), and the exact `--record-import` command. Requires consent (exit 5 otherwise).
- CLI `--record-import FILE|-` → `record_import(context_dir, text, *, now=None) -> list[Path]`: sections whose heading is a value of `IMPORT_TARGETS`; unknown heading or a section without a `Source:` line → exit 1, nothing written. Missing target → created with the section body. Existing target → appended block `<!-- rup-import source="<sources>" date="<iso>" -->\n<body>\n<!-- /rup-import -->`. One log row per file.

- [ ] **Step 1: Failing tests:** `test_import_packet_lists_inventory_and_targets`; `test_record_import_creates_missing_target`; `test_record_import_appends_block_and_keeps_existing_lines` (existing file content is a prefix of the new content); `test_record_import_rejects_unknown_target_or_missing_source` (exit 1, files unchanged); `test_import_never_touches_originals` (originals' bytes and mtimes unchanged).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(rup-context): import existing docs into .context`.

---

### Task 4: Frontmatter parser/writer

**Files:** Create `skills/_shared/frontmatter.py`; Test `tests/test_frontmatter.py`.

**Interfaces:**
- `parse(text: str) -> tuple[dict, str]` — leading `---` block; values: scalar strings, empty → `""`, inline lists `[a, b]` → `list[str]`; strips BOM; accepts CRLF. No frontmatter → `({}, text)`.
- `dump(meta: dict, body: str) -> str` — keys in insertion order; lists as `[a, b]`; LF endings.

- [ ] **Step 1: Failing tests:** `test_roundtrip_scalars_and_lists`; `test_crlf_and_bom_parse_like_lf`; `test_no_frontmatter_returns_body`; `test_values_with_colons_kept` (`source: docs/x.md#Use Case: Book`).
- [ ] **Step 2–4:** Run FAIL → implement → PASS. **Step 5:** Commit `feat(shared): frontmatter`.

---

### Task 5: Cards — model, IDs, creation; `rup-backlog --new/--show/--list`

**Files:**
- Create: `skills/_shared/cards.py`
- Create: `skills/rup-backlog/{SKILL.md, scripts/run.py, references/cards.md}`
- Test: `tests/test_cards.py`

**Interfaces:**
- `COLUMNS` (Global Constraints order); `TYPES = {"epic": "EP", "story": "ST", "task": "TK", "bug": "BUG"}`; `PRIORITIES = ["Must", "Should", "Could", "Won't"]`.
- `REQUIRED_SECTIONS = {"epic": ["Goal", "Scope"], "story": ["User story", "Acceptance criteria", "Definition of Done"], "task": ["Description", "Target files", "Covers"], "bug": ["Symptom", "Reproduction"]}` — matched with `discipline.missing_artifacts`.
- `PARENT_TYPE = {"story": "epic", "task": "story", "bug": "story"}` (bug parent optional; story/task parent required).
- `@dataclass Card: id: str; type: str; title: str; status: str; meta: dict; body: str; path: Path`.
- `load_all(context_dir) -> dict[str, Card]` — status taken from folder; duplicate IDs → `discipline.fail` naming both paths.
- `get(context_dir, card_id) -> Card` (exit 1 if unknown).
- `next_id(context_dir, type) -> str`.
- `number_criteria(story_id: str, body: str) -> str` — under `## Acceptance criteria`, each `- ` bullet becomes `- **ST-NNN/AC-n**: <text>` (n from 1; already-numbered bullets kept).
- `acceptance_criteria(card) -> list[str]` — the `ST-NNN/AC-n` IDs in that section.
- `covers(card) -> list[str]` — IDs listed under a task's `## Covers`.
- `create(context_dir, type, title, body, *, parent=None, priority="Should", source="", now=None) -> Card` — validates sections, parent existence/type, every `Covers` ID exists in the parent story; story bodies get `number_criteria`; epics get `release: ""`, `iteration: ""`; writes `kanban/1-backlog/<ID>.md` with `## History` line `<iso> created in 1-backlog`; logs via `context.append_event`. (Task 7 adds the `roadmap.regenerate_views` call to `create`, `move` and `set_section`.)
- `set_section(card, name, text) -> Card` — replace or append `## <name>`, persist, bump `updated_at`.
- CLI: `--new {epic,story,task} --title T --doc FILE|- [--parent ID] [--priority P] [--source S]` (prints the new ID); `--show ID`; `--list [--column C] [--type T]` (table: ID, type, title, column, parent). All writes call `ensure_writable(context_dir)` (consent).

- [ ] **Step 1: Failing tests:** `test_create_story_numbers_criteria` (`ST-001/AC-1`, `ST-001/AC-2`); `test_ids_are_sequential_per_type`; `test_missing_section_rejected_nothing_written`; `test_task_requires_existing_story_parent`; `test_task_covers_must_exist_in_story`; `test_folder_wins_over_status_field` (Review Focus); `test_duplicate_id_exits_1_naming_both` (Review Focus); `test_new_requires_consent` (exit 5).
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5:** Commit `feat(rup-backlog): cards and creation`.

---

### Task 6: Moves, history, log, parent roll-up

**Files:** Modify `skills/_shared/cards.py`, `skills/rup-backlog/scripts/run.py`; Test `tests/test_cards.py`.

**Interfaces:**
- `move(context_dir, card_id, column, reason, *, actor="agent", now=None, rollup=True) -> Card` — unknown column/ID → exit 1, no change; same column → exit 1 `already in <col>`; moves file, sets `status`/`updated_at`, History line `<iso> <from> → <to> — <reason> (<actor>)`, appends `⚠️ skipped <cols>` when the target index − source index > 1 (forward only); log row via `context.append_event` (Task 2); then roll-up. (Views are regenerated from Task 7 on.)
- `rollup(context_dir, card) -> list[Card]` — for the parent (and grandparent): if any child in `3-doing` or later and parent in `1-backlog`/`2-todo` → move parent to `3-doing` (reason `roll-up: <child> started`); if all children in `7-done` → move parent to `7-done` (reason `roll-up: all children done`). Roll-up moves use `rollup=False` on themselves and recurse upward explicitly.
- CLI `--move ID COLUMN --reason R`.

- [ ] **Step 1: Failing tests:** `test_move_updates_folder_status_history_and_log`; `test_move_unknown_column_or_id_changes_nothing` (Review Focus); `test_skip_columns_warns_but_moves`; `test_story_rolls_to_doing_when_first_task_starts`; `test_story_and_epic_roll_to_done_when_all_children_done`; `test_move_requires_consent`.
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5:** Commit `feat(rup-backlog): moves and roll-up`.

---

### Task 7: Roadmap — releases, iterations, planning, generated views

**Files:** Create `skills/_shared/roadmap.py`; Modify `cards.py` (call `roadmap.regenerate_views(context_dir)` at the end of `create`, `move` and `set_section`; `roadmap` imports `cards` lazily inside its functions to avoid a cycle), `rup-backlog/scripts/run.py`; Test `tests/test_roadmap.py`.

**Interfaces:**
- Files: `.context/roadmap/R<n>.md` (frontmatter `id, title, milestone, goal, target_date`) and `.context/roadmap/R<n>-I<m>.md` (`id, release, phase, goal, start, end`); `milestone` ∈ `context.PHASE_MILESTONES` values or `""`; `phase` ∈ `rup.PHASES`.
- `new_release(context_dir, title, *, milestone="", goal="", target_date="") -> str` (`R1`, `R2`…).
- `new_iteration(context_dir, release_id, phase, goal, *, start="", end="") -> str` (`R1-I1`…; unknown release/phase → exit 1).
- `plan_epic(context_dir, epic_id, iteration_id) -> Card` — sets epic `iteration`/`release`; non-epic or unknown iteration → exit 1; History line `planned into <iteration>`.
- `render_roadmap(context_dir) -> str` — header `> Generated by rup-backlog — do not edit.`; per release (milestone, goal) → per iteration (phase, goal) → each epic `EP-NNN title — <done>/<total> stories done (<column>)`; section `Unplanned epics`.
- `render_board(context_dir) -> str` — same header; one `## <column>` per column with `- <ID> [<type>] <title>`.
- `regenerate_views(context_dir) -> list[Path]` — writes `docs/06-roadmap.md` and `docs/06-board.md` only.
- CLI: `--release-new --title T [--milestone M] [--goal G] [--target-date D]`; `--iteration-new --release R --phase P --goal G [--start S] [--end E]`; `--plan EPIC --iteration I`; `--roadmap`.

- [ ] **Step 1: Failing tests:** `test_release_and_iteration_ids`; `test_plan_epic_sets_iteration_and_release`; `test_roadmap_shows_progress_and_unplanned` (2 stories, 1 in `7-done` → `1/2`); `test_board_lists_every_column`; `test_views_regenerated_after_move`; `test_06_kanban_never_touched` (pre-existing `docs/06-kanban.md` bytes unchanged after moves/roadmap).
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5:** Commit `feat(rup-backlog): releases, iterations, roadmap views`.

---

### Task 8: Derive epics/stories from the requirements artifact

**Files:** Modify `rup-backlog/scripts/run.py`, `cards.py`; Test `tests/test_cards.py`.

**Interfaces:**
- CLI `--derive [--phase P]` → packet: embeds the body of `docs/<phase>/rup-requirements.md` (exit 1 if absent: "record rup-requirements first"); lists existing cards with their `source`; instructions: one epic per use-case package, one story per use case, `--source "rup-requirements#<use case heading>"`, create each with `--new` (exact command shown), **only for sources not yet in the list**; reports `Already derived`, `Not yet derived` (headings without a card) and `Orphan cards` (sources whose heading no longer exists).
- `derivation_report(context_dir, phase) -> dict[str, list[str]]` with keys `derived`, `pending`, `orphans` — headings = level-2/3 headings of the requirements body.

- [ ] **Step 1: Failing tests:** `test_derive_requires_requirements_artifact`; `test_derive_report_pending_derived_orphans`; `test_derive_never_modifies_existing_cards` (card bytes unchanged).
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5:** Commit `feat(rup-backlog): derive from requirements`.

---

### Task 9: Test-value checks (`testcheck`)

**Files:** Create `skills/_shared/testcheck.py`; Test `tests/test_testcheck.py` (fixtures: small Python and JS test files written in `tmp_path`).

**Interfaces:**
- Delivery document format (required `##` sections): `What was done`, `Files changed`, `Tests` (one line per test: `- <path>::<test name> — covers <ID>[, <ID>…]`), `Red evidence` (one `### <path>::<test name>` subsection per test with a fenced block of the failing output).
- `@dataclass Delivery: sections: dict[str, str]; tests: list[tuple[str, str, list[str]]]; red: dict[str, str]`.
- `parse_delivery(text) -> Delivery`.
- `id_pattern(ref_id: str) -> re.Pattern` — matches `ST-001/AC-1`, `st_001_ac_1`, `ST001-AC1`, `BUG-007`, `bug_007` (case-insensitive, separators `/ _ -` optional).
- `@dataclass TestInfo: name: str; text: str; has_assertion: bool; trivial: bool; calls_code: bool`.
- `find_test(project_root: Path, path: str, name: str) -> TestInfo | None` — path resolved under `project_root` (outside → `None` + problem); `.py` via `ast` (`Class::method` supported), `.js/.jsx/.ts/.tsx` via regex on `test(`/`it(` titles; other extensions → name search only (`trivial=False`, `calls_code=True`, warning `language not analysed`).
- Python rules: assertion = `assert` stmt, call to `assert*`/`self.assert*`, `pytest.raises`; trivial = every assertion's tested expression is a constant or a comparison of constants; `calls_code` = at least one call whose function name is not an assertion helper, `pytest.*`, or a builtin.
- JS rules: assertion = `expect(`/`assert`; trivial = only `expect(<literal>).to…(<literal>)`/`assert(true)`.
- `check_delivery(delivery, task: Card, story: Card | None, project_root: Path) -> list[str]` — problems: missing section; test not found; test references no ID from its `covers` list (name, docstring or comments within/above the test); referenced ID not a criterion of the story (or not the bug ID for bugs); a task `Covers` ID with no test; no assertion; trivial; never calls project code; missing red evidence. Empty list = OK.

- [ ] **Step 1: Failing tests:** `test_good_python_test_passes`; `test_assert_true_rejected`; `test_constant_comparison_rejected`; `test_no_assertion_rejected`; `test_no_project_call_rejected`; `test_test_without_criterion_reference_rejected`; `test_uncovered_criterion_reported`; `test_missing_red_evidence_reported`; `test_js_expect_true_rejected_and_good_js_passes`; `test_missing_or_outside_file_is_a_problem_not_crash` (Review Focus); `test_id_pattern_variants`.
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5:** Commit `feat(shared): test-value checks`.

---

### Task 10: `rup-build` — start and finish a task

**Files:** Create `skills/rup-build/{SKILL.md, scripts/run.py, references/tdd.md}`; Test `tests/test_rup_build.py`.

**Interfaces:**
- `--start ID` (task or bug, must be in `1-backlog`/`2-todo`/`blocked`, else exit 1) → `cards.move(..., "3-doing", "started")`, sets meta `branch: tk-nnn-<slug>` (slug of title, ≤40 chars), prints execution packet: the card, parent story with criteria, target files, earlier `rup-*` artifacts of the epic's iteration phase (via `discipline.prior_artifacts`), branch name, the TDD rules (test first, name the criterion, run → red, implement, run → green, commit per green step), and the exact `--finish` command.
- `--finish ID --delivery FILE|- [--project-root DIR]` (default project root = `context_dir.parent`) → card must be in `3-doing`; `testcheck.check_delivery`; problems → exit 1, print them, nothing written; else `set_section(card, "Delivery", text)`, for bugs also `Fix` (= What was done) and `Regression test` (= Tests), then `move(..., "4-review", "delivered")`.

- [ ] **Step 1: Failing tests:** `test_start_moves_to_doing_sets_branch_and_prints_packet`; `test_start_from_wrong_column_exits_1`; `test_finish_with_good_delivery_records_and_moves_to_review`; `test_finish_with_trivial_test_refuses_and_writes_nothing`; `test_finish_requires_doing`; `test_build_requires_consent`.
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5:** Commit `feat(rup-build): TDD start/finish`.

---

### Task 11: `rup-debug`

**Files:** Create `skills/rup-debug/{SKILL.md, scripts/run.py, references/debugging.md}`; Test `tests/test_rup_debug.py`.

**Interfaces:**
- `--open --title T --doc FILE|- [--parent ST-NNN] [--priority P]` → `cards.create(type="bug")`; prints the protocol: reproduce → failing regression test naming `BUG-NNN` → find the root cause → `--diagnose` → fix → `rup-build --finish BUG-NNN`.
- `--diagnose BUG-NNN --doc FILE|-` → document must contain `## Root cause` (non-empty) → `set_section(card, "Root cause", …)`; moves `1-backlog`/`2-todo` → `3-doing` (reason `diagnosed`). A bug without `Root cause` cannot be finished (`rup-build --finish` adds that check for bugs).

- [ ] **Step 1: Failing tests:** `test_open_creates_bug_with_required_sections`; `test_diagnose_records_root_cause`; `test_finish_bug_without_root_cause_refused`; `test_regression_test_must_reference_bug_id`.
- [ ] **Step 2–4:** FAIL → implement (including the bug check in `rup-build`) → PASS. **Step 5:** Commit `feat(rup-debug): bug protocol`.

---

### Task 12: `rup-review`

**Files:** Create `skills/rup-review/{SKILL.md, scripts/run.py, references/review.md}`; Test `tests/test_rup_review.py`.

**Interfaces:**
- `ID` (card in `4-review`, else exit 1) → checklist packet: criteria covered (from Delivery), delivery files vs `Target files` (listing extras/missing), a fresh `check_delivery` run summary, traceability (`source`, parent chain), branch integration steps toward `7-done`, and the exact `--record` command.
- `--record ID --doc FILE|-` → required sections `Verdict` (first non-empty line `approved` or `changes requested`, case-insensitive) and `Findings`; writes `## Review` (appended with timestamp, previous reviews kept); `approved` → move `5-testing` (reason `review approved`); `changes requested` → move `3-doing` (reason `changes requested: <first finding line>`).

- [ ] **Step 1: Failing tests:** `test_review_packet_requires_card_in_review`; `test_review_packet_flags_files_outside_target`; `test_approved_moves_to_testing`; `test_changes_requested_moves_back_to_doing_with_reason`; `test_invalid_verdict_exits_1`.
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5:** Commit `feat(rup-review): review checklist and verdict`.

---

### Task 13: `rup-discover` + hooks in the existing skills

**Files:**
- Create: `skills/rup-discover/{SKILL.md, scripts/run.py, references/discovery.md}`
- Modify: `skills/_shared/discipline.py` (`prior_artifacts`, `main` default phase), `skills/rup-orchestrator/scripts/run.py` (`governance_spec` instruction)
- Test: `tests/test_rup_discover.py`, `tests/test_context_persistence.py`

**Interfaces:**
- `rup-discover/scripts/run.py` = a `SPEC` with `key: None`, `title: "Discovery"`, `default_phase: "Inception"`, one role `Discovery Facilitator` with artifacts `Problem, Users, Goals, Non-goals, Anti-goals, Constraints, Open questions`, and instructions: talk with the user **before** writing — one question per message, build each question on the last answer, play back each part and ask what is wrong or missing; record only when the user confirms.
- `discipline.main(spec, *, script)` honors `spec.get("default_phase", "Elaboration")`.
- `discipline.prior_artifacts` embeds `rup-discover` first (label `Discovery (rup-discover)`) for every skill except `rup-discover` itself.
- Orchestrator `governance_spec` adds instruction: allocate epics to iterations with `rup-backlog --plan` and reference the iteration ID (`R<n>-I<m>`) in the Iteration Plan.

- [ ] **Step 1: Failing tests:** `test_discover_packet_defaults_to_inception_and_lists_sections`; `test_discover_record_writes_rup_discover_md`; `test_discover_artifact_embedded_first_in_requirements_packet`; `test_governance_packet_mentions_rup_backlog_plan`.
- [ ] **Step 2–4:** FAIL → implement → PASS (full suite). **Step 5:** Commit `feat(rup-discover): discovery conversation + hooks`.

---

### Task 14: Documentation, ADR-0013 and this repository's `.context/`

**Files:** `README.md`, `CLAUDE.md`, `AGENT.md`, `docs/{ARCHITECTURE,SKILLS,INSTALLATION}.md`, `skills/README.md`, `.context/README.md`, `.context/docs/**` (architecture, api-contracts, data-dictionary card schema, test-strategy, requirements RF/NFR), `.context/kanban/README.md` (new card types/IDs/commands), `.context/tracking/{decisions,progress}.md`, move `INIT-03-*` to `.context/inbox/processed/` with `[Done]`.

- [ ] **Step 1:** ADR-0013 (authorization gate amends ADR-0011's silent creation; execution skills; card model; generated views; test-value checks). Update every listed doc (exit code 5, 15 skills, protocols).
- [ ] **Step 2:** Run `rup-context --status` against this repository; **ask the owner** before `rup-context --init --authorized-by "<owner>"` on this repo (it adds the marker, missing skeletons and the pointer block to `CLAUDE.md`/`AGENT.md`).
- [ ] **Step 3:** Full suite + `bash scripts/install.sh --dry-run` (15 skills + `_shared`) → green; `git status --short` clean of stray files.
- [ ] **Step 4:** Commit `docs: execution skills (ADR-0013)`.
