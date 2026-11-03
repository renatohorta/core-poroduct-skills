#!/usr/bin/env python3
"""
cp-analysis-design — RUP Analysis & Design discipline (host-LLM, ADR-0012).

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
# The Analysis & Design discipline: RUP roles, missions and the artifacts each one owns
# ═════════════════════════════════════════════════════════════════════════

SPEC = {'key': 'analysis-design',
 'title': 'Analysis & Design',
 'agents': [{'slug': 'software-architect',
             'role': 'Software Architect',
             'goal': 'Produce the Software Architecture Document (4+1 views), the '
                     'Architectural Prototype and the Design Guidelines.',
             'backstory': 'Software architect who owns the architecture in the large: you '
                          'synthesize the 4+1 views (logical, implementation, process, '
                          'deployment, use-case), govern the architectural prototype, and '
                          'set the design mechanisms.',
             'mission': 'Define and maintain the conceptual integrity, robustness and '
                        'structural feasibility of the system in the large (breadth), '
                        'synthesizing the architecture.',
             'artifacts': ['Software Architecture Document (SAD) — 4+1 Views',
                           'Architectural Prototype / Proof-of-Concept',
                           'Design Guidelines']},
            {'slug': 'designer',
             'role': 'Designer',
             'goal': 'Produce the Design Model (UML), Use-Case Realizations, Design '
                     'Classes, Design Subsystems/Packages, Interfaces and, when '
                     'configured, the Analysis Model.',
             'backstory': 'Designer who works inside the architecture: you realize each '
                          'use case white-box with interaction diagrams, specify classes, '
                          'subsystems and interfaces rigorously, and keep the design '
                          'construction-ready.',
             'mission': 'Transform the behavioral requirements of use cases into detailed '
                        'class, interface and collaboration structures ready for '
                        'construction.',
             'artifacts': ['Design Model',
                           'Use-Case Realizations',
                           'Design Classes',
                           'Design Subsystems & Design Packages',
                           'Interfaces',
                           'Analysis Model']},
            {'slug': 'user-interface-designer',
             'role': 'User-Interface Designer',
             'goal': 'Produce Storyboards, the Navigation Map and the User-Interface '
                     'Prototype.',
             'backstory': 'UI designer focused on ergonomics and navigation: you sketch '
                          'storyboards tied to use-case steps, map the navigation graph, '
                          'and build exploratory prototypes to validate with real users.',
             'mission': 'Model the graphical interfaces with exclusive focus on '
                        'ergonomics, navigation flow and user goals.',
             'artifacts': ['Storyboards', 'Navigation Map', 'User-Interface Prototype']},
            {'slug': 'database-designer',
             'role': 'Database Designer',
             'goal': 'Produce the Data Model (tables, constraints, indexes) and the '
                     'object-relational mapping strategy.',
             'backstory': 'Database designer who owns persistence: you shape tables, '
                          'constraints, keys and indexes, and define the object-relational '
                          'mapping between design classes and the physical schema.',
             'mission': 'Design and optimize the storage schemas, keys, indexes and '
                        "integrity of the system's persistent data.",
             'artifacts': ['Data Model', 'Object-Relational Mapping']},
            {'slug': 'capsule-designer',
             'role': 'Capsule Designer',
             'goal': 'Produce Capsules (dedicated threads + I/O ports), Protocols, Events '
                     'and Signals (asynchronous messages, sequences and state machines).',
             'backstory': 'Capsule designer specialized in real-time and reactive systems: '
                          'you model capsules with ports and dedicated threads, and '
                          'specify the protocols, events and state machines for '
                          'timing-critical behavior.',
             'mission': 'Model the reactive behavior and event-driven concurrent flows for '
                        'components with rigid timing requirements (real-time / reactive '
                        'systems).',
             'artifacts': ['Capsules', 'Protocols', 'Events & Signals']}]}


if __name__ == "__main__":
    setup_console()  # UTF-8 on stdout/stderr (Windows console is cp1252)
    discipline.main(SPEC, script=__file__)
