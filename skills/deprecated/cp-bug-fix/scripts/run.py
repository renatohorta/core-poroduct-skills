#!/usr/bin/env python3
"""
cp-bug-fix — NEXUS-Micro Bug Fix Crew (self-contained)

Builds a CrewAI crew with embedded agents (no external dependency):
  Developer → QA (API Tester + Test Automation Engineer) → Evidence Collector

Usage:
  python run.py "bug description here"
  python run.py --bug "the /login endpoint returns 500 with an accented email" --type backend
"""

import argparse
import sys
import os
from pathlib import Path
try:
    from crewai import Agent, Task, Crew, Process
except ImportError:  # DT-07: the lib is only required for real execution, not --help
    Agent = Task = Crew = Process = None
import sys as _sys
from pathlib import Path as _Path
_SKILLS_ROOT = _Path(__file__).resolve().parent.parent.parent  # skills/
if str(_SKILLS_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_SKILLS_ROOT))
from _shared.llm import (build_crew_llm, require_crewai, require_llm,
                         setup_console)

setup_console()  # DT-01: UTF-8 no stdout/stderr (console Windows e cp1252)

# ═══════════════════════════════════════════════════════════════════════════
# EMBEDDED AGENTS (self-contained — no dependency on agency-agents/)
# ═══════════════════════════════════════════════════════════════════════════

AGENTS = {
    "engineering-backend-architect": {
        "role": "Backend Architect",
        "goal": "Design and implement scalable, secure, and performant backend systems",
        "backstory": (
            "Senior backend architect specializing in scalable system design, "
            "database architecture, API development, and cloud infrastructure. "
            "You build robust, secure, performant server-side applications and microservices. "
            "You are strategic, security-focused, scalability-minded, and reliability-obsessed."
        ),
    },
    "engineering-frontend-developer": {
        "role": "Frontend Developer",
        "goal": "Build responsive, accessible, and performant web applications with pixel-perfect precision",
        "backstory": (
            "Expert frontend developer specializing in modern web technologies, "
            "React/Vue/Angular frameworks, UI implementation, and performance optimization. "
            "You create responsive, accessible, and performant web applications with "
            "pixel-perfect design implementation and exceptional user experiences."
        ),
    },
    "testing-api-tester": {
        "role": "API Tester",
        "goal": "Validate the bug fix: test the endpoint/feature, verify edge cases, and confirm the fix works",
        "backstory": (
            "Expert API testing specialist focused on comprehensive API validation, "
            "performance testing, and quality assurance. You ensure reliable, performant, "
            "and secure API integrations. Thorough, security-conscious, automation-driven, "
            "and quality-obsessed. You break APIs before users do."
        ),
    },
    "testing-test-automation-engineer": {
        "role": "Test Automation Engineer",
        "goal": (
            "Create automated tests that prevent this bug from ever returning. "
            "Write deterministic, isolated tests with proper selectors and no hard sleeps"
        ),
        "backstory": (
            "Expert end-to-end test automation engineer who builds test suites teams actually trust. "
            "You are allergic to sleep(), obsessive about root causes, and protective of pipeline speed. "
            "Every test you write owns its data, waits on conditions instead of clocks, "
            "and leaves behind artifacts that make failures debuggable without a rerun."
        ),
    },
    "testing-evidence-collector": {
        "role": "Evidence Collector",
        "goal": (
            "Verify the fix with visual evidence. Screenshots, test output, logs — prove it works"
        ),
        "backstory": (
            "Skeptical QA specialist who requires visual proof for everything. "
            "You have persistent memory and HATE fantasy reporting. "
            "Screenshots don't lie — if you can't see it working, it doesn't work. "
            "Default to finding issues: first implementations ALWAYS have 3-5+ issues minimum."
        ),
    },
    "engineering-senior-developer": {
        "role": "Senior Developer",
        "goal": "Diagnose root causes of failures and implement minimal fixes",
        "backstory": (
            "Senior full-stack developer who creates premium web experiences. "
            "You are creative, detail-oriented, performance-focused, and innovation-driven. "
            "You've built many systems and know the difference between a proper fix and a workaround."
        ),
    },
}


