#!/usr/bin/env python3
"""
RUP-Implementation — RUP Implementation Crew (self-contained)

Builds a CrewAI crew with embedded agents (no external dependency) for the RUP
Implementation discipline. Agents are defined inline, matching the RUP specification
(Kruchten, "The Rational Unified Process: An Introduction", 3rd ed.).

Usage:
  python run.py "briefing for the Implementation discipline"
  python run.py "briefing" --phase Inception --dry-run
  python run.py --input context.txt --output implementation.md
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
    "system-integrator": {
        "role": 'System Integrator',
        "goal": 'Produce the Integration Build Plan and the integrated, publishable Builds.',
        "backstory": 'System integrator allergic to big-bang integration: you sequence subsystem builds per iteration, execute integrations continuously, and publish builds ready for verification testing.',
    },
    "implementer": {
        "role": 'Implementer',
        "goal": 'Produce Implementation Elements (source, binaries), Implementation Subsystems, Developer Tests and Test Stubs/Testability Elements.',
        "backstory": 'Implementer who turns design into code: you write source, compile binaries, organize implementation subsystems along the architectural layers, and ship developer tests and testability hooks with every component.',
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
TITLE = 'Implementation'

# ═════════════════════════════════════════════════════════════════════════
# Crew builder
# ═════════════════════════════════════════════════════════════════════════

def build_crew(briefing: str, phase: str = "Elaboration"):
    """Build a CrewAI crew for the RUP Implementation discipline."""

    system_integrator = get_agent("system-integrator")
    implementer = get_agent("implementer")

    system_integrator_task = Task(
        description=f"""
PHASE: {phase}

BRIEFING / CONTEXT:
{briefing}

YOUR MISSION: Plan and execute the incremental software integration strategy, avoiding late big-bang integrations.

Produce the artifacts you own: Integration Build Plan, Build.

Produce each artifact as a clearly delimited, self-contained section.
Follow the RUP conventions for that artifact type. Be specific and
traceable; where information is missing, state assumptions explicitly
rather than inventing facts.
        """,
        expected_output="The RUP artifacts: Integration Build Plan, Build. Each section self-contained, with assumptions and open questions called out.",
        agent=system_integrator,
    )

    implementer_task = Task(
        description=f"""
PHASE: {phase}

BRIEFING / CONTEXT:
{briefing}

YOUR MISSION: Write source code, build binaries, compile, generate components and run unit tests.

Produce the artifacts you own: Implementation Elements, Implementation Subsystems, Developer Tests, Test Stubs & Testability Elements.

Produce each artifact as a clearly delimited, self-contained section.
Follow the RUP conventions for that artifact type. Be specific and
traceable; where information is missing, state assumptions explicitly
rather than inventing facts.
        """,
        expected_output="The RUP artifacts: Implementation Elements, Implementation Subsystems, Developer Tests, Test Stubs & Testability Elements. Each section self-contained, with assumptions and open questions called out.",
        agent=implementer,
    )

    crew = Crew(
        agents=[system_integrator, implementer],
        tasks=[system_integrator_task, implementer_task],
        process=Process.sequential,
        verbose=True,
    )
    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="RUP Implementation discipline crew (self-contained)",
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
