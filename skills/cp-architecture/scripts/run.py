#!/usr/bin/env python3
"""
cp-architecture — Software Architecture and Design Crew (self-contained)

Creates a CrewAI crew with specialized agents to define architecture,
model data, design APIs, design UX and validate technical decisions.

Usage:
  python run.py "scheduling system for clinics"
  python run.py --briefing "I need an app to manage inventory" --output architecture.md
  python run.py --input requirements.md
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
    "software-architect": {
        "role": "Software Architect",
        "goal": "Define the system architecture, patterns, architectural styles and document decisions in ADRs",
        "backstory": (
            "Senior software architect with over 15 years of experience in projects of all sizes. "
            "You have seen systems born, grow and die because of poor architectural decisions. "
            "You master styles such as monolith, microservices, modular monolith, event-driven architecture, "
            "and hexagonal architecture. You know there is no silver bullet — every decision has trade-offs. "
            "You document each decision as an ADR (Architecture Decision Record) with context, decision and consequences. "
            "You think about scalability, maintainability, coupling and cohesion before writing a single line of code."
        ),
    },
    "data-architect": {
        "role": "Data Architect",
        "goal": "Model the database, define schema, relationships, indexes and migration strategy",
        "backstory": (
            "DBA and data architect with vast experience in relational and NoSQL modeling. "
            "You think about performance and consistency from the very first schema. "
            "You know normalization, strategic denormalization, composite indexes, partitioning, "
            "and migration strategies (zero-downtime, blue-green). "
            "You know when to use SQL vs NoSQL, when to denormalize for performance, "
            "and how to model data to support future queries without rewriting the schema. "
            "Your motto: 'A well-modeled schema saves months of refactoring.'"
        ),
    },
    "api-architect": {
        "role": "API Architect",
        "goal": "Design REST/GraphQL API contracts, specify endpoints, payloads, versioning and security",
        "backstory": (
            "API design specialist who has integrated dozens of systems throughout their career. "
            "You master REST, GraphQL, gRPC and WebSockets. "
            "You design APIs thinking about consistency, semantic versioning, pagination, "
            "rate limiting, authentication and documentation (OpenAPI/Swagger). "
            "You know a good API is intuitive — the consumer should not need to read documentation to guess the endpoint. "
            "You advocate for strong contracts with rigorous validation and clear error messages. "
            "Your mantra: 'API design is UX for developers.'"
        ),
    },
    "ux-architect": {
        "role": "UX Architect",
        "goal": "Design user flows, journeys, navigation prototypes and validate the experience before code",
        "backstory": (
            "User experience architect who thinks about the journey before the code. "
            "You map complete flows (user flows), identify friction points, "
            "and design navigation prototypes that guide development. "
            "You work with concepts such as user journey, screens, states (loading, empty, error, edge cases), "
            "and usability principles (Nielsen heuristics). "
            "You know a bad experience can kill a technically perfect product. "
            "Your goal: ensure the architecture supports the experience, not the other way around."
        ),
    },
    "technical-reviewer": {
        "role": "Technical Reviewer",
        "goal": "Validate architectural decisions, identify risks, point out inconsistencies and suggest alternatives",
        "backstory": (
            "Skeptical senior software engineer who questions every decision. "
            "You have seen beautiful architectures on paper fail in practice. "
            "You analyze each decision under a magnifying glass: scalability, operational cost, accidental complexity, "
            "time-to-market, technical debt, and alignment with requirements. "
            "You do not accept 'we have always done it this way' as a justification. "
            "Your job is not to approve blindly — it is to ensure the team has considered "
            "the risks and trade-offs before implementing. "
            "Issue PASS only if the architecture is solid, documented and justified."
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
    """Build a CrewAI crew for software architecture and design."""

    architect = get_agent("software-architect")
    data = get_agent("data-architect")
    api = get_agent("api-architect")
    ux = get_agent("ux-architect")
    reviewer = get_agent("technical-reviewer")

    # --- Task 1: Requirements analysis and architecture definition ---
    task_architecture = Task(
        description=f"""
        SYSTEM BRIEFING / REQUIREMENTS:
        {briefing}

        YOUR JOB — ARCHITECTURE DEFINITION:

        Based on the provided requirements, produce:

        1. **Architectural Requirements Analysis**
           - Critical functional requirements that impact the architecture
           - Non-functional requirements (performance, scalability, security, availability)
           - Technical and business constraints

        2. **Architectural Decision (ADR 001)**
           - Context: why this decision is necessary
           - Decision: chosen architectural style (monolith, microservices, modular monolith, etc.)
           - Consequences: pros, cons, trade-offs
           - Alternatives considered and why they were discarded

        3. **C4 Diagram — Level 1 (Context)**
           - Describe the system and its external users/actors
           - Relationships between the system and the outside world

        4. **C4 Diagram — Level 2 (Containers)**
           - Which containers/applications make up the system
           - Responsibilities of each container
           - Communication between containers (protocols, synchronous/asynchronous)

        5. **Architectural Patterns**
           - Chosen patterns (e.g.: CQRS, Event Sourcing, Saga, Repository, etc.)
           - Justification for each pattern

        6. **ADR 002: Technologies**
           - Main stack (language, framework, database, message broker, etc.)
           - Justification for each technology choice

        Format: markdown with clear sections. Each ADR must follow the format:
        ## ADR-N: Title
        - **Context**: ...
        - **Decision**: ...
        - **Consequences**: ...
        - **Alternatives**: ...
        """,
        expected_output="Architecture document: architectural requirements analysis, ADRs, C4 diagram levels 1-2, patterns and technology stack",
        agent=architect,
    )

    # --- Task 2: Data modeling ---
    task_data = Task(
        description=f"""
        SYSTEM BRIEFING / REQUIREMENTS:
        {briefing}

        YOUR JOB — DATA MODELING:

        Based on the defined architecture, produce:

        1. **Conceptual Model**
           - Main domain entities
           - Relationships between entities (1:N, N:N, 1:1)
           - Cardinalities

        2. **Logical Model (Schema)**
           - Tables/collections with columns/fields
           - Data types
           - Primary and foreign keys
           - Recommended indexes (simple and composite)
           - Constraints and integrity rules

        3. **Storage Strategy**
           - SQL vs NoSQL: justification
           - If relational: entity-relationship diagram (textual)
           - If NoSQL: document/aggregate, access patterns
           - Partitioning strategy (if applicable)

        4. **Migrations**
           - Migration strategy (zero-downtime?)
           - Schema versioning
           - Rollback plan

        5. **Performance Considerations**
           - Most important indexes
           - Critical queries and how to optimize them
           - Cache strategy (if applicable)

        Format: markdown with tables for entities and indexes.
        """,
        expected_output="Complete data model: entities, schema, indexes, storage and migration strategy",
        agent=data,
    )

    # --- Task 3: API design ---
    task_api = Task(
        description=f"""
        SYSTEM BRIEFING / REQUIREMENTS:
        {briefing}

        YOUR JOB — API DESIGN:

        Based on the defined architecture and data model, produce:

        1. **API Strategy**
           - REST, GraphQL, gRPC or hybrid? Justification
           - Versioning (URL, header, or semantic)
           - Standard response format

        2. **API Contracts**
           For each endpoint/operation:
           - HTTP method and path
           - Parameters (query, path, body)
           - Request payload (example)
           - Response payload (example)
           - Status codes (200, 201, 400, 404, 500, etc.)
           - Required authentication/authorization

        3. **Error Handling**
           - Standardized error format
           - Business error codes
           - Friendly messages

        4. **Pagination, Filters and Sorting**
           - Pagination strategy (cursor vs offset)
           - Filter pattern
           - Sorting pattern

        5. **Security**
           - Authentication (JWT, OAuth2, API Key?)
           - Rate limiting
           - Input validation
           - Protection against common attacks

        6. **Documentation**
           - OpenAPI/Swagger: schema descriptions
           - Request and response examples for each endpoint

        Format: markdown with JSON examples for payloads.
        """,
        expected_output="Complete API contracts: endpoints, payloads, errors, pagination, security and OpenAPI documentation",
        agent=api,
    )

    # --- Task 4: UX/Flow design ---
    task_ux = Task(
        description=f"""
        SYSTEM BRIEFING / REQUIREMENTS:
        {briefing}

        YOUR JOB — UX DESIGN / USER FLOWS:

        Based on the defined architecture, data and APIs, produce:

        1. **Personas / User Profiles**
           - Who are the system's users
           - Goals of each profile
           - Technical knowledge level

        2. **User Flows**
           For each main feature:
           - Happy path
           - Alternative flows
           - Error flows
           - Decision points

        3. **Navigation Map**
           - Main screens/views
           - Transitions between screens
           - Navigation hierarchy

        4. **Interface States**
           - Initial / empty state
           - Loading state
           - Error state
           - Success state
           - Edge cases

        5. **UX Recommendations**
           - Applicable usability heuristics
           - Recommended interaction patterns
           - Accessibility (WCAG)
           - Responsiveness / mobile-first

        Format: markdown with flows described textually (pseudo-flowchart).
        """,
        expected_output="UX document: personas, user flows, navigation map, interface states and usability recommendations",
        agent=ux,
    )

    # --- Task 5: Technical review and validation ---
    task_review = Task(
        description=f"""
        SYSTEM BRIEFING / REQUIREMENTS:
        {briefing}

        YOUR JOB — TECHNICAL REVIEW AND ARCHITECTURAL VALIDATION:

        Review the ENTIRE produced architecture document (architecture, data, APIs, UX)
        and evaluate the following aspects:

        1. **Internal Consistency**
           - Is the defined architecture consistent with the requirements?
           - Does the data model support the designed APIs?
           - Do the APIs support the designed UX flows?
           - Are there contradictions between the decisions?

        2. **Risk Analysis**
           - Identified technical risks
           - Scalability risks
           - Operational cost risks
           - Time-to-market risks
           - Future technical debt risks

        3. **Trade-off Evaluation**
           - For each architectural decision, were the trade-offs well documented?
           - Are there alternatives that should have been considered?
           - Is the taken decision the best for the context?

        4. **Points of Attention**
           - What could go wrong in the implementation?
           - What needs to be validated with a prototype/PoC before implementing?
           - Improvement suggestions

        5. **Final Verdict**
           - **PASS**: The architecture is solid, documented and ready for implementation
           - **FAIL**: The architecture needs fixes before moving forward
           - If FAIL, explicitly list what needs to be fixed and why

        Be rigorous. A FAIL now is better than a crisis in production.
        """,
        expected_output="Technical review report: risk analysis, trade-offs, points of attention and PASS/FAIL verdict",
        agent=reviewer,
    )

    # --- Crew ---
    crew = Crew(
        agents=[architect, data, api, ux, reviewer],
        tasks=[task_architecture, task_data, task_api, task_ux, task_review],
        process=Process.sequential,
        verbose=True,
    )

    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-architecture: Software Architecture and Design Crew (self-contained)",
    )
    parser.add_argument(
        "briefing",
        nargs="?",
        help="Client briefing / problem description / system requirements",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="File with the briefing (alternative to the positional argument)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file to save the architecture document",
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
        print("\n❌ Error: provide the system briefing (argument or --input)")
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

    print("🚀 Running architecture and design crew...\n")
    require_llm()  # DT-08: fail early, with a message, if there is no LLM
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Architecture Document generated!\n")
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
        out_file = output_dir / f"architecture_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Saved to: {out_file.resolve()}")


if __name__ == "__main__":
    main()
