#!/usr/bin/env python3
"""
cp-implementation — Software Implementation Crew (self-contained)

Creates a CrewAI crew with 5 specialized agents to implement,
review and integrate software code.

Usage:
  python run.py "implement user CRUD with JWT authentication"
  python run.py "create reports endpoint" --type backend
  python run.py "login screen with validation" --type frontend
  python run.py "scheduling system" --type full
  python run.py --input specification.md --output ./implementation
  python run.py "test" --dry-run
"""

import argparse
import sys
import os
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
# EMBEDDED AGENTS (self-contained)
# ═══════════════════════════════════════════════════════════════════════════

AGENTS = {
    "backend-developer": {
        "role": "Backend Developer",
        "goal": (
            "Implement REST/GraphQL APIs, business logic, data models, "
            "database migrations, authentication, authorization and performant endpoints"
        ),
        "backstory": (
            "Senior backend engineer with over 12 years of experience "
            "in distributed systems, RESTful APIs, GraphQL, relational databases "
            "and NoSQL. You are obsessed with clean, testable, performant code. "
            "You always think about edge cases, input validation, error handling "
            "and security before writing a single line of code. "
            "You follow SOLID, DRY and KISS principles. "
            "Your APIs are documented, versioned and follow RESTful standards. "
            "You never deliver code without unit tests."
        ),
    },
    "frontend-developer": {
        "role": "Frontend Developer",
        "goal": (
            "Implement responsive, accessible, performant user interfaces "
            "with complete API integration"
        ),
        "backstory": (
            "Frontend engineer specialized in React, TypeScript, Tailwind CSS "
            "and modern frameworks. You create reusable components, manage "
            "state efficiently (React Query, Zustand, Redux), and implement "
            "smooth animations and natural transitions. "
            "You are obsessed with accessibility (WCAG 2.1 AA/AAA), performance "
            "Core Web Vitals, and user experience. "
            "Every component you create has loading, empty, error "
            "and edge case states covered. You integrate frontend with API using typed "
            "contracts and handle network errors gracefully."
        ),
    },
    "mobile-developer": {
        "role": "Mobile Developer",
        "goal": (
            "Implement native/cross-platform mobile apps with React Native "
            "or Flutter, with performance, fluid navigation and API integration"
        ),
        "backstory": (
            "Senior mobile engineer specialized in React Native and Flutter. "
            "You build apps that feel native, with 60fps animations, "
            "intuitive navigation and efficient state management. "
            "You think about: battery consumption, data usage, small screens, "
            "touch versus click, native gestures, and offline-first. "
            "Every screen you create considers loading states, pull-to-refresh, "
            "friendly error handling and empty states. "
            "You integrate with REST APIs using typed contracts and manage "
            "local cache for offline experience."
        ),
    },
    "code-reviewer": {
        "role": "Code Reviewer",
        "goal": (
            "Review all implemented code: check patterns, best practices, "
            "security, performance, readability and architectural cohesion"
        ),
        "backstory": (
            "Senior software engineer who has reviewed thousands of pull requests "
            "across dozens of projects. You have a clinical eye for: "
            "dead code, high cyclomatic complexity, abstraction leakage, "
            "excessive coupling, lack of cohesion, and bad security practices. "
            "You do not approve code that: has no tests, has magic numbers, "
            "generic exception handling, or duplicated logic. "
            "Your feedback is constructive, specific and actionable — you always "
            "suggest HOW to improve, not just point out the problem. "
            "You issue a detailed report with: problems found, "
            "severity (low/medium/high/critical), and fix suggestions."
        ),
    },
    "integrator": {
        "role": "Integrator",
        "goal": (
            "Ensure backend, frontend and mobile work together: validate "
            "API contracts, end-to-end flows and data consistency"
        ),
        "backstory": (
            "Experienced integration engineer who ensures all the pieces "
            "of the system fit together perfectly. You verify: "
            "whether API contracts are respected (status codes, response "
            "formats, headers), whether the frontend consumes the data correctly, "
            "whether the mobile handles the same scenarios, and whether there are no breaks between "
            "the layers. "
            "You run integration tests mentally, validating complete "
            "flows: from the user's click to the database and back. "
            "Your motto: 'If it doesn't work integrated, it doesn't work.' "
            "You issue a PASS or FAIL verdict with specific evidence."
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

def build_crew(
    specification: str,
    type: str = "full",
    output_dir: str = None,
):
    """
    Build a CrewAI crew for software implementation.

    Args:
        specification: Technical specification / feature description
        type: 'backend', 'frontend', 'mobile', or 'full'
        output_dir: Directory to save output files
    """
    agents = {}
    tasks = []

    # --- Agent: Backend Developer ---
    agents["backend"] = get_agent("backend-developer")

    # --- Agent: Frontend Developer ---
    agents["frontend"] = get_agent("frontend-developer")

    # --- Agent: Mobile Developer (optional) ---
    agents["mobile"] = get_agent("mobile-developer")

    # --- Agent: Code Reviewer ---
    agents["reviewer"] = get_agent("code-reviewer")

    # --- Agent: Integrator ---
    agents["integrator"] = get_agent("integrator")

    # ─────────────────────────────────────────────────────────────────────
    # Task 1: Backend Implementation
    # ─────────────────────────────────────────────────────────────────────
    if type in ("backend", "full"):
        task_backend = Task(
            description=f"""
            TECHNICAL SPECIFICATION:
            {specification}

            YOUR JOB — BACKEND IMPLEMENTATION:

            1. Analyze the specification and identify the endpoints, models and business rules
            2. Implement:
               - Data models and migrations
               - REST/GraphQL endpoints with input validation
               - Business logic with error handling
               - Authentication/authorization when applicable
               - Unit tests for the implemented logic
            3. Document the API contracts (method, path, request/response)
            4. Follow best practices: SOLID, DRY, KISS, consistent error handling

            IMPORTANT:
            - Clean, well-structured code
            - Input validation on all endpoints
            - Error handling with appropriate status codes
            - Logs for production debugging
            - Mandatory unit tests
            """,
            expected_output=(
                "Implemented backend code: models, endpoints, business logic, "
                "unit tests. Documented API contracts."
            ),
            agent=agents["backend"],
        )
        tasks.append(task_backend)

    # ─────────────────────────────────────────────────────────────────────
    # Task 2: Frontend Implementation
    # ─────────────────────────────────────────────────────────────────────
    if type in ("frontend", "full"):
        task_frontend = Task(
            description=f"""
            TECHNICAL SPECIFICATION:
            {specification}

            YOUR JOB — FRONTEND IMPLEMENTATION:

            1. Analyze the specification and the API contracts
            2. Implement:
               - React/Vue/Angular components with TypeScript
               - States: loading, empty, error, success
               - API integration (React Query, SWR, or fetch)
               - Navigation between screens
               - Forms with validation
               - Responsive and accessible design (WCAG)
            3. Handle all UI states:
               - Loading: skeleton/spinner
               - Empty: friendly message + call to action
               - Error: message + retry button
               - Success: visual feedback

            IMPORTANT:
            - Accessibility (aria-labels, roles, focus management)
            - Performance (code splitting, lazy loading)
            - Network error handling
            - Visual feedback for all user actions
            """,
            expected_output=(
                "Implemented frontend code: components, screens, API integration, "
                "UI states, accessibility."
            ),
            agent=agents["frontend"],
        )
        tasks.append(task_frontend)

    # ─────────────────────────────────────────────────────────────────────
    # Task 3: Mobile Implementation (optional)
    # ─────────────────────────────────────────────────────────────────────
    if type in ("mobile", "full"):
        task_mobile = Task(
            description=f"""
            TECHNICAL SPECIFICATION:
            {specification}

            YOUR JOB — MOBILE IMPLEMENTATION:

            1. Analyze the specification and the API contracts
            2. Implement (React Native or Flutter):
               - Screens with fluid navigation
               - Optimized native components
               - REST API integration
               - States: loading, empty, error, success
               - Native gestures and animations
               - Offline-first cache when applicable
            3. Consider:
               - Performance on low-cost devices
               - Battery and data consumption
               - Screens of different sizes
               - Offline mode

            IMPORTANT:
            - Intuitive navigation (stack, tab, drawer)
            - Pull-to-refresh on lists
            - Friendly error handling
            - Empty states with illustrations
            """,
            expected_output=(
                "Implemented mobile code: screens, navigation, API integration, "
                "UI states, offline cache."
            ),
            agent=agents["mobile"],
        )
        tasks.append(task_mobile)

    # ─────────────────────────────────────────────────────────────────────
    # Task 4: Code Review
    # ─────────────────────────────────────────────────────────────────────
    task_review = Task(
        description=f"""
        TECHNICAL SPECIFICATION:
        {specification}

        YOUR JOB — CODE REVIEW:

        Review ALL the implemented code (backend, frontend and/or mobile) and evaluate:

        1. **Patterns and best practices**: Does the code follow framework/language conventions?
        2. **Security**: Are there vulnerabilities? (SQL injection, XSS, CSRF, exposed sensitive data)
        3. **Performance**: Are there bottlenecks? (N+1 queries, unnecessary renders, large bundle)
        4. **Readability**: Is the code clear? Are variable/function names descriptive?
        5. **Maintainability**: Is there duplicated code? Unnecessary complexity?
        6. **Tests**: Do the tests cover the important scenarios?
        7. **Error handling**: Are all errors handled properly?

        For each problem found, report:
        - Location (file, approximate line)
        - Severity: 🔴 Critical / 🟠 High / 🟡 Medium / 🔵 Low
        - Problem description
        - Fix suggestion

        Report format:
        ```
        ## Code Review Report

        ### 🔴 Critical Problems
        ...

        ### 🟠 High Problems
        ...

        ### 🟡 Medium Problems
        ...

        ### 🔵 Low Problems
        ...

        ### ✅ Positive Points
        ...

        ### 📊 Summary
        - Total problems: N
        - Critical: N | High: N | Medium: N | Low: N
        - Verdict: APPROVED / REJECTED
        ```
        """,
        expected_output=(
            "Complete code review report with problems categorized by severity, "
            "fix suggestions and final verdict."
        ),
        agent=agents["reviewer"],
    )
    tasks.append(task_review)

    # ─────────────────────────────────────────────────────────────────────
    # Task 5: Integration and Validation
    # ─────────────────────────────────────────────────────────────────────
    task_integration = Task(
        description=f"""
        TECHNICAL SPECIFICATION:
        {specification}

        YOUR JOB — INTEGRATION AND VALIDATION:

        You are the last quality gate. Verify that everything works together:

        1. **API Contracts**: Does the backend expose what the frontend/mobile expects?
           - Correct status codes (200, 201, 400, 401, 404, 500)?
           - Consistent response format?
           - Compatible authentication headers?

        2. **End-to-end flows**:
           - User performs action in frontend → API call → response → UI updated
           - Are API errors handled in the UI?
           - Do loading states appear while the request is in progress?

        3. **Consistency**:
           - Are field names consistent between backend and frontend?
           - Are data types compatible?
           - Do pagination, filters and sorting work the same across all layers?

        4. **Duplicate validation**:
           - Validation in the frontend AND the backend?
           - Are error messages consistent?

        Issue the final verdict:

        ```
        ## Integration Report

        ### ✅ Verified Items
        - API Contracts: [OK/ISSUES]
        - E2E Flows: [OK/ISSUES]
        - Consistency: [OK/ISSUES]
        - Validation: [OK/ISSUES]

        ### 🔴 Integration Problems
        ...

        ### 📋 Final Verdict
        ## PASS ✅ / FAIL ❌

        ### Recommendations
        ...
        ```
        """,
        expected_output=(
            "Complete integration report with contract verification, E2E flows, "
            "consistency and final PASS/FAIL verdict."
        ),
        agent=agents["integrator"],
    )
    tasks.append(task_integration)

    # --- Build agent list (only the used ones) ---
    agent_list = []
    if type in ("backend", "full"):
        agent_list.append(agents["backend"])
    if type in ("frontend", "full"):
        agent_list.append(agents["frontend"])
    if type in ("mobile", "full"):
        agent_list.append(agents["mobile"])
    agent_list.append(agents["reviewer"])
    agent_list.append(agents["integrator"])

    # --- Crew ---
    crew = Crew(
        agents=agent_list,
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
        description="cp-implementation: Software Implementation Crew (self-contained)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py "implement user CRUD with JWT authentication"
  python run.py "create reports endpoint" --type backend
  python run.py "login screen with validation" --type frontend
  python run.py "catalog mobile app" --type mobile
  python run.py "scheduling system" --type full
  python run.py --input specification.md --output ./implementation
  python run.py "test" --dry-run
        """,
    )
    parser.add_argument(
        "specification",
        nargs="?",
        help="Technical specification of what to implement",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="File with the technical specification (alternative to the positional argument)",
    )
    parser.add_argument(
        "--type", "-t",
        choices=["backend", "frontend", "mobile", "full"],
        default="full",
        help="Implementation type (default: full = backend + frontend + mobile)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output directory to save the code and reports",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only build the crew and show the agents, without executing",
    )
    args = parser.parse_args()

    require_crewai()  # DT-07: actionable message instead of traceback

    # --- Resolve specification ---
    specification = None
    if args.input_file:
        input_path = Path(args.input_file)
        if not input_path.exists():
            print(f"❌ File not found: {args.input_file}")
            sys.exit(1)
        specification = input_path.read_text(encoding="utf-8")
    elif args.specification:
        specification = args.specification
    else:
        parser.print_help()
        print("\n❌ Error: provide the technical specification (argument or --input)")
        sys.exit(1)

    output_dir = args.output

    # --- Type map ---
    type_label = {
        "backend": "Backend",
        "frontend": "Frontend",
        "mobile": "Mobile",
        "full": "Full Stack (Backend + Frontend + Mobile)",
    }

    print(f"\n📋 Specification: {specification[:120]}...")
    print(f"🔧 Type: {type_label.get(args.type, args.type)}")
    print(f"📂 Agents: embedded (self-contained)")
    print()

    crew = build_crew(specification, args.type, output_dir)

    if args.dry_run:
        print("🧪 DRY RUN — crew built, agents:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
        print(f"\n📋 Tasks ({len(crew.tasks)}):")
        for i, task in enumerate(crew.tasks, 1):
            agent_name = task.agent.role if hasattr(task, 'agent') and task.agent else "?"
            print(f"  {i}. {task.description[:80]}... → {agent_name}")
        print("\n✅ Crew ready. Remove --dry-run to execute.")
        return

    print("🚀 Running implementation crew...\n")
    require_llm()  # DT-08: fail early, with a message, if there is no LLM
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Implementation complete!\n")
    print(result_str)

    # --- Save output ---
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        report_file = out_path / "implementation_report.md"
        report_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Report saved to: {report_file.resolve()}")
    else:
        # Save to default location
        output_path = Path(__file__).resolve().parent.parent / "outputs"
        output_path.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = output_path / f"implementation_{timestamp}.md"
        report_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Report saved to: {report_file.resolve()}")


if __name__ == "__main__":
    main()
