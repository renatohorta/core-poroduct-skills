# Survivor triage — rules

`--mutation-report` writes `.context/tests/mutation/triage.md` with one row per
surviving mutant. Fill **Class**, **Reason / scenario** and **Action** in every
row, then run `--triage-check`: it fails until every survivor is classified
by these rules. New survivors are appended on the next report; rows already
filled are kept.

| Class | When | Reason must say | Action |
|---|---|---|---|
| `real gap` | A wrong line the suite lets pass | The scenario: input → wrong behavior that passes the suite | The `TK-`/`BUG-` card of the test to write |
| `equivalent` | No test can tell the mutant apart | Why: "no caller uses the return (grep)", "the value only changes the message" | `—` or a note |
| `dead code` | Unreachable branch, return nobody uses | The evidence (grep of callers, unreachable condition) | A simplification CR (`cp-ccm`), not a test |
| `out of scope` | Log text, message wording, formatting | Why it does not matter | `—` |

1. A survivor becomes `equivalent` **only** with the reason written down.
2. A `real gap` needs the scenario: input → wrong behavior that would pass.
3. For each real gap, write the test, then re-run the survivors
   (`--mutate --rerun-survivors --files …`): **the mutant must die**. Only then is
   the gap closed. `--triage-check` lists real gaps whose mutant still survives.
4. Unused returns and unreachable branches are CRs for simplification, not tests.
5. Do not chase 100%: mutants in messages, logs and formatting stay `out of scope`.

Card for a gap (one per module is fine when the scenarios are related):

```bash
cp-backlog --new task --parent ST-NNN --title "Test: <behavior> (<module>)" \
  --source "cp-test#mutation:<module>:<line>" --doc - <<'EOF'
## Description
Mutant #<idx> (<mutation>) at <module>:<line> survives: <scenario>.
## Target files
- <test file>
## Covers
- ST-NNN/AC-n
EOF
```

## Example

| Module | # | Line | Mutation | Class | Reason / scenario | Action |
|---|---:|---:|---|---|---|---|
| `orders/display.py` | 41 | 54 | return None | real gap | public party with a tax ID: the response has no document and no test fails | TK-031 |
| `cache/cleanup.py` | 12 | 70 | True -> False | dead code | `delete_key` returns a bool no caller uses (grep) | CR: return None |
| `core/queues.py` | 88 | 88 | remove call notify | equivalent | notify is a no-op in tests by design; covered by the contract test of the queue | — |
