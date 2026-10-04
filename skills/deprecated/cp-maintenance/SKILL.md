---
name: cp-maintenance
description: "Software Maintenance and Evolution — creates a CrewAI crew with a Bug Analyst, Fix Developer, Refactoring Engineer and Impact Analyst to fix bugs, refactor code and evolve existing systems. Use when the user says 'fix bug', 'refactor', 'improve code', 'do maintenance', 'evolve functionality'."
---

# cp-maintenance — Software Maintenance and Evolution

Creates a self-contained CrewAI crew with 4 specialized agents for software maintenance and evolution: diagnosing bugs, implementing fixes, refactoring code and assessing the impact of changes.

## Agents

| Agent | Function |
|-------|----------|
| **Bug Analyst** | Triage, reproduction, bug diagnosis, root cause analysis. Experienced debugger who finds the root cause while others treat symptoms. |
| **Fix Developer** | Implements minimal and safe fixes. Surgical developer who fixes exactly what is broken, nothing more. |
| **Refactoring Engineer** | Improves existing code without changing behavior. Engineer who leaves the code cleaner than they found it, without introducing bugs. |
| **Impact Analyst** | Assesses the impact of proposed changes, identifies potential regressions. Analyst who thinks about all the consequences before a change is made. |

## Pipeline

```
[Bug Analyst] ──► [Impact Analyst] ──► [Fix Dev / Refactoring Eng.] ──► [Regression Tests] ──► Quality Gate
       │                       │                            │                              │                    │
       │  diagnosis            │  assesses impact           │  implements                │  validates         │  PASS/FAIL
       │  + root cause         │  + risks                   │  fix/refactoring           │  + regressions     │
       └───────────────────────┴────────────────────────────┴──────────────────────────────┴─────────────────────┴──► PASS/FAIL
```

## Operation Modes

| Mode | Description | Agents involved |
|------|-------------|-----------------|
| `bug-fix` | Fix a specific bug | Bug Analyst → Impact Analyst → Fix Dev → Tests |
| `refactor` | Refactor code without changing behavior | Impact Analyst → Refactoring Eng. → Tests |
| `improvement` | Improve existing code (performance, readability) | Impact Analyst → Refactoring Eng. → Tests |
| `full` | Complete pipeline: diagnosis → impact → fix → tests | All 4 agents |

## Input

- **Bug description / improvement request** — direct text or a file via `--input`
- May include: stack trace, error logs, expected vs. current behavior, improvement suggestions

## Output

- Root cause diagnosis (Bug Analyst)
- Impact analysis report with identified risks (Impact Analyst)
- Fixed or refactored code (Fix Dev / Refactoring Eng.)
- Validated regression tests
- Quality gate: final PASS/FAIL verdict

## Quality Gate

The Impact Analyst issues the final verdict after validating the regression tests:
- **PASS** ✅ — Bug fixed / code refactored, tests passing, no regressions
- **FAIL** ❌ — Problems identified that need to be resolved before considering it complete

## Usage

```bash
# Fix a bug
python .hermes/skills/cp-maintenance/scripts/run.py "the /login endpoint returns 500 when the email has an accent" --mode bug-fix

# Refactor code
python .hermes/skills/cp-maintenance/scripts/run.py "refactor the payments module to use the Strategy Pattern" --mode refactor

# Improve existing code
python .hermes/skills/cp-maintenance/scripts/run.py "improve the performance of the reports query" --mode improvement

# Complete pipeline
python .hermes/skills/cp-maintenance/scripts/run.py "fix a bug in the shipping calculation and refactor the discount logic" --mode full

# With an input file
python .hermes/skills/cp-maintenance/scripts/run.py --input bug_report.md --mode bug-fix

# Save output to a specific directory
python .hermes/skills/cp-maintenance/scripts/run.py "fix CPF validation" --output ./fixes

# Only see the crew structure
python .hermes/skills/cp-maintenance/scripts/run.py "test" --dry-run
```

## Example

```bash
python .hermes/skills/cp-maintenance/scripts/run.py \
  "Bug: when creating an order with free shipping (above R$ 200), the system applies \
   a duplicate discount. Stack trace: ValueError in the checkout module. \
   Expected behavior: discount applied only once." \
  --mode bug-fix --output ./fix-shipping
```

## Script

The `scripts/run.py` script is self-contained — all 4 agents are embedded in the Python code itself. It does not depend on an external agents directory.
