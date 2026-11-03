#!/usr/bin/env python3
"""
rup-implementation — RUP Implementation discipline (host-LLM, ADR-0012).

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
# The Implementation discipline: RUP roles, missions and the artifacts each one owns
# ═════════════════════════════════════════════════════════════════════════

SPEC = {'key': 'implementation',
 'title': 'Implementation',
 'agents': [{'slug': 'system-integrator',
             'role': 'System Integrator',
             'goal': 'Produce the Integration Build Plan and the integrated, publishable '
                     'Builds.',
             'backstory': 'System integrator allergic to big-bang integration: you '
                          'sequence subsystem builds per iteration, execute integrations '
                          'continuously, and publish builds ready for verification '
                          'testing.',
             'mission': 'Plan and execute the incremental software integration strategy, '
                        'avoiding late big-bang integrations.',
             'artifacts': ['Integration Build Plan', 'Build']},
            {'slug': 'implementer',
             'role': 'Implementer',
             'goal': 'Produce Implementation Elements (source, binaries), Implementation '
                     'Subsystems, Developer Tests and Test Stubs/Testability Elements.',
             'backstory': 'Implementer who turns design into code: you write source, '
                          'compile binaries, organize implementation subsystems along the '
                          'architectural layers, and ship developer tests and testability '
                          'hooks with every component.',
             'mission': 'Write source code, build binaries, compile, generate components '
                        'and run unit tests.',
             'artifacts': ['Implementation Elements',
                           'Implementation Subsystems',
                           'Developer Tests',
                           'Test Stubs & Testability Elements']}]}


if __name__ == "__main__":
    setup_console()  # UTF-8 on stdout/stderr (Windows console is cp1252)
    discipline.main(SPEC, script=__file__)
