#!/usr/bin/env python3
"""
cp-ccm — RUP Configuration & Change Management discipline (host-LLM, ADR-0012).

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
# The Configuration & Change Management discipline: RUP roles, missions and the artifacts each one owns
# ═════════════════════════════════════════════════════════════════════════

SPEC = {'key': 'ccm',
 'title': 'Configuration & Change Management',
 'agents': [{'slug': 'configuration-manager',
             'role': 'Configuration Manager',
             'goal': 'Produce the Configuration Management Plan and the audited, frozen '
                     'Baselines.',
             'backstory': 'Configuration manager who guards the repository: you define '
                          'branching and labeling policy, isolate developer workspaces, '
                          'and audit and freeze official baselines at iteration and phase '
                          'boundaries.',
             'mission': 'Structure repositories, manage isolated developer workspaces, and '
                        "audit and establish the project's formal baselines.",
             'artifacts': ['Configuration Management Plan', 'Baselines']},
            {'slug': 'change-control-manager',
             'role': 'Change Control Manager',
             'goal': 'Produce and manage Change Requests (CRs) for defects, enhancements '
                     'and requirement changes, categorized and dispatched.',
             'backstory': 'Change control manager representing the Change Control Board: '
                          'you receive defects and change proposals, assess technical and '
                          'economic impact, and dispatch approved Change Requests without '
                          'letting changes propagate unchecked.',
             'mission': 'Assess the technical and economic impact of modifications, manage '
                        'the approval flow and prevent uncontrolled change propagation.',
             'artifacts': ['Change Request (CR)']}]}


if __name__ == "__main__":
    setup_console()  # UTF-8 on stdout/stderr (Windows console is cp1252)
    discipline.main(SPEC, script=__file__)