def get_agent(slug: str) -> Agent:
    _crew_llm = build_crew_llm()
    """Get a CrewAI Agent from the embedded definitions."""
    data = AGENTS.get(slug)
    if not data:
        print(f"  [!] Agent not found: {slug} — using defaults")
        return Agent(
            role=slug.replace("-", " ").title(),
            goal="Complete the assigned task with excellence",
            backstory="Specialized AI agent",
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

def build_crew(bug_description: str, bug_type: str = "backend"):
    """Build a CrewAI crew for bug fixing."""

    # --- Developer agent ---
    if bug_type == "frontend":
        developer = get_agent("engineering-frontend-developer")
    else:
        developer = get_agent("engineering-backend-architect")

    # --- QA agents ---
    api_tester = get_agent("testing-api-tester")
    test_automation = get_agent("testing-test-automation-engineer")
    evidence_collector = get_agent("testing-evidence-collector")

    # --- Tasks ---
    investigate_and_fix = Task(
        description=f"""
        BUG REPORT:
        {bug_description}

        YOUR JOB:
        1. Read the relevant source files to understand the codebase
        2. Reproduce the bug — confirm you can see the error
        3. Identify the root cause
        4. Implement the minimal fix (do NOT refactor unrelated code)
        5. Verify the fix locally before handing off

        IMPORTANT:
        - Only fix what's described in the bug report
        - Do NOT add features, refactor, or change unrelated code
        - Document what you changed and why
        - If you cannot reproduce or fix the bug, say so clearly
        """,
        expected_output="A clear report: (1) root cause identified, (2) exact changes made with file paths and line numbers, (3) how you verified the fix locally",
        agent=developer,
    )

    qa_validate = Task(
        description=f"""
        BUG REPORT:
        {bug_description}

        YOUR JOB:
        1. Review the developer's fix — does it actually address the root cause?
        2. Test the fix: happy path, edge cases, error handling
        3. Verify no regressions were introduced
        4. Report: PASS or FAIL with specific evidence

        If PASS: hand off to Test Automation Engineer
        If FAIL: provide specific, actionable feedback for the developer
        """,
        expected_output="QA validation report: PASS/FAIL with specific test results, edge cases checked, and evidence",
        agent=api_tester,
    )

    create_tests = Task(
        description=f"""
        BUG REPORT:
        {bug_description}

        YOUR JOB:
        The developer has fixed this bug. The API Tester has validated the fix.
        Now create automated tests that will catch this bug if it ever returns.

        Requirements:
        1. Write tests that specifically reproduce the original bug scenario
        2. Tests must be deterministic — no sleeps, no flaky selectors
        3. Tests must own their data — create what they need, don't depend on seed data
        4. Use the project's existing test framework (pytest, Jest, Playwright, etc.)
        5. Place tests in the correct test directory following project conventions
        6. Run the tests to confirm they pass with the fix

        Output: the test file(s) created, where they were placed, and confirmation they pass.
        """,
        expected_output="Test file(s) created with path, test names, and confirmation they pass. If tests cannot be created, explain why.",
        agent=test_automation,
    )

    final_verification = Task(
        description=f"""
        BUG REPORT:
        {bug_description}

        YOUR JOB — FINAL VERIFICATION:
        1. Review the developer's fix
        2. Review the QA validation results
        3. Review the automated tests created
        4. Collect evidence: screenshots, test output, logs
        5. Issue final verdict: PASS or FAIL

        If PASS: the bug is fixed, tests are in place, evidence is collected.
        If FAIL: provide specific issues that must be addressed.

        Remember: default to finding issues. "Zero issues found" is a red flag.
        """,
        expected_output="Final verification report with evidence (screenshots, test output) and PASS/FAIL verdict",
        agent=evidence_collector,
    )

    # --- Crew ---
    crew = Crew(
        agents=[developer, api_tester, test_automation, evidence_collector],
        tasks=[investigate_and_fix, qa_validate, create_tests, final_verification],
        process=Process.sequential,
        verbose=True,
    )

    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-bug-fix: NEXUS-Micro bug fix crew (self-contained)",
    )
    parser.add_argument(
        "bug_description",
        nargs="?",
        help="Description of the bug to fix",
    )
    parser.add_argument(
        "--bug", "-b",
        dest="bug",
        help="Bug description (alternative to the positional argument)",
    )
    parser.add_argument(
        "--type", "-t",
        choices=["backend", "frontend"],
        default="backend",
        help="Bug type: backend or frontend (default: backend)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only builds the crew and shows the agents, without running",
    )
    args = parser.parse_args()

    require_crewai()  # DT-07: actionable message instead of a traceback

    bug_description = args.bug or args.bug_description
    if not bug_description:
        parser.print_help()
        print("\n❌ Error: provide the bug description")
        sys.exit(1)

    print(f"\n🐛 Bug: {bug_description}")
    print(f"🔧 Type: {args.type}")
    print(f"📂 Agents: embedded (self-contained)")
    print()

    crew = build_crew(bug_description, args.type)

    if args.dry_run:
        print("🧪 DRY RUN — crew built, agents:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
        print("\n✅ Crew ready. Remove --dry-run to execute.")
        return

    print("🚀 Running crew...\n")
    require_llm()  # DT-08: fails early, with a message, if there is no LLM
    result = crew.kickoff()
    print(f"\n✅ Final result:\n{result}")


if __name__ == "__main__":
    main()