# BUG-04 — `"OK"` matched as a substring produces false PASS [Fixed]

**Type**: Bug · **Severity**: Medium · **Opened on**: 2026-08-18
**Related**: BUG-03 (same function)

## Symptom

`_check_quality_gate` tests `kw in output_upper` — **substring**, not word. The
`pass_keyword` `"OK"` appears inside common words in error messages:

| Skill output | pass | fail | Gate |
|--------------|------|------|------|
| `Error: invalid API t**ok**en` | 1 | 0 | **PASS** ❌ |
| `Br**ok**en pipeline` | 1 | 0 | **PASS** ❌ |
| `ModuleNotFoundError: No module named crewai` | 0 | 0 | WARN |
| `Traceback (most recent call last)` | 0 | 0 | WARN |

Any authentication error that mentions "token" — the most frequent case when an
LLM credential is missing — is classified as **success**.

## Proposed fix

Match by word boundary and do not count short keywords as substrings:

```python
import re
def _count(keywords, text):
    return sum(1 for kw in keywords
               if re.search(rf"\b{re.escape(kw)}\b", text))
```

Also consider removing `"OK"` from the list: it is too short to be a reliable
quality-gate signal.

## Acceptance criterion

- `"invalid API token"` does not produce PASS.
- `"Tests OK"` still produces PASS.


---

## Resolution

**Fixed on 2026-08-18**, propagated to the agents via `./scripts/install.sh`.
Verified empirically with the two-layer harness (without `crewai` / with
`crewai` stub and no key). See `.context/docs/04-quality-qa.md`.
