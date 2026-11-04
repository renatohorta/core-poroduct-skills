# Test-value audit — protocol and runner pitfalls

Coverage says which lines ran. It does not say whether a test would notice if a
line were wrong: a project with 96% line coverage scored 76% on mutation, and a
green suite of 875 tests missed 12 real defects found by an independent review.
The audit answers "do our tests catch bugs?" with three instruments: **measured
execution**, **mutation** and **adversarial review**.

`python scripts/run.py "<briefing>" --audit [--files a.py b.py] [--workers N] [--budget 2h]`
prints the protocol with the exact commands for the project.

## Protocol A0–A8

| Step | What | Output (in `.context/tests/`) |
|---|---|---|
| A0 Profile | Language, runner, suite command, test dependencies (DB, queues), isolation per worker | `profile.json` (`--profile-template`) |
| A1 Baseline | Whole suite + coverage on a clean tree: command, SHA, duration, totals | `baseline.md` |
| A2 Inventory | Tests per suite/app, `autouse` fixtures, markers, what is mocked and how | Test Evaluation Summary |
| A3 Static audit | No assertion, constant/tautological asserts, no project call, self-mock | `static-audit.md` (`--static-audit`) |
| A4 Choose modules | By business risk (Risk List, rules, security, money, concurrency) and size, justified | Test Value Assessment |
| A5 Mutation | Isolated copies, env per worker, the module's tests first, timeout, resumable | `mutation/results.jsonl`, `state.json` |
| A6 Triage | Every survivor: equivalent / real gap / dead code / out of scope | `mutation/report.md`, `triage.md` |
| A7 Action | Real gap → task card + test, re-run: the mutant must die. Dead code → CR | cards (`cp-backlog`), CRs (`cp-ccm`) |
| A8 Record | Test Evaluation Summary, Test Value Assessment, Test Log | `docs/<phase>/cp-test.md` |

The cp-test packet embeds `baseline.md`, `static-audit.md`, `report.md` and
`triage.md` when they exist, so the artifacts use measured numbers.

## profile.json

```json
{
  "python": ".venv/bin/python",
  "test_command": ["{python}", "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", "{tests}"],
  "killed_exit_codes": [1],
  "workers": 0,
  "env": {"DB_NAME": "test_mut{worker}"},
  "test_map": {"src/apps/orders": ["src/apps/orders/tests", "src/apps/common/tests"]},
  "priority": {"src/apps/orders/pricing.py": ["src/apps/orders/tests/test_pricing.py"]},
  "timeout_factor": 3,
  "timeout_extra_s": 30
}
```

- `{tests}` = priority tests of the module, then its `test_map` entry (longest
  prefix; none = whole suite). Default priority: every `test_<module>.py`.
- `killed_exit_codes`: only "a test failed" counts as killed. pytest exits 2/4/5
  on interruption, usage and empty collection: those are **errors**, reported
  apart and left out of the score.

## Mutants (Python, `ast`)

Comparison swap (`==`↔`!=`, `<`↔`>=`, `in`↔`not in`, `is`↔`is not`), `and`↔`or`,
remove `not`, arithmetic swap, `True`↔`False`, integer +1, negate `if`,
`return x` → `return None`, remove a call statement. Calls on `logger`, `log`,
`logging`, `warnings`, `print` are not removed, and annotations are not mutated.
Each mutant keeps line + description; `--show-mutant FILE:IDX` rebuilds its diff.

Other languages: use the ecosystem tool (Stryker for JS/TS, PIT for Java,
go-mutesting for Go, cargo-mutants for Rust) with the same steps, and convert its
output to the same JSONL lines (`file`, `idx`, `line`, `kind`, `desc`, `status`
in `killed|survived|timeout|error<N>|invalid`) so the report and triage work.

## Runner pitfalls (learned the hard way)

| Pitfall | Rule (what the runner does or you must do) |
|---|---|
| Reused test DB with transactional tests (`--reuse-db` + a test that flushes) | Recreate the DB per run, or reuse only when the baseline passes twice in a row |
| Mutating the repository in use | Always copies; the original is never written |
| Run interrupted mid-mutant | Copies are recreated on every run; `results.jsonl` says what already ran |
| Code changed under the run (branch switch, edit) | The run fingerprints every non-test file and refuses to continue on a change (`--fresh` to restart). Test files may change: that is how gaps are closed |
| CPU contention | Workers = cores − 1 by default; lower it when other work runs; the forecast is printed after the baseline |
| One worker's baseline fails | The whole run aborts: every mutant would look killed |
| Slow kills | The module's own tests run first, with stop-on-first-failure (`-x`) |
| Exit codes mixed up | `killed` only for a test failure; `timeout` counts as detected but is listed; `error<N>` apart |
| Mass equivalent mutants | Log calls are skipped; unused returns are triaged as dead code (CR), not tests |
| `ast.unparse` reformats the file | Only line + description are stored; `--show-mutant` for the diff |
| Stale `.pyc` (same size and mtime) | `PYTHONDONTWRITEBYTECODE=1` in every worker |

## Long runs

A run of 2,000 mutants takes hours. Use `--budget 2h` to stop starting new
mutants after a time box; run the same command again to resume.
`--mutation-status` shows progress from `.context/tests/mutation/`. Do not
switch branches while it runs: run it from a dedicated worktree, or let it
finish.

## Mutation in the daily flow

- **cp-build**: `--mutate --lines <file>:<a>-<b>` on the lines the task changed; the
  delivery's `## Mutation` gives the score and explains every survivor.
- **cp-debug**: after the fix, mutate the fixed lines; the mutants that undo the
  fix must die, or the regression test does not guard it.
- **cp-review**: reads `## Mutation` and recommends an adversarial review by an
  agent without the builder's context.
