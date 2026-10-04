#!/usr/bin/env python3
"""
cp-benchmark-to-spec — Benchmark to Technical Specification (self-contained)

Transforms a reference product into complete, replicable technical documentation.
Receives inputs (URLs, web research, screenshots), crawls the documentation,
extracts the design system from the screens, and generates the RUP specification
+ project management.

Usage:
  python run.py "product: Attio; URL: https://attio.com/help/reference"
  python run.py --context "product X" --output ./spec
  python run.py --input context.txt
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
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

setup_console()  # DT-01: UTF-8 on stdout/stderr (Windows console is cp1252)

# ═══════════════════════════════════════════════════════════════════════════
# EMBEDDED AGENTS
# ═══════════════════════════════════════════════════════════════════════════

AGENTS = {
    "documentation-analyst": {
        "role": "Documentation Analyst",
        "goal": "Crawl the reference product's documentation and extract the complete source content",
        "backstory": (
            "Documentation analyst experienced in product reverse engineering. "
            "You know how to extract the maximum information from public documentation, "
            "llms.txt files and web pages. You identify the product structure "
            "(modules, features, integrations) and organize the source content so "
            "that a technical specifier can work with it. You prioritize efficiency: "
            "if the product offers an llms.txt/llms-full.txt file, you use it "
            "instead of scraping page by page. Your motto: 'Good documentation is "
            "what can be rebuilt.'"
        ),
    },
    "design-analyst": {
        "role": "Design Analyst",
        "goal": "Analyze product screenshots and extract the complete design system (colors, typography, components)",
        "backstory": (
            "Design analyst with a clinical eye for design systems. You extract from "
            "screenshots the UI tokens: color palette (hex), typography (fonts, "
            "sizes, weights), spacing, borders, radii, shadows, icons, buttons, "
            "inputs, tables, badges. You consolidate the analysis of a few key screens "
            "instead of analyzing image by image, avoiding loops. You mark estimated "
            "values as such and recommend validating against the real CSS. Your motto: "
            "'Visual consistency is what makes a product look professional.'"
        ),
    },
    "technical-specifier": {
        "role": "Technical Specifier",
        "goal": "Generate the complete RUP specification (4 phases) from the source content, referencing without duplicating",
        "backstory": (
            "Senior technical specifier with mastery of software architecture. "
            "You transform a reference product's source content into complete, "
            "replicable technical documentation: vision, actors, requirements, glossary, "
            "architecture, use cases, schema, per-module specifications, API, "
            "frontend, tests, deploy and training. You organize by RUP phases "
            "(Inception, Elaboration, Construction, Transition) and ensure each "
            "document references the others without duplicating content. You issue the "
            "final completeness verdict (PASS/FAIL)."
        ),
    },
    "project-manager": {
        "role": "Project Manager",
        "goal": "Generate epics, stories, tasks and roadmap referencing the technical specification",
        "backstory": (
            "Experienced project manager in turning technical specifications into "
            "execution plans. You create epics (EP), stories (HS) and tasks (TSK) "
            "that reference the technical documents without duplicating content. You define "
            "the delivery roadmap with phases and milestones, and ensure the traceability "
            "Epic → Story → Task → Use Case → Requirement → Specification. "
            "Your motto: 'A good plan is one the team can execute.'"
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

def build_crew(context: str, output_path: str = None):
    """Build a CrewAI crew for benchmark-to-spec."""

    doc_analyst = get_agent("documentation-analyst")
    design_analyst = get_agent("design-analyst")
    specifier = get_agent("technical-specifier")
    manager = get_agent("project-manager")

    # --- Task 1: Documentation crawler ---
    crawler = Task(
        description=f"""
        CONTEXT (REFERENCE PRODUCT INPUTS):
        {context}

        YOUR JOB — DOCUMENTATION CRAWLER:
        1. Identify the reference product and its documentation URLs
        2. If the product offers an llms.txt/llms-full.txt file, use it (it is the most efficient)
        3. Otherwise, navigate the documentation pages and extract the text
        4. Map the product structure: modules, features, integrations, key concepts
        5. Organize the source content so a technical specifier can work with it

        OUTPUT FORMAT:
        ## Reference Product
        - Name, category, positioning
        ## Product Structure
        - Main modules/features
        ## Key Concepts
        - Domain terminology
        ## Source Content
        - Summary of what was extracted and where it is
        """,
        expected_output="Product identified, structure mapped, key concepts and organized source content",
        agent=doc_analyst,
    )

    # --- Task 2: Design System ---
    design = Task(
        description=f"""
        CONTEXT (REFERENCE PRODUCT INPUTS):
        {context}

        YOUR JOB — DESIGN SYSTEM:
        Based on the product screenshots (if provided) and the source content:

        1. **Color palette** — brand, neutral, semantic colors (hex)
        2. **Typography** — fonts, sizes, weights, hierarchy
        3. **Spacing** — base grid, applications
        4. **Borders and radii** — values per component
        5. **Shadows** — elevation levels
        6. **Icons** — style, sizes
        7. **Components** — buttons, inputs, tables, badges, cards, sidebar, topbar
        8. **Micro-interactions** — transitions, hovers

        Consolidate the analysis of a few key screens. Mark estimated values as such.

        OUTPUT FORMAT:
        ## Design System
        - Color palette (tokens)
        - Typography (scale)
        - Spacing, borders, radii, shadows
        - UI components
        - Micro-interactions
        """,
        expected_output="Complete design system with color tokens, typography, spacing, components and micro-interactions",
        agent=design_analyst,
    )

    # --- Task 3: RUP Specification ---
    spec = Task(
        description=f"""
        CONTEXT (REFERENCE PRODUCT INPUTS):
        {context}

        YOUR JOB — COMPLETE RUP SPECIFICATION:
        Based on the source content and the design system, generate the complete
        technical specification for the team to rebuild the product. Organize by RUP phases:

        **Phase 1 — Inception (`01-inception/`):**
        - `00-product-vision.md` — vision, problem, solution, target audience, differentiators
        - `01-actors.md` — actors and roles
        - `02-general-requirements.md` — functional (FR) and non-functional (NFR) requirements
        - `03-glossary.md` — domain terminology

        **Phase 2 — Elaboration (`02-elaboration/`):**
        - `04-system-architecture.md` — architecture (backend/frontend/database)
        - `use-cases/` — detailed use cases per domain

        **Phase 3 — Construction (`03-construction/`):**
        - `schema/` — PostgreSQL data model + migrations
        - `specification/` — technical detail per module
        - `api/` — REST + WebSocket specification
        - `frontend/` — React components, pages, types

        **Phase 4 — Transition (`04-transition/`):**
        - `05-test-plan.md` — tests per level
        - `06-deploy-and-infra.md` — deploy, CI/CD, infrastructure
        - `07-training.md` — training

        **Design System (root):**
        - `design-system.md` — UI/UX specification

        RULES:
        - Each document references the others, does NOT duplicate content
        - Use English for the documentation; codes/payloads in English
        - Mark items not documented in the source as "not documented in the source"
        - Target stack: Django REST + React/Vite/TS + PostgreSQL + Redis + Celery

        Finally, issue the **completeness verdict**: PASS or FAIL.
        If FAIL, list what is missing.

        OUTPUT FORMAT:
        ## RUP Specification
        - Phase 1: Inception (documents)
        - Phase 2: Elaboration (documents)
        - Phase 3: Construction (documents)
        - Phase 4: Transition (documents)
        - Design System
        ## Quality Gate: PASS/FAIL
        """,
        expected_output="Complete RUP specification (4 phases) + design system, with PASS/FAIL verdict",
        agent=specifier,
    )

    # --- Task 4: Project Management ---
    project = Task(
        description=f"""
        CONTEXT (REFERENCE PRODUCT INPUTS):
        {context}

        YOUR JOB — PROJECT MANAGEMENT:
        Based on the RUP specification, generate the project management in `05-project-management/`:

        - `README.md` — overview, ID conventions, epic→UC→docs mapping
        - `01-epics.md` — epics (EP-XX) per domain, with technical references
        - `02-stories.md` — stories (HS) with acceptance criteria linked to the use cases
        - `03-tasks.md` — tasks (TSK) with technical implementation references
        - `04-roadmap.md` — delivery phases, dependencies and milestones

        RULES:
        - Each epic/story/task references the technical documents, does NOT duplicate
        - Traceability: Epic → Story → Task → Use Case → Requirement → Specification
        - Use English

        OUTPUT FORMAT:
        ## Project Management
        - Epics (EP-XX)
        - Stories (HS-XX)
        - Tasks (TSK-XX)
        - Roadmap (phases and milestones)
        """,
        expected_output="Complete project management: epics, stories, tasks and roadmap referencing the spec",
        agent=manager,
    )

    # --- Crew ---
    crew = Crew(
        agents=[doc_analyst, design_analyst, specifier, manager],
        tasks=[crawler, design, spec, project],
        process=Process.sequential,
        verbose=True,
    )

    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-benchmark-to-spec: Benchmark to Technical Specification (self-contained)",
    )
    parser.add_argument(
        "context",
        nargs="?",
        help="Reference product inputs: URLs, research, screenshots, request",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="File with the context (alternative to the positional argument)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output folder to save the specification (default: doc_dev/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only builds the crew and shows the agents, without running",
    )
    args = parser.parse_args()

    require_crewai()  # DT-07: actionable message instead of a traceback

    # --- Resolve context ---
    context = None
    if args.input_file:
        context = Path(args.input_file).read_text(encoding="utf-8")
    elif args.context:
        context = args.context
    else:
        parser.print_help()
        print("\n❌ Error: provide the context (argument or --input)")
        sys.exit(1)

    output_path = args.output

    print(f"\n📋 Context: {context[:120]}...")
    print(f"📂 Agents: embedded (self-contained)")
    print()

    crew = build_crew(context, output_path)

    if args.dry_run:
        print("🧪 DRY RUN — crew built, agents:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
        print("\n✅ Crew ready. Remove --dry-run to execute.")
        return

    print("🚀 Running benchmark-to-spec crew...\n")
    require_llm()  # DT-08: fails early, with a message, if there is no LLM
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Technical Specification generated!\n")
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
        out_file = output_dir / f"benchmark-to-spec_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Saved to: {out_file.resolve()}")


if __name__ == "__main__":
    main()
