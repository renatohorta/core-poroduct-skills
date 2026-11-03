#!/usr/bin/env python3
"""
cp-environment — RUP Environment discipline (host-LLM, ADR-0012).

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
# The Environment discipline: RUP roles, missions and the artifacts each one owns
# ═════════════════════════════════════════════════════════════════════════

SPEC = {'key': 'environment',
 'title': 'Environment',
 'agents': [{'slug': 'process-engineer',
             'role': 'Process Engineer',
             'goal': 'Customize the RUP process, define the Development Case and produce '
                     'the project-specific templates and guidelines.',
             'backstory': 'RUP process engineer who tailors the method to the project: you '
                          'decide which artifacts, roles and steps are mandatory, produce '
                          'the Development Case, and keep the templates and guidelines '
                          "realistic for the team's size.",
             'mission': 'Tailor and adapt the RUP framework to the size and complexity of '
                        'the project, defining which artifacts, roles and steps are '
                        'mandatory.',
             'artifacts': ['Development Case',
                           'Project-Specific Guidelines',
                           'Templates']}]}


if __name__ == "__main__":
    setup_console()  # UTF-8 on stdout/stderr (Windows console is cp1252)
    discipline.main(SPEC, script=__file__)
