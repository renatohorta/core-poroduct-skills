#!/usr/bin/env python3
"""
RUP-Test — RUP Test Crew (self-contained)

Builds a CrewAI crew with embedded agents (no external dependency) for the RUP
Test discipline. Agents are defined inline, matching the RUP specification
(Kruchten, "The Rational Unified Process: An Introduction", 3rd ed.).

Usage:
  python run.py "briefing for the Test discipline"
  python run.py "briefing" --phase Inception --dry-run
  python run.py --input context.txt --output test.md
"""

import argparse
import sys
from pathlib import Path
try:
    from crewai import Agent, Task, Crew, Process
except ImportError:  # the lib is only required for real execution, not --help
    Agent = Task = Crew = Process = None
import sys as _sys
from pathlib import Path as _Path
_SKILLS_ROOT = _Path(__file__).resolve().parent.parent.parent  # skills/rup/
if str(_SKILLS_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_SKILLS_ROOT))
from _shared.llm import (build_crew_llm, require_crewai, require_llm,
                         setup_console)

setup_console()  # UTF-8 on stdout/stderr (Windows console is cp1252)
# ═════════════════════════════════════════════════════════════════════════
# EMBEDDED AGENTS (self-contained — no dependency on an external dir)
# ═════════════════════════════════════════════════════════════════════════

AGENTS = {
    "test-manager": {
        "role": 'Test Manager',
        "goal": 'Produce the Test Plan and the Test Evaluation Summary.',
        "backstory": 'Test manager who protects test independence: you scope the test effort, allocate resources and milestones, and compile the analytic Test Evaluation Summary with coverage, defect rates and readiness.',
    },
    "test-analyst": {
        "role": 'Test Analyst',
        "goal": 'Produce the Test Ideas List, Test Cases, Test Data and the Workload Analysis Model.',
        "backstory": 'Test analyst who hunts for failure hypotheses: you derive test cases directly from use cases and requirements, design the data sets, and model the workload for performance testing.',
    },
    "test-designer": {
        "role": 'Test Designer',
        "goal": 'Produce the Test Strategy, the Test Automation Architecture, the Test Environment Configuration and the Test Interface Specification.',
        "backstory": 'Test designer who engineers the test architecture: you choose the tooling, define the automation framework, specify the environments, and state the testability requirements the software must expose.',
    },
    "tester": {
        "role": 'Tester',
        "goal": 'Produce Test Scripts, Test Suites, the Test Log and the Test Results.',
        "backstory": 'Tester who executes and records: you run automated and manual test scripts, keep raw telemetry in the Test Log, and report objective pass/fail results and regressions.',
    },
}



def get_agent(slug: str) -> Agent:
    """Get a CrewAI Agent from the embedded definitions."""
    _crew_llm = build_crew_llm()
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


PHASES = ["Inception", "Elaboration", "Construction", "Transition"]
TITLE = 'Test'

# ═════════════════════════════════════════════════════════════════════════
# Crew builder
# ═════════════════════════════════════════════════════════════════════════

