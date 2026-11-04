# Review checklist and verdict

Review the card against the packet, then the code. Be specific: a finding names a file, a test or a criterion.

## Checklist

1. **Criteria.** Every criterion the card must cover (task `Covers`, or the bug ID) has a delivery test that really asserts it.
2. **Files.** Changes stay inside `Target files`. Each file outside needs a reason; each target not changed needs one too.
3. **Tests.** The packet's `Test checks` line is `OK`. Read the tests: real assertions, calling project code, red evidence plausible.
4. **Mutation.** The delivery's `## Mutation` covers the changed lines; every survivor has a test that kills it or a reason (cp-test `references/triage.md`). Missing → ask for it on logic that matters.
5. **Adversarial review.** For non-trivial cards, an agent without the builder's context reviews the diff against the story (concurrency, retries, transactions/migrations, unindexed queries, wrong counts, error paths). Each real finding starts with a test that reproduces it.
6. **Traceability.** The card links to its story and epic; the work matches the story's intent and the epic's scope.
7. **Quality.** Minimal change, no dead code, no unrelated refactors; the full suite is green.
8. **Integration.** The branch merges cleanly; follow the packet's steps toward `7-done`.

## Verdict document

```
## Verdict

approved            <- or: changes requested

## Findings

- <first finding: becomes the move reason when changes are requested>
- <more findings; write `none` when approved with nothing to report>
```

- The first non-empty line of `## Verdict` is exactly `approved` or `changes requested`.
- `approved` moves the card to `5-testing`; `changes requested` moves it back to `3-doing` with the first finding as reason.
- Reviews accumulate in the card's `## Review` section, newest last.
