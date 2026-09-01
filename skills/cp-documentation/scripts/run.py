#!/usr/bin/env python3
"""
cp-documentation — Software Documentation Crew (self-contained)

Creates a CrewAI crew with specialized agents to generate technical,
API, user documentation and software diagrams.

Usage:
  python run.py "scheduling API for clinics"
  python run.py --input description.txt --output docs/complete.md
  python run.py "orders REST API" --mode tech
  python run.py "e-commerce system" --mode diagrams --dry-run
"""

import argparse
import sys
import json
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
    "technical-writer": {
        "role": "Technical Writer",
        "goal": (
            "Analyze what needs to be documented and produce clear, "
            "complete, useful technical and API documentation for developers"
        ),
        "backstory": (
            "Senior technical writer with over 12 years of experience in "
            "software documentation. You turn complex code, "
            "intricate architectures and detail-heavy APIs into "
            "clear, precise, actionable documentation. "
            "You understand both technology and communication — "
            "you know how to explain complex concepts without oversimplifying. "
            "Your READMEs are references, your API docs are so good "
            "that developers don't need to read the source code. "
            "You document: architecture, components, data flows, "
            "technical decisions, endpoints, schemas, authentication, "
            "request/response examples, error codes and best practices."
        ),
    },
    "user-writer": {
        "role": "User Writer",
        "goal": (
            "Produce manuals, guides, FAQs and tutorials that any "
            "end user can understand and follow"
        ),
        "backstory": (
            "Writer specialized in end-user documentation. "
            "You have the rare gift of translating technical jargon into "
            "simple, accessible language. Your motto: 'If the user needs a "
            "tutorial to understand the tutorial, you failed.' "
            "You write step-by-step installation guides, usage "
            "manuals with practical examples, FAQs that actually answer "
            "the questions users ask, and tutorials that "
            "work on the first try. "
            "You always include: prerequisites, clear instructions, "
            "real-world examples, troubleshooting for common problems and "
            "a glossary of terms."
        ),
    },
    "diagrammer": {
        "role": "Diagrammer",
        "goal": (
            "Create diagrams, flowcharts and visuals that communicate "
            "architecture and flows clearly and intuitively"
        ),
        "backstory": (
            "Technical designer specialized in visual communication. "
            "You know a good diagram is worth more than a thousand words "
            "of documentation. You create Mermaid and PlantUML diagrams "
            "that are self-explanatory, beautiful and accurate. "
            "You produce: system architecture diagrams, "
            "sequence diagrams for API flows, "
            "entity-relationship diagrams for the database, "
            "business process flowcharts, "
            "component and deployment diagrams. "
            "Every diagram you create has: title, legend when "
            "necessary, consistent colors, and explanatory annotations. "
            "Your diagrams are so good they become project references."
        ),
    },
    "documentation-reviewer": {
        "role": "Documentation Reviewer",
        "goal": (
            "Review all documentation to ensure clarity, "
            "completeness, consistency and spelling correctness"
        ),
        "backstory": (
            "Detail-oriented, relentless reviewer with over 15 years of "
            "experience in technical documentation. You don't let any "
            "spelling error, missing information, "
            "inconsistency between sections, or ambiguity pass. "
            "You check: spelling and grammar, clarity and "
            "objectivity, completeness (nothing left out?), "
            "consistency (terms used the same way throughout the "
            "document?), functional examples, links and cross-"
            "references, tone and voice appropriate to the target audience. "
            "Your verdict is PASS or FAIL. If FAIL, you list "
            "exactly what needs to be fixed. "
            "You are demanding but fair — quality documentation "
            "is a right of those who use the software."
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
    """Build a CrewAI crew for software documentation."""

    technical_writer = get_agent("technical-writer")
    user_writer = get_agent("user-writer")
    diagrammer = get_agent("diagrammer")
    reviewer = get_agent("documentation-reviewer")

    # --- Task 1: Analysis (always present) ---
    analysis = Task(
        description=f"""
        DESCRIPTION OF WHAT TO DOCUMENT:
        {description}

        YOUR JOB — DOCUMENTATION SCOPE ANALYSIS:
        1. Analyze the provided description and identify:
           - What the software/system/API is
           - Target audience of the documentation (developers, end users, both)
           - Technologies involved
           - Main features
           - Endpoints/APIs (if applicable)
           - Data flows
        2. Define the scope of the necessary documentation
        3. Identify mandatory sections
        4. List assumptions and information that need confirmation

        OUTPUT FORMAT:
        ## Documentation Scope Analysis
        - Software/System: [description]
        - Target audience: [who]
        - Technologies: [list]
        - Features: [list]
        - Necessary documentation sections: [list]
        - Assumptions: [list]
        - Missing information: [list]
        """,
        expected_output=(
            "Complete documentation scope analysis: software, "
            "target audience, technologies, features, necessary sections, "
            "assumptions and missing information"
        ),
        agent=technical_writer,
    )

    tasks = [analysis]

    # --- Task 2: Technical and API Documentation ---
    if mode in ("full", "tech", "api"):
        doc_technical = Task(
            description=f"""
            DESCRIPTION OF WHAT TO DOCUMENT:
            {description}

            YOUR JOB — TECHNICAL AND API DOCUMENTATION:
            Based on the scope analysis, produce the complete technical documentation:

            1. **README** — Project overview, purpose, status, how to contribute
            2. **Architecture** — Description of the architecture, components, patterns used
            3. **Technologies** — Technology stack with versions
            4. **Project Structure** — Directory and module organization
            5. **Configuration** — Environment variables, dependencies, setup
            6. **Installation and Execution** — Step-by-step to run the project
            7. **Tests** — How to run and interpret the tests

            If applicable (full or api mode), also include:
            8. **API Documentation** — For each endpoint:
               - HTTP method and URL
               - Description of what it does
               - Parameters (path, query, body)
               - Headers (authentication, content-type)
               - Request example (curl)
               - Response example (JSON)
               - Possible error codes
               - Rate limiting (if applicable)

            Write in clear, objective English. Use markdown.
            Include code blocks with syntax highlighting.
            """,
            expected_output=(
                "Complete technical documentation: README, architecture, "
                "technologies, structure, configuration, installation, tests "
                "and API documentation (when applicable)"
            ),
            agent=technical_writer,
        )
        tasks.append(doc_technical)

    # --- Task 3: User Documentation ---
    if mode in ("full", "user"):
        doc_user = Task(
            description=f"""
            DESCRIPTION OF WHAT TO DOCUMENT:
            {description}

            YOUR JOB — USER DOCUMENTATION:
            Based on the scope analysis and technical documentation, produce
            the documentation aimed at the end user:

            1. **Quick Start Guide** — The minimum the user needs
               to know to start using it in 5 minutes
            2. **User Manual** — Main features explained
               step by step with practical examples
            3. **FAQ** — Frequently asked questions with clear, direct answers
            4. **Troubleshooting** — Common problems and how to solve them
            5. **Glossary** — Technical terms explained in simple language

            Rules:
            - Simple, accessible language (avoid technical jargon)
            - Real-world examples the user recognizes
            - Numbered steps for sequential actions
            - Screenshots described in text (e.g.: "Click the 'Save' button")
            - Friendly, patient tone
            - Each section must be independent (the user can skip sections)

            Write in clear English. Use markdown.
            """,
            expected_output=(
                "Complete user documentation: quick start guide, "
                "user manual, FAQ, troubleshooting and glossary"
            ),
            agent=user_writer,
        )
        tasks.append(doc_user)

    # --- Task 4: Diagrams ---
    if mode in ("full", "diagrams"):
        diagrams = Task(
            description=f"""
            DESCRIPTION OF WHAT TO DOCUMENT:
            {description}

            YOUR JOB — DIAGRAMS AND VISUALS:
            Based on the scope analysis and the produced documentation, create
            diagrams that visually communicate the architecture and flows:

            Create diagrams using Mermaid (markdown format with ```mermaid blocks):

            1. **Architecture Diagram** — Overview of the system's components
               and how they communicate (graph TD or C4 diagram)
            2. **Sequence Diagram** — Main flow of a typical
               operation (sequenceDiagram)
            3. **Entity-Relationship Diagram** — Main entities
               and their relationships (erDiagram)
            4. **Process Flowchart** — System usage flow
               by the user (flowchart)
            5. **Deployment Diagram** — How the system is deployed
               (if applicable)

            For each diagram, include:
            - Descriptive title
            - The Mermaid code inside a ```mermaid block
            - Brief explanation of what the diagram shows
            - Legend when necessary

            If the system has many components, focus on the main ones.
            Quality > quantity.
            """,
            expected_output=(
                "Set of Mermaid diagrams: architecture, sequence, "
                "entity-relationship, flowchart and deployment, "
                "each with title and explanation"
            ),
            agent=diagrammer,
        )
        tasks.append(diagrams)

    # --- Task 5: Review (always present) ---
    review = Task(
        description=f"""
        DESCRIPTION OF WHAT TO DOCUMENT:
        {description}

        YOUR JOB — FINAL DOCUMENTATION REVIEW:
        Review all the produced documentation and verify:

        1. **Spelling and Grammar** — Spelling errors?
        2. **Clarity** — Is each section clear and objective?
        3. **Completeness** — Was anything important left out?
        4. **Consistency** — Are terms used the same way throughout the document?
        5. **Tone and Voice** — Appropriate to the target audience of each section?
        6. **Examples** — Are the examples correct and do they work?
        7. **Links and References** — Are cross-references correct?
        8. **Diagrams** — Are they clear and well explained?

        For each problem found, document:
        - The specific problem (with approximate location)
        - Why it is a problem
        - Fix suggestion

        Issue a verdict: PASS or FAIL.
        If PASS: the documentation is ready for publication.
        If FAIL: list exactly what needs to be fixed before approval.
        """,
        expected_output=(
            "Review report: problems found (if any), "
            "fix suggestions, and PASS/FAIL verdict"
        ),
        agent=reviewer,
    )
    tasks.append(review)

    # --- Crew ---
    crew = Crew(
        agents=[technical_writer, user_writer, diagrammer, reviewer],
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
        description="cp-documentation: Software Documentation Crew (self-contained)",
    )
    parser.add_argument(
        "description",
        nargs="?",
        help="Description of what to document (software, API, system)",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="File with the description (alternative to the positional argument)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file to save the complete documentation",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["full", "tech", "user", "api", "diagrams"],
        default="full",
        help=(
            "Documentation mode: "
            "full (complete, default), "
            "tech (technical + API), "
            "user (user), "
            "api (API only), "
            "diagrams (diagrams only)"
        ),
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
        print("\n❌ Error: provide the description of what to document (argument or --input)")
        sys.exit(1)

    output_path = args.output
    mode = args.mode

    mode_names = {
        "full": "Complete Documentation",
        "tech": "Technical and API Documentation",
        "user": "User Documentation",
        "api": "API Documentation",
        "diagrams": "Diagrams and Visuals",
    }

    print(f"\n📋 Description: {description[:120]}...")
    print(f"📂 Mode: {mode_names.get(mode, mode)}")
    print(f"📂 Agents: embedded (self-contained)")
    print()

    crew = build_crew(description, mode, output_path)

    if args.dry_run:
        print("🧪 DRY RUN — crew built, agents:")
        for slug, data in AGENTS.items():
            print(f"  - {data['role']}")
        print(f"\n📋 Tasks ({len(crew.tasks)}):")
        for i, task in enumerate(crew.tasks, 1):
            print(f"  {i}. {task.description[:80]}...")
        print("\n✅ Crew ready. Remove --dry-run to execute.")
        return

    print("🚀 Running documentation crew...\n")
    require_llm()  # DT-08: fail early, with a message, if there is no LLM
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Documentation generated!\n")
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
        mode_suffix = mode if mode != "full" else "complete"
        out_file = output_dir / f"documentation_{mode_suffix}_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Saved to: {out_file.resolve()}")


if __name__ == "__main__":
    main()