def build_crew(briefing: str, phase: str = "Elaboration"):
    """Build a CrewAI crew for the RUP Test discipline."""

    test_manager = get_agent("test-manager")
    test_analyst = get_agent("test-analyst")
    test_designer = get_agent("test-designer")
    tester = get_agent("tester")

    test_manager_task = Task(
        description=f"""
PHASE: {phase}

BRIEFING / CONTEXT:
{briefing}

YOUR MISSION: Supervise the overall test success, guarantee the independence of the quality assessment, and manage test resources and consolidated reports.

Produce the artifacts you own: Test Plan, Test Evaluation Summary.

Produce each artifact as a clearly delimited, self-contained section.
Follow the RUP conventions for that artifact type. Be specific and
traceable; where information is missing, state assumptions explicitly
rather than inventing facts.
        """,
        expected_output="The RUP artifacts: Test Plan, Test Evaluation Summary. Each section self-contained, with assumptions and open questions called out.",
        agent=test_manager,
    )

    test_analyst_task = Task(
        description=f"""
PHASE: {phase}

BRIEFING / CONTEXT:
{briefing}

YOUR MISSION: Identify test ideas, design functional and stress test cases, and define the verification data sets.

Produce the artifacts you own: Test Ideas List, Test Cases, Test Data, Workload Analysis Model.

Produce each artifact as a clearly delimited, self-contained section.
Follow the RUP conventions for that artifact type. Be specific and
traceable; where information is missing, state assumptions explicitly
rather than inventing facts.
        """,
        expected_output="The RUP artifacts: Test Ideas List, Test Cases, Test Data, Workload Analysis Model. Each section self-contained, with assumptions and open questions called out.",
        agent=test_analyst,
    )

    test_designer_task = Task(
        description=f"""
PHASE: {phase}

BRIEFING / CONTEXT:
{briefing}

YOUR MISSION: Design the technical architecture of the tests, define the automation frameworks and specify the test interfaces.

Produce the artifacts you own: Test Strategy, Test Automation Architecture, Test Environment Configuration, Test Interface Specification.

Produce each artifact as a clearly delimited, self-contained section.
Follow the RUP conventions for that artifact type. Be specific and
traceable; where information is missing, state assumptions explicitly
rather than inventing facts.
        """,
        expected_output="The RUP artifacts: Test Strategy, Test Automation Architecture, Test Environment Configuration, Test Interface Specification. Each section self-contained, with assumptions and open questions called out.",
        agent=test_designer,
    )

    tester_task = Task(
        description=f"""
PHASE: {phase}

BRIEFING / CONTEXT:
{briefing}

YOUR MISSION: Execute automated and manual tests, document anomalous behavior and log formal defect reports.

Produce the artifacts you own: Test Scripts, Test Suites, Test Log, Test Results.

Produce each artifact as a clearly delimited, self-contained section.
Follow the RUP conventions for that artifact type. Be specific and
traceable; where information is missing, state assumptions explicitly
rather than inventing facts.
        """,
        expected_output="The RUP artifacts: Test Scripts, Test Suites, Test Log, Test Results. Each section self-contained, with assumptions and open questions called out.",
        agent=tester,
    )

    crew = Crew(
        agents=[test_manager, test_analyst, test_designer, tester],
        tasks=[test_manager_task, test_analyst_task, test_designer_task, tester_task],
        process=Process.sequential,
        verbose=True,
    )
    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="RUP Test discipline crew (self-contained)",
    )
    parser.add_argument("briefing", nargs="?",
                        help="Briefing / business demand for the discipline")
    parser.add_argument("--input", dest="input_file",
                        help="File with the briefing/context (alternative to the positional)")
    parser.add_argument("--phase", choices=PHASES, default="Elaboration",
                        help="RUP phase (default: Elaboration)")
    parser.add_argument("--output", "-o", help="File to write the result to")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only builds the crew and shows the agents, without running")
    args = parser.parse_args()

    require_crewai()

    briefing = args.briefing
    if args.input_file:
        briefing = Path(args.input_file).read_text(encoding="utf-8", errors="replace")
    if not briefing:
        parser.print_help()
        print("\n❌ Error: provide the briefing (positional, --input, or a file)")
        sys.exit(1)

    print(f"\n🏛️  RUP discipline: {TITLE}")
    print(f"📐 Phase: {args.phase}")
    print(f"🤖 Agents: {len(AGENTS)}")
    print()

    crew = build_crew(briefing, args.phase)

    if args.dry_run:
        print("🧪 DRY RUN — crew built, agents:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
        print("\n✅ Crew ready. Remove --dry-run to execute.")
        return

    print("🚀 Running crew...\n")
    require_llm()
    result = crew.kickoff()
    print(f"\n✅ Final result:\n{result}")
    if args.output:
        Path(args.output).write_text(str(result), encoding="utf-8")
        print(f"\n📄 Result written to {args.output}")


if __name__ == "__main__":
    main()
