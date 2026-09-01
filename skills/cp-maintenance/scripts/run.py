#!/usr/bin/env python3
"""
cp-maintenance — Software Maintenance and Evolution Crew (self-contained)

Creates a CrewAI crew with 4 specialized agents for software maintenance and
evolution: diagnosing bugs, implementing fixes, refactoring code and
assessing the impact of changes.

Usage:
  python run.py "the /login endpoint returns 500 when the email has an accent" --mode bug-fix
  python run.py "refactor the payments module" --mode refactor
  python run.py "improve the performance of the reports query" --mode improvement
  python run.py "fix a bug and refactor the logic" --mode full
  python run.py --input bug_report.md --mode bug-fix
  python run.py "test" --dry-run
"""

import argparse
import sys
import os
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
# EMBEDDED AGENTS (self-contained)
# ═══════════════════════════════════════════════════════════════════════════

AGENTS = {
    "bug-analyst": {
        "role": "Bug Analyst",
        "goal": (
            "Perform triage, reproduction and complete bug diagnosis, "
            "identifying the root cause with surgical precision"
        ),
        "backstory": (
            "Experienced debugger with over 15 years of experience "
            "in complex systems analysis. You are known for finding "
            "the root cause while others are busy treating symptoms. "
            "Your approach is methodical: first reproduce the bug, then isolate "
            "the variables involved, then trace the call chain until "
            "you find the exact origin of the problem. "
            "You analyze logs, stack traces, database states and "
            "request flows with a clinical eye. "
            "Your diagnosis includes: what is broken, why it is broken, "
            "when it started breaking, and the smallest path to fix it. "
            "You document each step of the investigation so others can "
            "understand the reasoning."
        ),
    },
    "fix-developer": {
        "role": "Fix Developer",
        "goal": (
            "Implement minimal, safe and well-tested fixes for identified "
            "bugs, without introducing side effects"
        ),
        "backstory": (
            "Surgical developer who fixes exactly what is broken, "
            "nothing more. You have iron discipline to not do refactors "
            "or improvements along the way — every changed line has a clear "
            "and justifiable purpose. "
            "Your philosophy: 'the smallest possible change that solves the problem'. "
            "You always consider: could this fix break something else? "
            "Is it consistent with the rest of the code? Is it testable? "
            "Before implementing, you fully understand the bug analyst's "
            "diagnosis. After implementing, you verify that the "
            "bug was truly eliminated and that the existing tests still "
            "pass. "
            "You write defensive code, with edge validation and proper "
            "error handling, but without overdoing it."
        ),
    },
    "refactoring-engineer": {
        "role": "Refactoring Engineer",
        "goal": (
            "Improve the quality of existing code — readability, "
            "performance, maintainability — without changing external behavior"
        ),
        "backstory": (
            "Software engineer who leaves the code cleaner than "
            "they found it, without introducing bugs. You are an expert in safe "
            "refactoring: method extraction, renaming, conditional simplification, "
            "replacing inheritance with composition, applying design patterns "
            "when appropriate. "
            "You follow Martin Fowler's principle: 'refactoring is a change "
            "to the code that improves its structure without changing its behavior'. "
            "Each refactoring you do is small, atomic and reversible. "
            "You never refactor and add functionality in the same commit. "
            "Your priority is: (1) break nothing, (2) improve readability, "
            "(3) reduce complexity, (4) improve performance. "
            "You always validate that the existing tests keep passing "
            "after each refactoring."
        ),
    },
    "impact-analyst": {
        "role": "Impact Analyst",
        "goal": (
            "Assess the impact of proposed changes on the system, identify "
            "potential regressions and ensure the quality of the final delivery"
        ),
        "backstory": (
            "Analyst who thinks about all the consequences before a change "
            "is made. You have a systemic mind that sees software as "
            "an interconnected ecosystem — changing one piece affects many others. "
            "Your specialty is mapping dependencies, identifying hidden "
            "couplings and predicting regressions before they happen. "
            "You analyze: which modules are affected? Which user flows "
            "could break? Which regression tests need to be run? "
            "Are there security or performance risks? Is the change consistent with "
            "the existing architecture? "
            "You are the final quality gate — skeptical by nature, demanding by "
            "principle. Your PASS or FAIL verdict is based on concrete "
            "evidence, not assumptions. "
            "You document risks, test scenarios and recommendations for "
            "mitigation."
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
    output_dir: str = None,
):
    """
    Build a CrewAI crew for software maintenance.

    Args:
        description: Bug report / improvement request description
        mode: 'bug-fix', 'refactor', 'improvement', or 'full'
        output_dir: Directory to save output files
    """
    agents = {}
    tasks = []

    # --- Agent: Bug Analyst ---
    agents["analyst"] = get_agent("bug-analyst")

    # --- Agent: Fix Developer ---
    agents["fixer"] = get_agent("fix-developer")

    # --- Agent: Refactoring Engineer ---
    agents["refactorer"] = get_agent("refactoring-engineer")

    # --- Agent: Impact Analyst ---
    agents["impact"] = get_agent("impact-analyst")

    # ─────────────────────────────────────────────────────────────────────
    # Task 1: Analysis and Diagnosis (Bug Analyst)
    # Runs in all modes except 'refactor' and 'improvement'
    # ─────────────────────────────────────────────────────────────────────
    if mode in ("bug-fix", "full"):
        task_diagnosis = Task(
            description=f"""
            PROBLEM DESCRIPTION:
            {description}

            YOUR JOB — ANALYSIS AND DIAGNOSIS:

            You are the Bug Analyst. Investigate this problem deeply:

            1. **Reproduce the bug mentally**: What is the exact scenario that triggers the error?
            2. **Analyze the root cause**: Do not stop at the symptom — find the origin.
            3. **Document the diagnosis**:
               - Expected behavior vs. current behavior
               - Conditions to reproduce the bug
               - Identified root cause (file, function, line)
               - Call chain that leads to the error
               - Estimated impact (how many users affected, severity)
            4. **Suggest fix approaches**: List 1-3 possible fixes
               with pros and cons of each

            Report format:
            ```
            ## Bug Diagnosis

            ### Expected Behavior
            ...

            ### Current Behavior
            ...

            ### Steps to Reproduce
            1. ...
            2. ...

            ### Root Cause
            - File: ...
            - Function: ...
            - Explanation: ...

            ### Impact
            - Severity: 🔴 Critical / 🟠 High / 🟡 Medium / 🔵 Low
            - Affected users: ...
            - ...

            ### Suggested Fix Approaches
            1. ... (recommended)
            2. ...
            ```
            """,
            expected_output=(
                "Complete diagnosis report with identified root cause, "
                "steps to reproduce, estimated impact and fix suggestions."
            ),
            agent=agents["analyst"],
        )
        tasks.append(task_diagnosis)

    # ─────────────────────────────────────────────────────────────────────
    # Task 2: Impact Analysis (Impact Analyst)
    # Runs in all modes
    # ─────────────────────────────────────────────────────────────────────
    task_impact = Task(
        description=f"""
        PROBLEM DESCRIPTION:
        {description}

        YOUR JOB — IMPACT ANALYSIS:

        You are the Impact Analyst. Assess the consequences of the proposed
        changes before they are implemented:

        1. **Map dependencies**: Which modules, services and features
           are connected to the area that will be modified?

        2. **Identify risks**:
           - Potential regressions (what could break?)
           - Security risks (does the change expose vulnerabilities?)
           - Performance risks (does the change degrade performance?)
           - Consistency risks (is the change coherent with the rest of the system?)

        3. **List regression test scenarios**:
           - Existing tests that must keep passing
           - New scenarios that need to be tested
           - Edge cases that deserve special attention

        4. **Recommendations**:
           - Should the change be made? Why?
           - Precautions to take during implementation
           - Suggested implementation order (if there are multiple changes)

        Report format:
        ```
        ## Impact Analysis

        ### Identified Dependencies
        - Module X → depends on Y → affects Z
        ...

        ### Identified Risks
        - 🔴 Critical: ...
        - 🟠 High: ...
        - 🟡 Medium: ...
        - 🔵 Low: ...

        ### Regression Test Scenarios
        1. ...
        2. ...

        ### Recommendations
        - Recommended action: ...
        - Precautions: ...
        ```
        """,
        expected_output=(
            "Impact analysis report with mapped dependencies, "
            "identified risks, regression test scenarios and recommendations."
        ),
        agent=agents["impact"],
    )
    tasks.append(task_impact)

    # ─────────────────────────────────────────────────────────────────────
    # Task 3a: Fix (Fix Developer) — bug-fix or full mode
    # ─────────────────────────────────────────────────────────────────────
    if mode in ("bug-fix", "full"):
        task_fix = Task(
            description=f"""
            PROBLEM DESCRIPTION:
            {description}

            YOUR JOB — IMPLEMENT THE FIX:

            You are the Fix Developer. Based on the Bug Analyst's diagnosis
            and the impact analysis, implement the fix:

            1. **Implement the minimal fix**: Only what is needed to
               eliminate the bug. No refactors, improvements or unrelated
               changes.

            2. **Follow best practices**:
               - Defensive code: validate inputs, handle edges
               - Error handling consistent with the rest of the code
               - Descriptive names and readable code
               - Comments only where the logic is not obvious

            3. **Document the changes**:
               - Modified files with exact paths
               - Changed lines (from/to)
               - Justification for each change
               - Why this approach was chosen

            4. **Verify**:
               - Was the bug truly eliminated?
               - Do the existing tests keep passing?
               - Are there no visible side effects?

            IMPORTANT:
            - Fix exactly what is broken, nothing more
            - Do not introduce new features
            - Do not refactor unrelated code
            - If the fix is complex, explain the reasoning

            Report format:
            ```
            ## Implemented Fix

            ### Modified Files
            - `path/file.py`: [description of the change]
              - Line X: `old code` → `new code`
              - Reason: ...

            ### Justification
            ...

            ### Verification
            - Bug eliminated: ✅ / ❌
            - Existing tests pass: ✅ / ❌
            - Side effects: None / [describe]
            ```
            """,
            expected_output=(
                "Fixed code with documentation of the changes: modified "
                "files, changed lines, justification and verification."
            ),
            agent=agents["fixer"],
        )
        tasks.append(task_fix)

    # ─────────────────────────────────────────────────────────────────────
    # Task 3b: Refactoring (Refactoring Engineer) — refactor, improvement or full mode
    # ─────────────────────────────────────────────────────────────────────
    if mode in ("refactor", "improvement", "full"):
        task_refactoring = Task(
            description=f"""
            PROBLEM DESCRIPTION:
            {description}

            YOUR JOB — REFACTORING / IMPROVEMENT:

            You are the Refactoring Engineer. Based on the impact analysis,
            improve the existing code without changing its external behavior:

            1. **Identify improvement points**:
               - Duplicated code → extract to function/method
               - High complexity → simplify conditionals
               - Bad names → rename to be descriptive
               - Long functions → extract methods
               - Strong coupling → apply design patterns
               - Poor performance → optimize without changing the API

            2. **Implement the refactorings**:
               - One change at a time (atomic steps)
               - Each step preserves behavior
               - Existing tests must pass after each step

            3. **Document the changes**:
               - What changed and why
               - Design pattern applied (if applicable)
               - Expected benefit (readability, performance, maintainability)
               - Mitigated risks

            IMPORTANT:
            - Do NOT change external behavior (API, contracts, output)
            - Do NOT add new features
            - Do NOT remove existing features
            - Each refactoring must be small and verifiable
            - If the change is risky, highlight the risk

            Report format:
            ```
            ## Refactoring / Improvement

            ### Changes Made
            1. **Method extraction** in `file.py`:
               - What: extracted email validation into a separate method
               - Why: it was duplicated in 3 places
               - Benefit: reduced duplication, testability

            2. **Renaming** in `file.py`:
               - `calculate()` → `calculate_shipping_with_discount()`
               - Why: the original name was too generic
               - Benefit: readability

            ### Benefits
            - Readability: ...
            - Maintainability: ...
            - Performance: ...

            ### Verification
            - Behavior preserved: ✅
            - Existing tests pass: ✅
            ```
            """,
            expected_output=(
                "Refactored code with documentation of the changes: what changed, "
                "why it changed, benefits and behavior-preservation verification."
            ),
            agent=agents["refactorer"],
        )
        tasks.append(task_refactoring)

    # ─────────────────────────────────────────────────────────────────────
    # Task 4: Regression Tests + Quality Gate (Bug Analyst + Impact Analyst)
    # ─────────────────────────────────────────────────────────────────────
    task_regression = Task(
        description=f"""
        PROBLEM DESCRIPTION:
        {description}

        YOUR JOB — REGRESSION TESTS AND QUALITY GATE:

        You are the Impact Analyst (final quality gate). Validate whether the
        fix/refactoring was successful and whether there are no regressions:

        1. **Validate the fix/refactoring**:
           - Was the bug truly fixed? (if applicable)
           - Was the behavior preserved? (if refactoring)
           - Is the change consistent with the system architecture?

        2. **Run regression tests mentally**:
           - Existing tests: all must pass
           - Edge scenarios: what happens with unexpected inputs?
           - Concurrency scenarios: is the change thread-safe?
           - Failure scenarios: what happens if an external service fails?

        3. **Check code quality**:
           - Is the fix minimal? (no unrelated changes)
           - Did the refactoring preserve behavior? (if applicable)
           - Are there tests for the fixed scenario?
           - Is the code clean and readable?

        4. **Issue the final verdict**:

        ```
        ## Quality Gate — Final Verdict

        ### ✅ Verified Items
        - Complete diagnosis: [OK/ISSUES]
        - Impact analysis performed: [OK/ISSUES]
        - Fix implemented: [OK/ISSUES/NA]
        - Refactoring performed: [OK/ISSUES/NA]
        - Behavior preserved: [OK/ISSUES/NA]
        - Regression tests: [OK/ISSUES]

        ### 🔴 Problems Found
        ...

        ### 📋 Final Verdict
        ## ✅ PASS / ❌ FAIL

        ### Recommendations
        ...
        ```
        """,
        expected_output=(
            "Regression test report with complete verification and "
            "final PASS/FAIL verdict with evidence."
        ),
        agent=agents["impact"],
    )
    tasks.append(task_regression)

    # --- Builds the agent list (only the used ones) ---
    agent_list = []
    if mode in ("bug-fix", "full"):
        agent_list.append(agents["analyst"])
    agent_list.append(agents["impact"])
    if mode in ("bug-fix", "full"):
        agent_list.append(agents["fixer"])
    if mode in ("refactor", "improvement", "full"):
        agent_list.append(agents["refactorer"])

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
        description="cp-maintenance: Software Maintenance and Evolution Crew (self-contained)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py "the /login endpoint returns 500 when the email has an accent" --mode bug-fix
  python run.py "refactor the payments module to use the Strategy Pattern" --mode refactor
  python run.py "improve the performance of the reports query" --mode improvement
  python run.py "fix a bug in the shipping calculation and refactor the discount logic" --mode full
  python run.py --input bug_report.md --mode bug-fix --output ./fixes
  python run.py "test" --dry-run
        """,
    )
    parser.add_argument(
        "description",
        nargs="?",
        help="Description of the bug / improvement request / refactoring",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="File with the problem description (alternative to the positional argument)",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["bug-fix", "refactor", "improvement", "full"],
        default="full",
        help="Operation mode (default: full = complete pipeline)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output directory to save reports",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only builds the crew and shows the agents, without running",
    )
    args = parser.parse_args()

    require_crewai()  # DT-07: actionable message instead of a traceback

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
        print("\n❌ Error: provide the problem description (argument or --input)")
        sys.exit(1)

    output_dir = args.output

    # --- Mode map ---
    mode_label = {
        "bug-fix": "Bug Fix",
        "refactor": "Refactoring",
        "improvement": "Improvement",
        "full": "Complete Pipeline (Diagnosis → Impact → Fix/Refactoring → Tests)",
    }

    print(f"\n📋 Description: {description[:120]}...")
    print(f"🔧 Mode: {mode_label.get(args.mode, args.mode)}")
    print(f"📂 Agents: embedded (self-contained)")
    print()

    crew = build_crew(description, args.mode, output_dir)

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

    print("🚀 Running maintenance crew...\n")
    require_llm()  # DT-08: fails early, with a message, if there is no LLM
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Maintenance complete!\n")
    print(result_str)

    # --- Save output ---
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        report_file = out_path / "maintenance_report.md"
        report_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Report saved to: {report_file.resolve()}")
    else:
        # Save to default location
        output_path = Path(__file__).resolve().parent.parent / "outputs"
        output_path.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = output_path / f"maintenance_{timestamp}.md"
        report_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Report saved to: {report_file.resolve()}")


if __name__ == "__main__":
    main()
