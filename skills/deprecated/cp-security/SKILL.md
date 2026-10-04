---
name: cp-security
description: "Software Security — creates a CrewAI crew with Security Analyst, Penetration Tester, Compliance Specialist and Fix Engineer to analyze vulnerabilities, test intrusions and ensure compliance. Use when the user says 'audit security', 'do pentest', 'check vulnerabilities', 'ensure compliance', 'OWASP'."
---

# cp-security — Software Security

Creates a CrewAI crew with specialized agents to run the complete software security cycle:

1. **Security Analyst** — Reviews code and architecture against OWASP Top 10, identifies vulnerabilities
2. **Penetration Tester** — Runs automated intrusion tests, thinks like an attacker
3. **Compliance Specialist** — Verifies compliance (LGPD, GDPR, SOC2, ISO 27001)
4. **Fix Engineer** — Implements fixes for found vulnerabilities

## Agents

| Agent | Role |
|--------|--------|
| Security Analyst | Reviews code and architecture against OWASP Top 10, finds vulnerabilities where no one else looks |
| Penetration Tester | Runs automated intrusion tests, thinks like an attacker to protect the system |
| Compliance Specialist | Verifies compliance with LGPD, GDPR, SOC2, ISO 27001 and applicable regulations |
| Fix Engineer | Implements vulnerability fixes without introducing new ones |

## Input

Source code + architecture description. Can be:
- Direct text in the argument: `"login system with JWT"`
- File: `--input code.txt`

## Output

Complete security report containing:
- Vulnerability analysis (OWASP Top 10)
- Penetration test results
- Compliance verification (LGPD/GDPR/SOC2)
- Implemented fixes
- Quality gate: PASS/FAIL (zero critical/high vulnerabilities)

## Quality Gate

The Security Analyst re-analyzes the code post-fix and issues a PASS/FAIL verdict.
If FAIL, the fix cycle must be repeated until there are no critical or high vulnerabilities.

## Modes

| Mode | Trigger | Agents |
|------|---------|---------|
| **code-review** | Static code review | Security Analyst |
| **pentest** | Penetration test | Penetration Tester |
| **compliance** | Compliance verification | Compliance Specialist |
| **full** | Complete cycle (default) | All 4 agents |

## Usage

```bash
# Complete cycle
python .hermes/skills/cp-security/scripts/run.py "login system with JWT and 2FA authentication"

# Specific mode
python .hermes/skills/cp-security/scripts/run.py --mode pentest "REST API with file upload"

# With input file
python .hermes/skills/cp-security/scripts/run.py --input src/app.py --mode full

# Save output to a specific file
python .hermes/skills/cp-security/scripts/run.py "payment system" --output report.md

# Just view the crew structure
python .hermes/skills/cp-security/scripts/run.py "test" --dry-run
```

## Example

```bash
python .hermes/skills/cp-security/scripts/run.py \
  "Django REST API that manages patient data. \
   Has JWT authentication, PDF exam upload, \
   and sharing of medical records between doctors. \
   Needs to be LGPD compliant."
```

## Script

The `scripts/run.py` script is self-contained — all agents are embedded in the Python code itself. It does not depend on an external directory.
