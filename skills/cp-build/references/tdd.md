# TDD delivery — format and test rules

## Test rules

- Write the test before the code and run it: it must fail first (red).
- Tie every test to a criterion: put the ID (`ST-001/AC-1`, or `st_001_ac_1`) in
  the test name, its docstring or a comment directly above it. A bug's test
  references the bug ID (`BUG-007`) or a criterion of its story.
- A task's `Covers` criteria must each have at least one test.
- Rejected tests: `assert True`, constant comparisons (`assert 1 == 1`), no
  assertion at all, or a test that never calls project code.
- Every listed test needs red evidence: the failing output you saw.
- JS/TS tests are checked by pattern; other languages only by name (a warning).
- Green is not enough: mutate the lines you changed and show the tests catch a
  wrong line (below). `--finish` warns when `## Mutation` is missing.

## Delivery document

Required sections: `What was done`, `Files changed`, `Tests`, `Red evidence`.
Recommended: `Mutation` (shown to the reviewer; its absence is a warning).
Each test is one line `- <path>::<test> — covers <ID>[, <ID>]`; red evidence is
one `### <path>::<test>` block with a fenced output per test.

````markdown
## What was done

Booking endpoint that returns the booked slot.

## Files changed

- app/booking.py
- tests/test_booking.py

## Tests

- tests/test_booking.py::test_book_slot_st_001_ac_1 — covers ST-001/AC-1

## Red evidence

### tests/test_booking.py::test_book_slot_st_001_ac_1

```
E   ImportError: cannot import name 'book' from 'app.booking'
```
````

## Mutation of the changed lines

With `.context/tests/profile.json` in place (cp-test `--audit`, step A0), run the
mutants of the lines the task changed:

```bash
python <skills>/cp-test/scripts/run.py --mutate --lines app/booking.py:10-42 --fresh
python <skills>/cp-test/scripts/run.py --mutation-status
```

Then write the section. Every survivor needs a test that kills it (re-run with
`--rerun-survivors`) or the reason it cannot matter (cp-test `references/triage.md`):

````markdown
## Mutation

app/booking.py:10-42 — 14 mutants, 13 killed, 1 survived (93%).

- #22 line 31 `return None` — equivalent: the return value of `log_slot` is not used by any caller.
````
