#!/usr/bin/env python3
"""
cp-testing — Software Testing Crew (self-contained)

Creates a CrewAI crew with specialized Test Engineers to validate
software quality: unit, integration, E2E, performance and analysis.

Usage:
  python run.py "scheduling system" --source ./src
  python run.py "REST API" --source ./src --mode unit --output report.md
  python run.py "mobile app" --source ./src --mode full --acceptance criteria.md
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
    "unit-test-engineer": {
        "role": "Unit Test Engineer",
        "goal": (
            "Create complete, isolated unit tests with minimum 80% coverage, "
            "ensuring that each function/method is tested independently"
        ),
        "backstory": (
            "Test engineer obsessed with coverage and isolation. "
            "You believe all code should be tested in isolation, without external dependencies. "
            "You use mocks, stubs and fakes masterfully to isolate the unit under test. "
            "You write tests in pytest (Python) or Jest (JavaScript/TypeScript) following the "
            "AAA (Arrange-Act-Assert) pattern. Your motto: 'Coverage below 80% is technical debt.' "
            "You ensure that every branch, exception and edge case is covered."
        ),
    },
    "integration-test-engineer": {
        "role": "Integration Test Engineer",
        "goal": (
            "Test the integration between components, modules and services, "
            "ensuring that communication between them works correctly"
        ),
        "backstory": (
            "Specialist in finding bugs that only appear when components talk to each other. "
            "You test APIs, databases, queues, external services and the orchestration between them. "
            "You configure test databases, spin up dependencies in containers, and validate API contracts. "
            "You use testcontainers, pytest-integration, supertest or similar tools. "
            "You know unit tests pass but integration breaks — and it is your job "
            "to ensure that doesn't happen. Your motto: 'The system only works when the parts talk.'"
        ),
    },
    "e2e-test-engineer": {
        "role": "E2E Test Engineer",
        "goal": (
            "Create deterministic end-to-end tests that validate complete "
            "user flows, using role-based selectors and conditional waits"
        ),
        "backstory": (
            "E2E test engineer who hates sleeps with a passion. "
            "You use Playwright or Cypress with role-based selectors (getByRole, getByText) "
            "instead of fragile XPath or structure-dependent CSS. "
            "All waits are conditional (waitForSelector, waitForResponse, waitForURL) — "
            "never setTimeout. Your tests are deterministic: run 10x in a row and pass 10x. "
            "You test complete flows: login → navigation → action → verification → logout. "
            "Your motto: 'Sleep is a symptom of a badly written test.'"
        ),
    },
    "performance-test-engineer": {
        "role": "Performance Test Engineer",
        "goal": (
            "Perform load testing, stress testing and benchmarks to identify "
            "bottlenecks before users find them"
        ),
        "backstory": (
            "Performance engineer who finds bottlenecks before the user complains. "
            "You use k6, Locust or JMeter to simulate realistic load. "
            "Favorite metric: p95. You know p50 lies and p99 is cruel. "
            "You test scenarios: normal load (100 users), peak (1000 users) and stress (5000+). "
            "You monitor CPU, memory, database I/O and network latency during tests. "
            "Your motto: 'Performance is not a feature, it is a non-functional requirement.' "
            "Goals: p95 < 500ms for REST APIs, < 3s for page loading."
        ),
    },
    "results-analyst": {
        "role": "Test Results Analyst",
        "goal": (
            "Compile results from all test categories, calculate coverage, "
            "identify regressions and issue the final PASS/FAIL verdict"
        ),
        "backstory": (
            "Analyst who turns test data into quality decisions. "
            "You compile results from unit, integration, E2E and performance tests "
            "into a cohesive, actionable report. You calculate aggregate coverage per module. "
            "You identify regressions by comparing with previous runs. "
            "Your quality gate is rigorous: minimum 80% coverage, zero critical failures, "
            "performance within SLAs. You issue PASS only when EVERYTHING is green. "
            "If FAIL, you list exactly what needs to be fixed, prioritized by severity. "
            "Your motto: 'Test data without analysis is just noise.'"
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
    source_path: str = None,
    acceptance_criteria: str = None,
    mode: str = "full",
):
    """Build a CrewAI crew for software testing."""

    unit = get_agent("unit-test-engineer")
    integration = get_agent("integration-test-engineer")
    e2e = get_agent("e2e-test-engineer")
    performance = get_agent("performance-test-engineer")
    analyst = get_agent("results-analyst")

    # Build context block
    context_parts = [f"SYSTEM DESCRIPTION:\n{description}"]
    if source_path:
        context_parts.append(f"\nSOURCE CODE DIRECTORY: {source_path}")
    if acceptance_criteria:
        context_parts.append(f"\nACCEPTANCE CRITERIA:\n{acceptance_criteria}")
    context = "\n".join(context_parts)

    # --- Task 1: Analysis and Planning (Analyst) ---
    task_analysis = Task(
        description=f"""
        {context}

        YOUR JOB — CODE ANALYSIS AND TEST PLANNING:

        As Results Analyst, your first task is to ANALYZE the described
        system and PLAN the testing strategy.

        1. Analyze the system description and identify:
           - Main modules/components
           - Critical user flows
           - APIs and endpoints
           - External dependencies
           - Risk points (authentication, payment, sensitive data)

        2. For each module, determine:
           - Which functions/methods need unit tests
           - Which integrations need integration tests
           - Which complete flows need E2E tests
           - Which endpoints/scenarios need performance tests

        3. Define the coverage strategy:
           - Coverage target per module (minimum 80%)
           - Priority of each module (Critical/High/Medium/Low)
           - Test techniques (white box, black box, mutation)

        4. Estimate the effort of each test category

        OUTPUT FORMAT:
        ## Test Plan
        - Identified modules: [list]
        - Critical flows: [list]
        - Unit strategy: [description]
        - Integration strategy: [description]
        - E2E strategy: [description]
        - Performance strategy: [description]
        - Coverage targets: [table per module]
        - Estimated effort: [per category]
        """,
        expected_output=(
            "Complete test plan with modules, strategies, "
            "coverage targets and effort estimate"
        ),
        agent=analyst,
    )

    # --- Task 2: Unit Tests ---
    task_unit = Task(
        description=f"""
        {context}

        YOUR JOB — CREATING UNIT TESTS:

        Based on the test plan, create complete unit tests.

        1. For each identified function/method:
           - Create a test for the happy path
           - Create a test for each error condition
           - Create a test for edge cases (boundary values, empty, null)
           - Create a test for exceptions

        2. Follow the AAA (Arrange-Act-Assert) pattern:
           - Arrange: prepare the scenario (mocks, inputs)
           - Act: execute the function under test
           - Assert: verify the expected result

        3. Use mocks to isolate the unit:
           - Mock database calls
           - Mock external API calls
           - Mock file system and network

        4. Naming: test_[function]_[scenario]

        5. For each test, document:
           - What is being tested
           - Pre-conditions
           - Expected result

        OUTPUT FORMAT:
        ## Unit Tests
        - Framework: pytest / Jest
        - Total tests created: [N]
        - Estimated coverage: [X]%
        - List of tests with description and expected result
        - Test code (at least 5 complete examples)
        """,
        expected_output=(
            "Unit test suite with minimum 80% coverage, "
            "including example code and documentation"
        ),
        agent=unit,
    )

    # --- Task 3: Integration Tests ---
    task_integration = Task(
        description=f"""
        {context}

        YOUR JOB — CREATING INTEGRATION TESTS:

        Based on the test plan, create integration tests.

        1. For each identified integration point:
           - REST API test (status codes, headers, body, schemas)
           - Database test (CRUD, transactions, concurrency)
           - Queue/messaging test (produce/consume, order, retry)
           - External service test (mocked or in container)

        2. Mandatory scenarios:
           - Successful integration (complete flow)
           - Timeout and retry
           - Invalid data at the interface
           - Authentication/authorization between services
           - Concurrency (simultaneous requests)

        3. Use testcontainers or real database fixtures:
           - Spin up a clean test database
           - Populate with seed data
           - Run operations and verify state

        4. For REST APIs, validate:
           - OpenAPI/Swagger contract
           - Request/response schemas
           - Correct HTTP codes (200, 201, 400, 401, 404, 500)
           - Headers (CORS, Content-Type, Auth)

        OUTPUT FORMAT:
        ## Integration Tests
        - Tested integration points: [list]
        - Total tests: [N]
        - Integration coverage: [X]%
        - Test code (at least 3 complete examples)
        - Expected results per scenario
        """,
        expected_output=(
            "Integration test suite covering APIs, database, "
            "and communication between services"
        ),
        agent=integration,
    )

    # --- Task 4: E2E Tests ---
    task_e2e = Task(
        description=f"""
        {context}

        YOUR JOB — CREATING E2E TESTS:

        Based on the test plan, create end-to-end tests.

        1. For each identified critical flow:
           - Login/authentication flow
           - Main user flow (registration, query, action)
           - Error flow (invalid data, 404, server down)
           - Logout/session expiration flow

        2. Mandatory rules:
           - NEVER use sleep() or setTimeout() — use conditional waits
           - Use role-based selectors: getByRole, getByLabel, getByText
           - Each test must be independent (own setup/teardown)
           - Tests must be deterministic (run Nx and pass Nx)

        3. Structure of each test:
           - Setup: create necessary data (via API, not UI)
           - Navigate: go to the page under test
           - Act: interact with the UI (clicks, inputs, submits)
           - Verify: assertions on the final UI state
           - Teardown: clean up created data

        4. Screenshots on failure for debugging

        OUTPUT FORMAT:
        ## E2E Tests
        - Tested flows: [list]
        - Total tests: [N]
        - Framework: Playwright / Cypress
        - Test code (at least 3 complete flows)
        - Data cleanup strategy
        """,
        expected_output=(
            "Deterministic E2E test suite covering critical "
            "user flows, without sleeps, with role-based selectors"
        ),
        agent=e2e,
    )

    # --- Task 5: Performance Tests ---
    task_performance = Task(
        description=f"""
        {context}

        YOUR JOB — PERFORMANCE TESTS:

        Based on the test plan, create performance test scenarios.

        1. Mandatory scenarios:
           - **Normal load**: simulate 100 simultaneous users for 5 minutes
           - **Peak**: simulate 1000 simultaneous users for 2 minutes
           - **Stress**: gradually increase up to 5000 users or until the system breaks
           - **Soak**: keep 500 users for 30 minutes (memory leak)

        2. Metrics to collect:
           - p50, p95, p99 latency
           - Throughput (requests/second)
           - Error rate (%)
           - Server CPU and memory
           - Active database connections

        3. Recommended SLAs:
           - p95 < 500ms for REST APIs
           - p95 < 3s for page loading
           - Error rate < 1% under normal load
           - Minimum throughput: 100 req/s

        4. For each critical endpoint:
           - GET (read): query scenario
           - POST (write): creation scenario
           - PUT/PATCH (update): modification scenario
           - DELETE (removal): deletion scenario

        OUTPUT FORMAT:
        ## Performance Tests
        - Scenarios: [normal load, peak, stress, soak]
        - Tested endpoints: [list]
        - Expected metrics: [p50/p95/p99/throughput/error table]
        - Defined SLAs: [list]
        - Scenario code (k6/Locust) — at least 2 examples
        - Suggested thresholds and alerts
        """,
        expected_output=(
            "Performance test suite with load, peak, "
            "stress and soak scenarios, metrics and defined SLAs"
        ),
        agent=performance,
    )

    # --- Task 6: Compilation and Final Report (Analyst) ---
    task_report = Task(
        description=f"""
        {context}

        YOUR JOB — COMPILATION AND FINAL REPORT:

        As Results Analyst, compile all the results from the previous
        phases and produce the final test report.

        1. Compile the results of each category:
           - Unit Tests: total, coverage, pass/fail
           - Integration Tests: total, coverage, pass/fail
           - E2E Tests: total, covered flows, pass/fail
           - Performance Tests: metrics, SLAs, pass/fail

        2. Calculate the aggregate coverage:
           - Total system coverage
           - Coverage per module
           - Coverage gap (what was not tested)

        3. Identify regressions:
           - Compare with previous runs (if available)
           - Highlight new failures
           - Highlight performance degradation

        4. Quality Gate — issue verdict:
           - **PASS** if:
             - Coverage >= 80% in all modules
             - Zero critical failures
             - Performance within SLAs (p95 < 500ms API, < 3s page)
           - **FAIL** otherwise, with a prioritized list of what to fix

        5. Recommendations:
           - What to improve in the next iteration
           - Residual risks
           - Automation suggestions

        OUTPUT FORMAT:
        ## Final Test Report

        ### Executive Summary
        - Verdict: PASS / FAIL
        - Total coverage: [X]%
        - Tests created: [N] (unit: N, integration: N, E2E: N, perf: N)
        - Performance: p95 [X]ms / SLA [Y]ms

        ### Breakdown by Category
        [table with results of each category]

        ### Coverage by Module
        [module | coverage | status table]

        ### Identified Regressions
        [list if any]

        ### Quality Gate
        - Coverage >= 80%: ✅ / ❌
        - Critical failures = 0: ✅ / ❌
        - Performance OK: ✅ / ❌
        - Final Verdict: PASS / FAIL

        ### Recommendations
        [prioritized list]
        """,
        expected_output=(
            "Complete final test report with PASS/FAIL verdict, "
            "aggregate coverage, performance metrics and recommendations"
        ),
        agent=analyst,
    )

    # --- Build task list based on mode ---
    all_tasks = [task_analysis]

    if mode in ("full", "unit"):
        all_tasks.append(task_unit)
    if mode in ("full", "integration"):
        all_tasks.append(task_integration)
    if mode in ("full", "e2e"):
        all_tasks.append(task_e2e)
    if mode in ("full", "performance"):
        all_tasks.append(task_performance)

    all_tasks.append(task_report)

    # --- Agents used in this run ---
    used_agents = [analyst]
    if mode in ("full", "unit"):
        used_agents.append(unit)
    if mode in ("full", "integration"):
        used_agents.append(integration)
    if mode in ("full", "e2e"):
        used_agents.append(e2e)
    if mode in ("full", "performance"):
        used_agents.append(performance)

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
        description="cp-testing: Software Testing Crew (self-contained)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python run.py \"scheduling system\" --source ./src\n"
            "  python run.py \"REST API\" --source ./src --mode unit\n"
            "  python run.py \"mobile app\" --source ./src --mode full --output report.md\n"
            "  python run.py \"test\" --dry-run\n"
        ),
    )
    parser.add_argument(
        "description",
        nargs="?",
        help="Description of the system to be tested",
    )
    parser.add_argument(
        "--input", "-i",
        dest="input_file",
        help="File with the system description (alternative to the positional argument)",
    )
    parser.add_argument(
        "--source", "-s",
        dest="source_path",
        default=None,
        help="Path of the source code directory",
    )
    parser.add_argument(
        "--acceptance", "-a",
        dest="acceptance_file",
        default=None,
        help="File with acceptance criteria",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file to save the test report",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["full", "unit", "integration", "e2e", "performance"],
        default="full",
        help="Test mode (default: full — all types)",
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
        print("\n❌ Error: provide the system description (argument or --input)")
        sys.exit(1)

    # --- Resolve acceptance criteria ---
    acceptance_criteria = None
    if args.acceptance_file:
        acceptance_criteria = Path(args.acceptance_file).read_text(encoding="utf-8")

    output_path = args.output
    mode = args.mode

    # Mode name mapping
    mode_names = {
        "full": "Complete (unit + integration + E2E + performance)",
        "unit": "Unit Tests Only",
        "integration": "Integration Tests Only",
        "e2e": "E2E Tests Only",
        "performance": "Performance Tests Only",
    }

    print(f"\n📋 System: {description[:120]}...")
    if args.source_path:
        print(f"📂 Source code: {args.source_path}")
    print(f"🔧 Mode: {mode_names.get(mode, mode)}")
    print(f"🤖 Agents: embedded (self-contained)")
    print()

    crew = build_crew(
        description=description,
        source_path=args.source_path,
        acceptance_criteria=acceptance_criteria,
        mode=mode,
    )

    if args.dry_run:
        print("🧪 DRY RUN — crew built, agents:")
        for agent in crew.agents:
            print(f"  - {agent.role}")
        print(f"\n📋 Tasks ({len(crew.tasks)}):")
        for i, task in enumerate(crew.tasks, 1):
            desc_short = task.description[:100].replace("\n", " ").strip()
            print(f"  {i}. {desc_short}...")
        print(f"\n✅ Crew ready. Remove --dry-run to execute.")
        return

    print("🚀 Running testing crew...\n")
    require_llm()  # DT-08: fail early, with a message, if there is no LLM
    result = crew.kickoff()
    result_str = str(result)

    print(f"\n✅ Test Report generated!\n")
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
        out_file = output_dir / f"test-report_{timestamp}.md"
        out_file.write_text(result_str, encoding="utf-8")
        print(f"\n📁 Saved to: {out_file.resolve()}")


if __name__ == "__main__":
    main()
