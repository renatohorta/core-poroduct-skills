#!/usr/bin/env python3
"""
cp-security — Software Security Crew (self-contained)

Creates a CrewAI crew with specialized agents to analyze vulnerabilities,
test intrusions, verify compliance and fix security flaws.

Usage:
  python run.py "login system with JWT"
  python run.py --mode pentest "REST API with file upload"
  python run.py --input src/app.py --output report.md
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
try:
    from crewai import Agent, Task, Crew, Process
except ImportError:  # DT-07: the lib is only required for real execution, not for --help
    Agent = Task = Crew = Process = None
import sys as _sys
from pathlib import Path as _Path
_SKILLS_ROOT = _Path(__file__).resolve().parent.parent.parent  # skills/
if str(_SKILLS_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_SKILLS_ROOT))
from _shared.llm import (build_crew_llm, require_crewai, require_llm,
                         setup_console)

setup_console()  # DT-01: UTF-8 on stdout/stderr (Windows console is cp1252)

# ═══════════════════════════════════════════════════════════════════════════
# EMBEDDED AGENTS
# ═══════════════════════════════════════════════════════════════════════════

AGENTS = {
    "security-analyst": {
        "role": "Security Analyst",
        "goal": "Review code and architecture against OWASP Top 10 and identify critical vulnerabilities",
        "backstory": (
            "Senior security engineer with over 15 years of experience in software security. "
            "You are an expert in OWASP Top 10, static code analysis, threat modeling "
            "and security architecture review. You find vulnerabilities where no one else "
            "looks — in input validation, access control, cryptography, insecure configuration, "
            "and much more. Your clinical eye for security flaws has prevented hundreds of breaches. "
            "You don't just point out problems, you explain the real impact of each vulnerability "
            "and suggest specific fixes. Your motto: 'Security is not a feature, it is a property of the system.'"
        ),
    },
    "penetration-tester": {
        "role": "Penetration Tester",
        "goal": "Run automated intrusion tests to identify exploitable attack vectors",
        "backstory": (
            "Certified ethical pentester (OSCP, CEH) who thinks like an attacker to protect the system. "
            "You have experience in intrusion testing on web applications, APIs, cloud infrastructure "
            "and networks. You know the tactics, techniques and procedures (TTPs) of real attackers. "
            "You test: SQL injection, XSS, CSRF, SSRF, IDOR, LFI/RFI, insecure deserialization, "
            "broken authentication, path traversal, and much more. You document each attack with "
            "reproducible steps, proof of concept (PoC) and severity classification. "
            "Your goal: break the system before criminals do."
        ),
    },
    "compliance-specialist": {
        "role": "Compliance Specialist",
        "goal": "Verify compliance with LGPD, GDPR, SOC2, ISO 27001 and applicable regulations",
        "backstory": (
            "Experienced compliance officer who knows all data protection "
            "and information security regulations. You are an expert in LGPD (Brazil's General Data Protection Law), "
            "GDPR (European Union's General Data Protection Regulation), SOC2 (Service "
            "Organization Control), ISO 27001 (Information Security Management System) and "
            "PCI-DSS (Payment Card Industry Data Security Standard). You verify whether the "
            "system complies with each applicable regulation, identify gaps "
            "and recommend corrective actions. You know the specific articles, sections and controls "
            "of each standard. Your motto: 'Compliance is not optional — it is the law.'"
        ),
    },
    "fix-engineer": {
        "role": "Fix Engineer",
        "goal": "Implement fixes for found vulnerabilities without introducing new flaws",
        "backstory": (
            "Security-focused developer with vast experience in vulnerability remediation. "
            "You are an expert at implementing secure fixes without introducing new flaws or "
            "breaking existing functionality. You know secure coding practices: "
            "prepared statements, output encoding, CSP, backend input validation, "
            "secure authentication, session management, proper cryptography, and much more. "
            "For each found vulnerability, you implement the most appropriate fix "
            "considering the system context, performance and maintainability. "
            "You document each fix explaining what changed and why the approach is secure. "
            "Your motto: 'Fix one vulnerability without creating two new ones.'"
        ),
    },
}


def get_agent(slug: str) -> Agent:
    _crew_llm = build_crew_llm()
    """Get a CrewAI Agent from the embedded definitions."""
    data = AGENTS.get(slug)
    if not data:
        name = slug.replace("-", " ").title()
        print(f"  [!] Agent not found: {slug} — using generic fallback")
        return Agent(
            role=name,
            goal=f"Complete the task with excellence as {name}",
            backstory=f"Specialized agent acting as {name}.",
            llm=_crew_llm,
            verbose=True,
            allow_delegation=False,
        )
    return Agent(
        role=data["role"],
        goal=data["goal"],
        backstory=data["backstory"],
        llm=_crew_llm,
        verbose=True,
        allow_delegation=False,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Crew builder
# ═══════════════════════════════════════════════════════════════════════════

def build_crew(description: str, mode: str = "full", output_path: str = None):
    """Build a CrewAI crew for security analysis based on mode."""

    analyst = get_agent("security-analyst")
    pentester = get_agent("penetration-tester")
    compliance = get_agent("compliance-specialist")
    engineer = get_agent("fix-engineer")

    tasks = []

    # ── Task 1: Security Analysis (always present) ──
    task_analysis = Task(
        description=f"""\
