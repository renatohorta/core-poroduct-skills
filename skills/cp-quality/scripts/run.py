#!/usr/bin/env python3
"""
cp-quality — Software Quality Assurance Crew (self-contained)

Creates a CrewAI crew with 4 specialized agents to audit processes,
measure quality metrics, propose continuous improvements and validate artifacts.

Usage:
  python run.py "appointment scheduling system"
  python run.py "payments API" --mode audit
  python run.py --input description.md --output quality-report.md
  python run.py "test" --dry-run
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
    "quality-auditor": {
        "role": "Quality Auditor",
        "goal": (
            "Review whether software processes are being followed correctly, "
            "verify mandatory artifacts, identify process deviations "
            "and ensure compliance with established standards"
        ),
        "backstory": (
            "Rigorous quality auditor with over 15 years of experience "
            "in software process auditing. You follow checklists to the letter "
            "and don't accept shortcuts or 'workarounds'. "
            "You know CMMI, ISO 9001, ISO 25010 and software engineering best "
            "practices like the back of your hand. "
            "Every process deviation you find is documented with evidence, "
            "impact and severity. You don't let yourself be convinced by excuses — "
            "if the process wasn't followed, it's documented. "
            "Your motto: 'Process is not bureaucracy, it is quality assurance.' "
            "You verify: planning, requirements, design, implementation, "
            "testing, deploy, documentation and monitoring."
        ),
    },
    "metrics-analyst": {
        "role": "Metrics Analyst",
        "goal": (
            "Collect, analyze and interpret software quality metrics "
            "to turn raw data into actionable insights for the team"
        ),
        "backstory": (
            "Data analyst specialized in software engineering. "
            "You turn numbers into stories the team understands. "
            "Metrics you analyze: test coverage (line, branch, mutation), "
            "bug density, technical debt (estimated time to pay), "
            "team velocity, lead time, cycle time, MTTR, MTBF, "
            "cyclomatic complexity, coupling, cohesion, and code duplication. "
            "You don't just calculate metrics — you contextualize them: "
            "'85% coverage is good, but if the untested 15% is the system's core, it's a risk.' "
            "You generate mental dashboards with trends (last 4 sprints) "
            "and alerts when metrics leave acceptable thresholds. "
            "Your motto: 'What isn't measured can't be improved.' "
            "You always ask: 'Is this metric improving or worsening over time?'"
        ),
    },
    "continuous-improvement-engineer": {
        "role": "Continuous Improvement Engineer",
        "goal": (
            "Propose and implement improvements to the development process "
            "based on audit and metrics data, applying Kaizen, "
            "Lean and continuous improvement principles"
        ),
        "backstory": (
            "Process engineer who has applied Kaizen and Lean in software teams "
            "for over 10 years. You see waste where others see 'the way we do things'. "
            "For you, every process has bottlenecks waiting to be eliminated. "
            "You use the PDCA cycle (Plan-Do-Check-Act) and the DMAIC approach "
            "(Define-Measure-Analyze-Improve-Control) to structure improvements. "
            "You classify waste into 7 Lean categories: "
            "waiting, rework, overproduction, motion, transport, "
            "overprocessing and inventory. "
            "Each improvement you propose has: identified problem, "
            "root cause, proposed solution, estimated effort, expected impact "
            "and a metric to verify the improvement worked. "
            "Your motto: 'Improving 1% each sprint is better than waiting for the perfect solution.' "
            "You prioritize improvements by impact vs. effort (prioritization matrix)."
        ),
    },
    "artifact-validator": {
        "role": "Artifact Validator",
        "goal": (
            "Verify whether all mandatory artifacts of the development cycle "
            "exist, are complete, up to date and compliant with the established "
            "templates and standards"
        ),
        "backstory": (
            "Process QA who doesn't let missing documentation pass. "
            "You are the guardian of artifacts — if it isn't documented, it wasn't done. "
            "You verify each mandatory artifact of the lifecycle: "
            "vision document, requirements specification, architecture, "
            "UML diagrams, use cases, prototypes, test plan, "
            "test report, deploy manual, README, CHANGELOG, "
            "and API documentation. "
            "For each artifact, you verify: does it exist? is it complete? "
            "is it up to date? does it follow the template? was it approved by stakeholders? "
            "does it have version and date? is it accessible to the team? "
            "You don't accept 'I'll do it later' — if the artifact is mandatory "
            "for the phase, it needs to be ready before moving forward. "
            "Your motto: 'Documentation is not optional — it's what separates a project from a hack.' "
            "You issue a detailed checklist with status: ✅ Complete, ⚠️ Incomplete, ❌ Missing."
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
    description: str,
    mode: str = "full",
):
    """
    Build a CrewAI crew for software quality assurance.

    Args:
        description: Description of the project/system being audited
        mode: 'audit', 'metrics', 'improvement', or 'full'
    """
    auditor = get_agent("quality-auditor")
    analyst = get_agent("metrics-analyst")
    improvement = get_agent("continuous-improvement-engineer")
    validator = get_agent("artifact-validator")

    context = f"PROJECT/SYSTEM DESCRIPTION:\n{description}"

    # ─────────────────────────────────────────────────────────────────────
    # Task 1: Process Audit (Auditor)
    # ─────────────────────────────────────────────────────────────────────
    task_audit = Task(
        description=f"""
        {context}

        YOUR JOB — PROCESS AUDIT:

        As Quality Auditor, your mission is to review whether the software
        processes are being followed correctly.

        1. **Verification of Mandatory Processes:**
           - Planning: does a schedule exist? are risks mapped? are resources allocated?
           - Requirements: functional specification? acceptance criteria? traceability?
           - Design: documented architecture? recorded technical decisions? defined standards?
           - Implementation: mandatory code review? code standards? semantic commits?
           - Testing: test plan? minimum coverage? automated tests?
           - Deploy: CI/CD pipeline? rollback plan? health checks?
           - Monitoring: logs? alerts? dashboards? defined SLAs/SLOs?

        2. **Identification of Deviations:**
           - For each process not followed, document:
             - Which process was deviated
             - What should have been done
             - What was done instead
             - Impact of the deviation (Critical/High/Medium/Low)
             - Evidence of the deviation

        3. **Compliance Analysis:**
           - Percentage of processes followed vs. not followed
           - Deviation patterns (do they always skip the same step?)
           - Risks associated with the found deviations

        OUTPUT FORMAT:
        ## Process Audit Report

        ### Verified Processes
        | Process | Status | Evidence | Impact |
        |----------|--------|-----------|---------|
        | Planning | ✅/⚠️/❌ | ... | ... |
        | Requirements | ✅/⚠️/❌ | ... | ... |
        | ... | ... | ... | ... |

        ### Identified Deviations
        - [Severity] Process: description of the deviation
        - ...

        ### Overall Compliance
        - Processes followed: X/Y (X%)
        - Identified risks: [list]
        - Audit Verdict: ✅ Compliant / ⚠️ Non-compliant
        """,
        expected_output=(
            "Complete process audit report with verification of "
            "mandatory processes, identified deviations and compliance verdict"
        ),
        agent=auditor,
    )

    # ─────────────────────────────────────────────────────────────────────
    # Task 2: Artifact Validation (Validator)
    # ─────────────────────────────────────────────────────────────────────
    task_validation = Task(
        description=f"""
        {context}

        YOUR JOB — ARTIFACT VALIDATION:

        As Artifact Validator, your mission is to verify whether all
        mandatory artifacts exist and are complete.

        1. **Mandatory Artifacts by Phase:**

           **Planning:**
           - Product Vision Document
           - Project Schedule
           - Risk Matrix
           - Project Charter

           **Requirements:**
           - Functional Requirements Specification
           - Non-Functional Requirements Specification
           - Use Cases / User Stories
           - Acceptance Criteria
           - Prototypes / Wireframes

           **Design/Architecture:**
           - Architecture Document (ADR)
           - UML Diagrams (classes, sequence, states)
           - Data Model (ERD)
           - API Contracts (OpenAPI/Swagger)

           **Implementation:**
           - Source Code (with versioning)
           - Project README
           - Contribution Guide
           - CHANGELOG

           **Testing:**
           - Test Plan
           - Test Cases
           - Test Report
           - Coverage Report

           **Deploy/Operation:**
           - Deploy Manual
           - Operation Runbook
           - Rollback Plan
           - Infrastructure Documentation

        2. **Validation Criteria for Each Artifact:**
           - ✅ Exists: the file/document exists
           - ✅ Complete: all mandatory sections are filled
           - ✅ Up to date: reflects the project's current state
           - ✅ Approved: had stakeholder review/approval
           - ✅ Accessible: is available to the whole team

        3. **Final Checklist:**
           - Total mandatory artifacts: N
           - Complete: N (%)
           - Incomplete: N (%)
           - Missing: N (%)

        OUTPUT FORMAT:
        ## Artifact Validation Report

        ### Artifact Checklist
        | Artifact | Phase | Exists | Complete | Up to date | Status |
        |----------|------|--------|----------|------------|--------|
        | Vision Document | Planning | ✅ | ✅ | ✅ | ✅ |
        | ... | ... | ... | ... | ... | ... |

        ### Missing Artifacts (Critical)
        - [list with impact]

        ### Incomplete Artifacts (Attention)
        - [list with what's missing]

        ### Summary
        - Total: N | Complete: N | Incomplete: N | Missing: N
        - Compliance: X%
        - Verdict: ✅ Approved / ❌ Rejected
        """,
        expected_output=(
            "Complete artifact validation checklist with status per "
            "artifact, completeness analysis and approval verdict"
        ),
        agent=validator,
    )

    # ─────────────────────────────────────────────────────────────────────
    # Task 3: Metrics Analysis (Metrics Analyst)
    # ─────────────────────────────────────────────────────────────────────
    task_metrics = Task(
        description=f"""
        {context}

        YOUR JOB — METRICS ANALYSIS:

        As Metrics Analyst, your mission is to collect, analyze and interpret
        the software's quality metrics.

        1. **Metrics to Analyze:**

           **Code Quality:**
           - Test coverage (line, branch, mutation)
           - Average cyclomatic complexity
           - Bug density (bugs/KLOC)
           - Estimated technical debt (hours/days to pay)
           - Code duplication (%)
           - Coupling and cohesion

           **Process:**
           - Team velocity (points per sprint)
           - Lead time (from idea to deploy)
           - Cycle time (from development to deploy)
           - Rework rate (%)
           - MTTR (Mean Time to Recover)
           - MTBF (Mean Time Between Failures)

           **Product:**
           - Open vs. closed bugs
           - Bugs by severity (Critical/High/Medium/Low)
           - Average bug resolution time
           - Open vs. closed issues
           - User satisfaction (NPS/CSAT)

        2. **Analysis and Interpretation:**
           - For each metric, report:
             - Current value
             - Acceptable threshold
             - Trend (improving/worsening/stable)
             - Comparison with the previous period
           - Identify correlations between metrics
             - E.g.: 'Coverage drop + increase in production bugs'
           - Highlight metrics outside the threshold

        3. **Insights and Alerts:**
           - Top 3 metrics that need immediate attention
           - Metrics that improved (reinforce practices)
           - Risks based on trends

        OUTPUT FORMAT:
        ## Metrics Analysis Report

        ### Code Quality Metrics
        | Metric | Value | Threshold | Status | Trend |
        |---------|-------|-----------|--------|-----------|
        | Coverage | 72% | >= 80% | ❌ | 📉 worsening |
        | ... | ... | ... | ... | ... |

        ### Process Metrics
        | Metric | Value | Threshold | Status | Trend |
        |---------|-------|-----------|--------|-----------|

        ### Product Metrics
        | Metric | Value | Threshold | Status | Trend |
        |---------|-------|-----------|--------|-----------|

        ### Insights
        - 🔴 Alert: [metric] is [X%] above/below the threshold
        - 🟡 Attention: [metric] has been worsening for [N] sprints
        - 🟢 Positive: [metric] improved [X%] since the last measurement

        ### Identified Correlations
        - [correlation 1]
        - [correlation 2]

        ### Data-Based Recommendations
        - [recommendation 1]
        - [recommendation 2]
        """,
        expected_output=(
            "Complete metrics analysis report with metric tables, "
            "insights, correlations and data-based recommendations"
        ),
        agent=analyst,
    )

    # ─────────────────────────────────────────────────────────────────────
    # Task 4: Improvement Proposals (Continuous Improvement Eng.)
    # ─────────────────────────────────────────────────────────────────────
    task_improvement = Task(
        description=f"""
        {context}

        YOUR JOB — CONTINUOUS IMPROVEMENT PROPOSALS:

        As Continuous Improvement Engineer, your mission is to propose improvements
        to the process based on the audit, artifact validation
        and metrics analysis results.

        1. **Root Cause Analysis:**
           For each problem identified in the audit and metrics:
           - What is the root cause? (use 5 Whys or Ishikawa Diagram)
           - Is the problem one-off or systemic?
           - Who/which area is affected?

        2. **Waste Classification (Lean):**
           - **Waiting:** team waiting for code review, deploy, approval
           - **Rework:** bugs that come back, misunderstood requirements
           - **Overproduction:** features no one asked for, excessive documentation
           - **Motion:** context switching, unnecessary meetings
           - **Transport:** handoffs between teams, priority changes
           - **Overprocessing:** bureaucracy, long approval chains
           - **Inventory:** giant backlog, branches open for months

        3. **Improvement Proposals (minimum 5):**
           For each proposal:
           - **Problem:** which pain is being solved
           - **Root Cause:** why the problem exists
           - **Solution:** what to do to solve it
           - **Effort:** 🔵 Low / 🟡 Medium / 🔴 High
           - **Impact:** 🔵 Low / 🟡 Medium / 🔴 High
           - **Priority:** (Impact / Effort)
           - **Success Metric:** how to know the improvement worked
           - **Suggested Deadline:** short (1 sprint), medium (2-4 sprints), long (5+)

        4. **Prioritization Matrix:**
           - Organize the improvements in an Impact vs. Effort matrix
           - Quick Wins (High Impact, Low Effort) — do now
           - Big Projects (High Impact, High Effort) — plan
           - Fill-ins (Low Impact, Low Effort) — do when you can
           - Discardables (Low Impact, High Effort) — avoid

        5. **Action Plan (Next 30 Days):**
           - What to do in sprint 1
           - What to do in sprint 2
           - How to measure progress

        OUTPUT FORMAT:
        ## Continuous Improvement Report

        ### Root Cause Analysis
        - Problem: [description]
        - 5 Whys: [1] → [2] → [3] → [4] → [5]
        - Root Cause: [conclusion]

        ### Identified Waste
        | Type | Where | Impact |
        |------|------|---------|
        | Waiting | Code review takes 3 days | High |
        | ... | ... | ... |

        ### Improvement Proposals
        | # | Problem | Solution | Effort | Impact | Priority |
        |---|----------|---------|---------|---------|------------|
        | 1 | ... | ... | 🔵 | 🔴 | High |
        | ... | ... | ... | ... | ... | ... |

        ### Prioritization Matrix
        - **Quick Wins (High Impact, Low Effort):**
          - [improvement 1] — do now
          - [improvement 2] — do now
        - **Big Projects (High Impact, High Effort):**
          - [improvement 3] — plan
        - **Fill-ins (Low Impact, Low Effort):**
          - [improvement 4] — do when you can
        - **Discardables (Low Impact, High Effort):**
          - [improvement 5] — avoid

        ### Action Plan — Next 30 Days
        - Sprint 1: [actions]
        - Sprint 2: [actions]
        - Progress metrics: [how to measure]
        """,
        expected_output=(
            "Complete continuous improvement report with root cause analysis, "
            "identified waste, prioritized proposals and action plan"
        ),
        agent=improvement,
    )

    # ─────────────────────────────────────────────────────────────────────
    # Task 5: Quality Gate — Final Report (all agents)
    # ─────────────────────────────────────────────────────────────────────
    task_quality_gate = Task(
        description=f"""
        {context}

        YOUR JOB — QUALITY GATE AND FINAL REPORT:

        Compile all the results from the previous phases and produce the final
        quality report with a PASS/FAIL verdict.

        1. **Compile the Results:**

           **Process Audit:**
           - Processes followed: X%
           - Deviations found: N (Critical: N, High: N, Medium: N, Low: N)
           - Audit verdict

           **Artifact Validation:**
           - Complete artifacts: X%
           - Missing artifacts: N
           - Validation verdict

           **Metrics Analysis:**
           - Metrics within threshold: X%
           - Active alerts: N
           - Trends: [summary]

           **Continuous Improvement:**
           - Identified Quick Wins: N
           - Proposed improvements: N
           - Action plan: [summary]

        2. **Quality Gate — Criteria:**
           - **PASS** if ALL criteria are met:
             - Processes followed: 100%
             - Complete artifacts: 100%
             - Test coverage: >= 80%
             - Technical debt: < 20%
             - Critical bugs in production: 0
             - Velocity within the historical average
           - **FAIL** if ANY criterion is not met

        3. **Final Recommendations:**
           - What needs to be resolved URGENTLY (before the next release)
           - What needs to be resolved in 30 days
           - What to put in the continuous improvement backlog
           - Assumed residual risks

        OUTPUT FORMAT:
        ## Final Quality Report

        ### Executive Summary
        - Project: [name]
        - Audit date: [date]
        - Final Verdict: ✅ PASS / ❌ FAIL
        - Overall Compliance: X%

        ### Results by Dimension
        | Dimension | Result | Status |
        |----------|-----------|--------|
        | Process Audit | X% compliant | ✅/❌ |
        | Artifact Validation | X% complete | ✅/❌ |
        | Quality Metrics | X% within threshold | ✅/❌ |
        | Continuous Improvement | N proposals | ✅/❌ |

        ### Quality Gate
        - Processes 100% followed: ✅ / ❌
        - Artifacts 100% complete: ✅ / ❌
        - Coverage >= 80%: ✅ / ❌
        - Technical debt < 20%: ✅ / ❌
        - Critical bugs = 0: ✅ / ❌
        - Velocity OK: ✅ / ❌
        - **Final Verdict: PASS / FAIL**

        ### Urgent Actions (Before the Next Release)
        - [action 1]
        - [action 2]

        ### Actions in 30 Days
        - [action 1]
        - [action 2]

        ### Continuous Improvement Backlog
        - [item 1]
        - [item 2]

        ### Residual Risks
        - [risk 1]
        - [risk 2]

        ### Final Recommendations
        - [recommendation 1]
        - [recommendation 2]
        """,
        expected_output=(
            "Complete final quality report with PASS/FAIL verdict, "
            "compilation of all dimensions, urgent actions and recommendations"
        ),
        agent=auditor,
    )

    # --- Build task list based on mode ---
    all_tasks = []
    used_agents = []

    if mode in ("full", "audit"):
        all_tasks.append(task_audit)
        all_tasks.append(task_validation)
        used_agents.extend([auditor, validator])

    if mode in ("full", "metrics"):
        all_tasks.append(task_metrics)
        used_agents.append(analyst)

    if mode in ("full", "improvement"):
        all_tasks.append(task_improvement)
        used_agents.append(improvement)

    # Quality gate always runs
    all_tasks.append(task_quality_gate)
    if auditor not in used_agents:
        used_agents.append(auditor)

    # --- Crew ---
    crew = Crew(
        agents=used_agents,
        tasks=all_tasks,
        process=Process.sequential,
        verbose=True,
    )

    return crew


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="cp-quality: Software Quality Assurance Crew (self-contained)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python run.py \"appointment scheduling system\"\n"
            "  python run.py \"payments API\" --mode audit\n"
            "  python run.py --input description.md --output quality-report.md\n"
            "  python run.py \"test\" --dry-run\n"
        ),
    )
    parser.add_argument(
        "description",
        nargs="?",
        help="Description of the project/system to be audited",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="File with the project description (alternative to the positional argument)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file to save the quality report",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["full", "audit", "metrics", "improvement"],
        default="full",
        help="Execution mode (default: full — audit + metrics + improvement)",
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
        input_path = Path(args.input_file)
        if not input_path.exists():
            print(f"❌ File not found: {args.input_file}")
            sys.exit(1)
        description = input_path.read_text(encoding="utf-8")
    elif args.description:
        description = args.description
    else:
        parser.print_help()
        print("\n❌ Error: provide the project description (argument or --input)")
        sys.exit(1)

    output_path = args.output
    mode = args.mode

    # Mode name mapping
    mode_names = {
        "full": "Complete (audit + metrics + improvement)",
        "audit": "Process and Artifact Audit Only",
        "metrics": "Metrics Analysis Only",
        "improvement": "Improvement Proposals Only",
    }

    print(f"\n📋 Project: {description[:120]}...")
    print(f"🔧 Mode: {mode_names.get(mode, mode)}")
    print(f"🤖 Agents: embedded (self-contained)")
    print()

    crew = build_crew(
        description=description,
        mode=mode,
    )

    if args.dry_run:
        print("🧪 DRY RUN — crew built, agents:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
        print(f"\n📋 Tasks ({len(crew.tasks)}):")
        for i, task in enumerate(crew.tasks, 1):
            agent_name = task.agent.role if hasattr(task, 'agent') and task.agent else "?"
            desc_short = task.description[:100].replace("\n", " ").strip()
            print(f"  {i}. {desc_short}... → {agent_name}")
        print(f"\n✅ Crew ready. Remove --dry-run to execute.")
        return

    print("🚀 Running quality assurance crew...\n")
    require_llm()  # DT-08: fail early, with a message, if there is no LLM
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Quality Report generated!\n")
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
        out_file = output_dir / f"quality-report_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Saved to: {out_file.resolve()}")


if __name__ == "__main__":
    main()
