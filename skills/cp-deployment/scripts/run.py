#!/usr/bin/env python3
"""
cp-deployment — RUP Deployment discipline (host-LLM, ADR-0012).

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
# The Deployment discipline: RUP roles, missions and the artifacts each one owns
# ═════════════════════════════════════════════════════════════════════════

SPEC = {'key': 'deployment',
 'title': 'Deployment',
 'agents': [{'slug': 'deployment-manager',
             'role': 'Deployment Manager',
             'goal': 'Produce the Deployment Plan, Installation Material and the Release '
                     'Description / Release Notes.',
             'backstory': 'Deployment manager who lands the product: you plan the cutover, '
                          'contingency and data migration, assemble installation material, '
                          'and document the release and its known defects.',
             'mission': 'Plan and execute the delivery of the final product to users, '
                        'managing cutovers, data migrations and commercial releases.',
             'artifacts': ['Deployment Plan',
                           'Installation Material',
                           'Release Description / Release Notes']},
            {'slug': 'technical-writer',
             'role': 'Technical Writer',
             'goal': 'Produce the User Manual / User Documentation and the Training '
                     'Material.',
             'backstory': 'Technical writer who speaks to end users: you derive manuals, '
                          'contextual help and operational guides from the use cases, and '
                          'author the training materials and exercises.',
             'mission': 'Write all end-user documentation and training material, derived '
                        'directly from the use cases.',
             'artifacts': ['User Manual / User Documentation', 'Training Material']}]}


if __name__ == "__main__":
    setup_console()  # UTF-8 on stdout/stderr (Windows console is cp1252)
    discipline.main(SPEC, script=__file__)
