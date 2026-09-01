# BUG-03 — Quality gate ignores the exit code: a crashing skill becomes "success" [Fixed]

**Type**: Bug · **Severity**: **High** · **Opened on**: 2026-08-18
**Verified empirically**: yes

## Symptom

A skill that dies with a traceback and exit code 1 is approved with WARN, and the
pipeline reports success at the end:

```
$ python cp-orchestrator/scripts/run.py "test without llm" --mode bugfix --auto

  ⏱️  0.1s | Quality Gate: WARN
  ⚠️  Phase approved with caveats: Could not determine the result
  📄 Preview:
  Traceback (most recent call last):
    File "...cp-bug-fix/scripts/run.py", line 17, in <module>
      from crewai import Agent, Task, Crew, Process
  ModuleNotFoundError: No module named 'crewai'

  ✅ Pipeline completed successfully!          ← reports SUCCESS
     Phases: 1 | ✅ 0 | ⚠️  1 | ❌ 0 | ⏭️  0
```

## Cause

`_check_quality_gate(self, crew_key, output_text)` receives **only the text** of
the output and counts keywords. The `returncode` of `subprocess.run` is never
read — `grep -n "returncode" run.py` returns zero occurrences in the orchestrator.

A crash contains none of the `fail_keywords` (`FAIL`, `FAILED`, `REJECTED`,
`BLOCKED`, `CRITICAL`…), so it falls into the default branch → WARN → pipeline
continues.

## Impact

In a `full` pipeline (8 phases), phase 1 can crash, all the following ones run
over an empty artifact, and the final report says "completed successfully". The
quality gate — the orchestrator's main guarantee — does not protect against the
most common failure mode.

## Proposed fix

`returncode != 0` is an unconditional FAIL, before any text analysis:

```python
def _check_quality_gate(self, crew_key, output_text, returncode=0):
    if returncode != 0:
        return {"status": "FAIL",
                "detail": f"Skill ended with exit code {returncode}"}
    ...
```

And at the call site (line ~1193): `gate = self._check_quality_gate(ck, output, result.returncode)`.

## Acceptance criterion

- A phase whose skill exits with code ≠ 0 receives FAIL and stops the pipeline.
- The final report does not report success when any phase failed.


---

## Resolution

**Fixed on 2026-08-18**, propagated to the agents via `./scripts/install.sh`.
Verified empirically with the two-layer harness (without `crewai` / with
`crewai` stub and no key). See `.context/docs/04-quality-qa.md`.
