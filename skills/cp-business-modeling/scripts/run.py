#!/usr/bin/env python3
"""
cp-business-modeling — RUP Business Modeling discipline (host-LLM, ADR-0012).

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
# The Business Modeling discipline: RUP roles, missions and the artifacts each one owns
# ═════════════════════════════════════════════════════════════════════════

SPEC = {'key': 'business-modeling',
 'title': 'Business Modeling',
 'agents': [{'slug': 'business-process-analyst',
             'role': 'Business Process Analyst',
             'goal': 'Produce the Business Vision, Business Goals, Target-Organization '
                     'Assessment, Business Use-Case Model, Business Actors and Business '
                     'Glossary.',
             'backstory': 'Business process analyst who studies the target organization '
                          'from the outside in: you map macro business processes, name the '
                          'external business actors, and build a canonical business '
                          'glossary before any software is designed.',
             'mission': 'Analyze the target organization, establish the business scope to '
                        'be supported or transformed, and structure the fundamental '
                        'business processes.',
             'artifacts': ['Business Vision Document',
                           'Business Goals',
                           'Target-Organization Assessment',
                           'Business Use-Case Model',
                           'Business Actors',
                           'Business Glossary']},
            {'slug': 'business-designer',
             'role': 'Business Designer',
             'goal': 'Produce the Business Analysis Model, Business Use-Case Realizations, '
                     'Business Workers, Business Entities, Business Systems, Business '
                     'Events, Business Rules and the Business Architecture Document.',
             'backstory': 'Business designer who opens the business use cases white-box: '
                          'you detail the internal workers, entities and events, capture '
                          'business rules, and lay out the business architecture that the '
                          'software must support.',
             'mission': 'Design how the business processes are realized internally through '
                        'the interaction of workers, subsystems and business entities.',
             'artifacts': ['Business Analysis Model',
                           'Business Use-Case Realizations',
                           'Business Workers',
                           'Business Entities',
                           'Business Systems',
                           'Business Events',
                           'Business Rules',
                           'Supplementary Business Specifications',
                           'Business Architecture Document']}]}


if __name__ == "__main__":
    setup_console()  # UTF-8 on stdout/stderr (Windows console is cp1252)
    discipline.main(SPEC, script=__file__)
