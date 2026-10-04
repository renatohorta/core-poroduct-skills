#!/usr/bin/env python3
"""
RUP-Analysis & Design — RUP Analysis & Design Crew (self-contained)

Builds a CrewAI crew with embedded agents (no external dependency) for the RUP
Analysis & Design discipline. Agents are defined inline, matching the RUP specification
(Kruchten, "The Rational Unified Process: An Introduction", 3rd ed.).

Usage:
  python run.py "briefing for the Analysis & Design discipline"
  python run.py "briefing" --phase Inception --dry-run
  python run.py --input context.txt --output analysis-design.md
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
    "software-architect": {
        "role": 'Software Architect',
        "goal": 'Produce the Software Architecture Document (4+1 views), the Architectural Prototype and the Design Guidelines.',
        "backstory": 'Software architect who owns the architecture in the large: you synthesize the 4+1 views (logical, implementation, process, deployment, use-case), govern the architectural prototype, and set the design mechanisms.',
    },
    "designer": {
        "role": 'Designer',
        "goal": 'Produce the Design Model (UML), Use-Case Realizations, Design Classes, Design Subsystems/Packages, Interfaces and, when configured, the Analysis Model.',
        "backstory": 'Designer who works inside the architecture: you realize each use case white-box with interaction diagrams, specify classes, subsystems and interfaces rigorously, and keep the design construction-ready.',
    },
    "user-interface-designer": {
        "role": 'User-Interface Designer',
        "goal": 'Produce Storyboards, the Navigation Map and the User-Interface Prototype.',
        "backstory": 'UI designer focused on ergonomics and navigation: you sketch storyboards tied to use-case steps, map the navigation graph, and build exploratory prototypes to validate with real users.',
    },
    "database-designer": {
        "role": 'Database Designer',
        "goal": 'Produce the Data Model (tables, constraints, indexes) and the object-relational mapping strategy.',
        "backstory": 'Database designer who owns persistence: you shape tables, constraints, keys and indexes, and define the object-relational mapping between design classes and the physical schema.',
    },
    "capsule-designer": {
        "role": 'Capsule Designer',
        "goal": 'Produce Capsules (dedicated threads + I/O ports), Protocols, Events and Signals (asynchronous messages, sequences and state machines).',
        "backstory": 'Capsule designer specialized in real-time and reactive systems: you model capsules with ports and dedicated threads, and specify the protocols, events and state machines for timing-critical behavior.',
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
TITLE = 'Analysis & Design'

# ═════════════════════════════════════════════════════════════════════════
# Crew builder
# ═════════════════════════════════════════════════════════════════════════

def build_crew(briefing: str, phase: str = "Elaboration"):
    """Build a CrewAI crew for the RUP Analysis & Design discipline."""

    software_architect = get_agent("software-architect")
    designer = get_agent("designer")
    user_interface_designer = get_agent("user-interface-designer")
    database_designer = get_agent("database-designer")
    capsule_designer = get_agent("capsule-designer")

    software_architect_task = Task(
        description=f"""
PHASE: {phase}

BRIEFING / CONTEXT:
{briefing}

YOUR MISSION: Define and maintain the conceptual integrity, robustness and structural feasibility of the system in the large (breadth), synthesizing the architecture.

Produce the artifacts you own: Software Architecture Document (SAD) — 4+1 Views, Architectural Prototype / Proof-of-Concept, Design Guidelines.

Produce each artifact as a clearly delimited, self-contained section.
Follow the RUP conventions for that artifact type. Be specific and
traceable; where information is missing, state assumptions explicitly
rather than inventing facts.
        """,
        expected_output="The RUP artifacts: Software Architecture Document (SAD) — 4+1 Views, Architectural Prototype / Proof-of-Concept, Design Guidelines. Each section self-contained, with assumptions and open questions called out.",
        agent=software_architect,
    )

    designer_task = Task(
        description=f"""
PHASE: {phase}

BRIEFING / CONTEXT:
{briefing}

YOUR MISSION: Transform the behavioral requirements of use cases into detailed class, interface and collaboration structures ready for construction.

Produce the artifacts you own: Design Model, Use-Case Realizations, Design Classes, Design Subsystems & Design Packages, Interfaces, Analysis Model.

Produce each artifact as a clearly delimited, self-contained section.
Follow the RUP conventions for that artifact type. Be specific and
traceable; where information is missing, state assumptions explicitly
rather than inventing facts.
        """,
        expected_output="The RUP artifacts: Design Model, Use-Case Realizations, Design Classes, Design Subsystems & Design Packages, Interfaces, Analysis Model. Each section self-contained, with assumptions and open questions called out.",
        agent=designer,
    )

    user_interface_designer_task = Task(
        description=f"""
PHASE: {phase}

BRIEFING / CONTEXT:
{briefing}

YOUR MISSION: Model the graphical interfaces with exclusive focus on ergonomics, navigation flow and user goals.

Produce the artifacts you own: Storyboards, Navigation Map, User-Interface Prototype.

Produce each artifact as a clearly delimited, self-contained section.
Follow the RUP conventions for that artifact type. Be specific and
traceable; where information is missing, state assumptions explicitly
rather than inventing facts.
        """,
        expected_output="The RUP artifacts: Storyboards, Navigation Map, User-Interface Prototype. Each section self-contained, with assumptions and open questions called out.",
        agent=user_interface_designer,
    )

    database_designer_task = Task(
        description=f"""
PHASE: {phase}

BRIEFING / CONTEXT:
{briefing}

YOUR MISSION: Design and optimize the storage schemas, keys, indexes and integrity of the system's persistent data.

Produce the artifacts you own: Data Model, Object-Relational Mapping.

Produce each artifact as a clearly delimited, self-contained section.
Follow the RUP conventions for that artifact type. Be specific and
traceable; where information is missing, state assumptions explicitly
rather than inventing facts.
        """,
        expected_output="The RUP artifacts: Data Model, Object-Relational Mapping. Each section self-contained, with assumptions and open questions called out.",
        agent=database_designer,
    )

    capsule_designer_task = Task(
        description=f"""
PHASE: {phase}

BRIEFING / CONTEXT:
{briefing}

YOUR MISSION: Model the reactive behavior and event-driven concurrent flows for components with rigid timing requirements (real-time / reactive systems).

Produce the artifacts you own: Capsules, Protocols, Events & Signals.

Produce each artifact as a clearly delimited, self-contained section.
Follow the RUP conventions for that artifact type. Be specific and
traceable; where information is missing, state assumptions explicitly
rather than inventing facts.
        """,
        expected_output="The RUP artifacts: Capsules, Protocols, Events & Signals. Each section self-contained, with assumptions and open questions called out.",
        agent=capsule_designer,
    )

    crew = Crew(
        agents=[software_architect, designer, user_interface_designer, database_designer, capsule_designer],
        tasks=[software_architect_task, designer_task, user_interface_designer_task, database_designer_task, capsule_designer_task],
        process=Process.sequential,
        verbose=True,
    )
    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="RUP Analysis & Design discipline crew (self-contained)",
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
