#!/usr/bin/env python3
"""
cp-requirements — Requirements Engineering Crew (self-contained)

Creates a CrewAI crew with specialized agents to elicit, analyze,
specify and validate software requirements.

Usage:
  python run.py "scheduling system for clinics"
  python run.py --briefing "I need an app to manage inventory" --output requirements.md
  python run.py --input briefing.txt
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
    "business-analyst": {
        "role": "Business Analyst",
        "goal": "Discover, document and validate business rules with stakeholders",
        "backstory": (
            "Experienced business analyst with over 10 years in software projects. "
            "You are an expert at interviewing stakeholders, uncovering implicit business "
            "rules, and translating business needs into clear requirements. "
            "You ask 'why?' until you reach the real need. "
            "You know how to tell the difference between what the client ASKS for and what they NEED."
        ),
    },
    "requirements-specifier": {
        "role": "Requirements Specifier",
        "goal": "Write clear, testable user stories, use cases and acceptance criteria",
        "backstory": (
            "Requirements specification specialist with a software engineering background. "
            "You turn the business analyst's findings into formal artifacts: "
            "user stories in the format 'As [role], I want [feature] so that [benefit]', "
            "use cases with main and alternative flows, and acceptance criteria "
            "in BDD format (Given/When/Then). "
            "Your requirements are so clear that developers rarely need clarification."
        ),
    },
    "requirements-validator": {
        "role": "Requirements Validator",
        "goal": "Verify consistency, completeness, feasibility and traceability of requirements",
        "backstory": (
            "Rigorous, detail-oriented requirements validator. You check whether each requirement is: "
            "specific, measurable, achievable, relevant and time-bound (SMART). "
            "You hunt for inconsistencies, ambiguities, conflicting requirements and gaps. "
            "Your motto: 'An ambiguous requirement is a time bomb in the project budget.' "
            "You approve nothing without bidirectional traceability."
        ),
    },
    "product-owner-proxy": {
        "role": "Product Owner (Proxy)",
        "goal": "Prioritize requirements and ensure alignment with the product vision and business value",
        "backstory": (
            "Experienced Product Owner who represents the client's and the business's interests. "
            "You prioritize requirements based on business value, urgency and dependencies. "
            "You use techniques such as MoSCoW (Must/Should/Could/Won't) and Value vs Effort. "
            "You ensure that every delivered requirement generates real value for the user and the business. "
            "You know how to say 'no' to requirements that add no value."
        ),
    },
}


def get_agent(slug: str) -> Agent:
    _crew_llm = build_crew_llm()
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

def build_crew(briefing: str, output_path: str = None):
    """Build a CrewAI crew for requirements engineering."""

    analyst = get_agent("business-analyst")
    specifier = get_agent("requirements-specifier")
    validator = get_agent("requirements-validator")
    po = get_agent("product-owner-proxy")

    # --- Task 1: Elicitation ---
    elicitation = Task(
        description=f"""
        CLIENT BRIEFING:
        {briefing}

        YOUR JOB — REQUIREMENTS ELICITATION:
        1. Analyze the briefing and identify the problem domain
        2. Question implicit assumptions in the briefing
        3. Identify the stakeholders involved
        4. List business needs (NOT technical solutions)
        5. Identify business rules that may be implicit
        6. Document assumptions and risks

        OUTPUT FORMAT:
        ## Business Analysis
        - Domain: [which domain]
        - Stakeholders: [who they are]
        - Identified needs: [list]
        - Business rules: [list]
        - Assumptions: [list]
        - Risks: [list]
        """,
        expected_output="Complete business analysis with stakeholders, needs, rules, assumptions and risks",
        agent=analyst,
    )

    # --- Task 2: Specification ---
    specification = Task(
        description=f"""
        CLIENT BRIEFING:
        {briefing}

        YOUR JOB — REQUIREMENTS SPECIFICATION:
        Based on the business analysis performed, produce:

        1. **Epics and Features** — grouping of functionality
        2. **User Stories** — in the format "As [role], I want [feature] so that [benefit]"
        3. **Acceptance Criteria** — in BDD format (Given/When/Then)
        4. **Use Cases** — main flow + alternative flows for each user story
        5. **Business Rules** — formal and testable
        6. **Non-Functional Requirements** — performance, security, usability, etc.

        Be specific. Each user story should be implementable in 1-3 days.
        """,
        expected_output="Complete requirements document: epics, user stories, acceptance criteria, use cases, business rules and non-functional requirements",
        agent=specifier,
    )

    # --- Task 3: Validation ---
    validation = Task(
        description=f"""
        CLIENT BRIEFING:
        {briefing}

        YOUR JOB — REQUIREMENTS VALIDATION:
        Review the produced requirements document and verify:

        1. **Completeness**: Are all important scenarios covered?
        2. **Consistency**: Are there conflicting requirements?
        3. **Clarity**: Is each requirement specific and unambiguous?
        4. **Testability**: Is each acceptance criterion verifiable?
        5. **Traceability**: Is each requirement linked to a business need?
        6. **Feasibility**: Are the requirements technically feasible?

        For each problem found, document:
        - The specific problem
        - Why it is a problem
        - Suggested fix

        Issue a verdict: PASS or FAIL.
        If FAIL, list what needs to be fixed.
        """,
        expected_output="Validation report: problems found (if any), fix suggestions, and PASS/FAIL verdict",
        agent=validator,
    )

    # --- Task 4: Prioritization ---
    prioritization = Task(
        description=f"""
        CLIENT BRIEFING:
        {briefing}

        YOUR JOB — PRIORITIZATION:
        Based on the validated requirements document:

        1. Classify each requirement using MoSCoW:
           - **Must Have**: Essential for the MVP
           - **Should Have**: Important, but not critical for the MVP
           - **Could Have**: Desirable, can wait
           - **Won't Have**: Out of scope for now

        2. For the Must Haves, estimate relative effort (Small/Medium/Large)

        3. Define an MVP suggestion (minimum viable set)

        4. Identify dependencies between requirements

        Justify each prioritization decision based on business value.
        """,
        expected_output="Prioritized backlog (MoSCoW), MVP suggestion, dependencies between requirements, and business value justifications",
        agent=po,
    )

    # --- Crew ---
    crew = Crew(
        agents=[analyst, specifier, validator, po],
        tasks=[elicitation, specification, validation, prioritization],
        process=Process.sequential,
        verbose=True,
    )

    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-requirements: Requirements Engineering Crew (self-contained)",
    )
    parser.add_argument(
        "briefing",
        nargs="?",
        help="Client briefing / problem description",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="File with the briefing (alternative to the positional argument)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file to save the requirements document",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only build the crew and show the agents, without executing",
    )
    args = parser.parse_args()

    require_crewai()  # DT-07: actionable message instead of traceback

    # --- Resolve briefing ---
    briefing = None
    if args.input_file:
        briefing = Path(args.input_file).read_text(encoding="utf-8")
    elif args.briefing:
        briefing = args.briefing
    else:
        parser.print_help()
        print("\n❌ Error: provide the client briefing (argument or --input)")
        sys.exit(1)

    output_path = args.output

    print(f"\n📋 Briefing: {briefing[:120]}...")
    print(f"📂 Agents: embedded (self-contained)")
    print()

    crew = build_crew(briefing, output_path)

    if args.dry_run:
        print("🧪 DRY RUN — crew built, agents:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
        print("\n✅ Crew ready. Remove --dry-run to execute.")
        return

    print("🚀 Running requirements crew...\n")
    require_llm()  # DT-08: fail early, with a message, if there is no LLM
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Requirements Document generated!\n")
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
        out_file = output_dir / f"requirements_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Saved to: {out_file.resolve()}")


if __name__ == "__main__":
    main()