SYSTEM DESCRIPTION:
{description}

YOUR JOB — CODE AND ARCHITECTURE SECURITY ANALYSIS:

Analyze the described system against the following OWASP Top 10 categories:

1. **A01: Broken Access Control** — Missing or flawed access controls
2. **A02: Cryptographic Failures** — Cryptographic failures (exposed sensitive data)
3. **A03: Injection** — SQL, NoSQL, OS Command, LDAP injection
4. **A04: Insecure Design** — Design flaws that lead to vulnerabilities
5. **A05: Security Misconfiguration** — Insecure configurations
6. **A06: Vulnerable and Outdated Components** — Components with known vulnerabilities
7. **A07: Identification and Authentication Failures** — Authentication failures
8. **A08: Software and Data Integrity Failures** — Integrity failures
9. **A09: Security Logging and Monitoring Failures** — Logging and monitoring failures
10. **A10: Server-Side Request Forgery (SSRF)** — SSRF

For each identified vulnerability, document:
- **OWASP Category**: which of the 10 categories
- **Location**: where in the system the vulnerability manifests
- **Description**: explain the vulnerability in detail
- **Impact**: what the potential damage is (critical, high, medium, low)
- **Likelihood**: what the chance of exploitation is (high, medium, low)
- **Related CVE**: if applicable, mention known CVEs
- **Recommendation**: how to fix the vulnerability

OUTPUT FORMAT:
## Security Analysis Report
### Executive Summary
- Total vulnerabilities found: [N]
- Critical: [N] | High: [N] | Medium: [N] | Low: [N]
- Overall risk: [Critical/High/Medium/Low]

### Detailed Vulnerabilities
[For each vulnerability, use the format above]

### Priority Recommendations
[List of the 3-5 most important fixes]

""",
        expected_output="Security analysis report with vulnerabilities categorized by OWASP Top 10, impact and recommendations",
        agent=analyst,
    )
    tasks.append(task_analysis)

    # ── Task 2: Penetration Tests (if mode is pentest or full) ──
    if mode in ("pentest", "full"):
        task_pentest = Task(
            description=f"""\
SYSTEM DESCRIPTION:
{description}

YOUR JOB — AUTOMATED PENETRATION TESTS:

Based on the security analysis performed, run simulated penetration tests
against the described system. For each tested attack vector, document:

1. **SQL / NoSQL Injection**:
   - Try to identify entry points where user data is processed
   - Describe payloads that could be used
   - Expected attack result

2. **Cross-Site Scripting (XSS)**:
   - Identify points where user input is reflected or stored
   - Classify as Reflected, Stored or DOM-based
   - Describe payloads and impact

3. **Cross-Site Request Forgery (CSRF)**:
   - Check whether there is CSRF protection on sensitive operations
   - Describe how an attack could be executed

4. **IDOR (Insecure Direct Object References)**:
   - Identify endpoints that expose object IDs
   - Describe how to access unauthorized resources

