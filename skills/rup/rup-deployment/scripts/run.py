#!/usr/bin/env python3
"""
RUP-Deployment — RUP Deployment Crew (self-contained)

Builds a CrewAI crew with embedded agents (no external dependency) for the RUP
Deployment discipline. Agents are defined inline, matching the RUP specification
(Kruchten, "The Rational Unified Process: An Introduction", 3rd ed.).

Usage:
  python run.py "briefing for the Deployment discipline"
  python run.py "briefing" --phase Inception --dry-run
  python run.py --input context.txt --output deployment.md
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
    "deployment-manager": {
        "role": 'Deployment Manager',
        "goal": 'Produce the Deployment Plan, Installation Material and the Release Description / Release Notes.',
        "backstory": 'Deployment manager who lands the product: you plan the cutover, contingency and data migration, assemble installation material, and document the release and its known defects.',
    },
    "technical-writer": {
        "role": 'Technical Writer',
        "goal": 'Produce the User Manual / User Documentation and the Training Material.',
        "backstory": 'Technical writer who speaks to end users: you derive manuals, contextual help and operational guides from the use cases, and author the training materials and exercises.',
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
TITLE = 'Deployment'

# ═════════════════════════════════════════════════════════════════════════
# Crew builder
# ═════════════════════════════════════════════════════════════════════════

def build_crew(briefing: str, phase: str = "Elaboration"):
    """Build a CrewAI crew for the RUP Deployment discipline."""

    deployment_manager = get_agent("deployment-manager")
    technical_writer = get_agent("technical-writer")

    deployment_manager_task = Task(
        description=f"""
PHASE: {phase}

BRIEFING / CONTEXT:
{briefing}

YOUR MISSION: Plan and execute the delivery of the final product to users, managing cutovers, data migrations and commercial releases.

Produce the artifacts you own: Deployment Plan, Installation Material, Release Description / Release Notes.

Produce each artifact as a clearly delimited, self-contained section.
Follow the RUP conventions for that artifact type. Be specific and
traceable; where information is missing, state assumptions explicitly
rather than inventing facts.
        """,
        expected_output="The RUP artifacts: Deployment Plan, Installation Material, Release Description / Release Notes. Each section self-contained, with assumptions and open questions called out.",
        agent=deployment_manager,
    )

    technical_writer_task = Task(
        description=f"""
PHASE: {phase}

BRIEFING / CONTEXT:
{briefing}

YOUR MISSION: Write all end-user documentation and training material, derived directly from the use cases.

Produce the artifacts you own: User Manual / User Documentation, Training Material.

Produce each artifact as a clearly delimited, self-contained section.
Follow the RUP conventions for that artifact type. Be specific and
traceable; where information is missing, state assumptions explicitly
rather than inventing facts.
        """,
        expected_output="The RUP artifacts: User Manual / User Documentation, Training Material. Each section self-contained, with assumptions and open questions called out.",
        agent=technical_writer,
    )

    crew = Crew(
        agents=[deployment_manager, technical_writer],
        tasks=[deployment_manager_task, technical_writer_task],
        process=Process.sequential,
        verbose=True,
    )
    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="RUP Deployment discipline crew (self-contained)",
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
