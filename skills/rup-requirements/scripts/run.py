#!/usr/bin/env python3
"""
rup-requirements — RUP Requirements discipline (host-LLM, ADR-0012).

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
# The Requirements discipline: RUP roles, missions and the artifacts each one owns
# ═════════════════════════════════════════════════════════════════════════

SPEC = {'key': 'requirements',
 'title': 'Requirements',
 'agents': [{'slug': 'system-analyst',
             'role': 'System Analyst',
             'goal': 'Produce Stakeholder Requests, the Vision Document, the Use-Case '
                     'Model Survey, System Actors, the Glossary and the Requirements '
                     'Management Plan.',
             'backstory': 'System analyst who owns the problem space: you elicit '
                          'stakeholder requests, draw the system boundary, survey all '
                          'actors and use cases, and set up the requirements management '
                          'and traceability strategy.',
             'mission': "Elicit and structure stakeholders' needs, delimit the system "
                        'boundary and define the functional vision and high-level '
                        'attributes.',
             'artifacts': ['Stakeholder Requests',
                           'Vision Document',
                           'Use-Case Model Survey',
                           'System Actors',
                           'Glossary',
                           'Requirements Management Plan']},
            {'slug': 'requirements-specifier',
             'role': 'Requirements Specifier',
             'goal': 'Produce detailed Use Cases (basic, alternative and exception flows), '
                     'Use-Case Packages, Supplementary Specifications (FURPS), the SRS and '
                     'Requirements Attributes.',
             'backstory': 'Requirements specifier who turns surveys into contracts: you '
                          "write every use case's basic, alternative and exception flows, "
                          'organize non-functional requirements by FURPS, and assemble the '
                          'formal SRS with traceable attributes.',
             'mission': 'Detail the behavioral specifications of the use cases and the '
                        'supplementary quality specifications of the system.',
             'artifacts': ['Use Cases',
                           'Use-Case Packages',
                           'Supplementary Specifications (FURPS)',
                           'Software Requirements Specification (SRS)',
                           'Requirements Attributes']}]}


if __name__ == "__main__":
    setup_console()  # UTF-8 on stdout/stderr (Windows console is cp1252)
    discipline.main(SPEC, script=__file__)
