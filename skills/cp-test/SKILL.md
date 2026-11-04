---
name: cp-test
description: "RUP Test Discipline (6/9). This skill covers the RUP **Test Discipline**: test planning, analysis, design, execution and evaluation, plus a test-value audit (static audit, mutation testing, survivor triage). Use when the user says 'test plan, test cases, test strategy, run tests, test evaluation', asks whether the tests are any good / worth something, wants mutation testing, or needs the RUP test artifacts."
---

# cp-test — RUP Test Discipline

This skill covers the RUP **Test Discipline**: test planning, analysis, design, execution and evaluation.

Grounded in *The Rational Unified Process: An Introduction* (3rd ed.), Philippe
Kruchten. Part of the `rup` family — drive the whole lifecycle through
`cp-orchestrator`, or run this discipline directly.

## Agents (4)

| Agent (slug) | Role | Artifacts |
|--------------|------|-----------|
| `test-manager` | Test Manager | Test Plan, Test Evaluation Summary, Test Value Assessment |
| `test-analyst` | Test Analyst | Test Ideas List, Test Cases, Test Data, Workload Analysis Model |
| `test-designer` | Test Designer | Test Strategy, Test Automation Architecture, Test Environment Configuration, Test Interface Specification |
| `tester` | Tester | Test Scripts, Test Suites, Test Log, Test Results |

## Phase focus

Elaboration → Transition

## How to run this skill — you are the LLM

This skill does not call any model: **you, the agent running it, produce the
artifacts**. The script gives you the work packet and records your result.

1. **Get the work packet** (read-only):

   ```bash
   python scripts/run.py "<briefing>" --phase <Inception|Elaboration|Construction|Transition>
   python scripts/run.py --input briefing.md --phase Elaboration     # long briefings
   ```

   It prints the RUP roles of this discipline (goal, perspective, mission), the
   **exact list of artifacts** you must write, the briefing, and the artifacts
   already recorded in `.context/` that this discipline builds on (governance +
   the earlier disciplines of the same phase).

2. **Write ONE markdown document**: a `# <Role>` per role, and a level-2
   heading `## <Artifact>` for every artifact listed. Follow the RUP conventions,
   reuse names/IDs from the earlier artifacts, state assumptions explicitly.

3. **Record it — mandatory** (the packet prints the exact command):

   ```bash
   python scripts/run.py --record doc.md --phase Elaboration "<briefing>"
   cat doc.md | python scripts/run.py --record - --phase Elaboration --input briefing.md
   ```

   The recorder checks that every required `## <Artifact>` section exists (if not,
   it lists the missing ones, writes nothing and exits `1` — add them and record
   again) and writes `.context/docs/<NN-phase>/cp-test.md` with a provenance header,
   plus a row in `.context/tracking/rup-log.md`.

   **Evidence is mandatory**: run the suite (and coverage) yourself and put the
   command, commit SHA, duration and result of every execution in the Test Log.
   Never write a number you did not measure.

## Test-value audit — do the tests catch bugs? (ADR-0016)

Coverage says which lines ran, not whether a test would notice a wrong line.
When the question is the value of the tests, run the audit protocol:

```bash
python scripts/run.py "<briefing>" --audit [--files a.py b.py] [--workers N] [--budget 2h]
```

It prints steps A0–A8 with the exact commands: profile the project
(`.context/tests/profile.json`), baseline, inventory, static audit, choose the
modules by risk, mutate, triage the survivors, act (cards/CRs), record. The tools:

| Command | Does |
|---------|------|
| `--profile-template` | Prints the `profile.json` to fill (suite command, isolation per worker) |
| `--static-audit [DIR]` | Tests with no assertion, trivial asserts, no project call, self-mocks → `tests/static-audit.md` |
| `--mutants --files F… [--verbose]` | Counts/lists the mutants (read-only) |
| `--mutate --files F… [--lines F:A-B] [--workers N] [--budget 2h] [--fresh] [--rerun-survivors]` | Runs the mutants in disposable copies, in parallel, resumable → `tests/mutation/results.jsonl` |
| `--mutation-status` | Progress of a long run |
| `--mutation-report` | `tests/mutation/report.md` (score per module, worst first) + `triage.md` rows for the survivors |
| `--triage-check` | Fails until every survivor is classified with its reason and action |
| `--show-mutant F:IDX` | Diff of one mutant |

The mutation run executes the project's own test command (from the profile) in
copies of the project: the original is never written, git is never run, and the
run refuses to continue if the code under test changed. Python mutants are
generated here; other languages use their ecosystem tool with the same protocol.
Rules: `references/audit.md` (protocol, profile, runner pitfalls) and
`references/triage.md` (survivor classes).

## CLI contract

| Argument | Meaning |
|----------|---------|
| `briefing` (positional) | Business demand / context for the discipline |
| `--input <file>` | Read the briefing from a file (alternative to positional) |
| `--phase {Inception,Elaboration,Construction,Transition}` | RUP phase (default: Elaboration) |
| `--context-dir <dir>` | The `.context/` (default: `$RUP_CONTEXT_DIR`, else the nearest up to the git root) |
| `--record <file\|->` | Validate your document and write it to `.context/` |

The audit options are listed above. Exit codes: `0` success · `1` usage error /
missing artifacts / failed baseline / incomplete triage · `4` `.context/` not
writable · `5` `.context/` not authorized. Standard library only — no LLM key.

## Reference

Agent → artifact mapping and missions: `references/agents.md`. Audit:
`references/audit.md`, `references/triage.md`.
