---
name: cp-quality
description: "Software Quality Assurance — creates a CrewAI crew with Auditor, Metrics Analyst, Continuous Improvement Engineer and Artifact Validator to audit processes, measure metrics and ensure compliance. Use when the user says 'audit quality', 'measure metrics', 'verify process', 'ensure quality'."
---

# cp-quality — Software Quality Assurance

Creates a self-contained CrewAI crew with 4 specialized agents to audit processes, measure quality metrics, propose continuous improvements and validate software artifacts.

## Agents

| Agent | Role |
|--------|--------|
| **Quality Auditor** | Reviews whether processes are being followed, verifies mandatory artifacts, applies a rigorous checklist |
| **Metrics Analyst** | Collects and analyzes metrics (test coverage, bugs, technical debt, velocity) — turns numbers into insights |
| **Continuous Improvement Engineer** | Proposes and implements process improvements — applies Kaizen and Lean in software teams |
| **Artifact Validator** | Verifies whether all mandatory artifacts exist and are complete — doesn't let missing documentation pass |

## Pipeline

```
1. Process and artifact audit (Auditor + Validator)
   ├── Auditor: verifies whether processes are being followed
   └── Validator: verifies whether mandatory artifacts exist and are complete

2. Metrics analysis (Metrics Analyst)
   └── Collects metrics, calculates indicators, identifies trends

3. Improvement proposals (Continuous Improvement Eng.)
   └── Based on audit + metrics, proposes prioritized improvements

4. Quality Gate — Final report with verdict (all agents)
   └── Compiles everything and issues PASS/FAIL with recommendations
```

## Quality Gate

- **Processes followed:** 100% of verified mandatory processes
- **Complete artifacts:** 100% of mandatory artifacts present and complete
- **Test coverage:** >= 80%
- **Technical debt:** < 20% of the codebase
- **Critical bugs:** 0 in production
- **Velocity:** within the team's historical average
- **Verdict:** PASS (all ok) or FAIL (something below the minimum)

## Input

- Description of the project/system being audited
- Artifacts from all phases (requirements, design, code, tests, deploy)
- Available metrics (optional)
- Mode: audit, metrics, improvement, or full

## Output

Complete quality report containing:
- Process audit results
- Verified artifact checklist
- Quality metrics (coverage, bugs, technical debt, velocity)
- Prioritized improvement proposals
- Final PASS/FAIL verdict with justification

## Usage

```bash
# Complete mode (audit + metrics + improvement)
python .hermes/skills/cp-quality/scripts/run.py "appointment scheduling system"

# Specific mode
python .hermes/skills/cp-quality/scripts/run.py "payments API" --mode audit

# With input file
python .hermes/skills/cp-quality/scripts/run.py --input description.md

# Save report to file
python .hermes/skills/cp-quality/scripts/run.py "mobile app" --output quality-report.md

# Just view the crew structure
python .hermes/skills/cp-quality/scripts/run.py "test" --dry-run
```

## Example

```bash
python .hermes/skills/cp-quality/scripts/run.py \
  "medical appointment scheduling system with authentication, \
   patient CRUD, scheduling with time slots, \
   and email notifications" \
  --mode full \
  --output quality-report.md
```

## Script

The `scripts/run.py` script is self-contained — all 4 agents are embedded in the Python code itself. It does not depend on an external agent directory.