5. **Broken Authentication**:
   - Test session fixation, session hijacking scenarios
   - Check password policies, rate limiting, MFA

6. **SSRF (Server-Side Request Forgery)**:
   - Identify features that make requests to user-supplied URLs

7. **File Upload Vulnerabilities**:
   - If there is upload, test: file type, size, path traversal, double extension

8. **Security Misconfiguration**:
   - Check: security headers (CSP, HSTS, X-Frame-Options), CORS, debug endpoints

For each attack, provide:
- **Vector**: which type of attack
- **Target**: specific endpoint or feature
- **Payload**: description of the payload or technique used
- **Severity**: Critical/High/Medium/Low
- **PoC**: reproducible step-by-step of the attack
- **Expected Result**: what would happen if the attack succeeded

""",
            expected_output="Penetration test report with attack vectors, payloads, severity and proofs of concept",
            agent=pentester,
        )
        tasks.append(task_pentest)

    # ── Task 3: Compliance (if mode is compliance or full) ──
    if mode in ("compliance", "full"):
        task_compliance = Task(
            description=f"""\
SYSTEM DESCRIPTION:
{description}

YOUR JOB — COMPLIANCE VERIFICATION:

Based on the security analysis and penetration tests performed, verify
the system's compliance with the following regulations:

### 1. LGPD (Brazil's General Data Protection Law)
Verify:
- **Art. 7**: Legal basis for processing personal data
- **Art. 9**: Data subject's right of access
- **Art. 11**: Processing of sensitive data
- **Art. 15-18**: Data subject rights (access, correction, deletion, portability)
- **Art. 46**: Technical and administrative security measures
- **Art. 48**: Incident notification to the ANPD

### 2. GDPR (General Data Protection Regulation — EU)
Verify:
- **Art. 5**: Principles (lawfulness, purpose, minimization, accuracy, storage, integrity)
- **Art. 7**: Conditions for consent
- **Art. 17**: Right to erasure ("right to be forgotten")
- **Art. 25**: Privacy by Design and Privacy by Default
- **Art. 32**: Security of processing
- **Art. 33-34**: Data breach notification

### 3. SOC2 (Service Organization Control)
Verify the Trust Service criteria:
- **Security**: Protection against unauthorized access
- **Availability**: System availability
- **Processing Integrity**: Authorized and accurate processing
- **Confidentiality**: Protection of confidential information
- **Privacy**: Collection, use, retention and disposal of personal data

### 4. ISO 27001
Verify the Annex A controls:
- A.9: Access control
- A.10: Cryptography
- A.12: Operational security
- A.14: System acquisition, development and maintenance
- A.18: Compliance

For each regulation, document:
- **Status**: Compliant / Non-compliant / Partially compliant
- **Gaps**: What is missing to be compliant
- **Corrective Actions**: What needs to be implemented
- **Priority**: High/Medium/Low
- **Suggested Deadline**: Immediate / Short term / Medium term / Long term

""",
            expected_output="Compliance report with compliance status for LGPD, GDPR, SOC2 and ISO 27001, gaps and corrective actions",
            agent=compliance,
        )
        tasks.append(task_compliance)

    # ── Task 4: Vulnerability Fix (always present in full) ──
    if mode == "full":
        task_fix = Task(
            description=f"""\
SYSTEM DESCRIPTION:
{description}

YOUR JOB — VULNERABILITY FIX:

Based on the vulnerabilities identified in the security analysis, penetration
tests and compliance gaps, implement fixes for each vulnerability.

For each fix, document:

1. **Vulnerability**: which vulnerability is being fixed
2. **OWASP Category**: OWASP classification
3. **Original Severity**: what the severity was before the fix
4. **Fix Approach**: explain the strategy used
5. **Code/Configuration**: describe the necessary changes in code or configuration
6. **Validation**: how to verify the fix is effective
7. **Side Effects**: possible impacts on existing functionality
8. **Post-Fix Severity**: what the severity is after the fix (should be Low or N/A)

