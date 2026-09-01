# DT-01 — UnicodeEncodeError on Windows console (cp1252) [Fixed]

**Type**: Bug · **Severity**: Medium · **Opened on**: 2026-08-18

## Symptom

`skills/cp-orchestrator/scripts/run.py` aborts when printing the banner:

```
UnicodeEncodeError: 'charmap' codec can't encode characters in position 2-65
  File ".../encodings/cp1252.py", line 19, in encode
```

## Reproduction

```bash
python skills/cp-orchestrator/scripts/run.py "x" --mode full --dry-run
```

(without `PYTHONUTF8=1`, on a Windows console with cp1252 codepage)

## Cause

The banner and status emojis use characters outside cp1252; Python's default
`stdout` on Windows is not UTF-8. Affects any skill that prints box-drawing
or emoji — not just the orchestrator.

## Current workaround

```bash
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python .../run.py ...
```

## Proposed fix

At the top of each `run.py` (or in `_shared`), reconfigure stdout before printing:

```python
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
```

`errors="replace"` ensures no exotic environment breaks execution.

## Acceptance criterion

- `python skills/cp-orchestrator/scripts/run.py "x" --mode full --dry-run` returns 0
  on a Windows console **without** encoding env vars.


---

## Resolution

**Fixed on 2026-08-18**, propagated to the agents via `./scripts/install.sh`.
Verified empirically with the two-layer harness (without `crewai` / with
`crewai` stub and no key). See `.context/docs/04-quality-qa.md`.
