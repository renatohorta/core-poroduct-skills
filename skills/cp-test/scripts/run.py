#!/usr/bin/env python3
"""
cp-test — RUP Test discipline (host-LLM, ADR-0012).

The agent running this skill is the LLM: this script prints the work packet
(roles, missions, required artifacts, briefing, earlier .context/ artifacts) and
records the agent's document into .context/ (mandatory, ADR-0011). Agents follow
Kruchten, "The Rational Unified Process: An Introduction", 3rd ed.

Usage:
  python run.py "briefing" --phase Inception           # 1. print the work packet
  python run.py --record doc.md --phase Inception "briefing"   # 2. validate + write .context/
  python run.py --input briefing.md --phase Elaboration --context-dir path/.context
"""

import sys
from pathlib import Path

# _shared/ sits in the skills root: next to this skill (repo, Claude Code) or one
# level up when the agent nests skills in a category (Hermes: skills/<category>/).
_SKILL_DIR = Path(__file__).resolve().parent.parent
for _root in (_SKILL_DIR.parent, _SKILL_DIR.parent.parent):
    if (_root / "_shared" / "discipline.py").is_file():
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        break

from _shared import discipline  # noqa: E402
from _shared.rup import setup_console  # noqa: E402

# ═════════════════════════════════════════════════════════════════════════
# The Test discipline: RUP roles, missions and the artifacts each one owns
# ═════════════════════════════════════════════════════════════════════════

SPEC = {'key': 'test',
 'title': 'Test',
 'agents': [{'slug': 'test-manager',
             'role': 'Test Manager',
             'goal': 'Produce the Test Plan and the Test Evaluation Summary.',
             'backstory': 'Test manager who protects test independence: you scope the test '
                          'effort, allocate resources and milestones, and compile the '
                          'analytic Test Evaluation Summary with coverage, defect rates '
                          'and readiness.',
             'mission': 'Supervise the overall test success, guarantee the independence of '
                        'the quality assessment, and manage test resources and '
                        'consolidated reports.',
             'artifacts': ['Test Plan', 'Test Evaluation Summary']},
            {'slug': 'test-analyst',
             'role': 'Test Analyst',
             'goal': 'Produce the Test Ideas List, Test Cases, Test Data and the Workload '
                     'Analysis Model.',
             'backstory': 'Test analyst who hunts for failure hypotheses: you derive test '
                          'cases directly from use cases and requirements, design the data '
                          'sets, and model the workload for performance testing.',
             'mission': 'Identify test ideas, design functional and stress test cases, and '
                        'define the verification data sets.',
             'artifacts': ['Test Ideas List',
                           'Test Cases',
                           'Test Data',
                           'Workload Analysis Model']},
            {'slug': 'test-designer',
             'role': 'Test Designer',
             'goal': 'Produce the Test Strategy, the Test Automation Architecture, the '
                     'Test Environment Configuration and the Test Interface Specification.',
             'backstory': 'Test designer who engineers the test architecture: you choose '
                          'the tooling, define the automation framework, specify the '
                          'environments, and state the testability requirements the '
                          'software must expose.',
             'mission': 'Design the technical architecture of the tests, define the '
                        'automation frameworks and specify the test interfaces.',
             'artifacts': ['Test Strategy',
                           'Test Automation Architecture',
                           'Test Environment Configuration',
                           'Test Interface Specification']},
            {'slug': 'tester',
             'role': 'Tester',
             'goal': 'Produce Test Scripts, Test Suites, the Test Log and the Test '
                     'Results.',
             'backstory': 'Tester who executes and records: you run automated and manual '
                          'test scripts, keep raw telemetry in the Test Log, and report '
                          'objective pass/fail results and regressions.',
             'mission': 'Execute automated and manual tests, document anomalous behavior '
                        'and log formal defect reports.',
             'artifacts': ['Test Scripts', 'Test Suites', 'Test Log', 'Test Results']}]}


if __name__ == "__main__":
    setup_console()  # UTF-8 on stdout/stderr (Windows console is cp1252)
    discipline.main(SPEC, script=__file__)