Secure coding principles to follow:
- **Defense in Depth**: multiple layers of protection
- **Least Privilege**: minimum necessary privilege
- **Fail Secure**: fail in a secure way, not insecure
- **Input Validation**: always validate on the backend, never trust the frontend
- **Output Encoding**: encode output to prevent XSS
- **Parameterized Queries**: use prepared statements to prevent injection
- **Secure Cryptography**: use secure algorithms and modes (not MD5, SHA1, ECB)
- **Secure Session Management**: secure tokens, httpOnly, secure flags
- **CSP**: Content Security Policy to mitigate XSS
- **Rate Limiting**: protect against brute force and DoS

""",
            expected_output="Vulnerability fix plan with approaches, code/configuration and validation for each flaw",
            agent=engineer,
        )
        tasks.append(task_fix)

    # ── Task 5: Quality Gate — Post-fix re-analysis (only in full) ──
    if mode == "full":
        task_quality_gate = Task(
            description=f"""\
SYSTEM DESCRIPTION:
{description}

YOUR JOB — QUALITY GATE: POST-FIX RE-ANALYSIS:

Review the fixes proposed by the Fix Engineer and verify:

1. **Effectiveness**: Do the fixes actually eliminate the vulnerabilities?
2. **Completeness**: Were all identified vulnerabilities addressed?
3. **Security**: Do the fixes introduce new vulnerabilities?
4. **Impact**: Do the fixes break existing functionality?
5. **Best Practices**: Do the fixes follow security best practices?

Issue a verdict:

## QUALITY GATE — VERDICT

### Remaining Vulnerabilities
- Critical: [N] — [PASS/FAIL — must be 0]
- High: [N] — [PASS/FAIL — must be 0]
- Medium: [N] — [PASS/FAIL — acceptable if justified]
- Low: [N] — [PASS/FAIL — acceptable if justified]

### Final Result
**VERDICT: [PASS/FAIL]**

If PASS: The system has reached an acceptable security level.
If FAIL: List specifically what needs to be fixed before approval.

""",
            expected_output="Quality gate verdict: PASS/FAIL with analysis of remaining vulnerabilities and justifications",
            agent=analyst,
        )
        tasks.append(task_quality_gate)

    # --- Crew ---
    agents = [analyst]
    if mode in ("pentest", "full"):
        agents.append(pentester)
    if mode in ("compliance", "full"):
        agents.append(compliance)
    if mode == "full":
        agents.append(engineer)

    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-security: Software Security Crew (self-contained)",
    )
    parser.add_argument(
        "description",
        nargs="?",
        help="Description of the system/code to be audited",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="File with the system description (alternative to the positional argument)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file to save the security report",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["code-review", "pentest", "compliance", "full"],
        default="full",
        help="Operation mode (default: full — complete cycle)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only build the crew and show the agents, without executing",
    )
    args = parser.parse_args()

    require_crewai()  # DT-07: actionable message instead of traceback

    # --- Resolve description ---
    description = None
    if args.input_file:
        description = Path(args.input_file).read_text(encoding="utf-8")
    elif args.description:
        description = args.description
    else:
        parser.print_help()
        print("\n❌ Error: provide the system description (argument or --input)")
        sys.exit(1)

    output_path = args.output
    mode = args.mode

    print(f"\n🔒 Description: {description[:120]}...")
    print(f"📂 Agents: embedded (self-contained)")
    print(f"🎯 Mode: {mode}")
    print()

    crew = build_crew(description, mode, output_path)

    if args.dry_run:
        print("🧪 DRY RUN — crew built, agents:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
        print(f"\n📋 Tasks ({len(crew.tasks)}):")
        for i, task in enumerate(crew.tasks):
            desc_short = task.description[:80].replace("\n", " ").strip()
            print(f"  {i+1}. {desc_short}...")
        print(f"\n✅ Crew ready. Remove --dry-run to execute.")
        return

    print("🚀 Running security crew...\n")
    require_llm()  # DT-08: fail early, with a message, if there is no LLM
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Security Report generated!\n")
    print(result_str)

    # --- Save output ---
    if output_path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Saved to: {out_file.resolve()}")
    else:
        # Save to default location
        output_dir = Path(__file__).resolve().parent.parent / "outputs"
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = output_dir / f"security_{mode}_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Saved to: {out_file.resolve()}")


if __name__ == "__main__":
    main()
